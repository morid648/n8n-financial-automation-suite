# Cross-Cutting Standards

Portfolio-wide non-functional standards (tasks T1.13–T1.15, backing PRD Section 4). Every workflow must conform before it is considered shippable.

---

## T1.13 — Credential scoping

| Use case | Credential | Scope |
|---|---|---|
| SQL Data Governance — DB access | PostgreSQL role `n8n_governance_ro` | `CONNECT` + `SELECT` only; no `INSERT/UPDATE/DELETE/DDL`; `SET default_transaction_read_only = on` for the role |
| Vector queries (all RAG workflows) | Pinecone / Supabase key | query + upsert to the one designated index/table only; no index admin |
| Cohere embeddings | Cohere key | embed endpoint only |
| Gmail — fetch (Comms Triage, AR, Sanitization) | Gmail OAuth | `gmail.readonly` + `gmail.modify` for labels; **`gmail.readonly` only** on the Sanitization *fetch* step |
| Gmail — delete (Sanitization) | separate Gmail OAuth cred | `https://mail.google.com/` scope, used **only** by `Gmail_Delete_Op`, downstream of the approval gate |
| Ledger writes | Google Sheets OAuth | scoped to the single spreadsheet ID |
| Telegram | bot token | one chat ID |

Rules:

1. Every read-only use case uses a least-privilege credential — never a shared admin key.
2. Every destructive action (`Gmail_Delete_Op`, any `Master_Ledger_Update` write) sits **downstream of** an explicit approval step or a dry-run flag (see T1.3 / workflow-specific tasks).
3. No API keys or connection strings inline in node parameters — all via the n8n credential store (PRD Section 4, Secrets). Verified in the T5.1 audit.
4. Credentials are named `<workflow-or-service>_<scope>` (e.g. `postgres_governance_ro`, `gmail_sanitization_delete`).

---

## T1.14 — AI-node error-handling pattern

Applies to every agent / chain / classifier / extractor node (`SQL_Agent`, `NLP_Financial_Agent`, `LLM_Execution_Chain`, `NLP_Text_Classifier`, `Quantitative_Data_Parser`, `Gemini_Inference_Engine` consumers).

Each such node must have:

1. **Settings → Continue On Fail = true** (n8n `onError: continueRegularOutput` is not enough on its own — we want an explicit branch).
2. **`onError` output wired to a named error branch**, not left dangling.
3. The error branch does three things:
   - writes an audit-log row (`outcome: "failed"`, `detail` = error message + node name);
   - sends a low-noise notification (Telegram) **only** if the workflow is user-facing/critical (Sanitization, AR, Comms Triage);
   - stops the run for that item — never lets a failed extraction fall through to a ledger write or a delete.
4. **Output-parser failures count as errors** — a structured-output node that can't produce valid JSON against its schema routes to the same error branch.

Reference sub-graph:

```
AI_Node ──main──> <happy path>
        └─error─> Set_ErrorContext ──> Audit_Log_Write ──> (Telegram_Notify?) ──> NoOp_Stop
```

Two workflows already have an `onError` path; the other six need it added.

---

## T1.15 — Cost-control knobs

Each workflow exposes tunables as **workflow-level static data / a single `Set` "Config" node** at the top of the flow, so spend can be tuned without editing individual nodes. Especially important for the 4 high-frequency webhook RAG workflows.

| Knob | Where | Default | Notes |
|---|---|---|---|
| `model` | Config node → referenced by the chat-model node | `claude-haiku-4-5` for classification/extraction; `claude-sonnet-5` for IR/macro synthesis | Gemini workflows: `gemini-flash` default |
| `max_batch_size` | Config node → `Batch_Iterator` / `SplitInBatches` | 10 | governance & screening |
| `top_k` | Config node → vector query | 8 | RAG retrieval breadth |
| `chunk_size` / `chunk_overlap` | Config node → `Text_Chunking_Engine` | 800 / 100 | embedding cost on ingest |
| `max_tokens` | Config node → chat model | 1024 | cap response length |
| `enabled` | Config node | true | kill switch per workflow |

Rule: no model name or batch size hard-coded in a downstream node — all read from the Config node via expressions (`={{ $json.config.model }}` pattern or workflow static data).
