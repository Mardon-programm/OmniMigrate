from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

import libcst as cst
import libcst.helpers as cst_helpers
import libcst.metadata as cst_meta


@dataclass
class ASTFinding:
    line: int
    severity: str  # critical | warning | info
    category: str
    message: str
    suggestion: str | None = None

    def to_dict(self) -> dict:
        return {
            "line": self.line,
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "suggestion": self.suggestion,
        }


# Mapping of deprecated standard-library imports to modern equivalents.
DEPRECATED_IMPORTS: dict[str, str] = {
    "distutils": "setuptools / packaging (distutils removed in Python 3.12)",
    "imp": "importlib (removed in Python 3.12)",
    "cStringIO": "io.StringIO",
    "StringIO": "io.StringIO",
    "commands": "subprocess",
    "cgi": "cgi is removed in Python 3.13; use direct HTML processing",
    "collections": "replace collections.Iterable/Sequence/etc. imports with collections.abc",
    "pipes": "subprocess",
    "sre": "re",
    "fpectl": "removed module",
    "parser": "ast or libcst",
    "symbol": "ast or libcst",
    "gestalt": "removed module",
    "htmllib": "html.parser",
    "pickle": "review security implications when unpickling untrusted data",
    "Tkinter": "tkinter",
    "Queue": "queue",
    "urllib2": "urllib.request",
    "urlparse": "urllib.parse",
    "ConfigParser": "configparser",
    "thread": "_thread or threading",
    "dummy_thread": "_thread",
    "dbhash": "sqlite3 or another DB-API driver",
    "new": "removed module",
}

# Imports removed from collections.abc that used to be importable from collections.
LEGACY_COLLECTIONS_NAMES = (
    "Iterable",
    "Iterator",
    "Mapping",
    "MutableMapping",
    "MutableSequence",
    "MutableSet",
    "Sequence",
    "Set",
    "Callable",
    "Hashable",
    "Container",
    "Sized",
    "ItemsView",
    "KeysView",
    "ValuesView",
    "Generator",
)

LEGACY_TYPING_NAMES = {
    "List": "list",
    "Dict": "dict",
    "Set": "set",
    "Tuple": "tuple",
    "Optional": "X | None",
    "Union": "X | Y",
    "Type": "type",
    "Iterable": "collections.abc.Iterable",
    "Sequence": "collections.abc.Sequence",
    "Mapping": "collections.abc.Mapping",
    "Callable": "collections.abc.Callable",
    "Generator": "collections.abc.Generator",
    "Deque": "collections.deque",
    "FrozenSet": "frozenset",
    "DefaultDict": "collections.defaultdict",
    "Counter": "collections.Counter",
}

# Attribute calls removed / changed in modern Python.
REMOVED_METHODS = {
    ".iteritems()": "use items()",
    ".iterkeys()": "use keys()",
    ".itervalues()": "use values()",
    ".has_key(": "use `in` operator",
    ".next(": "use next(iterator)",
    ".viewitems()": "use items()",
    ".viewkeys()": "use keys()",
    ".viewvalues()": "use values()",
}


