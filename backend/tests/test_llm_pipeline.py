from app.core.prompts import (
    DEFAULT_CONTEXT_RULE,
    build_refactor_prompt,
    build_self_heal_prompt,
)
from app.services.ast_parser import findings_to_text
from app.services.llm_agent import LLMAgent


def test_refactor_prompt_contains_code_and_rule():
    prompt = build_refactor_prompt("print('hi')", "Migrate to Python 3.12", [])
    assert "print('hi')" in prompt
    assert "Migrate to Python 3.12" in prompt
    assert "No findings reported." in prompt


def test_refactor_prompt_renders_findings():
    findings = [
        {
            "line": 3,
            "severity": "warning",
            "category": "deprecated-api",
            "message": "utcnow",
            "suggestion": "use now",
        }
    ]
    prompt = build_refactor_prompt("x", DEFAULT_CONTEXT_RULE, findings)
    assert "deprecated-api" in prompt
    assert "utcnow" in prompt


def test_self_heal_prompt_includes_error():
    prompt = build_self_heal_prompt("rule", "broken code", "SyntaxError: boom")
    assert "SyntaxError: boom" in prompt
    assert "broken code" in prompt


def test_extract_code_strips_fences():
    raw = "```python\ndef f():\n    return 1\n```"
    assert LLMAgent._extract_code(raw) == "def f():\n    return 1\n"


def test_extract_code_passes_plain_code():
    code = "def f():\n    return 1\n"
    assert LLMAgent._extract_code(code) == "def f():\n    return 1"


def test_extract_code_removes_filler_intro():
    raw = "Here's the refactored code:\n\ndef f():\n    return 1\n"
    out = LLMAgent._extract_code(raw)
    assert out.startswith("def f():")


def test_findings_to_text():
    findings = [
        {
            "line": 1,
            "severity": "critical",
            "category": "security",
            "message": "secret",
            "suggestion": "use env",
        }
    ]
    text = findings_to_text(findings)
    assert "security" in text
    assert "use env" in text


def test_findings_to_text_empty():
    assert findings_to_text([]) == "No findings detected."
