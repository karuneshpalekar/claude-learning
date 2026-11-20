import json, os, sys
ORDER = [("agent-architecture",50),("agent-construction",50),("agent-patterns",100),("understanding-reqs",100),("systems-life-cycle",100),("claude-api-mechanics",100),("sw-eng-foundations",100),("claude-app-design",100),("config-management",100),("claude-code-operation",100),("debugging",100),("llm-fundamentals",75),("tech-fundamentals",100),("model-selection",100),("cost-token-management",100),("context-engineering",100),("prompt-engineering",100),("output-handling",100),("ai-app-security",100),("guardrails",100),("hooks",100),("identity-secrets",100),("tool-implementation",100),("mcp-dev",100),("agentic-customization",100)]
out=[]; issues=[]
for slug,score in ORDER:
    p=f"content/{slug}.json"
    if not os.path.exists(p): issues.append(f"MISSING {slug}"); continue
    d=json.load(open(p)); d["slug"]=slug; d["score"]=score
    d.setdefault("sections",[]); d.setdefault("quiz",[]); d.setdefault("keyTakeaways",[]); d.setdefault("glossary",[]); d.setdefault("sources",[])
    for i,q in enumerate(d["quiz"]):
        if not (isinstance(q.get("answer"),int) and 0<=q["answer"]<len(q.get("options",[]))): issues.append(f"{slug} q{i} bad answer")
    out.append(d)
open("site/data.js","w").write("window.DATA="+json.dumps(out,ensure_ascii=False)+";")
print(len(out),"objectives;",sum(len(d["quiz"]) for d in out),"questions;",sum(len(d["sections"]) for d in out),"sections")
print("\n".join(issues) or "no issues")
