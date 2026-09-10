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

_TBD — populate from the imported `SQL_Data_Governance_Agent.json` once the skeleton is in place._

Key nodes: `SQL_Agent` / `Batch_Iterator` / `PostgreSQL` tool / output parser.

## Required credentials

- PostgreSQL — **least-privilege, read-only role** (see PRD Section 4, Credential scoping)
- Anthropic API key (via n8n credential store, never inline)

## Known gaps

- `ai_languageModel` / `ai_tool` / `ai_outputParser` sub-connections not wired to the agent (PRD 3.2).
- `Batch_Iterator` has no loop-back connection.
- Read-only PostgreSQL role not yet enforced.
- Structured JSON verdict schema not yet defined.

## Setup steps

1. Import `SQL_Data_Governance_Agent.json` into n8n.
2. Create a read-only PostgreSQL role and add it as a credential.
3. Add the Anthropic credential.
4. Wire the LangChain sub-connections per [`../../docs/LANGCHAIN_WIRING_CHECKLIST.md`](../../docs/LANGCHAIN_WIRING_CHECKLIST.md).
5. Run against 5–10 sample checks before connecting production databases.
