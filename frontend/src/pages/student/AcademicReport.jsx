import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faGraduationCap,
  faCalendarDays,
  faChartSimple,
  faChartLine,
  faBookOpen,
  faArrowTrendUp,
  faArrowTrendDown,
  faLightbulb,
  faCircleCheck,
  faDownload,
  faFileLines,
  faArrowLeft,
  faChevronRight,
  faCheck,
  faLayerGroup,
  faShieldHalved,
  faTriangleExclamation,
} from "@fortawesome/free-solid-svg-icons";

import {
  getAcademicOverview,
  getSemesterResults,
  getAcademicPerformanceHistory,
  getExaminationRecords,
  getAcademicDocuments,
  exportAcademicReport,
} from "../../services/academicService";
import PageState from "../../components/PageState";
import "./AcademicReport.css";

export default function AcademicReport() {
  const navigate = useNavigate();

  // Active tab: "overview" | "results" | "performance" | "exams" | "documents"
  const [activeTab, setActiveTab] = useState("overview");

  // Loading & error states
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Selected semester filter
  const [selectedSemester, setSelectedSemester] = useState(null);

  // Data states
  const [overviewData, setOverviewData] = useState(null);
  const [resultsData, setResultsData] = useState(null);
  const [performanceHistory, setPerformanceHistory] = useState([]);
  const [examinations, setExaminations] = useState([]);
  const [documents, setDocuments] = useState([]);

  // Export state
  const [exporting, setExporting] = useState(false);
  const [exportSuccess, setExportSuccess] = useState(false);
  const [exportError, setExportError] = useState(null);

  // Chart tooltip state
  const [chartTooltip, setChartTooltip] = useState(null);

  // 1. Initial Load of Overview & History
  useEffect(() => {
    let active = true;

    async function loadInitialData() {
      setLoading(true);
      setError(null);
      try {
        const [overviewRes, historyRes, examsRes, docsRes] = await Promise.all([
          getAcademicOverview(),
          getAcademicPerformanceHistory(),
          getExaminationRecords(),
          getAcademicDocuments(),
        ]);

        if (active) {
          if (overviewRes?.success && overviewRes.data) {
            setOverviewData(overviewRes.data);
            // Default selected semester
            const currentSem = overviewRes.data.student?.current_semester || 1;
            setSelectedSemester(currentSem);
          }
          if (historyRes?.success && historyRes.data) {
            setPerformanceHistory(historyRes.data);
          }
          if (examsRes?.success && examsRes.data) {
            setExaminations(examsRes.data);
          }
          if (docsRes?.success && docsRes.data) {
            setDocuments(docsRes.data);
          }
        }
      } catch (err) {
        if (active) {
          console.error("Error loading academic data:", err);
          setError(err?.response?.data?.message || "Failed to load academic records. Please try again.");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadInitialData();

    return () => {
      active = false;
    };
  }, []);

  // 2. Load Semester-Specific Results when selectedSemester changes
  useEffect(() => {
    if (selectedSemester === null) return;

    let active = true;

    async function loadSemesterData() {
      try {
        const res = await getSemesterResults({ semester: selectedSemester });
        if (active && res?.success && res.data) {
          setResultsData(res.data);
        }
      } catch (err) {
        if (active) {
          console.error("Error loading semester results:", err);
        }
      }
    }

    loadSemesterData();

    return () => {
      active = false;
    };
  }, [selectedSemester]);

  // Handle Export Report (Genuine PDF Grade Card)
  const handleExport = async () => {
    if (exporting) return;
    setExporting(true);
    setExportSuccess(false);
    setExportError(null);
    try {
      const response = await exportAcademicReport({
        semester: selectedSemester || undefined,
        format: "pdf",
      });

      const semLabel = selectedSemester ? `Sem${selectedSemester}` : "All";
      const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, "");
      let filename = `Academic_Grade_Card_${student.enrollment_no || "Student"}_${semLabel}_${dateStr}.pdf`;

      const disposition =
        response.headers?.["content-disposition"] ||
        response.headers?.get?.("content-disposition");
      if (disposition) {
        const match = disposition.match(/filename\*?=['"]?(?:UTF-\d['"])?([^;\r\n'"]*)['"]?/i);
        if (match && match[1]) {
          filename = match[1];
        }
      }

      // Create genuine binary PDF blob and trigger browser download
      const blob = new Blob([response.data], { type: "application/pdf" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      setExportSuccess(true);
      setTimeout(() => setExportSuccess(false), 5000);
    } catch (err) {
      console.error("Export error:", err);
      let errorMsg = "Failed to export academic report. Please try again.";
      if (err?.response?.data instanceof Blob) {
        try {
          const text = await err.response.data.text();
          const json = JSON.parse(text);
          if (json.message) errorMsg = json.message;
        } catch {
          // Fallback to default message
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

  // Extract variables
  const student = overviewData?.student || {};
  const metrics = overviewData?.metrics || {};
  const availableSemesters = overviewData?.available_semesters || [];

  const resultsList = resultsData?.results || [];
  const subjectPerformance = resultsData?.subject_performance || [];
  const insights = resultsData?.insights || [];
  const hasPublishedResults = metrics.has_published_results;

  // Chart Coordinates Calculation
  const chartPoints = useMemo(() => {
    if (!performanceHistory || performanceHistory.length === 0) return null;

    const width = 340;
    const height = 150;
    const paddingLeft = 32;
    const paddingRight = 16;
    const paddingTop = 16;
    const paddingBottom = 24;

    const plotWidth = width - paddingLeft - paddingRight;
    const plotHeight = height - paddingTop - paddingBottom;

    const maxVal = 10;
    const minVal = 0;

    const count = performanceHistory.length;
    const stepX = count > 1 ? plotWidth / (count - 1) : plotWidth / 2;

    const gpaPoints = performanceHistory.map((item, idx) => {
      const x = paddingLeft + (count > 1 ? idx * stepX : plotWidth / 2);
      const val = item.gpa !== null ? item.gpa : 0;
      const y = paddingTop + plotHeight - ((val - minVal) / (maxVal - minVal)) * plotHeight;
      return { x, y, val, sem: item.semester_name };
    });

    const cgpaPoints = performanceHistory.map((item, idx) => {
      const x = paddingLeft + (count > 1 ? idx * stepX : plotWidth / 2);
      const val = item.cgpa !== null ? item.cgpa : 0;
      const y = paddingTop + plotHeight - ((val - minVal) / (maxVal - minVal)) * plotHeight;
      return { x, y, val, sem: item.semester_name };
    });

    const gpaPath = gpaPoints.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
    const cgpaPath = cgpaPoints.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");

    // Area fill under GPA line
    const baselineY = paddingTop + plotHeight;
    const gpaAreaPath =
      gpaPoints.length > 0
        ? `${gpaPath} L ${gpaPoints[gpaPoints.length - 1].x} ${baselineY} L ${gpaPoints[0].x} ${baselineY} Z`
        : "";

    return {
      width,
      height,
      paddingLeft,
      paddingTop,
      plotWidth,
      plotHeight,
      baselineY,
      gpaPoints,
      cgpaPoints,
      gpaPath,
      cgpaPath,
      gpaAreaPath,
      history: performanceHistory,
    };
  }, [performanceHistory]);

  if (loading) {
    return (
      <div className="academic-report-container">
        <PageState type="loading" title="Loading Academic Records" message="Fetching verified academic history..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="academic-report-container">
        <PageState
          type="error"
          title="Unable to Load Academic Records"
          message={error}
          actionLabel="Try Again"
          onAction={() => window.location.reload()}
        />
      </div>
    );
  }

  return (
    <div className="academic-report-container">
      {/* 1. Header Banner */}
      <section className="academic-banner" aria-label="Academic Records Banner">
        <div className="academic-banner-content">
          <div className="academic-banner-icon-box">
            <FontAwesomeIcon icon={faGraduationCap} />
          </div>

          <div className="academic-banner-text">
            <h1 className="academic-banner-title">Academic Records</h1>
            <p className="academic-banner-subtitle">View your semester results and academic progress.</p>
          </div>
        </div>

        <div className="academic-banner-meta">
          <div className="academic-meta-badge">
            <FontAwesomeIcon icon={faCalendarDays} className="academic-meta-icon" />
            <div className="academic-meta-text">
              <span className="academic-meta-label">Academic Year</span>
              <strong className="academic-meta-value">{student.academic_year || "2024 - 2025"}</strong>
            </div>
          </div>

          <div className="academic-meta-badge">
            <FontAwesomeIcon icon={faLayerGroup} className="academic-meta-icon" />
            <div className="academic-meta-text">
              <span className="academic-meta-label">Current Semester</span>
              <strong className="academic-meta-value">
                {student.current_semester_label || "Spring Semester"}
              </strong>
            </div>
          </div>
        </div>
      </section>

      {/* 2. Top 4 KPI Summary Cards */}
      <section className="academic-cards-grid" aria-label="Academic Performance Summary">
        {/* Card 1: Current Semester */}
        <div className="academic-card card-semester">
          <div className="academic-card-header">
            <div className="academic-card-icon icon-blue">
              <FontAwesomeIcon icon={faGraduationCap} />
            </div>
            <div className="academic-card-titles">
              <span className="academic-card-label">Current Semester</span>
              <h2 className="academic-card-value text-blue">
                {student.current_semester_label || `Semester ${student.current_semester || 1}`}
              </h2>
            </div>
          </div>

          <div className="academic-details-grid">
            <div className="academic-detail-item">
              <span className="detail-label">Program</span>
              <span className="detail-value">{student.program || "B.Tech"}</span>
            </div>
            <div className="academic-detail-item">
              <span className="detail-label">Department</span>
              <span className="detail-value">{student.department || "Computer Science"}</span>
            </div>
            <div className="academic-detail-item">
              <span className="detail-label">Batch</span>
              <span className="detail-value">{student.batch || "2022 - 2026"}</span>
            </div>
          </div>
        </div>

        {/* Card 2: Current GPA */}
        <div className="academic-card card-gpa">
          <div className="academic-card-header">
            <div className="academic-card-icon icon-green">
              <FontAwesomeIcon icon={faChartSimple} />
            </div>
            <div className="academic-card-titles">
              <span className="academic-card-label">Current GPA</span>
              <div className="academic-score-wrap">
                <span className="academic-score-number">
                  {metrics.current_gpa !== null && metrics.current_gpa !== undefined
                    ? metrics.current_gpa.toFixed(2)
                    : "—"}
                </span>
                <span className="academic-score-scale">/ 10</span>
              </div>
            </div>
          </div>

          <div className="academic-card-footer">
            <span className="footer-label">Previous Semester</span>
            {metrics.previous_gpa !== null && metrics.previous_gpa !== undefined ? (
              <span className="footer-trend trend-positive">
                {metrics.previous_gpa.toFixed(2)}{" "}
                {metrics.gpa_trend && (
                  <FontAwesomeIcon
                    icon={metrics.gpa_trend.direction === "up" ? faArrowTrendUp : faArrowTrendDown}
                    className="trend-icon"
                  />
                )}
              </span>
            ) : (
              <span className="footer-trend">N/A</span>
            )}
          </div>
        </div>

        {/* Card 3: CGPA */}
        <div className="academic-card card-cgpa">
          <div className="academic-card-header">
            <div className="academic-card-icon icon-purple">
              <FontAwesomeIcon icon={faChartLine} />
            </div>
            <div className="academic-card-titles">
              <span className="academic-card-label">CGPA</span>
              <div className="academic-score-wrap">
                <span className="academic-score-number text-purple">
                  {metrics.cgpa !== null && metrics.cgpa !== undefined ? metrics.cgpa.toFixed(2) : "—"}
                </span>
                <span className="academic-score-scale">/ 10</span>
              </div>
            </div>
          </div>

          <div className="academic-card-footer">
            <span className="footer-label">Total Credits Earned</span>
            <span className="footer-highlight">
              {metrics.total_credits_earned ?? 0} / {metrics.total_degree_credits ?? 120}
            </span>
          </div>
        </div>

        {/* Card 4: Total Subjects */}
        <div className="academic-card card-subjects">
          <div className="academic-card-header">
            <div className="academic-card-icon icon-coral">
              <FontAwesomeIcon icon={faBookOpen} />
            </div>
            <div className="academic-card-titles">
              <span className="academic-card-label">Total Subjects</span>
              <span className="academic-score-number text-coral">
                {metrics.total_subjects ?? resultsList.length ?? 0}
              </span>
            </div>
          </div>

          <div className="academic-card-footer split-footer">
            <span className="sub-stat">
              Completed <strong className="stat-passed">{metrics.completed_subjects ?? 0}</strong>
            </span>
            <span className="sub-stat">
              In Progress <strong className="stat-progress">{metrics.in_progress_subjects ?? 0}</strong>
            </span>
          </div>
        </div>
      </section>

      {/* 3. Navigation Tabs Bar */}
      <nav className="academic-tabs-bar" aria-label="Academic Views">
        <button
          type="button"
          className={`academic-tab-btn ${activeTab === "overview" ? "tab-active" : ""}`}
          onClick={() => setActiveTab("overview")}
        >
          Overview
        </button>
        <button
          type="button"
          className={`academic-tab-btn ${activeTab === "results" ? "tab-active" : ""}`}
          onClick={() => setActiveTab("results")}
        >
          Semester Results
        </button>
        <button
          type="button"
          className={`academic-tab-btn ${activeTab === "performance" ? "tab-active" : ""}`}
          onClick={() => setActiveTab("performance")}
        >
          Performance
        </button>
        <button
          type="button"
          className={`academic-tab-btn ${activeTab === "exams" ? "tab-active" : ""}`}
          onClick={() => setActiveTab("exams")}
        >
          Examination Records
        </button>
        <button
          type="button"
          className={`academic-tab-btn ${activeTab === "documents" ? "tab-active" : ""}`}
          onClick={() => setActiveTab("documents")}
        >
          Documents
        </button>
      </nav>

      {/* Export status banners */}
      {exportSuccess && (
        <div className="export-success-banner" role="status">
          <FontAwesomeIcon icon={faCheck} className="success-icon" />
          <span>Official Academic Grade Card (PDF) successfully downloaded!</span>
        </div>
      )}
      {exportError && (
        <div className="export-error-banner" role="alert">
          <FontAwesomeIcon icon={faTriangleExclamation} className="error-icon" />
          <span>{exportError}</span>
        </div>
      )}

      {/* 4. Tab Views Content */}

      {/* TAB 1: OVERVIEW (Matching reference layout) */}
      {activeTab === "overview" && (
        <div className="academic-main-layout">
          {/* Left Column: Semester Results & Subject Performance */}
          <div className="academic-left-col">
            {/* Semester Results Table Card */}
            <div className="academic-content-card">
              <div className="content-card-header">
                <h3 className="content-card-title">Semester Results</h3>

                {/* Semester Selector Dropdown */}
                <div className="semester-select-wrap">
                  <select
                    className="semester-dropdown"
                    value={selectedSemester || ""}
                    onChange={(e) => setSelectedSemester(Number(e.target.value))}
                    aria-label="Filter by semester"
                  >
                    {availableSemesters.map((s) => (
                      <option key={s.semester} value={s.semester}>
                        {s.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Results Table */}
              {resultsList.length > 0 ? (
                <>
                  <div className="academic-table-wrap">
                    <table className="academic-table">
                      <thead>
                        <tr>
                          <th className="th-num">#</th>
                          <th>Subject Code</th>
                          <th>Subject Name</th>
                          <th className="th-center">Credits</th>
                          <th className="th-center">Marks</th>
                          <th className="th-center">Grade</th>
                          <th className="th-center">Grade Points</th>
                          <th className="th-center">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {resultsList.map((row) => (
                          <tr key={row.result_id}>
                            <td className="td-num">{row.index}</td>
                            <td className="td-code">{row.subject_code}</td>
                            <td className="td-name">{row.subject_name}</td>
                            <td className="td-center">{row.credits}</td>
                            <td className="td-center">{row.marks !== null ? row.marks : "—"}</td>
                            <td className="td-center td-grade">{row.grade}</td>
                            <td className="td-center">{row.grade_points.toFixed(1)}</td>
                            <td className="td-center">
                              <span
                                className={`academic-status-pill ${
                                  row.status === "Pass" ? "status-pass" : "status-fail"
                                }`}
                              >
                                {row.status}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <div className="academic-table-footer">
                    <span>
                      Showing 1 – {resultsList.length} of {resultsList.length} subjects
                    </span>
                  </div>
                </>
              ) : (
                <div className="academic-empty-state">
                  <FontAwesomeIcon icon={faFileLines} className="empty-state-icon" />
                  <h4>No Published Results Available</h4>
                  <p>
                    Official examination results for {resultsData?.semester_label || "this semester"} have not been
                    published yet.
                  </p>
                </div>
              )}
            </div>

            {/* Subject Performance Horizontal Bars Card */}
            <div className="academic-content-card">
              <div className="content-card-header">
                <h3 className="content-card-title">Subject Performance</h3>
              </div>

              {subjectPerformance.length > 0 ? (
                <div className="subject-performance-grid">
                  {subjectPerformance.map((item) => (
                    <div key={item.subject_code} className="subject-perf-item">
                      <div className="subject-perf-info">
                        <span className="perf-subject-name">{item.subject_name}</span>
                        <span className="perf-percentage">{item.percentage}%</span>
                      </div>
                      <div className="perf-bar-track">
                        <div
                          className="perf-bar-fill"
                          style={{ width: `${Math.min(100, item.percentage)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="academic-empty-state mini-empty">
                  <p>Subject performance scores will appear once marks are released.</p>
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Academic Performance Chart, Key Insights, Quick Actions */}
          <div className="academic-right-col">
            {/* Academic Performance SVG Line Chart */}
            <div className="academic-content-card chart-card">
              <div className="content-card-header chart-header">
                <h3 className="content-card-title">Academic Performance</h3>

                {/* Chart Legend */}
                <div className="chart-legend">
                  <span className="legend-item legend-gpa">
                    <span className="legend-dot dot-gpa" />
                    GPA
                  </span>
                  <span className="legend-item legend-cgpa">
                    <span className="legend-dot dot-cgpa" />
                    CGPA
                  </span>
                </div>
              </div>

              {chartPoints && chartPoints.history.length > 0 ? (
                <div className="academic-svg-chart-container">
                  <svg
                    viewBox={`0 0 ${chartPoints.width} ${chartPoints.height}`}
                    className="academic-line-chart-svg"
                  >
                    <defs>
                      <linearGradient id="gpaGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#2563eb" stopOpacity="0.28" />
                        <stop offset="100%" stopColor="#2563eb" stopOpacity="0.0" />
                      </linearGradient>
                    </defs>

                    {/* Horizontal subtle dashed gridlines */}
                    {[0, 2, 4, 6, 8, 10].map((val) => {
                      const y =
                        chartPoints.paddingTop +
                        chartPoints.plotHeight -
                        (val / 10) * chartPoints.plotHeight;
                      return (
                        <g key={val} className="chart-grid-row">
                          <text
                            x={chartPoints.paddingLeft - 8}
                            y={y + 3}
                            className="chart-axis-label"
                            textAnchor="end"
                          >
                            {val}
                          </text>
                          <line
                            x1={chartPoints.paddingLeft}
                            y1={y}
                            x2={chartPoints.width - 16}
                            y2={y}
                            className="chart-grid-line"
                          />
                        </g>
                      );
                    })}

                    {/* Gradient Area under GPA line */}
                    {chartPoints.gpaAreaPath && (
                      <path d={chartPoints.gpaAreaPath} fill="url(#gpaGradient)" />
                    )}

                    {/* CGPA Line (Green) */}
                    {chartPoints.cgpaPath && (
                      <path
                        d={chartPoints.cgpaPath}
                        fill="none"
                        stroke="#10b981"
                        strokeWidth="2.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    )}

                    {/* GPA Line (Blue) */}
                    {chartPoints.gpaPath && (
                      <path
                        d={chartPoints.gpaPath}
                        fill="none"
                        stroke="#2563eb"
                        strokeWidth="2.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    )}

                    {/* X-axis labels and interactive circles */}
                    {chartPoints.gpaPoints.map((pt, i) => (
                      <g key={pt.sem}>
                        <text
                          x={pt.x}
                          y={chartPoints.baselineY + 16}
                          className="chart-axis-x"
                          textAnchor="middle"
                        >
                          {pt.sem}
                        </text>

                        {/* GPA Circle */}
                        <circle
                          cx={pt.x}
                          cy={pt.y}
                          r="4"
                          className="chart-circle-gpa"
                          onMouseEnter={() =>
                            setChartTooltip({
                              x: pt.x,
                              y: pt.y,
                              title: pt.sem,
                              gpa: pt.val,
                              cgpa: chartPoints.cgpaPoints[i]?.val,
                            })
                          }
                          onMouseLeave={() => setChartTooltip(null)}
                        />

                        {/* CGPA Circle */}
                        {chartPoints.cgpaPoints[i] && (
                          <circle
                            cx={chartPoints.cgpaPoints[i].x}
                            cy={chartPoints.cgpaPoints[i].y}
                            r="4"
                            className="chart-circle-cgpa"
                            onMouseEnter={() =>
                              setChartTooltip({
                                x: chartPoints.cgpaPoints[i].x,
                                y: chartPoints.cgpaPoints[i].y,
                                title: pt.sem,
                                gpa: pt.val,
                                cgpa: chartPoints.cgpaPoints[i].val,
                              })
                            }
                            onMouseLeave={() => setChartTooltip(null)}
                          />
                        )}
                      </g>
                    ))}
                  </svg>

                  {/* Hover Tooltip */}
                  {chartTooltip && (
                    <div
                      className="chart-tooltip-popup"
                      style={{
                        left: `${(chartTooltip.x / chartPoints.width) * 100}%`,
                        top: `${(chartTooltip.y / chartPoints.height) * 100}%`,
                      }}
                    >
                      <strong>{chartTooltip.title}</strong>
                      <div>GPA: {chartTooltip.gpa?.toFixed(2)}</div>
                      {chartTooltip.cgpa && <div>CGPA: {chartTooltip.cgpa?.toFixed(2)}</div>}
                    </div>
                  )}
                </div>
              ) : (
                <div className="academic-empty-state mini-empty">
                  <p>Progression history requires completed semester results.</p>
                </div>
              )}
            </div>

            {/* Key Insights Card */}
            <div className="academic-content-card insights-card">
              <div className="content-card-header">
                <h3 className="content-card-title with-icon">
                  <FontAwesomeIcon icon={faLightbulb} className="insights-bulb" />
                  Key Insights
                </h3>
              </div>

              <ul className="insights-list">
                {insights.map((insight, idx) => (
                  <li key={idx} className="insight-item">
                    <FontAwesomeIcon icon={faCircleCheck} className="insight-check-icon" />
                    <span>{insight}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Quick Actions Card */}
            <div className="academic-content-card quick-actions-card">
              <div className="content-card-header">
                <h3 className="content-card-title">Quick Actions</h3>
              </div>

              <div className="quick-actions-list">
                <button
                  type="button"
                  className="quick-action-btn"
                  onClick={handleExport}
                  disabled={exporting || !hasPublishedResults}
                  aria-label="Download Report PDF"
                >
                  <div className="action-btn-left">
                    <FontAwesomeIcon icon={faDownload} className="action-icon icon-blue" />
                    <span>{exporting ? "Generating Official Report..." : "Download Report (PDF)"}</span>
                  </div>
                  <FontAwesomeIcon icon={faChevronRight} className="action-chevron" />
                </button>

                <button
                  type="button"
                  className="quick-action-btn"
                  onClick={() => setActiveTab("exams")}
                  aria-label="View Examination Records"
                >
                  <div className="action-btn-left">
                    <FontAwesomeIcon icon={faFileLines} className="action-icon icon-purple" />
                    <span>View Examination Records</span>
                  </div>
                  <FontAwesomeIcon icon={faChevronRight} className="action-chevron" />
                </button>

                <button
                  type="button"
                  className="quick-action-btn"
                  onClick={() => navigate("/student/dashboard")}
                  aria-label="Back to Dashboard"
                >
                  <div className="action-btn-left">
                    <FontAwesomeIcon icon={faArrowLeft} className="action-icon icon-dark" />
                    <span>Back to Dashboard</span>
                  </div>
                  <FontAwesomeIcon icon={faChevronRight} className="action-chevron" />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: SEMESTER RESULTS (Expanded full-width view) */}
      {activeTab === "results" && (
        <div className="academic-content-card full-view-card">
          <div className="content-card-header">
            <div>
              <h3 className="content-card-title">Detailed Semester Grade Card</h3>
              <p className="content-card-subtitle">
                Official course grades, marks distribution, and credit weights for {resultsData?.semester_label}
              </p>
            </div>

            <div className="semester-select-wrap">
              <select
                className="semester-dropdown"
                value={selectedSemester || ""}
                onChange={(e) => setSelectedSemester(Number(e.target.value))}
                aria-label="Filter by semester"
              >
                {availableSemesters.map((s) => (
                  <option key={s.semester} value={s.semester}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {resultsList.length > 0 ? (
            <div className="academic-table-wrap">
              <table className="academic-table full-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Subject Code</th>
                    <th>Subject Name</th>
                    <th className="th-center">Credits</th>
                    <th className="th-center">Marks Obtained</th>
                    <th className="th-center">Maximum Marks</th>
                    <th className="th-center">Letter Grade</th>
                    <th className="th-center">Grade Points</th>
                    <th className="th-center">Result Status</th>
                    <th>Remarks</th>
                  </tr>
                </thead>
                <tbody>
                  {resultsList.map((row) => (
                    <tr key={row.result_id}>
                      <td>{row.index}</td>
                      <td className="td-code">{row.subject_code}</td>
                      <td className="td-name">{row.subject_name}</td>
                      <td className="td-center">{row.credits}</td>
                      <td className="td-center">{row.marks !== null ? row.marks : "—"}</td>
                      <td className="td-center">{row.max_marks}</td>
                      <td className="td-center td-grade">{row.grade}</td>
                      <td className="td-center">{row.grade_points.toFixed(1)}</td>
                      <td className="td-center">
                        <span
                          className={`academic-status-pill ${
                            row.status === "Pass" ? "status-pass" : "status-fail"
                          }`}
                        >
                          {row.status}
                        </span>
                      </td>
                      <td className="td-remarks">{row.remarks}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="academic-empty-state">
              <FontAwesomeIcon icon={faFileLines} className="empty-state-icon" />
              <h4>No Published Records Found</h4>
              <p>No verified results have been published for this semester.</p>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: PERFORMANCE (Detailed Breakdown) */}
      {activeTab === "performance" && (
        <div className="academic-content-card full-view-card">
          <div className="content-card-header">
            <h3 className="content-card-title">Subject Performance Breakdown</h3>
          </div>

          {subjectPerformance.length > 0 ? (
            <div className="subject-performance-detailed">
              {subjectPerformance.map((item) => (
                <div key={item.subject_code} className="perf-detail-card">
                  <div className="perf-detail-top">
                    <div>
                      <strong className="perf-detail-code">{item.subject_code}</strong>
                      <h4 className="perf-detail-title">{item.subject_name}</h4>
                    </div>
                    <span className="perf-detail-badge">Grade: {item.grade}</span>
                  </div>

                  <div className="perf-bar-track large-track">
                    <div
                      className="perf-bar-fill"
                      style={{ width: `${Math.min(100, item.percentage)}%` }}
                    />
                  </div>

                  <div className="perf-detail-bottom">
                    <span>
                      Marks: {item.marks} / {item.max_marks}
                    </span>
                    <strong>{item.percentage}%</strong>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="academic-empty-state">
              <FontAwesomeIcon icon={faChartSimple} className="empty-state-icon" />
              <h4>No Performance Records</h4>
              <p>Performance scores will be calculated when marks are entered.</p>
            </div>
          )}
        </div>
      )}

      {/* TAB 4: EXAMINATION RECORDS */}
      {activeTab === "exams" && (
        <div className="academic-content-card full-view-card">
          <div className="content-card-header">
            <h3 className="content-card-title">Institutional Examination Cycles</h3>
          </div>

          {examinations.length > 0 ? (
            <div className="academic-table-wrap">
              <table className="academic-table">
                <thead>
                  <tr>
                    <th>Exam Name</th>
                    <th>Type</th>
                    <th>Academic Year</th>
                    <th>Semester</th>
                    <th>Published Date</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {examinations.map((ex) => (
                    <tr key={ex.exam_id}>
                      <td className="td-name">{ex.exam_name}</td>
                      <td>{ex.exam_type}</td>
                      <td>{ex.academic_year}</td>
                      <td>{ex.semester_label}</td>
                      <td>{ex.published_at ? ex.published_at.slice(0, 10) : "—"}</td>
                      <td>
                        <span className="academic-status-pill status-pass">{ex.status}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="academic-empty-state">
              <FontAwesomeIcon icon={faCalendarDays} className="empty-state-icon" />
              <h4>No Published Examination Schedules</h4>
              <p>Upcoming examination cycles will appear here when scheduled by the registrar.</p>
            </div>
          )}
        </div>
      )}

      {/* TAB 5: DOCUMENTS */}
      {activeTab === "documents" && (
        <div className="academic-content-card full-view-card">
          <div className="content-card-header">
            <h3 className="content-card-title">Official Academic Documents</h3>
          </div>

          {documents.length > 0 ? (
            <div className="academic-docs-list">
              {documents.map((doc) => (
                <div key={doc.document_id} className="academic-doc-item">
                  <div className="doc-item-left">
                    <div className="doc-icon-wrap">
                      <FontAwesomeIcon icon={faFileLines} />
                    </div>
                    <div>
                      <strong className="doc-item-title">{doc.title}</strong>
                      <p className="doc-item-meta">
                        {doc.document_type} • Issued: {doc.issued_at || "Recent"}
                      </p>
                    </div>
                  </div>

                  <div className="doc-item-right">
                    {doc.is_verified && (
                      <span className="doc-verified-badge">
                        <FontAwesomeIcon icon={faShieldHalved} />
                        Verified
                      </span>
                    )}
                    <button
                      type="button"
                      className="doc-download-btn"
                      onClick={handleExport}
                      disabled={exporting || !hasPublishedResults}
                      aria-label={`Download ${doc.title}`}
                    >
                      <FontAwesomeIcon icon={faDownload} />
                      {exporting ? "Generating..." : "Download"}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="academic-empty-state">
              <FontAwesomeIcon icon={faFileLines} className="empty-state-icon" />
              <h4>No Digital Transcripts Issued Yet</h4>
              <p>Official grade sheets and certified documents are available after semester completion.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
