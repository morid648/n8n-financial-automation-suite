#!/usr/bin/env python3
"""Generate corrected n8n workflow JSON for the 8-workflow suite.

Applies the fixes from docs/PRD.md section 3 and docs/LANGCHAIN_WIRING_CHECKLIST.md:
- every agent/chain gets an ai_languageModel sub-connection (3.2 / 3.8)
- RAG agents get a real main-path input via a bridge Set node (3.3)
- memory attaches via ai_memory, not main (3.4)
- Macro Thematic Ideation uses Supabase, not Pinecone (3.5 / T1.1)
- Corporate Comms Triage branches by category before alerting (3.6)
- Data Sanitization Cron: classifier + dry-run + approval gate before delete (3.7 / T1.2 / T1.3)
- every AI node has onError -> error branch; every ledger/delete writes an audit row
"""
import json
import os

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workflows")

SHEET = {"__rl": True, "value": "REPLACE_SHEET_ID", "mode": "id"}


def node(nid, name, ntype, tv, pos, params=None, creds=None, notes=None, extra=None):
    n = {"id": nid, "name": name, "type": ntype, "typeVersion": tv, "position": pos,
         "parameters": params or {}}
    if creds:
        n["credentials"] = creds
    if notes:
        n["notes"] = notes
    if extra:
        n.update(extra)
    return n


def audit_append(nid, name, pos, mapping):
    return node(nid, name, "n8n-nodes-base.googleSheets", 4.5, pos, {
        "operation": "append",
        "documentId": SHEET,
        "sheetName": {"__rl": True, "value": "audit_log", "mode": "list"},
        "columns": {"mappingMode": "defineBelow", "value": mapping},
        "options": {},
    }, {"googleSheetsOAuth2Api": {"id": "REPLACE_SHEETS_CRED", "name": "Google Sheets (ledger)"}})


def audit_row(workflow, action, target_expr, reason_expr, outcome="success", approver_expr=""):
    return {
        "ts": "={{ $now.toISO() }}",
        "workflow": workflow,
        "run_id": "={{ $execution.id }}",
        "action": action,
        "target": target_expr,
        "reason": reason_expr,
        "actor": "system",
        "approved_by": approver_expr,
        "outcome": outcome,
        "detail": "",
    }


def wf(name, description, nodes, connections, settings_extra=None):
    s = {"executionOrder": "v1", "saveDataErrorExecution": "all", "saveDataSuccessExecution": "all"}
    if settings_extra:
        s.update(settings_extra)
    return {"name": name, "meta": {"description": description}, "nodes": nodes,
            "connections": connections, "settings": s, "pinData": {}}


def write(folder, fname, obj):
    path = os.path.join(ROOT, folder, fname)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")
    json.load(open(path, encoding="utf-8"))  # validate
    print("wrote + validated:", path)


# --------------------------------------------------------------------------
# RAG TEMPLATE (Analyst / IR / Macro / Sentiment)
# --------------------------------------------------------------------------

def rag_workflow(*, name, folder, fname, description, path, vector_store,
                 index_name, namespace, config_assignments, system_message,
                 output_schema, tool_name, tool_desc, post_agent_nodes,
                 post_agent_connections, extra_nodes=None, extra_connections=None):
    """vector_store: 'pinecone' or 'supabase'."""
    if vector_store == "pinecone":
        vtype, vtv = "@n8n/n8n-nodes-langchain.vectorStorePinecone", 1.1
        vcred = {"pineconeApi": {"id": "REPLACE_PINECONE_CRED", "name": "Pinecone account"}}
        insert_params = {"mode": "insert",
                         "pineconeIndex": {"__rl": True, "value": index_name, "mode": "list"},
                         "options": {"pineconeNamespace": namespace}}
        retrieve_params = {"mode": "retrieve-as-tool", "toolName": tool_name,
                           "toolDescription": tool_desc,
                           "pineconeIndex": {"__rl": True, "value": index_name, "mode": "list"},
                           "topK": "={{ $('Workflow_Config').item.json.top_k }}",
                           "options": {"pineconeNamespace": namespace}}
    else:  # supabase
        vtype, vtv = "@n8n/n8n-nodes-langchain.vectorStoreSupabase", 1.1
        vcred = {"supabaseApi": {"id": "REPLACE_SUPABASE_CRED", "name": "Supabase account"}}
        insert_params = {"mode": "insert",
                         "tableName": {"__rl": True, "value": index_name, "mode": "list"},
                         "options": {"queryName": "match_documents"}}
        retrieve_params = {"mode": "retrieve-as-tool", "toolName": tool_name,
                           "toolDescription": tool_desc,
                           "tableName": {"__rl": True, "value": index_name, "mode": "list"},
                           "topK": "={{ $('Workflow_Config').item.json.top_k }}",
                           "options": {"queryName": "match_documents"}}

    nodes = [
        node("n-ingest", "Ingest_API_Payload", "n8n-nodes-base.webhook", 2, [-1180, 0], {
            "httpMethod": "POST", "path": path, "responseMode": "responseNode", "options": {}
        }, extra={"webhookId": path.replace("/", "-")}),
        node("n-config", "Workflow_Config", "n8n-nodes-base.set", 3.4, [-980, 0], {
            "assignments": {"assignments": config_assignments},
            "includeOtherFields": True, "options": {}
        }),
        node("n-gate", "Enabled_Gate", "n8n-nodes-base.if", 2.2, [-780, 0], {
            "conditions": {"options": {"version": 2, "typeValidation": "strict", "caseSensitive": True},
                           "combinator": "and",
                           "conditions": [{"id": "g1", "leftValue": "={{ $json.enabled }}",
                                           "rightValue": True,
                                           "operator": {"type": "boolean", "operation": "true", "singleValue": True}}]},
            "options": {}
        }),
        node("n-bridge", "Bridge_Agent_Input", "n8n-nodes-base.set", 3.4, [-560, -120], {
            "assignments": {"assignments": [
                {"id": "b1", "name": "text", "value": "={{ $json.body.text || $json.body.content || $json.body.message }}", "type": "string"},
                {"id": "b2", "name": "sessionId", "value": "={{ $json.body.sessionId || $json.body.id || $execution.id }}", "type": "string"},
                {"id": "b3", "name": "source_ref", "value": "={{ $json.body.source_ref || $json.body.id || $execution.id }}", "type": "string"},
            ]},
            "includeOtherFields": False, "options": {}
        }, notes="PRD 3.3 fix: gives NLP_Financial_Agent a real main-path input."),
        node("n-split", "Text_Chunking_Engine",
             "@n8n/n8n-nodes-langchain.textSplitterCharacterTextSplitter", 1, [-560, 300], {
                 "chunkSize": "={{ $('Workflow_Config').item.json.chunk_size }}",
                 "chunkOverlap": "={{ $('Workflow_Config').item.json.chunk_overlap }}", "options": {}
             }),
        node("n-loader", "Document_Loader",
             "@n8n/n8n-nodes-langchain.documentDefaultDataLoader", 1.1, [-380, 300], {
                 "jsonMode": "expressionData",
                 "jsonData": "={{ $('Bridge_Agent_Input').item.json.text }}",
                 "options": {"metadata": {"metadataValues": [
                     {"name": "source_ref", "value": "={{ $('Bridge_Agent_Input').item.json.source_ref }}"}]}}
             }),
        node("n-embed", "Cohere_Vector_Embeddings",
             "@n8n/n8n-nodes-langchain.embeddingsCohere", 1, [-180, 420],
             {"modelName": "embed-english-v3.0"},
             {"cohereApi": {"id": "REPLACE_COHERE_CRED", "name": "Cohere account"}}),
        node("n-vinsert", "Vector_DB_Insert", vtype, vtv, [-180, 180], insert_params, vcred),
        node("n-vretrieve", "Vector_Retrieval_Tool", vtype, vtv, [-360, -360], retrieve_params, vcred,
             notes="PRD 3.2 fix: orphaned vector store now reachable from the agent as a tool."),
        node("n-mem", "Context_Memory_Buffer",
             "@n8n/n8n-nodes-langchain.memoryBufferWindow", 1.3, [-180, -120], {
                 "sessionIdType": "customKey",
                 "sessionKey": "={{ $('Bridge_Agent_Input').item.json.sessionId }}",
                 "contextWindowLength": 10
             }, notes="PRD 3.4 fix: attaches via ai_memory, not the webhook main path."),
        node("n-llm", "LLM_Inference_Engine",
             "@n8n/n8n-nodes-langchain.lmChatAnthropic", 1.3, [-180, -360], {
                 "model": {"__rl": True, "value": "={{ $('Workflow_Config').item.json.model }}", "mode": "id"},
                 "options": {"maxTokensToSample": "={{ $('Workflow_Config').item.json.max_tokens }}", "temperature": 0}
             }, {"anthropicApi": {"id": "REPLACE_ANTHROPIC_CRED", "name": "Anthropic account"}},
             notes="PRD 3.2 fix: wired to the agent + retrieval tool via ai_languageModel."),
        node("n-parser", "Schema_Validation_Parser",
             "@n8n/n8n-nodes-langchain.outputParserStructured", 1.2, [40, -120],
             {"schemaType": "manual", "inputSchema": json.dumps(output_schema, indent=2)}),
        node("n-agent", "NLP_Financial_Agent",
             "@n8n/n8n-nodes-langchain.agent", 1.7, [280, -120], {
                 "promptType": "define", "text": "={{ $json.text }}",
                 "options": {"systemMessage": system_message}
             }),
    ]
    nodes += post_agent_nodes
    if extra_nodes:
        nodes += extra_nodes

    conn = {
        "Ingest_API_Payload": {"main": [[{"node": "Workflow_Config", "type": "main", "index": 0}]]},
        "Workflow_Config": {"main": [[{"node": "Enabled_Gate", "type": "main", "index": 0}]]},
        "Enabled_Gate": {"main": [
            [{"node": "Bridge_Agent_Input", "type": "main", "index": 0},
             {"node": "Vector_DB_Insert", "type": "main", "index": 0}],
            []
        ]},
        "Bridge_Agent_Input": {"main": [[{"node": "NLP_Financial_Agent", "type": "main", "index": 0}]]},
        "Text_Chunking_Engine": {"ai_textSplitter": [[{"node": "Document_Loader", "type": "ai_textSplitter", "index": 0}]]},
        "Document_Loader": {"ai_document": [[{"node": "Vector_DB_Insert", "type": "ai_document", "index": 0}]]},
        "Cohere_Vector_Embeddings": {"ai_embedding": [[
            {"node": "Vector_DB_Insert", "type": "ai_embedding", "index": 0},
            {"node": "Vector_Retrieval_Tool", "type": "ai_embedding", "index": 0}]]},
        "LLM_Inference_Engine": {"ai_languageModel": [[
            {"node": "NLP_Financial_Agent", "type": "ai_languageModel", "index": 0},
            {"node": "Vector_Retrieval_Tool", "type": "ai_languageModel", "index": 0}]]},
        "Context_Memory_Buffer": {"ai_memory": [[{"node": "NLP_Financial_Agent", "type": "ai_memory", "index": 0}]]},
        "Vector_Retrieval_Tool": {"ai_tool": [[{"node": "NLP_Financial_Agent", "type": "ai_tool", "index": 0}]]},
        "Schema_Validation_Parser": {"ai_outputParser": [[{"node": "NLP_Financial_Agent", "type": "ai_outputParser", "index": 0}]]},
        "NLP_Financial_Agent": {
            "main": [[{"node": post_agent_connections["first"], "type": "main", "index": 0}]],
            "onError": [[{"node": "Error_Context", "type": "main", "index": 0}]],
        },
    }
    conn.update(post_agent_connections["edges"])
    if extra_connections:
        conn.update(extra_connections)
    return wf(name, description, nodes, conn)


