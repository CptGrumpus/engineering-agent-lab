"""Render one result scene in Blender (runs inside Blender's own Python).

    blender -b --factory-startup -P scripts/blender/render_scene.py -- SCENE.npz OUT_PREFIX [--samples N]

Reads the scene written by harness.femesh.write_scene (surface mesh, scalar
per vertex, metadata) and writes two images:

  OUT_PREFIX_beauty.png  Cycles render: studio lighting, soft shadow on a
                         transparent background, banded contour colours.
  OUT_PREFIX_flat.png    the same view, unlit emission only and no
                         anti-aliasing: the colour check reads this to prove
                         every visible colour is a legend colour.

Colour fidelity is the point. The scalar (not a colour) is stored on the
mesh and mapped to a constant-interpolation colour ramp in the shader, so
band edges are exact and nothing blends between legend colours; the view
transform is "Standard" so Blender's filmic/AgX tone mapping cannot shift
the colours away from the legend.
"""

import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
SCENE = Path(argv[0])
OUT = Path(argv[1])
SAMPLES = int(argv[argv.index("--samples") + 1]) if "--samples" in argv else 128
meta = json.loads(SCENE.with_suffix(".json").read_text(encoding="utf-8"))
data = np.load(SCENE)

RES = meta.get("resolution", [1600, 1000])
FILL = meta.get("fill", 0.86)          # fraction of the frame the part spans


def srgb_to_linear(c):
    c = np.asarray(c, dtype=float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


# ----------------------------------------------------------------------------- scene

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.render.resolution_x, scene.render.resolution_y = RES
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.image_settings.color_depth = "8"
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
scene.view_settings.exposure = 0.0
scene.view_settings.gamma = 1.0
scene.display_settings.display_device = "sRGB"


def use_gpu_if_available():
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for kind in ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL"):
            try:
                prefs.compute_device_type = kind
            except TypeError:
                continue
            prefs.get_devices()
            gpus = [d for d in prefs.devices if d.type == kind]
            if gpus:
                for d in prefs.devices:
                    d.use = d.type == kind
                scene.cycles.device = "GPU"
                return kind
    except Exception:  # noqa: BLE001 - any failure means CPU rendering
        pass
    scene.cycles.device = "CPU"
    return "CPU"


DEVICE = use_gpu_if_available()

# ----------------------------------------------------------------------------- geometry
# Normalise: centre the bounding box at the origin and scale the largest dimension to 2 units,
# so lights and camera distances are the same for every part whatever its size in mm.

xyz = data["xyz"]
ghost = data["ghost_xyz"] if "ghost_xyz" in data else None
allpts = xyz if ghost is None else np.vstack([xyz, ghost])
lo, hi = allpts.min(axis=0), allpts.max(axis=0)
centre, scale = (lo + hi) / 2, 2.0 / float((hi - lo).max())


def make_mesh(name, pts, tris):
    me = bpy.data.meshes.new(name)
    me.from_pydata(((pts - centre) * scale).tolist(), [], tris.tolist())
    me.validate(clean_customdata=False)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(meta.get("sharp_angle_deg", 32)))
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    return ob, me


part, part_me = make_mesh("part", xyz, data["tris"])

# ----------------------------------------------------------------------------- materials

def node_tree(mat):
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    return nt, out


