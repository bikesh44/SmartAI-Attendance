import { useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  CalendarDays,
  CheckCircle2,
  XCircle,
  BookOpen,
  Calendar,
  Clock,
  Zap,
  BarChart3,
  User as UserIcon,
  ChevronRight,
  GraduationCap,
  TrendingUp,
  TrendingDown,
  Check,
  Circle,
  Target,
  AlertCircle,
} from "lucide-react";

import "./StudentDashboard.css";
import useAuth from "../../hooks/useAuth";
import { getStudentDashboard } from "../../services/studentService";

// Card background images - directly served from public directory for 100% reliable rendering
const bannerCampusImg = "/image/student_banner_campus.jpg";
const cardAttendanceImg = "/image/student_card_attendance.jpg";
const cardAttendedImg = "/image/student_card_attended.jpg";
const cardMissedImg = "/image/student_card_missed.jpg";
const cardCoursesImg = "/image/student_card_courses.jpg";
const cardMotivationImg = "/image/student_card_motivation.jpg";

function getGreeting() {
  const hour = new Date().getHours();
  if (hour >= 5 && hour < 12) {
    return "Good Morning";
  }
  if (hour >= 12 && hour < 17) {
    return "Good Afternoon";
  }
  return "Good Evening";
}

function getFirstName(fullName) {
  if (!fullName) return "Student";
  const clean = fullName
    .replace(/^(dr\.|dr|mr\.|mr|ms\.|ms|mrs\.|mrs|prof\.|prof)\s+/i, "")
    .trim();
  const first = clean.split(/\s+/)[0];
  return first || "Student";
}