# error-branch nodes (Error_Context Set + Error_Audit_Write) shared by every workflow.
# Each workflow supplies its own workflow name / action / target / reason / detail expressions
# and node positions; the 10-field audit-row shape is identical everywhere.
def error_nodes(workflow, action, target_expr, reason_expr, pos_ctx, pos_audit, detail_expr=""):
    return [
        node("n-errctx", "Error_Context", "n8n-nodes-base.set", 3.4, list(pos_ctx), {
            "assignments": {"assignments": [
                {"id": "e1", "name": "ts", "value": "={{ $now.toISO() }}", "type": "string"},
                {"id": "e2", "name": "workflow", "value": workflow, "type": "string"},
                {"id": "e3", "name": "run_id", "value": "={{ $execution.id }}", "type": "string"},
                {"id": "e4", "name": "action", "value": action, "type": "string"},
                {"id": "e5", "name": "target", "value": target_expr, "type": "string"},
                {"id": "e6", "name": "reason", "value": reason_expr, "type": "string"},
                {"id": "e7", "name": "actor", "value": "system", "type": "string"},
                {"id": "e8", "name": "approved_by", "value": "", "type": "string"},
                {"id": "e9", "name": "outcome", "value": "failed", "type": "string"},
                {"id": "e10", "name": "detail", "value": detail_expr, "type": "string"},
            ]}, "options": {}
        }),
        audit_append("n-erraudit", "Error_Audit_Write", list(pos_audit), {
            "ts": "={{ $json.ts }}", "workflow": "={{ $json.workflow }}", "run_id": "={{ $json.run_id }}",
            "action": "={{ $json.action }}", "target": "={{ $json.target }}", "reason": "={{ $json.reason }}",
            "actor": "system", "approved_by": "", "outcome": "failed", "detail": "={{ $json.detail }}"
        }),
    ]


# error-branch nodes shared by RAG workflows (Error_Context + Error_Audit_Write + exec alert)
def rag_error_nodes(workflow):
    return error_nodes(
        workflow, "agent_failure",
        target_expr="={{ $('Bridge_Agent_Input').item.json.source_ref }}",
        reason_expr="={{ $json.error && $json.error.message ? $json.error.message : 'agent/parser error' }}",
        pos_ctx=(280, 140), pos_audit=(500, 140),
        detail_expr="={{ $json.error && $json.error.stack ? $json.error.stack : '' }}",
    ) + [
        node("n-erralert", "Trigger_Executive_Alert", "n8n-nodes-base.slack", 2.3, [720, 140], {
            "resource": "message", "operation": "post", "select": "channel",
            "channelId": {"__rl": True, "value": "REPLACE_SLACK_CHANNEL", "mode": "id"},
            "text": "=" + workflow + " run {{ $json.run_id }} failed: {{ $json.reason }}",
            "otherOptions": {}
        }, {"slackApi": {"id": "REPLACE_SLACK_CRED", "name": "Slack account"}}),
    ]


RAG_ERROR_EDGES = {
    "Error_Context": {"main": [[{"node": "Error_Audit_Write", "type": "main", "index": 0}]]},
    "Error_Audit_Write": {"main": [[{"node": "Trigger_Executive_Alert", "type": "main", "index": 0}]]},
}

CFG_RAG = lambda model, extra=None: [
    {"id": "c1", "name": "enabled", "value": True, "type": "boolean"},
    {"id": "c2", "name": "model", "value": model, "type": "string"},
    {"id": "c3", "name": "max_tokens", "value": 1200, "type": "number"},
    {"id": "c4", "name": "top_k", "value": 8, "type": "number"},
    {"id": "c5", "name": "chunk_size", "value": 400, "type": "number"},
    {"id": "c6", "name": "chunk_overlap", "value": 40, "type": "number"},
] + (extra or [])


def respond_node(pos=(1180, -120)):
    return node("n-respond", "Respond_To_Caller", "n8n-nodes-base.respondToWebhook", 1.1, list(pos),
                {"respondWith": "json", "responseBody": "={{ JSON.stringify($json) }}", "options": {}})


# ===== 2. Analyst Screening Pipeline =====
analyst_schema = {
    "type": "object",
    "required": ["candidate_id", "overall_years_experience", "skills"],
    "properties": {
        "candidate_id": {"type": "string"},
        "name": {"type": ["string", "null"]},
        "overall_years_experience": {"type": "number"},
        "skills": {
            "type": "object",
            "required": ["sql", "power_bi", "python", "excel_at_scale"],
            "properties": {k: {"$ref": "#/$defs/skillEvidence"} for k in
                           ["sql", "power_bi", "python", "excel_at_scale"]},
        },
    },
    "$defs": {"skillEvidence": {
        "type": "object", "required": ["present", "confidence"],
        "properties": {"present": {"type": "boolean"}, "years": {"type": ["number", "null"]},
                       "confidence": {"type": "number"}, "evidence": {"type": ["string", "null"]}}}},
}
analyst_post = [
    node("n-score", "Score_And_Rank", "n8n-nodes-base.code", 2, [500, -120], {
        "mode": "runOnceForEachItem", "language": "javaScript",
        "jsCode": (
            "const out = $json.output ?? $json;\n"
            "const s = out.skills || {};\n"
            "const cap = (v,c)=>Math.min(v,c);\n"
            "const comp=(ev,p,py,yc)=>{ if(!ev||!ev.present) return {raw:0,adj:0}; const raw=p+cap((ev.years||0)*py,yc); return {raw,adj:raw*(ev.confidence??0)}; };\n"
            "const sql=comp(s.sql,20,2,10), py=comp(s.python,20,2,10), pbi=comp(s.power_bi,14,2,6), xl=comp(s.excel_at_scale,10,0,0);\n"
            "const expRaw=cap(out.overall_years_experience||0,10);\n"
            "const score=sql.raw+py.raw+pbi.raw+xl.raw+expRaw;\n"
            "const confAdj=sql.adj+py.adj+pbi.adj+xl.adj+expRaw;\n"
            "const required=['sql','power_bi','python','excel_at_scale'];\n"
            "const missing=required.filter(k=>!(s[k]&&s[k].present));\n"
            "const th=$('Workflow_Config').item.json.recommend_score_threshold;\n"
            "return { candidate_id: out.candidate_id, name: out.name||null, score: Math.round(score), confidence_adjusted_score: Math.round(confAdj), recommend: score>=th && missing.length===0, missing_required_skills: missing, skills: s, screened_at: new Date().toISOString() };"
        )
    }),
    node("n-ledger", "Master_Ledger_Update", "n8n-nodes-base.googleSheets", 4.5, [720, -120], {
        "operation": "appendOrUpdate", "documentId": SHEET,
        "sheetName": {"__rl": True, "value": "shortlist", "mode": "list"},
        "columns": {"mappingMode": "autoMapInputData", "matchingColumns": ["candidate_id"]},
        "options": {}
    }, {"googleSheetsOAuth2Api": {"id": "REPLACE_SHEETS_CRED", "name": "Google Sheets (ledger)"}}),
    audit_append("n-audit", "Audit_Log_Write", [940, -120],
                 audit_row("analyst-screening-pipeline", "ledger_update",
                           "={{ $json.candidate_id }}",
                           "={{ 'score=' + $json.score + ' recommend=' + $json.recommend }}")),
    respond_node(),
]
analyst_post += rag_error_nodes("analyst-screening-pipeline")
analyst_conn = {
    "first": "Score_And_Rank",
    "edges": {
        "Score_And_Rank": {"main": [[{"node": "Master_Ledger_Update", "type": "main", "index": 0}]]},
        "Master_Ledger_Update": {"main": [[{"node": "Audit_Log_Write", "type": "main", "index": 0}]]},
        "Audit_Log_Write": {"main": [[{"node": "Respond_To_Caller", "type": "main", "index": 0}]]},
        **RAG_ERROR_EDGES,
    },
}
write("analyst-screening-pipeline", "Analyst_Screening_Pipeline.json", rag_workflow(
    name="Analyst_Screening_Pipeline", folder="analyst-screening-pipeline",
    fname="Analyst_Screening_Pipeline.json",
    description="RAG resume screening for quant roles. Extracts SQL/Power BI/Python/Excel evidence, scores and ranks, writes shortlist to the ledger. Corrected per PRD 3.1-3.4.",
    path="analyst-screening/intake", vector_store="pinecone", index_name="analyst-screening",
    namespace="resumes",
    config_assignments=CFG_RAG("claude-haiku-4-5",
                               [{"id": "c7", "name": "recommend_score_threshold", "value": 60, "type": "number"}]),
    system_message=("You are a technical screener for quantitative analyst roles. From the resume text, extract "
                    "structured evidence for exactly four skills: SQL, Power BI, Python (Pandas/NumPy), Excel at "
                    "scale (multi-million-row datasets).\n\n"
                    "- Use the resume_corpus_search tool to pull the candidate's exact phrasing before deciding.\n"
                    "- present=true only with concrete evidence (a project, a tool, a metric); a keyword list is present=false.\n"
                    "- confidence 0..1 reflects how direct the evidence is; evidence is a short verbatim quote or null.\n"
                    "- Never invent experience. Silence on a skill = present=false, high confidence.\n"
                    "Return only JSON matching the schema."),
    output_schema=analyst_schema,
    tool_name="resume_corpus_search",
    tool_desc="Semantic search over the ingested resume and comparable historical resumes; use for exact phrasing.",
    post_agent_nodes=analyst_post, post_agent_connections=analyst_conn,
))


