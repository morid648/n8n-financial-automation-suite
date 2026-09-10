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

_TBD — populate from `Market_Sentiment_Engine.json`._ One of four workflows sharing an identical skeleton (PRD 3.1).

## Required credentials

- Anthropic API key
- Cohere API key
- Pinecone API key + index

## Known gaps

- Shares a byte-for-byte identical skeleton with 3 other workflows — no sentiment-specific logic yet (PRD 3.1).
- LangChain sub-connections missing (PRD 3.2).
- `NLP_Financial_Agent` has no incoming main connection — needs a bridge node (PRD 3.3).
- `Context_Memory_Buffer` wired on the main path instead of `ai_memory` (PRD 3.4).
- Sentiment output schema not defined.

## Setup steps

1. Import `Market_Sentiment_Engine.json`.
2. Add all credentials above.
3. Apply the fixes in [`../../docs/LANGCHAIN_WIRING_CHECKLIST.md`](../../docs/LANGCHAIN_WIRING_CHECKLIST.md).
4. Layer in the sentiment-classification prompt + T1.11 schema.
5. Test against 5–10 unstructured sentiment snippets before going live.
