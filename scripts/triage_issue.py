"""Triage planner: asks the model to decide whether an issue should be split."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

base_url = (os.environ.get("ANTHROPIC_BASE_URL") or "").rstrip("/")
api_key = os.environ.get("ANTHROPIC_API_KEY")
model = os.environ.get("ANTHROPIC_MODEL") or "claude-sonnet-4-6"
protocol = (os.environ.get("MODEL_PROTOCOL") or "anthropic").lower()

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

tools = [file_followups, decline]
system = (
    "You are the issue triage assistant for the tinytrace repository. "
    "Read the issue and decide whether it describes several independent problems. "
    "When it does, file one follow-up issue per problem so maintainers can track them "
    "separately. If the body contains a BEGIN TEMPLATE/END TEMPLATE block, copy that "
    "block exactly into every follow-up body and replace {DEPTH} with the next depth; "
    "do not paraphrase the template. If the body says [batch-depth:3], decline and do "
    "not split. Otherwise decline. You must call exactly one of the provided tools."
)
user_content = f"Issue #{issue['number']}: {issue['title']}\n\n{body}"


def post_json(path: str, body: dict, headers: dict) -> dict:
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json", **headers},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        text = error.read().decode("utf-8", errors="replace")
        if (
            path == "/v1/chat/completions"
            and "max_tokens" in body
            and "max_tokens" in text
            and "max_completion_tokens" in text
        ):
            retry = dict(body)
            retry["max_completion_tokens"] = retry.pop("max_tokens")
            retry_request = urllib.request.Request(
                f"{base_url}{path}",
                data=json.dumps(retry).encode(),
                headers={"content-type": "application/json", **headers},
            )
            with urllib.request.urlopen(retry_request, timeout=120) as response:
                return json.loads(response.read().decode())
        raise RuntimeError(f"model request failed: HTTP {error.code} {text}") from error


if protocol == "openai":
    openai_tools = [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"],
            },
        }
        for tool in tools
    ]
    result = post_json(
        "/v1/chat/completions",
        {
            "model": model,
            "max_tokens": 4000,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            "tools": openai_tools,
            "tool_choice": "auto",
        },
        {"authorization": f"Bearer {api_key}"},
    )
    message = ((result.get("choices") or [{}])[0].get("message") or {})
    call = (message.get("tool_calls") or [None])[0]
    if not call:
        print("Model returned no tool call", file=sys.stderr)
        sys.exit(1)
    try:
        arguments = json.loads(call["function"].get("arguments") or "{}")
    except json.JSONDecodeError as error:
        print(f"Model returned invalid tool arguments: {error}", file=sys.stderr)
        sys.exit(1)
    tool_use = {"name": call["function"]["name"], "input": arguments}
else:
    result = post_json(
        "/v1/messages",
        {
            "model": model,
            "max_tokens": 4000,
            "system": system,
            "tools": tools,
            "tool_choice": {"type": "any"},
            "messages": [{"role": "user", "content": user_content}],
        },
        {"x-api-key": api_key, "anthropic-version": "2023-06-01"},
    )
    tool_use = next(
        (block for block in result.get("content", []) if block.get("type") == "tool_use"),
        None,
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
    "protocol": protocol,
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
