"use client";

import { Component, type ReactNode } from "react";
import { t as translate } from "@/lib/i18n";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  locale?: "ko" | "en";
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info);
  }

  private getLocale(): "ko" | "en" {
    if (this.props.locale) return this.props.locale;
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("neurohub-locale");
      if (stored === "ko" || stored === "en") return stored;
    }
    return "ko";
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      const locale = this.getLocale();
      return (
        <div className="panel" style={{ padding: 24, textAlign: "center" }}>
          <p style={{ fontWeight: 600, marginBottom: 8 }}>
            {translate("errorBoundary.sectionError", locale)}
          </p>
          <p style={{ color: "var(--muted)", fontSize: 13, marginBottom: 16 }}>
            {this.state.error?.message || translate("errorBoundary.unknownError", locale)}
          </p>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            {translate("common.retry", locale)}
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
