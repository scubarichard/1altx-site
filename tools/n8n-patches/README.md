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

## patch_unified_scorer_prompt_sync.py

Patches the **scoring lane** of workflow `f2RPzoJ2m45Odu4k` ("1AltX Upwork — Unified Pipeline") so its `Build Anthropic Request` node mirrors `score_rows.py` (canonical source: `~/Dropbox/.../proposal-video-creator/pvc2/score_rows.py`).

**What it changes** — replaces the older Sonnet prompt with the synced one:
- Adds **X1-X6 veto layer** (LangChain/Docker/voice/teaching/FTE/Salesforce-Apex hard skips).
- Adds **client_signal** field with `new_blank_slate` guidance (blank-slate clients get V=6-8 instead of default V=3).
- Collapses tiers: `status="Pursue|Ignore"` (no Apply), `priority_flag="🔥 Hot|⏭ Skip"`. PVC2 gate stays at W≥14.
- Keeps Sonnet 4.6 + the existing JSON output schema (Map Fields downstream silently ignores additive fields).

**Why this exists**: pre-2026-06-21, the unified pipeline silently re-scored Hot rows ~15 min after `score_rows.py` triage, demoting edge cases (W=14-16) below threshold and short-circuiting PVC2 renders (`SKIP: Score 13 < 14 — not worth producing`). See memory `project_unified_scorer_prompt_sync.md`.

**Run** (idempotent — re-run anytime to restore the synced prompt if anyone edits in the n8n UI):
```bash
/home/richard/proposal-video-creator/.venv/bin/python3 patch_unified_scorer_prompt_sync.py
```
First run prints `Patched 'Build Anthropic Request': N -> M chars`; subsequent runs print `NO-OP: ... already matches synced prompt`.

**Drift risk**: the prompt lives in two places now (this script's `SCORER_JSCODE` constant + `score_rows.py::SCORE_PROMPT`). When you change one, update the other and re-run this script. Future fix: extract to a shared prompt file both scorers read.

**Test**: there's no equivalent of 07C's `7c-proposal-prep` webhook for the scorer's `7b-score-now` lane that returns a deterministic body. After patching, watch the next scheduled execution (every 15 min, on the `Every 15 Min (Scoring)` schedule trigger) and confirm new Hot rows carry `client_signal` and `exclusion_gate` in `Scoring Notes` (col AE) when a veto fires.

## Cloudflare gotcha

n8n.dakona.net is behind Cloudflare; the default `python-urllib/3.x` User-Agent gets blocked with `error code: 1010`. Always send a browser-like UA on requests from Python scripts.
