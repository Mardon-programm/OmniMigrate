/**
 * k6 Load Test — Full API coverage with ramp-up
 *
 * Stages:
 *   30s warm-up → 2 min at 20 VUs → 2 min at 50 VUs → 2 min at 50 VUs → 2 min ramp down
 *
 * Targets: 20-50 concurrent users
 */
import http from "k6/http";
import { check, sleep } from "k6";
import { Counter, Rate, Trend } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const API_PREFIX = `${BASE_URL}/api/v1`;

const apiLatency = new Trend("api_latency");
const errorRate = new Rate("errors");

export const options = {
  stages: [
    { duration: "30s", target: 10 },
    { duration: "2m", target: 20 },
    { duration: "2m", target: 50 },
    { duration: "2m", target: 50 },
    { duration: "2m", target: 10 },
    { duration: "1m", target: 0 },
  ],
  thresholds: {
    http_req_duration: ["p(95)<800", "p(99)<2000"],
    http_req_failed: ["rate<0.10"],
  },
};

function randomEmail() {
  return `load_${Date.now()}_${Math.random().toString(36).slice(2, 8)}@test.com`;
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
      password: "LoadTest123!",
      full_name: "Load Test User",
    }),
    { headers: { "Content-Type": "application/json" } }
  );

  let token = extractToken(registerRes, "access_token");
  let refresh = extractToken(registerRes, "refresh_token");

  if (!token) {
    const loginRes = http.post(
      `${API_PREFIX}/auth/login`,
      JSON.stringify({ email, password: "LoadTest123!" }),
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

  // Core API paths — weighted by real usage patterns
  const endpoints = [
    { method: "GET", path: "/healthz", auth: false, weight: 5 },
    { method: "GET", path: "/users/me", auth: true, weight: 4 },
    { method: "GET", path: "/projects", auth: true, weight: 4 },
    { method: "GET", path: "/jobs", auth: true, weight: 3 },
    { method: "GET", path: "/billing/plans", auth: true, weight: 2 },
    { method: "GET", path: "/users", auth: true, weight: 1 },
  ];

  // Weighted random selection
  const totalWeight = endpoints.reduce((s, e) => s + e.weight, 0);
  let rand = Math.random() * totalWeight;
  let selected = endpoints[0];
  for (const ep of endpoints) {
    rand -= ep.weight;
    if (rand <= 0) {
      selected = ep;
      break;
    }
  }

  const url = selected.auth
    ? `${API_PREFIX}${selected.path}`
    : `${BASE_URL}${selected.path}`;
  const headers = selected.auth ? h : {};

  const res = http.request(selected.method, url, null, { headers });
  const ok = check(res, {
    "status is 2xx": (r) => r.status >= 200 && r.status < 300,
  });
  if (!ok) errorRate.add(1);
  apiLatency.add(res.timings.duration);

  sleep(0.2);
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
