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

payload = (
    "window.FINDINGS=" + json.dumps(findings, separators=(",", ":")) + ";\n"
    "window.VERIFY=" + json.dumps(verify, separators=(",", ":")) + ";\n"
    "window.BUILT=" + json.dumps(str(datetime.date.today())) + ";"
)

for tpl_name, out_name in [("template.html", "index.html"),
                           ("minimal_template.html", "minimal.html")]:
    tpl = (ROOT / "site" / tpl_name).read_text()
    (ROOT / "site" / out_name).write_text(tpl.replace("/*__DATA__*/", payload))
    print(f"built site/{out_name}  ({len(findings)} findings, "
          f"{len(verify.get('sample', []))} verified rows)")
