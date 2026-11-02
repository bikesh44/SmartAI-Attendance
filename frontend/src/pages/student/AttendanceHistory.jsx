import { useEffect, useState, useId } from "react";
import { Link } from "react-router-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faCalendarDays,
  faClock,
  faCheck,
  faXmark,
  faFilter,
  faRotateRight,
  faChevronLeft,
  faChevronRight,
  faLightbulb,
  faUser,
  faDoorOpen,
  faGraduationCap,
  faIdBadge,
} from "@fortawesome/free-solid-svg-icons";

import useAuth from "../../hooks/useAuth";
import {
  getStudentAttendance,
  getStudentAttendanceSummary,
  getStudentAttendanceDetail,
} from "../../services/attendanceService";
import { getStudentProfile } from "../../services/studentService";
import PageState from "../../components/PageState";
import "./AttendanceHistory.css";

const PAGE_SIZE = 10;

function formatDisplayDate(dateStr) {
  if (!dateStr) return "-";
  try {
    const d = new Date(dateStr);
    if (Number.isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "2-digit",
      year: "numeric",
    });
  } catch {
    return dateStr;
  }
}

function AttendanceHistory() {
  const auth = useAuth();
  const loggedInUser = auth?.user;

  // Student Profile
  const [profile, setProfile] = useState(null);

  // Filter States
  const [academicYear, setAcademicYear] = useState("all");
  const [semester, setSemester] = useState("all");
  const [courseId, setCourseId] = useState("all");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [dateError, setDateError] = useState("");

  // Applied Filters (used to trigger data fetching)
  const [appliedFilters, setAppliedFilters] = useState({
    academicYear: "all",
    semester: "all",
    courseId: "all",
    dateFrom: "",
    dateTo: "",
  });

  // Filter Options (populated from backend)
  const [filterOptions, setFilterOptions] = useState({
    academic_years: [],
    semesters: [],
    courses: [],
  });

  // Table & Summary States
  const [attendanceRecords, setAttendanceRecords] = useState([]);
  const [page, setPage] = useState(1);
  const [totalRecords, setTotalRecords] = useState(0);
  const [totalPages, setTotalPages] = useState(0);

  const [summary, setSummary] = useState({
    total_sessions: 0,
    present_sessions: 0,
    absent_sessions: 0,
    late_sessions: 0,
    present_days: 0,
    absent_days: 0,
    late_days: 0,
    total_days: 0,
    attendance_percentage: 0,
  });

  const [courseSummaries, setCourseSummaries] = useState([]);

  // Loading & Error States
  const [tableLoading, setTableLoading] = useState(true);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [error, setError] = useState("");

  // Record Detail Modal
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Generate unique IDs for form labels
  const academicYearId = useId();
  const semesterId = useId();
  const courseIdInputId = useId();
  const dateFromId = useId();
  const dateToId = useId();

  // Load Profile once
  useEffect(() => {
    let active = true;
    getStudentProfile()
      .then((res) => {
        if (active && res?.success && res.data) {
          setProfile(res.data);
        }
      })
      .catch(() => {});

    return () => {
      active = false;
    };
  }, []);

  // Load Summary & Filter Options whenever applied filters change
  useEffect(() => {
    let active = true;

    async function loadSummary() {
      try {
        setSummaryLoading(true);
        const params = {};

        if (appliedFilters.academicYear !== "all") {
          params.academic_year = appliedFilters.academicYear;
        }
        if (appliedFilters.semester !== "all") {
          params.semester = appliedFilters.semester;
        }
        if (appliedFilters.courseId !== "all") {
          params.course_id = appliedFilters.courseId;
        }
        if (appliedFilters.dateFrom) {
          params.date_from = appliedFilters.dateFrom;
        }
        if (appliedFilters.dateTo) {
          params.date_to = appliedFilters.dateTo;
        }

        const res = await getStudentAttendanceSummary(params);
        if (!active) return;

        if (res?.success) {
          if (res.overall) {
            setSummary(res.overall);
          }
          if (Array.isArray(res.data)) {
            setCourseSummaries(res.data);
          }
          if (res.filter_options) {
            setFilterOptions((prev) => ({
              academic_years:
                res.filter_options.academic_years?.length > 0
                  ? res.filter_options.academic_years
                  : prev.academic_years,
              semesters:
                res.filter_options.semesters?.length > 0
                  ? res.filter_options.semesters
                  : prev.semesters,
              courses:
                res.filter_options.courses?.length > 0
                  ? res.filter_options.courses
                  : prev.courses,
            }));
          }
        }
      } catch (err) {
        if (!active) return;
        // Non-blocking summary error handling
        console.error("Failed to load attendance summary:", err);
      } finally {
        if (active) {
          setSummaryLoading(false);
        }
      }
    }

    loadSummary();

    return () => {
      active = false;
    };
  }, [appliedFilters]);

  // Load Paginated Records whenever applied filters or page change
  useEffect(() => {
    let active = true;

    async function loadRecords() {
      try {
        setTableLoading(true);
        setError("");

        const params = {
          page,
          per_page: PAGE_SIZE,
        };

        if (appliedFilters.academicYear !== "all") {
          params.academic_year = appliedFilters.academicYear;
        }
        if (appliedFilters.semester !== "all") {
          params.semester = appliedFilters.semester;
        }
        if (appliedFilters.courseId !== "all") {
          params.course_id = appliedFilters.courseId;
        }
        if (appliedFilters.dateFrom) {
          params.date_from = appliedFilters.dateFrom;
        }
        if (appliedFilters.dateTo) {
          params.date_to = appliedFilters.dateTo;
        }

        const result = await getStudentAttendance(params);
        if (!active) return;

        if (!result?.success) {
          setAttendanceRecords([]);
          setTotalRecords(0);
          setTotalPages(0);
          setError(result?.message || "Unable to load attendance records.");
          return;
        }

        setAttendanceRecords(result.data ?? []);
        setTotalRecords(result.total_records ?? 0);
        setTotalPages(result.total_pages ?? 0);
      } catch (err) {
        if (!active) return;
        setAttendanceRecords([]);
        setTotalRecords(0);
        setTotalPages(0);
        setError(
          err?.response?.data?.message || "Unable to load attendance records."
        );
      } finally {
        if (active) {
          setTableLoading(false);
        }
      }
    }

    loadRecords();

    return () => {
      active = false;
    };
  }, [page, appliedFilters]);

  // Filter Actions
  const handleApplyFilters = (e) => {
    e.preventDefault();

    if (dateFrom && dateTo && dateFrom > dateTo) {
      setDateError("Start date cannot be after end date.");
      return;
    }
    setDateError("");

    setAppliedFilters({
      academicYear,
      semester,
      courseId,
      dateFrom,
      dateTo,
    });
    setPage(1);
  };

  const handleResetFilters = () => {
    setAcademicYear("all");
    setSemester("all");
    setCourseId("all");
    setDateFrom("");
    setDateTo("");
    setDateError("");

    setAppliedFilters({
      academicYear: "all",
      semester: "all",
      courseId: "all",
      dateFrom: "",
      dateTo: "",
    });
    setPage(1);
  };

  // Open Detail Modal
  const handleOpenDetail = async (record) => {
    setSelectedRecord(record);
    if (!record?.attendance_id) return;

    try {
      setDetailLoading(true);
      const detailRes = await getStudentAttendanceDetail(record.attendance_id);
      if (detailRes?.success && detailRes.data) {
        setSelectedRecord(detailRes.data);
      }
    } catch {
      // Fallback to row data already present
    } finally {
      setDetailLoading(false);
    }
  };

  // Profile data resolution
  const displayName = profile?.name || loggedInUser?.name || "Student";
  const enrollmentNo = profile?.enrollment_no || loggedInUser?.enrollment_no || "N/A";
  const departmentName = profile?.department?.department_name || "Computer Science";
  const semesterText = profile?.semester
    ? `Semester ${profile.semester}`
    : profile?.academic_year
    ? `Term ${profile.academic_year}`
    : "Active Term";

  // Encouragement Message Calculation
  const attendancePct = Number(summary.attendance_percentage || 0);
  const getEncouragement = () => {
    if (attendancePct >= 90) {
      return {
        title: "Good Job!",
        message: "Your attendance is above 90%. Keep it up!",
        colorClass: "encourage-high",
      };
    }
    if (attendancePct >= 75) {
      return {
        title: "On Track!",
        message: `Your attendance is ${attendancePct}%. Aim for 90% to maintain excellence!`,
        colorClass: "encourage-good",
      };
    }
    return {
      title: "Attention Required",
      message: `Your attendance is ${attendancePct}%. Maintain at least 75% to remain eligible for examinations.`,
      colorClass: "encourage-low",
    };
  };

  const encouragement = getEncouragement();

  // SVG Donut Chart Calculation
  const presentCount = summary.present_sessions || 0;
  const absentCount = summary.absent_sessions || 0;
  const lateCount = summary.late_sessions || 0;
  const chartTotal = presentCount + absentCount + lateCount;

  // Donut geometry
  const radius = 62;
  const strokeWidth = 14;
  const circumference = 2 * Math.PI * radius;

  const presentRatio = chartTotal > 0 ? presentCount / chartTotal : 0;
  const absentRatio = chartTotal > 0 ? absentCount / chartTotal : 0;
  const lateRatio = chartTotal > 0 ? lateCount / chartTotal : 0;

  const presentStroke = presentRatio * circumference;
  const absentStroke = absentRatio * circumference;
  const lateStroke = lateRatio * circumference;

  const presentOffset = 0;
  const absentOffset = -presentStroke;
  const lateOffset = -(presentStroke + absentStroke);

  return (
    <div className="attendance-history-page">
      {/* ========================================================
          1. ATTENDANCE HISTORY BANNER
      ======================================================== */}
      <section className="attendance-banner-card" aria-label="Attendance History Banner">
        <img
          src="/image/student_timetable_card.png"
          alt=""
          className="attendance-banner-bg-img"
          aria-hidden="true"
        />

        <div className="attendance-banner-content">
          <div className="attendance-banner-left">
            <div className="attendance-banner-icon-box">
              <FontAwesomeIcon icon={faCalendarDays} className="banner-cal-icon" />
            </div>

            <div className="attendance-banner-text">
              <h1 className="attendance-banner-title">Attendance History</h1>
              <p className="attendance-banner-subtitle">
                View your complete attendance record for all courses and sessions.
              </p>
            </div>
          </div>

          <div className="attendance-banner-right">
            <div className="student-profile-badge-card">
              <div className="student-badge-avatar">
                {profile?.photo_url ? (
                  <img
                    src={profile.photo_url}
                    alt={displayName}
                    className="student-badge-avatar-img"
                  />
                ) : (
                  <div className="student-badge-avatar-illustration">
                    <svg viewBox="0 0 64 64" fill="none" className="student-avatar-svg">
                      <circle cx="32" cy="32" r="30" fill="#e0f2fe" />
                      <circle cx="32" cy="24" r="12" fill="#0284c7" />
                      <path
                        d="M14 52C14 42.0589 22.0589 34 32 34C41.9411 34 50 42.0589 50 52"
                        stroke="#0284c7"
                        strokeWidth="5"
                        strokeLinecap="round"
                      />
                    </svg>
                  </div>
                )}
              </div>

              <div className="student-badge-info">
                <strong className="student-badge-name">{displayName}</strong>
                <span className="student-badge-meta">{enrollmentNo}</span>
                <span className="student-badge-meta">{departmentName}</span>
                <span className="student-badge-meta semester-tag">{semesterText}</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ========================================================
          2. SUMMARY CARDS
      ======================================================== */}
      <section className="attendance-summary-grid" aria-label="Attendance Summary Metrics">
        {/* Card 1: Overall Attendance */}
        <div className="summary-metric-card">
          <div className="metric-icon-bubble bubble-green">
            <FontAwesomeIcon icon={faCheck} />
          </div>
          <div className="metric-details">
            <span className="metric-label">Overall Attendance</span>
            <div className="metric-value-row">
              <strong className="metric-value">
                {summaryLoading ? "--" : `${attendancePct}%`}
              </strong>
            </div>
            <span className="metric-subtext">
              {summaryLoading
                ? "Loading records..."
                : `${summary.present_sessions || 0} / ${
                    summary.total_sessions || 0
                  } classes attended`}
            </span>
          </div>
        </div>

        {/* Card 2: Present Days */}
        <div className="summary-metric-card">
          <div className="metric-icon-bubble bubble-blue">
            <FontAwesomeIcon icon={faCalendarDays} />
          </div>
          <div className="metric-details">
            <span className="metric-label">Present Days</span>
            <strong className="metric-value">
              {summaryLoading ? "--" : summary.present_days ?? summary.present_sessions ?? 0}
            </strong>
            <span className="metric-subtext">
              {summaryLoading
                ? "Loading records..."
                : `out of ${summary.total_days ?? summary.total_sessions ?? 0} total days`}
            </span>
          </div>
        </div>

        {/* Card 3: Absent Days */}
        <div className="summary-metric-card">
          <div className="metric-icon-bubble bubble-red">
            <FontAwesomeIcon icon={faXmark} />
          </div>
          <div className="metric-details">
            <span className="metric-label">Absent Days</span>
            <strong className="metric-value">
              {summaryLoading ? "--" : summary.absent_days ?? summary.absent_sessions ?? 0}
            </strong>
            <span className="metric-subtext">
              {summaryLoading
                ? "Loading records..."
                : `out of ${summary.total_days ?? summary.total_sessions ?? 0} total days`}
            </span>
          </div>
        </div>

        {/* Card 4: Late Days */}
        <div className="summary-metric-card">
          <div className="metric-icon-bubble bubble-purple">
            <FontAwesomeIcon icon={faClock} />
          </div>
          <div className="metric-details">
            <span className="metric-label">Late Days</span>
            <strong className="metric-value">
              {summaryLoading ? "--" : summary.late_days ?? summary.late_sessions ?? 0}
            </strong>
            <span className="metric-subtext">
              {summaryLoading
                ? "Loading records..."
                : `out of ${summary.total_days ?? summary.total_sessions ?? 0} total days`}
            </span>
          </div>
        </div>
      </section>

      {/* ========================================================
          3. HORIZONTAL FILTERS PANEL
      ======================================================== */}
      <section className="attendance-filter-panel" aria-label="Attendance Filters">
        <form className="attendance-filter-form" onSubmit={handleApplyFilters}>
          {/* Academic Year */}
          <div className="filter-group">
            <label htmlFor={academicYearId} className="filter-label">Academic Year</label>
            <select
              id={academicYearId}
              className="filter-select"
              value={academicYear}
              onChange={(e) => setAcademicYear(e.target.value)}
            >
              <option value="all">All Academic Years</option>
              {filterOptions.academic_years.map((ay) => (
                <option key={ay} value={ay}>
                  {ay}
                </option>
              ))}
            </select>
          </div>

          {/* Semester */}
          <div className="filter-group">
            <label htmlFor={semesterId} className="filter-label">Semester</label>
            <select
              id={semesterId}
              className="filter-select"
              value={semester}
              onChange={(e) => setSemester(e.target.value)}
            >
              <option value="all">All Semesters</option>
              {filterOptions.semesters.map((sem) => (
                <option key={sem} value={sem}>
                  Semester {sem}
                </option>
              ))}
            </select>
          </div>

          {/* Course */}
          <div className="filter-group">
            <label htmlFor={courseIdInputId} className="filter-label">Course</label>
            <select
              id={courseIdInputId}
              className="filter-select"
              value={courseId}
              onChange={(e) => setCourseId(e.target.value)}
            >
              <option value="all">All Courses</option>
              {filterOptions.courses.map((c) => (
                <option key={c.course_id} value={c.course_id}>
                  {c.course_code} - {c.course_name}
                </option>
              ))}
            </select>
          </div>

          {/* Date Range */}
          <div className="filter-group date-range-group">
            <label htmlFor={dateFromId} className="filter-label">Date Range</label>
            <div className="date-inputs-wrapper">
              <input
                id={dateFromId}
                type="date"
                className="filter-date-input"
                value={dateFrom}
                onChange={(e) => {
                  setDateFrom(e.target.value);
                  setDateError("");
                }}
                aria-label="Start date"
              />
              <span className="date-range-sep">to</span>
              <input
                id={dateToId}
                type="date"
                className="filter-date-input"
                value={dateTo}
                onChange={(e) => {
                  setDateTo(e.target.value);
                  setDateError("");
                }}
                aria-label="End date"
              />
            </div>
          </div>

          {/* Buttons */}
          <div className="filter-actions-group">
            <button type="submit" className="btn-filter-apply">
              <FontAwesomeIcon icon={faFilter} className="btn-icon" />
              <span>Apply Filter</span>
            </button>

            <button
              type="button"
              className="btn-filter-reset"
              onClick={handleResetFilters}
            >
              <FontAwesomeIcon icon={faRotateRight} className="btn-icon" />
              <span>Reset</span>
            </button>
          </div>
        </form>

        {dateError && (
          <div className="filter-date-error-row" role="alert">
            <small>{dateError}</small>
          </div>
        )}
      </section>

      {/* ========================================================
          4. MAIN 2-COLUMN LAYOUT: HISTORY TABLE + SIDEBAR
      ======================================================== */}
      <div className="attendance-history-layout">
        {/* Left Column: Attendance History Table */}
        <div className="attendance-history-table-column">
          <div className="history-table-card">
            <div className="history-table-header">
              <div className="history-header-title">
                <FontAwesomeIcon
                  icon={faCalendarDays}
                  className="history-header-icon"
                />
                <h2>Attendance History</h2>
              </div>
            </div>

            <div className="history-table-wrapper">
              {tableLoading ? (
                <div className="table-state-box">
                  <PageState
                    title="Loading attendance records"
                    message="Fetching your attendance records from the server..."
                  />
                </div>
              ) : error ? (
                <div className="table-state-box">
                  <PageState
                    title="Unable to load attendance records"
                    message={error}
                  />
                </div>
              ) : attendanceRecords.length === 0 ? (
                <div className="table-state-box">
                  <PageState
                    title="No Attendance Records Found"
                    message="No attendance sessions match the current filter selection."
                  />
                </div>
              ) : (
                <table className="attendance-custom-table" aria-label="Attendance Records Table">
                  <thead>
                    <tr>
                      <th scope="col">Date</th>
                      <th scope="col">Course Code</th>
                      <th scope="col">Course Title</th>
                      <th scope="col">Session</th>
                      <th scope="col">Status</th>
                      <th scope="col">Attendance Time</th>
                      <th scope="col">Remarks</th>
                      <th scope="col" className="col-action">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {attendanceRecords.map((record) => {
                      const isPresent = record.status === "PRESENT";
                      const isAbsent = record.status === "ABSENT";
                      const isLate = record.status === "LATE";

                      const statusBadgeClass = isPresent
                        ? "badge-present"
                        : isAbsent
                        ? "badge-absent"
                        : isLate
                        ? "badge-late"
                        : "badge-default";

                      const statusIcon = isPresent
                        ? faCheck
                        : isAbsent
                        ? faXmark
                        : isLate
                        ? faClock
                        : null;

                      return (
                        <tr key={record.attendance_id || record.session_id}>
                          <td className="col-date">
                            {formatDisplayDate(record.session_date)}
                          </td>
                          <td className="col-code">
                            <strong>{record.course_code || "-"}</strong>
                          </td>
                          <td className="col-title">
                            {record.course_name || "-"}
                          </td>
                          <td className="col-session">
                            <span className="session-label">
                              {record.session || record.session_name || "Regular"}
                            </span>
                          </td>
                          <td className="col-status">
                            <span className={`status-pill ${statusBadgeClass}`}>
                              {statusIcon && (
                                <FontAwesomeIcon
                                  icon={statusIcon}
                                  className="status-pill-icon"
                                />
                              )}
                              <span>
                                {record.status
                                  ? record.status.charAt(0) +
                                    record.status.slice(1).toLowerCase()
                                  : "-"}
                              </span>
                            </span>
                          </td>
                          <td className="col-time">
                            {record.attendance_time || "-"}
                          </td>
                          <td className="col-remarks">
                            {record.remarks || "-"}
                          </td>
                          <td className="col-action">
                            <button
                              type="button"
                              className="action-icon-btn"
                              onClick={() => handleOpenDetail(record)}
                              title="View session details"
                              aria-label={`View details for ${
                                record.course_name || "session"
                              } on ${formatDisplayDate(record.session_date)}`}
                            >
                              <FontAwesomeIcon icon={faChevronRight} />
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>

            {/* Pagination Controls */}
            {!tableLoading && !error && totalRecords > 0 && (
              <div
                className="history-pagination-bar"
                aria-label="Attendance history pagination"
              >
                <span className="pagination-info-text">
                  Showing {(page - 1) * PAGE_SIZE + 1} &ndash;{" "}
                  {Math.min(page * PAGE_SIZE, totalRecords)} of {totalRecords}{" "}
                  records
                </span>

                <div className="pagination-pages-group">
                  <button
                    type="button"
                    className="pagination-nav-btn"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => Math.max(p - 1, 1))}
                    aria-label="Previous page"
                  >
                    <FontAwesomeIcon icon={faChevronLeft} />
                  </button>

                  {Array.from({ length: totalPages }, (_, i) => i + 1)
                    .filter((p) => {
                      // Keep active page and adjacent pages
                      return (
                        p === 1 ||
                        p === totalPages ||
                        (p >= page - 2 && p <= page + 2)
                      );
                    })
                    .map((p, index, filteredArray) => {
                      const prevPage = filteredArray[index - 1];
                      const showEllipsis = prevPage && p - prevPage > 1;

                      return (
                        <span key={p} className="pagination-btn-wrapper">
                          {showEllipsis && (
                            <span className="pagination-ellipsis">...</span>
                          )}
                          <button
                            type="button"
                            className={`pagination-num-btn ${
                              p === page ? "num-btn-active" : ""
                            }`}
                            onClick={() => setPage(p)}
                            aria-current={p === page ? "page" : undefined}
                          >
                            {p}
                          </button>
                        </span>
                      );
                    })}

                  <button
                    type="button"
                    className="pagination-nav-btn"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => Math.min(p + 1, totalPages))}
                    aria-label="Next page"
                  >
                    <FontAwesomeIcon icon={faChevronRight} />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Attendance Overview & Subject-wise */}
        <aside className="attendance-history-sidebar-column">
          {/* Card 1: Attendance Overview Donut Chart */}
          <div className="sidebar-widget-card">
            <h3 className="sidebar-widget-title">Attendance Overview</h3>

            <div className="overview-chart-container">
              <div
                className="overview-donut-wrapper"
                role="img"
                aria-label={`Attendance distribution: Present ${presentCount}, Absent ${absentCount}, Late ${lateCount}, Overall attendance ${attendancePct}%`}
              >
                <svg
                  viewBox="0 0 160 160"
                  className="overview-donut-svg"
                  aria-hidden="true"
                >
                  {/* Background Track */}
                  <circle
                    cx="80"
                    cy="80"
                    r={radius}
                    fill="transparent"
                    stroke="#e2e8f0"
                    strokeWidth={strokeWidth}
                  />

                  {chartTotal > 0 && (
                    <>
                      {/* Present segment (Green) */}
                      {presentStroke > 0 && (
                        <circle
                          cx="80"
                          cy="80"
                          r={radius}
                          fill="transparent"
                          stroke="#10b981"
                          strokeWidth={strokeWidth}
                          strokeDasharray={`${presentStroke} ${circumference}`}
                          strokeDashoffset={presentOffset}
                          strokeLinecap="round"
                          transform="rotate(-90 80 80)"
                        />
                      )}

                      {/* Absent segment (Red) */}
                      {absentStroke > 0 && (
                        <circle
                          cx="80"
                          cy="80"
                          r={radius}
                          fill="transparent"
                          stroke="#ef4444"
                          strokeWidth={strokeWidth}
                          strokeDasharray={`${absentStroke} ${circumference}`}
                          strokeDashoffset={absentOffset}
                          strokeLinecap="round"
                          transform="rotate(-90 80 80)"
                        />
                      )}

                      {/* Late segment (Amber) */}
                      {lateStroke > 0 && (
                        <circle
                          cx="80"
                          cy="80"
                          r={radius}
                          fill="transparent"
                          stroke="#f59e0b"
                          strokeWidth={strokeWidth}
                          strokeDasharray={`${lateStroke} ${circumference}`}
                          strokeDashoffset={lateOffset}
                          strokeLinecap="round"
                          transform="rotate(-90 80 80)"
                        />
                      )}
                    </>
                  )}
                </svg>

                <div className="overview-donut-center">
                  <strong className="donut-center-pct">
                    {summaryLoading ? "--" : `${attendancePct}%`}
                  </strong>
                  <span className="donut-center-label">Overall</span>
                </div>
              </div>

              {/* Overview Legend */}
              <div className="overview-legend">
                <div className="legend-row">
                  <div className="legend-label-col">
                    <span className="legend-dot dot-present" />
                    <span>Present</span>
                  </div>
                  <strong className="legend-val">{presentCount}</strong>
                </div>

                <div className="legend-row">
                  <div className="legend-label-col">
                    <span className="legend-dot dot-absent" />
                    <span>Absent</span>
                  </div>
                  <strong className="legend-val">{absentCount}</strong>
                </div>

                <div className="legend-row">
                  <div className="legend-label-col">
                    <span className="legend-dot dot-late" />
                    <span>Late</span>
                  </div>
                  <strong className="legend-val">{lateCount}</strong>
                </div>
              </div>
            </div>
          </div>

          {/* Card 2: Subject-wise Attendance */}
          <div className="sidebar-widget-card">
            <div className="sidebar-widget-header">
              <h3 className="sidebar-widget-title">Subject-wise Attendance</h3>
              <Link to="/student/reports" className="sidebar-widget-link">
                View All
              </Link>
            </div>

            <div className="subject-attendance-list">
              {courseSummaries.length === 0 ? (
                <div className="subject-empty-state">
                  <span>No course attendance data available.</span>
                </div>
              ) : (
                courseSummaries.slice(0, 5).map((course) => {
                  const pct = Number(course.attendance_percentage || 0);
                  const isHealthy = pct >= 75;
                  const progressColor = isHealthy ? "#059669" : "#d97706";

                  return (
                    <div
                      key={course.offering_id || course.course_code}
                      className="subject-item-box"
                    >
                      <div className="subject-item-row-top">
                        <span className="subject-item-name" title={course.course_name}>
                          {course.course_name}
                        </span>
                        <span className="subject-item-pct">{pct}%</span>
                      </div>

                      <div className="subject-progress-track">
                        <div
                          className="subject-progress-fill"
                          style={{
                            width: `${Math.min(pct, 100)}%`,
                            backgroundColor: progressColor,
                          }}
                        />
                      </div>

                      <div className="subject-item-meta-row">
                        <span className="subject-code-tag">{course.course_code}</span>
                        <span className="subject-fraction-text">
                          {course.present_sessions} / {course.total_sessions}
                        </span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Card 3: Attendance Encouragement Banner */}
          <div className={`sidebar-encouragement-card ${encouragement.colorClass}`}>
            <div className="encouragement-icon-box">
              <FontAwesomeIcon icon={faLightbulb} />
            </div>
            <div className="encouragement-text-box">
              <strong className="encouragement-title">
                {encouragement.title}
              </strong>
              <p className="encouragement-desc">
                {encouragement.message}
              </p>
            </div>
          </div>
        </aside>
      </div>

      {/* ========================================================
          5. SESSION & ATTENDANCE DETAIL MODAL
      ======================================================== */}
      {selectedRecord && (
        <div
          className="attendance-modal-backdrop"
          onClick={() => setSelectedRecord(null)}
          role="dialog"
          aria-modal="true"
          aria-labelledby="attendance-modal-title"
        >
          <div
            className="attendance-modal-card"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="attendance-modal-header">
              <div className="modal-title-left">
                <span className="modal-course-badge">
                  {selectedRecord.course_code || "COURSE"}
                </span>
                <h3 id="attendance-modal-title" className="modal-title-text">
                  {selectedRecord.course_name || "Attendance Record Details"}
                </h3>
              </div>

              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setSelectedRecord(null)}
                aria-label="Close details"
              >
                <FontAwesomeIcon icon={faXmark} />
              </button>
            </div>

            <div className="attendance-modal-body">
              {detailLoading && (
                <div className="modal-loading-indicator">
                  <span>Refreshing details...</span>
                </div>
              )}

              {/* Status Header inside modal */}
              <div className="modal-status-banner">
                <span
                  className={`status-pill ${
                    selectedRecord.status === "PRESENT"
                      ? "badge-present"
                      : selectedRecord.status === "ABSENT"
                      ? "badge-absent"
                      : "badge-late"
                  }`}
                >
                  <FontAwesomeIcon
                    icon={
                      selectedRecord.status === "PRESENT"
                        ? faCheck
                        : selectedRecord.status === "ABSENT"
                        ? faXmark
                        : faClock
                    }
                    className="status-pill-icon"
                  />
                  <span>
                    Status:{" "}
                    {selectedRecord.status
                      ? selectedRecord.status.charAt(0) +
                        selectedRecord.status.slice(1).toLowerCase()
                      : "Unknown"}
                  </span>
                </span>
              </div>

              <div className="modal-info-grid">
                <div className="modal-info-item">
                  <div className="modal-item-icon">
                    <FontAwesomeIcon icon={faCalendarDays} />
                  </div>
                  <div className="modal-item-content">
                    <span className="modal-item-label">Date & Session</span>
                    <strong className="modal-item-value">
                      {formatDisplayDate(selectedRecord.session_date)} (
                      {selectedRecord.session || selectedRecord.session_name || "Regular"})
                    </strong>
                  </div>
                </div>

                <div className="modal-info-item">
                  <div className="modal-item-icon">
                    <FontAwesomeIcon icon={faClock} />
                  </div>
                  <div className="modal-item-content">
                    <span className="modal-item-label">Scheduled Time</span>
                    <strong className="modal-item-value">
                      {selectedRecord.session_timing ||
                        (selectedRecord.start_time
                          ? `${selectedRecord.start_time} - ${
                              selectedRecord.end_time || ""
                            }`
                          : "Scheduled Slot")}
                    </strong>
                  </div>
                </div>

                <div className="modal-info-item">
                  <div className="modal-item-icon">
                    <FontAwesomeIcon icon={faIdBadge} />
                  </div>
                  <div className="modal-item-content">
                    <span className="modal-item-label">Check-in Time</span>
                    <strong className="modal-item-value">
                      {selectedRecord.attendance_time || "Not Recorded (Absent)"}
                    </strong>
                  </div>
                </div>

                <div className="modal-info-item">
                  <div className="modal-item-icon">
                    <FontAwesomeIcon icon={faDoorOpen} />
                  </div>
                  <div className="modal-item-content">
                    <span className="modal-item-label">Classroom / Room</span>
                    <strong className="modal-item-value">
                      {selectedRecord.room || "Room Assigned"}
                    </strong>
                  </div>
                </div>

                <div className="modal-info-item">
                  <div className="modal-item-icon">
                    <FontAwesomeIcon icon={faUser} />
                  </div>
                  <div className="modal-item-content">
                    <span className="modal-item-label">Faculty In-Charge</span>
                    <strong className="modal-item-value">
                      {selectedRecord.faculty_name || "Faculty Assigned"}
                    </strong>
                  </div>
                </div>

                <div className="modal-info-item">
                  <div className="modal-item-icon">
                    <FontAwesomeIcon icon={faGraduationCap} />
                  </div>
                  <div className="modal-item-content">
                    <span className="modal-item-label">Academic Term</span>
                    <strong className="modal-item-value">
                      Semester {selectedRecord.semester || profile?.semester || "-"} (
                      {selectedRecord.academic_year || profile?.academic_year || "-"})
                    </strong>
                  </div>
                </div>
              </div>

              {/* Remarks / Verification Note */}
              <div className="modal-remarks-box">
                <span className="modal-remarks-label">Verification & Remarks</span>
                <p className="modal-remarks-text">
                  {selectedRecord.remarks ||
                    (selectedRecord.status === "PRESENT"
                      ? "Attendance verified through facial recognition system."
                      : selectedRecord.status === "LATE"
                      ? "Arrived after class session commenced."
                      : "Student marked absent for this scheduled class session.")}
                </p>
                {selectedRecord.confidence_score && (
                  <small className="modal-confidence-text">
                    Biometric confidence: {(selectedRecord.confidence_score * 100).toFixed(1)}%
                  </small>
                )}
              </div>
            </div>

            <div className="attendance-modal-footer">
              <button
                type="button"
                className="modal-btn-close-action"
                onClick={() => setSelectedRecord(null)}
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

export default AttendanceHistory;
