"""
Memory logger. Appends structured entries to memory/daily/ markdown files.

Usage:
    python skills/memory/logger.py --type daily --content "Regime: RISK-ON ..."
    python skills/memory/logger.py --type regime --regime RISK-ON --signals "..."
"""
import argparse
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
ET = ZoneInfo("America/New_York")


def append_daily(content: str) -> Path:
    today = date.today().isoformat()
    path = ROOT / "memory" / "daily" / f"{today}.md"
    timestamp = datetime.now(ET).strftime("%H:%M ET")

    if not path.exists():
        path.write_text(f"# Daily Log — {today}\n\n", encoding="utf-8")

    with path.open("a", encoding="utf-8") as f:
        f.write(f"\n## {timestamp}\n\n{content}\n")

    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", required=True, choices=["daily"])
    parser.add_argument("--content", required=True)
    args = parser.parse_args()

    if args.type == "daily":
        path = append_daily(args.content)
        print(f"Logged to {path}")
