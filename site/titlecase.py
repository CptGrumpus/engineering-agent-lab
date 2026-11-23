"""Title case for every title on the site: page titles, headings, study titles, card titles and the nav.

The rule (AP style, which is what most engineering publications use):
- capitalise every word, including the first and last, and the first word after a colon;
- leave articles, coordinating conjunctions and prepositions of three letters or fewer in lower case
  (a, an, the, and, but, or, nor, for, yet, as, at, by, in, of, off, on, per, to, via, vs);
- capitalise each part of a hyphenated word ("Mass-Spring-Damper"), except those short words ("Roller-on-Plate");
- leave alone anything already carrying a capital after its first letter or a digit (CAD, FEA, 3D, kW, ASME)
  and units (mm, rpm, Hz, MPa).

The build applies title_case() to every title as it writes the pages, so a heading written in sentence case in a
study fragment still comes out right. Sentences (captions, chart headings, ledes) are not titles and are left alone.
"""
import re

SMALL = {"a", "an", "the", "and", "but", "or", "nor", "for", "yet", "as", "at", "by", "in", "of", "off", "on",
         "per", "to", "via", "vs", "vs."}
UNITS = {"mm", "cm", "km", "kg", "ms", "rpm", "hz", "mpa", "kpa", "gpa"}   # kept as written after a number

WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’.]*")


def _cap(part: str) -> str:
    return part[:1].upper() + part[1:]


def _word(w: str, edge: bool, prev: str) -> str:
    if any(c.isdigit() for c in w) or any(c.isupper() for c in w[1:]):
        return w                                            # 3D, CAD, kW, ASME, 1.243
    if prev and prev[-1].isdigit() and w.lower() in UNITS:
        return w                                            # "12 mm", "7,200 rpm"
    parts = w.split("-")
    out = []
    for i, p in enumerate(parts):
        inner_edge = (edge and (i == 0 or i == len(parts) - 1)) if len(parts) > 1 else edge
        if p.lower() in SMALL and not inner_edge and not (i == 0 and len(parts) > 1 and edge):
            out.append(p.lower())
        else:
            out.append(_cap(p))
    return "-".join(out)


def title_case(text: str) -> str:
    """Title-case plain text (no tags)."""
    words = list(WORD.finditer(text))
    if not words:
        return text
    res, last = [], 0
    for i, m in enumerate(words):
        before = text[last:m.start()]
        after_colon = bool(re.search(r"[:·—–]\s*$", text[:m.start()]))
        edge = i == 0 or i == len(words) - 1 or after_colon
        prev = words[i - 1].group(0) if i else ""
        res.append(before + _word(m.group(0), edge, prev if text[words[i - 1].end():m.start()].strip() == "" else ""))
        last = m.end()
    return "".join(res) + text[last:]


def title_case_html(html: str) -> str:
    """Title-case the text of an HTML fragment that may hold inline tags (<em>, <span>), treating the words across
    all its text nodes as one title, so the first and last word are found correctly."""
    pieces = re.split(r"(<[^>]+>|&[#a-zA-Z0-9]+;)", html)
    # title-case the text with tags blanked out, then put the tags back in place
    masked = "".join(p if not p.startswith(("<", "&")) else "\x01" * len(p) for p in pieces)
    cased = title_case(masked.replace("\x01", " "))
    out, pos = [], 0
    for p in pieces:
        if p.startswith(("<", "&")):
            out.append(p)
        else:
            out.append(cased[pos:pos + len(p)])
        pos += len(p)
    return "".join(out)


# the elements whose text is a title, as they appear in the built pages
_TITLE_ELEMENTS = [
    re.compile(r"(<title>)(.*?)(</title>)", re.S),
    re.compile(r'(<meta property="og:title" content=")([^"]*)(")'),
    re.compile(r"(<h[1-4]\b[^>]*>)(.*?)(</h[1-4]>)", re.S),
    re.compile(r'(<span class="card-title">)(.*?)(</span>)', re.S),
    re.compile(r'(<a class="(?:prev|next)"[^>]*><small>[^<]*</small><b>)(.*?)(</b>)', re.S),
    re.compile(r'(<a class="linkcard"[^>]*><b>)(.*?)(</b>)', re.S),
    re.compile(r'(<div class="skill"><code>[^<]*</code><b>)(.*?)(</b>)', re.S),
    re.compile(r'(<article class="skill">\s*<span class="plan-meta">.*?</span></span>\s*<b>)(.*?)(</b>)', re.S),
    re.compile(r'(<nav class="topbar".*?</nav>)', re.S),
    re.compile(r'(<button type="button" aria-pressed="(?:true|false)" data-f="[^"]+">)(.*?)(</button>)'),
    re.compile(r'(<span class="r-no">[^<]*</span> )(.*?)(</a>)', re.S),
]


def _nav(m):
    return re.sub(r"(<a [^>]*>)([^<]*)(</a>)", lambda n: n.group(1) + title_case(n.group(2)) + n.group(3), m.group(1))


def apply(doc: str) -> str:
    """Title-case every title in a built page."""
    for pat in _TITLE_ELEMENTS:
        if pat.groups == 1:
            doc = pat.sub(_nav, doc)
        else:
            doc = pat.sub(lambda m: m.group(1) + title_case_html(m.group(2)) + m.group(3), doc)
    return doc


if __name__ == "__main__":
    for s in ["Two studies running", "Flexible flag behind a cylinder", "Mass-spring-damper baseline",
              "Roller-on-plate contact, nonlinear FEA", "Cantilever bracket: stress check, then optimised",
              "Limits, and what I'd do next", "A model that wasn't repeatable", "Simulation, proof attached.",
              "Flow over a backward-facing step", "The rotor bridge at 7,200 rpm", "Why it's harder",
              "Cable hole in a strap, CAD to FEA", "Cantilever bracket, 3D finite elements", "How I work",
              "Aluminium strap: cable hole, fatigue life and proof test", "What I can model, and with what"]:
        print(f"{s:58} -> {title_case(s)}")
    print(title_case_html("Simulation, <em>proof attached.</em>"))
