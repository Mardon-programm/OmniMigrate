import axios, { AxiosError, type AxiosInstance } from "axios";

import type {
  DiffPayload,
  Finding,
  Job,
  JobStatusRead,
  Project,
  TokenResponse,
  User,
} from "@/types";

const TOKEN_KEY = "omnimigrate_access_token";
const REFRESH_KEY = "omnimigrate_refresh_token";

export class ApiError extends Error {
  status: number;
  code: string;
  errors?: unknown;

  constructor(status: number, message: string, code = "UNKNOWN", errors?: unknown) {
    super(message);
    this.status = status;
    this.code = code;
    this.errors = errors;
  }
}

export function getAccessToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(tokens: TokenResponse): void {
  localStorage.setItem(TOKEN_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
}

export function clearTokens(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

const client: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "/api/v1",
  timeout: 60000,
  headers: { "Content-Type": "application/json" },
});

client.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as typeof error.config & { _retried?: boolean };
    const status = error.response?.status;

    if (status === 401 && original && !original._retried && getRefreshToken()) {
      original._retried = true;
      try {
        const res = await axios.post<TokenResponse>(
          `${client.defaults.baseURL}/auth/refresh`,
          { refresh_token: getRefreshToken() },
        );
        setTokens(res.data);
        original.headers.Authorization = `Bearer ${res.data.access_token}`;
        return client(original);
      } catch {
        clearTokens();
        if (!window.location.pathname.startsWith("/login")) {
          window.location.href = "/login";
        }
      }
    }

    const detail = (error.response?.data as { detail?: string | unknown })?.detail;
    const code = (error.response?.data as { code?: string })?.code;
    if (typeof detail === "string") {
      throw new ApiError(status ?? 0, detail, code);
    }
    throw new ApiError(
      status ?? 0,
      error.message ?? "Network error",
      code,
      error.response?.data,
    );
  },
);

async function unwrap<T>(promise: Promise<{ data: T }>): Promise<T> {
  const res = await promise;
  return res.data;
}

export const api = {
  // Auth
  login: (email: string, password: string) =>
    unwrap(client.post<TokenResponse>("/auth/login", { email, password })),
  register: (email: string, password: string, full_name: string) =>
    unwrap(client.post<TokenResponse>("/auth/register", { email, password, full_name })),
  me: () => unwrap(client.get<User>("/auth/me")),

  // Projects
  listProjects: () => unwrap(client.get<Project[]>("/projects")),
  createProject: (data: Partial<Project>) =>
    unwrap(client.post<Project>("/projects", data)),
  getProject: (id: number) => unwrap(client.get<Project>(`/projects/${id}`)),
  updateProject: (id: number, data: Partial<Project>) =>
    unwrap(client.patch<Project>(`/projects/${id}`, data)),
  deleteProject: (id: number) => unwrap(client.delete(`/projects/${id}`)),

  // Jobs
  listJobs: (projectId?: number) =>
    unwrap(
      client.get<JobStatusRead[]>("/jobs", {
        params: projectId ? { project_id: projectId } : {},
      }),
    ),
  getJob: (id: number) => unwrap(client.get<Job>(`/jobs/${id}`)),
  getJobStatus: (id: number) =>
    unwrap(client.get<JobStatusRead>(`/jobs/${id}/status`)),
  getJobDiff: (id: number) => unwrap(client.get<{ job_id: number; diff: string }>(`/jobs/${id}/diff`)),
  getJobOutput: (id: number) =>
    unwrap(client.get<{ job_id: number; output_code: string }>(`/jobs/${id}/output`)),
  cancelJob: (id: number) => unwrap(client.delete(`/jobs/${id}`)),

  // Migration engine
  submitJob: (data: {
    project_id: number;
    title: string;
    context_rule?: string;
    input_code: string;
  }) => unwrap(client.post<Job>("/jobs", data)),
  analyze: (code: string, filename?: string) =>
    unwrap(
      client.post<{ success: boolean; findings: Finding[]; parse_error: string | null }>(
        "/migrations/analyze",
        { code, filename },
      ),
    ),
  previewDiff: (legacy: string, modern: string) =>
    unwrap(client.post<DiffPayload>("/migrations/preview-diff", { legacy, modern })),
  engineHealth: () => unwrap(client.get<Record<string, unknown>>("/migrations/health")),
};
