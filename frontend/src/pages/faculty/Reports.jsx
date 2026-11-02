
import { useEffect, useMemo, useState } from "react";

import {
  getFacultyAttendanceAnalytics,
  getFacultyAttendanceReports,
  exportFacultyAttendanceReport,
} from "../../services/reportService";

import { faXmark } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

import "./Reports.css";

const EMPTY_METRICS = {
  overallAttendance: null,
  totalStudents: null,
  totalSessions: null,
  totalPresent: null,
  totalAbsent: null,
  lowAttendance: null,
};

const statuses = ["All", "Present", "Absent"];

const formatMetric = (value) => {
  if (value === null || value === undefined) {
    return "N/A";
  }

  return value;
};

const formatPercentage = (value) => {
  if (value === null || value === undefined) {
    return "N/A";
  }

  return `${value}%`;
};

const getInitials = (name = "") => {
  const words = name.trim().split(/\s+/).filter(Boolean);

  if (!words.length) {
    return "S";
  }

  return words
    .slice(0, 2)
    .map((word) => word[0].toUpperCase())
    .join("");
};

function Reports() {
  const [searchTerm, setSearchTerm] = useState("");

  const [reportStudents, setReportStudents] = useState([]);
  const [classReports, setClassReports] = useState([]);

  const [classOptions, setClassOptions] = useState([
    {
      value: "All Classes",
      label: "All Classes",
    },
  ]);

  const [metricsData, setMetricsData] = useState(EMPTY_METRICS);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [selectedClass, setSelectedClass] = useState("All Classes");

  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const [status, setStatus] = useState("All");

  const [selectedStudent, setSelectedStudent] = useState(null);
  const [showExportModal, setShowExportModal] = useState(false);
  const [exportingFormat, setExportingFormat] = useState(null);
  const [exportError, setExportError] = useState("");

  useEffect(() => {
    let isMounted = true;

    const loadReports = async () => {
      setLoading(true);
      setError("");

      if (dateFrom && dateTo && dateFrom > dateTo) {
        setError("Date From cannot be later than Date To.");
        setReportStudents([]);
        setClassReports([]);
        setMetricsData(EMPTY_METRICS);
        setLoading(false);
        return;
      }

      try {
        const offeringId =
          selectedClass !== "All Classes"
            ? selectedClass
            : undefined;

        const params = {
          offering_id: offeringId,
          from_date: dateFrom || undefined,
          to_date: dateTo || undefined,
        };

        const [analyticsResponse, reportsResponse] =
          await Promise.all([
            getFacultyAttendanceAnalytics(params),
            getFacultyAttendanceReports(params),
          ]);

        if (!isMounted) {
          return;
        }

        const analyticsData = analyticsResponse?.data || {};
        const reportsData = reportsResponse?.data || [];

        const lowAttendanceCount =
          analyticsData.low_attendance_students ??
          reportsData.reduce(
            (total, report) =>
              total +
              (report.students || []).filter(
                (student) => student.is_low_attendance === true
              ).length,
            0
          );

        setMetricsData({
          overallAttendance:
            analyticsData.overall_attendance_percentage ?? null,

          totalStudents: analyticsData.total_students ?? null,

          totalSessions: analyticsData.total_sessions ?? null,

          totalPresent: analyticsData.total_present ?? null,

          totalAbsent: analyticsData.total_absent ?? null,

          lowAttendance: lowAttendanceCount,
        });

        const courses = analyticsData.courses || [];

        setClassOptions([
          {
            value: "All Classes",
            label: "All Classes",
          },
          ...courses.map((course) => ({
            value: String(course.offering_id),
            label: `${course.course_code} - ${course.section}`,
          })),
        ]);

        const students = reportsData.flatMap((report) =>
          (report.students || []).map((student) => ({
            id: `${report.offering_id}-${student.student_id}`,

            studentId:
              student.enrollment_no || String(student.student_id),

            studentName: student.student_name || "N/A",

            className: `${report.course_code} - ${report.section}`,

            sessions: student.total_sessions ?? null,

            present: student.present_sessions ?? null,

            absent: student.absent_sessions ?? null,

            attendanceRate: student.attendance_percentage ?? null,

            isLowAttendance: student.is_low_attendance ?? null,

            email: student.email || "",

            offeringId: String(report.offering_id),
          }))
        );

        const classData = courses.map((course) => ({
          id: course.offering_id,

          className: `${course.course_code} - ${course.section}`,

          students: course.students ?? null,

          sessions: course.total_sessions ?? null,

          attendanceRate: course.attendance_percentage ?? null,

          courseCode: course.course_code,

          courseName: course.course_name,

          offeringId: String(course.offering_id),
        }));

        setReportStudents(students);
        setClassReports(classData);
      } catch (requestError) {
        if (!isMounted) {
          return;
        }

        console.error(
          "Failed to load faculty reports:",
          requestError
        );

        setError(
          requestError?.response?.data?.message ||
            "Unable to load attendance reports."
        );

        setReportStudents([]);
        setClassReports([]);
        setMetricsData(EMPTY_METRICS);
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    loadReports();

    return () => {
      isMounted = false;
    };
  }, [selectedClass, dateFrom, dateTo]);

  const filteredStudents = useMemo(() => {
    const normalizedSearch = searchTerm.trim().toLowerCase();

    return reportStudents.filter((student) => {
      const matchesSearch =
        !normalizedSearch ||
        student.studentId?.toLowerCase().includes(normalizedSearch) ||
        student.studentName?.toLowerCase().includes(normalizedSearch);

      const matchesClass =
        selectedClass === "All Classes" ||
        String(student.offeringId) === String(selectedClass);

      const presentCount = Number(student.present ?? 0);
      const absentCount = Number(student.absent ?? 0);

      const matchesStatus =
        status === "All" ||
        (status === "Present" && presentCount > 0) ||
        (status === "Absent" && absentCount > 0);

      return matchesSearch && matchesClass && matchesStatus;
    });
  }, [reportStudents, searchTerm, selectedClass, status]);

  const clearFilters = () => {
    setSearchTerm("");
    setSelectedClass("All Classes");
    setDateFrom("");
    setDateTo("");
    setStatus("All");
  };

  const hasFilters =
    Boolean(searchTerm) ||
    selectedClass !== "All Classes" ||
    Boolean(dateFrom) ||
    Boolean(dateTo) ||
    status !== "All";

  const invalidDateRange = Boolean(
    dateFrom && dateTo && dateFrom > dateTo
  );

  const handleExport = async (format) => {
    if (exportingFormat) return;
    setExportingFormat(format);
    setExportError("");

    try {
      const offeringId =
        selectedClass !== "All Classes" ? selectedClass : undefined;
      const params = {
        format,
        offering_id: offeringId,
        from_date: dateFrom || undefined,
        to_date: dateTo || undefined,
        status: status !== "All" ? status : undefined,
        search: searchTerm.trim() || undefined,
      };

      const response = await exportFacultyAttendanceReport(params);

      let filename = `Faculty_Attendance_Report_${new Date().toISOString().slice(0, 10)}.${format}`;
      const disposition =
        response.headers?.["content-disposition"] ||
        response.headers?.get?.("content-disposition");
      if (disposition) {
        const match = disposition.match(/filename\*?=['"]?(?:UTF-\d['"])?([^;\r\n'"]*)['"]?/i);
        if (match && match[1]) {
          filename = match[1];
        }
      }

      const mimeType =
        format === "pdf"
          ? "application/pdf"
          : format === "xlsx"
          ? "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          : "text/csv;charset=utf-8;";

      const blob = new Blob([response.data], { type: mimeType });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      setShowExportModal(false);
    } catch (err) {
      console.error("Export failed:", err);
      let message = "Failed to export report. Please try again.";
      if (err?.response?.data instanceof Blob) {
        try {
          const text = await err.response.data.text();
          const json = JSON.parse(text);
          if (json.message) message = json.message;
        } catch {
          // fallback message
        }
      } else if (err?.response?.data?.message) {
        message = err.response.data.message;
      }
      setExportError(message);
    } finally {
      setExportingFormat(null);
    }
  };

  const metrics = [
    {
      label: "Overall Attendance",
      value: formatPercentage(metricsData.overallAttendance),
      tone: "blue",
      icon: (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path
            d="M4 19V5M4 19h17"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
          <path
            d="m7 15 4-4 3 2 5-6"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      ),
    },
    {
      label: "Total Students",
      value: formatMetric(metricsData.totalStudents),
      tone: "purple",
      icon: (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path
            d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
          <circle
            cx="9"
            cy="7"
            r="4"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
          />
          <path
            d="M16 3.5a4 4 0 0 1 0 7.8"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </svg>
      ),
    },
    {
      label: "Total Sessions",
      value: formatMetric(metricsData.totalSessions),
      tone: "green",
      icon: (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <rect
            x="3"
            y="4"
            width="18"
            height="17"
            rx="2"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
          />
          <path
            d="M8 2v4M16 2v4M3 9h18"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </svg>
      ),
    },
    {
      label: "Low Attendance",
      value: formatMetric(metricsData.lowAttendance),
      tone: "orange",
      icon: (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path
            d="M12 3 22 20H2L12 3Z"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinejoin="round"
          />
          <path
            d="M12 9v5M12 17v.5"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </svg>
      ),
    },
  ];

  return (
    <div className="faculty-reports-page">
      <section className="reports-page-header">
        <div>
          <span className="reports-eyebrow">FACULTY PORTAL</span>

          <h1>Reports</h1>

          <p>
            Analyze attendance performance for your assigned classes
            and generate attendance reports.
          </p>
        </div>

        <button
          type="button"
          className="reports-primary-button"
          onClick={() => setShowExportModal(true)}
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path
              d="M12 3v12M7 10l5 5 5-5M5 21h14"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          Export Report
        </button>
      </section>

      <section className="reports-metrics-grid">
        {metrics.map((metric) => (
          <article className="reports-metric-card" key={metric.label}>
            <div className={`reports-metric-icon ${metric.tone}`}>
              {metric.icon}
            </div>

            <div className="reports-metric-content">
              <span>{metric.label}</span>
              <strong>{loading ? "..." : metric.value}</strong>
            </div>
          </article>
        ))}
      </section>

      <section className="reports-section">
        <div className="reports-section-heading">
          <div>
            <h2>Report Filters</h2>
            <p>Filter attendance information by student, class, and date.</p>
          </div>
        </div>

        <div className="reports-filters-card">
          <div className="reports-filter reports-search-filter">
            <label htmlFor="report-search">Search Student</label>

            <div className="reports-search-wrapper">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <circle
                  cx="11"
                  cy="11"
                  r="7"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                />
                <path
                  d="m20 20-4-4"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                />
              </svg>

              <input
                id="report-search"
                type="search"
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                placeholder="Search by student ID or name..."
              />
            </div>
          </div>

          <div className="reports-filter">
            <label htmlFor="report-class">Class</label>

            <select
              id="report-class"
              value={selectedClass}
              onChange={(event) => setSelectedClass(event.target.value)}
            >
              {classOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div className="reports-filter">
            <label htmlFor="report-date-from">Date From</label>

            <input
              id="report-date-from"
              type="date"
              value={dateFrom}
              max={dateTo || undefined}
              aria-invalid={invalidDateRange}
              onChange={(event) => setDateFrom(event.target.value)}
            />
          </div>

          <div className="reports-filter">
            <label htmlFor="report-date-to">Date To</label>

            <input
              id="report-date-to"
              type="date"
              value={dateTo}
              min={dateFrom || undefined}
              aria-invalid={invalidDateRange}
              onChange={(event) => setDateTo(event.target.value)}
            />
          </div>

          <div className="reports-filter">
            <label htmlFor="report-status">Status</label>

            <select
              id="report-status"
              value={status}
              onChange={(event) => setStatus(event.target.value)}
            >
              {statuses.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            className="reports-clear-button"
            onClick={clearFilters}
            disabled={!hasFilters}
          >
            <span aria-hidden="true">↻</span>
            Clear Filters
          </button>
        </div>
      </section>

      {error && (
        <section className="reports-integration-notice">
          <div className="reports-notice-icon">!</div>
          <div>
            <strong>Unable to load reports</strong>
            <p>{error}</p>
          </div>
        </section>
      )}

      <section className="reports-overview-card">
        <div className="reports-overview-header">
          <div>
            <h2>Attendance Overview</h2>
            <p>Attendance distribution across your assigned classes.</p>
          </div>

          <span className="reports-data-badge">Backend Data</span>
        </div>

        <div className="reports-overview-grid">
          <div className="reports-overview-main">
            <span>Overall Attendance</span>

            <strong>
              {loading
                ? "..."
                : formatPercentage(metricsData.overallAttendance)}
            </strong>

            <div className="reports-progress-track">
              <div
                className="reports-progress-fill"
                style={{
                  width:
                    metricsData.overallAttendance !== null
                      ? `${Math.min(
                          Math.max(
                            Number(metricsData.overallAttendance),
                            0
                          ),
                          100
                        )}%`
                      : "0%",
                }}
              />
            </div>
          </div>

          <div className="reports-overview-stat">
            <span className="reports-stat-dot present" />
            <div>
              <small>Present</small>
              <strong>
                {loading
                  ? "..."
                  : formatMetric(metricsData.totalPresent)}
              </strong>
            </div>
          </div>

          <div className="reports-overview-stat">
            <span className="reports-stat-dot absent" />
            <div>
              <small>Absent</small>
              <strong>
                {loading
                  ? "..."
                  : formatMetric(metricsData.totalAbsent)}
              </strong>
            </div>
          </div>

          <div className="reports-overview-stat">
            <span className="reports-stat-dot late" />
            <div>
              <small>Late</small>
              <strong>N/A</strong>
            </div>
          </div>
        </div>
      </section>

      <section className="reports-section">
        <div className="reports-section-heading">
          <div>
            <h2>Student Attendance</h2>
            <p>Attendance summary for students in your assigned classes.</p>
          </div>
        </div>

        <div className="reports-table-card">
          {loading ? (
            <div className="reports-empty-state">
              <div className="reports-empty-icon">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    d="M5 4h14v16H5z"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinejoin="round"
                  />
                  <path
                    d="M8 8h8M8 12h8M8 16h5"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                  />
                </svg>
              </div>
              <h3>Loading attendance reports</h3>
              <p>Fetching attendance data from the backend.</p>
            </div>
          ) : reportStudents.length === 0 ? (
            <div className="reports-empty-state">
              <div className="reports-empty-icon">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    d="M5 4h14v16H5z"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinejoin="round"
                  />
                  <path
                    d="M8 8h8M8 12h8M8 16h5"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                  />
                </svg>
              </div>
              <h3>No attendance reports available</h3>
              <p>
                No student attendance data was returned for the selected
                filters.
              </p>
            </div>
          ) : filteredStudents.length === 0 ? (
            <div className="reports-empty-state compact">
              <div className="reports-empty-icon">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <circle
                    cx="11"
                    cy="11"
                    r="7"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                  />
                  <path
                    d="m20 20-4-4"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                  />
                </svg>
              </div>
              <h3>No matching reports</h3>
              <p>Try changing your search or filters.</p>
            </div>
          ) : (
            <div className="reports-table-wrapper">
              <table className="reports-table">
                <thead>
                  <tr>
                    <th>Student</th>
                    <th>Student ID</th>
                    <th>Class</th>
                    <th>Sessions</th>
                    <th>Present</th>
                    <th>Absent</th>
                    <th>Late</th>
                    <th>Attendance</th>
                    <th>Action</th>
                  </tr>
                </thead>

                <tbody>
                  {filteredStudents.map((student) => (
                    <tr key={student.id}>
                      <td>
                        <div className="reports-student">
                          <div className="reports-student-avatar">
                            {getInitials(student.studentName)}
                          </div>
                          <strong>{student.studentName}</strong>
                        </div>
                      </td>

                      <td>{student.studentId || "N/A"}</td>
                      <td>{student.className || "N/A"}</td>
                      <td>{student.sessions ?? "N/A"}</td>
                      <td>{student.present ?? "N/A"}</td>
                      <td>{student.absent ?? "N/A"}</td>
                      <td>N/A</td>
                      <td>{formatPercentage(student.attendanceRate)}</td>

                      <td>
                        <button
                          type="button"
                          className="reports-view-button"
                          onClick={() => setSelectedStudent(student)}
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="reports-list-footer">
          <span>
            Showing {filteredStudents.length} of {reportStudents.length}{" "}
            students
          </span>

          <div className="reports-pagination">
            <button type="button" disabled>
              ‹ Previous
            </button>
            <button type="button" className="active" disabled>
              1
            </button>
            <button type="button" disabled>
              Next ›
            </button>
          </div>
        </div>
      </section>

      <section className="reports-section">
        <div className="reports-section-heading">
          <div>
            <h2>Class-wise Attendance</h2>
            <p>Attendance summary across your assigned classes.</p>
          </div>
        </div>

        <div className="reports-table-card class-report-card">
          {loading ? (
            <div className="reports-empty-state compact">
              <h3>Loading class reports</h3>
              <p>Fetching class analytics from the backend.</p>
            </div>
          ) : classReports.length === 0 ? (
            <div className="reports-empty-state compact">
              <div className="reports-empty-icon">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    d="M4 5h16v14H4z"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinejoin="round"
                  />
                  <path
                    d="M8 9h8M8 13h5"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                  />
                </svg>
              </div>
              <h3>No class reports available</h3>
              <p>
                No class attendance summaries were returned for the selected
                filters.
              </p>
            </div>
          ) : (
            <div className="reports-table-wrapper">
              <table className="reports-table">
                <thead>
                  <tr>
                    <th>Class</th>
                    <th>Students</th>
                    <th>Sessions</th>
                    <th>Attendance</th>
                    <th>Action</th>
                  </tr>
                </thead>

                <tbody>
                  {classReports.map((report) => (
                    <tr key={report.id}>
                      <td>{report.className || "N/A"}</td>
                      <td>{report.students ?? "N/A"}</td>
                      <td>{report.sessions ?? "N/A"}</td>
                      <td>{formatPercentage(report.attendanceRate)}</td>

                      <td>
                        <button
                          type="button"
                          className="reports-view-button"
                          onClick={() => {
                            setSelectedClass(String(report.offeringId));
                            setStatus("All");
                            setSearchTerm("");
                          }}
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>

      {showExportModal && (
        <div
          className="reports-modal-backdrop"
          onMouseDown={() => setShowExportModal(false)}
        >
          <div
            className="reports-modal"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="reports-modal-header">
              <div>
                <span className="reports-eyebrow">REPORTS</span>
                <h2>Export Report</h2>
              </div>

              <button
                type="button"
                className="reports-modal-close"
                onClick={() => setShowExportModal(false)}
                aria-label="Close"
              >
                <FontAwesomeIcon icon={faXmark} />
              </button>
            </div>

            <div className="reports-modal-body">
              <p>
                Export the currently filtered attendance report in your preferred format.
              </p>

              <div className="reports-export-options">
                <button
                  type="button"
                  onClick={() => handleExport("csv")}
                  disabled={Boolean(exportingFormat) || filteredStudents.length === 0}
                  className={exportingFormat === "csv" ? "exporting" : ""}
                >
                  {exportingFormat === "csv" ? "Exporting CSV..." : "CSV (.csv)"}
                </button>

                <button
                  type="button"
                  onClick={() => handleExport("xlsx")}
                  disabled={Boolean(exportingFormat) || filteredStudents.length === 0}
                  className={exportingFormat === "xlsx" ? "exporting" : ""}
                >
                  {exportingFormat === "xlsx" ? "Exporting Excel..." : "Excel (.xlsx)"}
                </button>

                <button
                  type="button"
                  onClick={() => handleExport("pdf")}
                  disabled={Boolean(exportingFormat) || filteredStudents.length === 0}
                  className={exportingFormat === "pdf" ? "exporting" : ""}
                >
                  {exportingFormat === "pdf" ? "Exporting PDF..." : "PDF (.pdf)"}
                </button>
              </div>

              {exportError ? (
                <div className="reports-export-error" role="alert">
                  {exportError}
                </div>
              ) : (
                <div className="reports-export-info">
                  Export reflects active filters ({filteredStudents.length} student{filteredStudents.length === 1 ? "" : "s"}).
                </div>
              )}
            </div>

            <div className="reports-modal-footer">
              <button
                type="button"
                className="reports-secondary-button"
                onClick={() => setShowExportModal(false)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {selectedStudent && (
        <div
          className="reports-modal-backdrop"
          onMouseDown={() => setSelectedStudent(null)}
        >
          <div
            className="reports-modal"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="reports-modal-header">
              <div>
                <span className="reports-eyebrow">STUDENT REPORT</span>
                <h2>Attendance Report</h2>
              </div>

              <button
                type="button"
                className="reports-modal-close"
                onClick={() => setSelectedStudent(null)}
                aria-label="Close"
              >
                <FontAwesomeIcon icon={faXmark} />
              </button>
            </div>

            <div className="reports-student-detail">
              <div className="reports-detail-profile">
                <div className="reports-detail-avatar">
                  {getInitials(selectedStudent.studentName)}
                </div>

                <div>
                  <strong>{selectedStudent.studentName || "N/A"}</strong>
                  <span>{selectedStudent.studentId || "N/A"}</span>
                </div>
              </div>

              <div className="reports-detail-grid">
                <div>
                  <span>Class</span>
                  <strong>{selectedStudent.className || "N/A"}</strong>
                </div>

                <div>
                  <span>Total Sessions</span>
                  <strong>{selectedStudent.sessions ?? "N/A"}</strong>
                </div>

                <div>
                  <span>Present</span>
                  <strong>{selectedStudent.present ?? "N/A"}</strong>
                </div>

                <div>
                  <span>Absent</span>
                  <strong>{selectedStudent.absent ?? "N/A"}</strong>
                </div>

                <div>
                  <span>Late</span>
                  <strong>N/A</strong>
                </div>

                <div>
                  <span>Attendance</span>
                  <strong>
                    {formatPercentage(selectedStudent.attendanceRate)}
                  </strong>
                </div>
              </div>
            </div>

            <div className="reports-history-placeholder">
              <strong>Attendance History</strong>
              <p>
                Detailed attendance history is not provided by the current
                faculty reports endpoint.
              </p>
            </div>

            <div className="reports-modal-footer">
              <button
                type="button"
                className="reports-secondary-button"
                onClick={() => setSelectedStudent(null)}
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

export default Reports;
