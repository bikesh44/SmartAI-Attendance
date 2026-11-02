import { useEffect, useRef, useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faBook,
  faCalendarDays,
  faClock,
  faDoorOpen,
  faGraduationCap,
  faSave,
  faSpinner,
  faTriangleExclamation,
  faUser,
  faXmark,
} from "@fortawesome/free-solid-svg-icons";

import "./EditTimetableModal.css";

const DAYS_OF_WEEK = [
  { value: "MONDAY", label: "Monday" },
  { value: "TUESDAY", label: "Tuesday" },
  { value: "WEDNESDAY", label: "Wednesday" },
  { value: "THURSDAY", label: "Thursday" },
  { value: "FRIDAY", label: "Friday" },
  { value: "SATURDAY", label: "Saturday" },
  { value: "SUNDAY", label: "Sunday" },
];

function titleCase(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function normalizeTimeForInput(val) {
  if (!val) return "";
  const parts = String(val).trim().split(":");
  if (parts.length >= 2) {
    const hr = String(Number(parts[0])).padStart(2, "0");
    const mn = String(Number(parts[1])).padStart(2, "0");
    if (!Number.isNaN(Number(hr)) && !Number.isNaN(Number(mn))) {
      return `${hr}:${mn}`;
    }
  }
  return String(val).trim();
}

function EditTimetableDialog({ entry, onClose, onSave }) {
  const firstInputRef = useRef(null);

  const isPersisted = Boolean(entry && entry.id !== undefined && entry.id !== null);

  const initialDay = (() => {
    const rawDay = entry.dayKey || entry.day_of_week || entry.day || "MONDAY";
    const normalizedDay = String(rawDay).trim().toUpperCase();
    return DAYS_OF_WEEK.find((d) => d.value === normalizedDay)
      ? normalizedDay
      : "MONDAY";
  })();

  const [day, setDay] = useState(initialDay);
  const [startTime, setStartTime] = useState(() =>
    normalizeTimeForInput(entry.startTime || entry.start_time || "")
  );
  const [endTime, setEndTime] = useState(() =>
    normalizeTimeForInput(entry.endTime || entry.end_time || "")
  );
  const [room, setRoom] = useState(() =>
    entry.room === "Not assigned" ? "" : (entry.room || "")
  );

  const [fieldErrors, setFieldErrors] = useState({});
  const [serverError, setServerError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    firstInputRef.current?.focus();
  }, []);

  // Extract display-only metadata
  const courseCode = entry.courseCode || entry.course_code || "";
  const courseName = entry.courseName || entry.course_name || "";
  const semester = entry.semester ?? "";
  const section = entry.section || entry.class_group || "";
  const faculty =
    entry.effectiveFaculty ||
    entry.faculty ||
    entry.faculty_name ||
    "Not assigned";
  const academicYear = entry.academicYear || entry.academic_year || "";

  function validate() {
    const errors = {};

    if (!day) {
      errors.day = "Please select a valid day of the week.";
    }

    const timePattern = /^([01]\d|2[0-3]):([0-5]\d)$/;

    if (!startTime) {
      errors.startTime = "Start time is required (HH:MM).";
    } else if (!timePattern.test(startTime)) {
      errors.startTime = "Start time must be in 24-hour HH:MM format.";
    }

    if (!endTime) {
      errors.endTime = "End time is required (HH:MM).";
    } else if (!timePattern.test(endTime)) {
      errors.endTime = "End time must be in 24-hour HH:MM format.";
    }

    if (startTime && endTime && timePattern.test(startTime) && timePattern.test(endTime)) {
      const [startH, startM] = startTime.split(":").map(Number);
      const [endH, endM] = endTime.split(":").map(Number);
      const startMinutes = startH * 60 + startM;
      const endMinutes = endH * 60 + endM;

      if (endMinutes <= startMinutes) {
        errors.endTime = "End time must be later than start time.";
      }
    }

    if (room && room.trim().length > 50) {
      errors.room = "Room name cannot exceed 50 characters.";
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setServerError("");

    if (!validate()) return;
    if (isSubmitting) return;

    setIsSubmitting(true);

    try {
      await onSave({
        day: titleCase(day),
        dayKey: day,
        startTime,
        endTime,
        room: room.trim(),
        entry,
        isPersisted,
      });
      onClose();
    } catch (err) {
      const respData = err?.response?.data;
      const errorMsg =
        respData?.message ||
        err?.message ||
        "Failed to save timetable changes. Please check for scheduling conflicts.";

      setServerError(errorMsg);

      if (respData?.field) {
        if (respData.field === "start_time" || respData.field === "time") {
          setFieldErrors((prev) => ({ ...prev, startTime: errorMsg }));
        } else if (respData.field === "end_time") {
          setFieldErrors((prev) => ({ ...prev, endTime: errorMsg }));
        } else if (respData.field === "room") {
          setFieldErrors((prev) => ({ ...prev, room: errorMsg }));
        } else if (respData.field === "day_of_week") {
          setFieldErrors((prev) => ({ ...prev, day: errorMsg }));
        }
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div
      className="edit-timetable-dialog-box"
      role="dialog"
      aria-modal="true"
      aria-labelledby="edit-timetable-modal-title"
    >
      {/* Header */}
      <div className="edit-timetable-dialog-header">
        <div className="edit-timetable-header-left">
          <div className="edit-timetable-header-icon">
            <FontAwesomeIcon icon={faClock} />
          </div>
          <div>
            <div className="edit-timetable-title-row">
              <h2 id="edit-timetable-modal-title">Edit Timetable Entry</h2>
              <span
                className={`edit-timetable-status-badge ${
                  isPersisted ? "is-persisted" : "is-extracted"
                }`}
                title={
                  isPersisted
                    ? "This entry is already saved in the database."
                    : "This entry is in the import pipeline and not yet committed."
                }
              >
                {isPersisted ? "Saved Database Entry" : "Extracted Row (Draft)"}
              </span>
            </div>
            <p>
              Modify schedule timings, day of week, and room assignment.
            </p>
          </div>
        </div>

        <button
          type="button"
          className="edit-timetable-close-btn"
          onClick={onClose}
          disabled={isSubmitting}
          aria-label="Close edit modal"
        >
          <FontAwesomeIcon icon={faXmark} />
        </button>
      </div>

      {/* Read-Only Context Information Card */}
      <div className="edit-timetable-context-card">
        <div className="edit-timetable-context-item">
          <FontAwesomeIcon icon={faBook} className="edit-timetable-context-icon" />
          <div className="edit-timetable-context-text">
            <span className="context-label">Course</span>
            <strong>
              {courseCode ? `${courseCode}` : "—"}
              {courseName ? ` · ${courseName}` : ""}
            </strong>
          </div>
        </div>

        <div className="edit-timetable-context-grid">
          <div className="edit-timetable-context-item">
            <FontAwesomeIcon icon={faGraduationCap} className="edit-timetable-context-icon" />
            <div className="edit-timetable-context-text">
              <span className="context-label">Semester & Section</span>
              <strong>
                {semester ? `Sem ${semester}` : "—"} {section ? `(Section ${section})` : ""}
              </strong>
            </div>
          </div>

          <div className="edit-timetable-context-item">
            <FontAwesomeIcon icon={faUser} className="edit-timetable-context-icon" />
            <div className="edit-timetable-context-text">
              <span className="context-label">Assigned Faculty</span>
              <strong>{faculty}</strong>
            </div>
          </div>
        </div>

        {academicYear && (
          <div className="edit-timetable-context-footer">
            <small>Academic Session: <strong>{academicYear}</strong></small>
          </div>
        )}
      </div>

      {/* Server Conflict / Error Alert */}
      {serverError && (
        <div className="edit-timetable-alert is-error" role="alert">
          <FontAwesomeIcon icon={faTriangleExclamation} className="alert-icon" />
          <div className="alert-message">
            <strong>Action Failed:</strong> {serverError}
          </div>
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="edit-timetable-form" noValidate>
        {/* Day of Week */}
        <div className="edit-timetable-field-group">
          <label htmlFor="edit-timetable-day">
            <FontAwesomeIcon icon={faCalendarDays} /> Day of the Week
          </label>
          <select
            id="edit-timetable-day"
            ref={firstInputRef}
            value={day}
            onChange={(e) => {
              setDay(e.target.value);
              if (fieldErrors.day) {
                setFieldErrors((prev) => ({ ...prev, day: "" }));
              }
            }}
            disabled={isSubmitting}
            className={fieldErrors.day ? "has-error" : ""}
            aria-invalid={Boolean(fieldErrors.day)}
          >
            {DAYS_OF_WEEK.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
          {fieldErrors.day && (
            <span className="edit-timetable-error-text">
              <FontAwesomeIcon icon={faTriangleExclamation} /> {fieldErrors.day}
            </span>
          )}
        </div>

        {/* Time Inputs: 2 Columns */}
        <div className="edit-timetable-time-row">
          <div className="edit-timetable-field-group">
            <label htmlFor="edit-timetable-start-time">
              <FontAwesomeIcon icon={faClock} /> Start Time (HH:MM)
            </label>
            <input
              id="edit-timetable-start-time"
              type="time"
              step="60"
              value={startTime}
              onChange={(e) => {
                setStartTime(e.target.value);
                if (fieldErrors.startTime) {
                  setFieldErrors((prev) => ({ ...prev, startTime: "" }));
                }
              }}
              disabled={isSubmitting}
              className={fieldErrors.startTime ? "has-error" : ""}
              aria-invalid={Boolean(fieldErrors.startTime)}
              required
            />
            {fieldErrors.startTime && (
              <span className="edit-timetable-error-text">
                <FontAwesomeIcon icon={faTriangleExclamation} /> {fieldErrors.startTime}
              </span>
            )}
          </div>

          <div className="edit-timetable-field-group">
            <label htmlFor="edit-timetable-end-time">
              <FontAwesomeIcon icon={faClock} /> End Time (HH:MM)
            </label>
            <input
              id="edit-timetable-end-time"
              type="time"
              step="60"
              value={endTime}
              onChange={(e) => {
                setEndTime(e.target.value);
                if (fieldErrors.endTime) {
                  setFieldErrors((prev) => ({ ...prev, endTime: "" }));
                }
              }}
              disabled={isSubmitting}
              className={fieldErrors.endTime ? "has-error" : ""}
              aria-invalid={Boolean(fieldErrors.endTime)}
              required
            />
            {fieldErrors.endTime && (
              <span className="edit-timetable-error-text">
                <FontAwesomeIcon icon={faTriangleExclamation} /> {fieldErrors.endTime}
              </span>
            )}
          </div>
        </div>

        {/* Room Number */}
        <div className="edit-timetable-field-group">
          <label htmlFor="edit-timetable-room">
            <FontAwesomeIcon icon={faDoorOpen} /> Room / Classroom / Lab
          </label>
          <input
            id="edit-timetable-room"
            type="text"
            placeholder="e.g. CSE-1A-01, Room 203, Lab 4"
            value={room}
            onChange={(e) => {
              setRoom(e.target.value);
              if (fieldErrors.room) {
                setFieldErrors((prev) => ({ ...prev, room: "" }));
              }
            }}
            disabled={isSubmitting}
            className={fieldErrors.room ? "has-error" : ""}
            aria-invalid={Boolean(fieldErrors.room)}
            maxLength={50}
          />
          {fieldErrors.room && (
            <span className="edit-timetable-error-text">
              <FontAwesomeIcon icon={faTriangleExclamation} /> {fieldErrors.room}
            </span>
          )}
          <small className="edit-timetable-field-hint">
            Enter room code or number. Leave blank if no dedicated venue is assigned.
          </small>
        </div>

        {/* Modal Actions */}
        <div className="edit-timetable-modal-actions">
          <button
            type="button"
            className="edit-timetable-btn-cancel"
            onClick={onClose}
            disabled={isSubmitting}
          >
            Cancel
          </button>
          <button
            type="submit"
            id="edit-timetable-save-btn"
            className="edit-timetable-btn-save"
            disabled={isSubmitting}
          >
            <FontAwesomeIcon
              icon={isSubmitting ? faSpinner : faSave}
              spin={isSubmitting}
            />
            {isSubmitting ? "Saving Changes..." : "Save Changes"}
          </button>
        </div>
      </form>
    </div>
  );
}

export default function EditTimetableModal({
  isOpen,
  entry,
  onClose,
  onSave,
}) {
  // Keyboard accessibility: Close on Escape key
  useEffect(() => {
    if (!isOpen) return;

    function handleKeyDown(e) {
      if (e.key === "Escape") {
        onClose();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !entry) return null;

  const entryKey = entry.id !== undefined && entry.id !== null
    ? `persisted-${entry.id}`
    : `extracted-${entry.index}`;

  return (
    <div
      className="edit-timetable-modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
      role="presentation"
    >
      <EditTimetableDialog
        key={entryKey}
        entry={entry}
        onClose={onClose}
        onSave={onSave}
      />
    </div>
  );
}
