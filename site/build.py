#!/usr/bin/env python3
"""Bake data/findings.json + data/verification.json into a self-contained
site/index.html by injecting them into site/template.html.

    python site/build.py

Keeps the page a single portable file (no runtime fetch) while the data stays
version-controlled and re-generatable by the agent.
"""
import json, pathlib, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
findings = json.loads((ROOT / "data/findings.json").read_text())
try:
    verify = json.loads((ROOT / "data/verification.json").read_text())
except FileNotFoundError:
    verify = {"sample": [], "meta": {}}

tpl = (ROOT / "site/template.html").read_text()
payload = (
    "window.FINDINGS=" + json.dumps(findings, separators=(",", ":")) + ";\n"
    "window.VERIFY=" + json.dumps(verify, separators=(",", ":")) + ";\n"
    "window.BUILT=" + json.dumps(str(datetime.date.today())) + ";"
)
out = tpl.replace("/*__DATA__*/", payload)
(ROOT / "site/index.html").write_text(out)
print(f"built site/index.html  ({len(findings)} findings, "
      f"{len(verify.get('sample', []))} verified rows)")
