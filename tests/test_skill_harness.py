"""The skills in .claude/skills/ stay in step with the code: the mechanical half of the CLAUDE.md rule
"Keep the skills current" (the judgement half, what to add, refine or prune, is the agent's)."""

import re
from pathlib import Path

import pytest

from harness.registry import _studies

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / ".claude" / "skills"
SKILL_FILES = sorted(SKILLS.glob("*/SKILL.md"))


def _first_column(table_text: str) -> list[str]:
    return [row.split("|")[1] for row in table_text.splitlines() if row.startswith("| ") and not row.startswith("|---")]


def test_every_registered_model_is_in_the_run_case_table():
    text = (SKILLS / "run-case" / "SKILL.md").read_text(encoding="utf-8")
    listed = set(re.findall(r"^\| `([^`]+)` \|", text, flags=re.M))
    registered = {m for s in _studies() for m in s.models}
    assert not registered - listed, f"add rows to run-case/SKILL.md for {sorted(registered - listed)}"
    assert not listed - registered, f"run-case/SKILL.md lists unregistered models {sorted(listed - registered)}"


def test_every_study_is_in_the_verification_table():
    text = (SKILLS / "verify-against-reference" / "SKILL.md").read_text(encoding="utf-8")
    named = {n for cell in _first_column(text) for n in re.findall(r"`([a-z0-9_]+)`", cell)}
    studies = {s.name for s in _studies()}
    assert not studies - named, f"add rows to verify-against-reference/SKILL.md for {sorted(studies - named)}"


@pytest.mark.parametrize("skill", SKILL_FILES, ids=lambda p: p.parent.name)
def test_skill_file_is_lean_and_described(skill):
    text = skill.read_text(encoding="utf-8")
    assert len(text.splitlines()) < 500, "Anthropic's guidance: SKILL.md under 500 lines; move detail to references/"
    front = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    assert front, "SKILL.md needs YAML frontmatter"
    assert re.search(rf"^name: {re.escape(skill.parent.name)}$", front.group(1), flags=re.M)
    assert re.search(r"^description: \S", front.group(1), flags=re.M)


@pytest.mark.parametrize("doc", sorted(SKILLS.glob("*/**/*.md")), ids=lambda p: str(p.relative_to(SKILLS)))
def test_relative_links_resolve(doc):
    text = doc.read_text(encoding="utf-8")
    for target in re.findall(r"\]\(([^)#\s]+)", text):
        if re.match(r"[a-z]+:", target):
            continue
        assert (doc.parent / target).exists(), f"dead link {target!r} in {doc.relative_to(ROOT)}"
