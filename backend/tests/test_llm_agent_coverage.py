"""Tests targeting uncovered lines in app/services/llm_agent.py."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.services.llm_agent import LLMAgent, LLMUnavailableError


class TestInitBaseUrl:
    def test_base_url_set_when_configured(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.llm_agent.settings",
            SimpleNamespace(
                openai_model="gpt-4o",
                llm_temperature=0.2,
                llm_max_tokens=4096,
                openai_base_url="http://localhost:8080/v1",
                openai_api_key="",
            ),
        )
        agent = LLMAgent()
        assert agent._request_args["base_url"] == "http://localhost:8080/v1"

    def test_base_url_not_set_when_none(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.llm_agent.settings",
            SimpleNamespace(
                openai_model="gpt-4o",
                llm_temperature=0.2,
                llm_max_tokens=4096,
                openai_base_url=None,
                openai_api_key="",
            ),
        )
        agent = LLMAgent()
        assert "base_url" not in agent._request_args


class TestClientProperty:
    def test_raises_when_no_api_key(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.llm_agent.settings",
            SimpleNamespace(
                openai_model="gpt-4o",
                llm_temperature=0.1,
                llm_max_tokens=2048,
                openai_base_url=None,
                openai_api_key="",
            ),
        )
        agent = LLMAgent()
        with pytest.raises(LLMUnavailableError, match="OPENAI_API_KEY"):
            _ = agent.client

    def test_creates_client_when_key_present(self, monkeypatch):
        mock_client = MagicMock()
        mock_cls = MagicMock(return_value=mock_client)
        monkeypatch.setattr(
            "app.services.llm_agent.settings",
            SimpleNamespace(
                openai_model="gpt-4o",
                llm_temperature=0.1,
                llm_max_tokens=2048,
                openai_base_url=None,
                openai_api_key="sk-test-key",
            ),
        )
        monkeypatch.setattr("app.services.llm_agent.AsyncOpenAI", mock_cls)
        agent = LLMAgent()
        result = agent.client
        assert result is mock_client
        mock_cls.assert_called_once_with(api_key="sk-test-key", base_url=None)

    def test_caches_client(self, monkeypatch):
        mock_client = MagicMock()
        monkeypatch.setattr(
            "app.services.llm_agent.settings",
            SimpleNamespace(
                openai_model="gpt-4o",
                llm_temperature=0.1,
                llm_max_tokens=2048,
                openai_base_url=None,
                openai_api_key="sk-test",
            ),
        )
        monkeypatch.setattr(
            "app.services.llm_agent.AsyncOpenAI", MagicMock(return_value=mock_client)
        )
        agent = LLMAgent()
        first = agent.client
        second = agent.client
        assert first is second


class TestComplete:
    @pytest.fixture()
    def agent(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.llm_agent.settings",
            SimpleNamespace(
                openai_model="gpt-4o",
                llm_temperature=0.1,
                llm_max_tokens=2048,
                openai_base_url=None,
                openai_api_key="sk-test",
            ),
        )
        return LLMAgent()

    async def test_returns_content(self, agent):
        mock_message = SimpleNamespace(content="print('hello')")
        mock_choice = SimpleNamespace(message=mock_message)
        mock_response = SimpleNamespace(choices=[mock_choice])

        mock_create = AsyncMock(return_value=mock_response)
        mock_completions = SimpleNamespace(create=mock_create)
        mock_chat = SimpleNamespace(completions=mock_completions)

        mock_client = SimpleNamespace(chat=mock_chat)
        agent._client = mock_client

        result = await agent._complete("system prompt", "user prompt")
        assert result == "print('hello')"
        mock_create.assert_called_once()

    async def test_raises_on_empty_content(self, agent):
        mock_message = SimpleNamespace(content=None)
        mock_choice = SimpleNamespace(message=mock_message)
        mock_response = SimpleNamespace(choices=[mock_choice])

        mock_create = AsyncMock(return_value=mock_response)
        mock_completions = SimpleNamespace(create=mock_create)
        mock_chat = SimpleNamespace(completions=mock_completions)

        mock_client = SimpleNamespace(chat=mock_chat)
        agent._client = mock_client

        with pytest.raises(LLMUnavailableError, match="empty response"):
            await agent._complete("system", "user")

    async def test_raises_on_empty_string_content(self, agent):
        mock_message = SimpleNamespace(content="")
        mock_choice = SimpleNamespace(message=mock_message)
        mock_response = SimpleNamespace(choices=[mock_choice])

        mock_create = AsyncMock(return_value=mock_response)
        mock_completions = SimpleNamespace(create=mock_create)
        mock_chat = SimpleNamespace(completions=mock_completions)

        mock_client = SimpleNamespace(chat=mock_chat)
        agent._client = mock_client

        with pytest.raises(LLMUnavailableError, match="empty response"):
            await agent._complete("system", "user")


class TestRefactor:
    async def test_refactor_calls_complete_and_extracts(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.llm_agent.settings",
            SimpleNamespace(
                openai_model="gpt-4o",
                llm_temperature=0.1,
                llm_max_tokens=2048,
                openai_base_url=None,
                openai_api_key="sk-test",
            ),
        )
        agent = LLMAgent()
        agent._client = MagicMock()

        mock_complete = AsyncMock(return_value="```python\ndef f():\n    return 1\n```")
        monkeypatch.setattr(agent, "_complete", mock_complete)

        result = await agent.refactor("old code", "modernize", [{"line": 1, "message": "x"}])
        assert result == "def f():\n    return 1\n"
        mock_complete.assert_called_once()


class TestSelfHeal:
    async def test_self_heal_calls_complete_and_extracts(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.llm_agent.settings",
            SimpleNamespace(
                openai_model="gpt-4o",
                llm_temperature=0.1,
                llm_max_tokens=2048,
                openai_base_url=None,
                openai_api_key="sk-test",
            ),
        )
        agent = LLMAgent()
        agent._client = MagicMock()

        mock_complete = AsyncMock(return_value="def fixed():\n    pass\n")
        monkeypatch.setattr(agent, "_complete", mock_complete)

        result = await agent.self_heal("broken code", "NameError", "rule")
        assert result == "def fixed():\n    pass"
        mock_complete.assert_called_once()


class TestGetSystemPrompt:
    def test_returns_expected_string(self):
        prompt = LLMAgent._get_system_prompt()
        assert "OmniMigrate Core Engine" in prompt
        assert "ONLY the raw" in prompt
