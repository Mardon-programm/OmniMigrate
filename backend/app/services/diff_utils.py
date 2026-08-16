from __future__ import annotations

import difflib
from dataclasses import dataclass


@dataclass
class DiffStats:
    additions: int = 0
    deletions: int = 0
    files_changed: int = 1

    def to_dict(self) -> dict:
        return {
            "additions": self.additions,
            "deletions": self.deletions,
            "files_changed": self.files_changed,
            "net_lines": self.additions - self.deletions,
        }


def generate_diff(old_code: str, new_code: str, filename: str = "source.py") -> str:
    """Produce a unified diff between the legacy and refactored code."""
    old_lines = old_code.splitlines(keepends=True)
    new_lines = new_code.splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"legacy/{filename}",
            tofile=f"modern/{filename}",
            lineterm="\n",
        )
    )


def diff_stats(diff: str) -> DiffStats:
    stats = DiffStats()
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            stats.additions += 1
        elif line.startswith("-") and not line.startswith("---"):
            stats.deletions += 1
    return stats
