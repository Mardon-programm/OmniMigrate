from __future__ import annotations

import dataclasses
import logging
import re

import libcst as cst
import libcst.helpers as cst_helpers

logger = logging.getLogger(__name__)

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
        # Remove imports of modules that no longer exist in modern Python.
        remaining = []
        removed = False
        for alias in updated_node.names:
            name = cst_helpers.get_full_name_for_node(alias.name) or ""
            if name.split(".")[0] in REMOVED_MODULES:
                removed = True
            else:
                remaining.append(alias)
        if removed:
            self.applied_rules.append("removed import of module removed from stdlib")
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
        return RuleEngineResult(code=source, applied_rules=[])

    transformer = _ModernizationTransformer()
    new_module = module.visit(transformer)
    new_source = new_module.code
    new_source = _ensure_timezone_import(new_source, transformer.needs_timezone_import)
    return RuleEngineResult(code=new_source, applied_rules=transformer.applied_rules)
