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

`Ingest_Inbox_Stream (gmailTrigger) → Workflow_Config → Enabled_Gate → Quantitative_Data_Parser → Pre_Ledger_Validation → Valid_Invoice (IF)`:
- **valid** → `Generate_PDF_Record → Gmail_Operations → Master_Ledger_Update → Audit_Log_Write`
- **invalid** → `Flag_Needs_Review (Gmail label AR/needs-review) → Audit_Log_Skip`
- parser `onError` → `Error_Context → Error_Audit_Write`

`Gemini_Inference_Engine` is wired to `Quantitative_Data_Parser` via `ai_languageModel` (**PRD 3.8 fix**). `Pre_Ledger_Validation` enforces the T1.6 rules (amount present/positive/≤cap, ISO currency in allowlist, parseable due date, confidence ≥ 0.7). `Gmail_Operations` = ack reply (T1.7).

## Required credentials

- Gemini API key
- APITemplate.io API key
- Gmail OAuth
- Google Sheets OAuth

## Known gaps

- PRD 3.8 **fixed**; T1.6 validation + T1.7 `Gmail_Operations` + audit rows all in the current JSON.
- `Generate_PDF_Record` uses a generic `apiTemplateIo` param shape — set the real template ID on import.
- The `AR/needs-review` Gmail label ID (`Label_AR_needs_review`) is a placeholder; replace with the real label ID.
- Not yet run end-to-end (Phase 6).

## Setup steps

1. Import `Automated_Accounts_Receivable.json`.
2. Replace `REPLACE_*` credential IDs (two Gmail creds: `Gmail (AR read)` read-only, `Gmail (AR send/label)` for reply+label), `REPLACE_SHEET_ID`, the APITemplate template ID, and the needs-review label ID.
3. Create ledger tabs `accounts_receivable` + `audit_log`.
4. Test against 5–10 sample invoice emails **including one with a missing amount** — confirm it routes to needs-review, not the ledger.
