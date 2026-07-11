#!/usr/bin/env python3
"""Assemble data/verification.json from the three verification passes:
  pass 0 = memory-only baseline (no docs)
  pass 1 = doc-grounded research agent (first pass, pre-correction)
  pass 2 = adversarial verify + human WebFetch checks -> corrected = ground truth

Emits the per-app ledger + the accuracy ladder shown on the case-study page.
"""
import json, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent

# Ground truth after verification (status, verdict) for the 21-app sample.
TRUTH = {
 "Salesforce":("self-serve-free","buildable-now"),
 "Attio":("self-serve-free","buildable-now"),
 "Intercom":("self-serve-trial","buildable-now"),
 "Gladly":("gated-partnership","buildable-with-friction"),
 "Telegram":("self-serve-free","buildable-now"),
 "Google Ads":("gated-approval","buildable-with-friction"),
 "Klaviyo":("self-serve-free","buildable-now"),
 "Shopify":("self-serve-free","buildable-now"),
 "Amazon Selling Partner":("gated-approval","buildable-with-friction"),
 "Ahrefs":("gated-paid","buildable-with-friction"),
 "Sherlock":("self-serve-free","buildable-with-friction"),
 "GitHub":("self-serve-free","buildable-now"),
 "Snowflake":("self-serve-trial","buildable-with-friction"),
 "Notion":("self-serve-free","buildable-now"),
 "Stripe":("self-serve-free","buildable-now"),
 "Plaid":("gated-approval","buildable-with-friction"),
 "NotebookLM":("gated-partnership","blocked"),
 "Otter AI":("gated-partnership","buildable-with-friction"),
 "fanbasis":("self-serve-free","buildable-now"),
 "iPayX":("self-serve-free","buildable-now"),
 "Fathom":("self-serve-free","buildable-now"),
}

# Pass 0 — memory-only baseline agent output (verbatim, names normalized).
MEMORY = {
 "Salesforce":("self-serve-free","buildable-now"),
 "Attio":("self-serve-free","buildable-now"),
 "Intercom":("self-serve-free","buildable-now"),
 "Gladly":("gated-partnership","blocked"),
 "Telegram":("self-serve-free","buildable-now"),
 "Google Ads":("gated-approval","buildable-with-friction"),
 "Klaviyo":("self-serve-free","buildable-now"),
 "Shopify":("self-serve-free","buildable-now"),
 "Amazon Selling Partner":("gated-approval","buildable-with-friction"),
 "Ahrefs":("gated-paid","buildable-with-friction"),
 "Sherlock":("no-public-api","buildable-now"),
 "GitHub":("self-serve-free","buildable-now"),
 "Snowflake":("self-serve-trial","buildable-now"),
 "Notion":("self-serve-free","buildable-now"),
 "Stripe":("self-serve-free","buildable-now"),
 "Plaid":("self-serve-free","buildable-with-friction"),
 "NotebookLM":("no-public-api","blocked"),
 "Otter AI":("no-public-api","blocked"),
 "fanbasis":("no-public-api","blocked"),
 "iPayX":("no-public-api","blocked"),
 "Fathom":("no-public-api","blocked"),
}

# Pass 1 — doc-grounded first pass (before verification corrections).
# Identical to TRUTH except the 3 rows verification later corrected.
FIRST = dict(TRUTH)
FIRST["Otter AI"]=("gated-approval","buildable-with-friction")
FIRST["iPayX"]=("self-serve-trial","buildable-now")
FIRST["Fathom"]=("self-serve-trial","buildable-now")

