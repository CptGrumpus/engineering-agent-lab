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
    stats = f"16 studies  ·  {facts['checks']:,} automated checks  ·  {facts['runs']} saved runs  ·  open-source solvers"
    d.rectangle([(0, H - 72), (W, H)], fill=(8, 14, 26, 150))
    d.text((x, H - 50), stats, font=body, fill=INK)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(OUT, optimize=True)
    return OUT


if __name__ == "__main__":
    import extras
    print(make(extras.repo_facts()))
