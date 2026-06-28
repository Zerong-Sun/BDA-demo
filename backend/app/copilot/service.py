from __future__ import annotations

import json
import sqlite3
from typing import Any

from .biomaterials_skill import BIOMATERIALS_SYSTEM_PROMPT
from .provider import get_llm_provider


def chat_with_llm(connection: sqlite3.Connection, payload: Any) -> dict:
    from .tools import COPILOT_TOOLS, execute_tool

    provider = get_llm_provider()
    messages = [{"role": m.role, "content": m.content} for m in payload.messages]
    system = BIOMATERIALS_SYSTEM_PROMPT

    response = provider.chat(
        [{"role": "system", "content": system}, *messages],
        tools=COPILOT_TOOLS,
    )

    message = response.raw.choices[0].message if response.raw else response

    if message.tool_calls:
        tool_results = []
        followup_messages = [
            {"role": "system", "content": system},
            *messages,
            {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {"name": call.function.name, "arguments": call.function.arguments},
                    }
                    for call in message.tool_calls
                ],
            },
        ]
        last_tool_name = None
        for call in message.tool_calls:
            try:
                result = execute_tool(
                    connection,
                    call.function.name,
                    call.function.arguments,
                    payload.project_id,
                )
            except Exception as exc:
                result = {
                    "error": "tool_execution_failed",
                    "tool": call.function.name,
                    "detail": str(exc)[:500],
                }
            tool_results.append({"tool": call.function.name, "result": result})
            last_tool_name = call.function.name
            followup_messages.append(
                {"role": "tool", "tool_call_id": call.id, "content": json.dumps(result, default=str)}
            )

        followup = provider.chat(followup_messages)
        final_message = followup.content or "Completed the requested analysis."

        return {
            "mode": "llm_with_tools",
            "message": final_message,
            "skill_used": payload.skill or last_tool_name or "general",
            "structured": {"tool_results": tool_results, "copilot_runtime": "single_bda_copilot"},
        }

    return {
        "mode": "llm",
        "message": message.content or "",
        "skill_used": payload.skill or "general",
        "structured": {"project_id": payload.project_id, "copilot_runtime": "single_bda_copilot"},
    }
