import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faChartColumn,
  faCalendarDays,
  faGraduationCap,
  faBookOpen,
  faAward,
  faClock,
  faTriangleExclamation,
  faLightbulb,
  faCheck,
  faEye,
  faDownload,
  faClockRotateLeft,
  faArrowLeft,
  faXmark,
  faUserTie,
  faDoorOpen,
  faCircleInfo,
  faBars,
} from "@fortawesome/free-solid-svg-icons";

import useAuth from "../../hooks/useAuth";
import {
  getStudentAttendanceSummary,
  exportStudentAttendanceReport,
} from "../../services/attendanceService";
import { getStudentProfile } from "../../services/studentService";
import PageState from "../../components/PageState";
import "./Reports.css";

// Authoritative distinct color palette for subjects
const SUBJECT_COLORS = [
  "#3b82f6", // 0: Blue (e.g., Computer Networks / Data Structures)
  "#10b981", // 1: Emerald Green (e.g., Internet of Things)
  "#f59e0b", // 2: Amber (e.g., Modeling & Simulation)
  "#ef4444", // 3: Coral Red (e.g., Natural Language Processing)
  "#8b5cf6", // 4: Purple (e.g., Information Security and IPR)
  "#06b6d4", // 5: Cyan (e.g., Blockchain Technology)
  "#ec4899", // 6: Pink (e.g., Privacy & Security in Social Media)
  "#6366f1", // 7: Indigo (e.g., Advanced Machine Learning)
  "#14b8a6", // 8: Teal (e.g., Infrastructure Systems Planning)
  "#f97316", // 9: Orange (e.g., Cyber Security)
];

function getStatusBadge(course) {
  const total = Number(course?.total_sessions ?? course?.eligible_sessions ?? 0);
  if (total === 0) {
    return { label: "No Sessions", className: "badge-pending" };
  }
  const pct = Number(course?.attendance_percentage ?? 0);
  if (pct >= 90) {
    return { label: "Excellent", className: "badge-excellent" };
  }
  if (pct >= 75) {
    return { label: "Good", className: "badge-good" };
  }
  return { label: "Needs Attention", className: "badge-attention" };
}

function truncateText(str, maxLen = 32) {
  if (!str) return "";
  return str.length > maxLen ? `${str.slice(0, maxLen - 1)}…` : str;
}

