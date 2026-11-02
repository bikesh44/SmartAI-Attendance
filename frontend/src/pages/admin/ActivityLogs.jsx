import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Clock,
  ArrowLeft,
  RotateCw,
  Filter,
  Shield,
  User,
  CheckCircle2,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  LogIn,
  UserPlus,
  UserX,
  UserCheck,
  Building2,
  BookOpen,
  Calendar,
  Layers,
  GraduationCap,
} from "lucide-react";

import { getActivityLogs } from "../../services/adminService";
import { formatActivityTime } from "../../utils/dateUtils";
import "./ActivityLogs.css";

const ACTION_FILTER_OPTIONS = [
  { value: "", label: "All Activity Types" },
  { value: "USER_LOGIN", label: "User Login" },
  { value: "USER_CREATED", label: "User Created" },
  { value: "USER_UPDATED", label: "User Updated" },
  { value: "USER_DEACTIVATED", label: "User Deactivated" },
  { value: "USER_REACTIVATED", label: "User Reactivated" },
  { value: "USER_DELETED", label: "User Deleted" },
  { value: "STUDENT_CREATED", label: "Student Created" },
  { value: "FACULTY_CREATED", label: "Faculty Created" },
  { value: "COURSE_CREATED", label: "Course Created" },
  { value: "DEPARTMENT_CREATED", label: "Department Created" },
  { value: "DEPARTMENT_UPDATED", label: "Department Updated" },
  { value: "TIMETABLE_IMPORTED", label: "Timetable Imported" },
  { value: "ATTENDANCE_SESSION_CREATED", label: "Attendance Session" },
  { value: "ENROLLMENT_BULK_CREATED", label: "Enrollment Created" },
  { value: "ENROLLMENT_DELETED", label: "Enrollment Removed" },
];

function getActionBadgeConfig(actionType = "") {
  const type = String(actionType).toUpperCase();

  if (type.includes("LOGIN")) {
    return {
      className: "badge-blue",
      icon: <LogIn size={13} />,
      label: "Login",
    };
  }
  if (type.includes("DEACTIVATE") || type.includes("DELETE")) {
    return {
      className: "badge-red",
      icon: <UserX size={13} />,
      label: type.replace("_", " "),
    };
  }
  if (type.includes("REACTIVATE")) {
    return {
      className: "badge-amber",
      icon: <UserCheck size={13} />,
      label: "Reactivated",
    };
  }
  if (type.includes("STUDENT")) {
    return {
      className: "badge-green",
      icon: <GraduationCap size={13} />,
      label: "Student",
    };
  }
  if (type.includes("FACULTY")) {
    return {
      className: "badge-indigo",
      icon: <User size={13} />,
      label: "Faculty",
    };
  }
  if (type.includes("DEPARTMENT")) {
    return {
      className: "badge-purple",
      icon: <Building2 size={13} />,
      label: "Department",
    };
  }
  if (type.includes("TIMETABLE")) {
    return {
      className: "badge-blue",
      icon: <Calendar size={13} />,
      label: "Timetable",
    };
  }
  if (type.includes("ATTENDANCE")) {
    return {
      className: "badge-green",
      icon: <CheckCircle2 size={13} />,
      label: "Attendance",
    };
  }
  if (type.includes("COURSE") || type.includes("ENROLLMENT")) {
    return {
      className: "badge-purple",
      icon: <BookOpen size={13} />,
      label: "Academic",
    };
  }
  if (type.includes("USER")) {
    return {
      className: "badge-indigo",
      icon: <UserPlus size={13} />,
      label: "User",
    };
  }
  return {
    className: "badge-slate",
    icon: <Layers size={13} />,
    label: actionType || "Event",
  };
}

