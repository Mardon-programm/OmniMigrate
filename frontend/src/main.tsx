import React, { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { initSentry } from "@/lib/sentry";
import { initPostHog } from "@/lib/posthog";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import App from "@/App";
import "@/index.css";

// Initialize Sentry as early as possible
initSentry();
// Initialize PostHog
initPostHog();

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element #root was not found");
}

createRoot(rootElement).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
);