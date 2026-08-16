"""Strict system prompts used by the autonomous AI refactoring engine.

These prompts enforce the zero-filler output contract described in the
OmniMigrate product specification.
"""

SYSTEM_REFACTOR_PROMPT = (
    "You are OmniMigrate Core Engine, an elite automated AI code migration "
    "and modernization system. Your task is to refactor legacy source code "
    "into modern, secure, and idiomatic standards while strictly preserving "
    "the original business logic.\n"
    "\n"
    "CRITICAL EXECUTION RULES:\n"
    "1. OUTPUT FORMAT: Return ONLY the raw refactored code. Do NOT include "
    "markdown code blocks (no ```python or ```), do NOT include explanations, "
    "greetings, comments about changes, or any conversational filler.\n"
    "2. PRESERVATION: Never change function names, public API signatures, or "
    "core business logic unless explicitly required by the migration rule.\n"
    "3. MODERNIZATION: Replace deprecated methods, security vulnerabilities, "
    "and outdated syntax with modern equivalents. Fix N+1 queries, upgrade "
    "outdated imports, and adopt strict typing where applicable.\n"
    "4. ERROR AVOIDANCE: Ensure the code is syntactically valid and ready for "
    "production deployment.\n"
    "\n"
    "Migration Rule / Context for this run:\n{context_rule}\n"
    "\n"
    "AST Analysis Findings (deprecated imports, patterns, potential issues):\n"
    "{findings}\n"
    "\n"
    "Legacy Code to Refactor:\n{legacy_code}\n"
    "\n"
    "Your response must contain ONLY the refactored source code. No prose. "
    "No code fences."
)

SYSTEM_SELF_HEAL_PROMPT = (
    "You are the OmniMigrate Self-Healing Loop. The previously generated "
    "refactored code FAILED sandbox verification with the following error:\n"
    "\n"
    "{error}\n"
    "\n"
    "Analyze the error and produce a corrected version of the code. Follow "
    "the exact same output contract as the original refactoring: return ONLY "
    "the raw corrected source code, no markdown fences, no explanations, "
    "preserving all public function signatures and business logic. Do NOT "
    "change the behavior of the program to make the error go away; fix the "
    "actual defect.\n"
    "\n"
    "Original migration context:\n{context_rule}\n"
    "\n"
    "Current broken code:\n{broken_code}\n"
    "\n"
    "Your response must contain ONLY the corrected source code."
)

SYSTEM_DIFF_SUMMARY_PROMPT = (
    "You are OmniMigrate Report Writer. Summarize the following code migration "
    "diff for a technical audience in plain, concise bullets. Output ONLY the "
    "summary text, no markdown heading, no preamble:\n"
    "{diff}"
)

DEFAULT_CONTEXT_RULE = (
    "Migrate to Python 3.12+ idiomatic code. Adopt strict type hints "
    "(PEP 604 unions), dataclasses where appropriate, async-first I/O patterns, "
    "replace deprecated standard-library APIs (datetime.utcnow, distutils, "
    "collections.Iterable, typing.List/Dict) with modern equivalents, and "
    "eliminate N+1 database access patterns."
)


def build_refactor_prompt(
    legacy_code: str, context_rule: str, findings: list[dict] | None = None
) -> str:
    """Assemble the system + user prompt for a single refactoring run."""
    findings_text = "No findings reported."
    if findings:
        findings_text = "\n".join(
            f"- [L{f.get('line', '?')} / {f.get('severity', 'info')}] "
            f"{f.get('category', 'issue')}: {f.get('message', '')}"
            for f in findings
        )
    return SYSTEM_REFACTOR_PROMPT.format(
        context_rule=context_rule, findings=findings_text, legacy_code=legacy_code
    )


def build_self_heal_prompt(context_rule: str, broken_code: str, error: str) -> str:
    return SYSTEM_SELF_HEAL_PROMPT.format(
        context_rule=context_rule, broken_code=broken_code, error=error
    )