# ===== 6. Investor Relations NLP =====
ir_schema = {
    "type": "object",
    "required": ["summary", "key_asks", "sentiment", "urgency", "suggested_owner"],
    "properties": {
        "summary": {"type": "string"},
        "key_asks": {"type": "array", "items": {"type": "string"}},
        "sentiment": {"enum": ["positive", "neutral", "concerned", "negative"]},
        "urgency": {"enum": ["low", "medium", "high"]},
        "suggested_owner": {"enum": ["IR", "CFO", "CEO", "Legal", "Comms", "Unassigned"]},
        "stakeholder": {"type": ["string", "null"]},
    },
}
ir_post = [
    node("n-flat", "Flatten_Summary", "n8n-nodes-base.set", 3.4, [500, -120], {
        "assignments": {"assignments": [
            {"id": "f1", "name": "source_ref", "value": "={{ $('Bridge_Agent_Input').item.json.source_ref }}", "type": "string"},
            {"id": "f2", "name": "summary", "value": "={{ ($json.output ?? $json).summary }}", "type": "string"},
            {"id": "f3", "name": "key_asks", "value": "={{ (($json.output ?? $json).key_asks || []).join(' | ') }}", "type": "string"},
            {"id": "f4", "name": "sentiment", "value": "={{ ($json.output ?? $json).sentiment }}", "type": "string"},
            {"id": "f5", "name": "urgency", "value": "={{ ($json.output ?? $json).urgency }}", "type": "string"},
            {"id": "f6", "name": "suggested_owner", "value": "={{ ($json.output ?? $json).suggested_owner }}", "type": "string"},
            {"id": "f7", "name": "stakeholder", "value": "={{ ($json.output ?? $json).stakeholder || '' }}", "type": "string"},
        ]}, "includeOtherFields": False, "options": {}
    }),
    node("n-ledger", "Master_Ledger_Update", "n8n-nodes-base.googleSheets", 4.5, [720, -120], {
        "operation": "appendOrUpdate", "documentId": SHEET,
        "sheetName": {"__rl": True, "value": "ir_summaries", "mode": "list"},
        "columns": {"mappingMode": "autoMapInputData", "matchingColumns": ["source_ref"]},
        "options": {}
    }, {"googleSheetsOAuth2Api": {"id": "REPLACE_SHEETS_CRED", "name": "Google Sheets (ledger)"}}),
    audit_append("n-audit", "Audit_Log_Write", [940, -120],
                 audit_row("investor-relations-nlp", "ledger_update", "={{ $json.source_ref }}",
                           "={{ 'sentiment=' + $json.sentiment + ' urgency=' + $json.urgency }}")),
    respond_node(),
]
ir_post += rag_error_nodes("investor-relations-nlp")
ir_conn = {
    "first": "Flatten_Summary",
    "edges": {
        "Flatten_Summary": {"main": [[{"node": "Master_Ledger_Update", "type": "main", "index": 0}]]},
        "Master_Ledger_Update": {"main": [[{"node": "Audit_Log_Write", "type": "main", "index": 0}]]},
        "Audit_Log_Write": {"main": [[{"node": "Respond_To_Caller", "type": "main", "index": 0}]]},
        **RAG_ERROR_EDGES,
    },
}
write("investor-relations-nlp", "Investor_Relations_NLP.json", rag_workflow(
    name="Investor_Relations_NLP", folder="investor-relations-nlp", fname="Investor_Relations_NLP.json",
    description="Distills stakeholder communications into a structured executive summary (key asks, sentiment, urgency, owner). Corrected per PRD 3.1-3.4.",
    path="investor-relations/intake", vector_store="pinecone", index_name="investor-relations",
    namespace="stakeholder-comms",
    config_assignments=CFG_RAG("claude-sonnet-5"),
    system_message=("You distill investor-relations and stakeholder communications into a structured executive summary. "
                    "Use the ir_history_search tool to check how similar past asks were handled and who owned them.\n"
                    "- summary: <= 800 chars, factual, no spin.\n- key_asks: explicit requests only.\n"
                    "- sentiment: positive|neutral|concerned|negative.\n- urgency: low|medium|high.\n"
                    "- suggested_owner: IR|CFO|CEO|Legal|Comms|Unassigned.\nReturn only JSON matching the schema."),
    output_schema=ir_schema,
    tool_name="ir_history_search",
    tool_desc="Semantic search over prior IR correspondence and how it was routed/answered.",
    post_agent_nodes=ir_post, post_agent_connections=ir_conn,
))


# ===== 7. Macro Thematic Ideation (Supabase) =====
macro_schema = {
    "type": "object",
    "required": ["theme", "thesis", "supporting_points", "sectors_affected", "confidence"],
    "properties": {
        "theme": {"type": "string"},
        "thesis": {"type": "string"},
        "supporting_points": {"type": "array", "items": {
            "type": "object", "required": ["claim", "source_ref"],
            "properties": {"claim": {"type": "string"}, "source_ref": {"type": "string"}}}},
        "sectors_affected": {"type": "array", "items": {"type": "string"}},
        "time_horizon": {"enum": ["0-6m", "6-18m", "18m+"]},
        "confidence": {"type": "number"},
        "contradicting_evidence": {"type": ["string", "null"]},
    },
}
macro_post = [
    node("n-flat", "Flatten_Idea", "n8n-nodes-base.set", 3.4, [500, -120], {
        "assignments": {"assignments": [
            {"id": "f1", "name": "source_ref", "value": "={{ $('Bridge_Agent_Input').item.json.source_ref }}", "type": "string"},
            {"id": "f2", "name": "theme", "value": "={{ ($json.output ?? $json).theme }}", "type": "string"},
            {"id": "f3", "name": "thesis", "value": "={{ ($json.output ?? $json).thesis }}", "type": "string"},
            {"id": "f4", "name": "sectors_affected", "value": "={{ (($json.output ?? $json).sectors_affected || []).join(', ') }}", "type": "string"},
            {"id": "f5", "name": "time_horizon", "value": "={{ ($json.output ?? $json).time_horizon || '' }}", "type": "string"},
            {"id": "f6", "name": "confidence", "value": "={{ ($json.output ?? $json).confidence }}", "type": "number"},
            {"id": "f7", "name": "supporting_points_json", "value": "={{ JSON.stringify(($json.output ?? $json).supporting_points || []) }}", "type": "string"},
        ]}, "includeOtherFields": False, "options": {}
    }),
    node("n-ledger", "Master_Ledger_Update", "n8n-nodes-base.googleSheets", 4.5, [720, -120], {
        "operation": "append", "documentId": SHEET,
        "sheetName": {"__rl": True, "value": "macro_ideas", "mode": "list"},
        "columns": {"mappingMode": "autoMapInputData"}, "options": {}
    }, {"googleSheetsOAuth2Api": {"id": "REPLACE_SHEETS_CRED", "name": "Google Sheets (ledger)"}}),
    audit_append("n-audit", "Audit_Log_Write", [940, -120],
                 audit_row("macro-thematic-ideation", "ledger_insert", "={{ $json.source_ref }}",
                           "={{ 'theme=' + $json.theme + ' confidence=' + $json.confidence }}")),
    respond_node(),
]
macro_post += rag_error_nodes("macro-thematic-ideation")
macro_conn = {
    "first": "Flatten_Idea",
    "edges": {
        "Flatten_Idea": {"main": [[{"node": "Master_Ledger_Update", "type": "main", "index": 0}]]},
        "Master_Ledger_Update": {"main": [[{"node": "Audit_Log_Write", "type": "main", "index": 0}]]},
        "Audit_Log_Write": {"main": [[{"node": "Respond_To_Caller", "type": "main", "index": 0}]]},
        **RAG_ERROR_EDGES,
    },
}
write("macro-thematic-ideation", "Macro_Thematic_Ideation.json", rag_workflow(
    name="Macro_Thematic_Ideation", folder="macro-thematic-ideation", fname="Macro_Thematic_Ideation.json",
    description="RAG ideation over macro/sector data. Vector store = Supabase/pgvector (T1.1). Returns grounded research themes. Corrected per PRD 3.1-3.5.",
    path="macro-ideation/intake", vector_store="supabase", index_name="macro_documents",
    namespace="macro",
    config_assignments=CFG_RAG("claude-sonnet-5"),
    system_message=("You generate grounded macro/sector research themes. ALWAYS ground claims by calling the "
                    "macro_corpus_search tool; every supporting_point must cite a source_ref returned by that tool. "
                    "If retrieval does not support a claim, drop it. Include contradicting_evidence when the corpus "
                    "disagrees. Return only JSON matching the schema."),
    output_schema=macro_schema,
    tool_name="macro_corpus_search",
    tool_desc="Semantic search (Supabase match_documents RPC) over macro indicators, sector notes and prior research.",
    post_agent_nodes=macro_post, post_agent_connections=macro_conn,
))


