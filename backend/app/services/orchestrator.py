from __future__ import annotations

import asyncio
import dataclasses
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable

from app.core.config import settings
from app.core.prompts import DEFAULT_CONTEXT_RULE
from app.models import JobStatus
from app.services.git_integrations import GitHubIntegrationService
from app.services.git_sandbox import (
    FileChange,
    GitOperationError,
    GitSandboxService,
    TestRunResult,
)
from app.services.llm_agent import LLMAgent
from app.services.rule_engine import apply_modernization_rules

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class PipelineResult:
    """Outcome of a full autonomous migration run."""

    repo_url: str
    branch_name: str
    pull_request_url: str | None
    pull_request_number: int | None
    changed_files: list[FileChange]
    baseline_tests: TestRunResult | None
    post_refactor_tests: TestRunResult | None
    heal_attempts: int
    diff_summary: str
    logs: list[str]

    def to_dict(self) -> dict:
        return {
            "repo_url": self.repo_url,
            "branch_name": self.branch_name,
            "pull_request_url": self.pull_request_url,
            "pull_request_number": self.pull_request_number,
            "files_changed": len(self.changed_files),
            "changed_files": [f.rel_path for f in self.changed_files],
            "baseline_tests": (
                {
                    "success": self.baseline_tests.success,
                    "summary": self.baseline_tests.summary(),
                }
                if self.baseline_tests
                else None
            ),
            "post_refactor_tests": (
                {
                    "success": self.post_refactor_tests.success,
                    "summary": self.post_refactor_tests.summary(),
                }
                if self.post_refactor_tests
                else None
            ),
            "heal_attempts": self.heal_attempts,
            "diff_summary": self.diff_summary,
            "logs": self.logs,
        }


