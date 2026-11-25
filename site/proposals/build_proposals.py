"""Fill the two home-page mock-ups (a.html, b.html) from the site's own data.

Nothing here is typed twice: the cards, verdicts, questions and page names are read from site/build_v2.py,
the counts from the built pages in docs/, the method steps and the lessons from site/pages/how.html, and the
memo excerpt from the sample memo. Run it from anywhere:

    python site/proposals/build_proposals.py

The mock-ups link to the built study pages in docs/, so they click through.
"""
from __future__ import annotations

import ast
import html
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent
REPO = SITE.parent
GH = "https://github.com/CptGrumpus/engineering-agent-lab/blob/main/"


def esc(s: str) -> str:
    return html.escape(s, quote=True)


# ---------------------------------------------------------------- the site's data, read from its build script
src = (SITE / "build_v2.py").read_text(encoding="utf-8")


def block(start: str, end: str) -> str:
    i = src.index(start)
    return src[i:src.index(end, i)]


ns: dict = {}
exec(block("CARDS = [", "SITE_URL ="), ns)                       # CARDS, VERDICT, GROUPS, PART_OF, GALLERY
exec(block("SLUG = {", "assert set(SLUG)"), ns)
exec(block("QUESTION = {", "# the drawing that opens"), ns)
FRONT = ast.literal_eval(re.search(r"^FRONT = (\[.*?\])", src, re.M | re.S).group(1))
CARDS, VERDICT, GROUPS, PART_OF, SLUG, QUESTION = (ns[k] for k in ("CARDS", "VERDICT", "GROUPS", "PART_OF", "SLUG", "QUESTION"))
GALLERY = sorted(ns["GALLERY"], key=lambda c: FRONT.index(c[0]) if c[0] in FRONT else len(FRONT))
assert set(QUESTION) == {g[0] for g in GALLERY}

DISC = {"struct": "Structures and vibration", "fluid": "Thermal and fluids", "em": "Electric machines",
        "vehicle": "Vehicle dynamics", "geom": "Geometry", "workflow": "Workflow"}
TONE = {"pass": "ok", "fail": "bad", "fix": "bad", "mixed": "warn", "line": "warn", "most": "warn",
        "checkmiss": "warn", "closed": "warn", "held": "warn", "wip": "warn"}
BUCKET = {"ok": "Passes", "bad": "Fails", "warn": "Qualified"}


def page(gk: str) -> str:
    return f"../../docs/{SLUG[gk]}.html"


def study_url(k: str) -> str:
    gk = PART_OF.get(k, k)
    return page(gk) + (f"#{k}" if k in PART_OF else "")


def first_part(text: str, least: int = 70) -> str:
    """The opening of a card's answer: whole sentences until there are at least `least` characters."""
    out = ""
    for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text):
        out = (out + " " + s).strip()
        if len(out) >= least:
            break
    return out


def kind(d: str) -> str:
    return re.sub(r"^(New|Featured) · ", "", d)


# ---------------------------------------------------------------- counts, read from the built pages
home = (REPO / "docs" / "index.html").read_text(encoding="utf-8")
STATS = dict(re.findall(r"<dt>(.*?)</dt><dd>(.*?)</dd>", home))
reqp = (REPO / "docs" / "requirements.html").read_text(encoding="utf-8")
MET, NOT, HELD = (int(re.search(rf">(\d+) {w}<", reqp).group(1)) for w in ("met", "not met", "withheld"))
REQ_N = int(re.search(r"(\d+) requirements across", reqp).group(1))
assert MET + NOT + HELD <= REQ_N, (MET, NOT, HELD, REQ_N)
OTHER = REQ_N - MET - NOT - HELD          # statuses that count as neither (the motor's provisional pass)

how = (SITE / "pages" / "how.html").read_text(encoding="utf-8")
STEPS = re.findall(r"<li><b>(.*?)</b><span>(.*?)</span></li>", how)
LESSONS = re.findall(r'<article class="finding"><span class="label">(.*?)</span><h3>(.*?)</h3><p>(.*?)</p><a href="#(\w+)">', how)
assert len(STEPS) == 4 and len(LESSONS) >= 6, (len(STEPS), len(LESSONS))
LESSON = {k: (label, title, text) for label, title, text, k in LESSONS}

memo_path = "portfolio/deliverables/coolant-channel-memo.md"
memo = (REPO / memo_path).read_text(encoding="utf-8")


