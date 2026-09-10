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

_TBD — populate from `Analyst_Screening_Pipeline.json`._ One of four workflows sharing an identical skeleton (PRD 3.1).

## Required credentials

- Anthropic API key
- Cohere API key
- Pinecone API key + index
- Google Sheets OAuth

## Known gaps

- Shares a byte-for-byte identical skeleton with 3 other workflows — no screening-specific logic yet (PRD 3.1).
- LangChain sub-connections missing (PRD 3.2).
- `NLP_Financial_Agent` has no incoming main connection — needs a bridge node (PRD 3.3).
- `Context_Memory_Buffer` wired on the main path instead of `ai_memory` (PRD 3.4).
- Extraction target schema + scoring/ranking rubric not yet defined.

## Setup steps

1. Import `Analyst_Screening_Pipeline.json`.
2. Add all credentials above.
3. Apply the fixes in [`../../docs/LANGCHAIN_WIRING_CHECKLIST.md`](../../docs/LANGCHAIN_WIRING_CHECKLIST.md).
4. Layer in the screening prompt + T1.5 extraction schema + ranking step.
5. Test against 5–10 sample resumes before going live.
