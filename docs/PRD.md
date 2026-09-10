# Product Requirements Document
## n8n Financial Automation Suite — 8-Workflow Portfolio

| Field | Value |
|---|---|
| Owner | Anshul |
| Scope | 8 n8n workflows for finance/data-analytics automation |
| Status | Draft — based on current skeleton JSON exports |
| Related | See each workflow's own `README.md` under `/workflows/<name>/` for build-level detail |

---

## 1. Purpose & Problem Statement

### 1.1 Purpose

This suite is a set of n8n workflows automating finance-adjacent operations: data governance, resume screening, accounts receivable, internal comms triage, mailbox hygiene, investor relations, macro research, and market sentiment. Each was exported as a JSON skeleton with an accompanying README. This PRD consolidates them into one portfolio-level spec, calls out the structural issues found across all 8, and defines what "done" looks like for each before any of them run against real data or live credentials.

### 1.2 Problem Statement

Each of the eight functions this suite targets is currently handled manually or by a disconnected point tool: SQL hygiene checked by hand, resumes screened by eye, invoices logged via manual data entry, inbox messages triaged by scanning, mailbox junk cleared manually, IR summaries written from scratch, macro research recalled from memory instead of retrieved against real data, and sentiment tracked informally if at all. This doesn't scale past a handful of items per day, is inconsistent between whoever is doing it, and is slow relative to the volume of communications and data a finance/analytics function actually generates.

The stakes are higher than "manual work is slow," though: several of these processes feed directly into higher-consequence outputs — data governance and accounts-receivable data feed BI dashboards and DCF/valuation models, and sentiment feeds a SOTP valuation overlay — so an error or delay upstream propagates into a financial decision downstream. At the same time, two of the workflows (mailbox deletion, ledger writes) involve actions that are hard or impossible to undo if the automation gets it wrong. The problem this suite solves is therefore twofold: (1) replace slow, inconsistent manual processes with automation, while (2) keeping a human checkpoint wherever the automated action is consequential or irreversible — a balance the current skeleton exports do not yet strike (see Section 3.7 for the most acute example).

## 2. Portfolio at a Glance

| # | Workflow | Trigger | Core Function | Primary Risk Level |
|---|---|---|---|---|
| 1 | SQL Data Governance Agent | Manual | LLM agent runs read-only SQL checks against PostgreSQL for data-quality issues | Medium (DB write risk if misconfigured) |
| 2 | Analyst Screening Pipeline | Webhook | RAG-based resume screening for quant roles (SQL/Python/Excel skill extraction) | Low |
| 3 | Automated Accounts Receivable | Gmail trigger | Parses invoice emails, generates PDF record, updates ledger | Medium (financial data accuracy) |
| 4 | Corporate Comms Triage | Gmail trigger | Classifies inbound mail (billing/updates/spam) and alerts on critical items | Low–Medium (alert fatigue if untuned) |
| 5 | Data Sanitization Cron | Schedule | Deletes flagged/scam emails on a cron | **High** (irreversible delete, no approval gate) |
| 6 | Investor Relations NLP | Webhook | Distills stakeholder communications into executive summaries | Low |
| 7 | Macro Thematic Ideation | Webhook | RAG retrieval over macro/sector data for research ideation | Low |
| 8 | Market Sentiment Engine | Webhook | Classifies unstructured sentiment via vector search | Low |

## 3. Critical Cross-Cutting Findings

These apply across multiple workflows and should be read before touching any individual JSON.

