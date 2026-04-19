# Autonomous ETF Trading Bot

An autonomous, scheduled research-and-trading agent powered by Claude Code.

- **Paper trades** on Alpaca (ETF-only, employer-compliant)
- **Signals** manual execution in Fidelity (real money stays with the human)
- **Five scheduled routines**: pre-market, market open, midday, EOD, weekly
- **Markdown-first**: strategy rules and memory logs are plain English, auditable by compliance

See `PLAN.md` for the full project plan and `CLAUDE.md` for Claude Code operating instructions.

## Quick start

```bash
# 1. Clone and enter the repo
git clone <repo-url>
cd auto-trading

# 2. Create your .env from the template
cp .env.example .env
# Edit .env — add your Alpaca paper API key and secret

# 3. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Verify Alpaca connection
python scripts/hello_alpaca.py
```

## Project structure

```
strategy/      ETF universe, regime rules, thesis (markdown)
guardrails/    Hard limits, restricted list, blackouts (markdown + code)
routines/      Five scheduled routine prompts (markdown)
skills/        Reusable code: alpaca, market_data, notifications, memory
memory/        Append-only audit trail: decisions, daily logs, positions
docs/          Compliance notes, ADRs, runbook
tests/         Guardrail and routine tests
```

## Status

Phase 0 — Environment setup in progress. See `PLAN.md §6` for the full milestone map.
