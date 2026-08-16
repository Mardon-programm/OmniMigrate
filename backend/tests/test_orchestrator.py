import pytest

from app.services.git_sandbox import GitSandboxService, GitOperationError
from app.services.orchestrator import (
    AutonomousMigrationOrchestrator,
    STAGE_TO_JOB_STATUS,
)


class TestStageMapping:
    def test_all_pipeline_stages_mapped(self):
        expected = {"clone", "baseline", "refactor", "verify", "heal", "pr"}
        assert expected.issubset(STAGE_TO_JOB_STATUS.keys())
        assert STAGE_TO_JOB_STATUS["heal"] == "healing"
        assert STAGE_TO_JOB_STATUS["verify"] == "verifying"


class TestOrchestratorHelpers:
    def test_branch_name_uses_prefix(self, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "git_branch_prefix", "omnimigrate")
        branch = AutonomousMigrationOrchestrator._branch_name()
        assert branch.startswith("omnimigrate/")

    def test_diff_summary_lists_files(self):
        from app.services.git_sandbox import FileChange

        change = FileChange(
            rel_path="src/legacy.py",
            before="for i in xrange(3):\n    pass\n",
            after="for i in range(3):\n    pass\n",
            applied_rules=["xrange -> range"],
        )
        summary = AutonomousMigrationOrchestrator._diff_summary([change])
        assert "src/legacy.py" in summary
        assert "xrange -> range" in summary


class TestPipelineValidation:
    def test_rejects_file_url_end_to_end(self):
        with pytest.raises(GitOperationError):
            GitSandboxService.validate_repo_url("file:///etc/passwd")
