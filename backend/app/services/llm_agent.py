from __future__ import annotations

import re

import structlog
from openai import AsyncOpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.prompts import build_refactor_prompt, build_self_heal_prompt

logger = structlog.get_logger(__name__)


class LLMUnavailableError(RuntimeError):
    """Raised when the LLM backend cannot be reached or the response is unusable."""


class LLMAgent:
    """Wrapper around the OpenAI SDK for the autonomous refactoring pipeline."""

    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None
        self._request_args: dict = {
            "model": settings.openai_model,
            "temperature": settings.llm_temperature,
            "max_tokens": settings.llm_max_tokens,
        }
        if settings.openai_base_url:
            self._request_args["base_url"] = settings.openai_base_url

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            if not settings.openai_api_key:
                raise LLMUnavailableError(
                    "OPENAI_API_KEY is not configured. "
                    "Set it in the backend .env to enable LLM refactoring."
                )
            self._client = AsyncOpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
            )
        return self._client

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def _complete(self, system: str, user: str) -> str:
        response = await self.client.chat.completions.create(
            model=settings.openai_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = response.choices[0].message.content
        if not content:
            raise LLMUnavailableError("LLM returned an empty response.")
        return content

    async def refactor(self, legacy_code: str, context_rule: str, findings: list[dict]) -> str:
        """Run a single refactoring pass and return only the raw code."""
        prompt = build_refactor_prompt(legacy_code, context_rule, findings)
        raw = await self._complete(self._get_system_prompt(), prompt)
        return self._extract_code(raw)

    async def self_heal(self, broken_code: str, error: str, context_rule: str) -> str:
        """Ask the model to repair code that failed sandbox verification."""
        prompt = build_self_heal_prompt(context_rule, broken_code, error)
        raw = await self._complete(self._get_system_prompt(), prompt)
        return self._extract_code(raw)

    @staticmethod
    def _get_system_prompt() -> str:
        # The system prompt is constructed per-run via build_refactor_prompt.
        return (
            "You are OmniMigrate Core Engine, an elite automated AI code migration "
            "and modernization system. You always respond with ONLY the raw "
            "refactored code, no markdown fences, no explanations."
        )

    @staticmethod
    def _extract_code(raw: str) -> str:
        """Strip accidental markdown fences and conversational filler."""
        cleaned = raw.strip()
        fence = re.search(
            r"```(?:python|py|javascript|typescript|ts|js|text)?\s*\n(.*?)\n```", cleaned, re.DOTALL
        )
        if fence:
            return fence.group(1).rstrip() + "\n"
        # Remove a leading conversational sentence if the model ignored instructions.
        cleaned = re.sub(
            r"^(Here(?:'s| is)(?: the)? (?:refactored|migrated|updated)? code[^:]*:?\s*\n+)",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        return cleaned