def md(s: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", esc(s))


MEMO = {
    "title": re.search(r"^# (.*)$", memo, re.M).group(1),
    "subject": re.search(r"\*\*Subject\*\* \| (.*?) \|", memo).group(1),
    "status": re.search(r"\*\*Status\*\* \| (.*?) \|", memo).group(1),
    "lead": re.search(r"## 1\. .*?\n\n(\*\*.*?\*\*)", memo, re.S).group(1),
    "bullets": re.findall(r"^- (At nominal.*|Across the gap.*)$", memo, re.M),
    "url": GH + memo_path,
}
assert len(MEMO["bullets"]) == 2

# ---------------------------------------------------------------- the three studies a visitor is sent to first
# headline numbers are quoted from the cards' own answers; the assert keeps them from drifting apart
LEAD = [
    dict(key="motor", number="18 %", unit="above the laboratory's test",
         line="A production traction motor, modelled from its drawings and parts list with nothing tuned. "
              "The model read high on back-EMF and torque, and I traced it, cause by cause, to the magnets.",
         result="../v2/fig_motor_field.webp", plate=True, quote="about 18 % high"),
    dict(key="bracket_opt", number="78 designs", unit="searched by an AI agent",
         line="The lightest machined bracket that stays under 100 MPa: 372 g at 98.3 MPa. "
              "The checks threw out the agent's first two answers before this one stood.",
         result="../v2/vp_bracket_opt.webp", plate=False, quote="78 designs"),
    dict(key="pv_nozzle", number="24 %", unit="over the limit, or 0.9 % under",
         line="A pressure vessel nozzle that passes its design code on one line and fails on another, "
              "on the same converged model. I'd judge it by the line that fails.",
         result="../v2/vp_pv_nozzle.webp", plate=False, quote="fails by 24 %"),
]
BY_KEY = {g[0]: g for g in GALLERY}
for L in LEAD:
    assert L["quote"] in BY_KEY[L["key"]][5], (L["key"], L["quote"])
    assert L["key"] in LESSON, L["key"]

# draft wording for the user to confirm; drawn from what the site already says it offers
SERVICES = [
    ("Build and check a model", "From your drawings and requirements to a verdict on each requirement, with the model, "
                                "the independent check behind it and the files to repeat it."),
    ("Check a result you already have", "An independent second answer to a number someone else produced: a hand "
                                        "calculation, a second tool or a mesh study, and a plain statement of what holds."),
    ("Automate a repeated analysis", "A sweep or an optimisation loop that an AI agent runs under written procedures, "
                                     "with the same checks on every run."),
    ("Engineering tasks for AI training", "Requirement-to-verdict tasks with automated graders, like the ones on the "
                                          "grading page."),
]
NEED = ["CV (PDF)", "LinkedIn", "Location and time zone", "Commercial tools used in industry", "Typical turnaround"]


# ---------------------------------------------------------------- shared pieces
def chip(v: str) -> str:
    return f'<span class="chip {TONE[v]}">{esc(VERDICT[v])}</span>'


def lead_data(L: dict) -> dict:
    k, no, g, d, title, answer, v, tools, tk = BY_KEY[L["key"]]
    label, ltitle, ltext = LESSON[k]
    return dict(L, no=no, disc=DISC[g], title=title, verdict=v, tools=tools, url=page(k), setup=f"../v2/tc_{k}.webp",
                question=QUESTION[k], caught=ltitle, caught_text=ltext)


def need_tags() -> str:
    return "".join(f'<span class="need">{esc(n)}</span>' for n in NEED)


# ---------------------------------------------------------------- version A: the ledger
def a_rows() -> str:
    rows = []
    for k, no, g, d, title, answer, v, tools, tk in GALLERY:
        rows.append(
            f'<tr data-g="{g}" data-t="{TONE[v]}">'
            f'<td class="c-part"><a class="part" href="{page(k)}"><img src="../v2/tc_{k}.webp" alt="" loading="lazy">'
            f'<span><i>{esc(no)}</i><b>{esc(title)}</b><em>{esc(QUESTION[k])}</em></span></a></td>'
            f'<td class="c-verdict">{chip(v)}</td>'
            f'<td class="c-find">{esc(first_part(answer))}</td>'
            f'<td class="c-tools">{esc(tools)}</td></tr>')
    return "\n".join(rows)


def a_leads() -> str:
    out = []
    for L in map(lead_data, LEAD):
        out.append(
            f'<a class="lead" href="{L["url"]}"><img src="{L["setup"]}" alt="">'
            f'<p class="tag">{esc(L["disc"])} · study {esc(L["no"])}</p>'
            f'<p class="big"><b>{esc(L["number"])}</b><span>{esc(L["unit"])}</span></p>'
            f'<p class="say">{esc(L["line"])}</p>{chip(L["verdict"])}</a>')
    return "\n".join(out)


def filters(tag: str = "button") -> str:
    used = [g for g in DISC if any(c[2] == g for c in GALLERY)]
    return ('<button type="button" aria-pressed="true" data-f="all">All</button>'
            + "".join(f'<button type="button" aria-pressed="false" data-f="{g}">{esc(DISC[g])}</button>' for g in used))


def lessons_list(n: int) -> str:
    return "\n".join(f'<li><a href="{study_url(k)}"><i>{esc(label)}</i><b>{esc(title)}</b></a><span>{text}</span></li>'
                     for label, title, text, k in LESSONS[:n])


def steps_list() -> str:
    return "\n".join(f"<li><b>{esc(a)}</b><span>{b}</span></li>" for a, b in STEPS)


def services() -> str:
    return "\n".join(f"<li><b>{esc(a)}</b><span>{esc(b)}</span></li>" for a, b in SERVICES)


def memo_block() -> str:
    return (f'<p class="m-h">Technical memo</p><h4>{esc(MEMO["title"].split(": ", 1)[1])}</h4>'
            f'<dl><dt>Subject</dt><dd>{esc(MEMO["subject"])}</dd><dt>Status</dt><dd>{esc(MEMO["status"])}</dd></dl>'
            f'<p class="m-lead">{md(MEMO["lead"])}</p><ul>' + "".join(f"<li>{md(b)}</li>" for b in MEMO["bullets"]) + "</ul>")


# ---------------------------------------------------------------- version B: the showcase
def b_leads() -> str:
    out = []
    for i, L in enumerate(map(lead_data, LEAD)):
        res = (f'<figure class="res plate"><img src="{L["result"]}" alt=""></figure>' if L["plate"]
               else f'<figure class="res"><img src="{L["result"]}" alt=""></figure>')
        out.append(
            f'<article class="case{" flip" if i % 2 else ""}">'
            f'<div class="case-text"><p class="tag">{i + 1:02d} · {esc(L["disc"])}</p>'
            f'<h3>{esc(L["title"])}</h3>'
            f'<p class="q">{esc(L["question"])}</p>'
            f'<p class="big"><b>{esc(L["number"])}</b><span>{esc(L["unit"])}</span></p>'
            f'<p class="say">{esc(L["line"])}</p>'
            f'<p class="caught"><i>What the checks caught</i>{esc(L["caught"])}</p>'
            f'<p class="go">{chip(L["verdict"])}<a href="{L["url"]}">Read the study →</a></p></div>'
            f'<div class="pair"><figure class="set"><img src="{L["setup"]}" alt=""><figcaption>The part</figcaption></figure>'
            f'{res.replace("</figure>", "<figcaption>The answer</figcaption></figure>")}</div></article>')
    return "\n".join(out)


def b_range() -> str:
    out = []
    for g, name in DISC.items():
        items = [(kind(c[3]), c[0]) for c in CARDS if c[2] == g]
        if not items:
            continue
        if len(items) == 1:               # one study: its kind only repeats the heading, so name the study
            items = [(next(c[4] for c in CARDS if c[0] == items[0][1]).split(",")[0].split(":")[0], items[0][1])]
        tags = "".join(f'<a href="{study_url(k)}">{esc(d)}</a>' for d, k in dict((d, k) for d, k in items).items())
        out.append(f'<div class="rg"><p><b>{len(items)}</b><span>{esc(name)}</span></p><div>{tags}</div></div>')
    return "\n".join(out)


def b_dots() -> str:
    cls = ["ok"] * MET + ["bad"] * NOT + ["warn"] * (HELD + OTHER)
    return "".join(f'<i class="{c}"></i>' for c in cls)


def b_cards() -> str:
    out = []
    for k, no, g, d, title, answer, v, tools, tk in GALLERY:
        out.append(
            f'<a class="card" href="{page(k)}" data-g="{g}">'
            f'<span class="duo"><img src="../v2/tc_{k}.webp" alt="" loading="lazy"><img src="../v2/th_{tk}.webp" alt="" loading="lazy"></span>'
            f'<span class="meta">{esc(no)} · {esc(kind(d))}</span><b>{esc(title)}</b>'
            f'<em>{esc(first_part(answer, 50))}</em>{chip(v)}</a>')
    return "\n".join(out)


FILL = {
    "{{STUDIES}}": STATS["studies"], "{{CHECKS}}": STATS["automated checks"], "{{RUNS}}": STATS["saved runs"],
    "{{PARTS}}": str(len(GALLERY)), "{{REQ_N}}": str(REQ_N), "{{MET}}": str(MET), "{{NOT}}": str(NOT),
    "{{HELD}}": str(HELD + OTHER), "{{CAUGHT_N}}": str(len(LESSONS)), "{{MEMO_URL}}": MEMO["url"],
    "{{FAILS}}": str(sum(TONE[g[6]] == "bad" for g in GALLERY)),
    "{{A_ROWS}}": a_rows(), "{{A_LEADS}}": a_leads(), "{{FILTERS}}": filters(), "{{LESSONS4}}": lessons_list(4),
    "{{LESSONS6}}": lessons_list(6), "{{STEPS}}": steps_list(), "{{SERVICES}}": services(), "{{MEMO}}": memo_block(),
    "{{NEED}}": need_tags(), "{{B_LEADS}}": b_leads(), "{{B_RANGE}}": b_range(), "{{B_DOTS}}": b_dots(),
    "{{B_CARDS}}": b_cards(),
}

for name in ("a", "b"):
    out = (HERE / f"{name}.tpl.html").read_text(encoding="utf-8")
    for key, val in FILL.items():
        out = out.replace(key, val)
    left = re.findall(r"\{\{[A-Z0-9_]+\}\}", out)
    assert not left, left
    (HERE / f"{name}.html").write_text(out, encoding="utf-8", newline="\n")
    print(f"wrote {name}.html  ({len(out) // 1024} kB)")
print(f"{len(GALLERY)} cards, {STATS['studies']} studies, {REQ_N} requirements: {MET} met, {NOT} not met, {HELD + OTHER} other")