contour = "value" in data
if contour:
    nb = int(meta.get("bands", 12))
    vmin, vmax = float(meta["vmin"]), float(meta["vmax"])
    s = np.clip((data["value"] - vmin) / (vmax - vmin), 0.0, 1.0 - 1e-6)
    attr = part_me.attributes.new("s", "FLOAT", "POINT")
    attr.data.foreach_set("value", s.astype(np.float32))
    band_rgb = np.asarray(meta["band_colors"], dtype=float)       # sRGB 0..1, one per band
    band_lin = srgb_to_linear(band_rgb)

    def contour_material(name, emission_only):
        mat = bpy.data.materials.new(name)
        nt, out = node_tree(mat)
        a = nt.nodes.new("ShaderNodeAttribute")
        a.attribute_type = "GEOMETRY"
        a.attribute_name = "s"
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        cr = ramp.color_ramp
        cr.interpolation = "CONSTANT"
        while len(cr.elements) < nb:
            cr.elements.new(0.5)
        for k, el in enumerate(cr.elements):
            el.position = k / nb
            el.color = (*band_lin[k], 1.0)
        nt.links.new(a.outputs["Fac"], ramp.inputs["Fac"])
        if emission_only:
            em = nt.nodes.new("ShaderNodeEmission")
            em.inputs["Strength"].default_value = 1.0
            nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
            nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
        else:
            bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
            bs.inputs["Roughness"].default_value = 0.42
            bs.inputs["Specular IOR Level"].default_value = 0.35
            nt.links.new(ramp.outputs["Color"], bs.inputs["Base Color"])
            nt.links.new(bs.outputs["BSDF"], out.inputs["Surface"])
        return mat

    beauty_mat = contour_material("contour", False)
    flat_mat = contour_material("contour_flat", True)
else:
    beauty_mat = bpy.data.materials.new("metal")
    nt, out = node_tree(beauty_mat)
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Base Color"].default_value = (*srgb_to_linear(meta.get("base_color", [0.86, 0.87, 0.89])), 1)
    bs.inputs["Metallic"].default_value = meta.get("metallic", 1.0)
    bs.inputs["Roughness"].default_value = meta.get("roughness", 0.32)
    if "Anisotropic" in bs.inputs:
        bs.inputs["Anisotropic"].default_value = meta.get("anisotropic", 0.0)
    nt.links.new(bs.outputs["BSDF"], out.inputs["Surface"])
    flat_mat = None
part_me.materials.append(beauty_mat)

def feature_edges(pts, tris, angle_deg):
    """Edges where the surface folds by more than angle_deg: the outline an FE
    post-processor draws for the undeformed shape."""
    T = pts[tris]
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-30
    e = np.sort(np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]]), axis=1)
    owner = np.tile(np.arange(len(tris)), 3)
    order = np.lexsort((e[:, 1], e[:, 0]))
    e, owner = e[order], owner[order]
    same = np.all(e[1:] == e[:-1], axis=1)
    i = np.nonzero(same)[0]
    cosang = np.einsum("ij,ij->i", n[owner[i]], n[owner[i + 1]])
    return e[i][cosang < math.cos(math.radians(angle_deg))]


ghost_ob = None
if ghost is not None:
    # undeformed shape as a thin dark outline of its feature edges: it never covers the contour colours
    edges = feature_edges(ghost, data["tris"].astype(np.int64), meta.get("sharp_angle_deg", 32))
    used = np.unique(edges)
    remap = np.full(len(ghost), -1)
    remap[used] = np.arange(len(used))
    gme = bpy.data.meshes.new("undeformed")
    gme.from_pydata(((ghost[used] - centre) * scale).tolist(), remap[edges].tolist(), [])
    curve_ob = bpy.data.objects.new("undeformed", gme)
    scene.collection.objects.link(curve_ob)
    bpy.context.view_layer.objects.active = curve_ob
    curve_ob.select_set(True)
    bpy.ops.object.convert(target="CURVE")
    ghost_ob = bpy.context.view_layer.objects.active
    ghost_ob.data.bevel_depth = meta.get("outline_width", 0.0032)
    ghost_ob.data.bevel_resolution = 2
    gm = bpy.data.materials.new("outline")
    nt, out = node_tree(gm)
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Base Color"].default_value = (0.08, 0.09, 0.11, 1)
    bs.inputs["Roughness"].default_value = 0.7
    nt.links.new(bs.outputs["BSDF"], out.inputs["Surface"])
    ghost_ob.data.materials.append(gm)
    ghost_ob.visible_shadow = False

# ----------------------------------------------------------------------------- camera
# Same angle convention as the matplotlib renders: the camera sits along
# d = (cos e cos a, cos e sin a, sin e) from the part. The focal length and lens
# shift are solved so the projected part fills FILL of the frame, centred.

