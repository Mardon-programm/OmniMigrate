import posthog from "posthog-js";

let initialized = false;

export function initPostHog() {
  const apiKey = import.meta.env.VITE_POSTHOG_KEY;
  const host = import.meta.env.VITE_POSTHOG_HOST || "https://app.posthog.com";
  const environment = import.meta.env.VITE_APP_ENV || "development";

  if (!apiKey || initialized) {
    return;
  }

  posthog.init(apiKey, {
    api_host: host,
    capture_pageview: true,
    capture_pageleave: true,
    persistence: "localStorage",
    loaded: (ph) => {
      if (environment === "development") {
        ph.debug();
      }
    },
  });

  initialized = true;
}

export function captureEvent(
  event: string,
  properties?: Record<string, unknown>,
) {
  if (initialized) {
    posthog.capture(event, properties);
  }
}

export function identify(
  userId: string,
  traits?: Record<string, unknown>,
) {
  if (initialized) {
    posthog.identify(userId, traits);
  }
}

export function reset() {
  if (initialized) {
    posthog.reset();
  }
}

export function setUserProperties(properties: Record<string, unknown>) {
  if (initialized) {
    posthog.people.set(properties);
  }
}

export function getSessionId() {
  return posthog.get_session_id?.();
}

export function optOut() {
  posthog.opt_out_capturing();
}

export function optIn() {
  posthog.opt_in_capturing();
}