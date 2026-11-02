import { useEffect, useState } from "react";

import AuthContext from "./authContext";
import {
  login as loginRequest,
  logout as logoutRequest,
  getCurrentUser,
} from "../services/authService";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const saved = sessionStorage.getItem("sams_user");
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(() => {
    try {
      return !sessionStorage.getItem("sams_user");
    } catch {
      return true;
    }
  });

  // Restore authenticated user from the backend JWT cookie.
  useEffect(() => {
    async function restoreSession() {
      try {
        const result = await getCurrentUser();

        if (result?.success && result?.data) {
          setUser(result.data);
          try {
            sessionStorage.setItem("sams_user", JSON.stringify(result.data));
          } catch {
            // Ignore storage errors
          }
        } else {
          setUser(null);
          try {
            sessionStorage.removeItem("sams_user");
          } catch {
            // Ignore storage errors
          }
        }
      } catch {
        // No valid session or backend unavailable.
        setUser(null);
        try {
          sessionStorage.removeItem("sams_user");
        } catch {
          // Ignore storage errors
        }
      } finally {
        setLoading(false);
      }
    }

    restoreSession();
  }, []);

  async function login(credentials) {
    const result = await loginRequest({
      email: credentials.email,
      password: credentials.password,
    });

    if (result?.success && result?.data) {
      setUser(result.data);
      try {
        sessionStorage.setItem("sams_user", JSON.stringify(result.data));
      } catch {
        // Ignore storage errors
      }
    }

    return result;
  }

  async function logout() {
    try {
      await logoutRequest();
    } catch {
      // Clear frontend session even if backend logout fails.
    } finally {
      setUser(null);
      try {
        sessionStorage.removeItem("sams_user");
      } catch {
        // Ignore storage errors
      }
    }
  }

  const value = {
    user,
    loading,
    login,
    logout,
    isAuthenticated: Boolean(user),
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}