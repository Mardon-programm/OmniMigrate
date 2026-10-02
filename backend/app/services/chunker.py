from __future__ import annotations

import ast
import hashlib
import libcst as cst
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.core.config import settings


@dataclass
class CodeChunk:
    """A chunk of code with metadata for LLM processing."""
    id: str
    content: str
    file_path: str
    start_line: int
    end_line: int
    imports: list[str] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)  # functions, classes defined
    dependencies: list[str] = field(default_factory=list)  # internal module deps
    token_estimate: int = 0
    language: str = "python"


@dataclass
class DependencyGraph:
    """Module-level dependency graph for a repository."""
    nodes: dict[str, set[str]] = field(default_factory=dict)  # file -> set of imported modules
    file_to_chunk_ids: dict[str, list[str]] = field(default_factory=dict)
    entry_points: list[str] = field(default_factory=list)  # main, __main__, handlers, etc.


class PythonASTVisitor(ast.NodeVisitor):
    """AST visitor to extract imports, exports, and dependencies from Python code."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.imports: list[str] = []
        self.exports: list[str] = []
        self.function_calls: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            self.imports.append(f"{module}.{alias.name}" if module else alias.name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.exports.append(node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.exports.append(node.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.exports.append(node.name)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            self.function_calls.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            self.function_calls.append(node.func.attr)
        self.generic_visit(node)


class PythonChunkExtractor(cst.CSTVisitor):
    """CST-based chunk extractor for Python files with token awareness."""

    def __init__(
        self,
        file_path: str,
        max_tokens: int = 3000,
        overlap_lines: int = 10,
    ):
        self.file_path = file_path
        self.max_tokens = max_tokens
        self.overlap_lines = overlap_lines
        self.chunks: list[CodeChunk] = []
        self._current_chunk_lines: list[str] = []
        self._current_start_line = 1
        self._imports: list[str] = []
        self._exports: list[str] = []
        self._dependencies: list[str] = []
        self._lines: list[str] = []

    def visit_Module(self, node: cst.Module) -> None:
        # Get all lines for token estimation
        self._lines = node.code_for_node.splitlines()
        self.generic_visit(node)

        # Flush remaining chunk
        if self._current_chunk_lines:
            self._flush_chunk()

    def visit_Import(self, node: cst.Import) -> None:
        for alias in node.names:
            self._imports.append(alias.name.value)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        module = node.module.value if node.module else ""
        for alias in node.names:
            self._imports.append(f"{module}.{alias.name.value}" if module else alias.name.value)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        self._exports.append(node.name.value)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: cst.AsyncFunctionDef) -> None:
        self._exports.append(node.name.value)
        self.generic_visit(node)

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        self._exports.append(node.name.value)
        self.generic_visit(node)

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars ~= 1 token)."""
        return len(text) // 4

    def _should_flush(self) -> bool:
        current_text = "\n".join(self._current_chunk_lines)
        return self._estimate_tokens(current_text) >= self.max_tokens

    def _flush_chunk(self) -> None:
        if not self._current_chunk_lines:
            return

        content = "\n".join(self._current_chunk_lines)
        chunk = CodeChunk(
            id=hashlib.md5(content.encode()).hexdigest()[:12],
            content=content,
            file_path=self.file_path,
            start_line=self._current_start_line,
            end_line=self._current_start_line + len(self._current_chunk_lines) - 1,
            imports=self._imports.copy(),
            exports=self._exports.copy(),
            dependencies=self._dependencies.copy(),
            token_estimate=self._estimate_tokens(content),
            language="python",
        )
        self.chunks.append(chunk)

        # Start new chunk with overlap
        overlap = self._current_chunk_lines[-self.overlap_lines:] if len(self._current_chunk_lines) > self.overlap_lines else []
        self._current_chunk_lines = overlap
        self._current_start_line = chunk.end_line - len(overlap) + 1

    def on_leave(self, original_node: cst.CSTNode, updated_node: cst.CSTNode) -> None:
        """Called when leaving a node - check if we should chunk."""
        if self._should_flush():
            self._flush_chunk()

    def on_visit(self, node: cst.CSTNode) -> bool:
        """Called when visiting a node."""
        if isinstance(node, cst.SimpleStatementLine):
            # Add line to current chunk
            self._current_chunk_lines.append(node.code_for_node)
        return True


