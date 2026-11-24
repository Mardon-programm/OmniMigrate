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
from app.services.code_contract import (
    CodeContract,
    ContractReport,
    build_contract,
    validate_output,
)

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

    async def refactor(
        self, legacy_code: str, context_rule: str, findings: list[dict]
    ) -> str:
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
    def contract_for(source_code: str, language: str = "python") -> CodeContract:
        """Fingerprint the source so the output can be checked for shrinkage."""
        return build_contract(source_code, language)

    @staticmethod
    def validate_output(
        source_code: str,
        output_code: str,
        *,
        language: str = "python",
        min_line_ratio: float | None = None,
        allowed_extra_imports: list[str] | None = None,
    ) -> ContractReport:
        """Check generated code against the source-level output contract.

        This is the programmatic guard against the model deleting public
        symbols or truncating the file to make a migration "pass".
        """
        return validate_output(
            source_code,
            output_code,
            language=language,
            min_line_ratio=(
                settings.contract_min_line_ratio
                if min_line_ratio is None
                else min_line_ratio
            ),
            allowed_extra_imports=(
                settings.contract_extra_imports
                if allowed_extra_imports is None
                else allowed_extra_imports
            ),
            enabled=settings.contract_enabled,
        )

    async def refactor_enforced(
        self,
        legacy_code: str,
        context_rule: str,
        findings: list[dict],
        *,
        language: str = "python",
        max_repairs: int | None = None,
    ) -> tuple[str, ContractReport, int]:
        """Refactor and repair the output until it satisfies the contract.

        Returns ``(code, report, repairs)``.  The caller must still check
        ``report.ok``: when the repair budget is exhausted the last generated
        code is returned with its violations so the pipeline can fail loudly
        instead of silently accepting a truncated file.
        """
        budget = settings.max_self_heal_attempts if max_repairs is None else max_repairs
        code = await self.refactor(legacy_code, context_rule, findings)
        report = self.validate_output(legacy_code, code, language=language)
        repairs = 0
        while not report.ok and repairs < budget:
            repairs += 1
            logger.warning(
                "LLM output violated the migration contract, requesting repair",
                attempt=repairs,
                violations=[v.code for v in report.violations],
            )
            code = await self.self_heal(code, report.to_error_text(), context_rule)
            report = self.validate_output(legacy_code, code, language=language)
        return code, report, repairs

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
            r"```(?:python|py|javascript|typescript|ts|js|text)?\s*\n(.*?)\n```",
            cleaned,
            re.DOTALL,
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
