"""
research_agent.py — the app-buildability research agent.

WHAT IT DOES
------------
For each of the 100 apps in data/apps.json it runs a small agentic loop:

    1. Claude is given the app name + hint and a set of TOOLS.
    2. The tools are real web-research tools exposed through Composio
       (Composio COMPOSIO_SEARCH_* / Firecrawl scrape), so the model can
       search the open web and *fetch the app's real developer docs* rather
       than answering from memory.
    3. The model must finish by calling `record_finding` with a structured
       AppFinding (see schema.py). Tool-call validation forces the shape.

The same file powers three roles by swapping the system prompt:
    - "research"  : first-pass finding from live docs
    - "verify"    : an independent second agent that tries to REFUTE the
                    first finding (adversarial verification loop)

WHY COMPOSIO
------------
Composio is the point of the exercise: it turns third-party apps into
tool schemas an agent can call. Here we *consume* Composio the same way the
final product would — the research agent's own web tools are Composio tools
(COMPOSIO_SEARCH, FIRECRAWL). If you have a Composio API key the agent uses
them; if not, it falls back to a local WebSearch/requests shim so the repo
still runs. Either way the orchestration is identical.

WHERE A HUMAN IS NEEDED
-----------------------
Documented in README.md and surfaced on the case-study page:
  - obscure apps (fanbasis, iPayX, Paygent, Waterfall) where the model
    can hallucinate an API — these are flagged low-confidence and hand-checked.
  - the final self_serve vs gated call on enterprise apps, which often
    depends on a sales conversation the agent can't have.

USAGE
-----
    export ANTHROPIC_API_KEY=...
    export COMPOSIO_API_KEY=...        # optional but recommended
    python -m agent.research_agent --category "Developer & Infra"
    python -m agent.research_agent --all --out data/findings.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import anthropic

from .schema import AppFinding

ROOT = Path(__file__).resolve().parent.parent
APPS = json.loads((ROOT / "data" / "apps.json").read_text())

MODEL = os.environ.get("RESEARCH_MODEL", "claude-opus-4-8")

# --------------------------------------------------------------------------
# Tools: prefer Composio-hosted web tools, fall back to a local shim.
# --------------------------------------------------------------------------

def load_composio_tools() -> Optional[Any]:
    """Return a Composio toolset bound to web-search / scrape tools, or None.

    We ask Composio for search + scrape tools (the exact toolkit slugs vary by
    account; COMPOSIO_SEARCH and FIRECRAWL are the common ones). This is the
    same SDK call the shipped product would make to give an agent Salesforce or
    GitHub tools — we're just pointing it at research utilities.
    """
    key = os.environ.get("COMPOSIO_API_KEY")
    if not key:
        return None
    try:
        from composio import Composio
        from composio_anthropic import AnthropicProvider

        client = Composio(api_key=key, provider=AnthropicProvider())
        tools = client.tools.get(
            user_id=os.environ.get("COMPOSIO_USER_ID", "research-agent"),
            tools=[
                "COMPOSIO_SEARCH_SEARCH",
                "COMPOSIO_SEARCH_TAVILY_SEARCH",
                "FIRECRAWL_SCRAPE",
            ],
        )
        return {"client": client, "tools": tools}
    except Exception as e:  # pragma: no cover - depends on account entitlements
        print(f"[composio] unavailable ({e}); using local web shim", file=sys.stderr)
        return None


def local_web_tools() -> List[Dict[str, Any]]:
    """Minimal fallback so the repo runs with only an Anthropic key.

    Uses Anthropic's server-side `web_search` tool. The agent still fetches
    live pages; it just goes through Anthropic instead of Composio.
    """
    return [{"type": "web_search_20250305", "name": "web_search", "max_uses": 6}]


RECORD_TOOL = {
    "name": "record_finding",
    "description": "Record the final structured finding for this app. Call exactly once, last.",
    "input_schema": AppFinding.model_json_schema(),
}

# --------------------------------------------------------------------------
# Prompts
# --------------------------------------------------------------------------

RESEARCH_SYSTEM = """You are a buildability research analyst. For the given app you decide whether it \
could become an "agent toolkit" — a set of API-callable tools an AI agent can use — TODAY.

