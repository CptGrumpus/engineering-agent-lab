"""Keep personal paths out of committed evidence.

Run records and solver logs naturally contain absolute paths: the Python executable, the
FreeCAD install, the temporary OpenFOAM case seen from WSL. Those paths carry the Windows user
name. `redact` replaces the repository root with "<repo>" and the user's home folder with "~",
in every spelling they appear in (backslashes, JSON-escaped backslashes, forward slashes, and
the WSL /mnt/c view). Only the path prefix changes; numbers and results are untouched.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOME = Path.home()

# Committed files must not contain an absolute path under any user's home folder.
# Used by the repository test, so it is deliberately generic rather than tied to this machine.
LEAK = re.compile(r"(?i)(\b[a-z]:(\\\\|\\|/)+users(\\\\|\\|/)+[^\\/\s\"'<>~]+|/mnt/[a-z]/users/[^/\s\"'<>~]+|/home/[^/\s\"'<>~]+)")

TEXT_SUFFIXES = {".json", ".md", ".log", ".txt", ".mos", ".csv", ".toml", ".inp", ".geo", ".sh", ".py", ""}


def _spellings(p: Path) -> list[str]:
    """Regex alternatives for one absolute Windows path in all the forms it gets written."""
    if not p.drive:                                         # POSIX (CI runners): one spelling
        return [re.escape(p.as_posix())]
    drive, rest = p.drive.rstrip(":"), [part for part in p.parts[1:]]
    out = []
    # escaped twice (an exception message stored in JSON), JSON-escaped, Windows, forward slash
    for sep in (r"\\\\\\\\", r"\\\\", r"\\", "/"):
        out.append(re.escape(drive) + ":" + sep + sep.join(re.escape(x) for x in rest))
    out.append("/mnt/" + re.escape(drive.lower()) + "/" + "/".join(re.escape(x) for x in rest))
    return out


def _pattern(p: Path) -> re.Pattern:
    return re.compile("(?i)(" + "|".join(_spellings(p)) + ")")


_REPO_RE = _pattern(REPO)
_HOME_RE = _pattern(HOME)


def redact(text: str) -> str:
    """Replace the repository root with <repo> and the home folder with ~."""
    return _HOME_RE.sub("~", _REPO_RE.sub("<repo>", text))


def scrub_tree(root: Path) -> dict:
    """Redact every text file under root in place and delete __pycache__ folders.

    Returns counts so the caller can report what changed."""
    changed, pycache = 0, 0
    for d in sorted(root.rglob("__pycache__"), reverse=True):
        if d.is_dir():
            shutil.rmtree(d)
            pycache += 1
    for f in root.rglob("*"):
        if not f.is_file() or (f.suffix.lower() not in TEXT_SUFFIXES and not f.name.startswith("log.")):
            continue
        raw = f.read_bytes()
        if b"\0" in raw:
            continue                                        # binary
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        new = redact(text)
        if new != text:
            f.write_bytes(new.encode("utf-8"))
            changed += 1
    return {"files_redacted": changed, "pycache_removed": pycache}
