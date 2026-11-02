import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Users,
  BookOpen,
  BarChart3,
  ExternalLink,
  ArrowRight,
  CheckCircle2,
  Check,
  Clock,
  Zap,
  Headphones,
  ChevronRight,
  Sparkles,
  FileText,
  AlertTriangle,
  RotateCw,
  LogIn,
  UserPlus,
  GraduationCap,
  Building2,
  Calendar,
} from "lucide-react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faChalkboardUser } from "@fortawesome/free-solid-svg-icons";

import {
  getAdminDashboard,
  getRecentActivity,
  getAdminAttendanceAnalytics,
} from "../../services/adminService";
import { formatActivityTime } from "../../utils/dateUtils";
import useAuth from "../../hooks/useAuth";
import "./AdminDashboard.css";

function getActivityIconConfig(actionType = "") {
  const type = String(actionType).toUpperCase();
  if (type.includes("LOGIN")) {
    return {
      icon: <LogIn size={13} />,
      bgClass: "activity-icon-blue",
    };
  }
  if (type.includes("STUDENT")) {
    return {
      icon: <GraduationCap size={13} />,
      bgClass: "activity-icon-green",
    };
  }
  if (type.includes("FACULTY")) {
    return {
      icon: <Users size={13} />,
      bgClass: "activity-icon-purple",
    };
  }
  if (type.includes("DEPARTMENT")) {
    return {
      icon: <Building2 size={13} />,
      bgClass: "activity-icon-amber",
    };
  }
  if (type.includes("TIMETABLE")) {
    return {
      icon: <Calendar size={13} />,
      bgClass: "activity-icon-teal",
    };
  }
  if (type.includes("ATTENDANCE")) {
    return {
      icon: <CheckCircle2 size={13} />,
      bgClass: "activity-icon-emerald",
    };
  }
  if (type.includes("COURSE") || type.includes("ENROLLMENT")) {
    return {
      icon: <BookOpen size={13} />,
      bgClass: "activity-icon-purple",
    };
  }
  if (type.includes("USER")) {
    return {
      icon: <UserPlus size={13} />,
      bgClass: "activity-icon-blue",
    };
  }
  return {
    icon: <Clock size={13} />,
    bgClass: "activity-icon-slate",
  };
}

function getGreeting() {
  const hour = new Date().getHours();
  if (hour >= 5 && hour < 12) return "Good morning";
  if (hour >= 12 && hour < 17) return "Good afternoon";
  if (hour >= 17 && hour < 22) return "Good evening";
  return "Welcome back";
}

