from pydantic import BaseModel, Field


class AutonomousRunRequest(BaseModel):
    """Start a full git + test-driven autonomous migration."""

    repo_url: str = Field(min_length=8, max_length=512)
    repo_owner: str = Field(min_length=1, max_length=128)
    repo_name: str = Field(min_length=1, max_length=128)
    github_token: str = Field(min_length=1, max_length=256)
    context_rule: str | None = Field(default=None, max_length=10000)
    base_branch: str = Field(default="main", min_length=1, max_length=128)
    title: str | None = Field(default=None, max_length=255)
    body: str | None = Field(default=None, max_length=10000)


class AutonomousRunResponse(BaseModel):
    job_id: int
    project_id: int
    status: str
    message: str


class AutonomousJobDetail(BaseModel):
    job_id: int
    status: str
    progress: int | None = None
    message: str | None = None
    pull_request_url: str | None = None
    branch_name: str | None = None
    error_message: str | None = None
    diff_summary: str | None = None
