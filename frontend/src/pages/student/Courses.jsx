import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  BookOpen,
  Calendar,
  CheckCircle2,
  Percent,
  Search,
  RotateCcw,
  LayoutGrid,
  List,
  Building2,
  User,
  Clock,
  ArrowRight,
  Lightbulb,
  GraduationCap,
  ClipboardCheck,
  BarChart3,
  CalendarDays,
  FileText,
  ChevronRight,
  MoreVertical,
  X,
  AlertCircle,
  RefreshCw,
  MapPin,
  Check,
  ShieldCheck,
} from "lucide-react";
import { getStudentCourses } from "../../services/studentService";
import "./Courses.css";

// Aesthetic color palettes matching reference screenshot
const CARD_COLOR_THEMES = [
  {
    theme: "blue",
    iconBg: "#eff6ff",
    iconColor: "#2563eb",
    codeBg: "#e0f2fe",
    codeColor: "#0369a1",
    dotColor: "#3b82f6",
  },
  {
    theme: "purple",
    iconBg: "#f5f3ff",
    iconColor: "#7c3aed",
    codeBg: "#f3e8ff",
    codeColor: "#7e22ce",
    dotColor: "#8b5cf6",
  },
  {
    theme: "amber",
    iconBg: "#fffbeb",
    iconColor: "#d97706",
    codeBg: "#fef3c7",
    codeColor: "#b45309",
    dotColor: "#f59e0b",
  },
  {
    theme: "coral",
    iconBg: "#fef2f2",
    iconColor: "#dc2626",
    codeBg: "#fee2e2",
    codeColor: "#b91c1c",
    dotColor: "#ef4444",
  },
  {
    theme: "teal",
    iconBg: "#f0fdf4",
    iconColor: "#059669",
    codeBg: "#dcfce7",
    codeColor: "#15803d",
    dotColor: "#10b981",
  },
  {
    theme: "indigo",
    iconBg: "#eef2ff",
    iconColor: "#4f46e5",
    codeBg: "#e0e7ff",
    codeColor: "#4338ca",
    dotColor: "#6366f1",
  },
];

function getCourseTheme(index, code = "") {
  if (code) {
    let hash = 0;
    for (let i = 0; i < code.length; i++) {
      hash = (hash << 5) - hash + code.charCodeAt(i);
      hash |= 0;
    }
    const idx = Math.abs(hash) % CARD_COLOR_THEMES.length;
    return CARD_COLOR_THEMES[idx];
  }
  return CARD_COLOR_THEMES[index % CARD_COLOR_THEMES.length];
}

