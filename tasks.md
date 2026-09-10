# Tasks — n8n Financial Automation Suite

Derived from [`docs/PRD.md`](docs/PRD.md). Tasks are atomic (one verifiable outcome each) and grouped into phases ordered by dependency. Do not start a phase until its predecessor's blocking tasks are done. Each task lists its dependencies by ID.

Legend: `[ ]` not started · `[~]` in progress · `[x]` done · **(BLOCKING)** = gates the rest of its phase or a later phase.

---

## Execution status (2026-09-11)

**Done — everything not requiring the n8n JSON files:**
- Phase 0 scaffold (T0.1–T0.3, T0.5–T0.7). Git repo initialised, 3 commits.
- Phase 1: all specs written — [`docs/SCHEMAS.md`](docs/SCHEMAS.md) (T1.2, T1.4–T1.12), [`docs/STANDARDS.md`](docs/STANDARDS.md) (T1.13–T1.15). All 3 blocking decisions resolved by the user: T1.1 = **Supabase**, T1.2 = **classifier-decides**, T1.3 = **dry-run + approval gate**.
- Phase 3: wiring fully documented in [`docs/LANGCHAIN_WIRING_CHECKLIST.md`](docs/LANGCHAIN_WIRING_CHECKLIST.md) (T3.1–T3.5).

**Hard-blocked — needs the 8 n8n skeleton `.json` exports (not in this repo) + a running n8n instance + live credentials:**
- **T0.4** — drop the JSON exports into `workflows/<name>/`.
- **T3.6** — build the reference RAG workflow JSON.
- **All of Phases 2, 4, 5, 6** — every task edits a workflow JSON or runs it end-to-end.

To unblock: add the 8 `.json` files (or point me at them) and provide/confirm the n8n environment.

**Assumptions in the specs to confirm:** T1.7 (`Gmail_Operations` = ack reply + `AR/processed` label), T1.8 (only `billing` is alert-critical), model defaults in T1.15.

---

## Phase 0 — Repository scaffolding & standards

Establishes the structure every later task writes into. No workflow logic yet.

- [x] **T0.1** Create the repo directory layout from README: `docs/`, `workflows/<name>/` for all 8 workflows. — deps: none
- [x] **T0.2** Move `prd.md` to `docs/PRD.md`; update the link in the root `README.md`. — deps: T0.1 · _(also renamed root README to `README.md`; README already linked `docs/PRD.md`)_
- [x] **T0.3** Add `LICENSE` (MIT) at repo root. — deps: T0.1
- [ ] **T0.4** Place each skeleton `.json` export into its `workflows/<name>/` folder with the filename given in the README. — deps: T0.1 · **BLOCKED — skeleton JSON exports are not in this repo; user must supply them.**
- [x] **T0.5** Create a stub `README.md` in each of the 8 workflow folders with the standard section headings (overview, tech stack, node reference, required credentials, known gaps, setup steps). — deps: T0.1
- [x] **T0.6** Write `docs/LANGCHAIN_WIRING_CHECKLIST.md` (filled beyond a skeleton — also covers T3.1–T3.5 documentation). — deps: T0.1
- [x] **T0.7** Initialise git repo, add `.gitignore` (exclude credential exports, `.env`), commit the scaffold. — deps: T0.1–T0.5

---

## Phase 1 — Decisions & specifications (no build work proceeds without these)

Pure decision/documentation tasks. Each unblocks concrete build work later.

### Blocking decisions

- [x] **T1.1 (BLOCKING)** Macro vector store → **Supabase** (pgvector). Recorded in [`workflows/macro-thematic-ideation/README.md`](workflows/macro-thematic-ideation/README.md) + checklist §2.4 note.
- [x] **T1.2 (BLOCKING)** "Flagged" → **LLM classifier decides** (`verdict ∈ {scam,junk}` & `confidence ≥ 0.9`). Recorded in [`workflows/data-sanitization-cron/README.md`](workflows/data-sanitization-cron/README.md); classifier schema in [`docs/SCHEMAS.md`](docs/SCHEMAS.md) T1.2.
- [x] **T1.3 (BLOCKING)** Safeguard → **both**: dry-run for first N runs, then Telegram approve/deny gate. Recorded in the workflow README + [`docs/STANDARDS.md`](docs/STANDARDS.md) T1.15.

