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

_TBD — populate from `Macro_Thematic_Ideation.json`._ One of four workflows sharing an identical skeleton (PRD 3.1).

## Vector store decision (resolved 2026-09-11)

**Decision:** Supabase (`vectorStoreSupabase`, pgvector).

**Rationale:** Keeps the README prose authoritative; consolidates macro/sector data alongside other Postgres-resident data; pgvector avoids a separate managed-index bill for a low-frequency research workflow. The other three RAG workflows stay on Pinecone.

**Build impact:** replace `vectorStorePinecone` nodes with `vectorStoreSupabase`; create a Supabase table with a `vector` column + an `ivfflat`/`hnsw` index + a `match_documents` RPC; swap the query node to call that RPC.

## Required credentials

- Anthropic API key
- Cohere API key
- Supabase — project URL + service role key (or a scoped key with `select`/`insert` on the vector table + `execute` on the match RPC)

## Known gaps

- Vector store mismatch **resolved** (Supabase) — JSON nodes still need swapping from Pinecone.
- Shares a byte-for-byte identical skeleton with 3 other workflows — no macro-specific logic yet (PRD 3.1).
- LangChain sub-connections missing (PRD 3.2).
- `NLP_Financial_Agent` has no incoming main connection — needs a bridge node (PRD 3.3).
- `Context_Memory_Buffer` wired on the main path instead of `ai_memory` (PRD 3.4).

## Setup steps

1. Provision Supabase: table with a `vector` column, ANN index, and a `match_documents` RPC.
2. Import `Macro_Thematic_Ideation.json`; replace `vectorStorePinecone` nodes with `vectorStoreSupabase`.
3. Add all credentials above.
4. Apply the fixes in [`../../docs/LANGCHAIN_WIRING_CHECKLIST.md`](../../docs/LANGCHAIN_WIRING_CHECKLIST.md).
5. Layer in the ideation prompt + T1.10 schema (see [`../../docs/SCHEMAS.md`](../../docs/SCHEMAS.md)).
6. Test against 5–10 sample research queries before going live.
