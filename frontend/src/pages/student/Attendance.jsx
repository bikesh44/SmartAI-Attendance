import { useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  Calendar,
  Clock,
  BookOpen,
  GraduationCap,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Percent,
  Laptop,
  Code,
  Atom,
  MessageSquare,
  Calculator,
  RotateCcw,
  Info,
} from "lucide-react";
import { getStudentDailyPunch } from "../../services/attendanceService";
import "./Attendance.css";

const SUBJECT_THEMES = [
  { prefix: "CS", icon: Code, bg: "#eff6ff", color: "#2563eb", pillBg: "#dbeafe", pillColor: "#1d4ed8" },
  { prefix: "IT", icon: Laptop, bg: "#f0fdf4", color: "#16a34a", pillBg: "#dcfce7", pillColor: "#15803d" },
  { prefix: "MAT", icon: Calculator, bg: "#f5f3ff", color: "#7c3aed", pillBg: "#ede9fe", pillColor: "#6d28d9" },
  { prefix: "PHY", icon: Atom, bg: "#fef2f2", color: "#ef4444", pillBg: "#fee2e2", pillColor: "#b91c1c" },
  { prefix: "HUM", icon: MessageSquare, bg: "#fffbeb", color: "#d97706", pillBg: "#fef3c7", pillColor: "#b45309" },
];

function getSubjectTheme(code = "", index = 0) {
  const upper = (code || "").toUpperCase();
  for (const theme of SUBJECT_THEMES) {
    if (upper.startsWith(theme.prefix) || upper.includes(theme.prefix)) {
      return theme;
    }
  }
  return SUBJECT_THEMES[index % SUBJECT_THEMES.length];
}