class CodeChunker:
    """
    Intelligent code chunker for large files and repositories.
    
    Features:
    - AST-aware chunking (preserves function/class boundaries)
    - Dependency graph construction
    - Token-aware splitting with overlap
    - Import/export tracking for context assembly
    """

    def __init__(
        self,
        max_tokens_per_chunk: int = 3000,
        overlap_lines: int = 10,
        max_file_tokens: int = 10000,
    ):
        self.max_tokens_per_chunk = max_tokens_per_chunk
        self.overlap_lines = overlap_lines
        self.max_file_tokens = max_file_tokens

    def chunk_file(self, file_path: Path, content: str) -> list[CodeChunk]:
        """Chunk a single file."""
        if file_path.suffix == ".py":
            return self._chunk_python(file_path, content)
        else:
            return self._chunk_generic(file_path, content)

    def _chunk_python(self, file_path: Path, content: str) -> list[CodeChunk]:
        """Chunk Python file using CST for accuracy."""
        try:
            extractor = PythonChunkExtractor(
                str(file_path),
                max_tokens=self.max_tokens_per_chunk,
                overlap_lines=self.overlap_lines,
            )
            tree = cst.parse_module(content)
            tree.visit(extractor)
            return extractor.chunks
        except Exception:
            # Fallback to simple line-based chunking
            return self._chunk_generic(file_path, content)

    def _chunk_generic(self, file_path: Path, content: str) -> list[CodeChunk]:
        """Simple line-based chunking for non-Python files."""
        lines = content.splitlines()
        chunks = []
        chunk_lines = []
        start_line = 1

        for i, line in enumerate(lines, 1):
            chunk_lines.append(line)
            if len("\n".join(chunk_lines)) // 4 >= self.max_tokens_per_chunk:
                chunk_content = "\n".join(chunk_lines)
                chunks.append(CodeChunk(
                    id=hashlib.md5(chunk_content.encode()).hexdigest()[:12],
                    content=chunk_content,
                    file_path=str(file_path),
                    start_line=start_line,
                    end_line=i,
                    token_estimate=len(chunk_content) // 4,
                    language=file_path.suffix.lstrip("."),
                ))
                # Overlap
                overlap = chunk_lines[-self.overlap_lines:]
                chunk_lines = overlap
                start_line = i - len(overlap) + 1

        if chunk_lines:
            chunk_content = "\n".join(chunk_lines)
            chunks.append(CodeChunk(
                id=hashlib.md5(chunk_content.encode()).hexdigest()[:12],
                content=chunk_content,
                file_path=str(file_path),
                start_line=start_line,
                end_line=len(lines),
                token_estimate=len(chunk_content) // 4,
                language=file_path.suffix.lstrip("."),
            ))

        return chunks

    def chunk_repository(
        self,
        repo_path: Path,
        exclude_patterns: list[str] = None,
    ) -> tuple[list[CodeChunk], DependencyGraph]:
        """
        Chunk entire repository and build dependency graph.
        
        Returns:
            Tuple of (all_chunks, dependency_graph)
        """
        exclude_patterns = exclude_patterns or [
            "**/__pycache__/**", "**/.git/**", "**/venv/**", "**/node_modules/**",
            "**/*.pyc", "**/.pytest_cache/**", "**/dist/**", "**/build/**",
        ]

        all_chunks = []
        graph = DependencyGraph()
        py_files = list(repo_path.rglob("*.py"))

        for py_file in py_files:
            if any(py_file.match(p) for p in exclude_patterns):
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
            except Exception:
                continue

            # Extract imports for dependency graph
            imports, exports = self._extract_imports_exports(content)

            # Chunk the file
            chunks = self.chunk_file(py_file, content)
            for chunk in chunks:
                chunk.imports = imports
                chunk.exports = exports

            all_chunks.extend(chunks)

            # Update graph
            rel_path = py_file.relative_to(repo_path).as_posix()
            graph.file_to_chunk_ids[rel_path] = [c.id for c in chunks]
            graph.nodes[rel_path] = set(imports)

            # Detect entry points
            if self._is_entry_point(content, py_file.name):
                graph.entry_points.append(rel_path)

        # Resolve internal dependencies
        self._resolve_internal_deps(graph, repo_path)

        return all_chunks, graph

    def _extract_imports_exports(self, content: str) -> tuple[list[str], list[str]]:
        """Extract imports and exports from Python code using AST."""
        imports = []
        exports = []
        try:
            tree = ast.parse(content)
            visitor = PythonASTVisitor("")
            visitor.visit(tree)
            imports = visitor.imports
            exports = visitor.exports
        except Exception:
            pass
        return imports, exports

    def _is_entry_point(self, content: str, filename: str) -> bool:
        """Heuristically detect entry points."""
        if filename in {"main.py", "__main__.py", "app.py", "handler.py", "lambda_function.py"}:
            return True
        if "if __name__ == \"__main__\"" in content:
            return True
        return False

    def _resolve_internal_deps(self, graph: DependencyGraph, repo_path: Path) -> None:
        """Resolve internal module dependencies."""
        module_map = {}
        for file_path in graph.nodes:
            # Convert file path to module name
            module_name = file_path.replace("/", ".").replace(".py", "")
            if module_name.endswith(".__init__"):
                module_name = module_name[:-9]
            module_map[module_name] = file_path

        for file_path, imports in graph.nodes.items():
            deps = set()
            for imp in imports:
                # Check if it's an internal module
                parts = imp.split(".")
                for i in range(len(parts), 0, -1):
                    candidate = ".".join(parts[:i])
                    if candidate in module_map:
                        dep_file = module_map[candidate]
                        if dep_file != file_path:
                            deps.add(dep_file)
                        break
            graph.nodes[file_path] = deps


