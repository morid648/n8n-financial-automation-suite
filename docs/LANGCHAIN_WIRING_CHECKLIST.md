# LangChain Wiring Checklist

Fixes PRD Sections 3.2, 3.3, 3.4, 3.8 once, as a reusable pattern applied per workflow. Every `@n8n/n8n-nodes-langchain.*` node in the suite currently has only `main` connections wired; none of the sub-connections below exist in any of the 8 JSON files.

---

## 1. Sub-connection types and what attaches with them

In n8n's LangChain integration, helper nodes attach to an agent/chain through typed **sub-connections**, not the `main` data path:

| Sub-connection | Source node type | Target | Notes |
|---|---|---|---|
| `ai_languageModel` | Chat model node (Anthropic Claude, Google Gemini) | Agent / chain / classifier / extractor | **Required** — without it the agent fails at runtime |
| `ai_tool` | Tool node (e.g. PostgreSQL tool, retrieval tool) | Agent | One edge per tool |
| `ai_outputParser` | Structured output parser node | Agent / chain | Needed for a typed JSON verdict/schema |
| `ai_memory` | Memory node (`Context_Memory_Buffer`) | Agent | **Not** on the main path (fixes 3.4) |
| `ai_embedding` | Embeddings node (`Cohere_Vector_Embeddings`) | Vector store node | Feeds both insert and query |
| `ai_vectorStore` | Vector store node (Pinecone / Supabase) | Retrieval tool → agent | Vector store attaches to a retriever tool, which attaches to the agent via `ai_tool` |

## 2. Per-node fix map

### 2.1 Language model not wired (PRD 3.2) — all 8 workflows

| Workflow | Model node | Connect via `ai_languageModel` to |
|---|---|---|
| SQL Data Governance Agent | Anthropic Claude | `SQL_Agent` |
| Analyst Screening Pipeline | Anthropic Claude | `NLP_Financial_Agent`, `LLM_Execution_Chain` |
| Automated Accounts Receivable | `Gemini_Inference_Engine` | `Quantitative_Data_Parser` |
| Corporate Comms Triage | `Gemini_Inference_Engine` | `NLP_Text_Classifier`, `LLM_Execution_Chain` |
| Data Sanitization Cron | (classifier model, if any) | flagging/classification node |
| Investor Relations NLP | Anthropic Claude | `NLP_Financial_Agent`, `LLM_Execution_Chain` |
| Macro Thematic Ideation | Anthropic Claude | `NLP_Financial_Agent`, `LLM_Execution_Chain` |
| Market Sentiment Engine | Anthropic Claude | `NLP_Financial_Agent`, `LLM_Execution_Chain` |

`Gemini_Inference_Engine` in AR and Comms Triage currently has **zero** connections (PRD 3.8) — this is the same fix, called out separately because those two are not RAG-template workflows.

### 2.2 Agent has no main-path input (PRD 3.3) — the 4 RAG workflows

`Analyst_Screening_Pipeline` / `Investor_Relations_NLP` / `Macro_Thematic_Ideation` / `Market_Sentiment_Engine`: the ingestion path `Ingest_API_Payload → Text_Chunking_Engine → Cohere_Vector_Embeddings` only populates the vector store; nothing hands data to `NLP_Financial_Agent`, so the agent never executes in the webhook's data path.

**Fix:** add a `Set` (or `Code`) bridge node that takes the original webhook payload and passes it as the agent's input `text`:

```
Ingest_API_Payload ──main──> Bridge_Set_AgentInput ──main──> NLP_Financial_Agent
                    └─main──> Text_Chunking_Engine ──> Cohere_Vector_Embeddings ──ai_embedding──> Vector_Store
```

### 2.3 `Context_Memory_Buffer` on the main path (PRD 3.4) — the 4 RAG workflows

Currently: `Webhook ──main──> Context_Memory_Buffer`.

**Fix:** delete that `main` edge; add `Context_Memory_Buffer ──ai_memory──> NLP_Financial_Agent`.

### 2.4 Orphaned RAG helper nodes (PRD 3.2) — the 4 RAG workflows

`Cohere_Vector_Embeddings`, `Vector_DB_Insert` / `Vector_DB_Query`, `Vector_Retrieval_Tool`, `Context_Memory_Buffer` are all orphaned from the agent. Wire:

- `Cohere_Vector_Embeddings ──ai_embedding──> Vector_DB_Insert` and `──> Vector_DB_Query`
- `Vector_DB_Query ──ai_vectorStore──> Vector_Retrieval_Tool`
- `Vector_Retrieval_Tool ──ai_tool──> NLP_Financial_Agent`
- `Context_Memory_Buffer ──ai_memory──> NLP_Financial_Agent`

## 3. Per-workflow verification

For each workflow, confirm before marking it done:

- [ ] Every agent/chain/classifier/extractor has exactly one `ai_languageModel` edge.
- [ ] Every tool the agent needs has an `ai_tool` edge.
- [ ] If the workflow produces a typed schema, an `ai_outputParser` edge exists.
- [ ] Memory nodes attach via `ai_memory`, never `main`.
- [ ] Embeddings attach to the vector store via `ai_embedding`.
- [ ] The agent has at least one incoming `main` connection carrying real input.
- [ ] "Continue on Fail" + a named error branch on every AI node (PRD Section 4).

## 4. Reference workflow

`T3.6` builds one corrected RAG workflow JSON to serve as the copy-source for the 4 clones. Link it here once it exists: `workflows/_reference/RAG_Reference.json`.
