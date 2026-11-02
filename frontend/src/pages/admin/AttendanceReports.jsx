import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  Calendar,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ClipboardCheck,
  Download,
  Filter,
  PieChart,
  RotateCcw,
  Target,
  TrendingUp,
  Users,
  X,
} from "lucide-react";

import {
  exportAdminAttendanceCsv,
  getAdminAttendanceDashboard,
  getAdminAttendanceFilterOptions,
  getAdminAttendanceRecordDetail,
  getAdminAttendanceRecordsList,
} from "../../services/adminService";

import attendanceBannerImg from "../../../image/attendance_banner.jpg";
import kpiPresentImg from "../../../image/admin_quickstat_students.jpg";
import kpiAbsentImg from "../../../image/admin_quickstat_absent.jpg";
import kpiClassesImg from "../../../image/admin_quickstat_courses.jpg";
import kpiRateImg from "../../../image/admin_quickstat_records.jpg";

import { formatAcademicYear } from "../../utils/academicYearUtils";
import "./AttendanceReports.css";

// =========================================================================
// HELPER FORMATTERS
// =========================================================================
function formatNumber(num) {
  if (num === null || num === undefined) return "0";
  return Number(num).toLocaleString();
}

function formatPercent(num) {
  if (num === null || num === undefined || Number.isNaN(Number(num))) return "0.0%";
  return `${Number(num).toFixed(1)}%`;
}

function formatDateDisplay(dateStr) {
  if (!dateStr) return "";
  try {
    const parts = String(dateStr).split("-");
    if (parts.length === 3) {
      const year = parseInt(parts[0], 10);
      const month = parseInt(parts[1], 10) - 1;
      const day = parseInt(parts[2], 10);
      const d = new Date(year, month, day);
      return d.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    }
    return dateStr;
  } catch {
    return dateStr;
  }
}

function getStatusBadgeClass(status) {
  const s = (status || "").toLowerCase();
  if (s === "present") return "present";
  if (s === "late") return "late";
  return "absent";
}

function formatSemesterSection(semester, section, preformatted) {
  if (preformatted) return preformatted;
  const semVal =
    semester !== null && semester !== undefined && semester !== ""
      ? `Semester ${semester}`
      : "N/A";
  const secVal =
    section !== null && section !== undefined && section !== ""
      ? `Section ${section}`
      : "N/A";
  if (semVal === "N/A" && secVal === "N/A") return "N/A";
  return `${semVal} / ${secVal}`;
}

// =========================================================================
// SVG CHART: ATTENDANCE TREND (Area + Spline Line Chart)
// =========================================================================
function AttendanceTrendChart({ trend = [], loading = false, error = null }) {
  const [hoveredPoint, setHoveredPoint] = useState(null);

  if (loading) {
    return (
      <div className="attendance-chart-empty-state">
        <p>Loading attendance trend...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="attendance-chart-empty-state">
        <p style={{ color: "#dc2626" }}>Unable to load trend data</p>
      </div>
    );
  }

  if (!trend || trend.length === 0) {
    return (
      <div className="attendance-chart-empty-state">
        <p>No attendance trend data available</p>
      </div>
    );
  }

  const width = 480;
  const height = 190;
  const padLeft = 40;
  const padRight = 20;
  const padTop = 15;
  const padBottom = 30;

  const chartW = width - padLeft - padRight;
  const chartH = height - padTop - padBottom;

  const step = trend.length > 1 ? chartW / (trend.length - 1) : chartW / 2;
  const coords = trend.map((p, i) => {
    const x = padLeft + i * step;
    const rateClamped = Math.max(0, Math.min(100, p.rate || 0));
    const y = padTop + chartH - (rateClamped / 100) * chartH;
    return { x, y, ...p };
  });

  let pathD = `M ${coords[0].x} ${coords[0].y}`;
  for (let i = 0; i < coords.length - 1; i++) {
    const p0 = coords[i];
    const p1 = coords[i + 1];
    const cx = (p0.x + p1.x) / 2;
    pathD += ` C ${cx} ${p0.y}, ${cx} ${p1.y}, ${p1.x} ${p1.y}`;
  }

  const lastX = coords[coords.length - 1].x;
  const firstX = coords[0].x;
  const bottomY = padTop + chartH;
  const areaD = `${pathD} L ${lastX} ${bottomY} L ${firstX} ${bottomY} Z`;

  const yTicks = [100, 75, 50, 25, 0];

  return (
    <div className="attendance-trend-chart-body">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        style={{ width: "100%", height: "100%", overflow: "visible" }}
      >
        <defs>
          <linearGradient id="trendGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#2563eb" stopOpacity="0.22" />
            <stop offset="100%" stopColor="#2563eb" stopOpacity="0.0" />
          </linearGradient>
        </defs>

        {/* Y Gridlines and labels */}
        {yTicks.map((tick) => {
          const y = padTop + chartH - (tick / 100) * chartH;
          return (
            <g key={tick}>
              <line
                x1={padLeft}
                y1={y}
                x2={width - padRight}
                y2={y}
                stroke="#e2e8f0"
                strokeDasharray="4 4"
                strokeWidth="1"
              />
              <text
                x={padLeft - 8}
                y={y + 3.5}
                textAnchor="end"
                fontSize="10"
                fill="#94a3b8"
                fontFamily="inherit"
              >
                {tick}%
              </text>
            </g>
          );
        })}

        {/* Shaded Area */}
        {areaD && <path d={areaD} fill="url(#trendGradient)" />}

        {/* Main Line */}
        {pathD && (
          <path
            d={pathD}
            fill="none"
            stroke="#2563eb"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        )}

        {/* Points & X-Labels */}
        {coords.map((c, i) => (
          <g key={i}>
            <circle
              cx={c.x}
              cy={c.y}
              r={hoveredPoint === i ? 6 : 4}
              fill="#2563eb"
              stroke="#ffffff"
              strokeWidth="2"
              style={{ cursor: "pointer", transition: "r 0.15s ease" }}
              onMouseEnter={() => setHoveredPoint(i)}
              onMouseLeave={() => setHoveredPoint(null)}
            />
            <text
              x={c.x}
              y={height - 8}
              textAnchor="middle"
              fontSize="10.5"
              fill="#64748b"
              fontWeight="500"
              fontFamily="inherit"
            >
              {c.label || c.date}
            </text>
          </g>
        ))}
      </svg>

      {/* Interactive Tooltip */}
      {hoveredPoint !== null && coords[hoveredPoint] && (
        <div
          className="attendance-chart-tooltip"
          style={{
            left: `${(coords[hoveredPoint].x / width) * 100}%`,
            top: `${(coords[hoveredPoint].y / height) * 100}%`,
          }}
        >
          <strong>{coords[hoveredPoint].label}</strong>: {coords[hoveredPoint].rate.toFixed(1)}%
          <br />
          <span>
            {coords[hoveredPoint].present} of {coords[hoveredPoint].total} students
          </span>
        </div>
      )}
    </div>
  );
}