class ContextAssembler:
    """
    Assembles relevant context for LLM from chunks and dependency graph.
    
    Strategies:
    - Topological order (dependencies first)
    - Entry point prioritization
    - Token budget management
    - Import context injection
    """

    def __init__(
        self,
        max_context_tokens: int = 8000,
        reserve_tokens: int = 2000,  # For prompt + response
    ):
        self.max_context_tokens = max_context_tokens
        self.reserve_tokens = reserve_tokens
        self.available_tokens = max_context_tokens - reserve_tokens

    def assemble_context(
        self,
        chunks: list[CodeChunk],
        graph: DependencyGraph,
        target_file: Optional[str] = None,
    ) -> tuple[str, list[CodeChunk]]:
        """
        Assemble context for LLM.
        
        Returns:
            Tuple of (context_string, selected_chunks)
        """
        if target_file and target_file in graph.file_to_chunk_ids:
            # Prioritize target file and its dependencies
            selected = self._select_with_deps(chunks, graph, target_file)
        else:
            # General selection: topological order
            selected = self._select_topological(chunks, graph)

        # Trim to token budget
        selected = self._trim_to_budget(selected)

        # Build context string
        context = self._build_context_string(selected)
        return context, selected

    def _select_with_deps(
        self,
        chunks: list[CodeChunk],
        graph: DependencyGraph,
        target: str,
    ) -> list[CodeChunk]:
        """Select target file + its transitive dependencies."""
        target_ids = set(graph.file_to_chunk_ids.get(target, []))
        dep_files = graph.nodes.get(target, set())
        dep_ids = set()
        for dep in dep_files:
            dep_ids.update(graph.file_to_chunk_ids.get(dep, []))

        all_ids = target_ids | dep_ids
        chunk_map = {c.id: c for c in chunks}
        return [chunk_map[cid] for cid in all_ids if cid in chunk_map]

    def _select_topological(self, chunks: list[CodeChunk], graph: DependencyGraph) -> list[CodeChunk]:
        """Select chunks in topological order (dependencies first)."""
        # Build reverse dependency map
        file_deps = {f: list(deps) for f, deps in graph.nodes.items()}
        
        # Topological sort (Kahn's algorithm)
        indegree = {f: 0 for f in file_deps}
        for f, deps in file_deps.items():
            for d in deps:
                if d in indegree:
                    indegree[d] += 1

        queue = [f for f, d in indegree.items() if d == 0]
        order = []

        while queue:
            f = queue.pop(0)
            order.append(f)
            for dep in file_deps.get(f, []):
                indegree[dep] -= 1
                if indegree[dep] == 0:
                    queue.append(dep)

        # Add remaining (cycles)
        for f in file_deps:
            if f not in order:
                order.append(f)

        # Map back to chunks
        chunk_map = {c.id: c for c in chunks}
        selected = []
        for f in order:
            for cid in graph.file_to_chunk_ids.get(f, []):
                if cid in chunk_map:
                    selected.append(chunk_map[cid])

        # Add entry points first if they exist
        entry_ids = set()
        for ep in graph.entry_points:
            entry_ids.update(graph.file_to_chunk_ids.get(ep, []))

        ordered = []
        for cid in entry_ids:
            if cid in chunk_map and chunk_map[cid] in selected:
                ordered.append(chunk_map[cid])
                selected.remove(chunk_map[cid])
        ordered.extend(selected)

        return ordered

    def _trim_to_budget(self, chunks: list[CodeChunk]) -> list[CodeChunk]:
        """Trim chunks to fit token budget."""
        total = 0
        result = []
        for chunk in chunks:
            if total + chunk.token_estimate > self.available_tokens:
                break
            result.append(chunk)
            total += chunk.token_estimate
        return result

    def _build_context_string(self, chunks: list[CodeChunk]) -> str:
        """Build formatted context string for LLM."""
        parts = []
        for chunk in chunks:
            parts.append(f"# File: {chunk.file_path} (lines {chunk.start_line}-{chunk.end_line})")
            if chunk.imports:
                parts.append(f"# Imports: {', '.join(chunk.imports)}")
            if chunk.exports:
                parts.append(f"# Exports: {', '.join(chunk.exports)}")
            parts.append(chunk.content)
            parts.append("")  # blank line
        return "\n".join(parts).strip()


# Utility functions
import hashlib

def estimate_tokens(text: str) -> int:
    """Rough token estimation: ~4 chars = 1 token."""
    return len(text) // 4

def split_by_tokens(text: str, max_tokens: int, overlap: int = 100) -> list[str]:
    """Simple token-based splitting for arbitrary text."""
    words = text.split()
    if len(words) * 0.75 <= max_tokens:  # rough word->token
        return [text]

    chunks = []
    current = []
    current_tokens = 0

    for word in words:
        word_tokens = len(word) / 4
        if current_tokens + word_tokens > max_tokens and current:
            chunks.append(" ".join(current))
            # Overlap
            overlap_words = current[-overlap:] if len(current) > overlap else current
            current = overlap_words
            current_tokens = sum(len(w) / 4 for w in current)
        current.append(word)
        current_tokens += word_tokens

    if current:
        chunks.append(" ".join(current))

    return chunks