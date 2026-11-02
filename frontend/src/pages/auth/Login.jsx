import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  faUser,
  faGraduationCap,
  faUsers,
  faEnvelope,
  faLock,
  faEye,
  faEyeSlash,
  faShieldHalved,
  faFaceSmile,
  faClock,
  faRightToBracket,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

import useAuth from "../../hooks/useAuth";
import "./Login.css";

const roles = [
  {
    value: "ADMIN",
    label: "Administrator",
    icon: faUser,
  },
  {
    value: "FACULTY",
    label: "Faculty",
    icon: faGraduationCap,
  },
  {
    value: "STUDENT",
    label: "Student",
    icon: faUsers,
  },
];

function Login() {
  const navigate = useNavigate();
  const { login, logout } = useAuth();

  const [credentials, setCredentials] = useState({
    role: "",
    email: "",
    password: "",
  });

  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);

  const [message, setMessage] = useState("");

  const [fieldErrors, setFieldErrors] = useState({
    email: "",
    password: "",
    role: "",
  });

  const [loading, setLoading] = useState(false);

  function handleChange(event) {
    const { name, value } = event.target;

    setCredentials((current) => ({
      ...current,
      [name]: value,
    }));

    setFieldErrors((current) => ({
      ...current,
      [name]: "",
    }));

    if (message) {
      setMessage("");
    }
  }

  function handleRoleChange(role) {
    setCredentials((current) => ({
      ...current,
      role,
    }));

    setFieldErrors((current) => ({
      ...current,
      role: "",
    }));

    if (message) {
      setMessage("");
    }
  }

  function validateForm() {
    const errors = {
      email: "",
      password: "",
      role: "",
    };

    if (!credentials.role) {
      errors.role = "Please select a portal.";
    }

    if (!credentials.email.trim()) {
      errors.email = "Please enter your email or ID.";
    } else {
      /*
       * The current backend authentication contract
       * accepts an email and password.
       */
      const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

      if (!emailPattern.test(credentials.email.trim())) {
        errors.email = "Please enter a valid email address.";
      }
    }

    if (!credentials.password) {
      errors.password = "Please enter your password.";
    }

    setFieldErrors(errors);

    return Object.values(errors).some(Boolean);
  }

  function redirectByRole(role) {
    switch (role) {
      case "ADMIN":
        navigate("/admin", { replace: true });
        break;

      case "FACULTY":
        navigate("/faculty", { replace: true });
        break;

      case "STUDENT":
        navigate("/student", { replace: true });
        break;

      default:
        navigate("/unauthorized", { replace: true });
    }
  }

  function getRoleLabel(role) {
    switch (role) {
      case "ADMIN":
        return "Administrator";

      case "FACULTY":
        return "Faculty";

      case "STUDENT":
        return "Student";

      default:
        return "the correct portal";
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();

    setMessage("");

    const hasValidationErrors = validateForm();

    if (hasValidationErrors) {
      return;
    }

    setLoading(true);

    try {
      const result = await login({
        email: credentials.email.trim(),
        password: credentials.password,
      });

      if (!result?.success) {
        setMessage(result?.message || "Login failed.");
        return;
      }

      const authenticatedRole = result?.data?.role;

      if (!authenticatedRole) {
        setMessage(
          "Login succeeded, but the authenticated role was not provided.",
        );

        await logout();
        return;
      }

      /*
       * The selected portal is only a UI selection.
       * The backend-authenticated role is authoritative.
       */
      if (credentials.role !== authenticatedRole) {
        await logout();

        setMessage(
          `This account is registered as ${getRoleLabel(
            authenticatedRole,
          )}. Please select ${getRoleLabel(
            authenticatedRole,
          )} and try again.`,
        );

        return;
      }

      redirectByRole(authenticatedRole);
    } catch (error) {
      const backendMessage =
        error?.response?.data?.message ||
        "Authentication service is currently unavailable. Please try again later.";

      setMessage(backendMessage);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-page">
      {/* =====================================================
          LEFT CAMPUS PANEL
         ===================================================== */}

      <section className="login-campus-panel">
        <div className="campus-overlay" />

        <div className="campus-content">
          <div className="campus-brand">
            <img
              src="/sams-logo.png"
              alt="SAMS-FR"
              className="campus-logo"
            />

            <div>
              <h1>SAMS-FR</h1>
              <p>Smart Attendance Management System</p>
            </div>
          </div>

          <div className="campus-main-content">
            <h2>
              Smart Attendance
              <br />
              for a Smarter Campus
            </h2>

            <p className="campus-description">
              AI-powered attendance management
              <br />
              using face recognition technology.
            </p>

            <div className="campus-features">
              <div className="campus-feature">
                <span className="campus-feature-icon">
                  <FontAwesomeIcon icon={faShieldHalved} />
                </span>

                <span>
                  <strong>Secure</strong>
                  <small>Authentication</small>
                </span>
              </div>

              <div className="campus-feature-divider" />

              <div className="campus-feature">
                <span className="campus-feature-icon">
                  <FontAwesomeIcon icon={faFaceSmile} />
                </span>

                <span>
                  <strong>AI-Based</strong>
                  <small>Recognition</small>
                </span>
              </div>

              <div className="campus-feature-divider" />

              <div className="campus-feature">
                <span className="campus-feature-icon">
                  <FontAwesomeIcon icon={faClock} />
                </span>

                <span>
                  <strong>Real-Time</strong>
                  <small>Attendance</small>
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* =====================================================
          RIGHT LOGIN PANEL
         ===================================================== */}

      <section className="login-right-panel">
        <div className="login-institution-header">
          <span>© 2026 SAMS-FR</span>
          <span className="institution-divider">|</span>
          <span>Institutional Portal</span>
        </div>

        <div className="login-card">
          <div className="login-card-brand">
            <img
              src="/sams-logo.png"
              alt="SAMS-FR"
              className="login-card-logo"
            />

            <div>
              <h2>SAMS-FR</h2>
              <p>Smart Attendance Management System</p>
            </div>
          </div>

          <div className="login-heading">
            <h1>Welcome Back</h1>
            <p>Sign in to your account</p>
          </div>

          <form
            className="login-form"
            onSubmit={handleSubmit}
            noValidate
          >
            {/* =================================================
                PORTAL SELECTION
               ================================================= */}

            <div className="portal-field">
              <label>Select Role</label>

              <div className="portal-options">
                {roles.map((role) => (
                  <button
                    key={role.value}
                    type="button"
                    className={`portal-option ${
                      credentials.role === role.value
                        ? "portal-option-active"
                        : ""
                    }`}
                    onClick={() =>
                      handleRoleChange(role.value)
                    }
                    disabled={loading}
                    aria-pressed={
                      credentials.role === role.value
                    }
                  >
                    <FontAwesomeIcon icon={role.icon} />
                    <span>{role.label}</span>
                  </button>
                ))}
              </div>

              {fieldErrors.role && (
                <p className="field-error" role="alert">
                  {fieldErrors.role}
                </p>
              )}
            </div>

            {/* =================================================
                EMAIL / ID
               ================================================= */}

            <div className="login-field">
              <label htmlFor="email">Email / ID</label>

              <div
                className={`login-input-wrapper ${
                  fieldErrors.email
                    ? "login-input-error"
                    : ""
                }`}
              >
                <FontAwesomeIcon
                  icon={faEnvelope}
                  className="login-input-icon"
                />

                <input
                  id="email"
                  name="email"
                  type="email"
                  value={credentials.email}
                  onChange={handleChange}
                  placeholder="Enter your institutional email or ID"
                  autoComplete="username"
                  disabled={loading}
                  aria-invalid={Boolean(
                    fieldErrors.email,
                  )}
                  aria-describedby={
                    fieldErrors.email
                      ? "email-error"
                      : undefined
                  }
                />
              </div>

              {fieldErrors.email && (
                <p
                  id="email-error"
                  className="field-error"
                  role="alert"
                >
                  {fieldErrors.email}
                </p>
              )}
            </div>

            {/* =================================================
                PASSWORD
               ================================================= */}

            <div className="login-field">
              <label htmlFor="password">Password</label>

              <div
                className={`login-input-wrapper ${
                  fieldErrors.password
                    ? "login-input-error"
                    : ""
                }`}
              >
                <FontAwesomeIcon
                  icon={faLock}
                  className="login-input-icon"
                />

                <input
                  id="password"
                  name="password"
                  type={
                    showPassword ? "text" : "password"
                  }
                  value={credentials.password}
                  onChange={handleChange}
                  placeholder="Enter your password"
                  autoComplete="current-password"
                  disabled={loading}
                  aria-invalid={Boolean(
                    fieldErrors.password,
                  )}
                  aria-describedby={
                    fieldErrors.password
                      ? "password-error"
                      : undefined
                  }
                />

                <button
                  type="button"
                  className="password-toggle"
                  onClick={() =>
                    setShowPassword(
                      (current) => !current,
                    )
                  }
                  disabled={loading}
                  aria-label={
                    showPassword
                      ? "Hide password"
                      : "Show password"
                  }
                >
                  <FontAwesomeIcon
                    icon={
                      showPassword
                        ? faEyeSlash
                        : faEye
                    }
                  />
                </button>
              </div>

              {fieldErrors.password && (
                <p
                  id="password-error"
                  className="field-error"
                  role="alert"
                >
                  {fieldErrors.password}
                </p>
              )}
            </div>

            {/* =================================================
                REMEMBER + FORGOT PASSWORD
               ================================================= */}

            <div className="login-options">
              <label className="remember-option">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(event) =>
                    setRememberMe(event.target.checked)
                  }
                  disabled={loading}
                />

                <span className="custom-checkbox" />

                <span>Remember me</span>
              </label>

              <button
                type="button"
                className="forgot-password"
                onClick={() =>
                  navigate("/auth/forgot-password")
                }
                disabled={loading}
              >
                Forgot Password?
              </button>
            </div>

            {/* =================================================
                GENERAL AUTHENTICATION ERROR
               ================================================= */}

            {message && (
              <div
                className="login-message"
                role="alert"
                aria-live="polite"
              >
                <span className="message-icon">!</span>

                <p>{message}</p>
              </div>
            )}

            {/* =================================================
                LOGIN
               ================================================= */}

            <button
              type="submit"
              className="login-submit"
              disabled={loading}
            >
              <FontAwesomeIcon
                icon={faRightToBracket}
              />

              <span>
                {loading ? "Signing in..." : "Login"}
              </span>
            </button>
          </form>
        </div>
      </section>
    </main>
  );
}

export default Login;