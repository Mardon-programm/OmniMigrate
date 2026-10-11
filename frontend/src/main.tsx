import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { initSentry } from "@/lib/sentry";
import { initPostHog } from "@/lib/posthog";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import App from "@/App";
import "@/index.css";

// Initialize Sentry and PostHog (side effects only)
void initSentry();
void initPostHog();

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