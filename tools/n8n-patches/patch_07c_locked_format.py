#!/usr/bin/env python3
"""
Patch the 07C lane of workflow WyD6dxFAGPquiqPG with the locked cover-letter
format per Richard's 2026-06-06 spec.
"""
import json
import os
import sys
import urllib.request
import subprocess

WORKFLOW_ID = "WyD6dxFAGPquiqPG"
N8N_BASE = "https://n8n.dakona.net"
N8N_KEY = subprocess.check_output(
    ["az", "keyvault", "secret", "show", "--vault-name", "kvdaxdakonapilot",
     "--name", "n8n-api-key", "--query", "value", "-o", "tsv"],
    text=True,
).strip()

# ─── Find Row ─────────────────────────────────────────────────────────────────
NEW_FIND_ROW = r"""const items = $input.all();
const rowNumber = $('Webhook').first().json.body.row_number;
const targetRow = items.find(item => item.json.row_number == rowNumber);
if (!targetRow) throw new Error(`Row ${rowNumber} not found in sheet`);

// Prefer col AK (PVC Variant) — pvc2.run writes the share.descript link here.
let _videoShareUrl = (targetRow.json['PVC Variant'] || '').toString().trim();
if (!_videoShareUrl.includes('share.descript.com')) {
  // Fallback: scan all string cells for a share.descript URL
  _videoShareUrl = Object.values(targetRow.json)
    .find(v => typeof v === 'string' && v.includes('share.descript.com')) || '';
}
const _videoMissing = !_videoShareUrl.includes('share.descript.com');

return [{ json: {
  ...targetRow.json,
  _videoShareUrl,
  _videoMissing,
  _rowNumber: rowNumber,
} }];
"""

# ─── Build Claude Request ─────────────────────────────────────────────────────
NEW_BUILD_CLAUDE = r"""const row = $('Find Row').first().json;
// Fetch Catalog (HTTP Request, responseFormat=json) splits array responses into one n8n item
// per array element. Reassemble with $input.all().
const catalog = $input.all().map(i => i.json).filter(i => i && i.title);

const jobTitle = (row['Job Title'] || '').replace(/^New job alert:\s*/i, '').trim();
const jobDescRaw = row['Job Link HTML'] || '';
const jobDesc = jobDescRaw
  .replace(/<[^>]+>/g, ' ')
  .replace(/&amp;/g, '&').replace(/&nbsp;/g, ' ')
  .replace(/\s+/g, ' ')
  .trim()
  .slice(0, 4500);

const videoLine = row._videoMissing
  ? 'I recorded this specifically for your posting → [PASTE VIDEO LINK]'
  : `I recorded this specifically for your posting → ${row._videoShareUrl}`;

// Compact authoritative catalog text — exact titles, URLs, tools.
const catalogText = (catalog || [])
  .filter(c => c && c.title && c.youtube_url)
  .map(c => `${c.title}\n  ${c.youtube_url}\n  Tools: ${(c.tools || []).join(', ')}\n  About: ${c.desc || ''}`)
  .join('\n\n');

const CREDENTIALS = `Make.com Advanced Certified automation engineer. Heavy daily user of n8n (local and cloud) with API integration across many use cases stemming from CRM, including X (Twitter) API, webhook listeners, multi-step pipelines, and data normalization workflows. 20+ years in IT and fintech. 100% Job Success Score, Top Rated on Upwork.`;

const systemPrompt = `You write Richard Mabbun's Upwork cover letters in his voice. Output the cover letter only — no preamble, no commentary, no markdown, no bullets, no bold. Plain text in the exact structure below.

═══ LOCKED FORMAT — every section, in this order ═══

LINE 1 — VIDEO LINE (mandatory, always first, copy verbatim):
${videoLine}

LINE 2 — HOOK
One punchy sentence naming the client's core pain and signaling you've solved it before. No greeting. No "I noticed". No throat-clearing. Generic framing only — never use the client's name, brand, or company name.

LINES 3-5 — CATALOG SAMPLES (2 or 3, each is this exact 3-line block, no labels, no bullets):
<Exact catalog title — copy/paste from the CATALOG below>
<YouTube URL — copy/paste from the CATALOG below>
<One sentence on why THIS sample matches THIS job.>

Selection: best match first, by exact tool/platform match → problem pattern → channel. Use 2-3 samples (3 only when truly relevant).

CRITICAL — CATALOG INTEGRITY:
- Use EXACT titles and EXACT URLs from the CATALOG. Never invent, rename, paraphrase, abbreviate, qualify, or merge entries.
- Never label a catalog item as using a tool it does not list. The Tools field in the CATALOG is authoritative.
- If a title is not in the CATALOG, it does not exist — skip it.

SOLUTION APPROACH (3-5 sentences)
Concrete plan using the client's actual stack plus Richard's standard automation stack (Make.com, n8n, Claude API, Airtable, Google Workspace, HubSpot/GHL/Pipedrive). Specific to this job. No client names.

CREDENTIALS BLOCK (verbatim, exact text — copy the whole paragraph):
${CREDENTIALS}

CLOSE — pick EXACTLY ONE based on the job type (no calls, no off-platform language):
- Broken or messy system → "Happy to start with a $250 Integration Audit — fixed scope, fixed price, applied to the rebuild."
- Vague scope → "Happy to start with a $250 Phase 1 — discovery + scope + small POC, fixed price, applied to the build."
- Complex $3K+ build → "Happy to start with a $500 Phase 0 — <2-3 concrete deliverables>, fixed price, applied to the build."
- Clear spec / budget under ~$2K / client has paid trial → "Clear spec, ready to start within your gate."
- Hourly or embedded role → "Ready to start at your hourly rate, no Phase 0 needed."

SIGNATURE (exact, on its own two lines):
– Richard
1AltX LLC

EXCEPTION: if the post bars agencies or explicitly asks for individuals only, drop the company line and sign just:
– Richard

═══ HARD RULES (must all pass) ═══
- Plain text. No markdown, no bold, no bullets, no headings, no asterisks.
- Under 5,000 characters total.
- No client names anywhere. Generic framing only.
- Upwork TOS: no off-platform contact, no email addresses, no phone numbers, no calendly/cal.com, no social media links, no scraping/circumvention language, no banned payment terms. The ONLY external links allowed: the LINE 1 video link and the catalog YouTube URLs.
- Honesty: never claim experience with a platform that doesn't appear in the CATALOG tools. If the job's required tool isn't represented (e.g. Dubsado, Follow Up Boss native, Fillout, voice-agent platforms, full-stack web-app dev), recommend a tool Richard has actually used and offer to wire the client's choice as a secondary path. Never overclaim.
- CamelCase any field names with underscores.

═══ CATALOG (authoritative) ═══
${catalogText}

═══ JOB ═══
Title: ${jobTitle}
Description: ${jobDesc}`;

const userPrompt = `Write the cover letter now. Follow the LOCKED FORMAT exactly. Output the letter only.`;

return [{ json: { system: systemPrompt, user: userPrompt, row, _videoMissing: row._videoMissing, _videoShareUrl: row._videoShareUrl } }];
"""

