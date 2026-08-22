/**
 * k6 Load Test — OmniMigrate API
 *
 * Targets:
 *   - Healthz: 100 RPS, p99 < 200ms
 *   - Auth endpoints: 50 RPS, p99 < 500ms
 *   - Job CRUD: 20 RPS, p99 < 1s
 *
 * Run:
 *   k6 run loadtest/smoke.js         # 1 min, 1 VU
 *   k6 run loadtest/load.js          # 10 min, ramp 1→50 VUs
 *   k6 run loadtest/stress.js        # 10 min, ramp 1→200 VUs
 *   k6 run loadtest/spike.js         # 5 min, spike to 500 VUs
 */
import http from "k6/http";
import { check, sleep } from "k6";
import { Counter, Rate, Trend } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const API_PREFIX = `${BASE_URL}/api/v1`;

// Custom metrics
const authLatency = new Trend("auth_latency");
const jobLatency = new Trend("job_latency");
const errorRate = new Rate("error_rate");

export const options = {
  thresholds: {
    http_req_duration: ["p(95)<500", "p(99)<1000"],
    http_req_failed: ["rate<0.05"],
    error_rate: ["rate<0.05"],
  },
};

// --- Helpers ---------------------------------------------------------------

function randomEmail() {
  return `loadtest_${Date.now()}_${Math.random().toString(36).slice(2, 8)}@test.com`;
}

function extractToken(response, key) {
  try {
    const body = JSON.parse(response.body);
    return body[key] || null;
  } catch {
    return null;
  }
}

// --- VU lifecycle -----------------------------------------------------------

let authToken = null;
let refreshToken = null;

export function setup() {
  // Register a test user and get tokens
  const email = randomEmail();
  const registerRes = http.post(
    `${API_PREFIX}/auth/register`,
    JSON.stringify({
      email,
      password: "LoadTest123!",
      full_name: "Load Test User",
    }),
    { headers: { "Content-Type": "application/json" } }
  );

  if (registerRes.status === 200 || registerRes.status === 201) {
    authToken = extractToken(registerRes, "access_token");
    refreshToken = extractToken(registerRes, "refresh_token");
  } else {
    // Try login if registration fails (user already exists)
    const loginRes = http.post(
      `${API_PREFIX}/auth/login`,
      JSON.stringify({ email, password: "LoadTest123!" }),
      { headers: { "Content-Type": "application/json" } }
    );
    authToken = extractToken(loginRes, "access_token");
    refreshToken = extractToken(loginRes, "refresh_token");
  }

  return { authToken, refreshToken };
}

export default function (data) {
  const headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${data.authToken}`,
  };

  // --- Healthz (unauthenticated) ---
  const healthRes = http.get(`${BASE_URL}/healthz`);
  check(healthRes, {
    "healthz status 200": (r) => r.status === 200,
    "healthz body ok": (r) => {
      try {
        return JSON.parse(r.body).status === "ok";
      } catch {
        return false;
      }
    },
  });

  // --- List projects (authenticated) ---
  const projectsRes = http.get(`${API_PREFIX}/projects`, { headers });
  check(projectsRes, {
    "list projects 200": (r) => r.status === 200,
  });
  if (projectsRes.status >= 400) errorRate.add(1);

  // --- Get current user ---
  const meRes = http.get(`${API_PREFIX}/users/me`, { headers });
  check(meRes, {
    "users/me 200": (r) => r.status === 200,
  });
  authLatency.add(meRes.timings.duration);

  // --- List jobs ---
  const jobsRes = http.get(`${API_PREFIX}/jobs`, { headers });
  check(jobsRes, {
    "list jobs 200": (r) => r.status === 200,
  });
  jobLatency.add(jobsRes.timings.duration);

  // --- Refresh token ---
  if (data.refreshToken) {
    const refreshRes = http.post(
      `${API_PREFIX}/auth/refresh`,
      JSON.stringify({ refresh_token: data.refreshToken }),
      { headers: { "Content-Type": "application/json" } }
    );
    check(refreshRes, {
      "refresh token 200": (r) => r.status === 200,
    });
    const newToken = extractToken(refreshRes, "access_token");
    if (newToken) data.authToken = newToken;
  }

  sleep(0.1); // 100ms think time between iterations
}

export function teardown(_data) {
  // Logout (best effort)
  if (data && data.refreshToken) {
    http.post(
      `${API_PREFIX}/auth/logout`,
      JSON.stringify({ refresh_token: data.refreshToken }),
      { headers: { "Content-Type": "application/json" } }
    );
  }
}
