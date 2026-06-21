#!/usr/bin/env python3
"""
Patch the scoring lane of workflow f2RPzoJ2m45Odu4k (1AltX Upwork — Unified
Pipeline) so its 'Build Anthropic Request' node mirrors score_rows.py — same
X1-X6 vetoes, same Hot/Skip tier collapse, same new_blank_slate client guidance.

WHY: pre-2026-06-21 the unified pipeline used an older Sonnet prompt with a
three-tier Pursue/Apply/Ignore scheme, no veto layer, and default V=3 when
client data was missing. score_rows.py wrote 🔥 Hot + W=15+ during triage, the
pipeline silently re-scored ~15 min later with the old prompt, demoted edge
rows below the W>=14 PVC2 threshold, and rendered jobs were short-circuited
("SKIP: Score 13 < 14 — not worth producing"). See
project_unified_scorer_prompt_sync.md.

Idempotent. Re-run anytime to restore the synced prompt if anyone edits in
the n8n UI. Preserves all other nodes, connections, settings, and the
auto-trigger PVC2/07C lane.

CANONICAL PROMPT SOURCE: /home/richard/Dropbox/Companies/1AltX/Projects/_clients/proposal-video-creator/pvc2/score_rows.py
If you edit the score_rows prompt, update the SCORER_JSCODE constant below to
match and re-run this script. Drift between the two scorers re-introduces the
divergence this patch was built to fix.
"""
import json
import subprocess
import sys
import urllib.request

WORKFLOW_ID = "f2RPzoJ2m45Odu4k"
N8N_BASE = "https://n8n.dakona.net"
SCORER_NODE_NAME = "Build Anthropic Request"
# Cloudflare-friendly UA — default urllib UA gets blocked with `error code: 1010`
UA = "Mozilla/5.0 (X11; Linux x86_64) curl-compatible"

N8N_KEY = subprocess.check_output(
    ["az", "keyvault", "secret", "show",
     "--vault-name", "kvdaxdakonapilot",
     "--name", "n8n-api-key",
     "--query", "value", "-o", "tsv"],
    text=True,
).strip()


