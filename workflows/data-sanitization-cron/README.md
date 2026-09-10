# Data Sanitization Cron

> ⚠️ Highest-priority fix in the portfolio. Cross-cutting findings live in [`../../docs/PRD.md`](../../docs/PRD.md) Section 3 (esp. 3.7) — this README links back rather than repeating them.

## Overview

Schedule-triggered workflow that deletes scam/junk emails from a mailbox. As exported it deletes **before** it alerts — no review step, dry-run, or undo. Both a dry-run phase and a human approval gate are **blocking** requirements before this runs against real data.

**Trigger:** Schedule (cron) · **Primary risk:** HIGH (irreversible delete)

## What "flagged" means (decided 2026-09-11, T1.2)

An LLM **classifier decides**. Each cron run:

1. `Gmail_Fetch_Candidates` pulls recent unread mail from a broad pre-filter (e.g. `in:inbox newer_than:7d -in:important`) — read-only.
2. `Scam_Classifier` (Gemini) scores each message → `{ verdict: "scam"|"junk"|"legit", confidence: 0..1, reason }` (closed set, structured output).
3. Deletion candidate = `verdict ∈ {scam, junk}` **AND** `confidence >= 0.9` (tunable via the Config node).
4. Everything else is left untouched and logged as `outcome: "skipped"`.

Because the basis for an irreversible action is a model judgment, the safeguards below are mandatory, not optional.

## Safeguards (decided 2026-09-11, T1.3 — BOTH)

| Phase | Mechanism |
|---|---|
| First `DRY_RUN_UNTIL` runs (Config node, default 10) | `dry_run = true`: candidates are written to the audit log with `action: "dry_run_candidate"`; `Gmail_Delete_Op` is skipped entirely. Operator reviews the log to confirm the classifier's precision. |
| After dry-run | `dry_run = false`: each run sends a Telegram message listing every candidate (sender, subject, date, classifier `reason`, `confidence`) with **Approve** / **Deny** buttons. `Gmail_Delete_Op` runs only for approved message IDs. Deny → logged `outcome: "denied"`, nothing deleted. No response within `APPROVAL_TIMEOUT` (default 6h) → treated as deny. |

Kill switch: `Config.enabled = false` halts the workflow.

## Tech stack

- n8n
- Google Gemini (`Scam_Classifier`)
- Gmail (fetch = read-only cred; delete = separate cred, `https://mail.google.com/`)
- Telegram (approval + notification)
- Audit sink (Google Sheet `audit_log` / table) — schema in [`../../docs/SCHEMAS.md`](../../docs/SCHEMAS.md) T1.12

## Node reference

Implemented in `Data_Sanitization_Cron.json`:
```
Chron_Scheduler → Workflow_Config → Enabled_Gate → Gmail_Fetch_Candidates (READ-ONLY cred)
   → Scam_Classifier (informationExtractor, Gemini via ai_languageModel) ──onError──► Error_Context → Error_Audit_Write
   → Attach_Message_Id → Deletion_Candidate_Filter (verdict≠legit AND confidence ≥ min_confidence)
   → Dry_Run_Gate (IF Workflow_Config.dry_run)
        ├─ true  → Audit_DryRun_Candidate            (nothing deleted)
        └─ false → Aggregate_Candidates → Format_Approval_Message
                   → Telegram_Approval_Gate (sendAndWait, Approve/Deny, timeout→deny)
                   → Was_Approved (IF)
                        ├─ approved → Split_Approved → Gmail_Delete_Op (DELETE cred) → Audit_Delete → Telegram_Run_Summary
                        └─ denied   → Audit_Denied
```
`Scam_Model` (Gemini) → `ai_languageModel` → `Scam_Classifier`. Two separate Gmail credentials: read-only on the fetch, delete-scope only on `Gmail_Delete_Op`.

## Required credentials

- `gmail_sanitization_readonly` — `gmail.readonly`, used by `Gmail_Fetch_Candidates`
- `gmail_sanitization_delete` — `https://mail.google.com/`, used **only** by `Gmail_Delete_Op`
- Gemini API key
- Telegram bot token + chat ID
- Audit sink credential

## Known gaps

- Rewire done in the JSON: delete is now downstream of both a dry-run gate and a human approval gate; fetch and delete use separate credentials.
- `DRY_RUN_UNTIL` is **informational** — n8n has no built-in run counter, so `dry_run` is a manual boolean the operator flips to `false` after reviewing that many runs of logged candidates.
- `Was_Approved` reads `$json.data.approved` from the Telegram `sendAndWait` response — confirm the exact field name against your n8n version on import.
- Not yet run end-to-end (Phase 2 tests T2.8/T2.9).

## Setup steps

1. Import `Data_Sanitization_Cron.json`.
2. Create **two** Gmail credentials: `Gmail (sanitization READ-ONLY)` with `gmail.readonly` only, and `Gmail (sanitization DELETE)` with `https://mail.google.com/`. Assign them to `Gmail_Fetch_Candidates` and `Gmail_Delete_Op` respectively.
3. Replace the Gemini cred, Telegram bot cred + `REPLACE_TELEGRAM_CHAT_ID`, `REPLACE_SHEET_ID`.
4. Leave `Workflow_Config.dry_run = true`. Run against 5–10 sample emails incl. a deliberate false positive; confirm **nothing is deleted** and `audit_log` shows `dry_run_candidate` rows.
5. After reviewing classifier precision, set `dry_run = false`. Test the approval path: confirm **Deny** and **timeout** both prevent deletion.
