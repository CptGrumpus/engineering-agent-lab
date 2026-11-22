"""The link preview card (Open Graph image) shown when the page link is pasted into LinkedIn, email or Slack.

1200 x 630, the size LinkedIn, Slack and most mail clients expect. It shows the optimised bracket render
on the viewer's background with the page headline and the counts from the run records, so the card
always agrees with the page. Called by build_v2.py; writes site/v2/og_card.png.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
OUT = HERE / "v2" / "og_card.png"
W, H = 1200, 630
TOP, BOT = (0x12, 0x1D, 0x33), (0x5A, 0x71, 0x93)       # --vp-top / --vp-bot
INK, INK2, ACCENT = (0xED, 0xF1, 0xF8), (0xB4, 0xC1, 0xD6), (0x8F, 0xA9, 0xFF)
FONTS = Path("C:/Windows/Fonts")


def _font(names: list[str], size: int) -> ImageFont.FreeTypeFont:
    for n in names:
        p = FONTS / n
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size)


def make(facts: dict) -> Path:
    img = Image.new("RGB", (W, H))
    px = ImageDraw.Draw(img)
    for y in range(H):                                   # the viewer's vertical gradient
        t = y / (H - 1)
        px.line([(0, y), (W, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(TOP, BOT)))
    grid = Image.new("RGBA", (W, H), (0, 0, 0, 0))       # faint grid, as in the viewer
    g = ImageDraw.Draw(grid)
    for x in range(0, W, 48):
        g.line([(x, 0), (x, H)], fill=(237, 241, 248, 16))
    for y in range(0, H, 48):
        g.line([(0, y), (W, y)], fill=(237, 241, 248, 16))
    img = Image.alpha_composite(img.convert("RGBA"), grid)

    part = Image.open(HERE / "v2" / "vp_bracket_opt.webp").convert("RGBA")
    part = part.crop(part.getbbox())
    # the part runs from its root (top left) down to the tip (bottom right), so it sits top right and
    # the text takes the empty triangle below it
    scale = 840 / part.width
    part = part.resize((round(part.width * scale), round(part.height * scale)), Image.LANCZOS)
    img.alpha_composite(part, (W - part.width - 36, 28))

    d = ImageDraw.Draw(img)
    mono = _font(["consola.ttf", "cour.ttf"], 18)
    title = _font(["segoeuib.ttf", "arialbd.ttf"], 62)
    body = _font(["segoeui.ttf", "arial.ttf"], 25)
    x = 64
    d.text((x, 272), "MECHANICAL ENGINEERING  ·  SIMULATION PORTFOLIO", font=mono, fill=INK2)
    d.text((x, 300), "Simulation,", font=title, fill=INK)
    d.text((x, 370), "proof attached.", font=title, fill=ACCENT)
    d.text((x, 462), "Featured: an agent-driven bracket optimisation,", font=body, fill=INK2)
    d.text((x, 494), "with all 78 candidate designs solved and checked", font=body, fill=INK2)
    stats = f"{facts.get('studies', 16)} studies  ·  {facts['checks']:,} automated checks  ·  {facts['runs']} saved runs  ·  open-source solvers"
    d.rectangle([(0, H - 72), (W, H)], fill=(8, 14, 26, 150))
    d.text((x, H - 50), stats, font=body, fill=INK)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(OUT, optimize=True)
    return OUT


def _wrap(d: ImageDraw.ImageDraw, text: str, font, width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if d.textlength(trial, font=font) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + [line]


def study(slug: str, eyebrow: str, title: str, verdict: str, image: Path, figure: bool = False) -> Path:
    """A study page's own preview card: its result image on the viewer's background, with its number, title and
    verdict, so a link to one study previews as that study. Writes site/v2/og_<slug>.png."""
    img = Image.new("RGB", (W, H))
    px = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        px.line([(0, y), (W, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(TOP, BOT)))
    img = img.convert("RGBA")
    part = Image.open(image).convert("RGBA")
    if figure:                                           # a plot: keep its light plate behind it
        plate = Image.new("RGBA", part.size, (252, 252, 251, 255))
        plate.alpha_composite(part)
        part = plate
    else:
        part = part.crop(part.getbbox())
    box_w, box_h = 560, 420
    scale = min(box_w / part.width, box_h / part.height)
    part = part.resize((round(part.width * scale), round(part.height * scale)), Image.LANCZOS)
    img.alpha_composite(part, (W - 40 - box_w + (box_w - part.width) // 2, 60 + (box_h - part.height) // 2))
    d = ImageDraw.Draw(img)
    mono = _font(["segoeuib.ttf", "arialbd.ttf"], 19)
    big = _font(["segoeuib.ttf", "arialbd.ttf"], 50)
    body = _font(["segoeui.ttf", "arial.ttf"], 25)
    x, y = 64, 96
    d.text((x, y), eyebrow.upper(), font=mono, fill=INK2)
    y += 44
    for line in _wrap(d, title, big, 500)[:4]:
        d.text((x, y), line, font=big, fill=INK)
        y += 60
    y += 18
    tw = d.textlength(verdict, font=body)
    d.rounded_rectangle([(x, y), (x + tw + 36, y + 46)], radius=23, outline=INK2, width=2)
    d.text((x + 18, y + 6), verdict, font=body, fill=INK)
    d.rectangle([(0, H - 72), (W, H)], fill=(8, 14, 26, 150))
    d.text((x, H - 50), "Justin Smith  ·  simulation portfolio  ·  every result checked against an independent reference", font=body, fill=INK)
    out = OUT.with_name(f"og_{slug}.png")
    img.convert("RGB").save(out, optimize=True)
    return out


if __name__ == "__main__":
    import extras
    print(make(extras.repo_facts()))
