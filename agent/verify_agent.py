"""
verify_agent.py — adversarial verification loop.

Takes the research agent's findings and, for a random sample, spawns an
INDEPENDENT agent whose job is to *refute* the finding by re-reading the app's
real docs. It focuses on the two fields that decide the whole exercise:
self_serve_status and buildability_verdict.

Output (data/verification.json) is a list of VerifyResult rows: agrees / the
disagreement / the corrected value / evidence. The case-study page reads this
file directly to show hits and misses honestly.

    python -m agent.verify_agent --sample 15 --in data/findings.json --out data/verification.json
    python -m agent.verify_agent --apps "Salesforce,Ahrefs,NotebookLM" --in data/findings.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# We deliberately reuse the research loop with the adversarial system prompt,
# so the verifier is a genuinely separate agent run, not a rubber stamp.
from .research_agent import run_agent, VERIFY_SYSTEM
from .schema import AppFinding

ROOT = Path(__file__).resolve().parent.parent


def deterministic_sample(items, k, seed=42):
    """Reproducible sample without importing random's global state.

    A tiny LCG so the same seed always picks the same rows — verification must
    be reproducible for the accuracy numbers on the page to mean anything.
    """
    picked, idx, state = [], list(range(len(items))), seed
    for _ in range(min(k, len(items))):
        state = (1103515245 * state + 12345) & 0x7FFFFFFF
        j = state % len(idx)
        picked.append(items[idx.pop(j)])
    return picked


def compare(finding: dict, verdict: dict) -> dict:
    """Diff the two most important fields."""
    fields = ["self_serve_status", "buildability_verdict"]
    diffs = []
    for f in fields:
        a, b = finding.get(f), verdict.get(f)
        if a and b and a != b:
            diffs.append(f"{f}: research={a!r} vs verify={b!r}")
    return {
        "app": finding["app"],
        "agrees": len(diffs) == 0,
        "disagreements": diffs,
        "research": {k: finding.get(k) for k in fields},
        "verify": {k: verdict.get(k) for k in fields},
        "verify_evidence": verdict.get("evidence_urls", []),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="data/findings.json")
    ap.add_argument("--out", default="data/verification.json")
    ap.add_argument("--sample", type=int, default=15)
    ap.add_argument("--apps", help="comma-separated app names to force-verify")
    args = ap.parse_args()

    findings = json.loads((ROOT / args.inp).read_text())
    by_name = {f["app"]: f for f in findings}

    if args.apps:
        chosen = [by_name[n.strip()] for n in args.apps.split(",") if n.strip() in by_name]
    else:
        chosen = deterministic_sample(findings, args.sample)

    results = []
    for finding in chosen:
        app = {"app": finding["app"], "category": finding["category"],
               "hint": finding.get("evidence_urls", [""])[0]}
        print(f"→ verifying {app['app']}", file=sys.stderr)
        verdict = run_agent(app, VERIFY_SYSTEM, prior=finding)
        if verdict:
            results.append(compare(finding, verdict))

    agree = sum(1 for r in results if r["agrees"])
    out = {
        "sample_size": len(results),
        "agreements": agree,
        "agreement_rate": round(agree / max(1, len(results)), 3),
        "results": results,
    }
    (ROOT / args.out).write_text(json.dumps(out, indent=2))
    print(f"agreement {agree}/{len(results)} → {args.out}")


if __name__ == "__main__":
    main()