### 3.1 Four workflows share one identical, unfinished skeleton
`Analyst_Screening_Pipeline`, `Investor_Relations_NLP`, `Macro_Thematic_Ideation`, and `Market_Sentiment_Engine` are **byte-for-byte identical** in `nodes` and `connections` — only the `name` field and README differ. This means none of them yet reflect their stated purpose at the workflow-logic level (e.g., the "macro ideation" workflow has no macro-specific logic; it's the same RAG shell as the "sentiment engine"). Each needs its own prompt engineering, field extraction, and output routing before it does what its README claims.

### 3.2 LangChain sub-connections are missing everywhere an AI node appears
Every workflow using `@n8n/n8n-nodes-langchain.*` nodes only has `main` connections wired. None of the required sub-connection types (`ai_languageModel`, `ai_tool`, `ai_outputParser`, `ai_memory`, `ai_embedding`, `ai_vectorStore`) are present in any of the 8 JSON files. Concretely:
- No agent or chain in any workflow has a language model actually wired to it — every `NLP_Financial_Agent`, `LLM_Execution_Chain`, and `Quantitative_Data_Parser` node will fail at runtime as-is.
- `Cohere_Vector_Embeddings`, `Vector_DB_Insert/Query`, `Vector_Retrieval_Tool`, and `Context_Memory_Buffer` (in the four RAG workflows) are all orphaned from the agent.
- This is not a one-off bug — it's a template-level gap. Fixing it once (as a checklist) and applying it per-workflow is faster than debugging each individually.

### 3.3 The RAG agent has no main-path input in all four RAG workflows
In `Analyst_Screening_Pipeline` / `Investor_Relations_NLP` / `Macro_Thematic_Ideation` / `Market_Sentiment_Engine`, tracing the `main` connection graph shows `NLP_Financial_Agent` has **no incoming main connection at all** — the ingestion path (`Ingest_API_Payload → Text_Chunking_Engine → Cohere_Vector_Embeddings`) only populates the vector store; it never hands data to the agent. As drawn, the agent node would never actually execute inside the webhook's data path. A bridging node (e.g., a `Set`/`Code` node passing the original webhook payload as the agent's input `text`) is required in all four.

### 3.4 `Context_Memory_Buffer` is wired incorrectly
In all four RAG workflows, `Context_Memory_Buffer` (a memory node) receives a `main` connection directly from the webhook. Memory nodes in n8n's LangChain integration attach to an agent via the `ai_memory` sub-connection, not the main data path. This connection should be removed and replaced with a proper `ai_memory` link to `NLP_Financial_Agent`.

### 3.5 Documentation/implementation mismatch: Macro Thematic Ideation
The README states the workflow retrieves data "via Supabase vector stores," but the JSON uses `vectorStorePinecone` nodes, identical to the Pinecone-based sentiment engine. Either the README or the node choice is wrong — this needs a decision before the workflow is built out, since Supabase and Pinecone require different credentials and query syntax.

### 3.6 Corporate Comms Triage doesn't actually reduce noise yet
The classifier (`NLP_Text_Classifier`) has a single downstream path straight into the alert chain — every classified message, regardless of category (billing, spam, project update), currently flows to `Telegram_Executive_Alert`. The README's value proposition ("eliminates noise... isolates critical alerts") requires conditional branching by category so only genuinely critical categories trigger an alert. This needs an `IF`/`Switch` node keyed off the classifier's output category.

### 3.7 Data Sanitization Cron deletes before it alerts — no human-in-the-loop
`Gmail_Delete_Op` runs immediately after `Gmail_Fetch_Flagged`, and `Telegram_Executive_Alert` only fires *after* the delete, as a notification of what already happened. For a workflow whose entire job is identifying "flagged scam vectors" for deletion, this is a real data-loss risk if the flagging logic has any false positives — there is no review step, no dry-run mode, and no undo path (Gmail's trash has a retention window, but that's not a designed safeguard here). **This is the single highest-priority fix in the whole portfolio** and is treated as a blocking requirement, not a nice-to-have (see Section 6.5).

### 3.8 Orphaned LLM nodes outside the RAG workflows too
`Gemini_Inference_Engine` in both `Automated_Accounts_Receivable` and `Corporate_Comms_Triage` has zero connections in the JSON — it's placed on the canvas but never wired to the node that needs it (`Quantitative_Data_Parser` and `NLP_Text_Classifier`/`LLM_Execution_Chain` respectively). Same category of issue as 3.2, called out separately because these two workflows aren't part of the RAG-template group.

## 4. Shared Non-Functional Requirements