function Courses() {
  const navigate = useNavigate();

  const [courses, setCourses] = useState([]);
  const [stats, setStats] = useState(null);
  const [todaySchedule, setTodaySchedule] = useState([]);
  const [departmentsList, setDepartmentsList] = useState([]);
  const [semestersList, setSemestersList] = useState([]);

  const [search, setSearch] = useState("");
  const [departmentFilter, setDepartmentFilter] = useState("all");
  const [semesterFilter, setSemesterFilter] = useState("all");
  const [viewMode, setViewMode] = useState("grid"); // "grid" | "list"

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedCourse, setSelectedCourse] = useState(null);
  const [reloadTrigger, setReloadTrigger] = useState(0);

  useEffect(() => {
    let isCancelled = false;

    async function fetchCourses() {
      try {
        setError("");

        const result = await getStudentCourses();
        if (isCancelled) return;

        if (result?.success) {
          setCourses(result.data || []);
          setStats(result.stats || null);
          setTodaySchedule(result.today_schedule || []);
          setDepartmentsList(result.departments || []);
          setSemestersList(result.semesters || []);
        } else {
          setCourses([]);
          setError(result?.message || "Unable to load your courses from academic records.");
        }
      } catch (err) {
        if (isCancelled) return;
        setCourses([]);
        setError(
          err?.response?.data?.message ||
            "Unable to load courses. Please verify backend connectivity."
        );
      } finally {
        if (!isCancelled) {
          setLoading(false);
        }
      }
    }

    fetchCourses();

    return () => {
      isCancelled = true;
    };
  }, [reloadTrigger]);

  const handleRetry = () => {
    setLoading(true);
    setReloadTrigger((prev) => prev + 1);
  };

  // Handle escape key to close modal
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && selectedCourse) {
        setSelectedCourse(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [selectedCourse]);

  // Derived filter options
  const departments = useMemo(() => {
    if (departmentsList && departmentsList.length > 0) {
      return departmentsList;
    }
    const map = new Map();
    courses.forEach((c) => {
      if (c.department?.department_name) {
        map.set(c.department.department_id || c.department.department_name, {
          department_id: c.department.department_id,
          department_name: c.department.department_name,
          department_code: c.department.department_code,
        });
      }
    });
    return Array.from(map.values());
  }, [departmentsList, courses]);

  const semesters = useMemo(() => {
    if (semestersList && semestersList.length > 0) {
      return semestersList;
    }
    const unique = new Set(courses.map((c) => c.semester).filter(Boolean));
    return Array.from(unique).sort((a, b) => a - b);
  }, [semestersList, courses]);

  // Filtered courses based on search & dropdowns
  const filteredCourses = useMemo(() => {
    const query = search.trim().toLowerCase();

    return courses.filter((course) => {
      const codeMatch = String(course.course_code || "").toLowerCase().includes(query);
      const nameMatch = String(course.course_name || "").toLowerCase().includes(query);
      const facultyMatch = String(course.faculty?.name || "").toLowerCase().includes(query);
      const deptMatch = String(course.department?.department_name || "").toLowerCase().includes(query);

      const matchesSearch = !query || codeMatch || nameMatch || facultyMatch || deptMatch;

      const matchesDept =
        departmentFilter === "all" ||
        String(course.department?.department_id) === String(departmentFilter) ||
        String(course.department?.department_name) === String(departmentFilter);

      const matchesSem =
        semesterFilter === "all" ||
        String(course.semester) === String(semesterFilter);

      return matchesSearch && matchesDept && matchesSem;
    });
  }, [courses, search, departmentFilter, semesterFilter]);

  const resetFilters = () => {
    setSearch("");
    setDepartmentFilter("all");
    setSemesterFilter("all");
  };

  // Quick formatted today's date
  const todayFormatted = useMemo(() => {
    const options = { month: "short", day: "numeric", year: "numeric" };
    return new Date().toLocaleDateString("en-US", options);
  }, []);

  return (
    <div className="sams-courses-page">
      {/* ========================================================
          1. HERO BANNER
      ======================================================== */}
      <section className="courses-hero-banner" aria-label="My Classes Banner">
        {/* Left: Cap icon, title, and subtitle */}
        <div className="courses-hero-left">
          <div className="courses-hero-icon-card">
            <GraduationCap size={28} className="courses-hero-cap-icon" />
          </div>

          <div className="courses-hero-text">
            <h1 className="courses-hero-title">My Classes</h1>
            <p className="courses-hero-subtitle">
              Access your enrolled classes, schedules, and class details in one place.
            </p>
          </div>
        </div>

        {/* Center: Scalable, high-res student study illustration grounded at desk */}
        <div className="courses-hero-center" aria-hidden="true">
          <img
            src="/image/student_my_classes_banner.png"
            alt="Student studying with laptop and books"
            className="courses-hero-student-img"
          />
        </div>

        {/* Right: Inspirational quote matching reference */}
        <div className="courses-hero-right">
          <div className="courses-quote-card">
            <span className="courses-quote-sparkle" aria-hidden="true">✦</span>
            <div className="courses-quote-text-group">
              <p className="courses-quote-text">
                &ldquo;Small steps every day<br />lead to big results.&rdquo;
              </p>
              <span className="courses-quote-underline" aria-hidden="true" />
            </div>
          </div>
        </div>
      </section>

      {/* ========================================================
          2. SUMMARY STAT CARDS (4 CARDS)
      ======================================================== */}
      <section className="courses-summary-row" aria-label="Course Statistics">
        {/* Card 1: Total Classes */}
        <div className="courses-summary-card">
          <div className="courses-stat-icon-wrap is-blue">
            <BookOpen size={20} strokeWidth={2.4} />
          </div>
          <div className="courses-stat-info">
            <span className="courses-stat-label">Total Classes</span>
            <strong className="courses-stat-value">
              {loading ? "..." : (stats?.total_courses ?? courses.length)}
            </strong>
            <small className="courses-stat-subtext">Enrolled this semester</small>
          </div>
        </div>

        {/* Card 2: Upcoming Classes */}
        <div className="courses-summary-card">
          <div className="courses-stat-icon-wrap is-green">
            <Calendar size={20} strokeWidth={2.4} />
          </div>
          <div className="courses-stat-info">
            <span className="courses-stat-label">Upcoming Classes</span>
            <strong className="courses-stat-value">
              {loading ? "..." : (stats?.upcoming_classes_7_days ?? 0)}
            </strong>
            <small className="courses-stat-subtext">Next 7 days</small>
          </div>
        </div>

        {/* Card 3: Completed Classes */}
        <div className="courses-summary-card">
          <div className="courses-stat-icon-wrap is-purple">
            <CheckCircle2 size={20} strokeWidth={2.4} />
          </div>
          <div className="courses-stat-info">
            <span className="courses-stat-label">Completed Classes</span>
            <strong className="courses-stat-value">
              {loading ? "..." : (stats?.completed_classes_semester ?? 0)}
            </strong>
            <small className="courses-stat-subtext">This semester</small>
          </div>
        </div>

        {/* Card 4: Attendance Rate */}
        <div className="courses-summary-card">
          <div className="courses-stat-icon-wrap is-pink">
            <Percent size={20} strokeWidth={2.4} />
          </div>
          <div className="courses-stat-info">
            <span className="courses-stat-label">Attendance Rate</span>
            <strong className="courses-stat-value">
              {loading
                ? "..."
                : stats?.overall_attendance_rate !== null &&
                  stats?.overall_attendance_rate !== undefined
                ? `${stats.overall_attendance_rate}%`
                : "N/A"}
            </strong>
            <small className="courses-stat-subtext">
              {stats?.has_attendance_data ? "Overall" : "No sessions held"}
            </small>
          </div>
        </div>
      </section>

      {/* ========================================================
          3. SEARCH & FILTERS BAR
      ======================================================== */}
      <section className="courses-filter-bar" aria-label="Course Filters">
        <div className="courses-search-wrap">
          <Search size={18} className="courses-search-icon" aria-hidden="true" />
          <input
            type="search"
            className="courses-search-input"
            placeholder="Search by course name, code, or faculty..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            disabled={loading || Boolean(error)}
            aria-label="Search by course name, code, or faculty"
          />
        </div>

        <div className="courses-filter-controls">
          <div className="courses-select-wrap">
            <select
              className="courses-filter-select"
              value={departmentFilter}
              onChange={(e) => setDepartmentFilter(e.target.value)}
              disabled={loading || Boolean(error)}
              aria-label="Filter by department"
            >
              <option value="all">All Departments</option>
              {departments.map((dept) => (
                <option
                  key={dept.department_id || dept.department_name}
                  value={dept.department_id || dept.department_name}
                >
                  {dept.department_name}
                </option>
              ))}
            </select>
          </div>

          <div className="courses-select-wrap">
            <select
              className="courses-filter-select"
              value={semesterFilter}
              onChange={(e) => setSemesterFilter(e.target.value)}
              disabled={loading || Boolean(error)}
              aria-label="Filter by semester"
            >
              <option value="all">All Semesters</option>
              {semesters.map((sem) => (
                <option key={sem} value={sem}>
                  Semester {sem}
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            className="courses-reset-btn"
            onClick={resetFilters}
            disabled={loading || (!search && departmentFilter === "all" && semesterFilter === "all")}
            aria-label="Reset filters"
          >
            <RotateCcw size={16} />
            <span>Reset</span>
          </button>
        </div>
      </section>

      {/* ========================================================
          4. TWO-COLUMN MAIN CONTENT
      ======================================================== */}
      <div className="courses-main-layout">
        {/* ==================== LEFT COLUMN: COURSES ==================== */}
        <section className="courses-left-col">
          {/* Section Header */}
          <div className="courses-section-header">
            <div className="courses-section-title-wrap">
              <GraduationCap size={22} className="courses-header-cap-icon" />
              <h2 className="courses-section-title">
                My Classes ({loading ? "..." : filteredCourses.length})
              </h2>
            </div>

            <div className="courses-view-switcher" role="group" aria-label="View toggle">
              <button
                type="button"
                className={`courses-view-btn ${viewMode === "grid" ? "is-active" : ""}`}
                onClick={() => setViewMode("grid")}
                aria-pressed={viewMode === "grid"}
              >
                <LayoutGrid size={16} />
                <span>Grid View</span>
              </button>
              <button
                type="button"
                className={`courses-view-btn ${viewMode === "list" ? "is-active" : ""}`}
                onClick={() => setViewMode("list")}
                aria-pressed={viewMode === "list"}
              >
                <List size={16} />
                <span>List View</span>
              </button>
            </div>
          </div>

          {/* Loading State */}
          {loading && (
            <div className="courses-status-card">
              <div className="courses-spinner" />
              <h3>Loading your courses</h3>
              <p>Fetching verified enrollments and timetable schedules...</p>
            </div>
          )}

          {/* Error State */}
          {!loading && error && (
            <div className="courses-status-card is-error">
              <AlertCircle size={32} className="courses-status-icon error" />
              <h3>Unable to load courses</h3>
              <p>{error}</p>
              <button
                type="button"
                className="courses-retry-btn"
                onClick={handleRetry}
              >
                <RefreshCw size={15} />
                <span>Retry</span>
              </button>
            </div>
          )}

          {/* Empty Filter State */}
          {!loading && !error && filteredCourses.length === 0 && (
            <div className="courses-status-card">
              <BookOpen size={36} className="courses-status-icon muted" />
              <h3>
                {courses.length === 0
                  ? "No enrolled courses found"
                  : "No matching classes found"}
              </h3>
              <p>
                {courses.length === 0
                  ? "Your academic enrollments will appear here once registered by your department."
                  : "Try clearing your search query or selecting a different department/semester."}
              </p>
              {courses.length > 0 && (
                <button
                  type="button"
                  className="courses-retry-btn"
                  onClick={resetFilters}
                >
                  <RotateCcw size={15} />
                  <span>Clear Filters</span>
                </button>
              )}
            </div>
          )}

          {/* ==================== GRID VIEW ==================== */}
          {!loading && !error && filteredCourses.length > 0 && viewMode === "grid" && (
            <div className="courses-cards-grid">
              {filteredCourses.map((course, idx) => {
                const theme = getCourseTheme(idx, course.course_code);
                const attPct = course.attendance?.attendance_percentage;
                const totalSessions = course.attendance?.total_sessions || 0;
                const hasSessions = totalSessions > 0;

                return (
                  <article
                    key={course.offering_id || course.course_code || idx}
                    className="course-card"
                  >
                    {/* Card Top Row */}
                    <div className="course-card-top">
                      <div className="course-card-left-badge">
                        <div
                          className="course-card-icon-box"
                          style={{
                            backgroundColor: theme.iconBg,
                            color: theme.iconColor,
                          }}
                        >
                          <BookOpen size={17} strokeWidth={2.4} />
                        </div>
                        <span
                          className="course-card-code-pill"
                          style={{
                            backgroundColor: theme.codeBg,
                            color: theme.codeColor,
                          }}
                        >
                          {course.course_code || "COURSE"}
                        </span>
                      </div>

                      <button
                        type="button"
                        className="course-card-dots-btn"
                        onClick={() => setSelectedCourse(course)}
                        aria-label={`Options for ${course.course_name}`}
                      >
                        <MoreVertical size={16} />
                      </button>
                    </div>

                    {/* Course Name */}
                    <h3 className="course-card-name" title={course.course_name}>
                      {course.course_name || "Untitled Course"}
                    </h3>

                    {/* Metadata Items */}
                    <div className="course-card-meta-list">
                      <div className="course-meta-row">
                        <Building2 size={15} className="course-meta-icon" />
                        <span className="course-meta-text">
                          {course.department?.department_name || "General Department"}
                        </span>
                      </div>

                      <div className="course-meta-row">
                        <User size={15} className="course-meta-icon" />
                        <span className="course-meta-text">
                          {course.faculty?.name || "Faculty not assigned"}
                        </span>
                      </div>

                      <div className="course-meta-row">
                        <CalendarDays size={15} className="course-meta-icon" />
                        <span className="course-meta-text">
                          {course.schedule_summary || "Schedule not assigned"}
                        </span>
                      </div>
                    </div>

                    {/* Card Footer */}
                    <div className="course-card-footer">
                      {hasSessions ? (
                        <div
                          className={`course-attendance-badge ${
                            attPct >= 75 ? "is-good" : "is-warning"
                          }`}
                        >
                          <Check size={13} strokeWidth={3} />
                          <span>{attPct}% Attendance</span>
                        </div>
                      ) : (
                        <div className="course-attendance-badge is-neutral">
                          <span>&mdash; No sessions held</span>
                        </div>
                      )}

                      <button
                        type="button"
                        className="course-view-details-btn"
                        onClick={() => setSelectedCourse(course)}
                      >
                        <span>View Details</span>
                        <ArrowRight size={14} className="course-arrow-icon" />
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          )}

          {/* ==================== LIST VIEW ==================== */}
          {!loading && !error && filteredCourses.length > 0 && viewMode === "list" && (
            <div className="courses-list-view">
              {filteredCourses.map((course, idx) => {
                const theme = getCourseTheme(idx, course.course_code);
                const attPct = course.attendance?.attendance_percentage;
                const totalSessions = course.attendance?.total_sessions || 0;
                const hasSessions = totalSessions > 0;

                return (
                  <article
                    key={course.offering_id || course.course_code || idx}
                    className="course-list-row"
                  >
                    <div className="course-list-main">
                      <div
                        className="course-card-icon-box"
                        style={{
                          backgroundColor: theme.iconBg,
                          color: theme.iconColor,
                        }}
                      >
                        <BookOpen size={17} strokeWidth={2.4} />
                      </div>

                      <div className="course-list-titles">
                        <div className="course-list-code-row">
                          <span
                            className="course-card-code-pill"
                            style={{
                              backgroundColor: theme.codeBg,
                              color: theme.codeColor,
                            }}
                          >
                            {course.course_code}
                          </span>
                          <span className="course-list-credits">
                            {course.credits} Credits &bull; Sem {course.semester}
                          </span>
                        </div>
                        <h3 className="course-list-name">{course.course_name}</h3>
                      </div>
                    </div>

                    <div className="course-list-meta-block">
                      <div className="course-meta-row">
                        <Building2 size={14} className="course-meta-icon" />
                        <span className="course-meta-text">
                          {course.department?.department_name || "General"}
                        </span>
                      </div>
                      <div className="course-meta-row">
                        <User size={14} className="course-meta-icon" />
                        <span className="course-meta-text">
                          {course.faculty?.name || "Faculty not assigned"}
                        </span>
                      </div>
                    </div>

                    <div className="course-list-schedule-block">
                      <div className="course-meta-row">
                        <CalendarDays size={14} className="course-meta-icon" />
                        <span className="course-meta-text">
                          {course.schedule_summary || "Schedule not assigned"}
                        </span>
                      </div>
                      {course.room && (
                        <div className="course-meta-row">
                          <MapPin size={14} className="course-meta-icon" />
                          <span className="course-meta-text">Room {course.room}</span>
                        </div>
                      )}
                    </div>

                    <div className="course-list-actions">
                      {hasSessions ? (
                        <div
                          className={`course-attendance-badge ${
                            attPct >= 75 ? "is-good" : "is-warning"
                          }`}
                        >
                          <Check size={13} strokeWidth={3} />
                          <span>{attPct}%</span>
                        </div>
                      ) : (
                        <div className="course-attendance-badge is-neutral">
                          <span>No sessions</span>
                        </div>
                      )}

                      <button
                        type="button"
                        className="course-view-details-btn"
                        onClick={() => setSelectedCourse(course)}
                      >
                        <span>View Details</span>
                        <ArrowRight size={14} className="course-arrow-icon" />
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>

        {/* ==================== RIGHT COLUMN: PANELS ==================== */}
        <aside className="courses-right-col" aria-label="Course sidebar panels">
          {/* Panel 1: Quick Links */}
          <div className="courses-side-card">
            <div className="courses-side-header">
              <div className="courses-side-header-left">
                <FileText size={18} className="courses-side-icon-blue" />
                <h3 className="courses-side-title">Quick Links</h3>
              </div>
            </div>

            <nav className="courses-quick-links-nav" aria-label="Quick Navigation">
              <button
                type="button"
                className="courses-quick-link-item"
                onClick={() => navigate("/student/attendance")}
              >
                <div className="courses-quick-link-left">
                  <ClipboardCheck size={17} className="courses-ql-icon text-blue" />
                  <span>My Attendance</span>
                </div>
                <ChevronRight size={16} className="courses-ql-arrow" />
              </button>

              <button
                type="button"
                className="courses-quick-link-item"
                onClick={() => navigate("/student/reports")}
              >
                <div className="courses-quick-link-left">
                  <BarChart3 size={17} className="courses-ql-icon text-purple" />
                  <span>Subject-wise Report</span>
                </div>
                <ChevronRight size={16} className="courses-ql-arrow" />
              </button>

              <button
                type="button"
                className="courses-quick-link-item"
                onClick={() => navigate("/student/timetable")}
              >
                <div className="courses-quick-link-left">
                  <CalendarDays size={17} className="courses-ql-icon text-emerald" />
                  <span>Timetable</span>
                </div>
                <ChevronRight size={16} className="courses-ql-arrow" />
              </button>

              <button
                type="button"
                className="courses-quick-link-item"
                onClick={() => navigate("/student/reports")}
              >
                <div className="courses-quick-link-left">
                  <GraduationCap size={17} className="courses-ql-icon text-amber" />
                  <span>Academic Records</span>
                </div>
                <ChevronRight size={16} className="courses-ql-arrow" />
              </button>
            </nav>
          </div>

          {/* Panel 2: Today's Schedule */}
          <div className="courses-side-card">
            <div className="courses-side-header">
              <div className="courses-side-header-left">
                <Calendar size={18} className="courses-side-icon-blue" />
                <div className="courses-schedule-title-wrap">
                  <h3 className="courses-side-title">Today&apos;s Schedule</h3>
                  <span className="courses-schedule-date">{todayFormatted}</span>
                </div>
              </div>
            </div>

            <div className="courses-timeline-wrap">
              {todaySchedule && todaySchedule.length > 0 ? (
                <div className="courses-timeline">
                  {todaySchedule.map((item, idx) => {
                    const theme = getCourseTheme(idx, item.course_code);
                    return (
                      <div
                        key={item.timetable_entry_id || `${item.course_code}-${idx}`}
                        className="courses-timeline-item"
                      >
                        <div
                          className="courses-timeline-dot"
                          style={{ backgroundColor: theme.dotColor }}
                        />
                        <div className="courses-timeline-content">
                          <div className="courses-timeline-top">
                            <strong className="courses-timeline-name">
                              {item.course_name}
                            </strong>
                            <span className="courses-timeline-code">
                              {item.course_code}
                            </span>
                          </div>
                          <div className="courses-timeline-time-row">
                            <Clock size={12} className="courses-timeline-clock" />
                            <span>{item.time_slot || `${item.start_time} - ${item.end_time}`}</span>
                            {item.room && item.room !== "TBD" && (
                              <span className="courses-timeline-room">
                                &bull; {item.room}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="courses-timeline-empty">
                  <CalendarDays size={24} className="courses-empty-cal-icon" />
                  <p>No classes scheduled for today.</p>
                </div>
              )}
            </div>
          </div>

          {/* Panel 3: Motivational Tip Card */}
          <div className="courses-side-card is-motivation">
            <div className="courses-motivation-content">
              <div className="courses-motivation-icon-wrap">
                <Lightbulb size={20} className="courses-bulb-icon" />
              </div>
              <div className="courses-motivation-text">
                <strong className="courses-motivation-title">
                  Keep attending, keep growing!
                </strong>
                <p className="courses-motivation-desc">
                  Your consistency today builds your success tomorrow.
                </p>
              </div>
            </div>
          </div>
        </aside>
      </div>

      {/* ========================================================
          5. COURSE DETAILS MODAL
      ======================================================== */}
      {selectedCourse && (
        <div
          className="courses-modal-backdrop"
          onClick={() => setSelectedCourse(null)}
          role="dialog"
          aria-modal="true"
          aria-labelledby="course-modal-title"
        >
          <div
            className="courses-modal-card"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="courses-modal-header">
              <div className="courses-modal-title-left">
                <span className="courses-modal-code-pill">
                  {selectedCourse.course_code}
                </span>
                <h2 id="course-modal-title" className="courses-modal-title">
                  {selectedCourse.course_name}
                </h2>
              </div>
              <button
                type="button"
                className="courses-modal-close-btn"
                onClick={() => setSelectedCourse(null)}
                aria-label="Close dialog"
              >
                <X size={18} />
              </button>
            </div>

            {/* Modal Body */}
            <div className="courses-modal-body">
              {/* Top Highlights Grid */}
              <div className="courses-modal-grid">
                <div className="courses-modal-meta-item">
                  <span className="modal-meta-label">Department</span>
                  <strong className="modal-meta-value">
                    {selectedCourse.department?.department_name || "General"}
                  </strong>
                </div>

                <div className="courses-modal-meta-item">
                  <span className="modal-meta-label">Credits</span>
                  <strong className="modal-meta-value">
                    {selectedCourse.credits} Credits
                  </strong>
                </div>

                <div className="courses-modal-meta-item">
                  <span className="modal-meta-label">Semester & Section</span>
                  <strong className="modal-meta-value">
                    Semester {selectedCourse.semester} &bull; Section {selectedCourse.section}
                  </strong>
                </div>

                <div className="courses-modal-meta-item">
                  <span className="modal-meta-label">Academic Year</span>
                  <strong className="modal-meta-value">
                    {selectedCourse.academic_year || "Current Year"}
                  </strong>
                </div>
              </div>

              {/* Faculty Information Section */}
              <div className="courses-modal-section">
                <h4 className="courses-modal-section-title">
                  <User size={16} />
                  <span>Assigned Faculty</span>
                </h4>
                {selectedCourse.faculty ? (
                  <div className="courses-modal-faculty-box">
                    <div className="courses-faculty-avatar">
                      {selectedCourse.faculty.name
                        ? selectedCourse.faculty.name.replace(/^Dr\.\s*|Prof\.\s*/i, "").slice(0, 2).toUpperCase()
                        : "FA"}
                    </div>
                    <div className="courses-faculty-details">
                      <strong>{selectedCourse.faculty.name}</strong>
                      <span>{selectedCourse.faculty.designation || "Faculty Member"}</span>
                      {selectedCourse.faculty.email && (
                        <small>{selectedCourse.faculty.email}</small>
                      )}
                    </div>
                  </div>
                ) : (
                  <p className="courses-modal-empty-text">Faculty not assigned yet.</p>
                )}
              </div>

              {/* Timetable Schedule Section */}
              <div className="courses-modal-section">
                <h4 className="courses-modal-section-title">
                  <Clock size={16} />
                  <span>Class Schedules &amp; Rooms</span>
                </h4>
                {selectedCourse.schedules && selectedCourse.schedules.length > 0 ? (
                  <div className="courses-modal-table-wrap">
                    <table className="courses-modal-table">
                      <thead>
                        <tr>
                          <th>Day</th>
                          <th>Time Slot</th>
                          <th>Room</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedCourse.schedules.map((slot) => (
                          <tr key={slot.timetable_entry_id || `${slot.day_of_week}-${slot.time_slot}`}>
                            <td>
                              <strong>{slot.day_of_week}</strong>
                            </td>
                            <td>{slot.time_slot || `${slot.start_time} - ${slot.end_time}`}</td>
                            <td>{slot.room || selectedCourse.room || "TBD"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="courses-modal-empty-text">
                    No active timetable entries assigned for this class.
                  </p>
                )}
              </div>

              {/* Attendance Statistics Section */}
              <div className="courses-modal-section">
                <h4 className="courses-modal-section-title">
                  <ShieldCheck size={16} />
                  <span>Attendance Record</span>
                </h4>
                {selectedCourse.attendance?.total_sessions > 0 ? (
                  <div className="courses-modal-att-grid">
                    <div className="courses-att-box">
                      <span className="att-label">Attended</span>
                      <strong className="att-val text-green">
                        {selectedCourse.attendance.present_sessions}
                      </strong>
                    </div>
                    <div className="courses-att-box">
                      <span className="att-label">Absent</span>
                      <strong className="att-val text-red">
                        {selectedCourse.attendance.absent_sessions}
                      </strong>
                    </div>
                    <div className="courses-att-box">
                      <span className="att-label">Total Sessions</span>
                      <strong className="att-val">
                        {selectedCourse.attendance.total_sessions}
                      </strong>
                    </div>
                    <div className="courses-att-box">
                      <span className="att-label">Percentage</span>
                      <strong className="att-val text-blue">
                        {selectedCourse.attendance.attendance_percentage}%
                      </strong>
                    </div>
                  </div>
                ) : (
                  <div className="courses-modal-no-att">
                    <p>No verified attendance sessions have been conducted yet for this class.</p>
                  </div>
                )}
              </div>
            </div>

            {/* Modal Footer */}
            <div className="courses-modal-footer">
              <button
                type="button"
                className="courses-modal-btn is-close"
                onClick={() => setSelectedCourse(null)}
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

export default Courses;
