import { Component, ErrorInfo, ReactNode } from "react";
import * as Sentry from "@sentry/react";
import { AlertTriangle, RefreshCw, Home } from "lucide-react";
import { Link } from "react-router-dom";
import { useI18n } from "@/i18n";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    Sentry.captureException(error, {
      extra: {
        componentStack: errorInfo.componentStack,
      },
    });
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    const { t } = useI18n();

    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex min-h-screen items-center justify-center bg-bg-primary px-4">
          <div className="card max-w-md w-full p-8 text-center">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-danger/10">
              <AlertTriangle className="h-7 w-7 text-danger" />
            </div>
            <h2 className="text-heading-md font-semibold text-text-primary mb-2">
              {t("errorBoundary.title")}
            </h2>
            <p className="text-body-sm text-text-secondary mb-6">
              {t("errorBoundary.subtitle")}
            </p>
            {this.state.error && (
              <details className="mb-6 text-left">
                <summary className="cursor-pointer text-caption text-text-tertiary mb-2">
                  {t("errorBoundary.details")}
                </summary>
                <pre className="code-block p-3 max-h-40 overflow-auto text-[11px]">
                  {this.state.error.message}
                  {this.state.error.stack && "\n\n" + this.state.error.stack}
                </pre>
              </details>
            )}
            <div className="flex gap-3 justify-center">
              <button
                onClick={this.handleRetry}
                className="btn-primary"
              >
                <RefreshCw className="h-4 w-4" />
                {t("errorBoundary.retry")}
              </button>
              <Link to="/" className="btn-secondary">
                <Home className="h-4 w-4" />
                {t("errorBoundary.home")}
              </Link>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}