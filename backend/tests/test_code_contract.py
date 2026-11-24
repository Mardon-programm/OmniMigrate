"""Tests for the anti-shrinkage output contract."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.services.code_contract import (
    CodeContractError,
    build_contract,
    count_code_lines,
    count_logic_lines,
    validate_output,
)
from app.services.llm_agent import LLMAgent

SOURCE = '''"""Legacy module."""

import os

API_TOKEN = "secret"

class LegacyCart:
    def add_item(self, sku):
        return sku

def load_config(path):
    return os.path.join(path, "config")

def fetch_catalog(endpoint):
    return endpoint
'''

COMPLETE = '''"""Legacy module."""

import os

API_TOKEN = os.environ.get("API_TOKEN", "secret")

class LegacyCart:
    def add_item(self, sku: str) -> str:
        return sku

def load_config(path: str) -> str:
    return os.path.join(path, "config")

def fetch_catalog(endpoint: str) -> str:
    return endpoint
'''

PY2_SOURCE = '''# -*- coding: utf-8 -*-
"""Legacy Python 2 module."""

import urllib2

TOKEN = "x"

class legacy_cart:
    def describe(self):
        print "cart"

def load_config(path):
    return path
'''

PY2_COMPLETE = '''"""Legacy Python 2 module."""

import urllib.request

TOKEN = "x"

class legacy_cart:
    def describe(self) -> None:
        print("cart")

def load_config(path: str) -> str:
    return path
'''


def _codes(report):
    return {v.code for v in report.violations}


def test_count_code_lines_ignores_comments_and_blanks():
    assert count_code_lines("# comment\n\nx = 1\n  # indented\n") == 1


def test_count_logic_lines_ignores_imports():
    source = (
        "import os\n"
        "from distutils.core import setup\n"
        "from typing import (\n"
        "    List,\n"
        ")\n"
        "\n"
        "VALUE = 1\n"
    )
    assert count_logic_lines(source) == 1


def test_removing_deprecated_imports_is_not_truncation():
    source = (
        "import imp\n"
        "import pipes\n"
        "import distutils\n"
        "from distutils.core import setup\n"
        "VALUE = 1\n"
        "def main():\n"
        "    return VALUE\n"
    )
    output = "VALUE = 1\ndef main():\n    return VALUE\n"
    report = validate_output(source, output)
    assert report.ok
    assert report.contract.logic_lines == 3
    assert report.output_logic_lines == 3


def test_truncated_logic_is_rejected_even_when_imports_survive():
    source = "\n".join(f"def f{i}():\n    return {i}\n" for i in range(20))
    output = "import os\n" + "\n".join(
        f"def f{i}():\n    return {i}\n" for i in range(3)
    )
    report = validate_output(source, output)
    assert "truncated-output" in _codes(report)
    assert report.output_logic_lines == 6


def test_complete_migration_passes():
    report = validate_output(SOURCE, COMPLETE)
    assert report.ok
    assert report.contract.symbols == {
        "API_TOKEN",
        "LegacyCart",
        "load_config",
        "fetch_catalog",
    }
    assert report.output_symbols == report.contract.symbols


def test_deleted_function_is_rejected():
    truncated = COMPLETE.replace(
        "\ndef fetch_catalog(endpoint: str) -> str:\n    return endpoint\n", ""
    )
    report = validate_output(SOURCE, truncated)
    assert not report.ok
    assert "missing-symbols" in _codes(report)
    assert any("fetch_catalog" in v.message for v in report.violations)
    assert "COMPLETE file" in report.to_error_text()


def test_truncated_output_is_rejected():
    source = "\n".join(f"def f{i}():\n    return {i}\n" for i in range(20))
    output = "\n".join(f"def f{i}():\n    return {i}\n" for i in range(3))
    report = validate_output(source, output)
    assert "truncated-output" in _codes(report)
    assert "missing-symbols" in _codes(report)


def test_unauthorized_third_party_import_is_rejected():
    output = COMPLETE.replace("import os\n", "import os\nimport aiohttp\n")
    report = validate_output(SOURCE, output)
    assert not report.ok
    assert "unauthorized-imports" in _codes(report)
    assert report.added_imports == frozenset({"aiohttp"})


def test_existing_third_party_import_is_allowed():
    source = COMPLETE.replace("import os\n", "import os\nimport requests\n")
    output = source.replace("return endpoint", "return requests.get(endpoint)")
    report = validate_output(source, output)
    assert report.ok


def test_allowed_extra_imports_override_guard():
    output = COMPLETE.replace("import os\n", "import os\nimport aiohttp\n")
    report = validate_output(SOURCE, output, allowed_extra_imports=["aiohttp"])
    assert report.ok


def test_docstring_removal_is_rejected():
    output = COMPLETE.replace('"""Legacy module."""\n\n', "", 1)
    report = validate_output(SOURCE, output)
    assert "missing-docstring" in _codes(report)


def test_invalid_output_is_rejected():
    report = validate_output(SOURCE, "def broken(:\n    pass\n")
    assert "invalid-python" in _codes(report)
    assert "missing-symbols" in _codes(report)


def test_python2_source_uses_regex_symbol_fallback():
    contract = build_contract(PY2_SOURCE)
    assert contract.parseable is False
    assert contract.symbols == {"TOKEN", "legacy_cart", "load_config"}

    report = validate_output(PY2_SOURCE, PY2_COMPLETE)
    assert report.ok


def test_python2_output_missing_symbol_is_rejected():
    output = PY2_COMPLETE.replace(
        "\ndef load_config(path: str) -> str:\n    return path\n", ""
    )
    report = validate_output(PY2_SOURCE, output)
    assert "missing-symbols" in _codes(report)
    assert any("load_config" in v.message for v in report.violations)


def test_non_python_language_is_not_enforced():
    report = validate_output("function f() {}", "", language="javascript")
    assert report.ok
    assert report.contract.enforced is False


def test_contract_can_be_disabled():
    report = validate_output(SOURCE, "", enabled=False)
    assert report.ok
    assert report.to_dict()["ok"] is True


class TestRefactorEnforced:
    async def test_repairs_deleted_symbol(self, monkeypatch):
        agent = LLMAgent()
        truncated = COMPLETE.replace(
            "\ndef fetch_catalog(endpoint: str) -> str:\n    return endpoint\n", ""
        )
        monkeypatch.setattr(agent, "refactor", AsyncMock(return_value=truncated))
        heal = AsyncMock(return_value=COMPLETE)
        monkeypatch.setattr(agent, "self_heal", heal)

        code, report, repairs = await agent.refactor_enforced(
            SOURCE, "modernize", [], max_repairs=2
        )

        assert code == COMPLETE
        assert report.ok
        assert repairs == 1
        assert "fetch_catalog" in heal.await_args.args[1]

    async def test_exhausted_budget_returns_violating_report(self, monkeypatch):
        agent = LLMAgent()
        truncated = COMPLETE.replace(
            "\ndef fetch_catalog(endpoint: str) -> str:\n    return endpoint\n", ""
        )
        monkeypatch.setattr(agent, "refactor", AsyncMock(return_value=truncated))
        monkeypatch.setattr(agent, "self_heal", AsyncMock(return_value=truncated))

        code, report, repairs = await agent.refactor_enforced(
            SOURCE, "modernize", [], max_repairs=2
        )

        assert code == truncated
        assert repairs == 2
        assert not report.ok
        assert "missing-symbols" in _codes(report)


def test_contract_error_exposes_report():
    report = validate_output(SOURCE, "")
    error = CodeContractError(report)
    assert error.report is report
    assert "contract" in str(error)


def test_validate_output_uses_settings_defaults(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "contract_min_line_ratio", 0.99)
    report = LLMAgent.validate_output(SOURCE, COMPLETE)
    assert report.ok


def test_newly_undefined_names_are_rejected():
    pytest.importorskip("pyflakes")
    source = """def render(items):
    results = []
    for item in items:
        results.append(item)
    return results
"""
    output = """def render(items):
    results = []
    for item in items:
        results.append(element)
    return results
"""
    report = validate_output(source, output)
    assert not report.ok
    assert "undefined-names" in _codes(report)
    assert "element" in report.added_undefined_names
