# Data Sanitization Cron

> ⚠️ Highest-priority fix in the portfolio. Cross-cutting findings live in [`../../docs/PRD.md`](../../docs/PRD.md) Section 3 (esp. 3.7) — this README links back rather than repeating them.

## Overview

Schedule-triggered workflow that deletes flagged/scam emails from a mailbox. As exported it deletes **before** it alerts — there is no review step, dry-run, or undo. A human-in-the-loop safeguard is a **blocking** requirement before this runs against real data.

**Trigger:** Schedule (cron) · **Primary risk:** HIGH (irreversible delete)

## Tech stack

- n8n
- Gmail (fetch + delete)
- Telegram (approval / notification)

## Node reference

_TBD — populate from `Data_Sanitization_Cron.json`._ Current path: `Gmail_Fetch_Flagged → Gmail_Delete_Op → Telegram_Executive_Alert` (delete happens first — must change).

## Required credentials

- Gmail OAuth — **read-only scope on the fetch step**; delete scope only on the delete step
- Telegram bot token + chat ID

## Known gaps (blocking)

- `Gmail_Delete_Op` runs immediately after fetch; alert only fires after deletion (PRD 3.7).
- No approval gate, no dry-run mode, no undo path.
- "Flagged" is undefined — which Gmail label/filter/query is the entire basis for the delete.

## Setup steps

1. Import `Data_Sanitization_Cron.json`.
2. **Define "flagged"** (specific Gmail label/filter) and document it here.
3. Re-wire to `Gmail_Fetch_Flagged → <approval or dry-run step> → Gmail_Delete_Op`.
4. Implement the Telegram approve/deny gate and/or a dry-run flag that logs candidates without deleting.
5. Add the post-delete audit-log write.
6. Run in dry-run against 5–10 sample emails; confirm nothing is deleted and the log is correct before enabling deletion.