function StudentReports() {
  const navigate = useNavigate();
  const auth = useAuth();
  const loggedInUser = auth?.user;

  // Student Profile
  const [profile, setProfile] = useState(null);

  // Term Filters
  const [academicYear, setAcademicYear] = useState("all");
  const [semester, setSemester] = useState("all");

  // Filter Options from backend
  const [filterOptions, setFilterOptions] = useState({
    academic_years: [],
    semesters: [],
    courses: [],
  });

  // Summary and Course Data
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
    has_eligible_sessions: false,
  });

  const [courseSummaries, setCourseSummaries] = useState([]);

  // UI States
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedSubject, setSelectedSubject] = useState(null);
  const [exporting, setExporting] = useState(false);
  const [exportSuccess, setExportSuccess] = useState(false);
  const [exportError, setExportError] = useState(null);
  const [hoveredCourseIndex, setHoveredCourseIndex] = useState(null);
  const [chartView, setChartView] = useState("horizontal"); // 'horizontal' (default) or 'vertical'
  const [retryTrigger, setRetryTrigger] = useState(0);

  // Load Student Profile once
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

  // Fetch Subject-wise Summary
  useEffect(() => {
    let active = true;

    async function loadSubjectData() {
      try {
        setLoading(true);
        setError("");

        const params = {};
        if (academicYear !== "all") {
          params.academic_year = academicYear;
        }
        if (semester !== "all") {
          params.semester = semester;
        }

        const res = await getStudentAttendanceSummary(params);
        if (!active) return;

        if (res?.success) {
          if (res.overall) {
            setSummary(res.overall);
          }
          if (Array.isArray(res.data)) {
            setCourseSummaries(res.data);
          } else {
            setCourseSummaries([]);
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
        } else {
          setError(res?.message || "Failed to load attendance report.");
        }
      } catch (err) {
        if (!active) return;
        if (err?.response?.status === 401) {
          setError("Your session has expired. Please log in again.");
        } else if (err?.response?.status === 403) {
          setError("Student authorization is required to view this report.");
        } else {
          setError(
            err?.response?.data?.message ||
              "Unable to load subject-wise attendance report."
          );
        }
        setCourseSummaries([]);
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadSubjectData();

    return () => {
      active = false;
    };
  }, [academicYear, semester, retryTrigger]);

  // Derived session metrics and authoritative attendance rankings
  const {
    totalEligibleSessions,
    totalEnrolledSubjects,
    hasAnyEligibleSessions,
    highestSubject,
    highestPct,
    lowestSubject,
    lowestPct,
  } = useMemo(() => {
    if (!courseSummaries || courseSummaries.length === 0) {
      return {
        totalEligibleSessions: 0,
        totalEnrolledSubjects: 0,
        hasAnyEligibleSessions: false,
        highestSubject: null,
        highestPct: "N/A",
        lowestSubject: null,
        lowestPct: "N/A",
      };
    }

    const totalEligible = courseSummaries.reduce(
      (sum, c) => sum + (c.total_sessions || c.eligible_sessions || 0),
      0
    );

    const withSessions = courseSummaries.filter(
      (c) => (c.total_sessions || c.eligible_sessions || 0) > 0
    );

    if (withSessions.length === 0) {
      return {
        totalEligibleSessions: 0,
        totalEnrolledSubjects: courseSummaries.length,
        hasAnyEligibleSessions: false,
        highestSubject: null,
        highestPct: "N/A",
        lowestSubject: null,
        lowestPct: "N/A",
      };
    }

    let highest = withSessions[0];
    let lowest = withSessions[0];

    for (const c of withSessions) {
      const cPct = Number(c.attendance_percentage ?? 0);
      const hPct = Number(highest.attendance_percentage ?? 0);
      const lPct = Number(lowest.attendance_percentage ?? 0);
      if (cPct > hPct) highest = c;
      if (cPct < lPct) lowest = c;
    }

    return {
      totalEligibleSessions: totalEligible,
      totalEnrolledSubjects: courseSummaries.length,
      hasAnyEligibleSessions: true,
      highestSubject: highest,
      highestPct: `${highest.attendance_percentage}%`,
      lowestSubject: lowest,
      lowestPct: `${lowest.attendance_percentage}%`,
    };
  }, [courseSummaries]);

  // Overall Attendance Percentage (only if eligible sessions exist)
  const overallPct = hasAnyEligibleSessions
    ? Number(summary.attendance_percentage || 0)
    : null;

  // Dynamic Term display
  const displayAcademicYear = useMemo(() => {
    if (academicYear !== "all") return academicYear;
    if (courseSummaries.length > 0 && courseSummaries[0].academic_year) {
      return courseSummaries[0].academic_year;
    }
    if (filterOptions.academic_years.length > 0) {
      return filterOptions.academic_years[0];
    }
    return profile?.academic_year || "2026-2027";
  }, [academicYear, courseSummaries, filterOptions, profile]);

  const displaySemester = useMemo(() => {
    if (semester !== "all") {
      return typeof semester === "number" ? `Semester ${semester}` : semester;
    }
    if (courseSummaries.length > 0 && courseSummaries[0].semester) {
      const s = courseSummaries[0].semester;
      return typeof s === "number" ? `Semester ${s}` : s;
    }
    if (filterOptions.semesters.length > 0) {
      const s = filterOptions.semesters[0];
      return typeof s === "number" ? `Semester ${s}` : s;
    }
    return profile?.semester ? `Semester ${profile.semester}` : "Semester 7";
  }, [semester, courseSummaries, filterOptions, profile]);

  // Donut Geometry calculation
  const donutSlices = useMemo(() => {
    if (!courseSummaries || courseSummaries.length === 0 || !hasAnyEligibleSessions) {
      return [];
    }

    const radius = 67.5;
    const circumference = 2 * Math.PI * radius; // ~424.115

    const eligibleCourses = courseSummaries.filter(
      (c) => (c.total_sessions || c.eligible_sessions || 0) > 0
    );
    if (eligibleCourses.length === 0) return [];

    const weights = eligibleCourses.map((c) =>
      Math.max(1, c.present_sessions || c.attendance_percentage || 1)
    );
    const totalWeight = weights.reduce((acc, w) => acc + w, 0);

    let accumulatedLength = 0;
    return eligibleCourses.map((c, i) => {
      const fraction = weights[i] / totalWeight;
      const arcLength = fraction * circumference;
      const gap = eligibleCourses.length > 1 ? 2.5 : 0;
      const strokeLength = Math.max(1, arcLength - gap);
      const strokeDasharray = `${strokeLength} ${circumference - strokeLength}`;
      const strokeDashoffset = -accumulatedLength - circumference * 0.25;
      accumulatedLength += arcLength;

      const color = SUBJECT_COLORS[i % SUBJECT_COLORS.length];
      return {
        course: c,
        color,
        strokeDasharray,
        strokeDashoffset,
      };
    });
  }, [courseSummaries, hasAnyEligibleSessions]);

  // Handle Download Report (Genuine Server-Generated PDF)
  const handleDownloadReport = async () => {
    if (exporting) return;
    setExporting(true);
    setExportSuccess(false);
    setExportError(null);
    try {
      const params = {
        format: "pdf",
      };
      if (academicYear !== "all") params.academic_year = academicYear;
      if (semester !== "all") params.semester = semester;

      const res = await exportStudentAttendanceReport(params);

      const studentId =
        profile?.enrollment_no || loggedInUser?.enrollment_no || "student";
      let filename = `Subject_Attendance_Report_${studentId}.pdf`;

      const disposition =
        res.headers?.["content-disposition"] ||
        res.headers?.get?.("content-disposition");
      if (disposition) {
        const match = disposition.match(/filename\*?=['"]?(?:UTF-\d['"])?([^;\r\n'"]*)['"]?/i);
        if (match && match[1]) {
          filename = match[1];
        }
      }

      const blob = new Blob([res.data], { type: "application/pdf" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      setExportSuccess(true);
      setTimeout(() => setExportSuccess(false), 5000);
    } catch (err) {
      console.error("Failed to export attendance report:", err);
      let errorMsg = "Failed to export subject-wise attendance report. Please try again.";
      if (err?.response?.data instanceof Blob) {
        try {
          const text = await err.response.data.text();
          const json = JSON.parse(text);
          if (json.message) errorMsg = json.message;
        } catch {
          // Fallback
        }
      } else if (err?.response?.data?.message) {
        errorMsg = err.response.data.message;
      }
      setExportError(errorMsg);
      setTimeout(() => setExportError(null), 6000);
    } finally {
      setExporting(false);
    }
  };

  // Full page loading state
  if (loading && courseSummaries.length === 0) {
    return (
      <div className="reports-page-wrapper">
        <PageState
          type="loading"
          title="Loading Subject-wise Report"
          message="Fetching real attendance analytics and subject statistics..."
        />
      </div>
    );
  }

  // Full page error state
  if (error && courseSummaries.length === 0) {
    return (
      <div className="reports-page-wrapper">
        <PageState
          type="error"
          title="Unable to Load Report"
          message={error}
          actionLabel="Try Again"
          onAction={() => setRetryTrigger((prev) => prev + 1)}
        />
      </div>
    );
  }

  // Chart Dimensions & Configuration
  const numCourses = courseSummaries.length;
  // Horizontal Chart layout
  const hRowHeight = 44;
  const hTopMargin = 20;
  const hBottomMargin = 45;
  const hChartHeight = Math.max(260, numCourses * hRowHeight + hTopMargin + hBottomMargin);
  const hChartWidth = 720;
  const hLabelWidth = 240;
  const hPlotRight = 640;
  const hPlotWidth = hPlotRight - hLabelWidth;

  // Vertical Chart layout
  const vChartWidth = 640;
  const vChartHeight = 300;
  const vPlotLeft = 60;
  const vPlotRight = 620;
  const vPlotTop = 30;
  const vPlotBottom = 220;
  const vPlotWidth = vPlotRight - vPlotLeft;
  const vPlotHeight = vPlotBottom - vPlotTop;
  const vSlotWidth = numCourses > 0 ? vPlotWidth / numCourses : vPlotWidth;
  const vBarWidth = Math.min(42, Math.max(20, vSlotWidth * 0.52));

  return (
    <div className="reports-page-wrapper">
      {/* ========================================================
          1. HERO BANNER
      ======================================================== */}
      <section className="reports-banner-card" aria-label="Subject-wise Report Banner">
        <img
          src="/image/student_timetable_card.png"
          alt=""
          className="reports-banner-bg"
          aria-hidden="true"
        />

        <div className="reports-banner-content">
          {/* Banner Left */}
          <div className="reports-banner-left">
            <div className="reports-banner-icon-bubble">
              <FontAwesomeIcon icon={faChartColumn} />
            </div>
            <div className="reports-banner-text">
              <h1 className="reports-banner-title">Subject-wise Report</h1>
              <p className="reports-banner-subtitle">
                View your attendance and performance for each subject.
              </p>
            </div>
          </div>

          {/* Banner Center Illustration */}
          <div className="reports-banner-illustration" aria-hidden="true">
            <svg
              viewBox="0 0 200 130"
              fill="none"
              className="student-study-svg"
            >
              {/* Desk */}
              <rect x="25" y="112" width="150" height="6" rx="3" fill="#cbd5e1" />
              <rect x="35" y="118" width="6" height="12" rx="2" fill="#94a3b8" />
              <rect x="159" y="118" width="6" height="12" rx="2" fill="#94a3b8" />

              {/* Books Stack */}
              <rect x="135" y="104" width="30" height="8" rx="2" fill="#3b82f6" />
              <rect x="138" y="96" width="26" height="8" rx="2" fill="#10b981" />
              <rect x="141" y="88" width="22" height="8" rx="2" fill="#f59e0b" />

              {/* Laptop */}
              <polygon points="70,112 110,112 105,92 75,92" fill="#64748b" />
              <rect x="75" y="80" width="30" height="20" rx="3" fill="#0f172a" />
              <rect x="78" y="83" width="24" height="14" rx="2" fill="#38bdf8" opacity="0.9" />

              {/* Student Figure */}
              <circle cx="58" cy="45" r="14" fill="#fde047" />
              <path
                d="M48 40 C48 30 68 30 68 40 C68 43 65 44 65 44 C65 44 62 36 54 37 C48 38 48 40 48 40 Z"
                fill="#1e293b"
              />
              <path
                d="M44 66 C44 56 72 56 72 66 L70 105 L46 105 Z"
                fill="#2563eb"
              />
              <path
                d="M46 66 L34 85 L42 88 L52 72 Z"
                fill="#1d4ed8"
              />
              <path
                d="M68 66 L82 88 L74 92 L62 72 Z"
                fill="#1d4ed8"
              />
            </svg>
          </div>

          {/* Banner Right Term Badge */}
          <div className="reports-banner-right">
            <div className="term-info-card">
              <div className="term-cal-icon">
                <FontAwesomeIcon icon={faCalendarDays} />
              </div>
              <div className="term-text-group">
                <div className="term-col">
                  <span className="term-label">Academic Year</span>
                  {filterOptions.academic_years.length > 1 ? (
                    <select
                      className="term-select"
                      value={academicYear}
                      onChange={(e) => setAcademicYear(e.target.value)}
                    >
                      <option value="all">All Years</option>
                      {filterOptions.academic_years.map((y) => (
                        <option key={y} value={y}>{y}</option>
                      ))}
                    </select>
                  ) : (
                    <strong className="term-value">{displayAcademicYear}</strong>
                  )}
                </div>
                <div className="term-col">
                  <span className="term-label">Semester</span>
                  {filterOptions.semesters.length > 1 ? (
                    <select
                      className="term-select"
                      value={semester}
                      onChange={(e) => setSemester(e.target.value)}
                    >
                      <option value="all">All Semesters</option>
                      {filterOptions.semesters.map((s) => (
                        <option key={s} value={s}>Semester {s}</option>
                      ))}
                    </select>
                  ) : (
                    <strong className="term-value">{displaySemester}</strong>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Export status notification banners */}
      {exportSuccess && (
        <div className="reports-export-banner banner-success" role="status">
          <FontAwesomeIcon icon={faCheck} className="banner-icon" />
          <span>Official Subject-wise Attendance Report (PDF) successfully downloaded!</span>
        </div>
      )}
      {exportError && (
        <div className="reports-export-banner banner-error" role="alert">
          <FontAwesomeIcon icon={faTriangleExclamation} className="banner-icon" />
          <span>{exportError}</span>
        </div>
      )}

      {/* ========================================================
          2. FOUR SUMMARY CARDS
      ======================================================== */}
      <section className="reports-summary-grid" aria-label="Attendance Summary Cards">
        {/* Card 1: Overall Attendance */}
        <div className="metric-card">
          <div className="metric-icon-wrap icon-wrap-green">
            <FontAwesomeIcon icon={faGraduationCap} />
          </div>
          <div className="metric-info">
            <span className="metric-title">Overall Attendance</span>
            <div className="metric-val-row">
              <strong className="metric-val">
                {hasAnyEligibleSessions ? `${overallPct}%` : "N/A"}
              </strong>
            </div>
            <span className="metric-sub">
              {hasAnyEligibleSessions
                ? `${summary.present_sessions || 0} / ${totalEligibleSessions} classes attended`
                : "0 classes recorded yet"}
            </span>
          </div>
        </div>

        {/* Card 2: Total Subjects */}
        <div className="metric-card">
          <div className="metric-icon-wrap icon-wrap-blue">
            <FontAwesomeIcon icon={faBookOpen} />
          </div>
          <div className="metric-info">
            <span className="metric-title">Total Subjects</span>
            <div className="metric-val-row">
              <strong className="metric-val">{totalEnrolledSubjects}</strong>
            </div>
            <span className="metric-sub">Enrolled subjects</span>
          </div>
        </div>

        {/* Card 3: Highest Attendance */}
        <div className="metric-card">
          <div className="metric-icon-wrap icon-wrap-purple">
            <FontAwesomeIcon icon={faAward} />
          </div>
          <div className="metric-info">
            <span className="metric-title">Highest Attendance</span>
            <div className="metric-val-row">
              <strong
                className="metric-val-subject"
                title={highestSubject?.course_name || "No sessions yet"}
              >
                {highestSubject?.course_name || "No sessions yet"}
              </strong>
            </div>
            <strong className="metric-val-pct pct-purple">
              {hasAnyEligibleSessions ? highestPct : "N/A"}
            </strong>
          </div>
        </div>

        {/* Card 4: Lowest Attendance */}
        <div className="metric-card">
          <div className="metric-icon-wrap icon-wrap-red">
            <FontAwesomeIcon icon={faTriangleExclamation} />
          </div>
          <div className="metric-info">
            <span className="metric-title">Lowest Attendance</span>
            <div className="metric-val-row">
              <strong
                className="metric-val-subject"
                title={lowestSubject?.course_name || "No sessions yet"}
              >
                {lowestSubject?.course_name || "No sessions yet"}
              </strong>
            </div>
            <strong className="metric-val-pct pct-red">
              {hasAnyEligibleSessions ? lowestPct : "N/A"}
            </strong>
          </div>
        </div>
      </section>

      {/* ========================================================
          3. CHARTS ROW (Overview Chart + Donut Distribution)
      ======================================================== */}
      <section className="reports-charts-row" aria-label="Attendance Charts">
        {/* Left Chart: Subject-wise Attendance Overview */}
        <div className="chart-panel overview-chart-panel">
          <div className="chart-header">
            <div className="chart-title-group">
              <h2 className="chart-title">Subject-wise Attendance Overview</h2>
              {hasAnyEligibleSessions && (
                <span className="chart-count-pill">
                  {numCourses} {numCourses === 1 ? "Subject" : "Subjects"}
                </span>
              )}
            </div>

            {hasAnyEligibleSessions && (
              <div className="chart-view-toggle">
                <button
                  type="button"
                  className={`btn-toggle ${chartView === "horizontal" ? "active" : ""}`}
                  onClick={() => setChartView("horizontal")}
                  title="Horizontal Bar View (Recommended for long subject names)"
                >
                  <FontAwesomeIcon icon={faBars} /> Horizontal
                </button>
                <button
                  type="button"
                  className={`btn-toggle ${chartView === "vertical" ? "active" : ""}`}
                  onClick={() => setChartView("vertical")}
                  title="Vertical Column View"
                >
                  <FontAwesomeIcon icon={faChartColumn} /> Vertical
                </button>
              </div>
            )}
          </div>

          <div className="chart-body">
            {/* STATE 1: Empty - No enrolled courses */}
            {courseSummaries.length === 0 ? (
              <div className="chart-empty-state">
                <FontAwesomeIcon icon={faCircleInfo} className="empty-state-icon" />
                <h3 className="empty-state-title">No Enrolled Subjects</h3>
                <p className="empty-state-desc">
                  No registered courses were found for the selected academic year and semester.
                </p>
              </div>
            ) : !hasAnyEligibleSessions ? (
              /* STATE 2: Subjects Enrolled, But No Attendance Sessions Held Yet */
              <div className="chart-no-sessions-state">
                <div className="no-sessions-banner">
                  <div className="no-sessions-icon-wrap">
                    <FontAwesomeIcon icon={faClock} />
                  </div>
                  <div className="no-sessions-text">
                    <h3 className="no-sessions-title">
                      Attendance Statistics Not Yet Available
                    </h3>
                    <p className="no-sessions-desc">
                      You are enrolled in <strong>{numCourses} subjects</strong>, but no closed class attendance
                      sessions have been conducted by faculty yet for <strong>{displaySemester}</strong>.
                      Statistics and comparison bars will be rendered once sessions take place.
                    </p>
                  </div>
                </div>

                {/* Enrolled Subjects List with Pending Sessions status */}
                <div className="enrolled-subjects-preview">
                  <h4 className="preview-heading">Enrolled Curriculum for {displaySemester}</h4>
                  <div className="preview-grid">
                    {courseSummaries.map((c, idx) => {
                      const color = SUBJECT_COLORS[idx % SUBJECT_COLORS.length];
                      return (
                        <div key={c.offering_id || c.course_id || idx} className="preview-subject-card">
                          <div className="preview-color-bar" style={{ backgroundColor: color }} />
                          <div className="preview-card-body">
                            <div className="preview-card-top">
                              <span className="preview-code">{c.course_code}</span>
                              <span className="preview-status-tag">No Sessions Held</span>
                            </div>
                            <strong className="preview-name" title={c.course_name}>
                              {c.course_name}
                            </strong>
                            <div className="preview-meta">
                              <span>Faculty: {c.faculty_name || "Assigned Faculty"}</span>
                              <span>Room: {c.room || "TBD"}</span>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            ) : chartView === "horizontal" ? (
              /* STATE 3A: Horizontal Bar Chart (Handles long names and many subjects cleanly) */
              <div className="svg-horizontal-container">
                <svg
                  viewBox={`0 0 ${hChartWidth} ${hChartHeight}`}
                  className="overview-hbar-svg"
                  preserveAspectRatio="xMidYMid meet"
                >
                  {/* Vertical Gridlines & X-Axis Ticks (0% to 100%) */}
                  {[0, 20, 40, 60, 80, 100].map((tick) => {
                    const x = hLabelWidth + (tick / 100) * hPlotWidth;
                    return (
                      <g key={tick} className="grid-tick-group">
                        <line
                          x1={x}
                          y1={hTopMargin}
                          x2={x}
                          y2={hChartHeight - hBottomMargin}
                          stroke="#e2e8f0"
                          strokeDasharray={tick === 0 ? "none" : "3 3"}
                          strokeWidth="1"
                        />
                        <text
                          x={x}
                          y={hChartHeight - hBottomMargin + 16}
                          textAnchor="middle"
                          className="svg-tick-text"
                        >
                          {tick}%
                        </text>
                      </g>
                    );
                  })}

                  {/* Horizontal Axis Title */}
                  <text
                    x={hLabelWidth + hPlotWidth / 2}
                    y={hChartHeight - 8}
                    textAnchor="middle"
                    className="svg-axis-label"
                  >
                    Attendance Percentage (%)
                  </text>

                  {/* Subject Rows */}
                  {courseSummaries.map((course, idx) => {
                    const rowY = hTopMargin + idx * hRowHeight;
                    const totalSess = Number(course.total_sessions || course.eligible_sessions || 0);
                    const presentSess = Number(course.present_sessions || 0);
                    const hasSessions = totalSess > 0;
                    const pct = hasSessions
                      ? Math.min(100, Math.max(0, Number(course.attendance_percentage || 0)))
                      : 0;

                    const color = SUBJECT_COLORS[idx % SUBJECT_COLORS.length];
                    const barWidthPx = hasSessions ? Math.max(6, (pct / 100) * hPlotWidth) : 0;
                    const isHovered = hoveredCourseIndex === idx;

                    return (
                      <g
                        key={course.offering_id || course.course_id || idx}
                        className={`hbar-row-group ${isHovered ? "row-active" : ""}`}
                        onMouseEnter={() => setHoveredCourseIndex(idx)}
                        onMouseLeave={() => setHoveredCourseIndex(null)}
                        tabIndex="0"
                        role="graphics-symbol"
                        aria-label={`${course.course_name}: ${hasSessions ? `${pct}%` : "No sessions yet"}`}
                      >
                        {/* Row Hover Background */}
                        <rect
                          x="10"
                          y={rowY}
                          width={hChartWidth - 20}
                          height={hRowHeight - 4}
                          rx="6"
                          ry="6"
                          fill={isHovered ? "#f1f5f9" : "transparent"}
                          className="row-bg-rect"
                        />

                        {/* Subject Code Badge */}
                        <rect
                          x="20"
                          y={rowY + 9}
                          width="70"
                          height="20"
                          rx="4"
                          ry="4"
                          fill={isHovered ? "#e0f2fe" : "#f1f5f9"}
                        />
                        <text
                          x="55"
                          y={rowY + 23}
                          textAnchor="middle"
                          className="hbar-code-text"
                          fill={isHovered ? "#0369a1" : "#475569"}
                        >
                          {course.course_code}
                        </text>

                        {/* Subject Name Label (Truncated with full tooltip) */}
                        <text
                          x="100"
                          y={rowY + 23}
                          textAnchor="start"
                          className="hbar-name-text"
                          fill={isHovered ? "#0f172a" : "#1e293b"}
                        >
                          {truncateText(course.course_name, 22)}
                          <title>{course.course_name} ({course.course_code})</title>
                        </text>

                        {/* Plot Area Track (Background Bar) */}
                        <rect
                          x={hLabelWidth}
                          y={rowY + 9}
                          width={hPlotWidth}
                          height="20"
                          rx="5"
                          ry="5"
                          fill="#f8fafc"
                          stroke="#e2e8f0"
                          strokeWidth="1"
                        />

                        {/* Actual Percentage Bar or Inactive Marker */}
                        {hasSessions ? (
                          <>
                            <rect
                              x={hLabelWidth}
                              y={rowY + 9}
                              width={barWidthPx}
                              height="20"
                              rx="5"
                              ry="5"
                              fill={color}
                              className="hbar-fill-rect"
                            />
                            {/* Percentage Text to the right */}
                            <text
                              x={hPlotRight + 12}
                              y={rowY + 24}
                              textAnchor="start"
                              className="hbar-val-text"
                              fill={color}
                            >
                              {pct}%
                            </text>
                          </>
                        ) : (
                          <>
                            <text
                              x={hLabelWidth + 12}
                              y={rowY + 23}
                              textAnchor="start"
                              className="hbar-no-sessions-text"
                            >
                              No sessions conducted yet
                            </text>
                            <text
                              x={hPlotRight + 12}
                              y={rowY + 24}
                              textAnchor="start"
                              className="hbar-na-text"
                            >
                              N/A
                            </text>
                          </>
                        )}

                        <title>
                          {course.course_code}: {course.course_name}
                          {"\n"}
                          {hasSessions
                            ? `Attendance: ${pct}% (${presentSess} / ${totalSess} classes attended)`
                            : "No eligible sessions conducted yet"}
                          {"\n"}
                          Faculty: {course.faculty_name || "Assigned Faculty"}
                        </title>
                      </g>
                    );
                  })}
                </svg>
              </div>
            ) : (
              /* STATE 3B: Vertical Column View (Optional view toggle) */
              <div className="svg-chart-container">
                <svg
                  viewBox={`0 0 ${vChartWidth} ${vChartHeight}`}
                  className="overview-bar-svg"
                  preserveAspectRatio="xMidYMid meet"
                >
                  <text
                    transform="rotate(-90)"
                    x="-125"
                    y="18"
                    textAnchor="middle"
                    className="svg-axis-label"
                  >
                    Attendance Percentage
                  </text>

                  {[0, 20, 40, 60, 80, 100].map((tick) => {
                    const y = vPlotBottom - (tick / 100) * vPlotHeight;
                    return (
                      <g key={tick} className="grid-tick-group">
                        <line
                          x1={vPlotLeft}
                          y1={y}
                          x2={vPlotRight}
                          y2={y}
                          stroke="#e2e8f0"
                          strokeDasharray={tick === 0 ? "none" : "3 3"}
                          strokeWidth="1"
                        />
                        <text
                          x={vPlotLeft - 8}
                          y={y + 4}
                          textAnchor="end"
                          className="svg-tick-text"
                        >
                          {tick}%
                        </text>
                      </g>
                    );
                  })}

                  {courseSummaries.map((course, idx) => {
                    const totalSess = Number(course.total_sessions || course.eligible_sessions || 0);
                    const hasSessions = totalSess > 0;
                    const pct = hasSessions
                      ? Math.min(100, Math.max(0, Number(course.attendance_percentage || 0)))
                      : 0;
                    const bHeight = hasSessions ? Math.max(6, (pct / 100) * vPlotHeight) : 4;
                    const bX = vPlotLeft + idx * vSlotWidth + (vSlotWidth - vBarWidth) / 2;
                    const bY = vPlotBottom - bHeight;
                    const color = SUBJECT_COLORS[idx % SUBJECT_COLORS.length];

                    return (
                      <g
                        key={course.offering_id || course.course_id || idx}
                        className="bar-group"
                        tabIndex="0"
                      >
                        <text
                          x={bX + vBarWidth / 2}
                          y={bY - 8}
                          textAnchor="middle"
                          className="bar-value-text"
                          fill={hasSessions ? color : "#94a3b8"}
                        >
                          {hasSessions ? `${pct}%` : "N/A"}
                        </text>

                        <rect
                          x={bX}
                          y={bY}
                          width={vBarWidth}
                          height={bHeight}
                          rx="5"
                          ry="5"
                          fill={hasSessions ? color : "#e2e8f0"}
                          className="svg-bar-rect"
                        />

                        {/* Abbreviated course code underneath to avoid overlap */}
                        <text
                          x={bX + vBarWidth / 2}
                          y={vPlotBottom + 18}
                          textAnchor="middle"
                          className="bar-sub-label line-1"
                        >
                          {course.course_code}
                          <title>{course.course_name}</title>
                        </text>
                      </g>
                    );
                  })}
                </svg>
              </div>
            )}
          </div>
        </div>

        {/* Right Chart: Subject-wise Attendance Distribution */}
        <div className="chart-panel distribution-chart-panel">
          <div className="chart-header">
            <h2 className="chart-title">Subject-wise Attendance Distribution</h2>
          </div>

          <div className="distribution-body">
            {!hasAnyEligibleSessions ? (
              <div className="distribution-empty-wrap">
                <div className="donut-svg-wrap">
                  <svg viewBox="0 0 200 200" className="donut-svg">
                    <circle
                      cx="100"
                      cy="100"
                      r="67.5"
                      fill="none"
                      stroke="#f1f5f9"
                      strokeWidth="24"
                    />
                    <text x="100" y="96" textAnchor="middle" className="donut-center-num">
                      N/A
                    </text>
                    <text x="100" y="118" textAnchor="middle" className="donut-center-label">
                      No Sessions
                    </text>
                  </svg>
                </div>
                <p className="distribution-pending-notice">
                  Attendance distribution will be calculated once sessions are conducted and marked.
                </p>
              </div>
            ) : (
              <div className="donut-layout">
                {/* Donut SVG */}
                <div className="donut-svg-wrap">
                  <svg
                    viewBox="0 0 200 200"
                    className="donut-svg"
                    role="img"
                    aria-label={`Overall Attendance ${overallPct}%`}
                  >
                    <circle
                      cx="100"
                      cy="100"
                      r="67.5"
                      fill="none"
                      stroke="#f1f5f9"
                      strokeWidth="24"
                    />

                    {donutSlices.map((slice, idx) => (
                      <circle
                        key={idx}
                        cx="100"
                        cy="100"
                        r="67.5"
                        fill="none"
                        stroke={slice.color}
                        strokeWidth="24"
                        strokeDasharray={slice.strokeDasharray}
                        strokeDashoffset={slice.strokeDashoffset}
                        className="donut-segment"
                      />
                    ))}

                    <text
                      x="100"
                      y="96"
                      textAnchor="middle"
                      className="donut-center-num"
                    >
                      {overallPct}%
                    </text>
                    <text
                      x="100"
                      y="118"
                      textAnchor="middle"
                      className="donut-center-label"
                    >
                      Overall
                    </text>
                  </svg>
                </div>

                {/* Donut Legend */}
                <div className="donut-legend-list">
                  {courseSummaries.map((c, i) => {
                    const color = SUBJECT_COLORS[i % SUBJECT_COLORS.length];
                    const hasSessions = Number(c.total_sessions || c.eligible_sessions || 0) > 0;
                    const pct = Number(c.attendance_percentage || 0);
                    return (
                      <div
                        key={c.offering_id || c.course_id || i}
                        className="donut-legend-item"
                        title={`${c.course_name} (${hasSessions ? `${pct}%` : "No sessions"})`}
                      >
                        <span
                          className="legend-dot"
                          style={{ backgroundColor: color }}
                        />
                        <span className="legend-subject-name">
                          {c.course_name}
                        </span>
                        <span className="legend-subject-pct">
                          {hasSessions ? `${pct}%` : "Pending"}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* ========================================================
          4. BOTTOM ROW (Table + Insights & Quick Actions)
      ======================================================== */}
      <section className="reports-bottom-grid" aria-label="Details and Quick Actions">
        {/* Left: Subject-wise Details Table */}
        <div className="table-card">
          <div className="table-card-header">
            <h2 className="table-card-title">Subject-wise Details</h2>
          </div>

          <div className="table-responsive">
            <table className="reports-table">
              <thead>
                <tr>
                  <th style={{ width: "40px" }}>S.</th>
                  <th>Subject Code</th>
                  <th>Subject Name</th>
                  <th>Total Classes</th>
                  <th>Attended</th>
                  <th>Missed</th>
                  <th>Attendance %</th>
                  <th>Status</th>
                  <th style={{ textAlign: "center" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {courseSummaries.length === 0 ? (
                  <tr>
                    <td colSpan="9" className="table-empty-cell">
                      No registered subjects found for this term.
                    </td>
                  </tr>
                ) : (
                  courseSummaries.map((course, idx) => {
                    const badge = getStatusBadge(course);
                    const totalSess = Number(course.total_sessions || course.eligible_sessions || 0);
                    const hasSessions = totalSess > 0;
                    return (
                      <tr
                        key={course.offering_id || course.course_id || idx}
                        className="table-row-hover"
                      >
                        <td>{idx + 1}</td>
                        <td>
                          <button
                            type="button"
                            className="subject-code-link"
                            onClick={() => setSelectedSubject(course)}
                            title={`View details for ${course.course_code}`}
                          >
                            {course.course_code}
                          </button>
                        </td>
                        <td className="subject-name-cell">
                          {course.course_name}
                        </td>
                        <td>{totalSess}</td>
                        <td>{course.present_sessions || 0}</td>
                        <td>{course.absent_sessions || 0}</td>
                        <td className="subject-pct-cell">
                          {hasSessions ? `${course.attendance_percentage || 0}%` : "N/A"}
                        </td>
                        <td>
                          <span className={`status-pill ${badge.className}`}>
                            {badge.label}
                          </span>
                        </td>
                        <td style={{ textAlign: "center" }}>
                          <button
                            type="button"
                            className="btn-action-view"
                            onClick={() => setSelectedSubject(course)}
                          >
                            <FontAwesomeIcon icon={faEye} /> View Details
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          <div className="table-card-footer">
            <span className="footer-range-text">
              Showing 1 – {courseSummaries.length} of {courseSummaries.length} subjects
            </span>
          </div>
        </div>

        {/* Right Stack: Key Insights & Quick Actions */}
        <div className="side-widgets-column">
          {/* Widget 1: Key Insights */}
          <div className="widget-card key-insights-card">
            <div className="widget-header">
              <div className="insight-bulb-icon">
                <FontAwesomeIcon icon={faLightbulb} />
              </div>
              <h3 className="widget-title">Key Insights</h3>
            </div>

            <ul className="insights-list">
              {!hasAnyEligibleSessions ? (
                <>
                  <li className="insight-item">
                    <span className="insight-check">
                      <FontAwesomeIcon icon={faCheck} />
                    </span>
                    <span>
                      You are enrolled in <strong>{totalEnrolledSubjects} subjects</strong> for {displaySemester}.
                    </span>
                  </li>
                  <li className="insight-item">
                    <span className="insight-check">
                      <FontAwesomeIcon icon={faCheck} />
                    </span>
                    <span>
                      Faculty has not conducted or closed any attendance sessions for this term yet.
                    </span>
                  </li>
                  <li className="insight-item">
                    <span className="insight-check">
                      <FontAwesomeIcon icon={faCheck} />
                    </span>
                    <span>
                      Attendance rankings and analytics will update automatically as classes are held.
                    </span>
                  </li>
                </>
              ) : (
                <>
                  <li className="insight-item">
                    <span className="insight-check">
                      <FontAwesomeIcon icon={faCheck} />
                    </span>
                    <span>
                      Your overall attendance is <strong>{overallPct}%</strong>.
                    </span>
                  </li>

                  {highestSubject && (
                    <li className="insight-item">
                      <span className="insight-check">
                        <FontAwesomeIcon icon={faCheck} />
                      </span>
                      <span>
                        Highest attendance in <strong>{highestSubject.course_name}</strong> ({highestPct}).
                      </span>
                    </li>
                  )}

                  {lowestSubject && (
                    <li className="insight-item">
                      <span className="insight-check">
                        <FontAwesomeIcon icon={faCheck} />
                      </span>
                      <span>
                        Lowest attendance in <strong>{lowestSubject.course_name}</strong> ({lowestPct}).
                      </span>
                    </li>
                  )}

                  <li className="insight-item">
                    <span className="insight-check">
                      <FontAwesomeIcon icon={faCheck} />
                    </span>
                    <span>
                      {overallPct >= 90
                        ? "Keep up the good work! Attendance meets all institutional honors requirements."
                        : overallPct >= 75
                        ? "Good standing! Attend upcoming classes to aim for 90%."
                        : "Attendance is below 75% in some subjects. Attend upcoming sessions to meet examination eligibility."}
                    </span>
                  </li>
                </>
              )}
            </ul>
          </div>

          {/* Widget 2: Quick Actions */}
          <div className="widget-card quick-actions-card">
            <div className="widget-header">
              <h3 className="widget-title">Quick Actions</h3>
            </div>

            <div className="quick-actions-btns">
              <button
                type="button"
                className="btn-quick-action"
                onClick={handleDownloadReport}
                disabled={exporting}
              >
                <FontAwesomeIcon icon={faDownload} className="action-btn-icon" />
                <span>
                  {exporting ? "Generating Report..." : "Download Report (PDF)"}
                </span>
              </button>

              <button
                type="button"
                className="btn-quick-action"
                onClick={() => navigate("/student/attendance-history")}
              >
                <FontAwesomeIcon
                  icon={faClockRotateLeft}
                  className="action-btn-icon"
                />
                <span>View Attendance History</span>
              </button>

              <button
                type="button"
                className="btn-quick-action"
                onClick={() => navigate("/student/dashboard")}
              >
                <FontAwesomeIcon
                  icon={faArrowLeft}
                  className="action-btn-icon"
                />
                <span>Back to Dashboard</span>
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* ========================================================
          5. SUBJECT DETAIL MODAL
      ======================================================== */}
      {selectedSubject && (
        <div
          className="modal-backdrop"
          onClick={() => setSelectedSubject(null)}
          role="dialog"
          aria-modal="true"
        >
          <div
            className="modal-content-card"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <div className="modal-title-wrap">
                <h3 className="modal-subject-title">
                  {selectedSubject.course_name}
                </h3>
                <span className="modal-course-badge">
                  {selectedSubject.course_code}
                </span>
              </div>
              <button
                type="button"
                className="btn-modal-close"
                onClick={() => setSelectedSubject(null)}
                aria-label="Close modal"
              >
                <FontAwesomeIcon icon={faXmark} />
              </button>
            </div>

            <div className="modal-body">
              {/* Meta information tags */}
              <div className="modal-meta-grid">
                <div className="modal-meta-item">
                  <FontAwesomeIcon icon={faUserTie} className="meta-icon" />
                  <div>
                    <span className="meta-label">Faculty</span>
                    <strong className="meta-value">
                      {selectedSubject.faculty_name || "Assigned Faculty"}
                    </strong>
                  </div>
                </div>

                <div className="modal-meta-item">
                  <FontAwesomeIcon icon={faDoorOpen} className="meta-icon" />
                  <div>
                    <span className="meta-label">Room</span>
                    <strong className="meta-value">
                      {selectedSubject.room || "Main Lecture Hall"}
                    </strong>
                  </div>
                </div>

                <div className="modal-meta-item">
                  <FontAwesomeIcon icon={faCalendarDays} className="meta-icon" />
                  <div>
                    <span className="meta-label">Semester / Term</span>
                    <strong className="meta-value">
                      {selectedSubject.semester
                        ? `Semester ${selectedSubject.semester}`
                        : "Active Semester"}{" "}
                      ({selectedSubject.academic_year || displayAcademicYear})
                    </strong>
                  </div>
                </div>

                {selectedSubject.credits && (
                  <div className="modal-meta-item">
                    <FontAwesomeIcon icon={faBookOpen} className="meta-icon" />
                    <div>
                      <span className="meta-label">Credits</span>
                      <strong className="meta-value">
                        {selectedSubject.credits} Credits
                      </strong>
                    </div>
                  </div>
                )}
              </div>

              {/* Attendance Breakdown Numbers */}
              <div className="modal-stats-grid">
                <div className="modal-stat-box">
                  <span className="stat-label">Total Classes</span>
                  <strong className="stat-num">
                    {selectedSubject.total_sessions || selectedSubject.eligible_sessions || 0}
                  </strong>
                </div>

                <div className="modal-stat-box">
                  <span className="stat-label">Attended</span>
                  <strong className="stat-num stat-green">
                    {selectedSubject.present_sessions || 0}
                  </strong>
                </div>

                <div className="modal-stat-box">
                  <span className="stat-label">Missed</span>
                  <strong className="stat-num stat-red">
                    {selectedSubject.absent_sessions || 0}
                  </strong>
                </div>

                <div className="modal-stat-box">
                  <span className="stat-label">Late</span>
                  <strong className="stat-num stat-amber">
                    {selectedSubject.late_sessions || 0}
                  </strong>
                </div>
              </div>

              {/* Progress and status */}
              <div className="modal-progress-section">
                <div className="progress-labels">
                  <span className="progress-title">Attendance Ratio</span>
                  <strong className="progress-pct">
                    {(selectedSubject.total_sessions || selectedSubject.eligible_sessions || 0) > 0
                      ? `${selectedSubject.attendance_percentage || 0}%`
                      : "No Sessions Held"}
                  </strong>
                </div>
                <div className="progress-track">
                  <div
                    className="progress-fill"
                    style={{
                      width: `${
                        (selectedSubject.total_sessions || selectedSubject.eligible_sessions || 0) > 0
                          ? Math.min(
                              100,
                              Math.max(0, selectedSubject.attendance_percentage || 0)
                            )
                          : 0
                      }%`,
                    }}
                  />
                </div>
                <div className="modal-status-row">
                  <span
                    className={`status-pill ${
                      getStatusBadge(selectedSubject).className
                    }`}
                  >
                    {getStatusBadge(selectedSubject).label}
                  </span>
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button
                type="button"
                className="btn-modal-history"
                onClick={() => {
                  setSelectedSubject(null);
                  navigate(
                    `/student/attendance-history?course_id=${
                      selectedSubject.course_id || selectedSubject.offering_id
                    }`
                  );
                }}
              >
                <FontAwesomeIcon icon={faClock} /> View Sessions in History
              </button>
              <button
                type="button"
                className="btn-modal-dismiss"
                onClick={() => setSelectedSubject(null)}
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

export default StudentReports;