// =========================================================================
// SVG CHART: ATTENDANCE BY COURSE (Donut Chart)
// =========================================================================
function AttendanceCourseDonut({ courses = [], totalClasses = 0, loading = false, error = null }) {
  const [hoveredIdx, setHoveredIdx] = useState(null);

  if (loading) {
    return (
      <div className="attendance-chart-empty-state">
        <p>Loading course statistics...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="attendance-chart-empty-state">
        <p style={{ color: "#dc2626" }}>Unable to load course statistics</p>
      </div>
    );
  }

  if (!courses || courses.length === 0) {
    return (
      <div className="attendance-chart-empty-state">
        <p>No course attendance data available</p>
      </div>
    );
  }

  const radius = 50;
  const strokeWidth = 24;
  const circumference = 2 * Math.PI * radius;

  const sumValues = courses.reduce((acc, c) => acc + (c.classes || c.total || 1), 0) || 1;

  const { slices } = courses.reduce(
    (acc, c, idx) => {
      const val = c.classes || c.total || 1;
      const strokeDasharray = (val / sumValues) * circumference;
      const currentOffset = acc.offset;
      return {
        slices: [
          ...acc.slices,
          {
            ...c,
            idx,
            dashArray: `${strokeDasharray} ${circumference - strokeDasharray}`,
            dashOffset: -currentOffset,
          },
        ],
        offset: currentOffset + strokeDasharray,
      };
    },
    { slices: [], offset: 0 }
  );

  return (
    <div className="attendance-course-donut-body">
      <div className="attendance-donut-svg-wrap">
        <svg
          viewBox="0 0 140 140"
          style={{ width: "100%", height: "100%", transform: "rotate(-90deg)" }}
        >
          {slices.map((slice) => (
            <circle
              key={slice.idx}
              cx="70"
              cy="70"
              r={radius}
              fill="transparent"
              stroke={slice.color || "#2563eb"}
              strokeWidth={hoveredIdx === slice.idx ? strokeWidth + 4 : strokeWidth}
              strokeDasharray={slice.dashArray}
              strokeDashoffset={slice.dashOffset}
              style={{
                cursor: "pointer",
                transition: "stroke-width 0.18s ease",
              }}
              onMouseEnter={() => setHoveredIdx(slice.idx)}
              onMouseLeave={() => setHoveredIdx(null)}
            />
          ))}
        </svg>

        <div className="attendance-donut-center-text">
          <div className="attendance-donut-number">
            {formatNumber(totalClasses)}
          </div>
          <div className="attendance-donut-label">Total Classes</div>
        </div>
      </div>

      <div className="attendance-course-legend-list">
        {courses.map((item, idx) => (
          <div
            key={item.course_id || idx}
            className="attendance-course-legend-item"
            onMouseEnter={() => setHoveredIdx(idx)}
            onMouseLeave={() => setHoveredIdx(null)}
            style={{
              backgroundColor: hoveredIdx === idx ? "#f1f5f9" : "transparent",
            }}
          >
            <div className="attendance-course-legend-left">
              <span
                className="attendance-course-color-dot"
                style={{ backgroundColor: item.color }}
              />
              <span className="attendance-course-name" title={item.course_name}>
                {item.course_name}
              </span>
            </div>
            <span className="attendance-course-pct">
              {item.rate !== undefined ? `${item.rate.toFixed(1)}%` : "0.0%"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// =========================================================================
// SVG CHART: ATTENDANCE BY SECTION (Bar Chart)
// =========================================================================
function AttendanceSectionBarChart({ sections = [], loading = false, error = null }) {
  const [hoveredBar, setHoveredBar] = useState(null);

  if (loading) {
    return (
      <div className="attendance-chart-empty-state">
        <p>Loading section statistics...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="attendance-chart-empty-state">
        <p style={{ color: "#dc2626" }}>Unable to load section statistics</p>
      </div>
    );
  }

  if (!sections || sections.length === 0) {
    return (
      <div className="attendance-chart-empty-state">
        <p>No section attendance data available</p>
      </div>
    );
  }

  const width = 320;
  const height = 210;
  const padLeft = 40;
  const padRight = 15;
  const padTop = 22;
  const padBottom = 26;

  const chartW = width - padLeft - padRight;
  const chartH = height - padTop - padBottom;

  const yTicks = [100, 75, 50, 25, 0];
  const barCount = Math.max(sections.length, 1);
  const slotW = chartW / barCount;
  const barW = Math.min(32, slotW * 0.58);

  return (
    <div className="attendance-section-bar-body">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        style={{ width: "100%", height: "100%", overflow: "visible" }}
      >
        {/* Y-Ticks */}
        {yTicks.map((tick) => {
          const y = padTop + chartH - (tick / 100) * chartH;
          return (
            <g key={tick}>
              <line
                x1={padLeft}
                y1={y}
                x2={width - padRight}
                y2={y}
                stroke="#e2e8f0"
                strokeDasharray="4 4"
                strokeWidth="1"
              />
              <text
                x={padLeft - 6}
                y={y + 3.5}
                textAnchor="end"
                fontSize="10"
                fill="#94a3b8"
                fontFamily="inherit"
              >
                {tick}%
              </text>
            </g>
          );
        })}

        {/* Section Bars */}
        {sections.map((sec, i) => {
          const slotX = padLeft + i * slotW;
          const barX = slotX + (slotW - barW) / 2;
          const rateVal = Math.max(0, Math.min(100, sec.rate || 0));
          const barHeight = (rateVal / 100) * chartH;
          const barY = padTop + chartH - barHeight;

          return (
            <g
              key={sec.section || i}
              onMouseEnter={() => setHoveredBar(i)}
              onMouseLeave={() => setHoveredBar(null)}
              style={{ cursor: "pointer" }}
            >
              <text
                x={barX + barW / 2}
                y={barY - 6}
                textAnchor="middle"
                fontSize="10"
                fill="#334155"
                fontWeight="600"
                fontFamily="inherit"
              >
                {rateVal.toFixed(1)}%
              </text>

              <rect
                x={barX}
                y={barY}
                width={barW}
                height={barHeight}
                rx="4"
                ry="4"
                fill={sec.color || "#2563eb"}
                opacity={hoveredBar === i ? 0.85 : 1}
                style={{ transition: "all 0.15s ease" }}
              />

              <text
                x={barX + barW / 2}
                y={height - 6}
                textAnchor="middle"
                fontSize="11"
                fill="#475569"
                fontWeight="600"
                fontFamily="inherit"
              >
                {sec.section}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// =========================================================================
// MAIN ATTENDANCE REPORTS COMPONENT
// =========================================================================
function AttendanceReports() {
  // Draft filter states (bound to visible select inputs, initialized neutral)
  const [draftAcademicYear, setDraftAcademicYear] = useState("All");
  const [draftSemester, setDraftSemester] = useState("All");
  const [draftSection, setDraftSection] = useState("All");
  const [draftCourseId, setDraftCourseId] = useState("All");
  const [draftFacultyId, setDraftFacultyId] = useState("All");
  const [draftFromDate, setDraftFromDate] = useState("");
  const [draftToDate, setDraftToDate] = useState("");
  const [dateError, setDateError] = useState(null);

  // Applied filter state (only updated when initial load, Apply, or Reset is executed)
  const [appliedFilters, setAppliedFilters] = useState({
    academicYear: "All",
    semester: "All",
    section: "All",
    courseId: "All",
    facultyId: "All",
    fromDate: "",
    toDate: "",
    period: "Last 4 Weeks",
  });

  // Dynamic filter options directly from backend API
  const [filterOptions, setFilterOptions] = useState({
    academic_years: [],
    semesters: [],
    sections: [],
    semester_sections: {},
    courses: [],
    faculty: [],
  });

  const [showDatePicker, setShowDatePicker] = useState(false);

  // Real Dashboard data directly from backend
  const [dashboardData, setDashboardData] = useState({
    kpi: {
      total_present: 0,
      total_absent: 0,
      total_classes: 0,
      attendance_rate: 0,
      present_rate: 0,
      absent_rate: 0,
      present_trend: null,
      absent_trend: null,
      classes_trend: null,
      rate_trend: null,
    },
    trend: [],
    by_course: [],
    by_section: [],
  });

  // Real Records Table Data directly from backend
  const [records, setRecords] = useState([]);
  const [page, setPage] = useState(1);
  const [totalRecords, setTotalRecords] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const perPage = 5;

  // View modal state
  const [selectedRecord, setSelectedRecord] = useState(null);

  // Loading & error states decoupled for dashboard and records
  const [dashboardLoading, setDashboardLoading] = useState(true);
  const [dashboardError, setDashboardError] = useState(null);
  const [recordsLoading, setRecordsLoading] = useState(true);
  const [recordsError, setRecordsError] = useState(null);
  const [exporting, setExporting] = useState(false);

  // Helper to build query parameters from applied filters
  const buildQueryParams = useCallback((filters) => {
    return {
      academic_year: filters.academicYear !== "All" ? filters.academicYear : undefined,
      semester: filters.semester !== "All" ? filters.semester : undefined,
      section: filters.section !== "All" ? filters.section : undefined,
      course_id: filters.courseId !== "All" ? filters.courseId : undefined,
      faculty_id: filters.facultyId !== "All" ? filters.facultyId : undefined,
      from_date: filters.fromDate || undefined,
      to_date: filters.toDate || undefined,
      period: filters.period,
    };
  }, []);

  // 1. Fetch dynamic filter options on mount (NEVER auto-select any specific academic year or dates)
  useEffect(() => {
    let ignore = false;

    async function loadFilterOptions() {
      try {
        const res = await getAdminAttendanceFilterOptions();
        if (ignore) return;
        if (res && res.success) {
          setFilterOptions({
            academic_years: res.academic_years || [],
            semesters: res.semesters || [],
            sections: res.sections || [],
            semester_sections: res.semester_sections || {},
            courses: res.courses || [],
            faculty: res.faculty || [],
          });
          // Note: Intentionally do NOT prefill draftAcademicYear or dates.
          // Neutral options remain selected: "All Academic Years", date range empty.
        }
      } catch (err) {
        if (!ignore) {
          console.warn("Could not load dynamic filter options from backend", err);
        }
      }
    }

    loadFilterOptions();

    return () => {
      ignore = true;
    };
  }, []);

  // 2. Fetch Dashboard & Records when appliedFilters change (or on initial mount with neutral filters)
  useEffect(() => {
    let ignore = false;

    async function loadReportData() {
      try {
        const qp = buildQueryParams(appliedFilters);
        const [dashRes, recRes] = await Promise.allSettled([
          getAdminAttendanceDashboard(qp),
          getAdminAttendanceRecordsList({
            ...qp,
            page: 1,
            per_page: perPage,
          }),
        ]);

        if (ignore) return;

        if (dashRes.status === "fulfilled" && dashRes.value?.success) {
          setDashboardData(dashRes.value);
          setDashboardError(null);
        } else {
          const errorMsg =
            dashRes.status === "rejected"
              ? dashRes.reason?.response?.data?.message || dashRes.reason?.message || "Failed to load dashboard data."
              : dashRes.value?.message || "Failed to load dashboard data.";
          setDashboardError(errorMsg);
        }
        setDashboardLoading(false);

        if (recRes.status === "fulfilled" && recRes.value?.success) {
          setRecords(recRes.value.data || []);
          setTotalRecords(recRes.value.total_records || 0);
          setTotalPages(recRes.value.total_pages || 1);
          setRecordsError(null);
        } else {
          const errorMsg =
            recRes.status === "rejected"
              ? recRes.reason?.response?.data?.message || recRes.reason?.message || "Failed to load attendance records."
              : recRes.value?.message || "Failed to load attendance records.";
          setRecordsError(errorMsg);
        }
        setRecordsLoading(false);
      } catch (err) {
        if (!ignore) {
          console.error("Attendance data fetch failed", err);
          setDashboardError("Failed to load attendance dashboard data.");
          setRecordsError("Failed to load attendance records.");
          setDashboardLoading(false);
          setRecordsLoading(false);
        }
      }
    }

    loadReportData();

    return () => {
      ignore = true;
    };
  }, [appliedFilters, buildQueryParams, perPage]);

  // 3. Retry handlers
  const handleRetryDashboard = async () => {
    setDashboardLoading(true);
    setDashboardError(null);
    try {
      const qp = buildQueryParams(appliedFilters);
      const res = await getAdminAttendanceDashboard(qp);
      if (res && res.success) {
        setDashboardData(res);
      } else {
        setDashboardError(res?.message || "Failed to load attendance dashboard data.");
      }
    } catch (err) {
      setDashboardError(
        err?.response?.data?.message || err?.message || "Failed to load attendance dashboard data."
      );
    } finally {
      setDashboardLoading(false);
    }
  };

  const handleRetryRecords = async () => {
    setRecordsLoading(true);
    setRecordsError(null);
    try {
      const qp = {
        ...buildQueryParams(appliedFilters),
        page,
        per_page: perPage,
      };
      const res = await getAdminAttendanceRecordsList(qp);
      if (res && res.success) {
        setRecords(res.data || []);
        setTotalRecords(res.total_records || 0);
        setTotalPages(res.total_pages || 1);
      } else {
        setRecordsError(res?.message || "Failed to load attendance records.");
      }
    } catch (err) {
      setRecordsError(
        err?.response?.data?.message || err?.message || "Failed to load attendance records."
      );
    } finally {
      setRecordsLoading(false);
    }
  };

  // 4. Handle page changes without refetching the entire dashboard
  const handlePageChange = async (newPage) => {
    setPage(newPage);
    setRecordsLoading(true);
    setRecordsError(null);
    try {
      const qp = {
        ...buildQueryParams(appliedFilters),
        page: newPage,
        per_page: perPage,
      };
      const res = await getAdminAttendanceRecordsList(qp);
      if (res && res.success) {
        setRecords(res.data || []);
        setTotalRecords(res.total_records || 0);
        setTotalPages(res.total_pages || 1);
      } else {
        setRecordsError(res?.message || "Failed to load attendance records.");
      }
    } catch (err) {
      setRecordsError(
        err?.response?.data?.message || err?.message || "Failed to load attendance records."
      );
    } finally {
      setRecordsLoading(false);
    }
  };

  // 5. Validate & Apply Filters
  const handleApplyFilters = () => {
    if (draftFromDate && draftToDate && draftFromDate > draftToDate) {
      setDateError("Start date cannot be after end date.");
      setShowDatePicker(true);
      return;
    }
    setDateError(null);
    setShowDatePicker(false);
    setPage(1);
    setDashboardLoading(true);
    setRecordsLoading(true);
    setAppliedFilters({
      academicYear: draftAcademicYear,
      semester: draftSemester,
      section: draftSection,
      courseId: draftCourseId,
      facultyId: draftFacultyId,
      fromDate: draftFromDate,
      toDate: draftToDate,
      period: appliedFilters.period,
    });
  };

  // 6. Reset Filters to neutral initial state
  const handleResetFilters = () => {
    setDraftAcademicYear("All");
    setDraftSemester("All");
    setDraftSection("All");
    setDraftCourseId("All");
    setDraftFacultyId("All");
    setDraftFromDate("");
    setDraftToDate("");
    setDateError(null);
    setShowDatePicker(false);
    setPage(1);
    setDashboardLoading(true);
    setRecordsLoading(true);
    setAppliedFilters({
      academicYear: "All",
      semester: "All",
      section: "All",
      courseId: "All",
      facultyId: "All",
      fromDate: "",
      toDate: "",
      period: "Last 4 Weeks",
    });
  };

  // 7. Handle Period change for Attendance Trend
  const handlePeriodChange = (newPeriod) => {
    setDashboardLoading(true);
    setAppliedFilters((prev) => ({ ...prev, period: newPeriod }));
  };

  // 7. Download real CSV report from backend API respecting applied filters
  const handleDownloadReport = async () => {
    try {
      setExporting(true);
      const queryParams = buildQueryParams(appliedFilters);
      const blobData = await exportAdminAttendanceCsv(queryParams);
      const blob = new Blob([blobData], { type: "text/csv;charset=utf-8;" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      const yearSuffix = appliedFilters.academicYear !== "All" ? `_${appliedFilters.academicYear}` : "";
      link.setAttribute("download", `Attendance_Report${yearSuffix}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Export failed", err);
      alert(err?.response?.data?.message || err?.message || "Failed to export attendance report from backend.");
    } finally {
      setExporting(false);
    }
  };

  // 8. View real record details from backend API in modal
  const handleViewRecord = async (record) => {
    setSelectedRecord(record);
    try {
      const res = await getAdminAttendanceRecordDetail(record.attendance_id);
      if (res && res.success) {
        setSelectedRecord(res.data);
      }
    } catch (err) {
      console.warn("Could not load single record detail from backend", err);
    }
  };

  // Restrict available sections dynamically based on selected semester
  const availableSections = useMemo(() => {
    if (draftSemester !== "All" && filterOptions.semester_sections?.[draftSemester]) {
      return filterOptions.semester_sections[draftSemester];
    }
    return filterOptions.sections || [];
  }, [draftSemester, filterOptions.semester_sections, filterOptions.sections]);

  const handleSemesterChange = (newSemester) => {
    setDraftSemester(newSemester);
    if (newSemester !== "All" && filterOptions.semester_sections?.[newSemester]) {
      const validSections = filterOptions.semester_sections[newSemester];
      if (draftSection !== "All" && !validSections.includes(draftSection)) {
        setDraftSection("All");
      }
    }
  };

  // Date range display text for the filter button
  const dateRangeDisplay = useMemo(() => {
    if (!draftFromDate && !draftToDate) return "Select Date Range";
    if (draftFromDate && draftToDate) {
      return `${formatDateDisplay(draftFromDate)} - ${formatDateDisplay(draftToDate)}`;
    }
    if (draftFromDate) return `From ${formatDateDisplay(draftFromDate)}`;
    return `Until ${formatDateDisplay(draftToDate)}`;
  }, [draftFromDate, draftToDate]);

  // Check if any filter is actively applied beyond neutral
  const hasActiveFilters = useMemo(() => {
    return (
      appliedFilters.academicYear !== "All" ||
      appliedFilters.semester !== "All" ||
      appliedFilters.section !== "All" ||
      appliedFilters.courseId !== "All" ||
      appliedFilters.facultyId !== "All" ||
      Boolean(appliedFilters.fromDate) ||
      Boolean(appliedFilters.toDate)
    );
  }, [appliedFilters]);

  const totalAttendanceMarks =
    (dashboardData.kpi?.total_present || 0) + (dashboardData.kpi?.total_absent || 0);

  return (
    <div className="attendance-page-container">
      {/* ================================================================= */}
      {/* 1. TOP BANNER CARD                                                */}
      {/* ================================================================= */}
      <section className="attendance-banner-card">
        <div className="attendance-banner-left">
          <div className="attendance-banner-icon-box">
            <ClipboardCheck size={22} strokeWidth={2.2} />
          </div>
          <div className="attendance-banner-text">
            <h1>Attendance Reports</h1>
            <p>View attendance statistics, generate reports, and analyze student performance.</p>
          </div>
        </div>

        <div className="attendance-banner-image-wrap">
          <img
            src={attendanceBannerImg || "/image/attendance_banner.jpg"}
            alt="Attendance reports workspace"
            className="attendance-banner-bg-img"
          />
          <div className="attendance-banner-image-gradient" />
        </div>
      </section>

      {/* ================================================================= */}
      {/* 2. FILTER BAR                                                     */}
      {/* ================================================================= */}
      <section className="attendance-filter-card">
        {/* Academic Year */}
        <div className="attendance-filter-group">
          <label className="attendance-filter-label" htmlFor="academic-year-select">
            Academic Year
          </label>
          <div className="attendance-select-wrapper">
            <select
              id="academic-year-select"
              className="attendance-filter-select"
              value={draftAcademicYear}
              onChange={(e) => setDraftAcademicYear(e.target.value)}
            >
              <option value="All">All Academic Years</option>
              {filterOptions.academic_years.map((year) => (
                <option key={year} value={year}>
                  {formatAcademicYear(year)}
                </option>
              ))}
            </select>
            <ChevronDown className="attendance-select-chevron" size={14} />
          </div>
        </div>

        {/* Semester */}
        <div className="attendance-filter-group">
          <label className="attendance-filter-label" htmlFor="semester-select">
            Semester
          </label>
          <div className="attendance-select-wrapper">
            <select
              id="semester-select"
              className="attendance-filter-select"
              value={draftSemester}
              onChange={(e) => handleSemesterChange(e.target.value)}
            >
              <option value="All">All Semesters</option>
              {filterOptions.semesters.map((sem) => (
                <option key={sem} value={sem}>
                  Semester {sem}
                </option>
              ))}
            </select>
            <ChevronDown className="attendance-select-chevron" size={14} />
          </div>
        </div>

        {/* Section */}
        <div className="attendance-filter-group">
          <label className="attendance-filter-label" htmlFor="section-select">
            Section
          </label>
          <div className="attendance-select-wrapper">
            <select
              id="section-select"
              className="attendance-filter-select"
              value={draftSection}
              onChange={(e) => setDraftSection(e.target.value)}
            >
              <option value="All">All Sections</option>
              {availableSections.map((sec) => (
                <option key={sec} value={sec}>
                  Section {sec}
                </option>
              ))}
            </select>
            <ChevronDown className="attendance-select-chevron" size={14} />
          </div>
        </div>

        {/* Course */}
        <div className="attendance-filter-group">
          <label className="attendance-filter-label" htmlFor="course-select">
            Course
          </label>
          <div className="attendance-select-wrapper">
            <select
              id="course-select"
              className="attendance-filter-select"
              value={draftCourseId}
              onChange={(e) => setDraftCourseId(e.target.value)}
            >
              <option value="All">All Courses</option>
              {filterOptions.courses.map((c) => (
                <option key={c.course_id} value={c.course_id}>
                  {c.course_code ? `${c.course_code} - ${c.course_name}` : c.course_name}
                </option>
              ))}
            </select>
            <ChevronDown className="attendance-select-chevron" size={14} />
          </div>
        </div>

        {/* Faculty */}
        <div className="attendance-filter-group">
          <label className="attendance-filter-label" htmlFor="faculty-select">
            Faculty
          </label>
          <div className="attendance-select-wrapper">
            <select
              id="faculty-select"
              className="attendance-filter-select"
              value={draftFacultyId}
              onChange={(e) => setDraftFacultyId(e.target.value)}
            >
              <option value="All">All Faculty</option>
              {filterOptions.faculty.map((f) => (
                <option key={f.faculty_id} value={f.faculty_id}>
                  {f.name}
                </option>
              ))}
            </select>
            <ChevronDown className="attendance-select-chevron" size={14} />
          </div>
        </div>

        {/* Date Range Picker */}
        <div className="attendance-filter-group date-group" style={{ position: "relative" }}>
          <label className="attendance-filter-label">Date Range</label>
          <button
            type="button"
            className="attendance-date-range-btn"
            onClick={() => setShowDatePicker(!showDatePicker)}
          >
            <Calendar size={14} className="attendance-date-icon" />
            <span className="attendance-date-text">{dateRangeDisplay}</span>
          </button>

          {showDatePicker && (
            <div className="attendance-daterange-picker-box">
              <div className="attendance-date-input-field">
                <label>From Date</label>
                <input
                  type="date"
                  value={draftFromDate}
                  onChange={(e) => {
                    setDraftFromDate(e.target.value);
                    setDateError(null);
                  }}
                />
              </div>
              <div className="attendance-date-input-field">
                <label>To Date</label>
                <input
                  type="date"
                  value={draftToDate}
                  onChange={(e) => {
                    setDraftToDate(e.target.value);
                    setDateError(null);
                  }}
                />
              </div>

              {dateError && (
                <div
                  style={{
                    color: "#ef4444",
                    fontSize: "11px",
                    fontWeight: 500,
                    display: "flex",
                    alignItems: "center",
                    gap: "4px",
                  }}
                >
                  <AlertCircle size={12} />
                  {dateError}
                </div>
              )}

              <div style={{ display: "flex", gap: "8px", marginTop: "4px" }}>
                <button
                  type="button"
                  className="attendance-btn-reset"
                  style={{ height: "30px", flex: 1, padding: "0 8px" }}
                  onClick={() => {
                    setDraftFromDate("");
                    setDraftToDate("");
                    setDateError(null);
                  }}
                >
                  Clear
                </button>
                <button
                  type="button"
                  className="attendance-btn-apply"
                  style={{ height: "30px", flex: 1, padding: "0 8px" }}
                  onClick={() => {
                    if (draftFromDate && draftToDate && draftFromDate > draftToDate) {
                      setDateError("Start date cannot be after end date.");
                      return;
                    }
                    setDateError(null);
                    setShowDatePicker(false);
                  }}
                >
                  Done
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="attendance-filter-actions">
          <button
            type="button"
            className="attendance-btn-apply"
            onClick={handleApplyFilters}
            disabled={dashboardLoading || recordsLoading}
          >
            <Filter size={14} />
            Apply Filters
          </button>
          <button
            type="button"
            className="attendance-btn-reset"
            onClick={handleResetFilters}
            disabled={dashboardLoading || recordsLoading}
          >
            <RotateCcw size={13} />
            Reset
          </button>
        </div>
      </section>

      {/* Active Filters Display */}
      {hasActiveFilters && (
        <div className="attendance-active-filters-bar" style={{ marginBottom: "16px" }}>
          <span className="attendance-active-filters-label">Active Filters:</span>
          {appliedFilters.academicYear !== "All" && (
            <span className="attendance-filter-tag">Academic Year: {appliedFilters.academicYear}</span>
          )}
          {appliedFilters.semester !== "All" && (
            <span className="attendance-filter-tag">Semester: {appliedFilters.semester}</span>
          )}
          {appliedFilters.section !== "All" && (
            <span className="attendance-filter-tag">Section: {appliedFilters.section}</span>
          )}
          {appliedFilters.courseId !== "All" && (
            <span className="attendance-filter-tag">
              Course:{" "}
              {filterOptions.courses.find((c) => String(c.course_id) === String(appliedFilters.courseId))
                ?.course_code || appliedFilters.courseId}
            </span>
          )}
          {appliedFilters.facultyId !== "All" && (
            <span className="attendance-filter-tag">
              Faculty:{" "}
              {filterOptions.faculty.find((f) => String(f.faculty_id) === String(appliedFilters.facultyId))
                ?.name || appliedFilters.facultyId}
            </span>
          )}
          {(appliedFilters.fromDate || appliedFilters.toDate) && (
            <span className="attendance-filter-tag">
              Date: {formatDateDisplay(appliedFilters.fromDate) || "Start"} -{" "}
              {formatDateDisplay(appliedFilters.toDate) || "End"}
            </span>
          )}
          <button
            type="button"
            className="attendance-clear-all-tag"
            onClick={handleResetFilters}
            title="Clear all filters"
          >
            Clear All
          </button>
        </div>
      )}

      {/* Dashboard Error Alert Banner */}
      {dashboardError && (
        <div className="attendance-error-banner" style={{ marginBottom: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <AlertCircle size={16} />
            <span>{dashboardError}</span>
          </div>
          <button
            type="button"
            className="attendance-retry-btn"
            onClick={handleRetryDashboard}
          >
            <RotateCcw size={12} /> Retry
          </button>
        </div>
      )}

      {/* ================================================================= */}
      {/* 3. KPI STAT CARDS (4 CARDS)                                       */}
      {/* ================================================================= */}
      <section className="attendance-kpi-grid">
        {/* Card 1: Total Present */}
        <div
          className="attendance-kpi-card kpi-card-present"
          style={{
            backgroundImage: `url("${kpiPresentImg || "/image/admin_quickstat_students.jpg"}")`,
          }}
        >
          <div className="attendance-kpi-left-icon present-icon">
            <Check size={22} strokeWidth={2.8} />
          </div>
          <div className="attendance-kpi-content">
            <span className="attendance-kpi-title">Total Present</span>
            <div className="attendance-kpi-value-row">
              <span className="attendance-kpi-value">
                {dashboardLoading ? "—" : dashboardError ? "—" : formatNumber(dashboardData.kpi?.total_present)}
              </span>
              {!dashboardLoading && !dashboardError && dashboardData.kpi?.present_trend && (
                <span className="attendance-kpi-trend positive">
                  ↑ {dashboardData.kpi.present_trend}
                </span>
              )}
            </div>
            <span className="attendance-kpi-subtitle">
              {dashboardLoading
                ? "Loading..."
                : dashboardError
                ? "Data unavailable"
                : totalAttendanceMarks > 0
                ? `${formatPercent(dashboardData.kpi?.present_rate)} of total`
                : "No attendance recorded"}
            </span>
          </div>
        </div>

        {/* Card 2: Total Absent */}
        <div
          className="attendance-kpi-card kpi-card-absent"
          style={{
            backgroundImage: `url("${kpiAbsentImg || "/image/admin_quickstat_absent.jpg"}")`,
          }}
        >
          <div className="attendance-kpi-left-icon absent-icon">
            <X size={22} strokeWidth={2.8} />
          </div>
          <div className="attendance-kpi-content">
            <span className="attendance-kpi-title">Total Absent</span>
            <div className="attendance-kpi-value-row">
              <span className="attendance-kpi-value">
                {dashboardLoading ? "—" : dashboardError ? "—" : formatNumber(dashboardData.kpi?.total_absent)}
              </span>
              {!dashboardLoading && !dashboardError && dashboardData.kpi?.absent_trend && (
                <span className="attendance-kpi-trend negative">
                  ↑ {dashboardData.kpi.absent_trend}
                </span>
              )}
            </div>
            <span className="attendance-kpi-subtitle">
              {dashboardLoading
                ? "Loading..."
                : dashboardError
                ? "Data unavailable"
                : totalAttendanceMarks > 0
                ? `${formatPercent(dashboardData.kpi?.absent_rate)} of total`
                : "No attendance recorded"}
            </span>
          </div>
        </div>

        {/* Card 3: Total Classes */}
        <div
          className="attendance-kpi-card kpi-card-classes"
          style={{
            backgroundImage: `url("${kpiClassesImg || "/image/admin_quickstat_courses.jpg"}")`,
          }}
        >
          <div className="attendance-kpi-left-icon classes-icon">
            <Calendar size={22} strokeWidth={2.4} />
          </div>
          <div className="attendance-kpi-content">
            <span className="attendance-kpi-title">Total Classes</span>
            <div className="attendance-kpi-value-row">
              <span className="attendance-kpi-value">
                {dashboardLoading ? "—" : dashboardError ? "—" : formatNumber(dashboardData.kpi?.total_classes)}
              </span>
              {!dashboardLoading && !dashboardError && dashboardData.kpi?.classes_trend && (
                <span className="attendance-kpi-trend positive">
                  ↑ {dashboardData.kpi.classes_trend}
                </span>
              )}
            </div>
            <span className="attendance-kpi-subtitle">
              {dashboardLoading ? "Loading..." : dashboardError ? "Data unavailable" : "Scheduled classes"}
            </span>
          </div>
        </div>

        {/* Card 4: Attendance Rate */}
        <div
          className="attendance-kpi-card kpi-card-rate"
          style={{
            backgroundImage: `url("${kpiRateImg || "/image/admin_quickstat_records.jpg"}")`,
          }}
        >
          <div className="attendance-kpi-left-icon rate-icon">
            <Target size={22} strokeWidth={2.4} />
          </div>
          <div className="attendance-kpi-content">
            <span className="attendance-kpi-title">Attendance Rate</span>
            <div className="attendance-kpi-value-row">
              <span className="attendance-kpi-value">
                {dashboardLoading ? "—" : dashboardError ? "—" : formatPercent(dashboardData.kpi?.attendance_rate)}
              </span>
              {!dashboardLoading && !dashboardError && dashboardData.kpi?.rate_trend && (
                <span className="attendance-kpi-trend positive">
                  ↑ {dashboardData.kpi.rate_trend}
                </span>
              )}
            </div>
            <span className="attendance-kpi-subtitle">
              {dashboardLoading ? "Loading..." : dashboardError ? "Data unavailable" : "Overall attendance"}
            </span>
          </div>
        </div>
      </section>

      {/* ================================================================= */}
      {/* 4. CHARTS ROW (3 CHARTS)                                          */}
      {/* ================================================================= */}
      <section className="attendance-charts-grid">
        {/* Chart 1: Attendance Trend */}
        <div className="attendance-chart-card">
          <div className="attendance-chart-header">
            <div className="attendance-chart-title-wrap">
              <TrendingUp className="attendance-chart-header-icon" size={17} />
              <h2 className="attendance-chart-title">Attendance Trend</h2>
            </div>
            <select
              className="attendance-period-select"
              value={appliedFilters.period}
              onChange={(e) => handlePeriodChange(e.target.value)}
            >
              <option value="Last 4 Weeks">Last 4 Weeks</option>
              <option value="Last 7 Days">Last 7 Days</option>
              <option value="Last 30 Days">Last 30 Days</option>
              <option value="This Semester">This Semester</option>
            </select>
          </div>

          <AttendanceTrendChart
            trend={dashboardData.trend}
            loading={dashboardLoading}
            error={dashboardError}
          />

          {!dashboardLoading && !dashboardError && dashboardData.trend && dashboardData.trend.length > 0 && (
            <div className="attendance-chart-legend-bottom">
              <span className="attendance-legend-dot" />
              <span>Attendance Rate</span>
            </div>
          )}
        </div>

        {/* Chart 2: Attendance by Course */}
        <div className="attendance-chart-card">
          <div className="attendance-chart-header">
            <div className="attendance-chart-title-wrap">
              <PieChart className="attendance-chart-header-icon" size={17} />
              <h2 className="attendance-chart-title">Attendance by Course</h2>
            </div>
          </div>

          <AttendanceCourseDonut
            courses={dashboardData.by_course}
            totalClasses={dashboardData.kpi?.total_classes}
            loading={dashboardLoading}
            error={dashboardError}
          />
        </div>

        {/* Chart 3: Attendance by Section */}
        <div className="attendance-chart-card">
          <div className="attendance-chart-header">
            <div className="attendance-chart-title-wrap">
              <Users className="attendance-chart-header-icon" size={17} />
              <h2 className="attendance-chart-title">Attendance by Section</h2>
            </div>
          </div>

          <AttendanceSectionBarChart
            sections={dashboardData.by_section}
            loading={dashboardLoading}
            error={dashboardError}
          />
        </div>
      </section>

      {/* ================================================================= */}
      {/* 5. RECENT ATTENDANCE RECORDS TABLE                                */}
      {/* ================================================================= */}
      <section className="attendance-table-card">
        <div className="attendance-table-header-row">
          <div className="attendance-table-title-wrap">
            <Calendar className="attendance-table-icon" size={18} />
            <h2 className="attendance-table-title">Recent Attendance Records</h2>
          </div>

          <button
            type="button"
            className="attendance-btn-download"
            onClick={handleDownloadReport}
            disabled={exporting || totalRecords === 0}
          >
            <Download size={14} />
            {exporting ? "Downloading..." : "Download Report"}
          </button>
        </div>

        <div className="attendance-table-responsive">
          <table className="attendance-data-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Student Name</th>
                <th>Roll No.</th>
                <th>Course Code</th>
                <th>Course Name</th>
                <th>Semester / Section</th>
                <th>Status</th>
                <th>Marked At</th>
                <th>Method</th>
                <th>Confidence Score</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {recordsLoading ? (
                <tr>
                  <td colSpan="11" style={{ textAlign: "center", padding: "34px", color: "#64748b" }}>
                    Loading attendance records from backend...
                  </td>
                </tr>
              ) : recordsError ? (
                <tr>
                  <td colSpan="11" style={{ textAlign: "center", padding: "34px", color: "#dc2626" }}>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "8px" }}>
                      <span>Failed to load attendance records: {recordsError}</span>
                      <button
                        type="button"
                        className="attendance-retry-btn"
                        onClick={handleRetryRecords}
                      >
                        <RotateCcw size={12} /> Retry
                      </button>
                    </div>
                  </td>
                </tr>
              ) : records.length === 0 ? (
                <tr>
                  <td colSpan="11" style={{ textAlign: "center", padding: "34px", color: "#64748b" }}>
                    No attendance records match the selected filters.
                  </td>
                </tr>
              ) : (
                records.map((rec) => (
                  <tr key={rec.attendance_id}>
                    <td>{rec.date}</td>
                    <td style={{ fontWeight: 600, color: "#0f172a" }}>
                      {rec.student_name}
                    </td>
                    <td>{rec.roll_no}</td>
                    <td>{rec.course_code}</td>
                    <td>{rec.course_name}</td>
                    <td>{formatSemesterSection(rec.semester, rec.section, rec.semester_section)}</td>
                    <td>
                      <span className={`attendance-status-badge ${getStatusBadgeClass(rec.status)}`}>
                        {rec.status}
                      </span>
                    </td>
                    <td>{rec.marked_at}</td>
                    <td>{rec.method}</td>
                    <td>{rec.confidence_score}</td>
                    <td>
                      <button
                        type="button"
                        className="attendance-btn-view"
                        onClick={() => handleViewRecord(rec)}
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Table Footer with real pagination */}
        <div className="attendance-table-footer">
          <span>
            {recordsLoading
              ? "Loading records..."
              : recordsError
              ? "Error loading records"
              : totalRecords > 0
              ? `Showing ${(page - 1) * perPage + 1} to ${Math.min(page * perPage, totalRecords)} of ${formatNumber(totalRecords)} records`
              : "Showing 0 records"}
          </span>

          {!recordsLoading && !recordsError && totalRecords > 0 && (
            <div className="attendance-pagination">
              <button
                type="button"
                className="attendance-page-btn"
                disabled={page <= 1}
                onClick={() => handlePageChange(Math.max(1, page - 1))}
                aria-label="Previous page"
              >
                <ChevronLeft size={14} />
              </button>

              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                const pageNum = i + 1;
                return (
                  <button
                    key={pageNum}
                    type="button"
                    className={`attendance-page-btn ${page === pageNum ? "active" : ""}`}
                    onClick={() => handlePageChange(pageNum)}
                  >
                    {pageNum}
                  </button>
                );
              })}

              {totalPages > 5 && (
                <>
                  <span style={{ padding: "0 4px" }}>...</span>
                  <button
                    type="button"
                    className={`attendance-page-btn ${page === totalPages ? "active" : ""}`}
                    onClick={() => handlePageChange(totalPages)}
                  >
                    {totalPages}
                  </button>
                </>
              )}

              <button
                type="button"
                className="attendance-page-btn"
                disabled={page >= totalPages}
                onClick={() => handlePageChange(Math.min(totalPages, page + 1))}
                aria-label="Next page"
              >
                <ChevronRight size={14} />
              </button>
            </div>
          )}
        </div>
      </section>

      {/* ================================================================= */}
      {/* 6. VIEW RECORD DETAIL MODAL                                       */}
      {/* ================================================================= */}
      {selectedRecord && (
        <div
          className="attendance-modal-overlay"
          onClick={() => setSelectedRecord(null)}
        >
          <div
            className="attendance-modal-card"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="attendance-modal-header">
              <h3>Attendance Record Details</h3>
              <button
                type="button"
                className="attendance-modal-close-btn"
                onClick={() => setSelectedRecord(null)}
              >
                <X size={18} />
              </button>
            </div>

            <div className="attendance-modal-body">
              <div className="attendance-modal-grid">
                <div className="attendance-modal-item">
                  <span className="attendance-modal-label">Student Name</span>
                  <span className="attendance-modal-value">
                    {selectedRecord.student?.name || selectedRecord.student_name}
                  </span>
                </div>

                <div className="attendance-modal-item">
                  <span className="attendance-modal-label">Roll Number</span>
                  <span className="attendance-modal-value">
                    {selectedRecord.student?.enrollment_no || selectedRecord.roll_no}
                  </span>
                </div>

                <div className="attendance-modal-item">
                  <span className="attendance-modal-label">Course</span>
                  <span className="attendance-modal-value">
                    {selectedRecord.course?.course_name || selectedRecord.course_name} (
                    {selectedRecord.course?.course_code || selectedRecord.course_code})
                  </span>
                </div>

                <div className="attendance-modal-item">
                  <span className="attendance-modal-label">Semester / Section</span>
                  <span className="attendance-modal-value">
                    {formatSemesterSection(
                      selectedRecord.semester ?? selectedRecord.student?.semester ?? selectedRecord.session?.semester,
                      selectedRecord.section ?? selectedRecord.student?.section,
                      selectedRecord.semester_section
                    )}
                  </span>
                </div>

                <div className="attendance-modal-item">
                  <span className="attendance-modal-label">Status</span>
                  <div>
                    <span className={`attendance-status-badge ${getStatusBadgeClass(selectedRecord.status)}`}>
                      {selectedRecord.status}
                    </span>
                  </div>
                </div>

                <div className="attendance-modal-item">
                  <span className="attendance-modal-label">Marked At</span>
                  <span className="attendance-modal-value">
                    {selectedRecord.marked_at || "-"}
                  </span>
                </div>

                <div className="attendance-modal-item">
                  <span className="attendance-modal-label">Verification Method</span>
                  <span className="attendance-modal-value">
                    {selectedRecord.recognition_method === "FACE" ||
                    selectedRecord.method === "Face Recognition"
                      ? "Face Recognition"
                      : selectedRecord.method || "Manual"}
                  </span>
                </div>

                <div className="attendance-modal-item">
                  <span className="attendance-modal-label">Confidence Score</span>
                  <span className="attendance-modal-value">
                    {selectedRecord.confidence_score
                      ? typeof selectedRecord.confidence_score === "number"
                        ? `${selectedRecord.confidence_score.toFixed(1)}%`
                        : selectedRecord.confidence_score
                      : "-"}
                  </span>
                </div>

                {selectedRecord.session && (
                  <>
                    <div className="attendance-modal-item">
                      <span className="attendance-modal-label">Session Date</span>
                      <span className="attendance-modal-value">
                        {selectedRecord.session.date}
                      </span>
                    </div>

                    <div className="attendance-modal-item">
                      <span className="attendance-modal-label">Faculty</span>
                      <span className="attendance-modal-value">
                        {selectedRecord.faculty?.name || "Assigned Faculty"}
                      </span>
                    </div>
                  </>
                )}
              </div>
            </div>

            <div className="attendance-modal-footer">
              <button
                type="button"
                className="attendance-btn-apply"
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

export default AttendanceReports;