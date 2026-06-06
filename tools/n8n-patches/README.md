# n8n workflow patches

Scripts that mutate live n8n workflows via the public API. Each script is idempotent — re-running it against the same workflow restores the patched state if anyone edits in the UI.

## patch_07c_locked_format.py

Patches the **07C cover-letter lane** inside workflow `WyD6dxFAGPquiqPG` ("1AltX Upwork Pipeline — Unified") with the locked-format prompt (Richard's 2026-06-06 spec).

**What it changes:**
- **Find Row** — prefers col AK (PVC Variant) for the share.descript URL, falls back to scanning all cells, sets `_videoMissing` flag.
- **Fetch Catalog** — URL → `data/catalog.json` (authoritative catalog, not the brief markdown).
- **Build Claude Request** — full locked-format system prompt: LINE 1 video line, hook, 2-3 catalog samples (exact titles + URLs only, sourced from catalog.json), solution approach, verbatim credentials block, one of 5 close types by job, signature with agency-exception. Catalog is reassembled from n8n's auto-split items via `$input.all()`.
- **Anthropic API Call** — `max_tokens` bumped from 1024 → 2000.
- **Parse Response** — validation: Line 1 must start with "I recorded this specifically for your posting →", no `web.descript.com`, length ≤ 5000, credentials block present, signature present, no markdown leakage, TOS blacklist scan, video-missing flag. Emits `_validation` field.
- **Map Sheet Fields** — also writes validation status to col AL (TOS Check).
- **Update Sheet** — added `TOS Check` column mapping.

**Run:**
```bash
/home/richard/proposal-video-creator/.venv/bin/python3 patch_07c_locked_format.py
```

Requires:
- `az` CLI logged into the Dakona tenant (pulls `n8n-api-key` from `kvdaxdakonapilot`).
- Network access to `n8n.dakona.net`.

After patching, **deactivate then reactivate** the workflow so the n8n webhook reloads the new code:
```bash
N8N_KEY=$(az keyvault secret show --vault-name kvdaxdakonapilot --name n8n-api-key --query value -o tsv)
UA="Mozilla/5.0 (X11; Linux x86_64) curl-compatible"
curl -s -X POST -A "$UA" -H "X-N8N-API-KEY: $N8N_KEY" \
  "https://n8n.dakona.net/api/v1/workflows/WyD6dxFAGPquiqPG/deactivate"
curl -s -X POST -A "$UA" -H "X-N8N-API-KEY: $N8N_KEY" \
  "https://n8n.dakona.net/api/v1/workflows/WyD6dxFAGPquiqPG/activate"
```

**Test:**
```bash
curl -s -X POST "https://n8n.dakona.net/webhook/7c-proposal-prep" \
  -H "Content-Type: application/json" -d '{"row_number": 28}'
```
Expected response body: `OK`. Read back `Cover Letter` (col Q) and `TOS Check` (col AL) on row 28 in the UpWork_Log sheet. First line of Q must be `I recorded this specifically for your posting → https://share.descript.com/view/...`. TOS Check must be `OK` (or a semicolon-separated list of validation failures).

## Cloudflare gotcha

n8n.dakona.net is behind Cloudflare; the default `python-urllib/3.x` User-Agent gets blocked with `error code: 1010`. Always send a browser-like UA on requests from Python scripts.