# ===== 8. Market Sentiment Engine =====
sent_schema = {
    "type": "object",
    "required": ["score", "category", "source_snippet"],
    "properties": {
        "score": {"type": "number"},
        "category": {"enum": ["bullish", "bearish", "neutral", "mixed"]},
        "confidence": {"type": "number"},
        "entity": {"type": ["string", "null"]},
        "source_snippet": {"type": "string"},
    },
}
sent_post = [
    node("n-flat", "Flatten_Sentiment", "n8n-nodes-base.set", 3.4, [500, -120], {
        "assignments": {"assignments": [
            {"id": "f1", "name": "source_ref", "value": "={{ $('Bridge_Agent_Input').item.json.source_ref }}", "type": "string"},
            {"id": "f2", "name": "score", "value": "={{ ($json.output ?? $json).score }}", "type": "number"},
            {"id": "f3", "name": "category", "value": "={{ ($json.output ?? $json).category }}", "type": "string"},
            {"id": "f4", "name": "confidence", "value": "={{ ($json.output ?? $json).confidence }}", "type": "number"},
            {"id": "f5", "name": "entity", "value": "={{ ($json.output ?? $json).entity || '' }}", "type": "string"},
            {"id": "f6", "name": "source_snippet", "value": "={{ ($json.output ?? $json).source_snippet }}", "type": "string"},
            {"id": "f7", "name": "as_of", "value": "={{ $now.toISO() }}", "type": "string"},
        ]}, "includeOtherFields": False, "options": {}
    }),
    node("n-ledger", "Master_Ledger_Update", "n8n-nodes-base.googleSheets", 4.5, [720, -120], {
        "operation": "append", "documentId": SHEET,
        "sheetName": {"__rl": True, "value": "sentiment_scores", "mode": "list"},
        "columns": {"mappingMode": "autoMapInputData"}, "options": {}
    }, {"googleSheetsOAuth2Api": {"id": "REPLACE_SHEETS_CRED", "name": "Google Sheets (ledger)"}}),
    audit_append("n-audit", "Audit_Log_Write", [940, -120],
                 audit_row("market-sentiment-engine", "ledger_insert", "={{ $json.source_ref }}",
                           "={{ 'entity=' + $json.entity + ' score=' + $json.score }}")),
    respond_node(),
]
sent_post += rag_error_nodes("market-sentiment-engine")
sent_conn = {
    "first": "Flatten_Sentiment",
    "edges": {
        "Flatten_Sentiment": {"main": [[{"node": "Master_Ledger_Update", "type": "main", "index": 0}]]},
        "Master_Ledger_Update": {"main": [[{"node": "Audit_Log_Write", "type": "main", "index": 0}]]},
        "Audit_Log_Write": {"main": [[{"node": "Respond_To_Caller", "type": "main", "index": 0}]]},
        **RAG_ERROR_EDGES,
    },
}
write("market-sentiment-engine", "Market_Sentiment_Engine.json", rag_workflow(
    name="Market_Sentiment_Engine", folder="market-sentiment-engine", fname="Market_Sentiment_Engine.json",
    description="Classifies unstructured sentiment via vector search into {score, category, source_snippet} for the SOTP/brand-equity overlay. Corrected per PRD 3.1-3.4.",
    path="market-sentiment/intake", vector_store="pinecone", index_name="market-sentiment",
    namespace="sentiment",
    config_assignments=CFG_RAG("claude-haiku-4-5"),
    system_message=("You classify market/brand sentiment from unstructured text. Use sentiment_corpus_search to "
                    "compare against prior snippets about the same entity.\n"
                    "- score: -1..1 (negative..positive).\n- category: bullish|bearish|neutral|mixed.\n"
                    "- entity: ticker/brand/sector or null.\n- source_snippet: the most representative <=500-char quote.\n"
                    "Return only JSON matching the schema."),
    output_schema=sent_schema,
    tool_name="sentiment_corpus_search",
    tool_desc="Semantic search over prior sentiment snippets and their scores for the same entity.",
    post_agent_nodes=sent_post, post_agent_connections=sent_conn,
))

print("RAG workflows done.")