# ─── Synced scorer prompt (Sonnet 4.6, mirrors score_rows.py) ────────────────
SCORER_JSCODE = r'''const item = $input.first();
const jobHtml = item.json._jobLinkHtml;
const dateSubmitted = item.json._dateSubmitted || '';
const now = new Date();
const cstNow = new Date(now.toLocaleString('en-US', { timeZone: 'America/Chicago' }));
const todayStr = cstNow.toISOString().split('T')[0];

const scorerPrompt = `You are a senior Upwork job scoring engine for Richard Mabbun of 1AltX (AI/automation consultant).
Return ONLY a single JSON object. No commentary. No markdown.

TODAY (CST): ${todayStr} | DATE SUBMITTED: ${dateSubmitted}
NOTE: Content below may be from an email alert (truncated). Score on available info; use client_signal=no_data when client metadata is absent.

JOB CONTENT:
"""${jobHtml}"""

JSON structure (return ONLY these fields):
{"exclusion_gate":"X1|X2|X3|X4|X5|X6|none","confidence_score":0,"job_fit_score":0,"client_quality_score":0,"combined_score":0,"status":"Pursue|Ignore","richard_fit_tag":"AI Automation|CRM Architecture|GHL Complex|Complex Integration|RIA/Compliance|Payments/Fintech|Pass","engagement_type":"One-off|Retainer Potential|Ongoing","competitive_difficulty":"Low|Medium|High","priority_flag":"\ud83d\udd25 Hot|\u23ed Skip","tos_risk":"demand|invite|none","client_signal":"premium_repeat|verified_paying|new_blank_slate|low_pay_floor|window_shopper|no_data","matching_project":null,"makecom":0,"n8n":0,"google_sheets":0,"google_docs":0,"gmail":0,"chatgpt":0,"google_drive":0,"airtable":0,"twilio":0,"hubspot":0,"other":"","proposed_rate":"","notes":""}

# === FILTER LAYER (apply IN ORDER, stop at first match) ===

AGE: DateSubmitted >2 days before today => exclusion_gate=none, status=Ignore, priority_flag=\u23ed Skip, all scores=0, notes="Job older than 2 days". Return immediately.

AVAILABILITY: Job content contains "This job is no longer available" or "Not available" => exclusion_gate=none, status=Ignore, priority_flag=\u23ed Skip, all scores=0, notes="Job no longer available". Return immediately.

BUDGET: Hourly <$30/hr OR fixed <$200 OR "$X.XX/hr avg" history <$30 => exclusion_gate=none, status=Ignore, priority_flag=\u23ed Skip, all scores=0, notes="Budget below floor". Return immediately.

TOS: Off-platform DEMAND signals (must pay PayPal/Stripe/wire/etc, "we don't use Upwork for payment", "communicate only via email/WhatsApp", "direct contract only", "long-term direct hire after trial") => tos_risk=demand, status=Ignore, priority_flag=\u23ed Skip, all scores=0, notes prefixed "TOS RED FLAG:". Return immediately. INVITE signals (prefer email, personal contact in JD, Calendly link) => tos_risk=invite, continue scoring.

# === VETO LAYER (X1-X6) \u2014 apply BEFORE positive scoring ===
# If ANY gate fires: combined_score=0, job_fit_score=0, client_quality_score=0, priority_flag=\u23ed Skip, status=Ignore, richard_fit_tag=Pass, exclusion_gate=<Xn>, notes prefixed "EXCLUDED[Xn] \u2014 <reason>". Return.

X1 Self-exclusion phrases \u2014 description contains any of (case-insensitive): "not a no-code wrapper", "not basic API integration", "not wrap-ChatGPT", "not a Make/n8n/Zapier role", "not a prompt-engineering role", "must write production code", "not just orchestration", "not just glue code", "real software engineers only", "not a vibe-coding role". => EXCLUDED[X1].

X2 Code-stack-primary \u2014 mandatory skills or required experience includes: LangChain, LangGraph, LlamaIndex, CrewAI, Semantic Kernel, fine-tuning, LoRA/QLoRA/PEFT, vLLM, llama.cpp, Docker, Kubernetes, MLOps, pgvector (as backend), AWS Lambda/ECS/SageMaker, "open-source agent framework", "self-hostable agent". => EXCLUDED[X2]. EXCEPTION: n8n-native RAG (n8n+Qdrant or n8n+Supabase as vector store, no source-code deliverable) stays writeable.

X3 Real-time voice primary \u2014 Twilio media streams / Retell / VAPI as primary platform, ElevenLabs real-time, "voice agent" with Node/Python backend, live inbound/outbound calling, sub-second latency. => EXCLUDED[X3]. EXCEPTION: n8n/Make orchestrating an existing voice tool (e.g., n8n triggers Vapi via webhook) stays writeable.

X4 Teaching as paid deliverable (intent-match, NOT keyword-match) \u2014 fires ONLY when buyer pays you to INSTRUCT humans. Both must hold: (a) instructional format as deliverable (live/scheduled sessions, weekly office hours, cohort, curriculum, homework, exam, recorded course modules, 1-on-1 tutoring); (b) compensated output IS the instruction. Does NOT fire: "Mentor" in title for an analyst/build role, "mentoring experience preferred" as qualification, "train our team on handoff", "Onboarding/Implementation specialist", "Document the workflow". => EXCLUDED[X4] only when both (a) and (b) clearly hold.

X5 Full-time embed \u2014 30+ hrs/week OR (>6 months AND queue/SLA/embedded framing like "join our team", "FTE-equivalent", "daily standups", "on-call rotation"). => EXCLUDED[X5].

X6 Mandatory-skill exclude \u2014 mandatory or required skills include: Next.js / React / Vue / Flutter / React Native / Python (as backend deliverable, not Claude API) / Node.js (as backend deliverable) / TypeScript backend / Django / Laravel / Supabase backend / Salesforce Apex. => EXCLUDED[X6]. NOTE: Python/Node mentions are OK when used as Claude/OpenAI API client only.

# === IF AND ONLY IF NO FILTER OR VETO FIRED, proceed to positive scoring ===

JOB FIT SCORE (0-10): Start 0. +2 n8n required/preferred, +2 Make.com required/preferred, +2 complex multi-system API (3+), +2 AI/LLM (Claude/GPT/OpenAI/agents), +1 HubSpot/Pipedrive/Close complex, +1 Airtable as system of record, +1 Twilio/SMS, +1 webhooks/REST primary, +1 compliance/regulated (RIA/fintech/HIPAA), +1 GHL complex (NOT funnel/LP), +1 Google Workspace automation, +1 MSP/IT automation. Deduct: -2 GHL funnel/LP build, -2 deep coding primary, -1 basic CRM no automation, -1 heavy offshore competition. Cap 10.

CLIENT QUALITY SCORE (0-10) \u2014 distinguish NEW from BAD:
- premium_repeat (verified, $5K+ spend, repeat hires, healthy avg rate) => V=9-10
- verified_paying (verified payment, some history, reasonable rate) => V=7-8
- new_blank_slate (Member since <30 days, $0 spent, 0 hires, real need) => V=6-8 (opportunity, NOT bad)
- low_pay_floor (verified but <$10/hr avg historically) => V=4-5
- window_shopper (long tenure, many posts, low hire rate <50%, unverified payment) => V=2-4
- no_data (missing client metadata entirely) => V=5

COMBINED = job_fit_score + client_quality_score (cap 20).

TIER COLLAPSE (no middle tier):
- combined >= 14 => status=Pursue, priority_flag=\ud83d\udd25 Hot
- combined < 14 => status=Ignore, priority_flag=\u23ed Skip
There is no Apply tier. Anything worth pursuing is Hot; everything else is Skip.

confidence_score = combined_score (legacy field, same value).

RICHARD FIT TAG: AI Automation | CRM Architecture | GHL Complex | Complex Integration | RIA/Compliance | Payments/Fintech | Pass

ENGAGEMENT TYPE: One-off | Retainer Potential | Ongoing
COMPETITIVE DIFFICULTY: Low (<10 proposals, US-only, niche) | Medium (10-30) | High (50+, worldwide, commoditized)

TOOL FLAGS (1 if clearly required else 0): makecom, n8n, google_sheets, google_docs, gmail, chatgpt, google_drive, airtable, twilio, hubspot. OTHER: list any tools not above.

MATCHING PROJECT (pick closest or null): "Close to ClickUp Automation" | "Smart Email Parser & Auto-Reply" | "Sheets to Signatures" | "Ringover Webhook Listener" | "Pipedrive to Zendesk Sync" | "MSP PSA to Spreadsheet Export" | "Heartland Language Scheduling" | "RPE Systems Dashboard" | "OPT Solutions Commission Reporting" | "DAX Platform / AI Workspace" | null

PROPOSED RATE: explicit fixed price => return exactly (e.g., "$1,400.00"). Hourly => "$100/hr". Unclear => "$100/hr".

NOTES: 1-2 sentences max. Prefix with "EXCLUDED[Xn] \u2014 " if a veto gate fired.

OUTPUT RULES: Return ONLY valid JSON. No markdown, no commentary, no arrays, no extra fields.`;

return [{ json: { ...item.json, _requestBody: { model: 'claude-sonnet-4-6', max_tokens: 1024, messages: [{ role: 'user', content: scorerPrompt }] } } }];
'''


