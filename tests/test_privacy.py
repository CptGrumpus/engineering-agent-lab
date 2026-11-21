"""Committed files must not carry personal paths (the Windows user name in absolute paths)."""

import subprocess
from pathlib import Path

from harness.privacy import LEAK, REPO, redact


def test_redact_handles_every_spelling():
    home = Path.home()
    repo = REPO
    win = str(repo / "runs" / "x")
    samples = [
        win,                                              # C:\Users\name\...
        win.replace("\\", "\\\\"),                        # JSON-escaped
        win.replace("\\", "/"),                           # forward slashes
        "/mnt/" + repo.drive[0].lower() + "/" + "/".join(repo.parts[1:]) + "/runs/x",   # WSL view
        str(home / "AppData" / "Local" / "Temp" / "case"),
    ]
    for s in samples:
        out = redact(s)
        assert not LEAK.search(out), (s, out)
        assert out.startswith(("<repo>", "~")), out
    assert redact("tip deflection 0.953 mm") == "tip deflection 0.953 mm"


def test_no_committed_file_contains_a_personal_path():
    files = subprocess.run(["git", "ls-files", "-z"], cwd=REPO, capture_output=True, check=True).stdout.split(b"\0")
    leaks = []
    for name in filter(None, files):
        path = REPO / name.decode()
        if not path.is_file():
            continue
        raw = path.read_bytes()
        if b"\0" in raw:
            leaks.append(f"{name.decode()} (binary file committed)") if name.endswith(b".pyc") else None
            continue
        m = LEAK.search(raw.decode("utf-8", "ignore"))
        if m:
            leaks.append(f"{name.decode()}: {m.group(0)}")
    assert not leaks, "personal paths in committed files (run scripts/scrub_paths.py):\n" + "\n".join(leaks[:20])
