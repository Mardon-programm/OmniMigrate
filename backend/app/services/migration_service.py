from __future__ import annotations

import contextlib
import time
from datetime import UTC, datetime
from typing import Any

import structlog
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.prompts import DEFAULT_CONTEXT_RULE
from app.models import JobStatus, MigrationJob
from app.services.ast_parser import analyze_source
from app.services.diff_utils import diff_stats, generate_diff
from app.services.llm_agent import LLMAgent
from app.services.observability import record_sandbox_result
from app.services.rule_engine import apply_modernization_rules
from app.services.sandbox import CodeSandbox

logger = structlog.get_logger(__name__)

STATE_KEY = "job:state:{job_id}"


def _now() -> datetime:
    return datetime.now(UTC)


class MigrationEngine:
    """Orchestrates the autonomous refactoring pipeline for a single job."""

    def __init__(
        self,
        session: AsyncSession,
        redis: Redis,
        llm: LLMAgent | None = None,
        sandbox: CodeSandbox | None = None,
    ) -> None:
        self.session = session
        self.redis = redis
        self.llm = llm or LLMAgent()
        self.sandbox = sandbox or CodeSandbox()

    # --- State helpers --------------------------------------------------
    async def _push_state(
        self, job: MigrationJob, status: str, progress: int, message: str
    ) -> None:
        job.status = status
        job.updated_at = _now()
        await self.session.flush()
        try:
            await self.redis.set(
                STATE_KEY.format(job_id=job.id),
                self._encode_state(status, progress, message),
                ex=3600 * 24 * 7,
            )
        except Exception:  # Redis must never break the pipeline.
            logger.warning("Failed to publish job state to Redis", exc_info=True)

    @staticmethod
    def _encode_state(status: str, progress: int, message: str) -> str:
        import json

        return json.dumps(
            {
                "status": status,
                "progress": progress,
                "message": message,
                "timestamp": _now().isoformat(),
            }
        )

    async def _persist(self, job: MigrationJob) -> None:
        job.updated_at = _now()
        await self.session.commit()

    # --- Pipeline --------------------------------------------------------
    async def run(self, job_id: int) -> None:
        started = time.monotonic()
        job = await self.session.get(MigrationJob, job_id)
        if job is None:
            logger.error("Migration job %s not found", job_id)
            return

        if job.status == JobStatus.cancelled.value:
            logger.info("Migration job %s was cancelled, skipping", job_id)
            return

        try:
            await self._push_state(job, JobStatus.parsing.value, 5, "Parsing source code via AST")
            await self._persist(job)

            # 1. AST analysis.
            parse = analyze_source("source.py", job.input_code)
            findings = parse.findings
            if parse.parse_error:
                logger.warning("AST parse issue for job %s: %s", job_id, parse.parse_error)
            if parse.python_version_suggestion:
                findings.append(
                    {
                        "line": 0,
                        "severity": "critical",
                        "category": "python2-syntax",
                        "message": parse.python_version_suggestion,
                        "suggestion": "Pre-convert Python 2 syntax before running the engine.",
                    }
                )

            job.findings = findings
            await self._push_state(
                job, JobStatus.analyzing.value, 25, "Analyzing modernization opportunities"
            )
            await self._persist(job)

            # 2. Refactoring: LLM provider, or deterministic local rule engine
            #    as a no-key fallback so the pipeline stays fully functional.
            context_rule = job.context_rule or DEFAULT_CONTEXT_RULE
            use_local_rules = not settings.openai_api_key and settings.llm_fallback_to_rules
            provider = "local-rule-engine" if use_local_rules else "llm"
            await self._push_state(
                job,
                JobStatus.refactoring.value,
                45,
                f"Running refactoring pipeline ({provider})",
            )
            await self._persist(job)

            if use_local_rules:
                result = apply_modernization_rules(job.input_code)
                output_code = result.code
            else:
                output_code = await self.llm.refactor(job.input_code, context_rule, findings)
            job.output_code = output_code
            await self._persist(job)

            # 3. Sandbox verification with self-healing loop.
            await self._push_state(
                job, JobStatus.verifying.value, 70, "Verifying output in sandbox"
            )
            await self._persist(job)

            verification = self.sandbox.verify(output_code)
            attempt = 0
            while not verification.success and attempt < settings.max_self_heal_attempts:
                attempt += 1
                job.self_heal_attempts = attempt
                await self._push_state(
                    job,
                    JobStatus.healing.value,
                    70 + attempt * 8,
                    f"Self-healing attempt {attempt}/{settings.max_self_heal_attempts}",
                )
                await self._persist(job)

                error_text = "; ".join(verification.errors[:5])
                if use_local_rules:
                    healed = apply_modernization_rules(output_code).code
                else:
                    healed = await self.llm.self_heal(output_code, error_text, context_rule)
                job.output_code = healed
                output_code = healed
                await self._persist(job)

                verification = self.sandbox.verify(healed)

            if not verification.success:
                record_sandbox_result(success=False)
                raise RuntimeError(
                    "Sandbox verification failed after self-healing: "
                    + "; ".join(verification.errors[:5])
                )

            # 4. Diff + completion.
            record_sandbox_result(success=True)
            diff = generate_diff(job.input_code, output_code)
            job.diff = diff
            elapsed = time.monotonic() - started
            job.metrics = {
                "duration_seconds": round(elapsed, 3),
                "findings_count": len(findings),
                "self_heal_attempts": attempt,
                "provider": provider,
                "sandbox_stdout": verification.stdout[:2000],
                **diff_stats(diff).to_dict(),
            }
            job.completed_at = _now()
            await self._push_state(
                job, JobStatus.completed.value, 100, "Migration completed successfully"
            )
            await self._persist(job)
            logger.info("Migration job %s completed in %.2fs", job_id, elapsed)

        except Exception as exc:
            logger.exception("Migration job %s failed", job_id)
            job.status = JobStatus.failed.value
            job.error_message = str(exc)[:4000]
            job.updated_at = _now()
            with contextlib.suppress(Exception):  # Redis must never break cleanup.
                await self.redis.set(
                    STATE_KEY.format(job_id=job_id),
                    self._encode_state(JobStatus.failed.value, 100, str(exc)[:4000]),
                    ex=3600 * 24 * 7,
                )
            await self.session.commit()


async def run_migration_job(ctx: dict[str, Any], job_id: int) -> None:
    """Arq worker entrypoint for migration jobs."""
    from app.core.worker import create_session

    async with create_session() as session:
        redis: Redis = ctx["redis"]
        engine = MigrationEngine(session=session, redis=redis)
        await engine.run(job_id)