### Output & taxonomy schemas (one task each — these become the agents' structured output contracts)

Drafted in [`docs/SCHEMAS.md`](docs/SCHEMAS.md). Mark `[x]` once the user confirms each; T1.7 and T1.8 embed choices the user may want to change.

- [x] **T1.4** SQL Data Governance Agent: structured JSON verdict schema — [`docs/SCHEMAS.md#t14`](docs/SCHEMAS.md).
- [x] **T1.5** Analyst Screening Pipeline: extraction schema + scoring/ranking rubric — [`docs/SCHEMAS.md#t15`](docs/SCHEMAS.md).
- [x] **T1.6** Automated Accounts Receivable: invoice extraction schema + pre-ledger validation rules — [`docs/SCHEMAS.md#t16`](docs/SCHEMAS.md).
- [x] **T1.7** Automated Accounts Receivable: `Gmail_Operations` spec'd as ack-reply + label — [`docs/SCHEMAS.md#t17`](docs/SCHEMAS.md). _(assumption — confirm)_
- [x] **T1.8** Corporate Comms Triage: closed taxonomy `{billing*, project_update, spam, other}`, `billing` = critical — [`docs/SCHEMAS.md#t18`](docs/SCHEMAS.md). _(assumption — confirm critical set)_
- [x] **T1.9** Investor Relations NLP: executive summary schema — [`docs/SCHEMAS.md#t19`](docs/SCHEMAS.md).
- [x] **T1.10** Macro Thematic Ideation: retrieval contract (Supabase `match_documents` RPC) + ideation output schema — [`docs/SCHEMAS.md#t110`](docs/SCHEMAS.md).
- [x] **T1.11** Market Sentiment Engine: sentiment output schema — [`docs/SCHEMAS.md#t111`](docs/SCHEMAS.md).
- [x] **T1.12** Shared audit-log row schema — [`docs/SCHEMAS.md#t112`](docs/SCHEMAS.md).

### Cross-cutting standards

Drafted in [`docs/STANDARDS.md`](docs/STANDARDS.md).

- [x] **T1.13** Credential-scoping standard — [`docs/STANDARDS.md#t113`](docs/STANDARDS.md).
- [x] **T1.14** AI-node error-handling pattern — [`docs/STANDARDS.md#t114`](docs/STANDARDS.md).
- [x] **T1.15** Per-workflow cost-control knobs (Config node pattern) — [`docs/STANDARDS.md#t115`](docs/STANDARDS.md).

---

## Phase 2 — Data Sanitization Cron approval gate (highest priority fix)

PRD Section 6.1: fix and test this before any other workflow. Fully self-contained.

- [ ] **T2.1** Define the read-only Gmail credential scope used to fetch flagged mail (no delete scope on the fetch step). — deps: T1.2, T1.13
- [ ] **T2.2** Re-wire the graph: `Gmail_Fetch_Flagged → <approval/dry-run step> → Gmail_Delete_Op`; remove the direct fetch→delete edge. — deps: T1.3
- [ ] **T2.3** Implement the approval step: Telegram message listing each candidate (sender, subject, date, reason flagged) with explicit approve/deny action that gates `Gmail_Delete_Op`. — deps: T2.2
- [ ] **T2.4** Implement the dry-run config flag: when on, write candidates to the audit log and skip `Gmail_Delete_Op` entirely. — deps: T2.2, T1.12
- [ ] **T2.5** Add the post-delete audit-log write (what was deleted, when, why, who approved). — deps: T2.2, T1.12
- [ ] **T2.6** Add "Continue on Fail" + error branch to any AI/classification node in this workflow. — deps: T1.14
- [ ] **T2.7** Update `workflows/data-sanitization-cron/README.md`: trigger, "flagged" definition, safeguard design, dry-run instructions, required creds, known gaps. — deps: T2.2–T2.5
- [ ] **T2.8** Test end-to-end against 5–10 sample emails in **dry-run** mode; confirm no deletion occurs and the log is correct. — deps: T2.4, T2.5
- [ ] **T2.9** Test the approval path against 5–10 samples with a deliberate false positive; confirm deny prevents deletion. — deps: T2.3
- [ ] **T2.10** Sign-off: mark workflow ready for production creds. — deps: T2.7–T2.9