class _DeprecationVisitor(cst.CSTVisitor):
    """LibCST visitor that collects modernization findings."""

    METADATA_DEPENDENCIES = (cst_meta.PositionProvider,)

    def __init__(self) -> None:
        self.findings: list[ASTFinding] = []

    def _add(
        self,
        node: cst.CSTNode,
        severity: str,
        category: str,
        message: str,
        suggestion: str | None = None,
    ) -> None:
        position = self.get_metadata(cst_meta.PositionProvider, node)
        line = position.start.line if position else 0
        self.findings.append(
            ASTFinding(line=line, severity=severity, category=category, message=message, suggestion=suggestion)
        )

    # --- Imports -------------------------------------------------------
    def visit_Import(self, node: cst.Import) -> None:
        for alias in node.names:
            full = cst_helpers.get_full_name_for_node(alias.name) or ""
            top = full.split(".")[0]
            if top in DEPRECATED_IMPORTS:
                self._add(
                    node,
                    "critical" if top in ("distutils", "imp") else "warning",
                    "deprecated-import",
                    f"Deprecated module '{top}' is imported.",
                    DEPRECATED_IMPORTS[top],
                )

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if node.module is None:
            return
        module_name = cst_helpers.get_full_name_for_node(node.module) or ""
        if module_name == "collections":
            for alias in node.names:
                imported = cst_helpers.get_full_name_for_node(alias.name)
                if imported in LEGACY_COLLECTIONS_NAMES:
                    self._add(
                        node,
                        "warning",
                        "deprecated-import",
                        f"'{imported}' is no longer importable from 'collections'.",
                        f"Import from 'collections.abc' instead: from collections.abc import {imported}",
                    )
        elif module_name == "typing":
            for alias in node.names:
                imported = cst_helpers.get_full_name_for_node(alias.name)
                if imported in LEGACY_TYPING_NAMES:
                    self._add(
                        node,
                        "warning",
                        "modern-typing",
                        f"Legacy typing construct 'typing.{imported}' detected.",
                        f"Prefer '{LEGACY_TYPING_NAMES[imported]}' (PEP 604 / collections.abc).",
                    )
        elif module_name in DEPRECATED_IMPORTS:
            self._add(
                node,
                "warning",
                "deprecated-import",
                f"Deprecated module '{module_name}' is imported.",
                DEPRECATED_IMPORTS[module_name],
            )

    # --- Names ---------------------------------------------------------
    def visit_Name(self, node: cst.Name) -> None:
        name = node.value
        if name in ("xrange", "long", "unicode", "basestring", "raw_input"):
            self._add(
                node,
                "critical",
                "python2-syntax",
                f"Python 2 built-in '{name}' is not available in Python 3.",
                "Use range(), int, str, str/bytes, and input() respectively.",
            )
        elif name in ("eval", "exec"):
            self._add(
                node,
                "warning",
                "security",
                f"Use of '{name}'() can execute arbitrary code.",
                "Avoid dynamic code execution; validate input or use ast.literal_eval.",
            )

    # --- Attribute / method calls -------------------------------------
    def visit_Call(self, node: cst.Call) -> None:
        func = node.func
        # datetime.utcnow / utcfromtimestamp
        func_name = cst_helpers.get_full_name_for_node(func)
        if func_name and func_name in ("datetime.utcnow", "datetime.datetime.utcnow"):
            self._add(
                node,
                "warning",
                "deprecated-api",
                "datetime.utcnow() is deprecated in Python 3.12+ and timezone-naive.",
                "Use datetime.now(timezone.utc) instead.",
            )
        if func_name and func_name in ("datetime.utcfromtimestamp",):
            self._add(
                node,
                "warning",
                "deprecated-api",
                "datetime.utcfromtimestamp() is deprecated.",
                "Use datetime.fromtimestamp(ts, tz=timezone.utc) instead.",
            )
        if func_name and func_name in ("asyncio.gather",):
            # Not deprecated, but possible missing return_exceptions — informational only.
            return
        if isinstance(func, cst.Attribute) and func_name:
            suffix = "." + func.attr.value
            if suffix == ".iteritems":
                self._add(node, "critical", "python2-syntax", "iteritems() does not exist in Python 3.", "Use .items()")
            elif suffix == ".iterkeys":
                self._add(node, "critical", "python2-syntax", "iterkeys() does not exist in Python 3.", "Use .keys()")
            elif suffix == ".itervalues":
                self._add(node, "critical", "python2-syntax", "itervalues() does not exist in Python 3.", "Use .values()")
            elif suffix == ".has_key":
                self._add(node, "critical", "python2-syntax", "dict.has_key() was removed.", "Use `key in mapping`.")
            elif suffix in (".system", ".popen", ".Popen"):
                self._add(
                    node,
                    "warning",
                    "security",
                    f"Subprocess execution via '{func_name}' detected.",
                    "Prefer subprocess.run() with shell=False and validated arguments.",
                )

    def visit_Subscript(self, node: cst.Subscript) -> None:
        value = node.value
        if isinstance(value, cst.Name) and value.value in LEGACY_TYPING_NAMES:
            # e.g. List[int] written without importing from typing — informational.
            self._add(
                node,
                "info",
                "modern-typing",
                f"Legacy typing usage '{value.value}[...]' detected.",
                f"Use '{LEGACY_TYPING_NAMES[value.value]}' where applicable.",
            )

    # --- Comparisons (== None) ----------------------------------------
    def visit_Comparison(self, node: cst.Comparison) -> None:
        for target in node.comparisons:
            op = target.operator
            if isinstance(op, (cst.Equal, cst.NotEqual)) and isinstance(
                target.comparator, cst.Name
            ):
                if target.comparator.value == "None":
                    self._add(
                        node,
                        "warning",
                        "code-style",
                        "Comparison to None should use identity operators.",
                        f"Use '{op.__class__.__name__.replace('Equal', '')} is None' instead of '{op.__class__.__name__.replace('Not', '')}== None'.",
                    )

    # --- Assignments of secrets ----------------------------------------
    def visit_Assign(self, node: cst.Assign) -> None:
        value = node.value
        if isinstance(value, (cst.SimpleString, cst.ConcatenatedString)):
            for target in node.targets:
                expr = target.target
                names = (
                    cst_helpers.get_full_name_for_node(expr)
                    if not isinstance(expr, (cst.Tuple, cst.List))
                    else None
                )
                if names and re.search(
                    r"(password|passwd|secret|api_?key|token|private_key|credential)",
                    names,
                    re.IGNORECASE,
                ):
                    self._add(
                        node,
                        "critical",
                        "security",
                        f"Hardcoded credential-like value assigned to '{names}'.",
                        "Move secrets to environment variables and reference them via os.environ.",
                    )

    # --- Potential N+1 query patterns ---------------------------------
    def visit_For(self, node: cst.For) -> None:
        for body_node in node.body.body:
            if isinstance(body_node, (cst.SimpleStatementLine, cst.FunctionDef)):
                continue
        # Lightweight heuristic: SQLAlchemy-style .all()/.first() calls inside a loop.
        target = node.target
        iterable = node.iter
        if isinstance(iterable, cst.Call):
            func_name = cst_helpers.get_full_name_for_node(iterable.func) or ""
            if func_name.endswith((".all", ".first", ".one", ".scalar")) or func_name.startswith(
                "Query("
            ):
                self._add(
                    node,
                    "info",
                    "n-plus-one",
                    "Query executed directly inside a for-loop — potential N+1 access pattern.",
                    "Use selectinload()/joinedload() eager loading or a single bulk query.",
                )


