from __future__ import annotations

import dataclasses
import re
from typing import Optional

import libcst as cst
import libcst.helpers as cst_helpers
import structlog

logger = structlog.get_logger(__name__)

LEGACY_TYPING_NAMES = {
    "List": "list",
    "Dict": "dict",
    "Set": "set",
    "Tuple": "tuple",
}

REMOVED_MODULES = ("distutils", "imp", "cStringIO", "commands", "sre", "pipes")


class _ModernizationTransformer(cst.CSTTransformer):
    """Deterministic LibCST codemods used when no LLM provider is configured."""

    def __init__(self) -> None:
        self.applied_rules: list[str] = []
        self.needs_timezone_import = False

    def leave_Import(
        self, original_node: cst.Import, updated_node: cst.Import
    ) -> cst.Import | cst.RemovalSentinel:
        """Remove imports of modules that no longer exist in modern Python."""
        remaining = []
        removed = False
        for alias in updated_node.names:
            name = cst_helpers.get_full_name_for_node(alias.name) or ""
            if name.split(".")[0] in REMOVED_MODULES:
                removed = True
                self.applied_rules.append(f"removed import of {name}")
            else:
                remaining.append(alias)
        if removed:
            if remaining:
                return updated_node.with_changes(names=remaining)
            return cst.RemoveFromParent()
        return updated_node

    def leave_ImportFrom(
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> cst.ImportFrom | cst.RemovalSentinel:
        if updated_node.module is None:
            return updated_node
        module_name = cst_helpers.get_full_name_for_node(updated_node.module) or ""
        if module_name.split(".")[0] in REMOVED_MODULES:
            self.applied_rules.append(f"removed import from removed module '{module_name}'")
            return cst.RemoveFromParent()
        return updated_node

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.Name:
        if updated_node.value == "xrange":
            self.applied_rules.append("xrange -> range")
            return updated_node.with_changes(value="range")
        return updated_node

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        func = updated_node.func
        if (
            isinstance(func, cst.Attribute)
            and isinstance(func.value, cst.Name)
            and func.value.value == "datetime"
            and func.attr.value == "utcnow"
        ):
            self.applied_rules.append("datetime.utcnow() -> datetime.now(timezone.utc)")
            self.needs_timezone_import = True
            return updated_node.with_changes(
                func=func.with_changes(attr=cst.Name(value="now")),
                args=[
                    cst.Arg(
                        cst.Attribute(value=cst.Name(value="timezone"), attr=cst.Name(value="utc")),
                        keyword=cst.Name(value="tz"),
                    )
                ],
            )
        return updated_node

    def leave_Subscript(
        self, original_node: cst.Subscript, updated_node: cst.Subscript
    ) -> cst.Subscript:
        value = updated_node.value
        if isinstance(value, cst.Name) and value.value in LEGACY_TYPING_NAMES:
            replacement = LEGACY_TYPING_NAMES[value.value]
            self.applied_rules.append(f"typing.{value.value}[...] -> {replacement}[...]")
            return updated_node.with_changes(value=value.with_changes(value=replacement))
        return updated_node

    def leave_Comparison(
        self, original_node: cst.Comparison, updated_node: cst.Comparison
    ) -> cst.Comparison:
        new_comparisons: list[cst.ComparisonTarget] = []
        changed = False
        for target in updated_node.comparisons:
            comparator = target.comparator
            is_none = isinstance(comparator, cst.Name) and comparator.value == "None"
            operator = target.operator
            if isinstance(operator, cst.Equal) and is_none:
                new_comparisons.append(target.with_changes(operator=cst.Is()))
                changed = True
            elif isinstance(operator, cst.NotEqual) and is_none:
                new_comparisons.append(target.with_changes(operator=cst.IsNot()))
                changed = True
            else:
                new_comparisons.append(target)
        if changed:
            self.applied_rules.append("== None -> is None / != None -> is not None")
            return updated_node.with_changes(comparisons=new_comparisons)
        return updated_node


def _ensure_timezone_import(source: str, needs_import: bool) -> str:
    if not needs_import:
        return source
    # Skip if `timezone` is already imported from datetime.
    if re.search(
        r"from\s+datetime\s+import\s+[^\n]*\btimezone\b|^import\s+timezone\b",
        source,
        re.MULTILINE,
    ):
        return source
    return f"from datetime import timezone\n{source}"


# Conservative text-level replacements for files that use Python 2-only
# syntax which a modern parser (LibCST) cannot even parse (e.g. `print "x"`,
# `import urllib2`). These run only as a last-resort fallback so legacy files
# still get a best-effort modernization when no LLM is configured.
_PY2_FALLBACK_RULES: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"\bxrange\("), "range(", "xrange -> range"),
    (re.compile(r"\bprint\s+([^#\n]+)$", re.MULTILINE), r"print(\1)", "print statement -> print()"),
    (re.compile(r"\b\.utcnow\(\)"), ".now(timezone.utc)", "datetime.utcnow -> now(timezone.utc)"),
]