# Adversarial verifier verdicts + evidence (from the 4 verify agents & human checks)
LEDGER = {
 "Salesforce":("agree","human+agent","Free Developer Edition org, no card; Connected App OAuth.","https://developer.salesforce.com/signup"),
 "Attio":("agree","agent","API tokens on all plans incl. free via Workspace > Developers.","https://attio.com/help/apps/other-apps/generating-an-api-key"),
 "Intercom":("agree","agent","Token on app creation, but no permanent free plan (14-day trial).","https://developers.intercom.com/docs/build-an-integration/learn-more/authentication"),
 "Gladly":("agree","agent","Sales-led; /free-trial 404s; token needs an account gained via contract.","https://help.gladly.com/implementation/docs/get-your-api-tokens"),
 "Telegram":("agree","agent","BotFather /newbot issues a token instantly, free, no approval.","https://core.telegram.org/bots/features#botfather"),
 "Google Ads":("agree","agent","Dev token auto-issued at Test level; prod needs Basic/Standard review (5-10 days).","https://developers.google.com/google-ads/api/docs/access-levels"),
 "Klaviyo":("agree","agent","Private API keys self-created (Owner/Admin), free accounts; official MCP.","https://developers.klaviyo.com/en/docs/klaviyo_mcp_server"),
 "Shopify":("agree","agent","Free partner acct + dev stores; custom-app Admin tokens instant.","https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/generate-app-access-tokens-admin"),
 "Amazon Selling Partner":("agree","agent","Developer registration + app approval; LWA OAuth; PII roles need extra review.","https://developer-docs.amazon.com/sp-api/docs/registering-your-application"),
 "Ahrefs":("agree","human+agent","API v3 needs paid Lite+; unit-metered (50 min/req); full access ~Enterprise.","https://docs.ahrefs.com/en/api/docs/introduction"),
 "Sherlock":("agree","agent","MIT open-source CLI, no auth/API; agent must wrap the local binary.","https://github.com/sherlock-project/sherlock"),
 "GitHub":("agree","agent","PATs/OAuth free & self-serve; official remote MCP.","https://docs.github.com/en/rest/authentication/authenticating-to-the-rest-api"),
 "Snowflake":("agree","agent","30-day OR credit-capped trial, no perpetual free tier; key-pair JWT.","https://docs.snowflake.com/en/user-guide/admin-trial-account"),
 "Notion":("agree","agent","Internal integration tokens self-serve on Free/Plus; hosted MCP.","https://developers.notion.com/docs/create-a-notion-integration"),
 "Stripe":("agree","agent","Test keys auto-created & free; hosted MCP + Agent Toolkit.","https://docs.stripe.com/keys"),
 "Plaid":("agree","agent","Sandbox self-serve; Production requires Plaid approval; official MCP.","https://plaid.com/docs/resources/mcp/"),
 "NotebookLM":("agree","human+agent","No consumer API; only NotebookLM Enterprise via paid Gemini Enterprise on GCP.","https://docs.cloud.google.com/gemini/enterprise/notebooklm-enterprise/docs/overview"),
 "Otter AI":("CORRECTED","agent","Enterprise API/MCP enabled by contacting account manager = partnership, not app-review.","https://help.otter.ai/hc/en-us/articles/36130822688279-Otter-ai-Public-API"),
 "fanbasis":("agree","human+agent","apidocs.fan is real & live; x-api-key self-serve from dashboard.","https://apidocs.fan/"),
 "iPayX":("CORRECTED","agent","Permanent free tier (~10 audits/day), not a 5-audit trial; API+MCP real.","https://www.ipayx.ai/docs/mcp-server"),
 "Fathom":("CORRECTED","agent","Self-serve API key + permanent free plan; no documented tier gate.","https://developers.fathom.ai/quickstart"),
}

def score(pred):
    s=sum(1 for a in TRUTH if pred[a][0]==TRUTH[a][0])
    v=sum(1 for a in TRUTH if pred[a][1]==TRUTH[a][1])
    both=sum(1 for a in TRUTH if pred[a]==TRUTH[a])
    n=len(TRUTH)
    return {"status":s,"verdict":v,"both":both,"n":n,
            "status_pct":round(100*s/n),"verdict_pct":round(100*v/n),"both_pct":round(100*both/n)}

sample=[]
for app,(status,verdict) in TRUTH.items():
    res,who,note,url=LEDGER[app]
    sample.append({
        "app":app,
        "memory":{"status":MEMORY[app][0],"verdict":MEMORY[app][1],
                  "status_ok":MEMORY[app][0]==status,"verdict_ok":MEMORY[app][1]==verdict},
        "first":{"status":FIRST[app][0],"verdict":FIRST[app][1],
                 "status_ok":FIRST[app][0]==status,"verdict_ok":FIRST[app][1]==verdict},
        "truth":{"status":status,"verdict":verdict},
        "result":res,"checked_by":who,"note":note,"evidence":url,
    })

out={
 "meta":{
   "sample_size":len(TRUTH),
   "ladder":{
     "memory":score(MEMORY),      # pass 0
     "first":score(FIRST),        # pass 1
     "verified":score(TRUTH),     # pass 2 (=100 by construction; it is the reference)
   },
   "corrections":[s["app"] for s in sample if s["result"]=="CORRECTED"],
   "human_checked":[a for a,(r,w,n,u) in LEDGER.items() if "human" in w],
 },
 "sample":sample,
}
(ROOT/"data/verification.json").write_text(json.dumps(out,indent=2))
L=out["meta"]["ladder"]
print("both-fields accuracy: memory %d%% -> first-pass %d%% -> verified %d%%"%(
    L["memory"]["both_pct"],L["first"]["both_pct"],L["verified"]["both_pct"]))
print("status accuracy:      memory %d%% -> first-pass %d%% -> verified %d%%"%(
    L["memory"]["status_pct"],L["first"]["status_pct"],L["verified"]["status_pct"]))
print("corrections:",out["meta"]["corrections"])
print("human-checked:",out["meta"]["human_checked"])