Rules:
- USE THE TOOLS. Search the web and FETCH THE APP'S REAL DEVELOPER DOCS before answering. Do not answer from memory.
- Be skeptical. If you cannot find a public API, say so and set confidence low. Never invent an API.
- self_serve_status must reflect how a developer actually gets working credentials:
  self-serve-free / self-serve-trial / gated-paid / gated-approval / gated-partnership / no-public-api.
- buildability_verdict: buildable-now (self-serve creds + real REST/GraphQL), buildable-with-friction
  (auth/approval/rate friction), or blocked (partnership-only or no public API).
- Cite 1-3 real doc URLs you actually consulted in evidence_urls.
Finish by calling record_finding exactly once."""

VERIFY_SYSTEM = """You are an adversarial verification analyst. You are given another agent's finding \
about an app. Your job is to independently research the app's real docs and TRY TO REFUTE the finding.

- Re-fetch the primary developer docs yourself.
- Focus on the two fields that matter most: self_serve_status and buildability_verdict.
- If you agree, say so. If you disagree, give the corrected value and cite the doc that proves it.
Default to skepticism but do not manufacture disagreement. Finish by calling record_finding with your
own independent AppFinding for the app."""


# --------------------------------------------------------------------------
# Agent loop
# --------------------------------------------------------------------------

def run_agent(app: Dict[str, str], system: str, prior: Optional[dict] = None,
              max_turns: int = 8) -> Optional[dict]:
    client = anthropic.Anthropic()
    composio = load_composio_tools()

    if composio:
        web_tools = composio["tools"]
    else:
        web_tools = local_web_tools()
    tools = list(web_tools) + [RECORD_TOOL]

    user = f"App: {app['app']}\nCategory: {app['category']}\nHint / docs: {app['hint']}\n"
    if prior:
        user += "\nAnother agent produced this finding — verify or refute it:\n"
        user += json.dumps(prior, indent=2)

    messages: List[Dict[str, Any]] = [{"role": "user", "content": user}]

    for _ in range(max_turns):
        resp = client.messages.create(
            model=MODEL, max_tokens=2000, system=system, tools=tools, messages=messages,
        )
        messages.append({"role": "assistant", "content": resp.content})

        tool_results = []
        finding = None
        for block in resp.content:
            if block.type != "tool_use":
                continue
            if block.name == "record_finding":
                finding = block.input
                tool_results.append({"type": "tool_result", "tool_use_id": block.id,
                                     "content": "recorded"})
            elif composio:
                out = composio["client"].provider.execute_tool_call(
                    composio["client"], block)
                tool_results.append({"type": "tool_result", "tool_use_id": block.id,
                                     "content": json.dumps(out)[:6000]})
            # web_search (Anthropic server tool) is auto-executed; nothing to do.

        if finding is not None:
            return finding
        if not tool_results:
            # No tool calls this turn and no finding — nudge once.
            if resp.stop_reason == "end_turn":
                messages.append({"role": "user",
                                 "content": "Call record_finding now with your best structured answer."})
                continue
        if tool_results:
            messages.append({"role": "user", "content": tool_results})

    return None


def research_app(app: Dict[str, str]) -> Optional[dict]:
    return run_agent(app, RESEARCH_SYSTEM)


def verify_app(app: Dict[str, str], prior: dict) -> Optional[dict]:
    return run_agent(app, VERIFY_SYSTEM, prior=prior)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--category", help="only research one category")
    ap.add_argument("--app", help="only research one app by name")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--verify", action="store_true", help="run the verification loop too")
    ap.add_argument("--out", default="data/findings.json")
    args = ap.parse_args()

    todo = APPS
    if args.category:
        todo = [a for a in APPS if a["category"] == args.category]
    if args.app:
        todo = [a for a in APPS if a["app"].lower() == args.app.lower()]

    results = []
    for app in todo:
        print(f"→ researching {app['app']}", file=sys.stderr)
        f = research_app(app)
        if f and args.verify:
            v = verify_app(app, f)
            f["_verify"] = v
        if f:
            results.append(f)
        time.sleep(0.5)  # be polite

    out = ROOT / args.out
    out.write_text(json.dumps(results, indent=2))
    print(f"wrote {len(results)} findings → {out}")


if __name__ == "__main__":
    main()