def _py2_regex_modernize(source: str) -> tuple[str, list[str]]:
    """Best-effort regex modernization for Python 2 syntax that won't parse."""
    new_source = source
    applied: list[str] = []
    for pattern, repl, label in _PY2_FALLBACK_RULES:
        if pattern.search(new_source):
            new_source, count = pattern.subn(repl, new_source)
            if count:
                applied.append(label)
    return new_source, applied


@dataclasses.dataclass
class RuleEngineResult:
    code: str
    applied_rules: list[str]


def apply_modernization_rules(source: str) -> RuleEngineResult:
    """Apply deterministic modernization codemods to Python source.

    Used as a no-key fallback provider; idempotent by design.
    """
    try:
        module = cst.parse_module(source)
    except cst.ParserSyntaxError:
        logger.warning("Local rule engine skipped: source could not be parsed")
        new_source, applied = _py2_regex_modernize(source)
        return RuleEngineResult(code=new_source, applied_rules=applied)

    transformer = _ModernizationTransformer()
    new_module = module.visit(transformer)
    new_source = new_module.code
    new_source = _ensure_timezone_import(new_source, transformer.needs_timezone_import)
    return RuleEngineResult(code=new_source, applied_rules=transformer.applied_rules)


# =============================================================================
# HYBRID TRANSFORM ENGINE - Clear separation of Deterministic vs LLM
# =============================================================================

@dataclasses.dataclass
class TransformStage:
    """Represents a single transformation stage."""
    name: str
    description: str
    applied_rules: list[str]
    code: str


@dataclasses.dataclass
class HybridTransformResult:
    """Result of hybrid transformation with clear stage separation."""
    stages: list[TransformStage]
    final_code: str
    deterministic_applied: list[str]
    llm_applied: list[str]

    def total_rules_applied(self) -> int:
        return len(self.deterministic_applied) + len(self.llm_applied)


