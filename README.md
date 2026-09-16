# n8n Financial Automation Suite

A portfolio of 8 n8n workflows automating finance and data-analytics operations — from PostgreSQL data governance and RAG-based resume screening to accounts receivable, investor relations, and market sentiment analysis. Built by [Anshul](https://github.com/morid648).

Each workflow is exported as an importable n8n JSON file alongside its own README covering architecture, required credentials, and known gaps. A portfolio-level PRD ties the eight together and documents cross-cutting issues found across the set.

## 🎯 Purpose & Problem Statement

**Purpose:** Replace eight manual, finance-adjacent processes — data governance, resume screening, accounts receivable, comms triage, mailbox hygiene, investor relations summarization, macro research, and market sentiment tracking — with n8n workflows that use LLM agents, RAG retrieval, and structured extraction to do the work faster and more consistently.

**Problem:** These processes are currently done by hand or with disconnected tools, which doesn't scale and is inconsistent between operators. Several of them also feed directly into higher-stakes outputs — data governance and AR feed BI dashboards and DCF models, sentiment feeds valuation overlays — so upstream errors propagate downstream. Two of the workflows (ledger writes, mailbox deletion) involve actions that are hard to undo, which is why this repo treats "wire it up and ship it" as insufficient — see `docs/PRD.md` Section 1.2 for the full problem statement and Section 3.7 for where the current exports fall short of that bar.

## 📄 Start Here

**[`docs/PRD.md`](docs/PRD.md)** — the combined product requirements document. Read this first: it documents structural findings that apply across multiple workflows (a shared unfinished template, missing agent connections, a data-loss risk in the cron workflow) before you dive into any individual folder.

## 📁 Repository Structure

```
n8n-financial-automation-suite/
├── README.md                          ← you are here
├── LICENSE
├── docs/
│   └── PRD.md                         ← combined portfolio PRD
└── workflows/
    ├── sql-data-governance-agent/
    │   ├── SQL_Data_Governance_Agent.json
    │   └── README.md
    ├── analyst-screening-pipeline/
    │   ├── Analyst_Screening_Pipeline.json
    │   └── README.md
    ├── automated-accounts-receivable/
    │   ├── Automated_Accounts_Receivable.json
    │   └── README.md
    ├── corporate-comms-triage/
    │   ├── Corporate_Comms_Triage.json
    │   └── README.md
    ├── data-sanitization-cron/
    │   ├── Data_Sanitization_Cron.json
    │   └── README.md
    ├── investor-relations-nlp/
    │   ├── Investor_Relations_NLP.json
    │   └── README.md
    ├── macro-thematic-ideation/
    │   ├── Macro_Thematic_Ideation.json
    │   └── README.md
    └── market-sentiment-engine/
        ├── Market_Sentiment_Engine.json
        └── README.md
```

## 🗂️ Workflows

All 8 workflow JSONs are fully wired (agents, chains, classifiers, and extractors all have their `ai_languageModel`/`ai_memory` connections in place — see [tasks.md](tasks.md#execution-status) for the full structural changelog). What's left for every workflow is the same: import-testing against a live n8n instance with real credentials (each JSON ships with `REPLACE_*` placeholders) — not further wiring work.

| Workflow | Purpose | Status |
|---|---|---|
| [SQL Data Governance Agent](workflows/sql-data-governance-agent/) | LLM agent runs read-only SQL data-quality checks against PostgreSQL | Wired — needs live n8n import test |
| [Analyst Screening Pipeline](workflows/analyst-screening-pipeline/) | RAG-based resume screening for quant roles | Wired — needs live n8n import test |
| [Automated Accounts Receivable](workflows/automated-accounts-receivable/) | Parses invoice emails, generates PDF records, updates ledger | Wired — needs live n8n import test |
| [Corporate Comms Triage](workflows/corporate-comms-triage/) | Classifies inbound mail, alerts on critical items | Wired — category branching implemented |
| [Data Sanitization Cron](workflows/data-sanitization-cron/) | Scheduled mailbox cleanup of flagged/scam emails | Wired — classifier → dry-run gate → Telegram approve/deny → delete |
| [Investor Relations NLP](workflows/investor-relations-nlp/) | Distills stakeholder comms into executive summaries | Wired — needs live n8n import test |
| [Macro Thematic Ideation](workflows/macro-thematic-ideation/) | RAG retrieval over macro/sector data for research ideation | Wired — uses Supabase vector store |
| [Market Sentiment Engine](workflows/market-sentiment-engine/) | Classifies unstructured sentiment via vector search | Wired — needs live n8n import test |

## 🛠️ Tech Stack Across the Suite

- **Orchestration:** n8n
- **LLMs:** Anthropic Claude, Google Gemini
- **Embeddings / Vector Search:** Cohere embeddings, Pinecone
- **Database:** PostgreSQL
- **Integrations:** Gmail, Google Sheets, Slack, Telegram, APITemplate.io

## ⚙️ Setup

1. Import any workflow's `.json` file into your n8n instance (Workflows → Import from File).
2. Read that workflow's `README.md` for the specific credentials and connection fixes it needs — **none of these workflows are wired end-to-end as exported**; each README documents exactly what's missing.
3. Add the required credentials in n8n's credential store (never hardcode keys in node parameters).
4. Test each workflow against a small sample before connecting live data sources, especially [Data Sanitization Cron](workflows/data-sanitization-cron/), which performs an irreversible delete.

## 📌 Portfolio-Level Notes

- Four of the eight workflows (`analyst-screening-pipeline`, `investor-relations-nlp`, `macro-thematic-ideation`, `market-sentiment-engine`) currently share an identical technical skeleton — see `docs/PRD.md` Section 3.1. Each needs workflow-specific prompt design and output schemas layered on top before it reflects its stated purpose.
- All AI-agent nodes across the suite are missing their LangChain sub-connections (language model, tool, output parser, memory) — see `docs/PRD.md` Section 3.2.

## License

MIT — see [`LICENSE`](LICENSE).