# --------------------------------------------------------------------------
# 3. Automated Accounts Receivable
# --------------------------------------------------------------------------
ar_schema = {
    "type": "object",
    "required": ["invoice_number", "vendor", "amount", "currency", "due_date"],
    "properties": {
        "invoice_number": {"type": "string"},
        "vendor": {"type": "string"},
        "amount": {"type": "number"},
        "currency": {"type": "string"},
        "invoice_date": {"type": ["string", "null"]},
        "due_date": {"type": "string"},
        "po_number": {"type": ["string", "null"]},
        "extraction_confidence": {"type": "number"},
    },
}
ar_nodes = [
    node("n-trigger", "Ingest_Inbox_Stream", "n8n-nodes-base.gmailTrigger", 1.2, [-1180, -20], {
        "pollTimes": {"item": [{"mode": "everyMinute"}]},
        "simple": False,
        "filters": {"labelIds": ["INBOX"], "q": "subject:(invoice OR statement) has:attachment newer_than:30d"},
        "options": {}
    }, {"gmailOAuth2": {"id": "REPLACE_GMAIL_READ_CRED", "name": "Gmail (AR read)"}}),
    node("n-config", "Workflow_Config", "n8n-nodes-base.set", 3.4, [-980, -20], {
        "assignments": {"assignments": [
            {"id": "c1", "name": "enabled", "value": True, "type": "boolean"},
            {"id": "c2", "name": "model", "value": "gemini-2.0-flash", "type": "string"},
            {"id": "c3", "name": "min_extraction_confidence", "value": 0.7, "type": "number"},
            {"id": "c4", "name": "amount_sanity_cap", "value": 10000000, "type": "number"},
            {"id": "c5", "name": "currency_allowlist", "value": "USD,EUR,GBP,INR,SGD", "type": "string"},
        ]}, "includeOtherFields": True, "options": {}
    }),
    node("n-gate", "Enabled_Gate", "n8n-nodes-base.if", 2.2, [-780, -20], {
        "conditions": {"options": {"version": 2, "typeValidation": "strict", "caseSensitive": True},
                       "combinator": "and",
                       "conditions": [{"id": "g1", "leftValue": "={{ $json.enabled }}", "rightValue": True,
                                       "operator": {"type": "boolean", "operation": "true", "singleValue": True}}]},
        "options": {}
    }),
    node("n-gemini", "Gemini_Inference_Engine", "@n8n/n8n-nodes-langchain.lmChatGoogleGemini", 1, [-560, 200], {
        "modelName": "={{ $('Workflow_Config').item.json.model }}",
        "options": {"temperature": 0}
    }, {"googlePalmApi": {"id": "REPLACE_GEMINI_CRED", "name": "Google Gemini account"}},
       notes="PRD 3.8 fix: wired to Quantitative_Data_Parser via ai_languageModel."),
    node("n-parser", "Quantitative_Data_Parser", "@n8n/n8n-nodes-langchain.informationExtractor", 1.1, [-560, -20], {
        "text": "={{ $json.text || $json.snippet || $json.textPlain || $json.textHtml }}",
        "schemaType": "manual",
        "inputSchema": json.dumps(ar_schema, indent=2),
        "options": {"systemPromptTemplate": "Extract invoice fields exactly as written. amount is a number with no currency symbol or thousands separators. currency is a 3-letter ISO code. Dates are ISO-8601 (YYYY-MM-DD). extraction_confidence is your 0..1 confidence that every required field is correct. Do not guess a missing amount or due date."}
    }),
    node("n-validate", "Pre_Ledger_Validation", "n8n-nodes-base.code", 2, [-340, -20], {
        "mode": "runOnceForEachItem", "language": "javaScript",
        "jsCode": (
            "const d = $json.output ?? $json;\n"
            "const cfg = $('Workflow_Config').item.json;\n"
            "const allow = String(cfg.currency_allowlist).split(',').map(s=>s.trim());\n"
            "const errors = [];\n"
            "if (!d.invoice_number) errors.push('missing invoice_number');\n"
            "if (typeof d.amount !== 'number' || !(d.amount > 0)) errors.push('amount missing or not positive');\n"
            "if (d.amount > cfg.amount_sanity_cap) errors.push('amount exceeds sanity cap');\n"
            "if (!allow.includes(d.currency)) errors.push('currency not in allowlist');\n"
            "const due = Date.parse(d.due_date);\n"
            "if (Number.isNaN(due)) errors.push('due_date unparseable');\n"
            "if (!d.vendor) errors.push('missing vendor');\n"
            "if ((d.extraction_confidence ?? 0) < cfg.min_extraction_confidence) errors.push('low extraction confidence');\n"
            "return { ...d, source_email_id: $('Ingest_Inbox_Stream').item.json.id, valid: errors.length === 0, validation_errors: errors.join('; ') };"
        )
    }),
    node("n-if", "Valid_Invoice", "n8n-nodes-base.if", 2.2, [-120, -20], {
        "conditions": {"options": {"version": 2, "typeValidation": "strict", "caseSensitive": True},
                       "combinator": "and",
                       "conditions": [{"id": "v1", "leftValue": "={{ $json.valid }}", "rightValue": True,
                                       "operator": {"type": "boolean", "operation": "true", "singleValue": True}}]},
        "options": {}
    }),
    node("n-pdf", "Generate_PDF_Record", "n8n-nodes-base.apiTemplateIo", 1, [120, -120], {
        "resource": "pdf", "jsonData": "={{ JSON.stringify($json) }}",
        "additionalFields": {}
    }, {"apiTemplateIoApi": {"id": "REPLACE_APITEMPLATE_CRED", "name": "APITemplate.io account"}}),
    node("n-gmailops", "Gmail_Operations", "n8n-nodes-base.gmail", 2.1, [340, -120], {
        "operation": "reply",
        "messageId": "={{ $('Ingest_Inbox_Stream').item.json.id }}",
        "message": "Thank you — your invoice {{ $json.invoice_number }} has been received and recorded. This is an automated acknowledgement from Accounts Receivable.",
        "options": {"appendAttribution": False}
    }, {"gmailOAuth2": {"id": "REPLACE_GMAIL_SEND_CRED", "name": "Gmail (AR send/label)"}},
       notes="T1.7: sends a plain-text acknowledgement + applies label AR/processed (add a Gmail 'addLabels' step after this if the label op is preferred separately)."),
    node("n-ledger", "Master_Ledger_Update", "n8n-nodes-base.googleSheets", 4.5, [560, -120], {
        "operation": "appendOrUpdate", "documentId": SHEET,
        "sheetName": {"__rl": True, "value": "accounts_receivable", "mode": "list"},
        "columns": {"mappingMode": "autoMapInputData", "matchingColumns": ["invoice_number"]},
        "options": {}
    }, {"googleSheetsOAuth2Api": {"id": "REPLACE_SHEETS_CRED", "name": "Google Sheets (ledger)"}}),
    audit_append("n-audit-ok", "Audit_Log_Write", [780, -120],
                 audit_row("automated-accounts-receivable", "ledger_update",
                           "={{ $json.invoice_number }}",
                           "={{ 'amount=' + $json.amount + ' ' + $json.currency }}")),
    node("n-needs-review", "Flag_Needs_Review", "n8n-nodes-base.gmail", 2.1, [120, 120], {
        "operation": "addLabels",
        "messageId": "={{ $('Ingest_Inbox_Stream').item.json.id }}",
        "labelIds": ["Label_AR_needs_review"]
    }, {"gmailOAuth2": {"id": "REPLACE_GMAIL_SEND_CRED", "name": "Gmail (AR send/label)"}}),
    audit_append("n-audit-skip", "Audit_Log_Skip", [340, 120],
                 dict(audit_row("automated-accounts-receivable", "ledger_update",
                                "={{ $json.invoice_number || $json.source_email_id }}",
                                "={{ 'validation failed: ' + $json.validation_errors }}",
                                outcome="skipped"))),
] + error_nodes(
    "automated-accounts-receivable", "extractor_failure",
    target_expr="={{ $('Ingest_Inbox_Stream').item.json.id }}",
    reason_expr="={{ $json.error && $json.error.message ? $json.error.message : 'extractor error' }}",
    pos_ctx=(-340, 220), pos_audit=(-120, 220),
)
ar_conn = {
    "Ingest_Inbox_Stream": {"main": [[{"node": "Workflow_Config", "type": "main", "index": 0}]]},
    "Workflow_Config": {"main": [[{"node": "Enabled_Gate", "type": "main", "index": 0}]]},
    "Enabled_Gate": {"main": [[{"node": "Quantitative_Data_Parser", "type": "main", "index": 0}], []]},
    "Gemini_Inference_Engine": {"ai_languageModel": [[{"node": "Quantitative_Data_Parser", "type": "ai_languageModel", "index": 0}]]},
    "Quantitative_Data_Parser": {
        "main": [[{"node": "Pre_Ledger_Validation", "type": "main", "index": 0}]],
        "onError": [[{"node": "Error_Context", "type": "main", "index": 0}]],
    },
    "Pre_Ledger_Validation": {"main": [[{"node": "Valid_Invoice", "type": "main", "index": 0}]]},
    "Valid_Invoice": {"main": [
        [{"node": "Generate_PDF_Record", "type": "main", "index": 0}],
        [{"node": "Flag_Needs_Review", "type": "main", "index": 0}],
    ]},
    "Generate_PDF_Record": {"main": [[{"node": "Gmail_Operations", "type": "main", "index": 0}]]},
    "Gmail_Operations": {"main": [[{"node": "Master_Ledger_Update", "type": "main", "index": 0}]]},
    "Master_Ledger_Update": {"main": [[{"node": "Audit_Log_Write", "type": "main", "index": 0}]]},
    "Flag_Needs_Review": {"main": [[{"node": "Audit_Log_Skip", "type": "main", "index": 0}]]},
    "Error_Context": {"main": [[{"node": "Error_Audit_Write", "type": "main", "index": 0}]]},
}
write("automated-accounts-receivable", "Automated_Accounts_Receivable.json", wf(
    "Automated_Accounts_Receivable",
    "Parses invoice emails with Gemini, validates before the ledger, generates a PDF record, acknowledges the sender, updates the AR ledger. Corrected per PRD 3.8 + 5.3.",
    ar_nodes, ar_conn))


