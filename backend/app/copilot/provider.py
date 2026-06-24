from __future__ import annotations

from typing import Any, Protocol


class LLMResponse:
    def __init__(self, content: str, tool_calls: list | None = None, raw: Any = None):
        self.content = content
        self.tool_calls = tool_calls or []
        self.raw = raw


class LLMProvider(Protocol):
    def chat(self, messages: list[dict], tools: list | None = None, response_format: dict | None = None) -> LLMResponse: ...

    def stream(self, messages: list[dict], tools: list | None = None): ...


class OpenAICompatibleProvider:
    """Works with OpenAI, Azure OpenAI, local vLLM, and Ollama (OpenAI-compatible)."""

    def __init__(self) -> None:
        from openai import OpenAI

        from ..settings import get_settings

        settings = get_settings()
        self._client = OpenAI(base_url=settings.llm_api_base, api_key=settings.llm_api_key)
        self._model = settings.llm_model
        self._is_deepseek = "api.deepseek.com" in settings.llm_api_base.lower()

    def chat(self, messages: list[dict], tools: list | None = None, response_format: dict | None = None) -> LLMResponse:
        kwargs: dict = {"model": self._model, "messages": messages}
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        if response_format:
            kwargs["response_format"] = response_format
        if self._is_deepseek and (tools or response_format):
            # DeepSeek defaults to thinking mode. Structured extraction does not
            # benefit from hidden reasoning, and tool turns require preserving
            # reasoning_content across messages. Disable thinking for these
            # compatibility-sensitive paths.
            kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
        response = self._client.chat.completions.create(**kwargs)
        message = response.choices[0].message
        return LLMResponse(
            content=message.content or "",
            tool_calls=list(message.tool_calls or []),
            raw=response,
        )

    def stream(self, messages: list[dict], tools: list | None = None):
        stream = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content


def get_llm_provider() -> LLMProvider:
    return OpenAICompatibleProvider()
