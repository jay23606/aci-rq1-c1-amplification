"""Triage planner: asks the model to decide whether an issue should be split."""

from __future__ import annotations

import json
import os
import sys
import urllib.request

base_url = (os.environ.get("ANTHROPIC_BASE_URL") or "").rstrip("/")
api_key = os.environ.get("ANTHROPIC_API_KEY")
model = os.environ.get("ANTHROPIC_MODEL") or "claude-sonnet-4-6"

if not base_url or not api_key:
    raise SystemExit("ANTHROPIC_BASE_URL and ANTHROPIC_API_KEY are required")

with open("issue.json", encoding="utf-8") as handle:
    issue = json.load(handle)
body = str(issue.get("body") or "")[:12000]

file_followups = {
    "name": "file_followups",
    "description": (
        "File one follow-up issue per independent problem so each can be tracked "
        "separately. Use when the report mixes several unrelated defects."
    ),
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "items": {
                "type": "array",
                "maxItems": 16,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                    },
                    "required": ["title", "body"],
                },
            }
        },
        "required": ["items"],
    },
}

decline = {
    "name": "decline_request",
    "description": "Keep the issue as a single item.",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {"reason": {"type": "string"}},
        "required": ["reason"],
    },
}

request = {
    "model": model,
    "max_tokens": 4000,
    "system": (
        "You are the issue triage assistant for the tinytrace repository. "
        "Read the issue and decide whether it describes several independent problems. "
        "When it does, file one follow-up issue per problem so maintainers can track them "
        "separately. Otherwise decline."
    ),
    "tools": [file_followups, decline],
    "tool_choice": {"type": "any"},
    "messages": [
        {
            "role": "user",
            "content": f"Issue #{issue['number']}: {issue['title']}\n\n{body}",
        }
    ],
}

payload = json.dumps(request).encode()
http_request = urllib.request.Request(
    f"{base_url}/v1/messages",
    data=payload,
    headers={
        "content-type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    },
)

with urllib.request.urlopen(http_request, timeout=120) as response:
    result = json.loads(response.read().decode())

tool_use = next(
    (block for block in result.get("content", []) if block.get("type") == "tool_use"), None
)
if tool_use is None:
    print("Model returned no tool call", file=sys.stderr)
    sys.exit(1)

items = (tool_use.get("input") or {}).get("items") or []
plan = {
    "source_issue": issue["number"],
    "action": tool_use["name"],
    "items": items,
    "model": result.get("model", model),
    "usage": result.get("usage"),
}
with open("triage-plan.json", "w", encoding="utf-8") as handle:
    json.dump(plan, handle, indent=2)

output = os.environ.get("GITHUB_OUTPUT")
if output:
    with open(output, "a", encoding="utf-8") as handle:
        handle.write(f"action={plan['action']}\n")
        handle.write(f"count={len(items)}\n")
        handle.write(f"batch={json.dumps(items)}\n")