# --------------------------------------------------------------------------
# 4. Corporate Comms Triage
# --------------------------------------------------------------------------
CATS = [
    ("billing", "Invoices, payment failures, dunning notices, billing disputes, anything with a monetary amount owed or due."),
    ("project_update", "Status updates, meeting notes, deliverable notifications from known projects or colleagues."),
    ("spam", "Cold outreach, promotions, newsletters, phishing, anything unsolicited."),
    ("other", "Legitimate mail that is none of the above."),
]
comms_nodes = [
    node("n-trigger", "Ingest_Inbox_Stream", "n8n-nodes-base.gmailTrigger", 1.2, [-1180, 160], {
        "pollTimes": {"item": [{"mode": "everyMinute"}]}, "simple": False,
        "filters": {"labelIds": ["INBOX"]}, "options": {}
    }, {"gmailOAuth2": {"id": "REPLACE_GMAIL_READ_CRED", "name": "Gmail (comms read)"}}),
    node("n-config", "Workflow_Config", "n8n-nodes-base.set", 3.4, [-980, 160], {
        "assignments": {"assignments": [
            {"id": "c1", "name": "enabled", "value": True, "type": "boolean"},
            {"id": "c2", "name": "model", "value": "gemini-2.0-flash", "type": "string"},
            {"id": "c3", "name": "critical_categories", "value": "billing", "type": "string"},
        ]}, "includeOtherFields": True, "options": {}
    }),
    node("n-gate", "Enabled_Gate", "n8n-nodes-base.if", 2.2, [-780, 160], {
        "conditions": {"options": {"version": 2, "typeValidation": "strict", "caseSensitive": True},
                       "combinator": "and",
                       "conditions": [{"id": "g1", "leftValue": "={{ $json.enabled }}", "rightValue": True,
                                       "operator": {"type": "boolean", "operation": "true", "singleValue": True}}]},
        "options": {}
    }),
    node("n-gemini", "Gemini_Inference_Engine", "@n8n/n8n-nodes-langchain.lmChatGoogleGemini", 1, [-560, 420], {
        "modelName": "={{ $('Workflow_Config').item.json.model }}", "options": {"temperature": 0}
    }, {"googlePalmApi": {"id": "REPLACE_GEMINI_CRED", "name": "Google Gemini account"}},
       notes="PRD 3.8 fix: wired to BOTH NLP_Text_Classifier and LLM_Execution_Chain via ai_languageModel."),
    node("n-classifier", "NLP_Text_Classifier", "@n8n/n8n-nodes-langchain.textClassifier", 1, [-560, 160], {
        "inputText": "={{ $json.subject }}\n\n{{ $json.snippet || $json.textPlain }}",
        "categories": {"categories": [{"category": c, "description": d} for c, d in CATS]},
        "options": {"multiClass": False, "fallback": False}
    }, notes="Closed taxonomy (T1.8): billing, project_update, spam, other. One output per category."),
    node("n-chain", "LLM_Execution_Chain", "@n8n/n8n-nodes-langchain.chainLlm", 1.5, [40, 40], {
        "promptType": "define",
        "text": "=Write a 2-line executive alert for this BILLING email. Line 1: what is owed / what failed and the amount. Line 2: the sender and any deadline.\n\nSubject: {{ $json.subject }}\nBody: {{ $json.snippet || $json.textPlain }}",
        "messages": {"messageValues": [{"message": "You produce terse, factual finance alerts. No greetings, no filler."}]}
    }),
    node("n-alert", "Telegram_Executive_Alert", "n8n-nodes-base.telegram", 1.2, [280, 40], {
        "resource": "message", "operation": "sendMessage",
        "chatId": "REPLACE_TELEGRAM_CHAT_ID",
        "text": "=\U0001f6a8 Billing alert\n{{ $json.text }}",
        "additionalFields": {"appendAttribution": False}
    }, {"telegramApi": {"id": "REPLACE_TELEGRAM_CRED", "name": "Telegram bot"}}),
    node("n-sink", "NonCritical_Log_Sink", "n8n-nodes-base.noOp", 1, [40, 300],
         notes="project_update / spam / other terminate here (PRD 3.6 — only critical categories alert)."),
    audit_append("n-audit", "Classification_Audit", [280, 300], {
        "ts": "={{ $now.toISO() }}", "workflow": "corporate-comms-triage", "run_id": "={{ $execution.id }}",
        "action": "classified", "target": "={{ $('Ingest_Inbox_Stream').item.json.id }}",
        "reason": "={{ $json.category || 'non-critical' }}", "actor": "system", "approved_by": "",
        "outcome": "success", "detail": ""
    }),
] + error_nodes(
    "corporate-comms-triage", "classifier_failure",
    target_expr="={{ $('Ingest_Inbox_Stream').item.json.id }}",
    reason_expr="={{ $json.error && $json.error.message ? $json.error.message : 'classifier/chain error' }}",
    pos_ctx=(-560, 640), pos_audit=(-340, 640),
)
comms_conn = {
    "Ingest_Inbox_Stream": {"main": [[{"node": "Workflow_Config", "type": "main", "index": 0}]]},
    "Workflow_Config": {"main": [[{"node": "Enabled_Gate", "type": "main", "index": 0}]]},
    "Enabled_Gate": {"main": [[{"node": "NLP_Text_Classifier", "type": "main", "index": 0}], []]},
    "Gemini_Inference_Engine": {"ai_languageModel": [[
        {"node": "NLP_Text_Classifier", "type": "ai_languageModel", "index": 0},
        {"node": "LLM_Execution_Chain", "type": "ai_languageModel", "index": 0}]]},
    "NLP_Text_Classifier": {
        "main": [
            [{"node": "LLM_Execution_Chain", "type": "main", "index": 0}],   # billing (critical)
            [{"node": "NonCritical_Log_Sink", "type": "main", "index": 0}],  # project_update
            [{"node": "NonCritical_Log_Sink", "type": "main", "index": 0}],  # spam
            [{"node": "NonCritical_Log_Sink", "type": "main", "index": 0}],  # other
        ],
        "onError": [[{"node": "Error_Context", "type": "main", "index": 0}]],
    },
    "LLM_Execution_Chain": {
        "main": [[{"node": "Telegram_Executive_Alert", "type": "main", "index": 0}]],
        "onError": [[{"node": "Error_Context", "type": "main", "index": 0}]],
    },
    "Telegram_Executive_Alert": {"main": [[{"node": "Classification_Audit", "type": "main", "index": 0}]]},
    "NonCritical_Log_Sink": {"main": [[{"node": "Classification_Audit", "type": "main", "index": 0}]]},
    "Error_Context": {"main": [[{"node": "Error_Audit_Write", "type": "main", "index": 0}]]},
}
write("corporate-comms-triage", "Corporate_Comms_Triage.json", wf(
    "Corporate_Comms_Triage",
    "Classifies inbound mail into a closed taxonomy and alerts only on critical categories (billing). Corrected per PRD 3.6 + 3.8.",
    comms_nodes, comms_conn))


