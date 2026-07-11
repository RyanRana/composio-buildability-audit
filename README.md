# 100-App Buildability Research Agent

> Can each of 100 SaaS apps become an **agent toolkit** today? An agent researched all 100,
> a second adversarial agent verified a sample, and a human spot-checked the rest.
> **Live case study → [add your Vercel URL here]**

This repo contains:

| Path | What it is |
|------|-----------|
| `agent/research_agent.py` | The research agent — a small agentic loop (Claude + Composio web tools) that fetches each app's real docs and emits a structured `AppFinding`. |
| `agent/schema.py` | The pydantic contract shared by the research agent, the verifier, and the HTML renderer. |
| `agent/verify_agent.py` | The adversarial verification loop — an independent agent that tries to *refute* each finding. |
| `data/apps.json` | The 100-app research set (name, category, doc hint). |
| `data/findings.json` | The agent's output: one row per app. |
| `data/verification.json` | The sample verification results (agent + human), with hits and misses. |
| `site/index.html` | The single self-explanatory case-study page (findings, patterns, agent, proof, verification). |

## What the agent does

For each app the agent runs this loop:

```
app name + doc hint
      │
      ▼
┌─────────────────────────────────────────────┐
│ Claude (claude-opus-4-8)                      │
│  tools: COMPOSIO_SEARCH, FIRECRAWL_SCRAPE     │  ← real web + doc fetch
│  must finish by calling record_finding(...)   │  ← forced structured output
└─────────────────────────────────────────────┘
      │
      ▼
AppFinding { auth_methods, self_serve_status,
             api_surface{type,breadth,has_mcp},
             buildability_verdict, main_blocker,
             confidence, evidence_urls[] }
```

The tools are exposed through **Composio's SDK** (`composio` + `composio_anthropic`). Composio is
the whole point: it turns a third-party app into tool schemas an agent can call. Here we *consume*
Composio the same way the shipped product would — the agent's own research tools (web search, doc
scrape) are Composio tools. If no `COMPOSIO_API_KEY` is set, it falls back to Anthropic's built-in
`web_search` tool so the repo still runs end-to-end.

### Where a human was needed

The agent is good but not infallible. A human was required for:

1. **Obscure long-tail apps** — `fanbasis`, `iPayX`, `Paygent Connect`, `Waterfall.io`. These are
   easy to hallucinate an API for. The agent flags them `confidence: low/medium`; a human opened the
   docs and confirmed or corrected. (e.g. the agent *found* fanbasis and iPayX had real self-serve
   APIs — a pleasant surprise — but Paygent stayed low-confidence because it's a white-label NMI gateway.)
2. **The self-serve vs gated judgment call** on enterprise apps (Salesforce Commerce Cloud, DealCloud,
   Gladly, PitchBook) — the true answer depends on a sales conversation, so the human confirms the
   *gate exists* from docs even when exact pricing is hidden.
3. **Final arbitration** when the research agent and the verifier disagreed.

## How to run

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
export COMPOSIO_API_KEY=...            # optional; falls back to Anthropic web_search

# research one category
python -m agent.research_agent --category "Developer & Infra"

# research everything + run the verification loop
python -m agent.research_agent --all --verify --out data/findings.json

# verify a random sample against the findings
python -m agent.verify_agent --sample 15 --in data/findings.json --out data/verification.json
```

The 100-app research fan-out in this repo was actually executed as **10 parallel category agents**
(one per category) via Claude Code's sub-agent orchestration — the Python entrypoint above is the
single-process equivalent you can run yourself.

## The verification loop (why the numbers are trustworthy)

Accuracy is the headline metric. Three passes:

1. **Pass 1 — research agent** produces 100 findings from live docs.
2. **Pass 2 — adversarial verifier** independently re-researches a random sample and tries to refute
   each finding. Disagreements are logged, not silently merged.
3. **Pass 3 — human spot-check** of the sample against the primary docs by hand.

The case-study page shows the sample, every hit and miss, and how accuracy moved from the first pass
to the corrected numbers.

## The findings, in one breath

Auth is dominated by **OAuth2 + token/API-key**. The **Developer/Infra** and **Productivity** clusters
are the easy wins — almost all self-serve-free with official MCP servers already. The **Ad platforms**
(Google/Meta/LinkedIn/Threads) are the hard cluster — universally gated behind app review or partner
programs. The single most common blocker is **not auth, but access**: getting production credentials.
See `site/index.html` for the full breakdown.
