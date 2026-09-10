# Output & Taxonomy Schemas

Structured-output contracts for every AI node in the suite (tasks T1.4–T1.12). Each schema is the target for an `ai_outputParser` node. JSON Schema draft-2020-12 style; `required` means the parser must reject output missing that field.

---

## T1.4 — SQL Data Governance Agent: verdict schema

One object per check executed in the batch.

```json
{
  "type": "object",
  "required": ["check_id", "table", "status", "severity", "row_count", "summary"],
  "properties": {
    "check_id":    { "type": "string", "description": "stable slug, e.g. null_pct_customers_email" },
    "check_name":  { "type": "string" },
    "table":       { "type": "string" },
    "column":      { "type": ["string", "null"] },
    "status":      { "enum": ["pass", "warn", "fail"] },
    "severity":    { "enum": ["info", "low", "medium", "high", "critical"] },
    "row_count":   { "type": "integer", "description": "rows affected / violating" },
    "sample_rows": { "type": "array", "items": { "type": "object" }, "maxItems": 5 },
    "metric":      { "type": ["number", "null"], "description": "e.g. null percentage" },
    "threshold":   { "type": ["number", "null"] },
    "summary":     { "type": "string", "maxLength": 400 },
    "remediation": { "type": "string" },
    "checked_at":  { "type": "string", "format": "date-time" }
  }
}
```

Batch output: `{ "run_id": string, "checks": [ <verdict>, ... ], "overall": "pass|warn|fail" }`.

---

## T1.5 — Analyst Screening Pipeline: extraction + scoring schema

### Extraction (per candidate)

```json
{
  "type": "object",
  "required": ["candidate_id", "skills", "overall_years_experience"],
  "properties": {
    "candidate_id":  { "type": "string" },
    "name":          { "type": ["string", "null"] },
    "overall_years_experience": { "type": "number" },
    "skills": {
      "type": "object",
      "required": ["sql", "power_bi", "python", "excel_at_scale"],
      "properties": {
        "sql":            { "$ref": "#/$defs/skillEvidence" },
        "power_bi":       { "$ref": "#/$defs/skillEvidence" },
        "python":         { "$ref": "#/$defs/skillEvidence", "description": "Pandas / NumPy" },
        "excel_at_scale": { "$ref": "#/$defs/skillEvidence" }
      }
    }
  },
  "$defs": {
    "skillEvidence": {
      "type": "object",
      "required": ["present", "confidence"],
      "properties": {
        "present":     { "type": "boolean" },
        "years":       { "type": ["number", "null"] },
        "confidence":  { "type": "number", "minimum": 0, "maximum": 1 },
        "evidence":    { "type": ["string", "null"], "description": "verbatim snippet from resume" }
      }
    }
  }
}
```

### Scoring rubric (deterministic, applied in a Code node after extraction)

| Component | Weight | Rule |
|---|---|---|
| SQL | 30 | `present` → 20; `+2` per year capped at 10 |
| Python (Pandas/NumPy) | 30 | same shape as SQL |
| Power BI | 20 | `present` → 14; `+2`/yr capped at 6 |
| Excel at scale | 10 | `present` → 10 |
| Overall experience | 10 | `min(years, 10)` |

`score` = weighted sum (0–100). `confidence_adjusted_score` = each component × its `confidence` before summing. Ledger receives the shortlist ordered by `confidence_adjusted_score` desc, with `rank` (1..N) and a `recommend` flag (`score >= 60` and no required skill with `present=false`).

---

## T1.6 — Automated Accounts Receivable: invoice extraction + validation

```json
{
  "type": "object",
  "required": ["invoice_number", "vendor", "amount", "currency", "due_date"],
  "properties": {
    "invoice_number": { "type": "string" },
    "vendor":         { "type": "string" },
    "amount":         { "type": "number", "exclusiveMinimum": 0 },
    "currency":       { "type": "string", "pattern": "^[A-Z]{3}$" },
    "invoice_date":   { "type": ["string", "null"], "format": "date" },
    "due_date":       { "type": "string", "format": "date" },
    "po_number":      { "type": ["string", "null"] },
    "line_items":     { "type": "array", "items": { "type": "object" } },
    "source_email_id":{ "type": "string" },
    "extraction_confidence": { "type": "number", "minimum": 0, "maximum": 1 }
  }
}
```

### Pre-ledger validation rules (fail → error branch, do not write)

- `invoice_number` non-empty and not already in the ledger (dedupe).
- `amount` present, numeric, `> 0`, ≤ a configurable sanity cap (default 10,000,000).
- `currency` is a valid ISO-4217 code from the allow-list.
- `due_date` parses as a real date and is not more than N days in the past (default 365) or > 2 years future.
- `vendor` non-empty.
- `extraction_confidence >= 0.7` (else route to human review, not ledger).

---

## T1.7 — Automated Accounts Receivable: `Gmail_Operations` definition