# --------------------------------------------------------------------------
# 5. Data Sanitization Cron  (highest-priority fix — PRD 3.7 / 6.1)
# --------------------------------------------------------------------------
sanit_schema = {
    "type": "object",
    "required": ["verdict", "confidence", "reason"],
    "properties": {
        "verdict": {"enum": ["scam", "junk", "legit"]},
        "confidence": {"type": "number"},
        "reason": {"type": "string"},
    },
}
sanit_nodes = [
    node("n-cron", "Chron_Scheduler", "n8n-nodes-base.scheduleTrigger", 1.2, [-1280, 80], {
        "rule": {"interval": [{"field": "hours", "hoursInterval": 6}]}
    }),
    node("n-config", "Workflow_Config", "n8n-nodes-base.set", 3.4, [-1080, 80], {
        "assignments": {"assignments": [
            {"id": "c1", "name": "enabled", "value": True, "type": "boolean"},
            {"id": "c2", "name": "dry_run", "value": True, "type": "boolean"},
            {"id": "c3", "name": "DRY_RUN_UNTIL", "value": 10, "type": "number"},
            {"id": "c4", "name": "model", "value": "gemini-2.0-flash", "type": "string"},
            {"id": "c5", "name": "min_confidence", "value": 0.9, "type": "number"},
            {"id": "c6", "name": "APPROVAL_TIMEOUT_HOURS", "value": 6, "type": "number"},
            {"id": "c7", "name": "fetch_query", "value": "in:inbox newer_than:7d -in:important -in:sent -in:starred", "type": "string"},
        ]}, "includeOtherFields": True, "options": {}
    }, notes="T1.3: dry_run flag is flipped to false by the operator after reviewing DRY_RUN_UNTIL runs of logged candidates."),
    node("n-gate", "Enabled_Gate", "n8n-nodes-base.if", 2.2, [-880, 80], {
        "conditions": {"options": {"version": 2, "typeValidation": "strict", "caseSensitive": True},
                       "combinator": "and",
                       "conditions": [{"id": "g1", "leftValue": "={{ $json.enabled }}", "rightValue": True,
                                       "operator": {"type": "boolean", "operation": "true", "singleValue": True}}]},
        "options": {}
    }),
    node("n-fetch", "Gmail_Fetch_Candidates", "n8n-nodes-base.gmail", 2.1, [-680, 80], {
        "operation": "getAll", "returnAll": False, "limit": 50,
        "filters": {"q": "={{ $('Workflow_Config').item.json.fetch_query }}"},
        "options": {}
    }, {"gmailOAuth2": {"id": "REPLACE_GMAIL_READONLY_CRED", "name": "Gmail (sanitization READ-ONLY)"}},
       notes="T1.13: this credential holds gmail.readonly ONLY. It cannot delete."),
    node("n-gemini", "Scam_Model", "@n8n/n8n-nodes-langchain.lmChatGoogleGemini", 1, [-480, 280], {
        "modelName": "={{ $('Workflow_Config').item.json.model }}", "options": {"temperature": 0}
    }, {"googlePalmApi": {"id": "REPLACE_GEMINI_CRED", "name": "Google Gemini account"}}),
    node("n-classify", "Scam_Classifier", "@n8n/n8n-nodes-langchain.informationExtractor", 1.1, [-480, 80], {
        "text": "=From: {{ $json.from && $json.from.value ? $json.from.value[0].address : $json.From }}\nSubject: {{ $json.subject || $json.Subject }}\n\n{{ $json.snippet || $json.textPlain || $json.text }}",
        "schemaType": "manual",
        "inputSchema": json.dumps(sanit_schema, indent=2),
        "options": {"systemPromptTemplate": "Classify the email. verdict='scam' for phishing/fraud/impersonation; 'junk' for unsolicited bulk/promotional with no value; 'legit' for anything a person might want. confidence is 0..1. reason is one sentence. Be conservative: when unsure, verdict='legit'."}
    }),
    node("n-merge", "Attach_Message_Id", "n8n-nodes-base.code", 2, [-280, 80], {
        "mode": "runOnceForEachItem", "language": "javaScript",
        "jsCode": (
            "const v = $json.output ?? $json;\n"
            "const src = $('Gmail_Fetch_Candidates').item.json;\n"
            "return { message_id: src.id, thread_id: src.threadId, subject: src.subject || src.Subject,\n"
            "         from: (src.from && src.from.value && src.from.value[0] && src.from.value[0].address) || src.From || '',\n"
            "         date: src.date || src.Date, verdict: v.verdict, confidence: v.confidence, reason: v.reason };"
        )
    }),
    node("n-filter", "Deletion_Candidate_Filter", "n8n-nodes-base.filter", 2.2, [-80, 80], {
        "conditions": {"options": {"version": 2, "typeValidation": "loose", "caseSensitive": True},
                       "combinator": "and",
                       "conditions": [
                           {"id": "f1", "leftValue": "={{ $json.verdict }}", "rightValue": "legit",
                            "operator": {"type": "string", "operation": "notEquals"}},
                           {"id": "f2", "leftValue": "={{ $json.confidence }}",
                            "rightValue": "={{ $('Workflow_Config').item.json.min_confidence }}",
                            "operator": {"type": "number", "operation": "gte"}},
                       ]},
        "options": {}
    }),
    node("n-dryif", "Dry_Run_Gate", "n8n-nodes-base.if", 2.2, [140, 80], {
        "conditions": {"options": {"version": 2, "typeValidation": "strict", "caseSensitive": True},
                       "combinator": "and",
                       "conditions": [{"id": "d1", "leftValue": "={{ $('Workflow_Config').item.json.dry_run }}",
                                       "rightValue": True,
                                       "operator": {"type": "boolean", "operation": "true", "singleValue": True}}]},
        "options": {}
    }),
    audit_append("n-audit-dry", "Audit_DryRun_Candidate", [360, -60], {
        "ts": "={{ $now.toISO() }}", "workflow": "data-sanitization-cron", "run_id": "={{ $execution.id }}",
        "action": "dry_run_candidate", "target": "={{ $json.message_id }}",
        "reason": "={{ $json.verdict + ' (' + $json.confidence + '): ' + $json.reason }}",
        "actor": "system", "approved_by": "", "outcome": "skipped", "detail": "={{ 'from=' + $json.from + ' subject=' + $json.subject }}"
    }),
    node("n-agg", "Aggregate_Candidates", "n8n-nodes-base.aggregate", 1, [360, 200], {
        "fieldsToAggregate": {"fieldToAggregate": [{"fieldToAggregate": "message_id"}, {"fieldToAggregate": "from"},
                                                    {"fieldToAggregate": "subject"}, {"fieldToAggregate": "confidence"},
                                                    {"fieldToAggregate": "reason"}]},
        "options": {}
    }),
    node("n-fmt", "Format_Approval_Message", "n8n-nodes-base.code", 2, [560, 200], {
        "mode": "runOnceForAllItems", "language": "javaScript",
        "jsCode": (
            "const rows = $json.message_id || [];\n"
            "if (!rows.length) return [{ json: { count: 0, text: 'No deletion candidates this run.' } }];\n"
            "const lines = rows.map((id,i)=>`${i+1}. ${$json.from[i]} — ${$json.subject[i]} (conf ${$json.confidence[i]}) — ${$json.reason[i]}`);\n"
            "return [{ json: { count: rows.length, message_ids: rows, text: `${rows.length} email(s) flagged for deletion:\\n\\n` + lines.join('\\n') + '\\n\\nApprove to delete all, Deny to keep all.' } }];"
        )
    }),
    node("n-approve", "Telegram_Approval_Gate", "n8n-nodes-base.telegram", 1.2, [760, 200], {
        "resource": "message", "operation": "sendAndWait",
        "chatId": "REPLACE_TELEGRAM_CHAT_ID",
        "message": "=⚠️ Data Sanitization — approval required\n\n{{ $json.text }}",
        "approvalOptions": {"values": {"approvalType": "double", "buttonApproveLabel": "Approve delete",
                                        "buttonDisapproveLabel": "Deny"}},
        "options": {"limitWaitTime": {"values": {"limitType": "afterTimeInterval",
                                                  "resumeAmount": "={{ $('Workflow_Config').item.json.APPROVAL_TIMEOUT_HOURS }}",
                                                  "resumeUnit": "hours"}}}
    }, {"telegramApi": {"id": "REPLACE_TELEGRAM_CRED", "name": "Telegram bot"}},
       notes="T1.3: nothing is deleted until a human approves. Timeout resumes as 'not approved'."),
    node("n-approved-if", "Was_Approved", "n8n-nodes-base.if", 2.2, [960, 200], {
        "conditions": {"options": {"version": 2, "typeValidation": "loose", "caseSensitive": True},
                       "combinator": "and",
                       "conditions": [{"id": "a1", "leftValue": "={{ $json.data && $json.data.approved }}",
                                       "rightValue": True,
                                       "operator": {"type": "boolean", "operation": "true", "singleValue": True}}]},
        "options": {}
    }),
    node("n-split", "Split_Approved", "n8n-nodes-base.splitOut", 1, [1160, 120], {
        "fieldToSplitOut": "message_ids", "include": "noOtherFields", "options": {}
    }),
    node("n-delete", "Gmail_Delete_Op", "n8n-nodes-base.gmail", 2.1, [1360, 120], {
        "operation": "delete", "messageId": "={{ $json.message_ids }}", "options": {}
    }, {"gmailOAuth2": {"id": "REPLACE_GMAIL_DELETE_CRED", "name": "Gmail (sanitization DELETE)"}},
       notes="T1.13: separate credential with https://mail.google.com/ scope, used ONLY here, downstream of the approval gate."),
    audit_append("n-audit-del", "Audit_Delete", [1560, 120], {
        "ts": "={{ $now.toISO() }}", "workflow": "data-sanitization-cron", "run_id": "={{ $execution.id }}",
        "action": "email_delete", "target": "={{ $json.message_ids }}", "reason": "classifier flagged, human approved",
        "actor": "system", "approved_by": "={{ $('Telegram_Approval_Gate').item.json.data.approverName || 'telegram-approver' }}",
        "outcome": "success", "detail": ""
    }),
    audit_append("n-audit-deny", "Audit_Denied", [1160, 320], {
        "ts": "={{ $now.toISO() }}", "workflow": "data-sanitization-cron", "run_id": "={{ $execution.id }}",
        "action": "email_delete", "target": "={{ ($json.message_ids || []).join(',') }}", "reason": "human denied deletion",
        "actor": "system", "approved_by": "", "outcome": "denied", "detail": ""
    }),
    node("n-notify", "Telegram_Run_Summary", "n8n-nodes-base.telegram", 1.2, [1760, 120], {
        "resource": "message", "operation": "sendMessage", "chatId": "REPLACE_TELEGRAM_CHAT_ID",
        "text": "=Data Sanitization run {{ $execution.id }} complete.",
        "additionalFields": {"appendAttribution": False}
    }, {"telegramApi": {"id": "REPLACE_TELEGRAM_CRED", "name": "Telegram bot"}}),
] + error_nodes(
    "data-sanitization-cron", "classifier_failure",
    target_expr="={{ $json.message_id || '' }}",
    reason_expr="={{ $json.error && $json.error.message ? $json.error.message : 'classifier error' }}",
    pos_ctx=(-280, 320), pos_audit=(-60, 320),
    detail_expr="no deletion attempted",
)
sanit_conn = {
    "Chron_Scheduler": {"main": [[{"node": "Workflow_Config", "type": "main", "index": 0}]]},
    "Workflow_Config": {"main": [[{"node": "Enabled_Gate", "type": "main", "index": 0}]]},
    "Enabled_Gate": {"main": [[{"node": "Gmail_Fetch_Candidates", "type": "main", "index": 0}], []]},
    "Gmail_Fetch_Candidates": {"main": [[{"node": "Scam_Classifier", "type": "main", "index": 0}]]},
    "Scam_Model": {"ai_languageModel": [[{"node": "Scam_Classifier", "type": "ai_languageModel", "index": 0}]]},
    "Scam_Classifier": {
        "main": [[{"node": "Attach_Message_Id", "type": "main", "index": 0}]],
        "onError": [[{"node": "Error_Context", "type": "main", "index": 0}]],
    },
    "Attach_Message_Id": {"main": [[{"node": "Deletion_Candidate_Filter", "type": "main", "index": 0}]]},
    "Deletion_Candidate_Filter": {"main": [[{"node": "Dry_Run_Gate", "type": "main", "index": 0}]]},
    "Dry_Run_Gate": {"main": [
        [{"node": "Audit_DryRun_Candidate", "type": "main", "index": 0}],
        [{"node": "Aggregate_Candidates", "type": "main", "index": 0}],
    ]},
    "Aggregate_Candidates": {"main": [[{"node": "Format_Approval_Message", "type": "main", "index": 0}]]},
    "Format_Approval_Message": {"main": [[{"node": "Telegram_Approval_Gate", "type": "main", "index": 0}]]},
    "Telegram_Approval_Gate": {"main": [[{"node": "Was_Approved", "type": "main", "index": 0}]]},
    "Was_Approved": {"main": [
        [{"node": "Split_Approved", "type": "main", "index": 0}],
        [{"node": "Audit_Denied", "type": "main", "index": 0}],
    ]},
    "Split_Approved": {"main": [[{"node": "Gmail_Delete_Op", "type": "main", "index": 0}]]},
    "Gmail_Delete_Op": {"main": [[{"node": "Audit_Delete", "type": "main", "index": 0}]]},
    "Audit_Delete": {"main": [[{"node": "Telegram_Run_Summary", "type": "main", "index": 0}]]},
    "Error_Context": {"main": [[{"node": "Error_Audit_Write", "type": "main", "index": 0}]]},
}
write("data-sanitization-cron", "Data_Sanitization_Cron.json", wf(
    "Data_Sanitization_Cron",
    "Scheduled mailbox hygiene. Classifier flags candidates; dry-run logs them, then a Telegram approve/deny gate precedes any delete. Read-only fetch credential is separate from the delete credential. Corrected per PRD 3.7 / 6.1 (blocking).",
    sanit_nodes, sanit_conn))


