from backend.app.copilot import provider
from backend.app.copilot.biomaterials_skill import is_programmable_biomaterials_question


def test_project_followup_is_in_biomaterials_scope():
    assert is_programmable_biomaterials_question("这个项目下一步怎么做？")


def test_deepseek_structured_calls_disable_thinking(monkeypatch):
    captured = {}

    class FakeMessage:
        content = '{"claims":[]}'
        tool_calls = []

    class FakeResponse:
        choices = [type("Choice", (), {"message": FakeMessage()})()]

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return FakeResponse()

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.chat = type("Chat", (), {"completions": FakeCompletions()})()

    monkeypatch.setattr("openai.OpenAI", FakeOpenAI)
    from backend.app.settings import get_settings

    settings = get_settings()
    original = (settings.llm_api_base, settings.llm_model, settings.llm_api_key)
    settings.llm_api_base = "https://api.deepseek.com/v1"
    settings.llm_model = "deepseek-v4-pro"
    settings.llm_api_key = "test"
    try:
        client = provider.OpenAICompatibleProvider()
        client.chat(
            [{"role": "user", "content": "extract"}],
            response_format={"type": "json_object"},
        )
    finally:
        settings.llm_api_base, settings.llm_model, settings.llm_api_key = original

    assert captured["extra_body"] == {"thinking": {"type": "disabled"}}