def fetch_workflow():
    req = urllib.request.Request(
        f"{N8N_BASE}/api/v1/workflows/{WORKFLOW_ID}",
        headers={"X-N8N-API-KEY": N8N_KEY, "User-Agent": UA},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def put_workflow(wf):
    body = json.dumps(wf).encode()
    req = urllib.request.Request(
        f"{N8N_BASE}/api/v1/workflows/{WORKFLOW_ID}",
        method="PUT",
        data=body,
        headers={
            "X-N8N-API-KEY": N8N_KEY,
            "Content-Type": "application/json",
            "User-Agent": UA,
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def main():
    wf = fetch_workflow()
    patched = 0
    for n in wf.get("nodes", []):
        if n["name"] == SCORER_NODE_NAME:
            old = n["parameters"].get("jsCode", "")
            if old.strip() == SCORER_JSCODE.strip():
                print(f"NO-OP: '{SCORER_NODE_NAME}' already matches synced prompt ({len(old)} chars)")
                return 0
            n["parameters"]["jsCode"] = SCORER_JSCODE
            print(f"Patched '{SCORER_NODE_NAME}': {len(old)} -> {len(SCORER_JSCODE)} chars")
            patched += 1
    if patched != 1:
        print(f"ERROR: expected to patch exactly 1 node, patched {patched}", file=sys.stderr)
        return 2
    # n8n API rejects extra settings keys on update — strip to the accepted subset
    wf["settings"] = {
        k: v for k, v in wf.get("settings", {}).items()
        if k in ("executionOrder", "saveManualExecutions", "timezone")
    }
    # PUT requires {name, nodes, connections, settings}; drop server-managed fields
    payload = {
        "name": wf["name"],
        "nodes": wf["nodes"],
        "connections": wf["connections"],
        "settings": wf["settings"],
    }
    result = put_workflow(payload)
    print(f"OK: updated workflow {result.get('id')} (versionId={result.get('versionId')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
