"""Output-contract checks for LLM-based code migration.

The refactoring model is prone to *code shrinkage*: when a migration is hard,
the cheapest way to make the output "work" is to delete the code that does
not.  Syntax/import checks cannot see that, so these guards compare the
generated file with the original source and reject:

* missing top-level classes, functions and constants;
* output that is drastically shorter than the source (truncation);
* a removed module docstring;
* newly introduced non-stdlib imports that were not present before;
* newly introduced undefined names (a classic sign of a broken rewrite).

The checks are deliberately conservative.  They do not care about formatting,
comments, or which stdlib modules are used.
"""

from __future__ import annotations

import ast
import dataclasses
import re
import sys
from collections.abc import Iterable

PYTHON_LANGUAGES = frozenset({"python", "py", "python3"})
DEFAULT_MIN_LINE_RATIO = 0.75

_STDLIB_IMPORTS = frozenset(sys.stdlib_module_names) | {"__future__"}

_TOP_LEVEL_DEF_RE = re.compile(
    r"^(?:async\s+def|def|class)\s+([A-Za-z_]\w*)", re.MULTILINE
)
_TOP_LEVEL_ASSIGN_RE = re.compile(r"^([A-Za-z_]\w*)\s*(?::[^=\n]+)?=", re.MULTILINE)
_IMPORT_RE = re.compile(r"^\s*import\s+([A-Za-z_][\w.]*)", re.MULTILINE)
_FROM_IMPORT_RE = re.compile(r"^\s*from\s+([A-Za-z_][\w.]*)\s+import\b", re.MULTILINE)


class CodeContractError(RuntimeError):
    """Raised when generated code violates the migration output contract."""

    def __init__(self, report: ContractReport) -> None:
        self.report = report
        super().__init__(report.to_error_text())


@dataclasses.dataclass(frozen=True)
class CodeContract:
    """Fingerprint of the source file that the output must respect."""

    language: str
    enforced: bool
    parseable: bool
    symbols: frozenset[str]
    code_lines: int
    logic_lines: int
    import_roots: frozenset[str]
    has_module_docstring: bool


@dataclasses.dataclass(frozen=True)
class ContractViolation:
    code: str
    message: str


@dataclasses.dataclass
class ContractReport:
    contract: CodeContract
    violations: list[ContractViolation] = dataclasses.field(default_factory=list)
    output_symbols: frozenset[str] = frozenset()
    output_lines: int = 0
    output_logic_lines: int = 0
    added_imports: frozenset[str] = frozenset()
    added_undefined_names: frozenset[str] = frozenset()

    @property
    def ok(self) -> bool:
        return not self.violations

    def to_error_text(self) -> str:
        details = "\n".join(f"- {v.message}" for v in self.violations)
        return (
            "The generated code violates the migration output contract:\n"
            f"{details}\n"
            "Return the COMPLETE file. Restore every original top-level class, "
            "function and module-level constant; do not truncate the output; "
            "use only the standard library and imports that already existed in "
            "the source; keep every local variable and name that the original "
            "code defined."
        )

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "violations": [
                {"code": v.code, "message": v.message} for v in self.violations
            ],
            "source_symbols": sorted(self.contract.symbols),
            "output_symbols": sorted(self.output_symbols),
            "source_lines": self.contract.code_lines,
            "output_lines": self.output_lines,
            "source_logic_lines": self.contract.logic_lines,
            "output_logic_lines": self.output_logic_lines,
            "added_imports": sorted(self.added_imports),
            "added_undefined_names": sorted(self.added_undefined_names),
        }


def count_code_lines(source: str) -> int:
    """Count non-empty, non-comment lines (a cheap truncation signal)."""
    count = 0
    for line in source.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            count += 1
    return count


_IMPORT_LINE_RE = re.compile(r"^(?:import|from)\s+[A-Za-z_]")


def count_logic_lines(source: str) -> int:
    """Count executable lines, ignoring comments, blanks and import statements.

    Imports are excluded because migrating away from a removed module
    (``distutils``, ``imp``...) legitimately deletes whole import lines and
    must not be mistaken for the model truncating the implementation.
    """
    count = 0
    import_depth = 0
    for line in source.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if import_depth:
            import_depth += stripped.count("(") - stripped.count(")")
            import_depth = max(import_depth, 0)
            continue
        if _IMPORT_LINE_RE.match(stripped):
            opened = stripped.count("(") - stripped.count(")")
            import_depth = max(opened, 0)
            continue
        count += 1
    return count


def _symbols_from_ast(tree: ast.Module) -> frozenset[str]:
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return frozenset(names)


def _symbols_from_text(source: str) -> frozenset[str]:
    """Best-effort top-level symbol extraction for unparseable Python 2 code."""
    names = set(_TOP_LEVEL_DEF_RE.findall(source))
    names.update(_TOP_LEVEL_ASSIGN_RE.findall(source))
    return frozenset(names)