| Category | Requirement |
|---|---|
| Credential scoping | Every read-only use case (SQL governance, vector queries) uses a least-privilege credential; every destructive action (Gmail delete, ledger writes) requires an explicit confirmation/approval step or a dry-run mode before going live |
| Error handling | Every AI node (agent/chain/classifier/extractor) needs "Continue on Fail" + a defined error branch, not just the two workflows that already have an `onError` path |
| Auditability | Every workflow that writes to `Master_Ledger_Update` or deletes data must log what it did, when, and why (a row per action, not just the end state) |
| Secrets | No API keys/connection strings inline in node parameters — all via n8n credentials store |
| Cost control | Batch sizes and model choice tunable per workflow to manage LLM token spend, especially for the four high-frequency, webhook-triggered RAG workflows |
| Documentation parity | A workflow's README must match its actual node types (see 3.5) before it's considered "shippable" |

## 5. Per-Workflow Requirements Summary

Full detail for each lives in `/workflows/<folder>/README.md`. Summarized here:

### 5.1 SQL Data Governance Agent
Wire `ai_languageModel`/`ai_tool`/`ai_outputParser` into the agent; add the batch loop-back on `Batch_Iterator`; enforce a read-only PostgreSQL role; define the structured JSON verdict schema. (Full spec previously delivered as a standalone PRD; see workflow README for the condensed version.)

### 5.2 Analyst Screening Pipeline
Fix 3.2/3.3/3.4. Define the extraction target schema (required skills: SQL, Power BI, Python/Pandas/NumPy, Excel at scale) as the agent's structured output. Add a scoring/ranking step before `Master_Ledger_Update` so the ledger reflects a ranked shortlist, not raw agent text.

### 5.3 Automated Accounts Receivable
Wire `Gemini_Inference_Engine` to `Quantitative_Data_Parser` via `ai_languageModel`. Define the extraction schema explicitly (invoice number, vendor, amount, due date, currency). Clarify what `Gmail_Operations` actually does (send acknowledgment? forward to AP team?) — currently undocumented. Add a validation step before `Master_Ledger_Update` to catch extraction errors (e.g., missing amount) before they hit the ledger feeding DCF inputs.

### 5.4 Corporate Comms Triage
Wire `Gemini_Inference_Engine` into both AI nodes. Add category-based branching (3.6) so only critical categories reach `Telegram_Executive_Alert`. Define the fixed category taxonomy (billing, project update, spam, other) as a closed set, not free text.

### 5.5 Data Sanitization Cron
**Blocking:** move `Telegram_Executive_Alert` (or a new approval step) to *before* `Gmail_Delete_Op`, with an explicit approve/deny action, or add a dry-run config flag that logs candidates for deletion without deleting on the first N runs. Define exactly what "flagged" means (which Gmail label/filter) since that's the entire basis for an irreversible action.

### 5.6 Investor Relations NLP
Same technical fixes as 5.2 (3.2/3.3/3.4), applied to a summarization/distillation prompt rather than a screening prompt. Define what "structured executive summary" means as an output schema (key asks, sentiment, urgency, suggested owner).

### 5.7 Macro Thematic Ideation
Resolve 3.5 (Supabase vs. Pinecone) before any further build work — this determines the vector store node type, credential, and query syntax. Apply the same 3.2/3.3/3.4 fixes once that's decided.

### 5.8 Market Sentiment Engine
Same technical fixes as 5.2/5.6, applied to a sentiment-classification prompt. Define the sentiment output schema (score, category, source snippet) so it can feed a SOTP/brand-equity overlay as the README claims.

## 6. Testing & Rollout Priorities (Portfolio-Wide)

1. **Fix and test Data Sanitization Cron's approval gate first** — it's the only workflow with an irreversible action and no safeguard.
2. Fix the shared LangChain wiring gap (3.2–3.4) once, then apply the same pattern to all five affected workflows.
3. Resolve the Macro Thematic Ideation vector-store mismatch (3.5) before building it out further.
4. Add category branching to Corporate Comms Triage (3.6) before enabling live alerting.
5. Run each workflow end-to-end against a small sample (5–10 items) before connecting to production credentials/mailboxes.

## 7. Repository & Documentation Standard

See root `README.md` for the repo layout. Each `/workflows/<name>/` folder contains:
- The workflow's `.json` export (importable directly into n8n)
- A `README.md` covering: overview, tech stack, node reference, required credentials, known gaps, and setup steps

This PRD is the single cross-workflow source of truth; individual READMEs should not repeat the cross-cutting findings in Section 3 — they link back here instead.
