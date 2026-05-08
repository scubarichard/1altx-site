# 1AltX site - project memory

## Upwork application triage

This repo includes the **upwork-triage** subagent for reviewing Upwork
application rows in Richard's Upwork tracking sheet.

**Invoke** in any Claude Code session in this repo:

    triage rows N-M

**Files:**
- `.claude/agents/upwork-triage.md` - agent definition (rubric, skip criteria, product catalog)
- `tools/upwork-triage/upwork_triage.py` - CLI for Sheets I/O
- `tools/upwork-triage/runs/` - historical run logs

**Setup required to run end-to-end:**
1. Google Cloud service account, Sheets API enabled, JSON key downloaded
2. Sheet shared with service account email as Editor
3. Env vars set:
   - `UPWORK_SHEET_ID=11cydvXB7zb38FGSqrLTXEnikIK5gec1FSe3nK3Hy_BY`
   - `UPWORK_SA_KEY=<path to service account JSON>`
4. `pip install -r tools/upwork-triage/requirements.txt`

Until setup is complete, the agent can still produce paste-down lists
by reading the sheet through the Google Drive MCP and outputting the
column W values for manual paste.

**Process flow:** read sheet rows -> apply skip criteria + rubric ->
write column W decisions back. The `sending to n8n` step (downstream
proposal submission) is a SEPARATE process - triage stops at writing
column W.