# ─── Parse Response ───────────────────────────────────────────────────────────
NEW_PARSE_RESPONSE = r"""const response = $input.first().json;
const text = (response.content?.[0]?.text || '').trim();
const buildOut = $('Build Claude Request').first().json;
const row = buildOut.row;

// ─── Validation ────────────────────────────────────────────────────────────
const errors = [];
const firstLine = text.split('\n')[0] || '';

if (!firstLine.startsWith('I recorded this specifically for your posting →')) {
  errors.push('LINE1_NOT_VIDEO');
}
if (text.includes('web.descript.com')) {
  errors.push('WEB_DESCRIPT_LINK');
}
if (text.length > 5000) {
  errors.push('OVER_5000_CHARS');
}
if (text.length < 400) {
  errors.push('TOO_SHORT');
}
// Credentials block presence
if (!text.includes('Make.com Advanced Certified automation engineer')) {
  errors.push('NO_CREDENTIALS');
}
// Signature presence
if (!text.includes('– Richard')) {
  errors.push('NO_SIGNATURE');
}
// Markdown leakage
if (/\*\*[^*]+\*\*/.test(text) || /^#{1,6}\s/m.test(text) || /^\s*[-*]\s/m.test(text)) {
  errors.push('MARKDOWN_LEAKAGE');
}
// TOS — disallowed off-platform tokens
const tosBlacklist = ['@gmail.com', '@outlook.com', '@yahoo.com', 'calendly.com', 'cal.com', 'whatsapp', 'telegram.me', 't.me/'];
const tosHit = tosBlacklist.find(t => text.toLowerCase().includes(t));
if (tosHit) errors.push(`TOS_${tosHit}`);

if (buildOut._videoMissing) {
  errors.push('VIDEO_MISSING_PLACEHOLDER');
}

const validation = errors.length ? errors.join('; ') : 'OK';

return [{ json: {
  coverLetter: text,
  row,
  _videoShareUrl: buildOut._videoShareUrl,
  _validation: validation,
} }];
"""