function ActivityLogs() {
  const [logs, setLogs] = useState([]);
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 15,
    total: 0,
    pages: 1,
  });
  const [selectedActionType, setSelectedActionType] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchLogs = useCallback(async (page = 1, actionType = selectedActionType) => {
    setLoading(true);
    setError("");

    try {
      const params = {
        page,
        limit: 15,
      };
      if (actionType) {
        params.action_type = actionType;
      }

      const response = await getActivityLogs(params);

      if (!response?.success) {
        throw new Error(response?.message || "Failed to load activity logs.");
      }

      setLogs(response.data || []);
      if (response.pagination) {
        setPagination(response.pagination);
      }
    } catch (err) {
      setError(
        err?.response?.data?.message ||
          err?.message ||
          "Unable to load activity logs."
      );
      setLogs([]);
    } finally {
      setLoading(false);
    }
  }, [selectedActionType]);

  useEffect(() => {
    const timerId = setTimeout(() => {
      fetchLogs(1, selectedActionType);
    }, 0);

    return () => clearTimeout(timerId);
  }, [fetchLogs, selectedActionType]);

  const handlePageChange = (newPage) => {
    if (newPage < 1 || newPage > pagination.pages || newPage === pagination.page) {
      return;
    }
    fetchLogs(newPage, selectedActionType);
  };

  const handleActionFilterChange = (e) => {
    const value = e.target.value;
    setSelectedActionType(value);
    fetchLogs(1, value);
  };

  const handleRefresh = () => {
    fetchLogs(pagination.page, selectedActionType);
  };

  const startRecord = pagination.total === 0 ? 0 : (pagination.page - 1) * pagination.limit + 1;
  const endRecord = Math.min(pagination.page * pagination.limit, pagination.total);

  return (
    <div className="activity-logs-page">
      {/* Top Header / Breadcrumb */}
      <div className="activity-logs-header">
        <div className="activity-header-left">
          <Link to="/admin/dashboard" className="activity-back-link">
            <ArrowLeft size={16} />
            <span>Back to Dashboard</span>
          </Link>
          <div className="activity-title-group">
            <div className="activity-icon-container">
              <Shield size={22} />
            </div>
            <div>
              <h1>System Activity & Audit Logs</h1>
              <p>
                Comprehensive audit trail of security events, administrative updates,
                and user activities across the platform.
              </p>
            </div>
          </div>
        </div>

        <div className="activity-header-actions">
          <button
            type="button"
            className="activity-btn-refresh"
            onClick={handleRefresh}
            disabled={loading}
            title="Refresh activity logs"
          >
            <RotateCw size={15} className={loading ? "spin" : ""} />
            <span>{loading ? "Refreshing..." : "Refresh"}</span>
          </button>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="activity-filter-bar">
        <div className="activity-filter-item">
          <Filter size={15} className="activity-filter-icon" />
          <select
            value={selectedActionType}
            onChange={handleActionFilterChange}
            className="activity-filter-select"
            aria-label="Filter by activity type"
          >
            {ACTION_FILTER_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div className="activity-filter-summary">
          <span>
            Total recorded events: <strong>{pagination.total}</strong>
          </span>
        </div>
      </div>

      {/* Main Table Card */}
      <div className="activity-table-card">
        {error && (
          <div className="activity-error-banner">
            <AlertCircle size={18} />
            <div className="activity-error-text">
              <strong>Unable to load activity logs</strong>
              <p>{error}</p>
            </div>
            <button
              type="button"
              className="activity-btn-retry"
              onClick={handleRefresh}
            >
              Retry
            </button>
          </div>
        )}

        {loading ? (
          <div className="activity-loading-state">
            <div className="activity-spinner" />
            <p>Loading activity logs from database...</p>
          </div>
        ) : logs.length === 0 ? (
          <div className="activity-empty-state">
            <div className="activity-empty-icon-circle">
              <Clock size={28} />
            </div>
            <h3>No activity logs found</h3>
            <p>
              {selectedActionType
                ? "No recorded events match the selected activity filter."
                : "No system activities have been recorded yet."}
            </p>
          </div>
        ) : (
          <div className="activity-table-container">
            <table className="activity-data-table">
              <thead>
                <tr>
                  <th style={{ width: "160px" }}>Timestamp</th>
                  <th style={{ width: "160px" }}>Action</th>
                  <th>Activity Description</th>
                  <th style={{ width: "160px" }}>Actor</th>
                  <th style={{ width: "130px" }}>Target</th>
                  <th style={{ width: "90px" }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => {
                  const badge = getActionBadgeConfig(log.action_type);
                  return (
                    <tr key={log.id} className="activity-table-row">
                      <td className="activity-time-cell" title={log.created_at || ""}>
                        <div className="activity-time-wrapper">
                          <Clock size={12} className="activity-clock-icon" />
                          <span>{formatActivityTime(log.created_at)}</span>
                        </div>
                      </td>

                      <td>
                        <span className={`activity-badge ${badge.className}`}>
                          {badge.icon}
                          <span>{badge.label}</span>
                        </span>
                      </td>

                      <td className="activity-desc-cell">
                        <span className="activity-desc-text">{log.description}</span>
                      </td>

                      <td>
                        <div className="activity-actor-cell">
                          <span className="activity-actor-name">
                            {log.actor_name || "System"}
                          </span>
                          {log.actor_role && (
                            <span className="activity-actor-role">
                              {log.actor_role}
                            </span>
                          )}
                        </div>
                      </td>

                      <td>
                        {log.entity_type ? (
                          <span className="activity-entity-tag">
                            {log.entity_type} {log.entity_id ? `#${log.entity_id}` : ""}
                          </span>
                        ) : (
                          <span className="activity-entity-none">—</span>
                        )}
                      </td>

                      <td>
                        {log.status === "SUCCESS" ? (
                          <span className="activity-status-success">
                            <CheckCircle2 size={13} />
                            <span>Success</span>
                          </span>
                        ) : (
                          <span className="activity-status-failed">
                            <AlertCircle size={13} />
                            <span>{log.status || "Failed"}</span>
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Footer */}
        {!loading && pagination.total > 0 && (
          <div className="activity-pagination-footer">
            <span className="activity-page-info">
              Showing <strong>{startRecord}</strong> - <strong>{endRecord}</strong> of{" "}
              <strong>{pagination.total}</strong> records
            </span>

            <div className="activity-page-controls">
              <button
                type="button"
                className="activity-page-btn"
                onClick={() => handlePageChange(pagination.page - 1)}
                disabled={pagination.page <= 1}
                aria-label="Previous page"
              >
                <ChevronLeft size={16} />
                <span>Previous</span>
              </button>

              <span className="activity-current-page-pill">
                Page {pagination.page} of {pagination.pages}
              </span>

              <button
                type="button"
                className="activity-page-btn"
                onClick={() => handlePageChange(pagination.page + 1)}
                disabled={pagination.page >= pagination.pages}
                aria-label="Next page"
              >
                <span>Next</span>
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default ActivityLogs;