function getInitials(name) {
  if (!name) return "AD";
  const cleanName = name
    .replace(/^(dr\.|dr|prof\.|prof|mr\.|mr|mrs\.|mrs|ms\.|ms)\s+/i, "")
    .trim();
  const parts = cleanName.split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "AD";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function AdminDashboard() {
  const { user } = useAuth();
  const displayName =
    user?.name ||
    user?.full_name ||
    user?.fullName ||
    user?.username ||
    (user?.email ? user.email.split("@")[0] : "Admin");
  const initials = getInitials(displayName);
  const greeting = getGreeting();

  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  const [recentActivities, setRecentActivities] = useState([]);
  const [activityLoading, setActivityLoading] = useState(false);
  const [activityError, setActivityError] = useState("");

  const [analyticsData, setAnalyticsData] = useState(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(true);
  const [analyticsError, setAnalyticsError] = useState("");

  const handleRetryAnalytics = async () => {
    try {
      setAnalyticsLoading(true);
      setAnalyticsError("");
      const res = await getAdminAttendanceAnalytics();
      if (res?.success) {
        setAnalyticsData(res.data || null);
      } else {
        setAnalyticsData(null);
        setAnalyticsError(res?.message || "Failed to load attendance analytics.");
      }
    } catch (err) {
      setAnalyticsData(null);
      setAnalyticsError(
        err?.response?.data?.message ||
          err?.message ||
          "Unable to load attendance analytics."
      );
    } finally {
      setAnalyticsLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;

    async function loadInitialData() {
      try {
        const [dashRes, analyticsRes] = await Promise.allSettled([
          getAdminDashboard(),
          getAdminAttendanceAnalytics(),
        ]);

        if (cancelled) return;

        if (dashRes.status === "fulfilled" && dashRes.value?.success) {
          setDashboardData(dashRes.value.data || null);
          setRecentActivities(dashRes.value.data?.recent_activity || []);
          setErrorMessage("");
          setActivityError("");
        } else {
          const err = dashRes.status === "rejected" ? dashRes.reason : null;
          setDashboardData(null);
          setRecentActivities([]);
          setErrorMessage(
            err?.response?.data?.message ||
              err?.message ||
              (dashRes.status === "fulfilled" && dashRes.value?.message) ||
              "Unable to load dashboard data."
          );
        }

        if (analyticsRes.status === "fulfilled" && analyticsRes.value?.success) {
          setAnalyticsData(analyticsRes.value.data || null);
          setAnalyticsError("");
        } else {
          const err = analyticsRes.status === "rejected" ? analyticsRes.reason : null;
          setAnalyticsData(null);
          setAnalyticsError(
            err?.response?.data?.message ||
              err?.message ||
              (analyticsRes.status === "fulfilled" && analyticsRes.value?.message) ||
              "Failed to load attendance analytics."
          );
        }
      } catch (err) {
        if (cancelled) return;
        setErrorMessage(err?.message || "Unexpected error loading dashboard.");
      } finally {
        if (!cancelled) {
          setLoading(false);
          setAnalyticsLoading(false);
        }
      }
    }

    loadInitialData();

    return () => {
      cancelled = true;
    };
  }, []);

  const handleRetryActivity = async () => {
    setActivityLoading(true);
    setActivityError("");
    try {
      const res = await getRecentActivity(6);
      if (res?.success) {
        setRecentActivities(res.data || []);
      } else {
        throw new Error(res?.message || "Failed to load recent activity.");
      }
    } catch (err) {
      setActivityError(
        err?.response?.data?.message ||
          err?.message ||
          "Unable to load recent activity."
      );
    } finally {
      setActivityLoading(false);
    }
  };

  const formatMetric = (value) => {
    return value === null || value === undefined ? "N/A" : value;
  };

  const totalStudents = dashboardData?.total_students;
  const totalFaculty = dashboardData?.total_faculty;
  const totalCourses = dashboardData?.total_courses;

  const attendanceSummary = dashboardData?.attendance_summary;

  const totalAttendanceRecords = attendanceSummary?.total_records;
  const presentAttendance = attendanceSummary?.present;
  const absentAttendance = attendanceSummary?.absent;

  const hasAttendanceData =
    attendanceSummary &&
    typeof totalAttendanceRecords === "number" &&
    totalAttendanceRecords > 0;

  const attendancePercentage = hasAttendanceData
    ? Math.round((presentAttendance / totalAttendanceRecords) * 100)
    : null;

  if (loading) {
    return (
      <section className="admin-dashboard">
        <div className="admin-dashboard-loading">
          <div className="admin-loading-icon">
            <i className="fa-solid fa-spinner fa-spin" />
          </div>
          <h2>Loading dashboard</h2>
          <p>
            Fetching the latest administration statistics from the backend.
          </p>
        </div>
      </section>
    );
  }

  if (errorMessage) {
    return (
      <section className="admin-dashboard">
        <div className="admin-dashboard-error">
          <div className="admin-error-icon">
            <i className="fa-solid fa-triangle-exclamation" />
          </div>
          <h2>Unable to load dashboard</h2>
          <p>{errorMessage}</p>
          <span>API integration is currently unavailable.</span>
        </div>
      </section>
    );
  }

  return (
    <section className="admin-dashboard">
      {/* =========================
          WELCOME BANNER
      ========================== */}
      <section className="admin-welcome-banner">
        <div className="admin-welcome-left">
          <div className="admin-welcome-avatar">{initials}</div>
          <div className="admin-welcome-text">
            <h1>{greeting}, {displayName}!</h1>
            <p>
              Monitor students, faculty, courses, and attendance from one centralized dashboard.
            </p>
          </div>
        </div>

        <div className="admin-welcome-quote">
          <p>“Better data,</p>
          <p>Smarter decisions.</p>
          <p>A more connected campus.”</p>
          <span>— SAMS-FR</span>
        </div>


        <div className="admin-welcome-image-wrapper">
          <img
            src="/image/admin_campus_banner.jpg"
            alt="Campus Architecture"
            className="admin-welcome-campus-img"
          />
        </div>
      </section>

      {/* =========================
          PRIMARY 4 STAT CARDS
      ========================== */}
      <div className="admin-stat-grid">
        <Link to="/admin/students" className="admin-stat-card admin-stat-students">
          <div className="admin-stat-icon-wrapper admin-icon-blue">
            <Users size={18} />
          </div>
          <div className="admin-stat-details">
            <span className="admin-stat-label">Total Students</span>
            <strong className="admin-stat-value">
              {formatMetric(totalStudents)}
            </strong>
            <span className="admin-stat-sub">Registered students</span>
          </div>
        </Link>

        <Link to="/admin/faculty" className="admin-stat-card admin-stat-faculty">
          <div className="admin-stat-icon-wrapper admin-icon-green">
            <FontAwesomeIcon icon={faChalkboardUser} />
          </div>
          <div className="admin-stat-details">
            <span className="admin-stat-label">Total Faculty</span>
            <strong className="admin-stat-value">
              {formatMetric(totalFaculty)}
            </strong>
            <span className="admin-stat-sub">Registered faculty members</span>
          </div>
        </Link>

        <Link to="/admin/academic-management" className="admin-stat-card admin-stat-courses">
          <div className="admin-stat-icon-wrapper admin-icon-purple">
            <BookOpen size={18} />
          </div>
          <div className="admin-stat-details">
            <span className="admin-stat-label">Total Courses</span>
            <strong className="admin-stat-value">
              {formatMetric(totalCourses)}
            </strong>
            <span className="admin-stat-sub">Courses in the system</span>
          </div>
        </Link>

        <Link to="/admin/attendance-reports" className="admin-stat-card admin-stat-attendance">
          <div className="admin-stat-icon-wrapper admin-icon-orange">
            <BarChart3 size={18} />
          </div>
          <div className="admin-stat-details">
            <span className="admin-stat-label">Overall Attendance</span>
            <strong className="admin-stat-value">
              {attendancePercentage === null ? "N/A" : `${attendancePercentage}%`}
            </strong>
            <span className="admin-stat-sub">Based on verified attendance records</span>
          </div>
        </Link>
      </div>

      {/* =========================
          MIDDLE 3-COLUMN SECTION
      ========================== */}
      <div className="admin-middle-grid">
        {/* Panel 1: Attendance Overview */}
        <section className="admin-panel admin-attendance-overview-panel">
          <div className="admin-panel-top">
            <div className="admin-panel-title-area">
              <BarChart3 size={18} className="admin-panel-header-icon text-blue" />
              <div>
                <h2>Attendance Overview</h2>
                <p>Course-wise attendance performance across active offerings.</p>
              </div>
            </div>
            <Link to="/admin/attendance-reports" className="admin-panel-link-badge">
              <span>View Reports</span>
              <ExternalLink size={11} />
            </Link>
          </div>

          {analyticsLoading ? (
            <div className="admin-panel-inner-box">
              <div
                className="admin-loading-icon"
                style={{ fontSize: "20px", color: "#3b82f6", marginBottom: "8px" }}
              >
                <i className="fa-solid fa-spinner fa-spin" />
              </div>
              <p>Loading attendance analytics...</p>
            </div>
          ) : analyticsError ? (
            <div className="admin-panel-inner-box">
              <div
                className="admin-empty-icon-circle"
                style={{ background: "#fef2f2", color: "#ef4444" }}
              >
                <AlertTriangle size={24} />
              </div>
              <h3>Unable to load analytics</h3>
              <p>{analyticsError}</p>
              <button
                type="button"
                className="admin-btn-primary"
                onClick={handleRetryAnalytics}
                style={{ marginTop: "12px", padding: "6px 14px", fontSize: "12px" }}
              >
                <span>Retry</span>
              </button>
            </div>
          ) : !analyticsData ||
            !Array.isArray(analyticsData.courses) ||
            analyticsData.courses.length === 0 ? (
            <div className="admin-panel-inner-box">
              <div className="admin-empty-icon-circle blue-circle">
                <BarChart3 size={24} />
              </div>
              <h3>No closed sessions yet</h3>
              <p>
                Attendance analytics will appear once attendance sessions are completed
                and closed.
              </p>
              <Link to="/admin/attendance-reports" className="admin-btn-primary">
                <span>Open attendance reports</span>
                <ArrowRight size={13} />
              </Link>
            </div>
          ) : (
            <div className="admin-analytics-list">
              {analyticsData.courses.slice(0, 4).map((c) => {
                const pct =
                  typeof c.attendance_percentage === "number"
                    ? c.attendance_percentage
                    : 0;
                const badgeClass =
                  pct >= 75 ? "badge-high" : pct >= 60 ? "badge-mid" : "badge-low";
                const barColor =
                  pct >= 75 ? "#10b981" : pct >= 60 ? "#f59e0b" : "#ef4444";
                const totalAtt =
                  (c.total_present || 0) + (c.total_absent || 0);

                return (
                  <div key={c.offering_id} className="admin-analytics-item">
                    <div className="admin-analytics-item-header">
                      <span
                        className="admin-analytics-course-name"
                        title={c.course?.course_name}
                      >
                        {c.course?.course_code} • {c.course?.course_name}
                      </span>
                      <span className={`admin-analytics-badge ${badgeClass}`}>
                        {pct}%
                      </span>
                    </div>

                    <div
                      className="admin-analytics-bar-bg"
                      role="progressbar"
                      aria-valuenow={pct}
                      aria-valuemin="0"
                      aria-valuemax="100"
                    >
                      <div
                        className="admin-analytics-bar-fill"
                        style={{
                          width: `${Math.min(100, Math.max(0, pct))}%`,
                          backgroundColor: barColor,
                        }}
                      />
                    </div>

                    <div className="admin-analytics-meta">
                      <span>
                        {c.faculty?.name
                          ? `Faculty: ${c.faculty.name}`
                          : `Sec ${c.section || "A"}`}
                      </span>
                      <span>
                        {c.total_present || 0} / {totalAtt} attended (
                        {c.total_sessions || 0} sessions)
                      </span>
                    </div>
                  </div>
                );
              })}

              <Link
                to="/admin/attendance-reports"
                className="admin-btn-primary"
                style={{ marginTop: "4px", justifyContent: "center" }}
              >
                <span>View Full Analytics</span>
                <ArrowRight size={13} />
              </Link>
            </div>
          )}
        </section>

        {/* Panel 2: Current Status */}
        <section className="admin-panel admin-current-status-panel">
          <div className="admin-panel-top">
            <div className="admin-panel-title-area">
              <span className="admin-status-dot-icon">
                <CheckCircle2 size={18} className="text-green" />
              </span>
              <div>
                <h2>Current Status</h2>
              </div>
            </div>
            <div className="admin-status-badges">
              <span className="admin-badge-green">
                <Check size={11} /> Attendance
              </span>
            </div>
          </div>

          <div className="admin-status-body">
            <div className="admin-donut-wrapper">
              <div
                className="admin-donut-chart"
                style={{
                  background: hasAttendanceData
                    ? `conic-gradient(#10b981 0% ${attendancePercentage}%, #e2e8f0 ${attendancePercentage}% 100%)`
                    : "#e2e8f0",
                }}
              >
                <div className="admin-donut-inner">
                  <strong>
                    {attendancePercentage !== null ? `${attendancePercentage}%` : "N/A"}
                  </strong>
                </div>
              </div>

              <div className="admin-donut-meta">
                <div className="admin-status-indicator">
                  <CheckCircle2 size={15} className="text-green" />
                  <strong>
                    {hasAttendanceData ? "Attendance available" : "No attendance records"}
                  </strong>
                </div>
                <p>
                  {hasAttendanceData
                    ? `${presentAttendance} present and ${absentAttendance} absent attendance records.`
                    : "Verified attendance records are not available yet."}
                </p>
              </div>
            </div>

            <Link to="/admin/attendance-reports" className="admin-btn-primary admin-btn-status">
              <span>View attendance reports</span>
              <ArrowRight size={13} />
            </Link>
          </div>
        </section>

        {/* Panel 3: Quick Actions */}
        <section className="admin-panel admin-quick-actions-panel">
          <div className="admin-panel-top">
            <div className="admin-panel-title-area">
              <Zap size={18} className="text-blue" />
              <div>
                <h2>Quick Actions</h2>
                <p>Quickly access common administration sections</p>
              </div>
            </div>
          </div>

          <div className="admin-quick-links-list">
            <Link to="/admin/students" className="admin-action-item">
              <div className="admin-action-icon action-icon-green">
                <Users size={16} />
              </div>
              <div className="admin-action-text">
                <strong>Students</strong>
                <span>View and manage registered students</span>
              </div>
              <ChevronRight size={14} className="admin-action-chevron" />
            </Link>

            <Link to="/admin/faculty" className="admin-action-item">
              <div className="admin-action-icon action-icon-blue">
                <FontAwesomeIcon icon={faChalkboardUser} />
              </div>
              <div className="admin-action-text">
                <strong>Faculty</strong>
                <span>View and manage faculty members</span>
              </div>
              <ChevronRight size={14} className="admin-action-chevron" />
            </Link>

            <Link to="/admin/academic-management" className="admin-action-item">
              <div className="admin-action-icon action-icon-purple">
                <BookOpen size={16} />
              </div>
              <div className="admin-action-text">
                <strong>Academic Management</strong>
                <span>View courses and academic structure</span>
              </div>
              <ChevronRight size={14} className="admin-action-chevron" />
            </Link>

            <Link to="/admin/attendance-reports" className="admin-action-item">
              <div className="admin-action-icon action-icon-orange">
                <BarChart3 size={16} />
              </div>
              <div className="admin-action-text">
                <strong>Attendance Reports</strong>
                <span>Review attendance records</span>
              </div>
              <ChevronRight size={14} className="admin-action-chevron" />
            </Link>
          </div>
        </section>
      </div>

      {/* =========================
          BOTTOM 3-COLUMN SECTION
      ========================== */}
      <div className="admin-bottom-grid">
        {/* Column 1: Quick Stats */}
        <section className="admin-panel admin-quick-stats-panel">
          <div className="admin-panel-top">
            <div className="admin-panel-title-area">
              <Sparkles size={18} className="text-blue" />
              <div>
                <h2>Quick Stats</h2>
                <p>Key metrics at a glance</p>
              </div>
            </div>
          </div>

          <div className="admin-quick-stats-2x2">
            <div className="admin-mini-stat-card mini-stat-courses">
              <div className="admin-mini-stat-content">
                <div className="admin-mini-stat-icon-wrapper mini-icon-blue">
                  <BookOpen size={15} />
                </div>
                <div className="admin-mini-stat-details">
                  <span className="admin-mini-stat-label">Total Courses</span>
                  <strong className="admin-mini-stat-value">
                    {formatMetric(totalCourses)}
                  </strong>
                  <span className="admin-mini-stat-sub">Courses in system</span>
                </div>
              </div>
            </div>

            <div className="admin-mini-stat-card mini-stat-students">
              <div className="admin-mini-stat-content">
                <div className="admin-mini-stat-icon-wrapper mini-icon-green">
                  <Users size={15} />
                </div>
                <div className="admin-mini-stat-details">
                  <span className="admin-mini-stat-label">Total Students</span>
                  <strong className="admin-mini-stat-value">
                    {formatMetric(totalStudents)}
                  </strong>
                  <span className="admin-mini-stat-sub">Registered students</span>
                </div>
              </div>
            </div>

            <div className="admin-mini-stat-card mini-stat-records">
              <div className="admin-mini-stat-content">
                <div className="admin-mini-stat-icon-wrapper mini-icon-purple">
                  <FileText size={15} />
                </div>
                <div className="admin-mini-stat-details">
                  <span className="admin-mini-stat-label">Attendance Records</span>
                  <strong className="admin-mini-stat-value">
                    {formatMetric(totalAttendanceRecords)}
                  </strong>
                  <span className="admin-mini-stat-sub">Verified records</span>
                </div>
              </div>
            </div>

            <div className="admin-mini-stat-card mini-stat-absent">
              <div className="admin-mini-stat-content">
                <div className="admin-mini-stat-icon-wrapper mini-icon-orange">
                  <AlertTriangle size={15} />
                </div>
                <div className="admin-mini-stat-details">
                  <span className="admin-mini-stat-label">Absent Records</span>
                  <strong className="admin-mini-stat-value">
                    {formatMetric(absentAttendance)}
                  </strong>
                  <span className="admin-mini-stat-sub">Attendance data</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Column 2: Recent Activity */}
        <section className="admin-panel admin-recent-activity-panel">
          <div className="admin-panel-top">
            <div className="admin-panel-title-area">
              <Clock size={18} className="admin-panel-header-icon text-blue" />
              <div>
                <h2>Recent Activity</h2>
                <p>Latest system events and operations</p>
              </div>
            </div>
            <Link to="/admin/activity" className="admin-panel-link-badge">
              <span>View All</span>
              <ExternalLink size={11} />
            </Link>
          </div>

          {activityLoading ? (
            <div className="admin-panel-inner-box admin-activity-loading-box">
              <div className="admin-activity-spinner" />
              <p>Loading recent activities...</p>
            </div>
          ) : activityError ? (
            <div className="admin-panel-inner-box admin-activity-error-box">
              <div className="admin-empty-icon-circle orange-circle">
                <AlertTriangle size={24} />
              </div>
              <h3>Failed to load activity</h3>
              <p>{activityError}</p>
              <button
                type="button"
                className="admin-btn-outline"
                onClick={handleRetryActivity}
              >
                <RotateCw size={12} className={activityLoading ? "spin" : ""} />
                <span>Retry</span>
              </button>
            </div>
          ) : recentActivities.length === 0 ? (
            <div className="admin-panel-inner-box">
              <div className="admin-empty-icon-circle blue-circle">
                <Clock size={24} />
              </div>
              <h3>No recent activity</h3>
              <p>No system activity has been recorded yet.</p>
              <Link to="/admin/activity" className="admin-btn-outline">
                <span>Open activity logs</span>
                <ExternalLink size={12} />
              </Link>
            </div>
          ) : (
            <div className="admin-activity-container">
              <div className="admin-activity-list">
                {recentActivities.slice(0, 4).map((item) => {
                  const iconConfig = getActivityIconConfig(item.action_type);
                  return (
                    <div key={item.id} className="admin-activity-row">
                      <div className={`admin-activity-icon ${iconConfig.bgClass}`}>
                        {iconConfig.icon}
                      </div>
                      <div className="admin-activity-content">
                        <p className="admin-activity-desc" title={item.description}>
                          {item.description}
                        </p>
                        <div className="admin-activity-meta">
                          {item.actor_name && (
                            <span className="admin-activity-actor">
                              {item.actor_name}
                            </span>
                          )}
                          {item.actor_name && (
                            <span className="admin-activity-dot">•</span>
                          )}
                          <span
                            className="admin-activity-time"
                            title={item.created_at || ""}
                          >
                            {formatActivityTime(item.created_at)}
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="admin-activity-footer">
                <Link to="/admin/activity" className="admin-activity-view-all-link">
                  <span>Open activity logs</span>
                  <ArrowRight size={13} />
                </Link>
              </div>
            </div>
          )}
        </section>

        {/* Column 3: Faculty Help + System Status */}
        <div className="admin-right-column">
          <section className="admin-panel admin-help-panel">
            <div className="admin-panel-top">
              <div className="admin-panel-title-area">
                <div className="admin-help-icon-wrapper">
                  <Headphones size={18} />
                </div>
                <div>
                  <h2>Faculty Help</h2>
                </div>
              </div>
            </div>

            <div className="admin-help-content">
              <p>
                If your courses, timetable, or attendance data are missing,
                contact your administrator to verify the relevant records.
              </p>
              <Link to="/admin/faculty" className="admin-btn-outline-blue">
                <span>View faculty profile</span>
                <ArrowRight size={13} />
              </Link>
            </div>
          </section>

          <div className="admin-system-status-card">
            <div className="admin-system-status-left">
              <div className="admin-status-badge-circle">
                <Check size={14} />
              </div>
              <div className="admin-status-text">
                <strong>System Status</strong>
                <span>All systems are connected and active.</span>
              </div>
            </div>
            <ChevronRight size={16} className="admin-status-chevron" />
          </div>
        </div>
      </div>
    </section>
  );
}

export default AdminDashboard;
