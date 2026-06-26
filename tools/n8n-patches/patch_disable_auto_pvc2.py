#!/usr/bin/env python3
"""
Patch f2RPzoJ2m45Odu4k (1AltX Upwork — Unified Pipeline) to disable the
auto-PVC2 trigger downstream of the scoring lane. After the patch:
- The scoring lane (Sonnet 4.6) keeps running every 15 min and writes its
  verdict to UpWork_Log.
- The "Score >= 14? -> Trigger PVC2 (wait) -> Trigger 07C" chain no longer
  fires; the "Update Google Sheet" node's onward connection to "Score >= 14?"
  is removed.
- PVC2 must now be fired manually after Nautilus runs rank_top10.py, so
  HeyGen credits are only burned on top-ranked rows (Connects-capped at 10).

WHY: pre-patch, Sonnet's auto-PVC2 trigger fired on every Hot row, which
collided with the manual triage flow (rank cap of 10, dedup against
ProcessedLog, G1 budget overrides). HeyGen credits were getting burned on
rows that Richard wouldn't actually submit. With this patch, Sonnet is the
single source of truth for scoring, Nautilus owns ranking + PVC2 firing.

Idempotent. Preserves all other nodes, connections, settings.
"""
import json
import subprocess
import sys
import urllib.request

WORKFLOW_ID = "f2RPzoJ2m45Odu4k"
N8N_BASE = "https://n8n.dakona.net"
UA = "Mozilla/5.0 (X11; Linux x86_64) curl-compatible"

# Nodes whose outbound connections should be removed
NODES_TO_DETACH = ["Update Google Sheet"]
# The connection target we're severing (so we can verify)
SEVERED_TARGET = "Score >= 14?"

N8N_KEY = subprocess.check_output(
    ["az", "keyvault", "secret", "show",
     "--vault-name", "kvdaxdakonapilot",
     "--name", "n8n-api-key",
     "--query", "value", "-o", "tsv"],
    text=True,
).strip()


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
    connections = wf.get("connections", {})

    # Find connections from "Update Google Sheet" that lead to "Score >= 14?"
    # and remove just that hop. Keep any other downstream branches intact.
    patched = []
    no_op = []
    for src in NODES_TO_DETACH:
        if src not in connections:
            no_op.append(f"{src} (no outbound connections)")
            continue
        main_branches = connections[src].get("main", [])
        new_branches = []
        changed = False
        for branch in main_branches:
            kept = [c for c in branch if c.get("node") != SEVERED_TARGET]
            if len(kept) != len(branch):
                changed = True
            new_branches.append(kept)
        # Strip trailing empty branches if all removed
        while new_branches and not new_branches[-1]:
            new_branches.pop()
        if changed:
            if new_branches:
                connections[src]["main"] = new_branches
            else:
                del connections[src]
            patched.append(f"{src} -> {SEVERED_TARGET}")
        else:
            no_op.append(f"{src} (already detached from {SEVERED_TARGET})")

    print(f"Patched: {patched or 'nothing (already at target state)'}", file=sys.stderr)
    print(f"No-op:   {no_op}", file=sys.stderr)

    if not patched:
        print("NO-OP: workflow already at target state", file=sys.stderr)
        return 0

    # Strip settings per memory pitfall (n8n API rejects extra keys on PUT)
    wf["settings"] = {
        k: v for k, v in wf.get("settings", {}).items()
        if k in ("executionOrder", "saveManualExecutions", "timezone")
    }
    payload = {
        "name": wf["name"],
        "nodes": wf["nodes"],
        "connections": connections,
        "settings": wf["settings"],
    }
    result = put_workflow(payload)
    print(f"OK: updated workflow {result.get('id')} versionId={result.get('versionId')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