class HybridTransformEngine:
    """
    Hybrid Transform Engine - Clear separation of deterministic and LLM-based transformations.
    
    Pipeline:
    1. Stage 1: Deterministic AST codemods (LibCST) - fast, deterministic, no API calls
    2. Stage 2: LLM-based transformations - semantic, context-aware
    3. Stage 3: Self-healing loop (sandbox verification + LLM fix)
    """
    
    def __init__(self, rule_engine=None, llm_agent=None, sandbox=None):
        self.rule_engine = rule_engine
        self.llm_agent = llm_agent
        self.sandbox = sandbox
    
    async def transform(
        self, 
        source_code: str, 
        context_rule: str,
        findings: list[dict],
        max_self_heal_attempts: int = 3
    ) -> HybridTransformResult:
        """
        Execute the full hybrid transformation pipeline.
        
        Returns HybridTransformResult with clear stage separation.
        """
        stages = []
        current_code = source_code
        
        # Stage 1: Deterministic AST transformations (no LLM needed)
        deterministic_result = apply_modernization_rules(current_code)
        stages.append(TransformStage(
            name="deterministic_ast",
            description="Applied deterministic AST codemods (imports, syntax, typing)",
            applied_rules=deterministic_result.applied_rules,
            code=deterministic_result.code
        ))
        current_code = deterministic_result.code
        
        # Stage 2: LLM-based semantic transformations (if available)
        llm_applied = []
        if self.llm_agent:
            try:
                # Build prompt with findings context
                prompt = build_refactor_prompt(current_code, context_rule, findings)
                llm_output = await self.llm_agent.refactor(current_code, context_rule, findings or [])
                llm_applied = ["LLM semantic refactoring applied"]
                
                stages.append(TransformStage(
                    name="llm_semantic",
                    description="LLM-based semantic refactoring with context awareness",
                    applied_rules=llm_applied,
                    code=llm_output
                ))
                current_code = llm_output
                llm_applied = ["LLM semantic refactoring applied"]
            except Exception as e:
                logger.warning(f"LLM transformation failed: {e}, falling back to deterministic only")
                llm_applied = []
        
        # Stage 3: Self-healing loop with sandbox verification
        self_heal_applied = []
        current_code_for_healing = current_code
        
        for attempt in range(max_self_heal_attempts):
            if self.sandbox:
                verification = self.sandbox.verify(current_code_for_healing)
                if verification.success:
                    self_heal_applied.append(f"Sandbox verification passed on attempt {attempt + 1}")
                    break
                
                # Self-healing attempt
                error_msg = "; ".join(verification.errors[:5])
                healed_code = await self._attempt_self_heal(
                    current_code_for_healing, 
                    error_msg, 
                    context_rule
                )
                
                if healed_code != current_code_for_healing:
                    self_heal_applied.append(f"Self-heal attempt {attempt + 1}: fixed {len(verification.errors)} errors")
                    current_code_for_healing = healed_code
                else:
                    self_heal_applied.append(f"Self-heal attempt {attempt + 1}: no fix found")
                    break
            else:
                self_heal_applied.append("Sandbox not available, skipping self-healing")
                break
        
        # Final stage
        stages.append(TransformStage(
            name="self_healing",
            description=f"Sandbox verification with self-healing ({len(self_heal_applied)} attempts)",
            applied_rules=self_heal_applied,
            code=current_code_for_healing
        ))
        
        # Collect all applied rules
        deterministic_rules = []
        llm_rules = []
        
        for stage in stages:
            if stage.name in ("deterministic_ast", "self_healing"):
                deterministic_rules.extend(stage.applied_rules)
            elif stage.name == "llm_semantic":
                llm_rules.extend(stage.applied_rules)
        
        return HybridTransformResult(
            stages=stages,
            final_code=current_code_for_healing,
            deterministic_applied=deterministic_rules,
            llm_applied=llm_rules
        )
    
    async def _attempt_self_heal(
        self, 
        broken_code: str, 
        error: str, 
        context_rule: str
    ) -> str:
        """Attempt to heal broken code using LLM."""
        if not self.llm_agent:
            return broken_code
        
        try:
            healed = await self.llm_agent.self_heal(broken_code, error, context_rule)
            return healed
        except Exception as e:
            logger.warning(f"Self-heal failed: {e}")
            return broken_code


# Backward compatibility
def apply_modernization_rules(source: str) -> RuleEngineResult:
    """Apply deterministic modernization codemods to Python source."""
    try:
        module = cst.parse_module(source)
    except cst.ParserSyntaxError:
        logger.warning("Local rule engine skipped: source could not be parsed")
        new_source, applied = _py2_regex_modernize(source)
        return RuleEngineResult(code=new_source, applied_rules=applied)

    transformer = _ModernizationTransformer()
    new_module = module.visit(transformer)
    new_source = new_module.code
    new_source = _ensure_timezone_import(new_source, transformer.needs_timezone_import)
    return RuleEngineResult(code=new_source, applied_rules=transformer.applied_rules)