class AutonomousMigrationOrchestrator:
    """Full Git + test-driven self-healing migration pipeline.

    Steps:
      1. Clone the remote repo into a fresh sandbox.
      2. Run the baseline test suite to establish a green reference.
      3. Refactor every Python file (LLM provider or local rule engine).
      4. Re-run tests; self-heal files implicated by failures until green
         or the attempt budget is exhausted.
      5. Commit, push a feature branch, and open a pull request.
      6. Clean up the sandbox.
    """

    def __init__(
        self,
        llm: LLMAgent | None = None,
        progress: Callable[[int, str, str], Awaitable[None]] | None = None,
    ) -> None:
        self.llm = llm or LLMAgent()
        self.progress = progress
        self.max_heal_attempts = settings.max_self_heal_attempts

    async def _report(self, progress: int, stage: str, message: str) -> None:
        logger.info("[%d%%] %s", progress, message)
        if self.progress:
            try:
                await self.progress(progress, stage, message)
            except Exception:  # noqa: BLE001 - progress must never break the run.
                logger.warning("Progress callback failed", exc_info=True)

    # --- Providers ---------------------------------------------------------

    def _use_llm(self) -> bool:
        return bool(settings.openai_api_key)

    def _make_refactor_fn(self, context_rule: str):
        """Return an async `(code, context_rule) -> code` refactor function."""
        if self._use_llm():
            async def refactor(code: str, rule: str) -> str:
                try:
                    return await self.llm.refactor(code, rule, [])
                except Exception:  # noqa: BLE001 - fall back to local rules.
                    logger.warning("LLM refactor failed, falling back to local rules", exc_info=True)
                    return apply_modernization_rules(code).code
            return refactor
        return lambda code, rule: apply_modernization_rules(code).code

    def _make_heal_fn(self, context_rule: str):
        if self._use_llm():
            async def heal(code: str, error: str, rule: str) -> str:
                try:
                    return await self.llm.self_heal(code, error, rule)
                except Exception:  # noqa: BLE001
                    logger.warning("LLM heal failed, falling back to local rules", exc_info=True)
                    return apply_modernization_rules(code).code
            return heal
        return lambda code, error, rule: apply_modernization_rules(code).code

    # --- Pipeline ----------------------------------------------------------

    async def execute_full_pipeline(
        self,
        repo_url: str,
        github_token: str,
        repo_owner: str,
        repo_name: str,
        context_rule: str | None = None,
        base_branch: str = "main",
        title: str | None = None,
        body: str | None = None,
    ) -> PipelineResult:
        """Run the entire pipeline and return the result with the PR URL."""
        rule = context_rule or DEFAULT_CONTEXT_RULE
        logs: list[str] = []
        heal_attempts = 0
        changed_files: list[FileChange] = []
        baseline: TestRunResult | None = None
        post_tests: TestRunResult | None = None
        pr_url: str | None = None
        pr_number: int | None = None
        project_dir: str | None = None

        def log(msg: str) -> None:
            logs.append(msg)
            logger.info(msg)

        try:
            # 1. Clone.
            await self._report(10, "clone", f"Cloning {repo_url}")
            project_dir = await asyncio.to_thread(
                GitSandboxService.clone_repository, repo_url, base_branch
            )

            # 2. Baseline tests.
            await self._report(20, "baseline", "Running baseline test suite")
            baseline = await asyncio.to_thread(GitSandboxService.run_tests, project_dir)
            log(f"Baseline tests: {'PASS' if baseline.success else 'FAIL'}")

            # 3. Refactor the whole tree.
            await self._report(40, "refactor", "Refactoring Python sources")
            refactor_fn = self._make_refactor_fn(rule)

            async def _run_process_dir() -> list[FileChange]:
                # process_directory expects a sync callable; adapt the async provider.
                if self._use_llm():
                    async def sync_refactor(code: str, _rule: str) -> str:
                        return await refactor_fn(code, _rule)

                    return await self._process_dir_async(project_dir, sync_refactor, rule)
                return await asyncio.to_thread(
                    GitSandboxService.process_directory, project_dir, refactor_fn, rule
                )

            changed_files = await _run_process_dir()
            log(f"Refactored {len(changed_files)} file(s)")

            # 4. Post-refactor tests with self-healing.
            await self._report(60, "verify", "Re-running tests after refactor")
            post_tests = await asyncio.to_thread(GitSandboxService.run_tests, project_dir)
            heal_fn = self._make_heal_fn(rule)

            while not post_tests.success and heal_attempts < self.max_heal_attempts:
                heal_attempts += 1
                await self._report(
                    60 + heal_attempts * 10,
                    "heal",
                    f"Self-healing attempt {heal_attempts}/{self.max_heal_attempts}",
                )
                error_output = f"{post_tests.stdout}\n{post_tests.stderr}"
                if self._use_llm():
                    healed = await self._heal_dir_async(project_dir, error_output, heal_fn, rule)
                else:
                    healed = await asyncio.to_thread(
                        GitSandboxService.heal_code_with_error,
                        project_dir,
                        error_output,
                        heal_fn,
                        rule,
                    )
                changed_files.extend(healed)
                log(f"Heal attempt {heal_attempts}: fixed {len(healed)} file(s)")
                post_tests = await asyncio.to_thread(GitSandboxService.run_tests, project_dir)

            if not post_tests.success:
                raise GitOperationError(
                    "Tests still failing after self-healing. "
                    + post_tests.summary()
                )

            # 5. Commit, push, and open a PR.
            await self._report(95, "pr", "Pushing branch and creating pull request")
            branch = self._branch_name()
            title = title or self._default_title(repo_owner, repo_name)
            body = body or self._default_body(changed_files)
            commit_message = self._default_commit_message(changed_files)

            await asyncio.to_thread(
                GitHubIntegrationService.commit_and_push,
                project_dir,
                github_token,
                repo_owner,
                repo_name,
                branch,
                commit_message,
            )
            github = GitHubIntegrationService(github_token)
            pr = await github.create_pull_request(
                repo_owner, repo_name, title, head=branch, base=base_branch, body=body
            )
            pr_url = pr["html_url"]
            pr_number = pr["number"]
            log(f"Pull request created: {pr_url}")

            return PipelineResult(
                repo_url=repo_url,
                branch_name=branch,
                pull_request_url=pr_url,
                pull_request_number=pr_number,
                changed_files=changed_files,
                baseline_tests=baseline,
                post_refactor_tests=post_tests,
                heal_attempts=heal_attempts,
                diff_summary=self._diff_summary(changed_files),
                logs=logs,
            )
        finally:
            if project_dir:
                await asyncio.to_thread(GitSandboxService.cleanup, project_dir)

    # --- Async directory walkers -------------------------------------------

    @staticmethod
    async def _process_dir_async(project_dir: str, refactor_fn, context_rule: str) -> list[FileChange]:
        root = Path(project_dir)
        changes: list[FileChange] = []
        for path in sorted(root.rglob("*.py")):
            rel = path.relative_to(root).as_posix()
            if GitSandboxService._is_excluded(rel):
                continue
            try:
                before = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            try:
                after = await refactor_fn(before, context_rule)
            except Exception:  # noqa: BLE001
                continue
            if after and after != before:
                path.write_text(after, encoding="utf-8")
                changes.append(FileChange(rel_path=rel, before=before, after=after))
        return changes

    @staticmethod
    async def _heal_dir_async(project_dir: str, error_output: str, heal_fn, context_rule: str) -> list[FileChange]:
        from app.services.git_sandbox import GitSandboxService

        root = Path(project_dir)
        affected = GitSandboxService._files_from_error(project_dir, error_output)
        changes: list[FileChange] = []
        for rel in affected:
            path = root / rel
            try:
                broken = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            try:
                healed = await heal_fn(broken, error_output, context_rule)
            except Exception:  # noqa: BLE001
                continue
            if healed and healed != broken:
                path.write_text(healed, encoding="utf-8")
                changes.append(FileChange(rel_path=rel, before=broken, after=healed))
        return changes

    # --- Naming helpers ----------------------------------------------------

    @staticmethod
    def _branch_name() -> str:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"{settings.git_branch_prefix}/{stamp}"

    @staticmethod
    def _default_title(owner: str, repo: str) -> str:
        return f"[OmniMigrate] Modernize {owner}/{repo} to Python 3.12+"

    @staticmethod
    def _default_commit_message(changed_files: list[FileChange]) -> str:
        return f"refactor: apply Python 3.12+ modernization ({len(changed_files)} files)"

    @staticmethod
    def _default_body(changed_files: list[FileChange]) -> str:
        lines = [
            "## What changed",
            "",
            f"OmniMigrate migrated **{len(changed_files)}** file(s):",
            "",
        ]
        lines += [f"- `{f.rel_path}`" for f in changed_files]
        lines.append(
            "\nGenerated autonomously by the OmniMigrate migration engine "
            "(test-driven, self-healing)."
        )
        return "\n".join(lines)

    @staticmethod
    def _diff_summary(changed_files: list[FileChange]) -> str:
        from app.services.diff_utils import diff_stats, generate_diff

        lines = [f"{len(changed_files)} file(s) changed.\n"]
        for change in changed_files[:100]:
            diff = generate_diff(change.before, change.after, change.rel_path)
            stats = diff_stats(diff)
            lines.append(f"### {change.rel_path} (+{stats.additions}/-{stats.deletions})\n")
            if change.applied_rules:
                lines.append("Rules: " + ", ".join(change.applied_rules) + "\n")
        return "\n".join(lines)