# ─── Map Sheet Fields ─────────────────────────────────────────────────────────
NEW_MAP_SHEET = r"""const d = $input.first().json;
return [{ json: {
  row_number: d.row._rowNumber,
  'Cover Letter': d.coverLetter,
  'TOS Check': d._validation,
} }];
"""

# ─── Fetch Catalog params ─────────────────────────────────────────────────────
NEW_FETCH_CATALOG_PARAMS = {
    "url": "https://raw.githubusercontent.com/scubarichard/1altx-site/master/data/catalog.json",
    "options": {"response": {"response": {"responseFormat": "json"}}},
}

# ─── Anthropic API Call params (bump max_tokens) ──────────────────────────────
NEW_ANTHROPIC_JSON_BODY = (
    "={{ JSON.stringify({"
    " model: 'claude-sonnet-4-6',"
    " max_tokens: 2000,"
    " system: $json.system,"
    " messages: [{ role: 'user', content: $json.user }]"
    " }) }}"
)

# ─── Update Sheet params (add TOS Check column) ───────────────────────────────
NEW_UPDATE_SHEET_COLUMNS = {
    "mappingMode": "defineBelow",
    "value": {
        "row_number": "={{ $json.row_number }}",
        "Cover Letter": "={{ $json['Cover Letter'] }}",
        "TOS Check": "={{ $json['TOS Check'] }}",
    },
    "matchingColumns": ["row_number"],
    "schema": [],
}

# ─── Apply patches ────────────────────────────────────────────────────────────
UA = "Mozilla/5.0 (X11; Linux x86_64) curl-compatible"
req = urllib.request.Request(
    f"{N8N_BASE}/api/v1/workflows/{WORKFLOW_ID}",
    headers={"X-N8N-API-KEY": N8N_KEY, "User-Agent": UA, "Accept": "application/json"},
)
wf = json.loads(urllib.request.urlopen(req).read())

patches = {
    "Find Row": ("code", "jsCode", NEW_FIND_ROW),
    "Build Claude Request": ("code", "jsCode", NEW_BUILD_CLAUDE),
    "Parse Response": ("code", "jsCode", NEW_PARSE_RESPONSE),
    "Map Sheet Fields": ("code", "jsCode", NEW_MAP_SHEET),
}

for n in wf["nodes"]:
    nm = n["name"]
    if nm in patches:
        kind, field, value = patches[nm]
        n["parameters"][field] = value
        print(f"  patched {nm} ({field}, {len(value)} chars)")
    elif nm == "Fetch Catalog":
        n["parameters"]["url"] = NEW_FETCH_CATALOG_PARAMS["url"]
        n["parameters"]["options"] = NEW_FETCH_CATALOG_PARAMS["options"]
        print(f"  patched Fetch Catalog url+options")
    elif nm == "Anthropic API Call":
        n["parameters"]["jsonBody"] = NEW_ANTHROPIC_JSON_BODY
        print(f"  patched Anthropic API Call (max_tokens=2000)")
    elif nm == "Update Sheet":
        n["parameters"]["columns"] = NEW_UPDATE_SHEET_COLUMNS
        print(f"  patched Update Sheet (added TOS Check)")

# Strip n8n-rejected settings keys
allowed = {"executionOrder", "saveManualExecutions", "timezone"}
settings = wf.get("settings", {})
wf["settings"] = {k: v for k, v in settings.items() if k in allowed}

# n8n public API also rejects extra top-level fields on PUT
allowed_top = {"name", "nodes", "connections", "settings", "staticData"}
wf_put = {k: v for k, v in wf.items() if k in allowed_top}

put_req = urllib.request.Request(
    f"{N8N_BASE}/api/v1/workflows/{WORKFLOW_ID}",
    data=json.dumps(wf_put).encode(),
    headers={
        "X-N8N-API-KEY": N8N_KEY,
        "Content-Type": "application/json",
        "User-Agent": UA,
        "Accept": "application/json",
    },
    method="PUT",
)
try:
    resp = urllib.request.urlopen(put_req).read()
    print("PUT succeeded:", json.loads(resp).get("id"))
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"PUT failed: {e.code} {body[:500]}")
    sys.exit(1)
