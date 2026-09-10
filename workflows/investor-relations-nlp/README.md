# Investor Relations NLP

> Cross-cutting findings live in [`../../docs/PRD.md`](../../docs/PRD.md) Section 3 — this README links back rather than repeating them.

## Overview

Webhook-triggered RAG workflow. Distills stakeholder communications into a structured executive summary (key asks, sentiment, urgency, suggested owner).

**Trigger:** Webhook · **Primary risk:** Low

## Tech stack

- n8n
- Anthropic Claude (agent language model)
- Cohere embeddings + Pinecone vector store

## Node reference

Same corrected RAG shape as the reference workflow ([`../analyst-screening-pipeline/`](../analyst-screening-pipeline/)): `Ingest_API_Payload → Workflow_Config → Enabled_Gate → Bridge_Agent_Input → NLP_Financial_Agent → Flatten_Summary → Master_Ledger_Update → Audit_Log_Write → Respond_To_Caller`, with an ingest branch to `Vector_DB_Insert` and `onError → Error_Context → Error_Audit_Write → Trigger_Executive_Alert`.

Sub-connections wired: `LLM_Inference_Engine` (Anthropic, `claude-sonnet-5`) `ai_languageModel`; `Context_Memory_Buffer` `ai_memory`; `Vector_Retrieval_Tool` (`ir_history_search`) `ai_tool`; `Schema_Validation_Parser` `ai_outputParser` (T1.9 summary schema); `Cohere_Vector_Embeddings` `ai_embedding`.

## Required credentials

- Anthropic API key
- Cohere API key
- Pinecone API key + index

## Known gaps

- PRD 3.1/3.2/3.3/3.4 **fixed** in the current JSON.
- Not yet run end-to-end (Phase 6). Credential IDs are `REPLACE_*` placeholders.
- Pinecone index `investor-relations` (namespace `stakeholder-comms`) must exist before first run.

## Setup steps

1. Import `Investor_Relations_NLP.json`.
2. Replace every `REPLACE_*` placeholder with real credentials / IDs in n8n.
3. Create the Pinecone index and ledger tabs `ir_summaries` + `audit_log`.
4. Test against 5–10 sample stakeholder messages; confirm the summary schema validates and the audit row is written.
