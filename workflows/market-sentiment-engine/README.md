# Market Sentiment Engine

> Cross-cutting findings live in [`../../docs/PRD.md`](../../docs/PRD.md) Section 3 — this README links back rather than repeating them.

## Overview

Webhook-triggered RAG workflow. Classifies unstructured sentiment via vector search, returning a structured output (score, category, source snippet) that can feed a SOTP / brand-equity valuation overlay.

**Trigger:** Webhook · **Primary risk:** Low

## Tech stack

- n8n
- Anthropic Claude (agent language model)
- Cohere embeddings + Pinecone vector store

## Node reference

Same corrected RAG shape as the reference workflow ([`../analyst-screening-pipeline/`](../analyst-screening-pipeline/)): agent → `Flatten_Sentiment → Master_Ledger_Update (sentiment_scores) → Audit_Log_Write → Respond_To_Caller`, ingest branch to `Vector_DB_Insert`, `onError` branch to Slack.

Sub-connections wired: `LLM_Inference_Engine` (Anthropic, `claude-haiku-4-5`) `ai_languageModel`; `Context_Memory_Buffer` `ai_memory`; `Vector_Retrieval_Tool` (`sentiment_corpus_search`) `ai_tool`; `Schema_Validation_Parser` `ai_outputParser` (T1.11 `{score, category, confidence, entity, source_snippet}`); `Cohere_Vector_Embeddings` `ai_embedding`.

## Required credentials

- Anthropic API key
- Cohere API key
- Pinecone API key + index

## Known gaps

- PRD 3.1/3.2/3.3/3.4 **fixed** in the current JSON.
- Not yet run end-to-end (Phase 6). Credential IDs are `REPLACE_*` placeholders.
- Pinecone index `market-sentiment` (namespace `sentiment`) must exist before first run.

## Setup steps

1. Import `Market_Sentiment_Engine.json`.
2. Replace every `REPLACE_*` placeholder with real credentials / IDs in n8n.
3. Create the Pinecone index and ledger tabs `sentiment_scores` + `audit_log`.
4. Test against 5–10 unstructured sentiment snippets; confirm `score` ∈ [-1,1] and the overlay can key on `entity` + `as_of`.
