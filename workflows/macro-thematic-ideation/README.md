# Macro Thematic Ideation

> Cross-cutting findings live in [`../../docs/PRD.md`](../../docs/PRD.md) Section 3 — this README links back rather than repeating them.

## Overview

Webhook-triggered RAG workflow. Retrieves over macro/sector data to support research ideation, returning a structured output (theme, supporting data points, sectors affected, confidence).

**Trigger:** Webhook · **Primary risk:** Low

## Tech stack

- n8n
- Anthropic Claude (agent language model)
- Cohere embeddings
- Vector store: **Supabase vs Pinecone — UNDECIDED (PRD 3.5)**

## Node reference

_TBD — populate from `Macro_Thematic_Ideation.json`._ One of four workflows sharing an identical skeleton (PRD 3.1).

## Vector store decision (blocking)

The README prose says Supabase; the JSON uses `vectorStorePinecone`. This must be resolved before build work — it determines the vector node type, credential, and query syntax.

**Decision:** _pending_ · **Rationale:** _pending_

## Required credentials

- Anthropic API key
- Cohere API key
- Supabase connection **or** Pinecone API key + index (per decision above)

## Known gaps

- Vector store mismatch unresolved (PRD 3.5).
- Shares a byte-for-byte identical skeleton with 3 other workflows — no macro-specific logic yet (PRD 3.1).
- LangChain sub-connections missing (PRD 3.2).
- `NLP_Financial_Agent` has no incoming main connection — needs a bridge node (PRD 3.3).
- `Context_Memory_Buffer` wired on the main path instead of `ai_memory` (PRD 3.4).

## Setup steps

1. Resolve the vector store decision above.
2. Import `Macro_Thematic_Ideation.json`; swap vector nodes if the decision is Supabase.
3. Add all credentials above.
4. Apply the fixes in [`../../docs/LANGCHAIN_WIRING_CHECKLIST.md`](../../docs/LANGCHAIN_WIRING_CHECKLIST.md).
5. Layer in the ideation prompt + T1.10 schema.
6. Test against 5–10 sample research queries before going live.