---

## Phase 3 — Shared LangChain wiring checklist (fix once, apply many times)

PRD 3.2–3.4, 6.2. Build the reusable pattern before touching the 5 affected workflows.

- [x] **T3.1** `docs/LANGCHAIN_WIRING_CHECKLIST.md` §1 — sub-connection types and what attaches with each. — deps: T0.6
- [x] **T3.2** Checklist §2.1 — per-workflow `ai_languageModel` fix map (PRD 3.2). — deps: T3.1
- [x] **T3.3** Checklist §2.2 — the `Bridge_Set_AgentInput` node spec for the 4 RAG workflows (PRD 3.3). — deps: T3.1
- [x] **T3.4** Checklist §2.3 — remove webhook→memory main edge, add `ai_memory` (PRD 3.4). — deps: T3.1
- [x] **T3.5** Checklist §2.1 note + §2.4 — orphaned `Gemini_Inference_Engine` / RAG helper wiring (PRD 3.8). — deps: T3.1
- [ ] **T3.6** Build one reference workflow JSON demonstrating the corrected RAG wiring (copy-source for the 4 clones). — deps: T3.2–T3.4 · **BLOCKED — needs the skeleton JSON (T0.4).**

---

## Phase 4 — Per-workflow build-out

Each workflow is independent once Phase 3 is done, except where noted. Order within the phase follows PRD Section 6 priorities (Comms Triage branching before live alerting; Macro after T1.1).

### 4A — SQL Data Governance Agent

- [ ] **T4A.1** Wire `ai_languageModel` / `ai_tool` / `ai_outputParser` into the agent per the checklist. — deps: T3.2
- [ ] **T4A.2** Add the batch loop-back connection on `Batch_Iterator`. — deps: T3.1
- [ ] **T4A.3** Create and enforce a read-only PostgreSQL role; point the workflow credential at it. — deps: T1.13
- [ ] **T4A.4** Implement the structured JSON verdict output parser using the T1.4 schema. — deps: T1.4, T4A.1
- [ ] **T4A.5** Add "Continue on Fail" + error branch to the agent. — deps: T1.14
- [ ] **T4A.6** Add audit-log write for any governance action recorded. — deps: T1.12
- [ ] **T4A.7** Update workflow README (node reference, creds, setup, known gaps). — deps: T4A.1–T4A.6
- [ ] **T4A.8** End-to-end test against 5–10 sample tables/checks. — deps: T4A.7

### 4B — Automated Accounts Receivable

- [ ] **T4B.1** Wire `Gemini_Inference_Engine → Quantitative_Data_Parser` via `ai_languageModel`. — deps: T3.5
- [ ] **T4B.2** Implement the invoice extraction schema (T1.6) as the parser's structured output. — deps: T1.6, T4B.1
- [ ] **T4B.3** Add the pre-`Master_Ledger_Update` validation node using T1.6 rules; route failures to an error branch. — deps: T1.6, T4B.2
- [ ] **T4B.4** Implement `Gmail_Operations` per the T1.7 decision. — deps: T1.7
- [ ] **T4B.5** Confirm PDF record generation (APITemplate.io) is wired and receives the extracted fields. — deps: T4B.2
- [ ] **T4B.6** Add audit-log write on every ledger update. — deps: T1.12
- [ ] **T4B.7** Move any inline API keys/connection strings into the n8n credential store. — deps: none
- [ ] **T4B.8** Add "Continue on Fail" + error branch to the parser. — deps: T1.14
- [ ] **T4B.9** Update workflow README. — deps: T4B.1–T4B.8
- [ ] **T4B.10** End-to-end test against 5–10 sample invoice emails, including one with a missing amount. — deps: T4B.9

### 4C — Corporate Comms Triage