# --- Arq worker entrypoint -------------------------------------------------

STAGE_TO_JOB_STATUS = {
    "clone": JobStatus.parsing.value,
    "baseline": JobStatus.analyzing.value,
    "refactor": JobStatus.refactoring.value,
    "verify": JobStatus.verifying.value,
    "heal": JobStatus.healing.value,
    "pr": JobStatus.refactoring.value,
    "done": JobStatus.completed.value,
}


async def run_autonomous_migration_job(
    ctx: dict,
    job_id: int,
    repo_url: str,
    repo_owner: str,
    repo_name: str,
    github_token: str,
    context_rule: str | None,
    base_branch: str,
    title: str | None = None,
    body: str | None = None,
) -> dict:
    """Arq worker task that runs the full pipeline for an autonomous job."""
    from datetime import datetime, timezone

    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models import MigrationJob
    from app.services.migration_service import MigrationEngine, STATE_KEY

    async with AsyncSessionLocal() as session:
        job = await session.get(MigrationJob, job_id)
        if job is None:
            raise RuntimeError(f"Autonomous job {job_id} not found.")
        redis = ctx["redis"]

        async def report(progress: int, stage: str, message: str) -> None:
            status = STAGE_TO_JOB_STATUS.get(stage, job.status)
            job.status = status
            job.updated_at = datetime.now(timezone.utc)
            await session.flush()
            try:
                await redis.set(
                    STATE_KEY.format(job_id=job.id),
                    MigrationEngine._encode_state(status, progress, message),
                    ex=3600 * 24 * 7,
                )
            except Exception:  # noqa: BLE001
                pass

        try:
            job.started_at = datetime.now(timezone.utc)
            await session.commit()
            orchestrator = AutonomousMigrationOrchestrator(progress=report)
            result = await orchestrator.execute_full_pipeline(
                repo_url=repo_url,
                github_token=github_token,
                repo_owner=repo_owner,
                repo_name=repo_name,
                context_rule=context_rule,
                base_branch=base_branch,
                title=title,
                body=body,
            )
            job.status = JobStatus.completed.value
            job.output_code = result.diff_summary
            job.diff = result.diff_summary
            job.metrics = result.to_dict()
            job.completed_at = datetime.now(timezone.utc)
            await session.commit()
            await redis.set(
                STATE_KEY.format(job_id=job.id),
                MigrationEngine._encode_state(
                    JobStatus.completed.value,
                    100,
                    f"PR created: {result.pull_request_url}",
                ),
                ex=3600 * 24 * 7,
            )
            return result.to_dict()
        except Exception as exc:  # noqa: BLE001 - record failures on the job.
            job.status = JobStatus.failed.value
            job.error_message = str(exc)[:4000]
            job.updated_at = datetime.now(timezone.utc)
            await session.commit()
            try:
                await redis.set(
                    STATE_KEY.format(job_id=job.id),
                    MigrationEngine._encode_state(JobStatus.failed.value, 100, str(exc)[:4000]),
                    ex=3600 * 24 * 7,
                )
            except Exception:  # noqa: BLE001
                pass
            raise
