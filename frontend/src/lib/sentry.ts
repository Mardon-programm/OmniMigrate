import * as Sentry from "@sentry/react";
import { browserTracingIntegration, replayIntegration } from "@sentry/browser";

export function initSentry() {
  const dsn = import.meta.env.VITE_SENTRY_DSN;
  const environment = import.meta.env.VITE_APP_ENV || "development";

  if (!dsn) {
    return;
  }

  Sentry.init({
    dsn,
    environment,
    integrations: [
      browserTracingIntegration(),
      replayIntegration({
        maskAllText: true,
        blockAllMedia: true,
      }),
    ],
    tracesSampleRate: environment === "production" ? 0.1 : 1.0,
    replaysSessionSampleRate: 0.1,
    replaysOnErrorSampleRate: 1.0,
    debug: environment === "development",
    beforeSend(event) {
      // Filter out noisy errors
      if (event.exception) {
        const errorMessage = event.exception.values?.[0]?.value || "";
        if (
          errorMessage.includes("Network Error") ||
          errorMessage.includes("Failed to fetch") ||
          errorMessage.includes("ResizeObserver loop limit exceeded")
        ) {
          return null;
        }
      }
      return event;
    },
  });
}

export function captureException(error: Error, context?: Record<string, unknown>) {
  Sentry.captureException(error, { extra: context });
}

export function captureMessage(message: string, level: Sentry.SeverityLevel = "info") {
  Sentry.captureMessage(message, level);
}

export function setUserContext(user: { id: string; email: string; role: string } | null) {
  if (user) {
    Sentry.setUser({ id: user.id, email: user.email, role: user.role });
  } else {
    Sentry.setUser(null);
  }
}

export function addBreadcrumb(breadcrumb: Sentry.Breadcrumb) {
  Sentry.addBreadcrumb(breadcrumb);
}