- [ ] **T4C.1** Wire `Gemini_Inference_Engine` into both AI nodes (`NLP_Text_Classifier`, `LLM_Execution_Chain`) via `ai_languageModel`. — deps: T3.5
- [ ] **T4C.2** Constrain the classifier to the closed T1.8 taxonomy (no free-text categories). — deps: T1.8, T4C.1
- [ ] **T4C.3 (BLOCKING for live alerting)** Add `IF`/`Switch` node keyed on the classifier category so only critical categories reach `Telegram_Executive_Alert`. — deps: T1.8, T4C.2
- [ ] **T4C.4** Route non-critical categories to a no-op / log sink. — deps: T4C.3
- [ ] **T4C.5** Add "Continue on Fail" + error branch to both AI nodes. — deps: T1.14
- [ ] **T4C.6** Update workflow README. — deps: T4C.1–T4C.5
- [ ] **T4C.7** End-to-end test with a 5–10 message sample spanning all categories; confirm only critical ones alert. — deps: T4C.6

### 4D — Analyst Screening Pipeline (RAG clone #1)

- [ ] **T4D.1** Copy the corrected RAG wiring from the T3.6 reference into this workflow. — deps: T3.6
- [ ] **T4D.2** Apply PRD 3.3 bridge node so the webhook payload reaches `NLP_Financial_Agent`. — deps: T3.3, T4D.1
- [ ] **T4D.3** Apply PRD 3.4 memory fix (`ai_memory` to agent). — deps: T3.4, T4D.1
- [ ] **T4D.4** Write the screening-specific agent prompt + field extraction for T1.5 schema. — deps: T1.5, T4D.2
- [ ] **T4D.5** Add the scoring/ranking step producing a ranked shortlist before `Master_Ledger_Update`. — deps: T1.5, T4D.4
- [ ] **T4D.6** Wire Cohere embeddings + vector store (insert/query) to the agent via `ai_embedding` / `ai_vectorStore`. — deps: T4D.1
- [ ] **T4D.7** Add "Continue on Fail" + error branch; add audit-log write on ledger update. — deps: T1.14, T1.12
- [ ] **T4D.8** Apply cost-control knobs (batch size, model). — deps: T1.15
- [ ] **T4D.9** Update workflow README. — deps: T4D.1–T4D.8
- [ ] **T4D.10** End-to-end test against 5–10 sample resumes. — deps: T4D.9

### 4E — Investor Relations NLP (RAG clone #2)

- [ ] **T4E.1** Copy corrected RAG wiring from T3.6; apply 3.3 bridge and 3.4 memory fix. — deps: T3.6, T3.3, T3.4
- [ ] **T4E.2** Write the summarization/distillation prompt + extraction for the T1.9 summary schema. — deps: T1.9, T4E.1
- [ ] **T4E.3** Wire embeddings + vector store sub-connections. — deps: T4E.1
- [ ] **T4E.4** Add error branch + audit-log write (if it writes to the ledger). — deps: T1.14, T1.12
- [ ] **T4E.5** Apply cost-control knobs. — deps: T1.15
- [ ] **T4E.6** Update workflow README. — deps: T4E.1–T4E.5
- [ ] **T4E.7** End-to-end test against 5–10 sample stakeholder messages. — deps: T4E.6

### 4F — Macro Thematic Ideation (RAG clone #3)

- [ ] **T4F.1 (BLOCKING)** Confirm T1.1 decision; if Supabase, swap `vectorStorePinecone` nodes for Supabase vector nodes and update credential + query syntax. — deps: T1.1
- [ ] **T4F.2** Copy corrected RAG wiring; apply 3.3 bridge and 3.4 memory fix. — deps: T3.6, T3.3, T3.4, T4F.1
- [ ] **T4F.3** Write the macro/sector ideation prompt + retrieval contract for the T1.10 schema. — deps: T1.10, T4F.2
- [ ] **T4F.4** Wire embeddings + the chosen vector store via sub-connections. — deps: T4F.1, T4F.2
- [ ] **T4F.5** Add error branch + audit-log write (if applicable). — deps: T1.14, T1.12
- [ ] **T4F.6** Apply cost-control knobs. — deps: T1.15
- [ ] **T4F.7** Update workflow README so node types match prose (resolves PRD 3.5 documentation mismatch). — deps: T4F.1–T4F.6
- [ ] **T4F.8** End-to-end test against 5–10 sample research queries. — deps: T4F.7

