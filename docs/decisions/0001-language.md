# ADR-0001: Python over TypeScript

Date: 2026-04-19
Status: Accepted

## Context

The bot needs to interact with the Alpaca trading API, pull market data, run scheduled routines, and send notifications. Both Python and TypeScript are viable general-purpose languages. A choice needed to be made before writing any production code.

## Decision

**Python.**

## Consequences

**Why Python wins:**
- `alpaca-py` is the official, first-party Alpaca SDK — actively maintained by Alpaca Markets. The TypeScript equivalent (`alpaca-trade-api-node`) is community-maintained and less complete.
- The entire quantitative finance data stack is Python-native: `pandas`, `yfinance`, `numpy`, `scipy`. Pulling, transforming, and analyzing market data is dramatically simpler.
- Scheduling (`APScheduler`), notifications (`smtplib`, `slack_sdk`), and environment management (`python-dotenv`) are all mature Python libraries with no real TypeScript equivalents.
- Python 3.11 is already installed on the development machine (confirmed in Phase 0).

**What we give up:**
- TypeScript's static typing catches certain bugs at compile time. Mitigated by using type hints throughout Python code and running `mypy` in CI.
- TypeScript is arguably more natural for anyone whose background is web development. Not a factor here.

**Runtime version:** Python 3.11.0
**Package manager:** pip + venv (simple; Poetry is an option later if dependency complexity grows)
