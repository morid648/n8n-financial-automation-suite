#!/usr/bin/env python3
"""Structural lint for the generated n8n workflows."""
import json, glob, os

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workflows")
AI_LM_CONSUMERS = {
    "@n8n/n8n-nodes-langchain.agent",
    "@n8n/n8n-nodes-langchain.chainLlm",
    "@n8n/n8n-nodes-langchain.textClassifier",
    "@n8n/n8n-nodes-langchain.informationExtractor",
}

problems = 0
for path in sorted(glob.glob(os.path.join(ROOT, "*", "*.json"))):
    wf = json.load(open(path, encoding="utf-8"))
    name = wf["name"]
    nodes = {n["name"]: n for n in wf["nodes"]}
    conns = wf["connections"]

    issues = []

    # 1. every connection target + source exists
    for src, outs in conns.items():
        if src not in nodes:
            issues.append(f"connection source '{src}' is not a node")
        for ctype, branches in outs.items():
            for branch in branches:
                for edge in branch:
                    if edge["node"] not in nodes:
                        issues.append(f"{src}.{ctype} -> missing node '{edge['node']}'")

    # 2. incoming edge map
    incoming = {n: set() for n in nodes}
    for src, outs in conns.items():
        for ctype, branches in outs.items():
            for branch in branches:
                for edge in branch:
                    if edge["node"] in incoming:
                        incoming[edge["node"]].add(ctype)

    # 3. every ai_languageModel consumer actually has one wired
    for nname, ninfo in nodes.items():
        ntype = ninfo["type"]
        if ntype in AI_LM_CONSUMERS:
            if "ai_languageModel" not in incoming[nname]:
                issues.append(f"'{nname}' ({ntype.split('.')[-1]}) has no ai_languageModel")
        if ntype == "@n8n/n8n-nodes-langchain.agent":
            if "main" not in incoming[nname]:
                issues.append(f"agent '{nname}' has no incoming main connection (PRD 3.3)")

    # 4. memory nodes must attach via ai_memory only, never main
    for nname, ninfo in nodes.items():
        ntype = ninfo["type"]
        if "memoryBufferWindow" in ntype:
            if "main" in incoming[nname]:
                issues.append(f"memory '{nname}' is on the main path (PRD 3.4)")
            if conns.get(nname) and "ai_memory" not in conns[nname]:
                issues.append(f"memory '{nname}' does not output ai_memory")

    # 5. orphan nodes (no incoming and no outgoing), triggers excluded
    for nname, ninfo in nodes.items():
        ntype = ninfo["type"]
        is_trigger = "rigger" in ntype or ntype.endswith("scheduleTrigger")
        has_out = nname in conns and any(conns[nname].values())
        has_in = bool(incoming[nname])
        if not is_trigger and not has_out and not has_in:
            issues.append(f"orphan node '{nname}'")

    # 6. every agent/classifier/extractor/chain has onError
    for nname, ninfo in nodes.items():
        ntype = ninfo["type"]
        if ntype in AI_LM_CONSUMERS:
            if "onError" not in conns.get(nname, {}):
                issues.append(f"'{nname}' has no onError branch (STANDARDS T1.14)")

    status = "OK" if not issues else f"{len(issues)} ISSUE(S)"
    print(f"\n== {name} :: {status}")
    for i in issues:
        print("   -", i)
    problems += len(issues)

print(f"\nTOTAL ISSUES: {problems}")
