from __future__ import annotations

import sqlite3
from typing import Any

from ..repositories import catalog
from ..settings import get_settings


def chat_with_llm(connection: sqlite3.Connection, payload: Any) -> dict:
    from openai import OpenAI

    from .tools import COPILOT_TOOLS, execute_tool

    settings = get_settings()
    client = OpenAI(base_url=settings.llm_api_base, api_key=settings.llm_api_key)

    messages = [{"role": m.role, "content": m.content} for m in payload.messages]
    system = (
        "You are BDA Copilot, an assistant for protein binder design workflows. "
        "Use available tools to query candidates, interpret results, and suggest workflow changes."
    )

    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[{"role": "system", "content": system}, *messages],
        tools=COPILOT_TOOLS,
        tool_choice="auto",
    )

    choice = response.choices[0]
    message = choice.message

    if message.tool_calls:
        tool_results = []
        for call in message.tool_calls:
            result = execute_tool(connection, call.function.name, call.function.arguments, payload.project_id)
            tool_results.append(result)
        return {
            "mode": "llm_with_tools",
            "message": message.content or str(tool_results[0]) if tool_results else "Done.",
            "skill_used": payload.skill or call.function.name,
            "structured": {"tool_results": tool_results},
        }

    return {
        "mode": "llm",
        "message": message.content or "",
        "skill_used": payload.skill or "general",
        "structured": {"project_id": payload.project_id},
    }
