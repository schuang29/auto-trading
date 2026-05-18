"""
PowerShell script validator for this repo's operational scripts.

WHY THIS EXISTS: every .ps1 here runs under Windows Task Scheduler via
`powershell.exe -File`. Windows PowerShell 5.1 decodes a no-BOM script using
the ANSI code page, so a non-ASCII character (em-dash, box-drawing, smart
quote) inside a string literal desyncs the tokenizer and the whole script
fails to parse. On 2026-05-17 this nearly shipped a regression that would have
re-caused a multi-day silent outage (and broke the heartbeat that was supposed
to catch it). The rule is therefore simple and absolute: **.ps1 files are
ASCII-only.**

Usage:
  python scripts/check_ps1.py FILE [FILE ...]          # ASCII check (fast)
  python scripts/check_ps1.py --full FILE [FILE ...]    # + powershell.exe parse

Exit code 0 = all clean; non-zero = at least one problem (details on stderr).
The `scan_non_ascii` function is imported by the PostToolUse hook
(scripts/hooks/ps1_guard.py) so the ASCII rule has a single source of truth.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def scan_non_ascii(path: Path) -> list[tuple[int, int, str]]:
    """Return [(line, col, char), ...] for every non-ASCII char in `path`.
    Empty list means the file is pure ASCII (the required state)."""
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    hits: list[tuple[int, int, str]] = []
    line = col = 1
    for ch in text:
        if ch == "\n":
            line += 1
            col = 1
            continue
        if ord(ch) > 127:
            hits.append((line, col, ch))
        col += 1
    return hits


def parse_with_powershell(path: Path) -> list[str]:
    """Parse `path` with the real powershell.exe (Task Scheduler's launcher).
    Returns a list of parse-error messages ([] = clean). If powershell.exe is
    unavailable, returns [] (best-effort — the ASCII check is the hard gate)."""
    pwsh = shutil.which("powershell.exe") or shutil.which("powershell")
    if not pwsh:
        return []
    ps = (
        "$e=$null;"
        f"[System.Management.Automation.Language.Parser]::ParseFile('{path}',"
        "[ref]$null,[ref]$e)|Out-Null;"
        "if($e){$e|ForEach-Object{$_.Message}}"
    )
    try:
        res = subprocess.run(
            [pwsh, "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, timeout=60,
        )
    except Exception as exc:  # noqa: BLE001 — best-effort
        return [f"(could not run powershell.exe: {exc!r})"]
    out = (res.stdout or "").strip()
    return [ln for ln in out.splitlines() if ln.strip()]


def check_file(path: Path, full: bool) -> list[str]:
    problems: list[str] = []
    hits = scan_non_ascii(path)
    if hits:
        shown = ", ".join(f"L{ln}:C{c} {ch!r}" for ln, c, ch in hits[:8])
        more = "" if len(hits) <= 8 else f" (+{len(hits) - 8} more)"
        problems.append(f"non-ASCII char(s): {shown}{more}")
    if full:
        for msg in parse_with_powershell(path):
            problems.append(f"powershell parse: {msg}")
    return problems


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    full = "--full" in args
    files = [a for a in args if a != "--full"]
    if not files:
        sys.stderr.write("usage: check_ps1.py [--full] FILE [FILE ...]\n")
        return 2
    failed = False
    for f in files:
        p = Path(f)
        if not p.exists():
            sys.stderr.write(f"[FAIL] {f}: not found\n")
            failed = True
            continue
        problems = check_file(p, full)
        if problems:
            failed = True
            sys.stderr.write(f"[FAIL] {f}\n")
            for pr in problems:
                sys.stderr.write(f"        - {pr}\n")
        else:
            sys.stdout.write(f"[OK]   {f}\n")
    if failed:
        sys.stderr.write(
            "\n.ps1 files MUST be pure ASCII (Task Scheduler runs them via "
            "powershell.exe -File; Windows PS 5.1 ANSI-decodes no-BOM files). "
            "Replace em-dashes/box-art/smart quotes with ASCII.\n"
        )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