e, az = math.radians(meta.get("elev", 24)), math.radians(meta.get("azim", -55))
d = np.array([math.cos(e) * math.cos(az), math.cos(e) * math.sin(az), math.sin(e)])
right = np.cross([0, 0, 1], d)
right /= np.linalg.norm(right)
up = np.cross(d, right)
P = (allpts - centre) * scale
if "frame_box" in meta:              # frame a detail: only points inside the box set the framing
    lo_b, hi_b = np.asarray(meta["frame_box"], dtype=float)
    P = P[np.all((allpts >= lo_b) & (allpts <= hi_b), axis=1)]
# aim at the framed region itself; aiming at the whole model's centre with lens shift turns a
# close-up into a long-lens, near-orthographic view (found on the contact close-up)
target = (P.min(axis=0) + P.max(axis=0)) / 2 if "frame_box" in meta else np.zeros(3)
P = P - target
radius = float(np.linalg.norm(P, axis=1).max())
dist = meta.get("distance_factor", 4.0) * radius
depth = dist - P @ d
u, v = (P @ right) / depth, (P @ up) / depth
aspect = RES[1] / RES[0]
su, sv = float(np.ptp(u)), float(np.ptp(v))
f = min(36.0 * FILL / su, 36.0 * aspect * FILL / sv)
cam_data = bpy.data.cameras.new("cam")
cam_data.sensor_fit = "HORIZONTAL"
cam_data.sensor_width = 36.0
cam_data.lens = f
cam_data.shift_x = f * float(u.min() + u.max()) / 2 / 36.0
cam_data.shift_y = f * float(v.min() + v.max()) / 2 / 36.0
cam_data.clip_start, cam_data.clip_end = 0.01, 100.0
cam = bpy.data.objects.new("cam", cam_data)
cam.location = Vector((target + d * dist).tolist())
cam.rotation_euler = Vector((-d).tolist()).to_track_quat("-Z", "Y").to_euler()
scene.collection.objects.link(cam)
scene.camera = cam

# ----------------------------------------------------------------------------- lights and ground

def area_light(name, direction, energy, size):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy, ld.size = energy, size
    ob = bpy.data.objects.new(name, ld)
    loc = np.asarray(direction, dtype=float)
    loc = loc / np.linalg.norm(loc) * 6.0
    ob.location = Vector(loc.tolist())
    ob.rotation_euler = Vector((-loc).tolist()).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(ob)
    return ob


lights = [
    area_light("key", d - 0.9 * right + 1.3 * up, meta.get("key_w", 260), 4.0),
    area_light("fill", d + 1.2 * right + 0.2 * up, meta.get("fill_w", 90), 6.0),
    area_light("rim", -d + 0.4 * up, meta.get("rim_w", 160), 3.0),
]
world = bpy.data.worlds.new("world")
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (0.9, 0.92, 0.95, 1)
bg.inputs["Strength"].default_value = meta.get("ambient", 0.25)
scene.world = world

zmin = float(((allpts - centre) * scale)[:, 2].min())
bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, zmin - 0.002))
ground = bpy.context.active_object
ground.is_shadow_catcher = True

# ----------------------------------------------------------------------------- render

scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.cycles.use_adaptive_sampling = True
scene.render.filepath = str(OUT.parent / (OUT.name + "_beauty.png"))
bpy.ops.render.render(write_still=True)

if flat_mat is not None:
    # colour-check pass: unlit, one sample at the pixel centre, nothing but the part
    part_me.materials[0] = flat_mat
    for ob in [ground, *lights] + ([ghost_ob] if ghost_ob else []):
        ob.hide_render = True
    bg.inputs["Strength"].default_value = 0.0
    scene.cycles.samples = 1
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.use_denoising = False
    scene.cycles.filter_width = 0.01
    scene.render.filepath = str(OUT.parent / (OUT.name + "_flat.png"))
    bpy.ops.render.render(write_still=True)

print(json.dumps({"render": OUT.name, "device": DEVICE, "lens_mm": round(f, 2),
                  "vertices": int(len(xyz)), "triangles": int(len(data["tris"]))}))
