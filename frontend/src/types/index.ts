export type UserRole = "admin" | "client" | "engineer";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface Project {
  id: number;
  owner_id: number;
  name: string;
  description: string | null;
  repo_url: string | null;
  source_language: string;
  target_stack: string;
  created_at: string;
  updated_at: string;
  job_count: number;
}

export interface JobStatusRead {
  id: number;
  project_id: number;
  title: string;
  status: JobStatus;
  self_heal_attempts: number;
  error_message: string | null;
  progress: number | null;
  message: string | null;
  created_at: string;
  updated_at: string;
}

export type JobStatus =
  | "queued"
  | "parsing"
  | "analyzing"
  | "refactoring"
  | "verifying"
  | "healing"
  | "completed"
  | "failed"
  | "cancelled";

export interface Finding {
  line: number | null;
  severity: "critical" | "warning" | "info";
  category: string;
  message: string;
  suggestion: string | null;
}

export interface Job {
  id: number;
  project_id: number;
  title: string;
  context_rule: string;
  status: JobStatus;
  input_code: string;
  output_code: string | null;
  diff: string | null;
  findings: Finding[];
  self_heal_attempts: number;
  error_message: string | null;
  metrics: {
    duration_seconds?: number;
    findings_count?: number;
    self_heal_attempts?: number;
    additions?: number;
    deletions?: number;
    net_lines?: number;
  };
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface LiveJobState {
  status: JobStatus;
  progress: number;
  message: string;
  timestamp: string;
}

export interface DiffStats {
  additions: number;
  deletions: number;
  files_changed: number;
  net_lines: number;
}

export interface DiffPayload {
  diff: string;
  stats: DiffStats;
}
