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

_TBD — populate from `Data_Sanitization_Cron.json`._

Target path:
```
Schedule → Config(Set) → Gmail_Fetch_Candidates → Scam_Classifier ─(err)→ Error_Branch
                                                          │
                                    Filter(verdict∈{scam,junk} && conf≥0.9)
                                                          │
                              ┌───────────── dry_run? ─────────────┐
                            true                                 false
                              │                                     │
                     Audit_Log(dry_run_candidate)        Telegram_Approval_Gate
                                                                    │ approved ids
                                                            Gmail_Delete_Op → Audit_Log(email_delete)
```

## Required credentials

- `gmail_sanitization_readonly` — `gmail.readonly`, used by `Gmail_Fetch_Candidates`
- `gmail_sanitization_delete` — `https://mail.google.com/`, used **only** by `Gmail_Delete_Op`
- Gemini API key
- Telegram bot token + chat ID
- Audit sink credential

## Known gaps

- All of the above is the **target** design — the exported JSON still has `Gmail_Fetch_Flagged → Gmail_Delete_Op → Telegram_Executive_Alert` (delete first). Rewiring is Phase 2 (T2.1–T2.10) and needs the skeleton JSON.

## Setup steps

1. Import `Data_Sanitization_Cron.json`.
2. Add the two separately-scoped Gmail credentials + Gemini + Telegram + audit sink.
3. Add the `Config` Set node (`enabled`, `dry_run`, `DRY_RUN_UNTIL`, `min_confidence`, `APPROVAL_TIMEOUT`).
4. Rewire to the target path above; delete the direct fetch→delete edge.
5. Add `Scam_Classifier` with structured output + "Continue on Fail" + error branch.
6. Implement the Telegram approve/deny gate and the dry-run branch.
7. Add audit-log writes on every path (candidate, delete, deny, skip, fail).
8. Run in dry-run against 5–10 sample emails incl. a deliberate false positive; confirm nothing is deleted and the log is correct.
9. Switch `dry_run = false`; test the approval path; confirm Deny prevents deletion.
