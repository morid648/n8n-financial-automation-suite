# Corporate Comms Triage

> Cross-cutting findings live in [`../../docs/PRD.md`](../../docs/PRD.md) Section 3 — this README links back rather than repeating them.

## Overview

Gmail-triggered workflow. Classifies inbound mail into a closed taxonomy (billing, project update, spam, other) and routes only genuinely critical categories to a Telegram executive alert.

**Trigger:** Gmail · **Primary risk:** Low–Medium (alert fatigue if untuned)

## Tech stack

- n8n
- Google Gemini (`Gemini_Inference_Engine` → `NLP_Text_Classifier` / `LLM_Execution_Chain`)
- Gmail, Telegram

## Node reference

`Ingest_Inbox_Stream (gmailTrigger) → Workflow_Config → Enabled_Gate → NLP_Text_Classifier`. The classifier has one output per category (closed set, T1.8):
- **billing** (output 0, critical) → `LLM_Execution_Chain` → `Telegram_Executive_Alert` → `Classification_Audit`
- **project_update / spam / other** (outputs 1–3) → `NonCritical_Log_Sink (noOp)` → `Classification_Audit`
- classifier / chain `onError` → `Error_Context → Error_Audit_Write`

`Gemini_Inference_Engine` is wired via `ai_languageModel` to **both** `NLP_Text_Classifier` and `LLM_Execution_Chain` (**PRD 3.8 fix**). Category branching (**PRD 3.6 fix**) means only `billing` reaches Telegram.

## Required credentials

- Gemini API key
- Gmail OAuth
- Telegram bot token + chat ID

## Known gaps

- PRD 3.6 + 3.8 **fixed**; closed taxonomy + error branches in the current JSON.
- `critical_categories` in `Workflow_Config` is currently just `billing` (T1.8 assumption — widen if needed). The branch wiring routes output 0 to the alert; if you add categories, re-check output order.
- Not yet run end-to-end (Phase 6).

## Setup steps

1. Import `Corporate_Comms_Triage.json`.
2. Replace `REPLACE_*` — Gemini cred, Gmail read cred, Telegram bot cred + `REPLACE_TELEGRAM_CHAT_ID`, `REPLACE_SHEET_ID`.
3. Create the `audit_log` ledger tab.
4. Test with a 5–10 message sample spanning every category; confirm only `billing` produces a Telegram alert **before** enabling live alerting (T6.4).
