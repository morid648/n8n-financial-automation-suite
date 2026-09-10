# Automated Accounts Receivable

> Cross-cutting findings live in [`../../docs/PRD.md`](../../docs/PRD.md) Section 3 — this README links back rather than repeating them.

## Overview

Gmail-triggered workflow. Parses inbound invoice emails, extracts structured invoice data, generates a PDF record, and updates the ledger. The ledger feeds DCF inputs, so a validation step must catch extraction errors before they land.

**Trigger:** Gmail · **Primary risk:** Medium (financial data accuracy)

## Tech stack

- n8n
- Google Gemini (`Gemini_Inference_Engine` → `Quantitative_Data_Parser`)
- APITemplate.io (PDF generation)
- Gmail, Google Sheets (`Master_Ledger_Update`)

## Node reference

_TBD — populate from `Automated_Accounts_Receivable.json`._

## Required credentials

- Gemini API key
- APITemplate.io API key
- Gmail OAuth
- Google Sheets OAuth

## Known gaps

- `Gemini_Inference_Engine` has zero connections — not wired to `Quantitative_Data_Parser` (PRD 3.8).
- Extraction schema (invoice number, vendor, amount, due date, currency) not defined.
- No validation step before `Master_Ledger_Update`.
- `Gmail_Operations` purpose undocumented (acknowledge? forward to AP?).
- No audit-log row per ledger write (PRD Section 4).

## Setup steps

1. Import `Automated_Accounts_Receivable.json`.
2. Add all credentials above (no inline keys).
3. Wire `Gemini_Inference_Engine` via `ai_languageModel` per the checklist.
4. Add the T1.6 extraction schema + validation node + audit-log write.
5. Test against 5–10 sample invoice emails, including one with a missing amount.
