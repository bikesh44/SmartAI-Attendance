import { useLocation, useNavigate } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import {
  faArrowLeft,
  faShieldHalved,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

import "./VerifyOtp.css";

function VerifyOtp() {
  const navigate = useNavigate();
  const location = useLocation();

  const method = location.state?.method || "email";
  const identifier = location.state?.identifier || "";

  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [resendTimer, setResendTimer] = useState(30);

  const inputRefs = useRef([]);

  useEffect(() => {
    const timer = setInterval(() => {
      setResendTimer((current) => {
        if (current <= 1) {
          clearInterval(timer);
          return 0;
        }

        return current - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    inputRefs.current[0]?.focus();
  }, []);

  function handleOtpChange(index, value) {
    if (!/^\d?$/.test(value)) {
      return;
    }

    const updatedOtp = [...otp];
    updatedOtp[index] = value;

    setOtp(updatedOtp);
    setError("");

    if (value && index < otp.length - 1) {
      inputRefs.current[index + 1]?.focus();
    }
  }

  function handleKeyDown(index, event) {
    if (
      event.key === "Backspace" &&
      !otp[index] &&
      index > 0
    ) {
      inputRefs.current[index - 1]?.focus();
    }
  }

  function handlePaste(event) {
    event.preventDefault();

    const pastedValue = event.clipboardData
      .getData("text")
      .replace(/\D/g, "")
      .slice(0, 6);

    if (!pastedValue) {
      return;
    }

    const updatedOtp = [...otp];

    pastedValue.split("").forEach((digit, index) => {
      updatedOtp[index] = digit;
    });

    setOtp(updatedOtp);
    setError("");

    const nextIndex = Math.min(
      pastedValue.length,
      otp.length - 1
    );

    inputRefs.current[nextIndex]?.focus();
  }

  function handleSubmit(event) {
    event.preventDefault();

    const enteredOtp = otp.join("");

    if (enteredOtp.length !== 6) {
      setError("Please enter the complete 6-digit OTP.");
      return;
    }

    /*
     * Backend OTP verification is not implemented yet.
     * This is temporary frontend behavior.
     */
    setLoading(true);

    setTimeout(() => {
      setLoading(false);

      setError(
        "OTP verification service is not connected yet. Please try again after backend integration."
      );
    }, 500);
  }

  function handleResend() {
    if (resendTimer > 0 || loading) {
      return;
    }

    /*
     * Temporary frontend behavior.
     * Real resend functionality will use the backend API.
     */
    setResendTimer(30);
    setError("");
  }

  const maskedIdentifier =
    method === "email"
      ? identifier.replace(
          /^(.{2}).*(@.*)$/,
          "$1••••$2"
        )
      : identifier
        ? `••••••${identifier.slice(-4)}`
        : "";

  return (
    <main className="verify-otp-page">
      <section className="verify-otp-card">
        <div className="verify-otp-brand">
          <img
            src="/sams-logo.png"
            alt="SAMS-FR"
            className="verify-otp-logo"
          />

          <div>
            <h1>SAMS-FR</h1>
            <p>Smart Attendance Management System</p>
          </div>
        </div>

        <div className="verify-otp-icon">
          <FontAwesomeIcon icon={faShieldHalved} />
        </div>

        <div className="verify-otp-heading">
          <h2>Verify Your Account</h2>

          <p>
            Enter the 6-digit verification code sent to
            your registered {method === "email" ? "email" : "phone"}.
          </p>

          {maskedIdentifier && (
            <strong>{maskedIdentifier}</strong>
          )}
        </div>

        <div className="otp-notice-box" role="status">
          <p>
            <strong>Advisory:</strong> Automated email/SMS OTP delivery is currently not configured. If you require an account password reset, please contact the administrator at <code>admin@sams.institution.edu</code>.
          </p>
        </div>

        <form
          className="verify-otp-form"
          onSubmit={handleSubmit}
          noValidate
        >
          <div className="otp-inputs">
            {otp.map((digit, index) => (
              <input
                key={index}
                ref={(element) => {
                  inputRefs.current[index] = element;
                }}
                type="text"
                inputMode="numeric"
                maxLength={1}
                value={digit}
                onChange={(event) =>
                  handleOtpChange(
                    index,
                    event.target.value
                  )
                }
                onKeyDown={(event) =>
                  handleKeyDown(index, event)
                }
                onPaste={
                  index === 0
                    ? handlePaste
                    : undefined
                }
                disabled={loading}
                aria-label={`OTP digit ${index + 1}`}
                className={
                  error ? "otp-input otp-input-error" : "otp-input"
                }
              />
            ))}
          </div>

          {error && (
            <p className="otp-error">
              {error}
            </p>
          )}

          <button
            type="submit"
            className="verify-otp-submit"
            disabled={loading}
          >
            {loading ? "Verifying..." : "Verify OTP"}
          </button>
        </form>

        <div className="otp-resend">
          {resendTimer > 0 ? (
            <p>
              Resend code in{" "}
              <strong>{resendTimer}s</strong>
            </p>
          ) : (
            <button
              type="button"
              onClick={handleResend}
              disabled={loading}
            >
              Resend OTP
            </button>
          )}
        </div>

        <button
          type="button"
          className="verify-otp-back"
          onClick={() => navigate("/auth/forgot-password")}
          disabled={loading}
        >
          <FontAwesomeIcon icon={faArrowLeft} />
          <span>Back</span>
        </button>
      </section>
    </main>
  );
}

export default VerifyOtp;