function StudentDashboard() {
  const navigate = useNavigate();
  const auth = useAuth();
  const loggedInUser = auth?.user;

  // Real backend states
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const [trendWeeks, setTrendWeeks] = useState(4);
  const [dashboardData, setDashboardData] = useState(null);
  const [hoveredPoint, setHoveredPoint] = useState(null);

  const greeting = getGreeting();

  // Load real student dashboard data from backend API
  useEffect(() => {
    let isCancelled = false;

    async function loadData() {
      try {
        setLoading(true);
        setErrorMessage("");

        const result = await getStudentDashboard(trendWeeks);

        if (isCancelled) return;

        if (result?.success && result?.data) {
          setDashboardData(result.data);
        } else {
          setErrorMessage(
            result?.message || "Unable to load student dashboard data."
          );
        }
      } catch (err) {
        if (isCancelled) return;
        setErrorMessage(
          err?.response?.data?.message ||
            err?.message ||
            "Failed to connect to student dashboard API."
        );
      } finally {
        if (!isCancelled) {
          setLoading(false);
        }
      }
    }

    loadData();

    return () => {
      isCancelled = true;
    };
  }, [trendWeeks]);

  // Extract real backend data with strict checks (no fake numbers)
  const student = dashboardData?.student || null;
  const stats = dashboardData?.stats || null;
  const trend = dashboardData?.attendance_trend || null;
  const trendPoints = useMemo(
    () => (Array.isArray(trend?.points) ? trend.points : []),
    [trend]
  );
  const todaySchedule = dashboardData?.today_schedule || null;
  const todayClasses = Array.isArray(todaySchedule?.classes)
    ? todaySchedule.classes
    : [];
  const courses = Array.isArray(dashboardData?.courses)
    ? dashboardData.courses
    : null;
  const recentAttendance = Array.isArray(dashboardData?.recent_attendance)
    ? dashboardData.recent_attendance
    : null;

  const displayName = student?.name || loggedInUser?.name || "";
  const firstName = getFirstName(displayName);
  const departmentName = student?.department_name || null;
  const semesterNumber = student?.semester;

  // Real metric values
  const overallPct = stats?.overall_attendance_percentage;
  const classesAttended = stats?.classes_attended;
  const classesMissed = stats?.classes_missed;
  const totalScheduled = stats?.total_classes_scheduled;
  const enrolledCount = stats?.enrolled_courses_count ?? courses?.length;

  const attendanceChange = stats?.attendance_change_percentage;
  const attendedChange = stats?.attended_change_percentage;
  const missedChange = stats?.missed_change_percentage;
  const isAboveAvg = stats?.is_above_average ?? (overallPct != null ? overallPct >= 75 : true);

  // SVG Chart calculation for Attendance Trend
  const chartWidth = 380;
  const chartHeight = 160;
  const paddingX = 40;
  const paddingY = 24;

  const pointsCoordinates = useMemo(() => {
    if (trendPoints.length === 0) return [];

    const usableWidth = chartWidth - paddingX * 2;
    const usableHeight = chartHeight - paddingY * 2;

    return trendPoints.map((pt, idx) => {
      const x =
        trendPoints.length === 1
          ? chartWidth / 2
          : paddingX + (idx / (trendPoints.length - 1)) * usableWidth;

      const hasSessions = pt.total != null && pt.total > 0 && pt.rate !== null && pt.rate !== undefined;
      const rateVal = hasSessions ? Math.min(100, Math.max(0, pt.rate)) : 0;
      const y = paddingY + usableHeight - (rateVal / 100) * usableHeight;

      return { x, y, hasSessions, ...pt };
    });
  }, [trendPoints]);

  const svgPathD = useMemo(() => {
    if (pointsCoordinates.length === 0) return "";
    if (pointsCoordinates.length === 1) {
      return `M ${pointsCoordinates[0].x} ${pointsCoordinates[0].y}`;
    }

    let d = `M ${pointsCoordinates[0].x} ${pointsCoordinates[0].y}`;
    for (let i = 0; i < pointsCoordinates.length - 1; i++) {
      const p0 = pointsCoordinates[i];
      const p1 = pointsCoordinates[i + 1];
      const cx = (p0.x + p1.x) / 2;
      d += ` C ${cx} ${p0.y}, ${cx} ${p1.y}, ${p1.x} ${p1.y}`;
    }
    return d;
  }, [pointsCoordinates]);

  return (
    <div className="student-dashboard-wrapper">
      {/* If error loading API */}
      {errorMessage && (
        <div className="student-api-alert" role="alert">
          <AlertCircle size={16} />
          <span>API integration pending: {errorMessage}</span>
        </div>
      )}

      {/* ============================================================
          1. HERO WELCOME BANNER
      ============================================================ */}
      <section className="student-hero-banner" aria-label="Student Welcome">
        <div className="student-hero-left">
          <h1 className="student-hero-title">
            {greeting}, {firstName}!
          </h1>
          <p className="student-hero-subtitle">
            Stay consistent, stay ahead. Your learning journey matters!
          </p>

          <div className="student-hero-badge">
            <GraduationCap size={16} strokeWidth={2.4} />
            <span>
              {departmentName
                ? `${departmentName} • Semester ${semesterNumber || 1}`
                : "API integration pending"}
            </span>
          </div>
        </div>

        <div className="student-hero-right">
          <div className="student-hero-image-wrap">
            <img
              src={bannerCampusImg || "/image/student_banner_campus.jpg"}
              alt="University Campus Building"
              className="student-hero-banner-img"
            />
          </div>
        </div>
      </section>

      {/* ============================================================
          2. TOP 4 METRIC STAT CARDS
      ============================================================ */}
      <section className="student-stat-cards-row" aria-label="Quick metrics">
        {/* Card 1: Overall Attendance */}
        <div className="student-stat-card student-card-blue">
          <div className="student-card-bg-wrap" aria-hidden="true">
            <img
              src={cardAttendanceImg}
              alt=""
              className="student-card-bg-img"
              loading="eager"
            />
          </div>
          <div className="student-card-overlay" aria-hidden="true" />
          <div className="student-card-inner">
            <div className="student-card-header">
              <div className="student-card-icon-badge blue-badge">
                <CalendarDays size={20} strokeWidth={2.2} />
              </div>
            </div>

            <div className="student-card-body">
              <span className="student-card-label">Overall Attendance</span>
              <div className="student-card-metric-row">
                {overallPct != null ? (
                  <>
                    <span className="student-card-value">{overallPct}%</span>
                    {attendanceChange != null ? (
                      <span
                        className={`student-card-trend-badge ${
                          attendanceChange >= 0 ? "green-trend" : "red-trend"
                        }`}
                      >
                        {attendanceChange >= 0 ? (
                          <TrendingUp size={13} strokeWidth={2.6} />
                        ) : (
                          <TrendingDown size={13} strokeWidth={2.6} />
                        )}
                        <span>{Math.abs(attendanceChange)}%</span>
                      </span>
                    ) : (
                      <span className="student-api-pending-badge">API pending</span>
                    )}
                  </>
                ) : (
                  <span className="student-api-pending">API integration pending</span>
                )}
              </div>
              <p className="student-card-footer">
                {classesAttended != null && totalScheduled != null
                  ? `${classesAttended} days present out of ${totalScheduled}`
                  : "API integration pending"}
              </p>
            </div>
          </div>
        </div>

        {/* Card 2: Classes Attended */}
        <div className="student-stat-card student-card-green">
          <div className="student-card-bg-wrap" aria-hidden="true">
            <img
              src={cardAttendedImg}
              alt=""
              className="student-card-bg-img"
              loading="eager"
            />
          </div>
          <div className="student-card-overlay" aria-hidden="true" />
          <div className="student-card-inner">
            <div className="student-card-header">
              <div className="student-card-icon-badge green-badge">
                <CheckCircle2 size={20} strokeWidth={2.2} />
              </div>
            </div>

            <div className="student-card-body">
              <span className="student-card-label">Classes Attended</span>
              <div className="student-card-metric-row">
                {classesAttended != null ? (
                  <>
                    <span className="student-card-value">{classesAttended}</span>
                    {attendedChange != null ? (
                      <span
                        className={`student-card-trend-badge ${
                          attendedChange >= 0 ? "green-trend" : "red-trend"
                        }`}
                      >
                        {attendedChange >= 0 ? (
                          <TrendingUp size={13} strokeWidth={2.6} />
                        ) : (
                          <TrendingDown size={13} strokeWidth={2.6} />
                        )}
                        <span>{Math.abs(attendedChange)}%</span>
                      </span>
                    ) : (
                      <span className="student-api-pending-badge">API pending</span>
                    )}
                  </>
                ) : (
                  <span className="student-api-pending">API integration pending</span>
                )}
              </div>
              <p className="student-card-footer">
                {totalScheduled != null
                  ? `out of ${totalScheduled} scheduled`
                  : "API integration pending"}
              </p>
            </div>
          </div>
        </div>

        {/* Card 3: Classes Missed */}
        <div className="student-stat-card student-card-red">
          <div className="student-card-bg-wrap" aria-hidden="true">
            <img
              src={cardMissedImg}
              alt=""
              className="student-card-bg-img"
              loading="eager"
            />
          </div>
          <div className="student-card-overlay" aria-hidden="true" />
          <div className="student-card-inner">
            <div className="student-card-header">
              <div className="student-card-icon-badge red-badge">
                <XCircle size={20} strokeWidth={2.2} />
              </div>
            </div>

            <div className="student-card-body">
              <span className="student-card-label">Classes Missed</span>
              <div className="student-card-metric-row">
                {classesMissed != null ? (
                  <>
                    <span className="student-card-value">{classesMissed}</span>
                    {missedChange != null ? (
                      <span
                        className={`student-card-trend-badge ${
                          missedChange > 0 ? "red-trend" : "green-trend"
                        }`}
                      >
                        {missedChange > 0 ? (
                          <TrendingDown size={13} strokeWidth={2.6} />
                        ) : (
                          <TrendingUp size={13} strokeWidth={2.6} />
                        )}
                        <span>{Math.abs(missedChange)}%</span>
                      </span>
                    ) : (
                      <span className="student-api-pending-badge">API pending</span>
                    )}
                  </>
                ) : (
                  <span className="student-api-pending">API integration pending</span>
                )}
              </div>
              <p className="student-card-footer">
                {totalScheduled != null
                  ? `out of ${totalScheduled} scheduled`
                  : "API integration pending"}
              </p>
            </div>
          </div>
        </div>

        {/* Card 4: Enrolled Courses */}
        <div className="student-stat-card student-card-purple">
          <div className="student-card-bg-wrap" aria-hidden="true">
            <img
              src={cardCoursesImg}
              alt=""
              className="student-card-bg-img"
              loading="eager"
            />
          </div>
          <div className="student-card-overlay" aria-hidden="true" />
          <div className="student-card-inner">
            <div className="student-card-header">
              <div className="student-card-icon-badge purple-badge">
                <BookOpen size={20} strokeWidth={2.2} />
              </div>
            </div>

            <div className="student-card-body">
              <span className="student-card-label">Enrolled Courses</span>
              <div className="student-card-metric-row">
                {enrolledCount != null ? (
                  <span className="student-card-value">{enrolledCount}</span>
                ) : (
                  <span className="student-api-pending">API integration pending</span>
                )}
              </div>
              <p className="student-card-footer">active this semester</p>
            </div>
          </div>
        </div>
      </section>

      {/* ============================================================
          3. MIDDLE SECTION (Trend Chart, Today's Schedule, Quick Actions)
      ============================================================ */}
      <section className="student-middle-grid">
        {/* Middle Left: Attendance Trend Card */}
        <div className="student-panel student-trend-panel">
          <div className="student-panel-header">
            <div className="student-panel-title-wrap">
              <div className="student-panel-icon blue-icon">
                <CalendarDays size={18} />
              </div>
              <h3>Attendance Trend</h3>
            </div>

            <div className="student-panel-actions">
              <select
                className="student-filter-select"
                value={trendWeeks}
                onChange={(e) => setTrendWeeks(Number(e.target.value))}
                aria-label="Select trend time range"
              >
                <option value={4}>Last 4 Weeks</option>
                <option value={8}>Last 8 Weeks</option>
                <option value={12}>This Semester</option>
              </select>
            </div>
          </div>

          <div className="student-trend-content">
            {/* SVG Chart side */}
            <div className="student-trend-chart-container">
              {trendPoints.length === 0 ? (
                <div className="student-empty-trend">
                  {loading ? "Loading trend..." : "API integration pending"}
                </div>
              ) : (
                <>
                  <div className="student-chart-svg-wrap">
                    <svg
                      viewBox={`0 0 ${chartWidth} ${chartHeight}`}
                      className="student-trend-svg"
                      preserveAspectRatio="none"
                    >
                      {/* Horizontal Grid lines */}
                      {[100, 75, 50, 25, 0].map((pct) => {
                        const usableHeight = chartHeight - paddingY * 2;
                        const y = paddingY + usableHeight - (pct / 100) * usableHeight;
                        return (
                          <g key={pct} className="student-grid-line-group">
                            <line
                              x1={paddingX}
                              y1={y}
                              x2={chartWidth - paddingX}
                              y2={y}
                              className="student-grid-line"
                            />
                            <text
                              x={paddingX - 8}
                              y={y + 4}
                              className="student-y-axis-label"
                              textAnchor="end"
                            >
                              {pct}%
                            </text>
                          </g>
                        );
                      })}

                      {/* Gradient Fill under the line */}
                      <defs>
                        <linearGradient
                          id="studentTrendAreaGrad"
                          x1="0"
                          y1="0"
                          x2="0"
                          y2="1"
                        >
                          <stop
                            offset="0%"
                            stopColor="#2563eb"
                            stopOpacity="0.16"
                          />
                          <stop
                            offset="100%"
                            stopColor="#2563eb"
                            stopOpacity="0.0"
                          />
                        </linearGradient>
                      </defs>

                      {/* Filled area path */}
                      {pointsCoordinates.length > 1 && (
                        <path
                          d={`${svgPathD} L ${
                            pointsCoordinates[pointsCoordinates.length - 1].x
                          } ${chartHeight - paddingY} L ${
                            pointsCoordinates[0].x
                          } ${chartHeight - paddingY} Z`}
                          fill="url(#studentTrendAreaGrad)"
                        />
                      )}

                      {/* The trend curve */}
                      {svgPathD && (
                        <path
                          d={svgPathD}
                          fill="none"
                          stroke="#2563eb"
                          strokeWidth="2.8"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      )}

                      {/* Trend Point Dots */}
                      {pointsCoordinates.map((pt, idx) => (
                        <g
                          key={idx}
                          className="student-chart-point-group"
                          onMouseEnter={() => setHoveredPoint(pt)}
                          onMouseLeave={() => setHoveredPoint(null)}
                        >
                          <circle
                            cx={pt.x}
                            cy={pt.y}
                            r="4.5"
                            className="student-chart-point"
                          />
                          <circle
                            cx={pt.x}
                            cy={pt.y}
                            r="9"
                            className="student-chart-point-hitbox"
                          />
                        </g>
                      ))}
                    </svg>

                    {/* Hover Tooltip */}
                    {hoveredPoint && (
                      <div
                        className="student-chart-tooltip"
                        style={{
                          left: `${(hoveredPoint.x / chartWidth) * 100}%`,
                          top: `${(hoveredPoint.y / chartHeight) * 100}%`,
                        }}
                      >
                        <strong>
                          {hoveredPoint.rate !== null && hoveredPoint.rate !== undefined
                            ? `${hoveredPoint.rate}%`
                            : "No sessions"}
                        </strong>
                        <small>
                          {hoveredPoint.label}
                          {hoveredPoint.total > 0
                            ? ` (${hoveredPoint.present}/${hoveredPoint.total} attended)`
                            : " (0 classes scheduled)"}
                        </small>
                      </div>
                    )}
                  </div>

                  {/* X-axis labels */}
                  <div className="student-x-axis-row">
                    {pointsCoordinates.map((pt, idx) => (
                      <span key={idx} className="student-x-axis-label">
                        {pt.label}
                      </span>
                    ))}
                  </div>

                  <div className="student-chart-legend">
                    <span className="legend-dot" />
                    <span>Attendance Rate</span>
                  </div>
                </>
              )}
            </div>

            {/* Right side stats summary & callout */}
            <div className="student-trend-sidebar">
              <div className="student-trend-current">
                <span className="trend-current-label">Current Attendance</span>
                <div className="trend-current-val-row">
                  {overallPct != null ? (
                    <>
                      <span className="trend-current-val">{overallPct}%</span>
                      {attendanceChange != null && (
                        <span
                          className={`student-card-trend-badge ${
                            attendanceChange >= 0 ? "green-trend" : "red-trend"
                          }`}
                        >
                          {attendanceChange >= 0 ? (
                            <TrendingUp size={12} strokeWidth={2.4} />
                          ) : (
                            <TrendingDown size={12} strokeWidth={2.4} />
                          )}
                          <span>{Math.abs(attendanceChange)}%</span>
                        </span>
                      )}
                    </>
                  ) : (
                    <span className="student-api-pending">API integration pending</span>
                  )}
                </div>
                <span className="trend-current-sub">
                  vs. last {trendWeeks} weeks
                </span>
              </div>

              {overallPct != null ? (
                <div
                  className={`student-status-callout ${
                    isAboveAvg ? "callout-good" : "callout-warning"
                  }`}
                >
                  <div className="callout-header">
                    <span className="callout-emoji">
                      {isAboveAvg ? "🎉" : "⚠️"}
                    </span>
                    <strong>{isAboveAvg ? "Great job!" : "Attention Needed"}</strong>
                  </div>
                  <p className="callout-text">
                    {isAboveAvg
                      ? "Your attendance is above the class average."
                      : "Your attendance is currently below 75% requirement."}
                  </p>
                </div>
              ) : (
                <div className="student-status-callout callout-pending">
                  <p className="callout-text">API integration pending</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Middle Center: Today's Schedule Card */}
        <div className="student-panel student-schedule-panel">
          <div className="student-panel-header">
            <div className="student-panel-title-wrap">
              <div className="student-panel-icon blue-icon">
                <Calendar size={18} />
              </div>
              <h3>Today's Schedule</h3>
            </div>
            <span className="student-panel-date">
              {todaySchedule?.date_display ||
                new Intl.DateTimeFormat("en-US", {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                  weekday: "short",
                }).format(new Date())}
            </span>
          </div>

          <div className="student-schedule-list">
            {!todaySchedule && !loading ? (
              <div className="student-schedule-empty">
                <p>API integration pending</p>
              </div>
            ) : todayClasses.length === 0 ? (
              <div className="student-schedule-empty">
                <Clock size={32} className="empty-icon" />
                <p>No classes scheduled for today.</p>
                <span>Enjoy your study time or review lecture notes!</span>
              </div>
            ) : (
              todayClasses.slice(0, 4).map((item, idx) => {
                const status = (item.status || "UPCOMING").toUpperCase();
                return (
                  <div key={item.timetable_entry_id || idx} className="student-schedule-item">
                    <div className="student-schedule-time">
                      <span>{item.time_slot || `${item.start_time} - ${item.end_time}`}</span>
                    </div>

                    <div className="student-schedule-details">
                      <h4 className="student-schedule-subject">{item.course_name}</h4>
                      <p className="student-schedule-meta">
                        Section {item.section} • {item.room}
                      </p>
                    </div>

                    <div className="student-schedule-status-wrap">
                      {status === "COMPLETED" && (
                        <span className="schedule-badge completed">
                          <Check size={12} strokeWidth={3} />
                          <span>Completed</span>
                        </span>
                      )}
                      {status === "ONGOING" && (
                        <span className="schedule-badge ongoing">
                          <span className="pulse-dot" />
                          <span>Ongoing</span>
                        </span>
                      )}
                      {status === "UPCOMING" && (
                        <span className="schedule-badge upcoming">
                          <Circle size={9} strokeWidth={2.5} />
                          <span>Upcoming</span>
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Middle Right: Quick Actions Card */}
        <div className="student-panel student-quick-actions-panel">
          <div className="student-panel-header">
            <div className="student-panel-title-wrap">
              <div className="student-panel-icon blue-icon">
                <Zap size={18} />
              </div>
              <h3>Quick Actions</h3>
            </div>
          </div>

          <div className="student-quick-actions-list">
            <button
              type="button"
              className="student-action-item"
              onClick={() => navigate("/student/timetable")}
            >
              <div className="action-icon-wrap blue-action">
                <CalendarDays size={18} strokeWidth={2.2} />
              </div>
              <div className="action-copy">
                <strong>View Timetable</strong>
                <span>Check your class schedule</span>
              </div>
              <ChevronRight size={17} className="action-arrow" />
            </button>

            <button
              type="button"
              className="student-action-item"
              onClick={() => navigate("/student/courses")}
            >
              <div className="action-icon-wrap green-action">
                <BookOpen size={18} strokeWidth={2.2} />
              </div>
              <div className="action-copy">
                <strong>My Courses</strong>
                <span>View enrolled courses</span>
              </div>
              <ChevronRight size={17} className="action-arrow" />
            </button>

            <button
              type="button"
              className="student-action-item"
              onClick={() => navigate("/student/reports")}
            >
              <div className="action-icon-wrap purple-action">
                <BarChart3 size={18} strokeWidth={2.2} />
              </div>
              <div className="action-copy">
                <strong>Attendance Reports</strong>
                <span>View detailed attendance</span>
              </div>
              <ChevronRight size={17} className="action-arrow" />
            </button>

            <button
              type="button"
              className="student-action-item"
              onClick={() => navigate("/student/profile")}
            >
              <div className="action-icon-wrap red-action">
                <UserIcon size={18} strokeWidth={2.2} />
              </div>
              <div className="action-copy">
                <strong>Profile</strong>
                <span>Manage your profile</span>
              </div>
              <ChevronRight size={17} className="action-arrow" />
            </button>
          </div>
        </div>
      </section>

      {/* ============================================================
          4. BOTTOM ROW (My Courses, Recent Attendance, Motivation Card)
      ============================================================ */}
      <section className="student-bottom-grid">
        {/* Bottom Left: My Courses Card */}
        <div className="student-panel student-courses-panel">
          <div className="student-panel-header">
            <div className="student-panel-title-wrap">
              <div className="student-panel-icon blue-icon">
                <BookOpen size={18} />
              </div>
              <h3>My Courses</h3>
            </div>
            <button
              type="button"
              className="student-view-all-btn"
              onClick={() => navigate("/student/courses")}
            >
              View All
            </button>
          </div>

          <div className="student-table-container">
            <table className="student-table">
              <thead>
                <tr>
                  <th style={{ width: "22%" }}>Course Code</th>
                  <th style={{ width: "38%" }}>Course Name</th>
                  <th style={{ width: "24%" }}>Faculty</th>
                  <th style={{ width: "16%" }}>Attendance</th>
                </tr>
              </thead>
              <tbody>
                {courses === null && !loading ? (
                  <tr>
                    <td colSpan={4} className="student-table-empty">
                      API integration pending
                    </td>
                  </tr>
                ) : courses && courses.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="student-table-empty">
                      No active courses enrolled this semester.
                    </td>
                  </tr>
                ) : (
                  (courses || []).slice(0, 5).map((course, idx) => {
                    const pct = Number(course.attendance_percentage || 0);
                    return (
                      <tr key={course.offering_id || course.course_id || idx}>
                        <td className="code-cell">{course.course_code}</td>
                        <td className="name-cell" title={course.course_name}>
                          {course.course_name}
                        </td>
                        <td className="faculty-cell" title={course.faculty_name}>
                          {course.faculty_name || "API integration pending"}
                        </td>
                        <td className="attendance-cell">
                          <div className="progress-cell-wrap">
                            <span className="progress-num">{pct}%</span>
                            <div className="mini-progress-bar">
                              <div
                                className={`mini-progress-fill ${
                                  pct >= 75 ? "fill-green" : "fill-amber"
                                }`}
                                style={{ width: `${Math.min(100, Math.max(0, pct))}%` }}
                              />
                            </div>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Bottom Center: Recent Attendance Card */}
        <div className="student-panel student-attendance-panel">
          <div className="student-panel-header">
            <div className="student-panel-title-wrap">
              <div className="student-panel-icon blue-icon">
                <Clock size={18} />
              </div>
              <h3>Recent Attendance</h3>
            </div>
            <button
              type="button"
              className="student-view-all-btn"
              onClick={() => navigate("/student/attendance")}
            >
              View All
            </button>
          </div>

          <div className="student-table-container">
            <table className="student-table">
              <thead>
                <tr>
                  <th style={{ width: "28%" }}>Date</th>
                  <th style={{ width: "47%" }}>Subject</th>
                  <th style={{ width: "25%" }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {recentAttendance === null && !loading ? (
                  <tr>
                    <td colSpan={3} className="student-table-empty">
                      API integration pending
                    </td>
                  </tr>
                ) : recentAttendance && recentAttendance.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="student-table-empty">
                      No recent attendance records found.
                    </td>
                  </tr>
                ) : (
                  (recentAttendance || []).slice(0, 5).map((record, idx) => {
                    const isPresent =
                      (record.status || "").toUpperCase() === "PRESENT";
                    return (
                      <tr key={record.attendance_id || idx}>
                        <td className="date-cell">{record.date}</td>
                        <td className="subject-cell" title={record.subject}>
                          {record.subject}
                        </td>
                        <td className="status-cell">
                          <span
                            className={`status-pill ${
                              isPresent ? "pill-present" : "pill-absent"
                            }`}
                          >
                            {isPresent ? "Present" : "Absent"}
                          </span>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Bottom Right: Motivational Card */}
        <div className="student-panel student-motivation-card">
          <div className="motivation-bg-wrap" aria-hidden="true">
            <img
              src={cardMotivationImg}
              alt=""
              className="motivation-bg-img"
              loading="eager"
            />
          </div>
          <div className="motivation-bg-overlay" aria-hidden="true" />

          <div className="motivation-content">
            <div className="motivation-icon-ring">
              <Target size={20} className="motivation-icon" />
            </div>

            <h3 className="motivation-title">
              Small steps every day lead to big results.
            </h3>

            <p className="motivation-sub">
              Keep attending, keep learning, keep growing!
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}

export default StudentDashboard;