def _import_roots_from_ast(tree: ast.Module) -> frozenset[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return frozenset(roots)


def _import_roots_from_text(source: str) -> frozenset[str]:
    roots = {match.split(".")[0] for match in _IMPORT_RE.findall(source)}
    roots.update(match.split(".")[0] for match in _FROM_IMPORT_RE.findall(source))
    return frozenset(roots)


def _has_module_docstring_ast(tree: ast.Module) -> bool:
    return bool(ast.get_docstring(tree, clean=False))


# Names supplied by the Python runtime rather than by an assignment/import.
# pyflakes does not know all of them (notably ``__path__`` in packages).
_RUNTIME_DEFINED_NAMES = frozenset(
    {
        "__path__",
        "__file__",
        "__cached__",
        "__name__",
        "__doc__",
        "__package__",
        "__loader__",
        "__spec__",
        "__builtins__",
        "__debug__",
    }
)


def _undefined_names(source: str) -> frozenset[str]:
    """Collect names that pyflakes considers undefined in ``source``.

    pyflakes is optional at runtime: if it is not installed, the guard is
    simply skipped instead of failing the migration.
    """
    try:
        from pyflakes.api import check
        from pyflakes.messages import UndefinedName
        from pyflakes.reporter import Reporter
    except ImportError:  # pragma: no cover - optional dependency
        return frozenset()

    class _Collector(Reporter):
        def __init__(self) -> None:
            self.names: set[str] = set()

        def flake(self, message) -> None:  # noqa: ANN001 - pyflakes API
            if isinstance(message, UndefinedName):
                self.names.add(message.message_args[0])

        def syntaxError(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
            pass

        def unexpectedError(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
            pass

    collector = _Collector()
    check(source, filename="<omni-contract>", reporter=collector)
    return frozenset(collector.names) - _RUNTIME_DEFINED_NAMES


def _has_module_docstring_text(source: str) -> bool:
    for line in source.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        return stripped.startswith(('"""', "'''"))
    return False


def build_contract(source: str, language: str = "python") -> CodeContract:
    """Fingerprint the original source before it is sent to the model."""
    lang = language.lower()
    if lang not in PYTHON_LANGUAGES:
        return CodeContract(
            language=language,
            enforced=False,
            parseable=True,
            symbols=frozenset(),
            code_lines=count_code_lines(source),
            logic_lines=count_logic_lines(source),
            import_roots=frozenset(),
            has_module_docstring=False,
        )

    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return CodeContract(
            language=language,
            enforced=True,
            parseable=False,
            symbols=_symbols_from_text(source),
            code_lines=count_code_lines(source),
            logic_lines=count_logic_lines(source),
            import_roots=_import_roots_from_text(source),
            has_module_docstring=_has_module_docstring_text(source),
        )

    return CodeContract(
        language=language,
        enforced=True,
        parseable=True,
        symbols=_symbols_from_ast(tree),
        code_lines=count_code_lines(source),
        logic_lines=count_logic_lines(source),
        import_roots=_import_roots_from_ast(tree),
        has_module_docstring=_has_module_docstring_ast(tree),
    )


def validate_output(
    source: str,
    output: str,
    *,
    language: str = "python",
    min_line_ratio: float = DEFAULT_MIN_LINE_RATIO,
    allowed_extra_imports: Iterable[str] = (),
    enabled: bool = True,
) -> ContractReport:
    """Check a generated file against the contract derived from ``source``."""
    contract = build_contract(source, language)
    if not enabled or not contract.enforced:
        return ContractReport(contract=contract)

    violations: list[ContractViolation] = []

    try:
        output_tree: ast.Module | None = ast.parse(output)
    except (SyntaxError, ValueError) as exc:
        output_tree = None
        violations.append(
            ContractViolation(
                "invalid-python",
                f"Output is not valid Python: {exc}",
            )
        )

    if output_tree is not None:
        output_symbols = _symbols_from_ast(output_tree)
        output_roots = _import_roots_from_ast(output_tree)
        has_docstring = _has_module_docstring_ast(output_tree)
    else:
        output_symbols = _symbols_from_text(output)
        output_roots = _import_roots_from_text(output)
        has_docstring = _has_module_docstring_text(output)

    output_lines = count_code_lines(output)
    output_logic_lines = count_logic_lines(output)

    missing = sorted(contract.symbols - output_symbols)
    if missing:
        violations.append(
            ContractViolation(
                "missing-symbols",
                "Top-level definitions were deleted or renamed and must be "
                "restored: " + ", ".join(missing),
            )
        )

    if (
        contract.logic_lines
        and output_logic_lines < contract.logic_lines * min_line_ratio
    ):
        violations.append(
            ContractViolation(
                "truncated-output",
                f"Output has only {output_logic_lines} code lines while the source "
                f"has {contract.logic_lines}; it looks truncated (minimum ratio "
                f"{min_line_ratio:.2f}).",
            )
        )

    if contract.has_module_docstring and not has_docstring:
        violations.append(
            ContractViolation(
                "missing-docstring",
                "The module docstring from the source was removed.",
            )
        )

    allowed_roots = _STDLIB_IMPORTS | contract.import_roots
    allowed_roots = allowed_roots | {
        name.split(".")[0] for name in allowed_extra_imports
    }
    added_imports = frozenset(output_roots - allowed_roots)
    if added_imports:
        violations.append(
            ContractViolation(
                "unauthorized-imports",
                "New non-stdlib imports were added without being requested: "
                + ", ".join(sorted(added_imports)),
            )
        )

    added_undefined: frozenset[str] = frozenset()
    if contract.parseable and output_tree is not None:
        added_undefined = _undefined_names(output) - _undefined_names(source)
        if added_undefined:
            violations.append(
                ContractViolation(
                    "undefined-names",
                    "The output references names that were not defined in the "
                    "original code: " + ", ".join(sorted(added_undefined)),
                )
            )

    return ContractReport(
        contract=contract,
        violations=violations,
        output_symbols=output_symbols,
        output_lines=output_lines,
        output_logic_lines=output_logic_lines,
        added_imports=added_imports,
        added_undefined_names=added_undefined,
    )
