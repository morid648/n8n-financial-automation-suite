# Analyst Screening Pipeline

> Cross-cutting findings live in [`../../docs/PRD.md`](../../docs/PRD.md) Section 3 — this README links back rather than repeating them.

## Overview

Webhook-triggered RAG workflow. Screens resumes for quant/analyst roles by extracting evidence of required skills (SQL, Power BI, Python/Pandas/NumPy, Excel at scale), scoring each candidate, and writing a ranked shortlist to `Master_Ledger_Update`.

**Trigger:** Webhook · **Primary risk:** Low

## Tech stack

- n8n
- Anthropic Claude (agent language model)
- Cohere embeddings + Pinecone vector store
- Google Sheets (`Master_Ledger_Update`)

## Node reference

| Node | Type | Role |
|---|---|---|
| `Ingest_API_Payload` | webhook | POST `analyst-screening/intake`, responds via `Respond_To_Caller` |
| `Workflow_Config` | set | cost/tuning knobs (model, top_k, chunk size, score threshold) |
| `Enabled_Gate` | if | halts when `enabled=false` |
| `Bridge_Agent_Input` | set | **PRD 3.3 fix** — passes payload `text`/`sessionId` to the agent's main input |
| `Text_Chunking_Engine` → `Document_Loader` → `Vector_DB_Insert` | LangChain | ingest branch, `ai_textSplitter`/`ai_document`/`ai_embedding` wired |
| `Cohere_Vector_Embeddings` | embeddingsCohere | `embed-english-v3.0`, feeds insert + retrieval |
| `Vector_Retrieval_Tool` | vectorStorePinecone (retrieve-as-tool) | `ai_tool` → agent |
| `LLM_Inference_Engine` | lmChatAnthropic | **PRD 3.2 fix** — `ai_languageModel` → agent + retrieval tool |
| `Context_Memory_Buffer` | memoryBufferWindow | **PRD 3.4 fix** — `ai_memory` → agent (off the main path) |
| `Schema_Validation_Parser` | outputParserStructured | `ai_outputParser` → agent, T1.5 extraction schema |
| `NLP_Financial_Agent` | agent | extracts skill evidence |
| `Score_And_Rank` | code | deterministic T1.5 rubric → ranked shortlist + `recommend` flag |
| `Master_Ledger_Update` → `Audit_Log_Write` → `Respond_To_Caller` | — | ledger + audit row + HTTP response |
| `Error_Context` → `Error_Audit_Write` → `Trigger_Executive_Alert` | — | agent `onError` branch (T1.14) |

## Required credentials

- Anthropic API key
- Cohere API key
- Pinecone API key + index
- Google Sheets OAuth

## Known gaps

- PRD 3.1/3.2/3.3/3.4 **fixed** in the current JSON (screening-specific prompt, LangChain sub-connections, bridge node, `ai_memory`).
- Not yet run end-to-end against sample data (Phase 6). All credential IDs are `REPLACE_*` placeholders.
- Pinecone index (`analyst-screening`, namespace `resumes`) must be created before first run.

## Setup steps

1. Import `Analyst_Screening_Pipeline.json`.
2. Replace every `REPLACE_*` credential ID and `REPLACE_SHEET_ID` / `REPLACE_SLACK_CHANNEL` with real values in n8n's credential store (no inline keys).
3. Create the Pinecone index and the ledger tabs `shortlist` + `audit_log`.
4. Seed the vector store with comparable historical resumes (optional but improves retrieval).
5. Test against 5–10 sample resumes; confirm the shortlist ranks correctly and the audit row is written.
