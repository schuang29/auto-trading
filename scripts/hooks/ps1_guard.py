"""
PostToolUse hook: reject non-ASCII written into any .ps1.

Wired in .claude/settings.json on Write|Edit|MultiEdit. Reads the hook JSON
from stdin, and if the edited file is a .ps1 containing non-ASCII characters,
exits 2 so the message is fed straight back to the model to fix immediately --
turning a silent, latent "Task Scheduler can't parse this" failure into an
instant, visible one. See scripts/check_ps1.py for the rationale.

Design: FAIL-OPEN. Any guard-internal error exits 0 (never wedge the workflow
over a bug in the guard). It exits non-zero ONLY on a definitive violation:
a .ps1 that actually contains non-ASCII bytes.
"""
import json
import sys
from pathlib import Path

# Single source of truth for the ASCII rule.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0  # not parseable -> not our problem; fail open

    tool_input = data.get("tool_input") or {}
    fp = tool_input.get("file_path") or tool_input.get("path")
    if not fp or not str(fp).lower().endswith(".ps1"):
        return 0

    path = Path(fp)
    if not path.exists():
        return 0

    try:
        from check_ps1 import scan_non_ascii

        hits = scan_non_ascii(path)
    except Exception:
        return 0  # guard bug must not block the user

    if not hits:
        return 0

    shown = ", ".join(f"L{ln}:C{c} {ch!r}" for ln, c, ch in hits[:8])
    more = "" if len(hits) <= 8 else f" (+{len(hits) - 8} more)"
    sys.stderr.write(
        f"BLOCKED: {path.name} now contains non-ASCII [{shown}{more}].\n"
        ".ps1 files in this repo MUST be pure ASCII -- Task Scheduler runs "
        "them via `powershell.exe -File` and Windows PowerShell 5.1 "
        "ANSI-decodes no-BOM files, so an em-dash/box-art/smart-quote in a "
        "string literal silently breaks the whole script (this nearly "
        "shipped a multi-day outage on 2026-05-17). Replace the flagged "
        "characters with ASCII equivalents (-- - ' \" ...).\n"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