### 4G — Market Sentiment Engine (RAG clone #4)

- [ ] **T4G.1** Copy corrected RAG wiring from T3.6; apply 3.3 bridge and 3.4 memory fix. — deps: T3.6, T3.3, T3.4
- [ ] **T4G.2** Write the sentiment-classification prompt + extraction for the T1.11 schema. — deps: T1.11, T4G.1
- [ ] **T4G.3** Wire Cohere embeddings + Pinecone insert/query via sub-connections. — deps: T4G.1
- [ ] **T4G.4** Add error branch + audit-log write (if applicable). — deps: T1.14, T1.12
- [ ] **T4G.5** Apply cost-control knobs. — deps: T1.15
- [ ] **T4G.6** Update workflow README. — deps: T4G.1–T4G.5
- [ ] **T4G.7** End-to-end test against 5–10 unstructured sentiment snippets; confirm output can feed the overlay. — deps: T4G.6

---

## Phase 5 — Cross-cutting NFR sweep (verify, don't assume)

Run after all workflows are built. Each task is a portfolio-wide audit.

- [ ] **T5.1** Secrets audit: grep all 8 JSON files for inline API keys / connection strings; confirm every one is a credential-store reference. — deps: Phase 4
- [ ] **T5.2** Credential-scoping audit: confirm every read-only use case uses a least-privilege credential and every destructive action has an approval or dry-run gate. — deps: Phase 4
- [ ] **T5.3** Error-handling audit: confirm every agent/chain/classifier/extractor node has "Continue on Fail" + a defined error branch. — deps: Phase 4
- [ ] **T5.4** Auditability audit: confirm every `Master_Ledger_Update` write and every delete emits a per-action log row matching the T1.12 schema. — deps: Phase 4
- [ ] **T5.5** Cost-control audit: confirm batch size and model choice are tunable per workflow, especially the 4 webhook RAG workflows. — deps: Phase 4
- [ ] **T5.6** Documentation-parity audit: for each workflow, diff README node references against actual JSON node types; fix mismatches. — deps: Phase 4

---

## Phase 6 — Testing & rollout (portfolio-wide)

PRD Section 6. Data Sanitization Cron (Phase 2) is already signed off before this phase.

- [ ] **T6.1** Confirm T2.10 sign-off still holds after any shared-wiring changes touched that workflow. — deps: Phase 2, Phase 3
- [ ] **T6.2** Run each remaining workflow end-to-end against its 5–10 item sample on **test** credentials; record pass/fail + notes. — deps: Phase 4, Phase 5
- [ ] **T6.3** Fix any failures from T6.2; re-run. — deps: T6.2
- [ ] **T6.4** Corporate Comms Triage: verify T4C.3 branching in a staging run before enabling live alerting. — deps: T4C.7
- [ ] **T6.5** Swap each workflow from test to production credentials/mailboxes one at a time; smoke-test after each. — deps: T6.3, T6.4
- [ ] **T6.6** Update the status column in the root `README.md` workflow table to reflect shipped state. — deps: T6.5

---

## Phase 7 — Documentation close-out

- [ ] **T7.1** Confirm `docs/PRD.md` is the single source of truth for Section 3 findings and no workflow README duplicates them (each links back). — deps: Phase 4
- [ ] **T7.2** Each workflow README covers: overview, tech stack, node reference, required credentials, known gaps, setup steps. — deps: Phase 4
- [ ] **T7.3** Root README setup steps verified against the finished workflows. — deps: T6.6
- [ ] **T7.4** Final commit + tag portfolio v1. — deps: T7.1–T7.3

---

## Dependency summary (critical path)

```
T1.1 ─────────────► T4F.1 ► T4F.* (Macro build)
T1.2 ► T1.3 ► Phase 2 (Data Sanitization — do first) ► T2.10
T0.6 ► T3.1 ► T3.2–T3.6 ► Phase 4 per-workflow builds
Phase 4 ► Phase 5 (NFR sweep) ► Phase 6 (rollout) ► Phase 7
T1.8 ► T4C.2 ► T4C.3 ► T6.4 (gate live alerting)
```
