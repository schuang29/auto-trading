# Compliance Source Documents

This directory holds the authoritative firm policy documents that govern the bot's trading universe. Store the PDFs here so the repo always contains the source material — not just our interpretation of it.

## Current documents

| File | Source | Date | Covers |
|------|--------|------|--------|
| FIRMWIDE_ANNEX__PERSONAL_TRADING_POLICY_APPENDIX_2_AND_3_FINAL_31-Mar-2026__v2_1_.pdf | Firm Personal Trading Policy | 2026-03-31 | Appendix 2 (approved ETFs) and Appendix 3 (removed ETFs) |

## When a new version is published

1. Save the new PDF here alongside the old one — never delete old versions. They are the historical record.
2. Diff the approved list against `strategy/appendix_2_approved.json`. Note tickers added, removed, changed.
3. Update `strategy/appendix_2_approved.json` with the new list.
4. Update `guardrails/restricted.md` with any new Appendix 3 removals.
5. Update the `last_updated` and `source` fields in the JSON.
6. Note the update in `docs/compliance.md`.
7. Commit with message `compliance: update to Personal Trading Policy v[X.Y]`.

## Why the PDF is committed

Committing the source PDF (not just our derived JSON) means any reviewer — compliance, audit, future you — can always verify that our JSON matches the firm's policy. The PDF is the contract; the JSON is the implementation.

**Note**: These PDFs are not user-secret but they are firm-internal. The repo is private and access should be restricted accordingly.
