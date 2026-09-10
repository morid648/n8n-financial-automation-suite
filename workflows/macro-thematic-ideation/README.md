# Macro Thematic Ideation

> Cross-cutting findings live in [`../../docs/PRD.md`](../../docs/PRD.md) Section 3 — this README links back rather than repeating them.

## Overview

Webhook-triggered RAG workflow. Retrieves over macro/sector data to support research ideation, returning a structured output (theme, supporting data points, sectors affected, confidence).

**Trigger:** Webhook · **Primary risk:** Low

## Tech stack

- n8n
- Anthropic Claude (agent language model)
- Cohere embeddings
- Vector store: **Supabase** (pgvector) — decided, see below

## Node reference

Corrected RAG shape with **Supabase** vector nodes (`vectorStoreSupabase`, `match_documents` RPC) in place of Pinecone: agent → `Flatten_Idea → Master_Ledger_Update (macro_ideas) → Audit_Log_Write → Respond_To_Caller`, ingest branch to `Vector_DB_Insert`, `onError` branch to Slack.

Sub-connections wired: `LLM_Inference_Engine` (Anthropic, `claude-sonnet-5`) `ai_languageModel`; `Context_Memory_Buffer` `ai_memory`; `Vector_Retrieval_Tool` (`macro_corpus_search`, Supabase) `ai_tool`; `Schema_Validation_Parser` `ai_outputParser` (T1.10 schema, every `supporting_point` must carry a `source_ref`); `Cohere_Vector_Embeddings` `ai_embedding`.

## Vector store decision (resolved 2026-09-11)

**Decision:** Supabase (`vectorStoreSupabase`, pgvector).

**Rationale:** Keeps the README prose authoritative; consolidates macro/sector data alongside other Postgres-resident data; pgvector avoids a separate managed-index bill for a low-frequency research workflow. The other three RAG workflows stay on Pinecone.

**Build impact:** replace `vectorStorePinecone` nodes with `vectorStoreSupabase`; create a Supabase table with a `vector` column + an `ivfflat`/`hnsw` index + a `match_documents` RPC; swap the query node to call that RPC.

## Required credentials

- Anthropic API key
- Cohere API key
- Supabase — project URL + service role key (or a scoped key with `select`/`insert` on the vector table + `execute` on the match RPC)

## Known gaps

- PRD 3.1/3.2/3.3/3.4/3.5 **fixed** — JSON now uses `vectorStoreSupabase`, macro-specific prompt, all sub-connections.
- Not yet run end-to-end (Phase 6). Credential IDs are `REPLACE_*` placeholders.
- Supabase table `macro_documents` (vector column + ANN index) and the `match_documents` RPC must be provisioned before first run.

## Setup steps

1. Provision Supabase: table with a `vector` column, ANN index, and a `match_documents` RPC.
2. Import `Macro_Thematic_Ideation.json`; replace `vectorStorePinecone` nodes with `vectorStoreSupabase`.
3. Add all credentials above.
4. Apply the fixes in [`../../docs/LANGCHAIN_WIRING_CHECKLIST.md`](../../docs/LANGCHAIN_WIRING_CHECKLIST.md).
5. Layer in the ideation prompt + T1.10 schema (see [`../../docs/SCHEMAS.md`](../../docs/SCHEMAS.md)).
6. Test against 5–10 sample research queries before going live.
