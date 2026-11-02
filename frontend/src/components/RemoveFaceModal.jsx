import { useState } from "react";
import {
  faCircleExclamation,
  faSpinner,
  faTriangleExclamation,
  faUserXmark,
  faXmark,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

import { removeStudentFaceRegistration } from "../services/faceService";

function getInitials(name) {
  if (!name) return "ST";
  return name
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function RemoveFaceModal({ isOpen, student, onClose, onSuccess }) {
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  if (!isOpen || !student) {
    return null;
  }

  const enrollmentNo = student.enrollment_no || student.roll_no || `ID: ${student.student_id}`;
  const studentName = student.name || "Student";
  const departmentText = student.department_name
    ? `${student.department_name}${student.department_code ? ` (${student.department_code})` : ""}`
    : student.department_code || "—";

  async function handleConfirm(e) {
    e.preventDefault();
    if (isSubmitting) return;

    setIsSubmitting(true);
    setError("");

    try {
      const result = await removeStudentFaceRegistration(student.student_id, {
        reason: reason.trim() || "Administrative removal of incorrect biometric registration",
      });

      if (!result?.success) {
        throw new Error(result?.message || "Failed to remove face registration.");
      }

      if (onSuccess) {
        onSuccess(result);
      }
      onClose();
    } catch (err) {
      console.error("Remove face registration error:", err);
      const msg =
        err?.response?.data?.message ||
        err?.message ||
        "Failed to remove face biometric registration. Please try again.";
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div
      className="student-modal-backdrop"
      role="presentation"
      onClick={() => {
        if (!isSubmitting) {
          onClose();
        }
      }}
    >
      <div
        className="student-dialog-box"
        role="dialog"
        aria-modal="true"
        aria-labelledby="remove-face-title"
        style={{ maxWidth: 540 }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="student-dialog-header">
          <div className="student-dialog-header-left">
            <div
              className="student-dialog-header-icon"
              style={{
                background: "#fef2f2",
                color: "#dc2626",
                border: "1px solid #fee2e2",
              }}
            >
              <FontAwesomeIcon icon={faUserXmark} />
            </div>
            <div>
              <h2 id="remove-face-title" style={{ color: "#991b1b" }}>
                Remove Face Registration
              </h2>
              <p>Deactivate student biometric facial recognition profile</p>
            </div>
          </div>
          <button
            type="button"
            className="student-dialog-close"
            onClick={onClose}
            disabled={isSubmitting}
            aria-label="Close modal"
          >
            <FontAwesomeIcon icon={faXmark} />
          </button>
        </div>

        {/* Target Student Identity Card */}
        <div
          style={{
            margin: "18px 24px 0",
            padding: "14px 16px",
            background: "#f8fafc",
            border: "1px solid #e2e8f0",
            borderRadius: "12px",
            display: "flex",
            alignItems: "center",
            gap: "14px",
          }}
        >
          {student.photo_url ? (
            <img
              src={student.photo_url}
              alt={studentName}
              style={{
                width: 52,
                height: 52,
                borderRadius: "50%",
                objectFit: "cover",
                border: "2px solid #e2e8f0",
                flexShrink: 0,
              }}
              onError={(e) => {
                e.currentTarget.style.display = "none";
              }}
            />
          ) : (
            <div
              style={{
                width: 52,
                height: 52,
                borderRadius: "50%",
                background: "#fee2e2",
                color: "#991b1b",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 700,
                fontSize: "18px",
                flexShrink: 0,
              }}
            >
              {getInitials(studentName)}
            </div>
          )}

          <div style={{ flex: 1, minWidth: 0 }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                flexWrap: "wrap",
                marginBottom: 2,
              }}
            >
              <strong style={{ fontSize: "15px", color: "#0f172a" }}>{studentName}</strong>
              <span
                style={{
                  fontSize: "11px",
                  fontWeight: 650,
                  padding: "1px 8px",
                  borderRadius: "9999px",
                  background: student.face_registered ? "#dcfce7" : "#fef3c7",
                  color: student.face_registered ? "#166534" : "#92400e",
                }}
              >
                {student.face_registered ? "Face Registered" : "Not Registered"}
              </span>
            </div>

            <div style={{ fontSize: "12px", color: "#64748b", lineHeight: 1.4 }}>
              <span>Roll / Enrollment: <strong style={{ color: "#1e293b" }}>{enrollmentNo}</strong></span>
              <span style={{ margin: "0 6px" }}>•</span>
              <span>{departmentText}</span>
              {student.semester != null && (
                <>
                  <span style={{ margin: "0 6px" }}>•</span>
                  <span>Sem {student.semester}</span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Warning Explanation Notice */}
        <div
          style={{
            margin: "14px 24px 0",
            padding: "14px 16px",
            background: "#fffbeb",
            border: "1px solid #fde68a",
            borderRadius: "12px",
            color: "#92400e",
            fontSize: "12.5px",
            lineHeight: 1.5,
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              fontWeight: 700,
              marginBottom: "8px",
              color: "#b45309",
            }}
          >
            <FontAwesomeIcon icon={faTriangleExclamation} />
            <span>Important Information & Consequences</span>
          </div>

          <ul style={{ margin: 0, paddingLeft: "18px" }}>
            <li style={{ marginBottom: "6px" }}>
              <strong>Biometric Deactivation:</strong> The student&apos;s face template will be removed from the active biometric recognition database.
            </li>
            <li style={{ marginBottom: "6px" }}>
              <strong>Attendance Suspended:</strong> Face-recognition attendance will <strong>NOT</strong> function for this student until a new face is registered.
            </li>
            <li>
              <strong style={{ color: "#065f46" }}>Records Preserved:</strong> Student profile details, enrolled courses, and all historical attendance records remain completely unchanged.
            </li>
          </ul>
        </div>

        <form onSubmit={handleConfirm}>
          <div style={{ padding: "16px 24px 0" }}>
            <label
              htmlFor="remove-face-reason"
              style={{
                display: "block",
                fontSize: "12px",
                fontWeight: 600,
                color: "#334155",
                marginBottom: 6,
              }}
            >
              Reason for Removal (Optional / Audit Log)
            </label>
            <input
              id="remove-face-reason"
              type="text"
              placeholder="e.g. Registered wrong student's face by accident, corrupted template"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              disabled={isSubmitting}
              style={{
                width: "100%",
                height: 38,
                borderRadius: 8,
                border: "1px solid #cbd5e1",
                padding: "0 12px",
                fontSize: "13px",
                color: "#1e293b",
                outline: "none",
                background: "#ffffff",
              }}
            />
            <small style={{ display: "block", fontSize: "11px", color: "#64748b", marginTop: 4 }}>
              This reason will be recorded in the system administrative audit log for security accountability.
            </small>
          </div>

          {error && (
            <div
              className="student-dialog-alert error"
              role="alert"
              style={{ marginTop: 14 }}
            >
              <FontAwesomeIcon icon={faCircleExclamation} />
              <span>{error}</span>
            </div>
          )}

          <div className="student-dialog-footer" style={{ marginTop: 18 }}>
            <button
              type="button"
              className="btn-secondary"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="face-reg-action-btn btn-remove"
              disabled={isSubmitting}
              style={{
                background: "#dc2626",
                color: "#ffffff",
                border: "none",
                height: 38,
                padding: "0 18px",
                borderRadius: 8,
                boxShadow: "0 2px 6px rgba(220, 38, 38, 0.25)",
              }}
            >
              {isSubmitting ? (
                <>
                  <FontAwesomeIcon icon={faSpinner} spin />
                  Removing Biometrics...
                </>
              ) : (
                <>
                  <FontAwesomeIcon icon={faUserXmark} />
                  Confirm & Remove Face
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default RemoveFaceModal;
