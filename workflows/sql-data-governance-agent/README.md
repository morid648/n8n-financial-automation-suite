# SQL Data Governance Agent

> Cross-cutting findings live in [`../../docs/PRD.md`](../../docs/PRD.md) Section 3 — this README links back rather than repeating them.

## Overview

Manual-triggered n8n workflow. An LLM agent runs read-only SQL data-quality checks against PostgreSQL and returns a structured JSON verdict per check. Feeds BI dashboards and DCF/valuation inputs downstream, so verdict accuracy matters.

**Trigger:** Manual · **Primary risk:** Medium (DB write risk if the credential is misconfigured)

## Tech stack

- n8n
- Anthropic Claude (agent language model)
- PostgreSQL (read-only role)

## Node reference

`Manual_Trigger → Workflow_Config → Load_Check_Definitions (code, 5 read-only checks) → Data_Splitter → Batch_Iterator (splitInBatches)`:
- loop output → `NLP_Financial_Agent → Collect_Verdict → Batch_Iterator` (**loop-back closed**)
- done output → `Data_Aggregator → Governance_Report_Write → Audit_Log_Write`
- agent `onError` → `Error_Context → Error_Audit_Write`

Sub-connections wired (**PRD 3.2 fix**): `LLM_Inference_Engine` (Anthropic) `ai_languageModel`; `PostgreSQL_Query_Engine` (postgresTool, read-only role) `ai_tool`; `Schema_Validation_Parser` `ai_outputParser` (T1.4 verdict schema). The agent runs the candidate `SELECT` for each check via `$fromAI`, compares metric vs threshold, and emits `{status, severity, row_count, summary, remediation}`.

## Required credentials

- PostgreSQL — **least-privilege, read-only role** (see PRD Section 4, Credential scoping)
- Anthropic API key (via n8n credential store, never inline)

## Known gaps

- PRD 3.2 **fixed**; batch loop-back closed; T1.4 verdict schema wired.
- The 5 checks in `Load_Check_Definitions` assume tables `customers` / `orders` / `invoices` / `transactions`. Edit the array to match the real schema.
- The read-only role still has to be **created in PostgreSQL** — the JSON only points a credential at it; it cannot enforce read-only by itself.
- Not yet run end-to-end (Phase 6).

## Setup steps

1. Import `SQL_Data_Governance_Agent.json` into n8n.
2. In PostgreSQL: `CREATE ROLE n8n_governance_ro LOGIN; GRANT CONNECT, SELECT ...; ALTER ROLE n8n_governance_ro SET default_transaction_read_only = on;` Add it as the `Postgres (READ-ONLY role)` credential.
3. Replace the Anthropic cred + `REPLACE_SHEET_ID`; create ledger tabs `governance_runs` + `audit_log`.
4. Adjust the check array in `Load_Check_Definitions` to your schema.
5. Run against 5–10 sample checks before pointing at a production database.