function Attendance() {
  const navigate = useNavigate();

  // State
  const [targetDate, setTargetDate] = useState(() => new Date().toISOString().split("T")[0]);
  const [viewMode, setViewMode] = useState("week"); // "week" | "day"
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadTrigger, setReloadTrigger] = useState(0);
  const [selectedCourseDetail, setSelectedCourseDetail] = useState(null);

  // Fetch daily punch matrix data from backend
  useEffect(() => {
    let isCancelled = false;

    async function fetchData() {
      try {
        setLoading(true);
        setError("");

        const result = await getStudentDailyPunch({ date: targetDate });

        if (isCancelled) return;

        if (result?.success) {
          setData(result);
        } else {
          setData(null);
          setError(result?.message || "Unable to load attendance records.");
        }
      } catch (err) {
        if (isCancelled) return;
        setData(null);
        setError(
          err?.response?.data?.message ||
            err?.message ||
            "Failed to connect to student attendance service."
        );
      } finally {
        if (!isCancelled) {
          setLoading(false);
        }
      }
    }

    fetchData();

    return () => {
      isCancelled = true;
    };
  }, [targetDate, reloadTrigger]);

  // Date Navigation Handlers
  const handlePrevWeek = () => {
    const d = new Date(targetDate);
    d.setDate(d.getDate() - 7);
    setTargetDate(d.toISOString().split("T")[0]);
  };

  const handleNextWeek = () => {
    const d = new Date(targetDate);
    d.setDate(d.getDate() + 7);
    setTargetDate(d.toISOString().split("T")[0]);
  };

  const handleToday = () => {
    setTargetDate(new Date().toISOString().split("T")[0]);
  };

  const [lastUpdated, setLastUpdated] = useState(() => new Date());

  const handleRefresh = () => {
    setLastUpdated(new Date());
    setReloadTrigger((prev) => prev + 1);
  };

  // Derived properties from backend response
  const summaryCards = data?.summary_cards || {
    present_today: 0,
    absent_today: 0,
    total_classes_today: 0,
    attendance_rate: 0.0,
    selected_date_display: new Date(targetDate).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      weekday: "long",
    }),
  };

  const weekInfo = data?.week_info || {
    days: [],
    date_range_display: "Current Week",
  };

  const matrix = Array.isArray(data?.matrix) ? data.matrix : [];
  const todaySchedule = Array.isArray(data?.today_schedule) ? data.today_schedule : [];
  const overallSummary = data?.overall_summary || {
    attendance_rate: summaryCards.attendance_rate || 0,
    present_percentage: 0,
    absent_percentage: 0,
    late_percentage: 0,
  };

  // Donut chart calculation
  const overallRate = Number(overallSummary.attendance_rate || summaryCards.attendance_rate || 0);
  const presentRate = Number(overallSummary.present_percentage || overallRate);
  const absentRate = Number(overallSummary.absent_percentage || (overallRate > 0 ? (100 - overallRate).toFixed(1) : 0));
  const lateRate = Number(overallSummary.late_percentage || 0);

  // Circumference for r=38 is 2 * PI * 38 = 238.76
  const circumference = 238.76;
  const presentStroke = (presentRate / 100) * circumference;
  const absentStroke = (absentRate / 100) * circumference;

  // Last updated timestamp
  const lastUpdatedText = useMemo(() => {
    return lastUpdated.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }, [lastUpdated]);

  return (
    <div className="sams-attendance-page">
      {/* ========================================================
          1. DAILY PUNCH BANNER
      ======================================================== */}
      <section className="attendance-hero-banner" aria-label="Daily Punch Welcome Banner">
        <div className="attendance-hero-left">
          <div className="attendance-hero-icon-card">
            <Calendar size={28} className="attendance-hero-cal-icon" />
          </div>
          <div className="attendance-hero-text">
            <h1 className="attendance-hero-title">Daily Punch</h1>
            <p className="attendance-hero-subtitle">
              Mark your attendance and view your daily class attendance status.
            </p>
          </div>
        </div>

        {/* Center: Scalable student illustration */}
        <div className="attendance-hero-center" aria-hidden="true">
          <img
            src="/image/student_my_classes_banner.png"
            alt="Student studying with laptop and books"
            className="attendance-hero-student-img"
          />
        </div>

        {/* Right: Dynamic Selected Date Card */}
        <div className="attendance-hero-right">
          <div className="attendance-today-date-card">
            <div className="attendance-date-icon-badge">
              <Calendar size={20} />
            </div>
            <div className="attendance-date-details">
              <span className="attendance-date-label">Today&apos;s Date</span>
              <strong className="attendance-date-val">
                {new Date(targetDate).toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                })}
              </strong>
              <small className="attendance-date-weekday">
                ({new Date(targetDate).toLocaleDateString("en-US", { weekday: "long" })})
              </small>
            </div>
          </div>
        </div>
      </section>

      {/* ========================================================
          2. SUMMARY CARDS (4 CARDS)
      ======================================================== */}
      <section className="attendance-summary-grid" aria-label="Daily Attendance Summary">
        {/* Card 1: Present Today */}
        <div className="attendance-summary-card">
          <div className="attendance-stat-icon is-green">
            <CheckCircle2 size={22} strokeWidth={2.4} />
          </div>
          <div className="attendance-stat-content">
            <span className="attendance-stat-title">Present Today</span>
            <div className="attendance-stat-number-row">
              <strong className="attendance-stat-num is-green">
                {loading ? "..." : summaryCards.present_today}
              </strong>
              <span className="attendance-stat-denom">
                / {loading ? "..." : summaryCards.total_classes_today}
              </span>
            </div>
            <small className="attendance-stat-caption">classes attended</small>
          </div>
        </div>

        {/* Card 2: Absent Today */}
        <div className="attendance-summary-card">
          <div className="attendance-stat-icon is-red">
            <XCircle size={22} strokeWidth={2.4} />
          </div>
          <div className="attendance-stat-content">
            <span className="attendance-stat-title">Absent Today</span>
            <div className="attendance-stat-number-row">
              <strong className="attendance-stat-num is-red">
                {loading ? "..." : summaryCards.absent_today}
              </strong>
              <span className="attendance-stat-denom">
                / {loading ? "..." : summaryCards.total_classes_today}
              </span>
            </div>
            <small className="attendance-stat-caption">classes missed</small>
          </div>
        </div>

        {/* Card 3: Total Classes Today */}
        <div className="attendance-summary-card">
          <div className="attendance-stat-icon is-purple">
            <Clock size={22} strokeWidth={2.4} />
          </div>
          <div className="attendance-stat-content">
            <span className="attendance-stat-title">Total Classes Today</span>
            <div className="attendance-stat-number-row">
              <strong className="attendance-stat-num is-purple">
                {loading ? "..." : summaryCards.total_classes_today}
              </strong>
            </div>
            <small className="attendance-stat-caption">scheduled classes</small>
          </div>
        </div>

        {/* Card 4: Attendance Rate */}
        <div className="attendance-summary-card">
          <div className="attendance-stat-icon is-blue">
            <Percent size={22} strokeWidth={2.4} />
          </div>
          <div className="attendance-stat-content">
            <span className="attendance-stat-title">Attendance Rate</span>
            <div className="attendance-stat-number-row">
              <strong className="attendance-stat-num is-blue">
                {loading ? "..." : `${overallRate.toFixed(1)}%`}
              </strong>
            </div>
            <small className="attendance-stat-caption">(This Semester)</small>
          </div>
        </div>
      </section>

      {/* Error Banner */}
      {error && (
        <div className="attendance-error-banner" role="alert">
          <div className="attendance-error-icon">
            <Info size={18} />
          </div>
          <div className="attendance-error-msg">{error}</div>
          <button type="button" className="attendance-error-retry" onClick={handleRefresh}>
            <RotateCcw size={14} />
            <span>Retry</span>
          </button>
        </div>
      )}

      {/* ========================================================
          3. MAIN LAYOUT: MATRIX (LEFT) + RIGHT-SIDE PANELS
      ======================================================== */}
      <div className="attendance-main-layout">
        {/* LEFT / CENTER MAIN PANEL */}
        <div className="attendance-left-col">
          <div className="attendance-panel-card">
            {/* Header: Title + Navigation Controls */}
            <div className="attendance-panel-header">
              <div className="attendance-panel-title-wrap">
                <div className="attendance-panel-icon-badge">
                  <Calendar size={18} />
                </div>
                <div>
                  <h2 className="attendance-panel-title">Weekly Subject Attendance</h2>
                  <p className="attendance-panel-desc">
                    View your attendance for each subject across the week.
                  </p>
                </div>
              </div>

              {/* Controls: Prev, Range, Next, View Switcher */}
              <div className="attendance-controls-group">
                <div className="attendance-nav-btn-group">
                  <button
                    type="button"
                    className="attendance-nav-arrow"
                    onClick={handlePrevWeek}
                    title="Previous Week"
                    aria-label="Previous Week"
                  >
                    <ChevronLeft size={16} />
                  </button>

                  <div className="attendance-date-range-badge" title="Selected Academic Week">
                    <Calendar size={14} />
                    <span>{weekInfo.date_range_display}</span>
                  </div>

                  <button
                    type="button"
                    className="attendance-nav-arrow"
                    onClick={handleNextWeek}
                    title="Next Week"
                    aria-label="Next Week"
                  >
                    <ChevronRight size={16} />
                  </button>

                  <button
                    type="button"
                    className="attendance-today-chip"
                    onClick={handleToday}
                    title="Jump to Current Week"
                  >
                    Today
                  </button>
                </div>

                {/* Week / Day View Mode Toggle */}
                <div className="attendance-view-toggle" role="tablist">
                  <button
                    type="button"
                    role="tab"
                    aria-selected={viewMode === "week"}
                    className={`attendance-toggle-btn ${viewMode === "week" ? "is-active" : ""}`}
                    onClick={() => setViewMode("week")}
                  >
                    Week View
                  </button>
                  <button
                    type="button"
                    role="tab"
                    aria-selected={viewMode === "day"}
                    className={`attendance-toggle-btn ${viewMode === "day" ? "is-active" : ""}`}
                    onClick={() => setViewMode("day")}
                  >
                    Day View
                  </button>
                </div>
              </div>
            </div>

            {/* Panel Body: Table Matrix or Day View */}
            <div className="attendance-table-container">
              {loading ? (
                <div className="attendance-skeleton-table">
                  <div className="attendance-skeleton-row is-head" />
                  <div className="attendance-skeleton-row" />
                  <div className="attendance-skeleton-row" />
                  <div className="attendance-skeleton-row" />
                  <div className="attendance-skeleton-row" />
                  <div className="attendance-skeleton-row" />
                </div>
              ) : matrix.length === 0 ? (
                <div className="attendance-empty-state">
                  <BookOpen size={40} className="attendance-empty-icon" />
                  <h3>No Enrolled Courses Found</h3>
                  <p>
                    You are not currently enrolled in active course offerings for this academic term.
                  </p>
                </div>
              ) : viewMode === "week" ? (
                /* ========================================================
                   WEEK VIEW: SUBJECT-BY-WEEKDAY ATTENDANCE MATRIX
                ======================================================== */
                <table className="attendance-matrix-table" aria-label="Weekly Attendance Matrix">
                  <thead>
                    <tr>
                      <th className="th-subject">Subject / Course Code</th>
                      {weekInfo.days.map((day) => (
                        <th key={day.date} className={`th-day ${day.is_today ? "is-today" : ""}`}>
                          <div className="day-header-inner">
                            <span className="day-name">{day.short_day}</span>
                            <span className="day-date">{day.short_date}</span>
                          </div>
                        </th>
                      ))}
                      <th className="th-action" aria-label="Actions" />
                    </tr>
                  </thead>
                  <tbody>
                    {matrix.map((row, idx) => {
                      const theme = getSubjectTheme(row.course_code, idx);
                      const SubjectIcon = theme.icon;

                      return (
                        <tr
                          key={row.offering_id || row.course_code}
                          className="matrix-subject-row"
                          onClick={() => setSelectedCourseDetail(row)}
                        >
                          {/* Subject Info Column */}
                          <td className="td-subject-info">
                            <div className="subject-info-cell">
                              <div
                                className="subject-icon-wrap"
                                style={{ background: theme.bg, color: theme.color }}
                              >
                                <SubjectIcon size={16} />
                              </div>
                              <div className="subject-text-wrap">
                                <span className="subject-name">{row.course_name}</span>
                                <span
                                  className="subject-code-pill"
                                  style={{ background: theme.pillBg, color: theme.pillColor }}
                                >
                                  {row.course_code}
                                </span>
                              </div>
                            </div>
                          </td>

                          {/* 5 Weekday Status Cells */}
                          {weekInfo.days.map((day) => {
                            const cell = row.week_attendance?.[day.date] || {
                              scheduled: false,
                              status: "NO_CLASS",
                              sessions: [],
                            };

                            let statusBadge;
                            if (cell.status === "PRESENT") {
                              statusBadge = (
                                <span className="cell-pill is-present" title="Present">
                                  P
                                </span>
                              );
                            } else if (cell.status === "ABSENT") {
                              statusBadge = (
                                <span className="cell-pill is-absent" title="Absent">
                                  A
                                </span>
                              );
                            } else if (cell.status === "LATE") {
                              statusBadge = (
                                <span className="cell-pill is-late" title="Late">
                                  L
                                </span>
                              );
                            } else if (cell.status === "PENDING") {
                              statusBadge = (
                                <span
                                  className="cell-pill is-pending"
                                  title="Class scheduled today, attendance pending"
                                >
                                  •
                                </span>
                              );
                            } else if (cell.status === "UPCOMING") {
                              statusBadge = (
                                <span
                                  className="cell-pill is-upcoming"
                                  title="Scheduled upcoming class"
                                >
                                  —
                                </span>
                              );
                            } else if (cell.status === "UNRECORDED") {
                              statusBadge = (
                                <span
                                  className="cell-pill is-unrecorded"
                                  title="Scheduled class (session not conducted/recorded)"
                                >
                                  —
                                </span>
                              );
                            } else {
                              statusBadge = (
                                <span
                                  className="cell-pill is-noclass"
                                  title="No class scheduled"
                                >
                                  —
                                </span>
                              );
                            }

                            return (
                              <td
                                key={day.date}
                                className={`td-status-cell ${day.is_today ? "is-today-col" : ""}`}
                              >
                                {statusBadge}
                              </td>
                            );
                          })}

                          {/* Action Chevron */}
                          <td className="td-chevron-cell">
                            <button
                              type="button"
                              className="matrix-row-chevron"
                              title="View course attendance breakdown"
                              aria-label={`View ${row.course_name} details`}
                            >
                              <ChevronRight size={16} />
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              ) : (
                /* ========================================================
                   DAY VIEW: SCHEDULED CLASSES FOR SELECTED DATE
                ======================================================== */
                <div className="attendance-day-schedule-view">
                  <div className="day-view-header">
                    <h3>
                      Scheduled Classes for{" "}
                      {new Date(targetDate).toLocaleDateString("en-US", {
                        month: "long",
                        day: "numeric",
                        year: "numeric",
                        weekday: "long",
                      })}
                    </h3>
                  </div>

                  {todaySchedule.length === 0 ? (
                    <div className="attendance-empty-day">
                      <Clock size={36} className="empty-day-icon" />
                      <p>No classes are scheduled on this date.</p>
                    </div>
                  ) : (
                    <table className="day-schedule-table">
                      <thead>
                        <tr>
                          <th>Time</th>
                          <th>Course</th>
                          <th>Room</th>
                          <th>Faculty</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {todaySchedule.map((item) => (
                          <tr key={item.timetable_entry_id || `${item.course_code}-${item.start_time}`}>
                            <td className="td-time">
                              <div className="time-badge">
                                <Clock size={13} />
                                <span>{item.time_slot}</span>
                              </div>
                            </td>
                            <td className="td-course-name">
                              <strong>{item.course_name}</strong>
                              <span className="course-code-tag">{item.course_code}</span>
                            </td>
                            <td>{item.room || "TBD"}</td>
                            <td>{item.faculty_name || "Assigned Faculty"}</td>
                            <td>
                              <span
                                className={`day-status-pill is-${(
                                  item.attendance_status || "upcoming"
                                )
                                  .toLowerCase()
                                  .replace(/\s+/g, "-")}`}
                              >
                                {item.attendance_status}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              )}
            </div>

            {/* Card Footer: Legend + Last Updated */}
            <div className="attendance-panel-footer">
              <div className="attendance-legend-row" aria-label="Attendance Status Legend">
                <div className="legend-item">
                  <span className="cell-pill is-present is-sample">P</span>
                  <span>Present</span>
                </div>
                <div className="legend-item">
                  <span className="cell-pill is-absent is-sample">A</span>
                  <span>Absent</span>
                </div>
                <div className="legend-item">
                  <span className="cell-pill is-late is-sample">L</span>
                  <span>Late</span>
                </div>
                <div className="legend-item">
                  <span className="cell-pill is-noclass is-sample">—</span>
                  <span>No Class</span>
                </div>
              </div>

              <div className="attendance-last-updated">
                <span>Last updated: {lastUpdatedText}</span>
                <button
                  type="button"
                  className="attendance-refresh-btn"
                  onClick={handleRefresh}
                  title="Refresh attendance records"
                  aria-label="Refresh attendance"
                >
                  <RefreshCw size={13} />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: 3 SUPPORTING PANELS */}
        <aside className="attendance-right-col" aria-label="Supporting Attendance Information">
          {/* Panel 1: Quick Links */}
          <div className="attendance-side-card">
            <div className="side-card-header">
              <div className="side-card-icon-badge">
                <GraduationCap size={16} />
              </div>
              <h3 className="side-card-title">Quick Links</h3>
            </div>
            <div className="side-quick-links-list">
              <button
                type="button"
                className="side-link-row"
                onClick={() => navigate("/student/attendance-history")}
              >
                <div className="side-link-left">
                  <Calendar size={15} className="side-link-icon" />
                  <span>My Attendance</span>
                </div>
                <ChevronRight size={15} className="side-link-arrow" />
              </button>

              <button
                type="button"
                className="side-link-row"
                onClick={() => navigate("/student/timetable")}
              >
                <div className="side-link-left">
                  <Clock size={15} className="side-link-icon" />
                  <span>Timetable</span>
                </div>
                <ChevronRight size={15} className="side-link-arrow" />
              </button>

              <button
                type="button"
                className="side-link-row"
                onClick={() => navigate("/student/courses")}
              >
                <div className="side-link-left">
                  <BookOpen size={15} className="side-link-icon" />
                  <span>Academic Records</span>
                </div>
                <ChevronRight size={15} className="side-link-arrow" />
              </button>
            </div>
          </div>

          {/* Panel 2: Attendance Summary */}
          <div className="attendance-side-card">
            <div className="side-card-header">
              <div className="side-card-icon-badge">
                <Percent size={16} />
              </div>
              <h3 className="side-card-title">Attendance Summary</h3>
            </div>
            <div className="side-summary-body">
              {/* Donut Ring Chart */}
              <div className="side-donut-wrap">
                <svg className="attendance-donut-svg" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="38" className="donut-bg-ring" />
                  {/* Present Ring */}
                  <circle
                    cx="50"
                    cy="50"
                    r="38"
                    className="donut-segment is-present"
                    strokeDasharray={`${presentStroke} ${circumference}`}
                    strokeDashoffset="0"
                  />
                  {/* Absent Ring */}
                  {absentStroke > 0 && (
                    <circle
                      cx="50"
                      cy="50"
                      r="38"
                      className="donut-segment is-absent"
                      strokeDasharray={`${absentStroke} ${circumference}`}
                      strokeDashoffset={`${-presentStroke}`}
                    />
                  )}
                </svg>
                <div className="donut-center-label">
                  <strong>{loading ? "..." : `${overallRate.toFixed(1)}%`}</strong>
                  <small>Overall</small>
                </div>
              </div>

              {/* Breakdown Legend */}
              <div className="side-summary-breakdown">
                <div className="breakdown-row">
                  <div className="breakdown-label">
                    <span className="dot is-green" />
                    <span>Present</span>
                  </div>
                  <strong className="breakdown-val">
                    {loading ? "..." : `${presentRate.toFixed(1)}%`}
                  </strong>
                </div>

                <div className="breakdown-row">
                  <div className="breakdown-label">
                    <span className="dot is-red" />
                    <span>Absent</span>
                  </div>
                  <strong className="breakdown-val">
                    {loading ? "..." : `${absentRate.toFixed(1)}%`}
                  </strong>
                </div>

                <div className="breakdown-row">
                  <div className="breakdown-label">
                    <span className="dot is-yellow" />
                    <span>Late</span>
                  </div>
                  <strong className="breakdown-val">
                    {loading ? "..." : `${lateRate.toFixed(1)}%`}
                  </strong>
                </div>
              </div>
            </div>
          </div>

          {/* Panel 3: Today's Schedule */}
          <div className="attendance-side-card">
            <div className="side-card-header">
              <div className="side-card-icon-badge">
                <Clock size={16} />
              </div>
              <div>
                <h3 className="side-card-title">Today&apos;s Schedule</h3>
                <span className="side-card-subdate">
                  {new Date(targetDate).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                  })}{" "}
                  ({new Date(targetDate).toLocaleDateString("en-US", { weekday: "long" })})
                </span>
              </div>
            </div>

            <div className="side-schedule-timeline">
              {loading ? (
                <div className="schedule-timeline-skeleton">
                  <div className="skeleton-item" />
                  <div className="skeleton-item" />
                  <div className="skeleton-item" />
                </div>
              ) : todaySchedule.length === 0 ? (
                <div className="side-schedule-empty">
                  <p>No classes scheduled for this date.</p>
                </div>
              ) : (
                todaySchedule.map((slot) => {
                  const statusKey = (slot.attendance_status || "upcoming")
                    .toLowerCase()
                    .replace(/\s+/g, "-");

                  return (
                    <div
                      key={slot.timetable_entry_id || `${slot.course_code}-${slot.start_time}`}
                      className="side-schedule-item"
                    >
                      <div className={`schedule-item-dot is-${statusKey}`} />
                      <div className="schedule-item-content">
                        <span className="schedule-item-time">{slot.time_slot}</span>
                        <strong className="schedule-item-name">
                          {slot.course_name} ({slot.course_code})
                        </strong>
                        <span className="schedule-item-room">Room: {slot.room || "TBD"}</span>
                      </div>
                      <span className={`schedule-item-status is-${statusKey}`}>
                        {slot.attendance_status}
                      </span>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </aside>
      </div>

      {/* ========================================================
          4. COURSE DETAIL MODAL
      ======================================================== */}
      {selectedCourseDetail && (
        <div
          className="attendance-modal-overlay"
          onClick={() => setSelectedCourseDetail(null)}
          role="dialog"
          aria-modal="true"
        >
          <div className="attendance-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="attendance-modal-header">
              <div>
                <h3>{selectedCourseDetail.course_name}</h3>
                <span className="modal-course-badge">{selectedCourseDetail.course_code}</span>
              </div>
              <button
                type="button"
                className="attendance-modal-close"
                onClick={() => setSelectedCourseDetail(null)}
                aria-label="Close modal"
              >
                &times;
              </button>
            </div>

            <div className="attendance-modal-body">
              <div className="modal-meta-grid">
                <div>
                  <small>Semester & Section</small>
                  <strong>
                    Sem {selectedCourseDetail.semester} • Section {selectedCourseDetail.section}
                  </strong>
                </div>
                <div>
                  <small>Assigned Faculty</small>
                  <strong>{selectedCourseDetail.faculty_name}</strong>
                </div>
                <div>
                  <small>Classroom</small>
                  <strong>{selectedCourseDetail.room}</strong>
                </div>
              </div>

              <div className="modal-week-breakdown">
                <h4>Sessions in Selected Week</h4>
                <div className="modal-sessions-list">
                  {weekInfo.days.map((day) => {
                    const cell = selectedCourseDetail.week_attendance?.[day.date];
                    if (!cell || (!cell.scheduled && (!cell.sessions || cell.sessions.length === 0))) {
                      return null;
                    }

                    return (
                      <div key={day.date} className="modal-session-row">
                        <div className="session-row-date">
                          <strong>{day.day_name}</strong>
                          <small>{day.short_date}</small>
                        </div>
                        <div className="session-row-status">
                          <span
                            className={`cell-pill is-${(cell.status || "noclass").toLowerCase()}`}
                          >
                            {cell.status === "PRESENT"
                              ? "P (Present)"
                              : cell.status === "ABSENT"
                              ? "A (Absent)"
                              : cell.status === "LATE"
                              ? "L (Late)"
                              : cell.status === "PENDING"
                              ? "Pending"
                              : cell.status}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            <div className="attendance-modal-footer">
              <button
                type="button"
                className="modal-btn-close"
                onClick={() => setSelectedCourseDetail(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Attendance;
