import React from "react";
import PageState from "./PageState";

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an unhandled error:", error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <div style={{ padding: "2rem", maxWidth: "600px", margin: "2rem auto", textAlign: "center" }}>
          <PageState
            type="error"
            title="Something went wrong"
            message={this.state.error?.message || "An unexpected error occurred while rendering this view."}
          />
          <button
            type="button"
            className="academic-primary-button"
            onClick={this.handleReset}
            style={{ marginTop: "1rem", display: "inline-flex" }}
          >
            Try Again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
