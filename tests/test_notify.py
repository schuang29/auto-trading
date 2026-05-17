"""
Tests for scripts/notify.py — focus on graceful degradation. The notifier must
NEVER raise and must return exit 2 (not an error) when SMTP is unconfigured,
because the caller relies on the local-file + non-zero-exit fallback and a
notifier exception would mask the underlying alert.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import notify  # noqa: E402

SMTP_VARS = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS",
             "NOTIFY_EMAIL_TO"]


def test_load_env_parses_kv_and_skips_comments(tmp_path):
    env = tmp_path / ".env"
    env.write_text(
        "# a comment\n\nSMTP_HOST=smtp.example.com\n"
        "GITHUB_TOKEN=abc=def\n",  # value containing '='
        encoding="utf-8",
    )
    parsed = notify.load_env(env)
    assert parsed["SMTP_HOST"] == "smtp.example.com"
    assert parsed["GITHUB_TOKEN"] == "abc=def"
    assert "# a comment" not in parsed


def test_send_returns_2_and_does_not_raise_when_unconfigured(
    tmp_path, monkeypatch
):
    for v in SMTP_VARS:
        monkeypatch.delenv(v, raising=False)
    # Point the module's .env at an empty file so nothing is configured.
    monkeypatch.setattr(notify, "ENV_FILE", tmp_path / "absent.env")
    rc = notify.send("test subject", "test body")
    assert rc == 2  # "not configured" — explicitly not a failure


def test_main_reads_body_from_arg(tmp_path, monkeypatch):
    for v in SMTP_VARS:
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setattr(notify, "ENV_FILE", tmp_path / "absent.env")
    rc = notify.main(["--subject", "s", "--body", "b"])
    assert rc == 2