**Decision:** `Gmail_Operations` sends a **plain-text acknowledgment reply** to the invoice sender confirming receipt, then applies the Gmail label `AR/processed`. It does **not** forward to a person and does **not** send payment confirmation. Triggered only after a successful ledger write; a validation failure instead applies label `AR/needs-review` and sends no reply.

---

## T1.8 — Corporate Comms Triage: category taxonomy

Closed set — classifier must return exactly one of these `category` values (no free text):

| category | critical? | routing |
|---|---|---|
| `billing` | yes | Telegram alert |
| `project_update` | no | log sink |
| `spam` | no | log sink |
| `other` | no | log sink |

`critical` categories → `Telegram_Executive_Alert`. Classifier output:

```json
{
  "type": "object",
  "required": ["category", "confidence", "reason"],
  "properties": {
    "category":   { "enum": ["billing", "project_update", "spam", "other"] },
    "confidence": { "type": "number", "minimum": 0, "maximum": 1 },
    "reason":     { "type": "string", "maxLength": 200 }
  }
}
```

Low confidence (`< 0.6`) on a non-critical category is still treated as non-critical; low confidence on `billing` still alerts (fail-safe toward alerting for the one critical category).

---

## T1.9 — Investor Relations NLP: executive summary schema

```json
{
  "type": "object",
  "required": ["summary", "key_asks", "sentiment", "urgency", "suggested_owner"],
  "properties": {
    "summary":        { "type": "string", "maxLength": 800 },
    "key_asks":       { "type": "array", "items": { "type": "string" }, "maxItems": 10 },
    "sentiment":      { "enum": ["positive", "neutral", "concerned", "negative"] },
    "urgency":        { "enum": ["low", "medium", "high"] },
    "suggested_owner":{ "enum": ["IR", "CFO", "CEO", "Legal", "Comms", "Unassigned"] },
    "stakeholder":    { "type": ["string", "null"] },
    "source_message_id": { "type": "string" }
  }
}
```

---

## T1.10 — Macro Thematic Ideation: retrieval contract + output schema

**Depends on T1.1 (Supabase vs Pinecone).** Retrieval query contract:

```json
{ "query_text": "string", "top_k": 8, "filters": { "sector": "string|null", "date_from": "date|null" } }
```

Output:

```json
{
  "type": "object",
  "required": ["theme", "thesis", "supporting_points", "sectors_affected", "confidence"],
  "properties": {
    "theme":            { "type": "string" },
    "thesis":           { "type": "string", "maxLength": 600 },
    "supporting_points":{ "type": "array", "items": {
        "type": "object",
        "required": ["claim", "source_ref"],
        "properties": { "claim": {"type":"string"}, "source_ref": {"type":"string"} } } },
    "sectors_affected": { "type": "array", "items": { "type": "string" } },
    "time_horizon":     { "enum": ["0-6m", "6-18m", "18m+"] },
    "confidence":       { "type": "number", "minimum": 0, "maximum": 1 },
    "contradicting_evidence": { "type": ["string", "null"] }
  }
}
```

---

## T1.11 — Market Sentiment Engine: sentiment schema

```json
{
  "type": "object",
  "required": ["score", "category", "source_snippet"],
  "properties": {
    "score":          { "type": "number", "minimum": -1, "maximum": 1 },
    "category":       { "enum": ["bullish", "bearish", "neutral", "mixed"] },
    "confidence":     { "type": "number", "minimum": 0, "maximum": 1 },
    "entity":         { "type": ["string", "null"], "description": "ticker / brand / sector" },
    "source_snippet": { "type": "string", "maxLength": 500 },
    "source_ref":     { "type": "string" },
    "as_of":          { "type": "string", "format": "date-time" }
  }
}
```

Feeds the SOTP / brand-equity overlay keyed on `entity` + `as_of`, aggregating `score` weighted by `confidence`.

---

## T1.12 — Shared audit-log row schema

Every workflow that writes to `Master_Ledger_Update` or deletes data emits one row per action (not just end state) to the audit sink (Google Sheet `audit_log` tab, or a dedicated table):

```json
{
  "type": "object",
  "required": ["ts", "workflow", "action", "target", "outcome"],
  "properties": {
    "ts":        { "type": "string", "format": "date-time" },
    "workflow":  { "type": "string", "description": "e.g. data-sanitization-cron" },
    "run_id":    { "type": "string" },
    "action":    { "enum": ["ledger_insert", "ledger_update", "email_delete", "email_ack", "dry_run_candidate"] },
    "target":    { "type": "string", "description": "invoice_number / gmail message id / ledger row key" },
    "reason":    { "type": "string" },
    "actor":     { "type": "string", "description": "\"system\" or approver identifier" },
    "approved_by": { "type": ["string", "null"] },
    "outcome":   { "enum": ["success", "skipped", "failed", "denied"] },
    "detail":    { "type": ["string", "null"] }
  }
}
```