@dataclass
class ParseResult:
    success: bool
    findings: list[dict] = field(default_factory=list)
    parse_error: str | None = None
    python_version_suggestion: str | None = None


def analyze_python_source(source: str) -> ParseResult:
    """Parse a Python source string with LibCST and return modernization findings."""
    try:
        module = cst.parse_module(source)
    except cst.ParserSyntaxError as exc:
        message = str(exc)
        suggestion = None
        if "invalid syntax" in message and any(
            kw in message for kw in ("print", "except", "exec")
        ):
            suggestion = (
                "Source appears to target Python 2 syntax; convert print statements, "
                "except clauses and exec usage to Python 3 first."
            )
        return ParseResult(success=False, parse_error=message, python_version_suggestion=suggestion)
    except Exception as exc:  # defensive: LibCST may raise on exotic input
        return ParseResult(success=False, parse_error=str(exc))

    wrapper = cst.MetadataWrapper(module)
    visitor = _DeprecationVisitor()
    wrapper.visit(visitor)
    findings = [f.to_dict() for f in visitor.findings]
    return ParseResult(success=True, findings=findings)


SUPPORTED_LANGUAGES: dict[str, str] = {
    ".py": "python",
    ".pyw": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".php": "php",
    ".rb": "ruby",
    ".cs": "csharp",
    ".sql": "sql",
    ".html": "html",
    ".css": "css",
}


def detect_language(filename: str) -> str:
    """Detect the programming language of a file from its extension."""
    import os

    _, ext = os.path.splitext(filename)
    return SUPPORTED_LANGUAGES.get(ext.lower(), "unknown")


def analyze_source(filename: str, source: str) -> ParseResult:
    """Dispatch source analysis based on detected language."""
    lang = detect_language(filename)
    if lang == "python":
        return analyze_python_source(source)
    # For non-Python targets, perform basic structural checks.
    return _analyze_generic(source, lang)


def _analyze_generic(source: str, lang: str) -> ParseResult:
    findings: list[dict] = []
    if "\ttodo" in source.lower() or "todo:" in source.lower():
        findings.append(
            {
                "line": 0,
                "severity": "info",
                "category": "todo",
                "message": "TODO marker found in source.",
                "suggestion": "Resolve or remove TODO markers.",
            }
        )
    if re.search(r"(password|secret|api_?key|token)\s*=\s*['\"][^'\"]+['\"]", source, re.IGNORECASE):
        findings.append(
            {
                "line": 0,
                "severity": "critical",
                "category": "security",
                "message": "Potential hardcoded credential detected.",
                "suggestion": "Move secrets to environment variables.",
            }
        )
    return ParseResult(success=True, findings=findings)


def findings_to_text(findings: Iterable[dict]) -> str:
    """Render findings as a compact text block for the LLM prompt."""
    lines = []
    for f in findings:
        loc = f"L{f.get('line') or '?'}"
        lines.append(f"- [{loc} / {f.get('severity', 'info')}] {f.get('category')}: {f.get('message')}")
        if f.get("suggestion"):
            lines.append(f"    -> {f['suggestion']}")
    return "\n".join(lines) if lines else "No findings detected."
