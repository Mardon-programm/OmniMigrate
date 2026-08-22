/**
 * k6 Stress Test — breaking point discovery
 *
 * Stages:
 *   2 min at 10 → 2 min at 50 → 2 min at 100 → 2 min at 200 → 2 min ramp down
 *
 * Purpose: find the system's breaking point and observe degradation behavior
 */
import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8003";
const API_PREFIX = `${BASE_URL}/api/v1`;

const errorRate = new Rate("errors");
const latencyP99 = new Trend("latency_p99");

export const options = {
  stages: [
    { duration: "2m", target: 10 },
    { duration: "2m", target: 50 },
    { duration: "2m", target: 100 },
    { duration: "2m", target: 200 },
    { duration: "2m", target: 10 },
  ],
  thresholds: {
    http_req_duration: ["p(95)<2000", "p(99)<5000"],
  },
};

function randomEmail() {
  return `stress_${Date.now()}_${Math.random().toString(36).slice(2, 8)}@test.com`;
}

function extractToken(res, key) {
  try {
    return JSON.parse(res.body)[key] || null;
  } catch {
    return null;
  }
}

export function setup() {
  const email = randomEmail();
  const registerRes = http.post(
    `${API_PREFIX}/auth/register`,
    JSON.stringify({
      email,
      password: "StressTest123!",
      full_name: "Stress Test User",
    }),
    { headers: { "Content-Type": "application/json" } }
  );

  let token = extractToken(registerRes, "access_token");
  let refresh = extractToken(registerRes, "refresh_token");

  if (!token) {
    const loginRes = http.post(
      `${API_PREFIX}/auth/login`,
      JSON.stringify({ email, password: "StressTest123!" }),
      { headers: { "Content-Type": "application/json" } }
    );
    token = extractToken(loginRes, "access_token");
    refresh = extractToken(loginRes, "refresh_token");
  }

  return { token, refresh };
}

export default function (data) {
  const h = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${data.token}`,
  };

  // Hit the most expensive endpoints to find bottlenecks
  const scenarios = [
    () => http.get(`${BASE_URL}/healthz`),
    () => http.get(`${API_PREFIX}/users/me`, { headers: h }),
    () => http.get(`${API_PREFIX}/projects`, { headers: h }),
    () => http.get(`${API_PREFIX}/jobs`, { headers: h }),
    () => http.get(`${API_PREFIX}/billing/plans`, { headers: h }),
    () => http.get(`${API_PREFIX}/users`, { headers: h }),
  ];

  const res = scenarios[Math.floor(Math.random() * scenarios.length)]();
  const ok = res.status >= 200 && res.status < 400;
  if (!ok) errorRate.add(1);
  latencyP99.add(res.timings.duration);

  sleep(0.1);
}

export function teardown(data) {
  if (data && data.refresh) {
    http.post(
      `${API_PREFIX}/auth/logout`,
      JSON.stringify({ refresh_token: data.refresh }),
      { headers: { "Content-Type": "application/json" } }
    );
  }
}
