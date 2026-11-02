import { Navigate } from "react-router-dom";
import useAuth from "../hooks/useAuth";

function ProtectedRoute({ allowedRole, children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div style={{
        display: "flex",
        minHeight: "100vh",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: "#0f172a",
        color: "#94a3b8",
        fontFamily: "system-ui, -apple-system, sans-serif",
      }}>
        <div style={{ textAlign: "center" }}>
          <div style={{
            width: "36px",
            height: "36px",
            border: "3px solid rgba(255, 255, 255, 0.1)",
            borderTopColor: "#38bdf8",
            borderRadius: "50%",
            animation: "spin 0.8s linear infinite",
            margin: "0 auto 12px",
          }} />
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
          <span>Authenticating...</span>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/auth" replace />;
  }

  if (allowedRole && user.role !== allowedRole) {
    return <Navigate to="/unauthorized" replace />;
  }

  return children;
}

export default ProtectedRoute;