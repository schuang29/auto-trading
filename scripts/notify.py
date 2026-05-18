"""
Minimal SMTP notifier for bot reliability alerts.

Used by the heartbeat dead-man's-switch and the wrappers' git push-verify step
to reach the operator when a routine goes dark or an audit-trail push fails.

This is NOT a general notification framework (that is deferred to Phase 5). It
does one thing: send a plain-text email via the SMTP_* settings in .env. It
NEVER raises — the caller always has the guaranteed local-file + non-zero-exit
fallback, so a notifier failure must not mask the underlying alert.

Exit codes:
  0  email sent
  2  SMTP not configured (expected until the user fills in .env) — not an error
  1  SMTP configured but the send failed

CLI:
  python scripts/notify.py --subject "..." --body "..."
  echo "body text" | python scripts/notify.py --subject "..."   # body from stdin
"""
from __future__ import annotations

import argparse
import smtplib
import ssl
import sys
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"


def load_env(env_file: Path | None = None) -> dict[str, str]:
    """Parse KEY=VALUE lines from .env, mirroring the wrapper scripts.

    Returns only the keys found in the file; callers fall back to os.environ
    for values already injected into the process (the scheduled path).

    `ENV_FILE` is resolved at call time (not bound as a default argument) so
    tests can redirect it via monkeypatch and never touch the real .env / send
    a real email.
    """
    if env_file is None:
        env_file = ENV_FILE
    values: dict[str, str] = {}
    if not env_file.exists():
        return values
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        eq = line.find("=")
        if eq <= 0:
            continue
        values[line[:eq].strip()] = line[eq + 1 :].strip()
    return values


def _cfg(key: str, env: dict[str, str], default: str = "") -> str:
    import os

    # Process env wins (scheduled wrappers inject .env into the environment);
    # fall back to parsing the file directly for standalone invocation.
    return os.environ.get(key) or env.get(key, default)


def send(subject: str, body: str) -> int:
    env = load_env()
    host = _cfg("SMTP_HOST", env)
    user = _cfg("SMTP_USER", env)
    password = _cfg("SMTP_PASS", env)
    to_addr = _cfg("NOTIFY_EMAIL_TO", env)
    port = int(_cfg("SMTP_PORT", env, "587") or "587")

    if not (host and user and password and to_addr):
        sys.stderr.write(
            "notify: SMTP not configured (SMTP_HOST/SMTP_USER/SMTP_PASS/"
            "NOTIFY_EMAIL_TO) — skipping email; rely on local+git fallback.\n"
        )
        return 2

    msg = EmailMessage()
    msg["Subject"] = f"[auto-trading] {subject}"
    msg["From"] = user
    msg["To"] = to_addr
    msg.set_content(body)

    try:
        if port == 465:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, context=ctx, timeout=30) as s:
                s.login(user, password)
                s.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=30) as s:
                s.starttls(context=ssl.create_default_context())
                s.login(user, password)
                s.send_message(msg)
    except Exception as exc:  # noqa: BLE001 — never raise; the alert must survive
        sys.stderr.write(f"notify: SMTP send failed: {exc!r}\n")
        return 1

    sys.stderr.write(f"notify: email sent to {to_addr}\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Send a bot reliability alert email.")
    p.add_argument("--subject", required=True)
    p.add_argument("--body", default=None, help="Body text; if omitted, read stdin.")
    args = p.parse_args(argv)
    body = args.body if args.body is not None else sys.stdin.read()
    return send(args.subject, body)


if __name__ == "__main__":
    raise SystemExit(main())