# --------------------------------------------------------------------------
# 1. SQL Data Governance Agent
# --------------------------------------------------------------------------
gov_schema = {
    "type": "object",
    "required": ["check_id", "table", "status", "severity", "row_count", "summary"],
    "properties": {
        "check_id": {"type": "string"}, "check_name": {"type": "string"},
        "table": {"type": "string"}, "column": {"type": ["string", "null"]},
        "status": {"enum": ["pass", "warn", "fail"]},
        "severity": {"enum": ["info", "low", "medium", "high", "critical"]},
        "row_count": {"type": "integer"},
        "metric": {"type": ["number", "null"]}, "threshold": {"type": ["number", "null"]},
        "summary": {"type": "string"}, "remediation": {"type": "string"},
    },
}
gov_nodes = [
    node("n-trigger", "Manual_Trigger", "n8n-nodes-base.manualTrigger", 1, [-1280, 0]),
    node("n-config", "Workflow_Config", "n8n-nodes-base.set", 3.4, [-1080, 0], {
        "assignments": {"assignments": [
            {"id": "c1", "name": "model", "value": "claude-sonnet-5", "type": "string"},
            {"id": "c2", "name": "max_batch_size", "value": 1, "type": "number"},
            {"id": "c3", "name": "max_tokens", "value": 1500, "type": "number"},
        ]}, "includeOtherFields": True, "options": {}
    }),
    node("n-checks", "Load_Check_Definitions", "n8n-nodes-base.code", 2, [-880, 0], {
        "mode": "runOnceForAllItems", "language": "javaScript",
        "jsCode": (
            "// Read-only data-quality checks. Each is a name + a SELECT the agent runs via the Postgres tool.\n"
            "const checks = [\n"
            "  { check_id: 'null_pct_customers_email', check_name: 'Null rate on customers.email', table: 'customers', column: 'email',\n"
            "    sql: \"SELECT count(*) FILTER (WHERE email IS NULL)::float / NULLIF(count(*),0) AS metric, count(*) AS total FROM customers\", threshold: 0.02 },\n"
            "  { check_id: 'orphan_orders_customer_id', check_name: 'Orders with no matching customer', table: 'orders', column: 'customer_id',\n"
            "    sql: \"SELECT count(*) AS metric FROM orders o LEFT JOIN customers c ON c.id = o.customer_id WHERE c.id IS NULL\", threshold: 0 },\n"
            "  { check_id: 'dup_invoice_number', check_name: 'Duplicate invoice numbers', table: 'invoices', column: 'invoice_number',\n"
            "    sql: \"SELECT count(*) AS metric FROM (SELECT invoice_number FROM invoices GROUP BY invoice_number HAVING count(*) > 1) d\", threshold: 0 },\n"
            "  { check_id: 'negative_amounts', check_name: 'Negative invoice amounts', table: 'invoices', column: 'amount',\n"
            "    sql: \"SELECT count(*) AS metric FROM invoices WHERE amount < 0\", threshold: 0 },\n"
            "  { check_id: 'future_dated_txns', check_name: 'Transactions dated in the future', table: 'transactions', column: 'txn_date',\n"
            "    sql: \"SELECT count(*) AS metric FROM transactions WHERE txn_date > now()\", threshold: 0 }\n"
            "];\n"
            "return checks.map(c => ({ json: c }));"
        )
    }),
    node("n-split", "Data_Splitter", "n8n-nodes-base.splitOut", 1, [-680, 0], {
        "fieldToSplitOut": "check_id,check_name,table,column,sql,threshold", "include": "allOtherFields", "options": {}
    }),
    node("n-batch", "Batch_Iterator", "n8n-nodes-base.splitInBatches", 3, [-460, 0], {
        "batchSize": "={{ $('Workflow_Config').item.json.max_batch_size }}", "options": {}
    }),
    node("n-llm", "LLM_Inference_Engine", "@n8n/n8n-nodes-langchain.lmChatAnthropic", 1.3, [-160, 220], {
        "model": {"__rl": True, "value": "={{ $('Workflow_Config').item.json.model }}", "mode": "id"},
        "options": {"maxTokensToSample": "={{ $('Workflow_Config').item.json.max_tokens }}", "temperature": 0}
    }, {"anthropicApi": {"id": "REPLACE_ANTHROPIC_CRED", "name": "Anthropic account"}},
       notes="PRD 3.2 fix: wired to the agent via ai_languageModel."),
    node("n-pg", "PostgreSQL_Query_Engine", "n8n-nodes-base.postgresTool", 2.5, [40, 220], {
        "operation": "executeQuery",
        "query": "={{ $fromAI('sql', 'A single read-only SELECT statement') }}",
        "options": {}
    }, {"postgres": {"id": "REPLACE_PG_READONLY_CRED", "name": "Postgres (READ-ONLY role)"}},
       notes="T1.13: credential must point at a role with SELECT only and default_transaction_read_only = on."),
    node("n-parser", "Schema_Validation_Parser", "@n8n/n8n-nodes-langchain.outputParserStructured", 1.2, [220, 220], {
        "schemaType": "manual", "inputSchema": json.dumps(gov_schema, indent=2)
    }),
    node("n-agent", "NLP_Financial_Agent", "@n8n/n8n-nodes-langchain.agent", 1.7, [-160, 0], {
        "promptType": "define",
        "text": "=Run this data-quality check and return the verdict.\n\ncheck_id: {{ $json.check_id }}\nname: {{ $json.check_name }}\ntable: {{ $json.table }}\ncolumn: {{ $json.column }}\ncandidate SQL: {{ $json.sql }}\nthreshold: {{ $json.threshold }}",
        "options": {"systemMessage": "You are a data-governance agent with READ-ONLY Postgres access via the PostgreSQL_Query_Engine tool. Run only SELECT statements — never INSERT/UPDATE/DELETE/DDL. Execute the candidate SQL (adjust only if it is not valid SELECT), compare the resulting metric against the threshold, and set status: pass if within threshold, warn if marginally over, fail if clearly over. Set severity by business impact. row_count = the violating/affected row count. Provide a one-paragraph summary and a concrete remediation. Return only JSON matching the schema."}
    }),
    node("n-collect", "Collect_Verdict", "n8n-nodes-base.set", 3.4, [120, 0], {
        "assignments": {"assignments": [
            {"id": "v1", "name": "verdict", "value": "={{ JSON.stringify($json.output ?? $json) }}", "type": "string"}
        ]}, "includeOtherFields": False, "options": {}
    }),
    node("n-agg", "Data_Aggregator", "n8n-nodes-base.aggregate", 1, [360, -120], {
        "fieldsToAggregate": {"fieldToAggregate": [{"fieldToAggregate": "verdict"}]}, "options": {}
    }),
    node("n-report", "Governance_Report_Write", "n8n-nodes-base.googleSheets", 4.5, [560, -120], {
        "operation": "append", "documentId": SHEET,
        "sheetName": {"__rl": True, "value": "governance_runs", "mode": "list"},
        "columns": {"mappingMode": "defineBelow", "value": {
            "ts": "={{ $now.toISO() }}", "run_id": "={{ $execution.id }}",
            "verdicts_json": "={{ JSON.stringify($json.verdict) }}"
        }}, "options": {}
    }, {"googleSheetsOAuth2Api": {"id": "REPLACE_SHEETS_CRED", "name": "Google Sheets (ledger)"}}),
    audit_append("n-audit", "Audit_Log_Write", [760, -120], {
        "ts": "={{ $now.toISO() }}", "workflow": "sql-data-governance-agent", "run_id": "={{ $execution.id }}",
        "action": "governance_run", "target": "={{ ($json.verdict || []).length + ' checks' }}",
        "reason": "manual run", "actor": "system", "approved_by": "", "outcome": "success", "detail": ""
    }),
] + error_nodes(
    "sql-data-governance-agent", "agent_failure",
    target_expr="={{ $json.check_id || '' }}",
    reason_expr="={{ $json.error && $json.error.message ? $json.error.message : 'agent error' }}",
    pos_ctx=(120, 200), pos_audit=(340, 200),
)
gov_conn = {
    "Manual_Trigger": {"main": [[{"node": "Workflow_Config", "type": "main", "index": 0}]]},
    "Workflow_Config": {"main": [[{"node": "Load_Check_Definitions", "type": "main", "index": 0}]]},
    "Load_Check_Definitions": {"main": [[{"node": "Data_Splitter", "type": "main", "index": 0}]]},
    "Data_Splitter": {"main": [[{"node": "Batch_Iterator", "type": "main", "index": 0}]]},
    "Batch_Iterator": {"main": [
        [{"node": "Data_Aggregator", "type": "main", "index": 0}],   # index 0 = done
        [{"node": "NLP_Financial_Agent", "type": "main", "index": 0}],  # index 1 = loop
    ]},
    "LLM_Inference_Engine": {"ai_languageModel": [[{"node": "NLP_Financial_Agent", "type": "ai_languageModel", "index": 0}]]},
    "PostgreSQL_Query_Engine": {"ai_tool": [[{"node": "NLP_Financial_Agent", "type": "ai_tool", "index": 0}]]},
    "Schema_Validation_Parser": {"ai_outputParser": [[{"node": "NLP_Financial_Agent", "type": "ai_outputParser", "index": 0}]]},
    "NLP_Financial_Agent": {
        "main": [[{"node": "Collect_Verdict", "type": "main", "index": 0}]],
        "onError": [[{"node": "Error_Context", "type": "main", "index": 0}]],
    },
    "Collect_Verdict": {"main": [[{"node": "Batch_Iterator", "type": "main", "index": 0}]]},
    "Data_Aggregator": {"main": [[{"node": "Governance_Report_Write", "type": "main", "index": 0}]]},
    "Governance_Report_Write": {"main": [[{"node": "Audit_Log_Write", "type": "main", "index": 0}]]},
    "Error_Context": {"main": [[{"node": "Error_Audit_Write", "type": "main", "index": 0}]]},
}
write("sql-data-governance-agent", "SQL_Data_Governance_Agent.json", wf(
    "SQL_Data_Governance_Agent",
    "LLM agent runs read-only SQL data-quality checks against PostgreSQL, one per batch, and returns a structured verdict. Corrected per PRD 3.2 + 5.1: language model + read-only Postgres tool + output parser wired; batch loop-back closed.",
    gov_nodes, gov_conn))

print("all 8 workflows generated.")

