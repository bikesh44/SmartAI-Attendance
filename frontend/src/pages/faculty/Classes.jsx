import { useEffect, useMemo, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  BookOpen,
  Users,
  Clock,
  Calendar,
  RotateCw,
  Eye,
  MoreVertical,
  Info,
  X,
  ChevronLeft,
  ChevronRight,
  GraduationCap,
  CalendarDays,
  MapPin,
  CheckCircle2,
  Download,
  FileSpreadsheet,
  FileText,
  ChevronDown,
  Check,
} from "lucide-react";

import {
  getFacultyCourses,
  getFacultyCourseDetails,
  getFacultyTimetable,
  getFacultyClassesSummary,
  exportClassRoster,
} from "../../services/facultyService";
import { invalidateApiCache } from "../../services/api";
import { formatAcademicYear } from "../../utils/academicYearUtils";

import bannerBg from "../../../images/faculty-classes-banner.png";
import cardBlueBg from "../../../images/faculty-classes-card-blue.png";
import cardGreenBg from "../../../images/faculty-classes-card-green.png";
import cardPurpleBg from "../../../images/faculty-classes-card-purple.png";
import cardOrangeBg from "../../../images/faculty-classes-card-orange.png";

import "./Classes.css";

const DAYS_OF_WEEK = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

function formatTime12(timeStr) {
  if (!timeStr) return "";
  const parts = String(timeStr).split(":");
  if (parts.length < 2) return String(timeStr);
  let hours = parseInt(parts[0], 10);
  const minutes = parts[1].slice(0, 2);
  if (isNaN(hours)) return String(timeStr);
  const ampm = hours >= 12 ? "PM" : "AM";
  hours = hours % 12;
  hours = hours ? hours : 12;
  const strHours = hours < 10 ? `0${hours}` : `${hours}`;
  return `${strHours}:${minutes} ${ampm}`;
}

function formatTimeRange(startTime, endTime) {
  if (!startTime && !endTime) return "—";
  if (startTime && !endTime) return formatTime12(startTime);
  return `${formatTime12(startTime)} - ${formatTime12(endTime)}`;
}

function getInitials(name) {
  if (!name) return "ST";
  return (
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part.charAt(0).toUpperCase())
      .join("") || "ST"
  );
}

function Classes() {
  const navigate = useNavigate();

  // Core Data
  const [classes, setClasses] = useState([]);
  const [summary, setSummary] = useState(null);
  const [timetable, setTimetable] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadError, setLoadError] = useState("");

  // Filters
  const [academicYear, setAcademicYear] = useState("All");
  const [semester, setSemester] = useState("All");
  const [section, setSection] = useState("All");
  const [day, setDay] = useState("All");

  // Tabs
  const [activeTab, setActiveTab] = useState("My Classes");

  // Pagination for My Classes table
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  // Row action menu dropdown
  const [activeMenuId, setActiveMenuId] = useState(null);
  const menuRef = useRef(null);

  // Class Details Modal
  const [detailsModalOpen, setDetailsModalOpen] = useState(false);
  const [selectedOffering, setSelectedOffering] = useState(null);
  const [courseDetails, setCourseDetails] = useState(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [detailsError, setDetailsError] = useState("");

  // Roster Export State
  const [exportingFormat, setExportingFormat] = useState(null);
  const [exportMenuOpen, setExportMenuOpen] = useState(false);
  const [exportSuccess, setExportSuccess] = useState("");
  const [exportError, setExportError] = useState("");
  const exportMenuRef = useRef(null);

  // Close menus on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setActiveMenuId(null);
      }
      if (exportMenuRef.current && !exportMenuRef.current.contains(event.target)) {
        setExportMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const [reloadKey, setReloadKey] = useState(0);

  // Fetch all data
  useEffect(() => {
    let ignore = false;

    async function loadData() {
      const params = {};
      if (academicYear !== "All" && academicYear) {
        params.academic_year = academicYear;
      }
      if (semester !== "All" && semester !== "") {
        params.semester = Number(semester);
      }
      if (section !== "All" && section !== "") {
        params.section = section;
      }
      if (day !== "All" && day !== "") {
        params.day = day;
      }

      try {
        const [coursesRes, summaryRes, timetableRes] =
          await Promise.allSettled([
            getFacultyCourses(params),
            getFacultyClassesSummary(params),
            getFacultyTimetable(),
          ]);

        if (ignore) return;

        // 1. Courses
        if (
          coursesRes.status === "fulfilled" &&
          coursesRes.value?.success &&
          Array.isArray(coursesRes.value.data)
        ) {
          setClasses(coursesRes.value.data);
          setLoadError("");
        } else {
          setClasses([]);
          if (coursesRes.status === "rejected") {
            const msg =
              coursesRes.reason?.response?.data?.message ||
              coursesRes.reason?.message;
            setLoadError(msg || "Unable to load assigned courses.");
          }
        }

        // 2. Summary
        if (
          summaryRes.status === "fulfilled" &&
          summaryRes.value?.success &&
          summaryRes.value.data
        ) {
          setSummary(summaryRes.value.data);
        } else {
          setSummary(null);
        }

        // 3. Timetable
        if (
          timetableRes.status === "fulfilled" &&
          timetableRes.value?.success &&
          Array.isArray(timetableRes.value.data)
        ) {
          setTimetable(timetableRes.value.data);
        } else {
          setTimetable([]);
        }
      } catch (err) {
        if (!ignore) {
          setLoadError(
            err?.response?.data?.message ||
              err?.message ||
              "Failed to load faculty classes."
          );
        }
      } finally {
        if (!ignore) {
          setLoading(false);
          setRefreshing(false);
        }
      }
    }

    loadData();

    return () => {
      ignore = true;
    };
  }, [academicYear, semester, section, day, reloadKey]);

  const handleRefresh = () => {
    invalidateApiCache("timetable");
    invalidateApiCache("faculty");
    setRefreshing(true);
    setReloadKey((prev) => prev + 1);
  };

  // Re-fetch when timetable updates occur elsewhere in application or window regains focus
  useEffect(() => {
    function handleTimetableUpdate() {
      invalidateApiCache("timetable");
      setReloadKey((prev) => prev + 1);
    }
    function handleStorage(e) {
      if (e.key === "sams_timetable_last_updated") {
        invalidateApiCache("timetable");
        setReloadKey((prev) => prev + 1);
      }
    }
    function handleFocus() {
      invalidateApiCache("timetable");
      setReloadKey((prev) => prev + 1);
    }

    window.addEventListener("sams:timetable-updated", handleTimetableUpdate);
    window.addEventListener("storage", handleStorage);
    window.addEventListener("focus", handleFocus);

    return () => {
      window.removeEventListener("sams:timetable-updated", handleTimetableUpdate);
      window.removeEventListener("storage", handleStorage);
      window.removeEventListener("focus", handleFocus);
    };
  }, []);

  // Dynamic filter options derived from complete classes dataset
  const filterOptions = useMemo(() => {
    const years = new Set();
    const sems = new Set();
    const secs = new Set();

    classes.forEach((c) => {
      if (c.academic_year) {
        years.add(formatAcademicYear(c.academic_year, c.semester));
      }
      if (c.semester !== null && c.semester !== undefined) sems.add(c.semester);
      if (c.section) secs.add(c.section);
    });

    return {
      academicYears: Array.from(years).sort(),
      semesters: Array.from(sems).sort((a, b) => Number(a) - Number(b)),
      sections: Array.from(secs).sort(),
    };
  }, [classes]);

  // Timetable lookup by offering_id
  const timetableByOffering = useMemo(() => {
    const map = {};
    timetable.forEach((entry) => {
      if (entry.offering_id) {
        const key = String(entry.offering_id);
        if (!map[key]) map[key] = [];
        map[key].push(entry);
      }
    });
    return map;
  }, [timetable]);

  // Calculate upcoming classes
  const upcomingClasses = useMemo(() => {
    const todayName = new Intl.DateTimeFormat("en-US", {
      weekday: "long",
    }).format(new Date());

    const now = new Date();
    const currentHours = now.getHours();
    const currentMinutes = now.getMinutes();
    const currentTimeStr = `${String(currentHours).padStart(2, "0")}:${String(
      currentMinutes
    ).padStart(2, "0")}`;

    // Filter timetable for today
    const todayEntries = timetable.filter(
      (e) => (e.day_of_week || "").toLowerCase() === todayName.toLowerCase()
    );

    // Upcoming entries today
    const todayUpcoming = todayEntries.filter((e) => {
      if (!e.end_time) return true;
      return e.end_time >= currentTimeStr;
    });

    if (todayUpcoming.length > 0) {
      return todayUpcoming.sort((a, b) =>
        (a.start_time || "").localeCompare(b.start_time || "")
      );
    }

    // If no more today, show upcoming this week
    const currentDayIndex = DAYS_OF_WEEK.findIndex(
      (d) => d.toLowerCase() === todayName.toLowerCase()
    );
    const restOfWeek = timetable.filter((e) => {
      const entryDayIndex = DAYS_OF_WEEK.findIndex(
        (d) => d.toLowerCase() === String(e.day_of_week || "").trim().toLowerCase()
      );
      return entryDayIndex > currentDayIndex;
    });

    return restOfWeek.sort((a, b) => {
      const aDayIndex = DAYS_OF_WEEK.findIndex(
        (d) => d.toLowerCase() === String(a.day_of_week || "").trim().toLowerCase()
      );
      const bDayIndex = DAYS_OF_WEEK.findIndex(
        (d) => d.toLowerCase() === String(b.day_of_week || "").trim().toLowerCase()
      );
      const dayDiff = aDayIndex - bDayIndex;
      if (dayDiff !== 0) return dayDiff;
      return (a.start_time || "").localeCompare(b.start_time || "");
    });
  }, [timetable]);

  // Fallback calculated metrics if summary endpoint is loading
  const calculatedMetrics = useMemo(() => {
    const totalClasses = classes.length;
    const uniqueStudents = new Set();
    const activeSemesters = new Set();

    classes.forEach((c) => {
      if (c.semester !== null && c.semester !== undefined) {
        activeSemesters.add(c.semester);
      }
    });

    let totalMinutes = 0;
    timetable.forEach((entry) => {
      if (entry.start_time && entry.end_time) {
        const [sh, sm] = entry.start_time.split(":").map(Number);
        const [eh, em] = entry.end_time.split(":").map(Number);
        const diff = eh * 60 + em - (sh * 60 + sm);
        if (diff > 0) totalMinutes += diff;
      } else {
        totalMinutes += 60;
      }
    });

    const weeklyHours = Math.round(totalMinutes / 60);

    return {
      totalClasses,
      totalStudents: uniqueStudents.size,
      totalHours: weeklyHours,
      activeSemesters: activeSemesters.size,
    };
  }, [classes, timetable]);

  // Pagination calculations
  const totalClassesCount = classes.length;
  const totalPages = Math.max(1, Math.ceil(totalClassesCount / pageSize));
  const paginatedClasses = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return classes.slice(start, start + pageSize);
  }, [classes, currentPage, pageSize]);

  // Open Details Modal
  const handleOpenDetails = async (offering) => {
    setSelectedOffering(offering);
    setDetailsModalOpen(true);
    setCourseDetails(null);
    setDetailsLoading(true);
    setDetailsError("");
    setExportError("");
    setExportSuccess("");
    setExportMenuOpen(false);
    setActiveMenuId(null);

    try {
      const res = await getFacultyCourseDetails(offering.course_id);
      if (res?.success && res.data) {
        setCourseDetails(res.data);
      } else {
        throw new Error(res?.message || "Failed to load course details.");
      }
    } catch (err) {
      setDetailsError(
        err?.response?.data?.message ||
          err?.message ||
          "Unable to load course and roster details."
      );
    } finally {
      setDetailsLoading(false);
    }
  };

  // Close Details Modal
  const handleCloseDetails = () => {
    setDetailsModalOpen(false);
    setSelectedOffering(null);
    setCourseDetails(null);
    setDetailsError("");
    setExportError("");
    setExportSuccess("");
    setExportMenuOpen(false);
  };

  // Export Class Roster
  const handleExportRoster = async (format) => {
    if (!selectedOffering?.offering_id || exportingFormat) return;
    setExportingFormat(format);
    setExportError("");
    setExportSuccess("");
    setExportMenuOpen(false);

    try {
      const response = await exportClassRoster(selectedOffering.offering_id, {
        format,
      });

      let filename = `Class_Roster_${selectedOffering.course_code || "Class"}_${selectedOffering.section || "Sec"}_${new Date().toISOString().slice(0, 10)}.${format}`;
      const disposition =
        response.headers?.["content-disposition"] ||
        response.headers?.get?.("content-disposition");
      if (disposition) {
        const match = disposition.match(
          /filename\*?=['"]?(?:UTF-\d['"])?([^;\r\n'"]*)['"]?/i
        );
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

      setExportSuccess(`Roster exported successfully (${format.toUpperCase()}).`);
      setTimeout(() => setExportSuccess(""), 4000);
    } catch (err) {
      console.error("Export roster failed:", err);
      let message = "Failed to export class roster. Please try again.";
      if (err?.response?.data instanceof Blob) {
        try {
          const text = await err.response.data.text();
          const parsed = JSON.parse(text);
          if (parsed?.message) message = parsed.message;
        } catch {
          // fallback
        }
      } else if (err?.response?.data?.message) {
        message = err.response.data.message;
      } else if (err?.message) {
        message = err.message;
      }
      setExportError(message);
    } finally {
      setExportingFormat(null);
    }
  };

  return (
    <div className="faculty-classes-container">
      {/* 1. Header Banner */}
      <section
        className="faculty-classes-banner"
        style={{
          backgroundImage: `url(${bannerBg})`,
        }}
        aria-label="My Classes Banner"
      >
        <div className="fc-banner-overlay" />
        <div className="fc-banner-content">
          <div className="fc-banner-left">
            <div className="fc-banner-icon-box" aria-hidden="true">
              <Users size={28} strokeWidth={2.4} color="#ffffff" />
            </div>
            <div className="fc-banner-headings">
              <h1 className="fc-banner-title">My Classes</h1>
              <p className="fc-banner-subtitle">
                View your assigned classes, timetable, and class details.
              </p>
            </div>
          </div>

          <div className="fc-banner-badge" aria-hidden="true">
            <span className="fc-badge-top">Teach Today</span>
            <span className="fc-badge-bottom">Build Tomorrow</span>
          </div>
        </div>
      </section>

      {/* 2. Filter Toolbar */}
      <section className="fc-filter-toolbar" aria-label="Class filters">
        <div className="fc-filter-group">
          <label className="fc-filter-field">
            <span className="fc-filter-label">Academic Year</span>
            <select
              className="fc-filter-select"
              value={academicYear}
              onChange={(e) => {
                setAcademicYear(e.target.value);
                setCurrentPage(1);
              }}
              aria-label="Filter by Academic Year"
            >
              <option value="All">All Academic Years</option>
              {filterOptions.academicYears.map((yr) => (
                <option key={yr} value={yr}>
                  {formatAcademicYear(yr)}
                </option>
              ))}
            </select>
          </label>

          <label className="fc-filter-field">
            <span className="fc-filter-label">Semester</span>
            <select
              className="fc-filter-select"
              value={semester}
              onChange={(e) => {
                setSemester(e.target.value);
                setCurrentPage(1);
              }}
              aria-label="Filter by Semester"
            >
              <option value="All">All Semesters</option>
              {filterOptions.semesters.map((sem) => (
                <option key={sem} value={String(sem)}>
                  Semester {sem}
                </option>
              ))}
            </select>
          </label>

          <label className="fc-filter-field">
            <span className="fc-filter-label">Section</span>
            <select
              className="fc-filter-select"
              value={section}
              onChange={(e) => {
                setSection(e.target.value);
                setCurrentPage(1);
              }}
              aria-label="Filter by Section"
            >
              <option value="All">All Sections</option>
              {filterOptions.sections.map((sec) => (
                <option key={sec} value={sec}>
                  Section {sec}
                </option>
              ))}
            </select>
          </label>

          <label className="fc-filter-field">
            <span className="fc-filter-label">Day</span>
            <select
              className="fc-filter-select"
              value={day}
              onChange={(e) => {
                setDay(e.target.value);
                setCurrentPage(1);
              }}
              aria-label="Filter by Day"
            >
              <option value="All">All Days</option>
              {DAYS_OF_WEEK.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </label>
        </div>

        <button
          type="button"
          className="fc-refresh-button"
          onClick={handleRefresh}
          disabled={loading || refreshing}
          aria-label="Refresh data"
          title="Refresh class and timetable data"
        >
          <RotateCw
            size={16}
            className={refreshing ? "fc-spin" : ""}
            aria-hidden="true"
          />
          <span>Refresh</span>
        </button>
      </section>

      {/* 3. 4 Summary Cards */}
      <section className="fc-cards-grid" aria-label="Classes summary">
        {/* Card 1: Total Classes */}
        <article
          className="fc-stat-card"
          style={{ backgroundImage: `url(${cardBlueBg})` }}
        >
          <div className="fc-stat-content">
            <div className="fc-stat-icon-wrap fc-icon-blue" aria-hidden="true">
              <BookOpen size={20} strokeWidth={2.4} color="#ffffff" />
            </div>
            <div className="fc-stat-info">
              <span className="fc-stat-label">Total Classes</span>
              <strong className="fc-stat-value">
                {loading
                  ? "—"
                  : summary?.total_offerings_count ?? calculatedMetrics.totalClasses}
              </strong>
              <small className="fc-stat-desc">Assigned this semester</small>
            </div>
          </div>
        </article>

        {/* Card 2: Total Students */}
        <article
          className="fc-stat-card"
          style={{ backgroundImage: `url(${cardGreenBg})` }}
        >
          <div className="fc-stat-content">
            <div className="fc-stat-icon-wrap fc-icon-green" aria-hidden="true">
              <Users size={20} strokeWidth={2.4} color="#ffffff" />
            </div>
            <div className="fc-stat-info">
              <span className="fc-stat-label">Total Students</span>
              <strong className="fc-stat-value">
                {loading
                  ? "—"
                  : summary?.enrolled_students_count ?? calculatedMetrics.totalStudents}
              </strong>
              <small className="fc-stat-desc">Across all classes</small>
            </div>
          </div>
        </article>

        {/* Card 3: Total Hours */}
        <article
          className="fc-stat-card"
          style={{ backgroundImage: `url(${cardPurpleBg})` }}
        >
          <div className="fc-stat-content">
            <div className="fc-stat-icon-wrap fc-icon-purple" aria-hidden="true">
              <Clock size={20} strokeWidth={2.4} color="#ffffff" />
            </div>
            <div className="fc-stat-info">
              <span className="fc-stat-label">Total Hours</span>
              <strong className="fc-stat-value">
                {loading
                  ? "—"
                  : summary?.weekly_hours ?? calculatedMetrics.totalHours}
              </strong>
              <small className="fc-stat-desc">Per week</small>
            </div>
          </div>
        </article>

        {/* Card 4: Active Semesters */}
        <article
          className="fc-stat-card"
          style={{ backgroundImage: `url(${cardOrangeBg})` }}
        >
          <div className="fc-stat-content">
            <div className="fc-stat-icon-wrap fc-icon-orange" aria-hidden="true">
              <Calendar size={20} strokeWidth={2.4} color="#ffffff" />
            </div>
            <div className="fc-stat-info">
              <span className="fc-stat-label">Active Semesters</span>
              <strong className="fc-stat-value">
                {loading
                  ? "—"
                  : summary?.active_semesters_count ??
                    calculatedMetrics.activeSemesters}
              </strong>
              <small className="fc-stat-desc">Current academic year</small>
            </div>
          </div>
        </article>
      </section>

      {/* 4. Main Content Tabs Navigation */}
      <div className="fc-tabs-container" role="tablist" aria-label="Class Views">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "My Classes"}
          className={`fc-tab-button${activeTab === "My Classes" ? " active" : ""}`}
          onClick={() => setActiveTab("My Classes")}
        >
          <span>My Classes</span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "Timetable"}
          className={`fc-tab-button${activeTab === "Timetable" ? " active" : ""}`}
          onClick={() => setActiveTab("Timetable")}
        >
          <span>Timetable</span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "Upcoming Classes"}
          className={`fc-tab-button${
            activeTab === "Upcoming Classes" ? " active" : ""
          }`}
          onClick={() => setActiveTab("Upcoming Classes")}
        >
          <span>Upcoming Classes</span>
          {upcomingClasses.length > 0 && (
            <span className="fc-tab-badge" aria-label={`${upcomingClasses.length} upcoming`}>
              {upcomingClasses.length}
            </span>
          )}
        </button>
      </div>

      {/* 5. Tab Content Panes */}

      {/* TAB 1: My Classes */}
      {activeTab === "My Classes" && (
        <section className="fc-classes-table-panel" aria-label="Classes Table">
          {loading ? (
            <div className="fc-loading-skeleton">
              <div className="fc-skeleton-row" />
              <div className="fc-skeleton-row" />
              <div className="fc-skeleton-row" />
            </div>
          ) : loadError ? (
            <div className="fc-empty-state fc-error-state" role="alert">
              <p className="fc-empty-title">Unable to Load Classes</p>
              <p className="fc-empty-subtitle">{loadError}</p>
              <button
                type="button"
                className="fc-button-outline"
                onClick={handleRefresh}
              >
                Retry
              </button>
            </div>
          ) : classes.length === 0 ? (
            <div className="fc-empty-state">
              <BookOpen size={42} strokeWidth={1.5} color="#94a3b8" />
              <p className="fc-empty-title">No Classes Assigned</p>
              <p className="fc-empty-subtitle">
                No course offerings match the selected filters for your account.
              </p>
            </div>
          ) : (
            <>
              <div className="fc-table-responsive">
                <table className="fc-table">
                  <thead>
                    <tr>
                      <th className="fc-th-num">#</th>
                      <th>Course Code</th>
                      <th>Course Name</th>
                      <th>Semester</th>
                      <th>Section</th>
                      <th>Day(s)</th>
                      <th>Time</th>
                      <th>Room / Lab</th>
                      <th>Students</th>
                      <th className="fc-th-actions">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedClasses.map((item, index) => {
                      const rowNum = (currentPage - 1) * pageSize + index + 1;
                      const offeringTT =
                        timetableByOffering[String(item.offering_id)] || [];

                      // Determine day(s) display
                      const daysText =
                        item.days_display && item.days_display !== "Not scheduled"
                          ? item.days_display
                          : offeringTT.length > 0
                          ? Array.from(
                              new Set(offeringTT.map((t) => t.day_of_week?.slice(0, 3)))
                            ).join(", ")
                          : "—";

                      // Determine time display
                      let timeText = item.time_display || "—";
                      if (timeText === "—" && offeringTT.length > 0) {
                        const first = offeringTT[0];
                        timeText = formatTimeRange(first.start_time, first.end_time);
                      }

                      // Room display
                      const roomText =
                        item.room ||
                        (offeringTT.length > 0 ? offeringTT[0].room : "Room TBA") ||
                        "Room TBA";

                      return (
                        <tr key={item.offering_id}>
                          <td className="fc-td-num">{rowNum}</td>
                          <td className="fc-td-code">{item.course_code}</td>
                          <td className="fc-td-name">{item.course_name}</td>
                          <td className="fc-td-semester">{item.semester}</td>
                          <td className="fc-td-section">{item.section}</td>
                          <td className="fc-td-days">{daysText}</td>
                          <td className="fc-td-time">{timeText}</td>
                          <td className="fc-td-room">{roomText}</td>
                          <td className="fc-td-students">
                            {item.student_count ?? 0}
                          </td>
                          <td className="fc-td-actions">
                            <div className="fc-action-cell-wrap">
                              <button
                                type="button"
                                className="fc-view-pill-btn"
                                onClick={() => handleOpenDetails(item)}
                                aria-label={`View details for ${item.course_code}`}
                              >
                                <Eye size={15} strokeWidth={2.2} />
                                <span>View</span>
                              </button>

                              <div className="fc-dropdown-wrap">
                                <button
                                  type="button"
                                  className="fc-kebab-btn"
                                  aria-label="More options"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setActiveMenuId(
                                      activeMenuId === item.offering_id
                                        ? null
                                        : item.offering_id
                                    );
                                  }}
                                >
                                  <MoreVertical size={16} />
                                </button>

                                {activeMenuId === item.offering_id && (
                                  <div
                                    className="fc-dropdown-menu"
                                    ref={menuRef}
                                    role="menu"
                                  >
                                    <button
                                      type="button"
                                      className="fc-dropdown-item"
                                      role="menuitem"
                                      onClick={() => handleOpenDetails(item)}
                                    >
                                      <Eye size={14} />
                                      <span>View Details</span>
                                    </button>
                                    <button
                                      type="button"
                                      className="fc-dropdown-item"
                                      role="menuitem"
                                      onClick={() => {
                                        setActiveMenuId(null);
                                        navigate("/faculty/attendance");
                                      }}
                                    >
                                      <CheckCircle2 size={14} />
                                      <span>Take Attendance</span>
                                    </button>
                                  </div>
                                )}
                              </div>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="fc-pagination-bar">
                <span className="fc-pagination-text">
                  Showing {(currentPage - 1) * pageSize + 1} to{" "}
                  {Math.min(currentPage * pageSize, totalClassesCount)} of{" "}
                  {totalClassesCount} classes
                </span>

                <div className="fc-pagination-controls">
                  <button
                    type="button"
                    className="fc-page-arrow"
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                    aria-label="Previous page"
                  >
                    <ChevronLeft size={16} />
                  </button>

                  {Array.from({ length: totalPages }, (_, i) => i + 1).map((pg) => (
                    <button
                      key={pg}
                      type="button"
                      className={`fc-page-num${currentPage === pg ? " active" : ""}`}
                      onClick={() => setCurrentPage(pg)}
                      aria-label={`Page ${pg}`}
                      aria-current={currentPage === pg ? "page" : undefined}
                    >
                      {pg}
                    </button>
                  ))}

                  <button
                    type="button"
                    className="fc-page-arrow"
                    onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                    disabled={currentPage === totalPages}
                    aria-label="Next page"
                  >
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            </>
          )}

          {/* Class Information Panel at Bottom */}
          <div className="fc-class-info-box" role="region" aria-label="Class Information">
            <div className="fc-info-icon-col" aria-hidden="true">
              <div className="fc-info-circle">
                <Info size={19} strokeWidth={2.4} color="#0d6efd" />
              </div>
            </div>
            <div className="fc-info-text-col">
              <strong className="fc-info-heading">Class Information</strong>
              <p className="fc-info-desc">
                Click on a class to view detailed information, attendance records, and student
                list. You can also download the class roster or export attendance data.
              </p>
            </div>
          </div>
        </section>
      )}

      {/* TAB 2: Timetable */}
      {activeTab === "Timetable" && (
        <section className="fc-timetable-view-panel" aria-label="Faculty Timetable">
          <div className="fc-timetable-grid">
            {DAYS_OF_WEEK.map((dayName) => {
              const dayEntries = timetable.filter(
                (e) => (e.day_of_week || "").toLowerCase() === dayName.toLowerCase()
              );

              return (
                <div key={dayName} className="fc-timetable-day-card">
                  <header className="fc-day-header">
                    <strong>{dayName}</strong>
                    <span className="fc-day-count">
                      {dayEntries.length}{" "}
                      {dayEntries.length === 1 ? "Class" : "Classes"}
                    </span>
                  </header>

                  <div className="fc-day-slots-list">
                    {dayEntries.length === 0 ? (
                      <p className="fc-no-slots">No classes scheduled</p>
                    ) : (
                      dayEntries.map((slot) => (
                        <div
                          key={slot.timetable_entry_id}
                          className="fc-slot-item"
                        >
                          <div className="fc-slot-time">
                            <Clock size={13} />
                            <span>
                              {formatTimeRange(slot.start_time, slot.end_time)}
                            </span>
                          </div>
                          <strong className="fc-slot-course">
                            {slot.course_code} — {slot.course_name}
                          </strong>
                          <div className="fc-slot-details">
                            <span>Sec: {slot.section || "A"}</span>
                            <span>·</span>
                            <span>{slot.room || "Room TBA"}</span>
                          </div>
                          {slot.active_adjustment && (
                            <span className="fc-substitute-pill">
                              Substitute: {slot.effective_faculty_name}
                            </span>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* TAB 3: Upcoming Classes */}
      {activeTab === "Upcoming Classes" && (
        <section className="fc-upcoming-view-panel" aria-label="Upcoming Classes">
          {upcomingClasses.length === 0 ? (
            <div className="fc-empty-state">
              <CalendarDays size={40} color="#94a3b8" />
              <p className="fc-empty-title">No Upcoming Classes</p>
              <p className="fc-empty-subtitle">
                You have no scheduled classes remaining for today or this week.
              </p>
            </div>
          ) : (
            <div className="fc-upcoming-list">
              {upcomingClasses.map((item) => (
                <article
                  key={item.timetable_entry_id}
                  className="fc-upcoming-card"
                >
                  <div className="fc-upcoming-left">
                    <div className="fc-upcoming-day-badge">
                      <span>{item.day_of_week}</span>
                      <strong>{formatTimeRange(item.start_time, item.end_time)}</strong>
                    </div>
                    <div className="fc-upcoming-info">
                      <h3>
                        {item.course_code} — {item.course_name}
                      </h3>
                      <div className="fc-upcoming-tags">
                        <span className="fc-tag">Section {item.section || "A"}</span>
                        <span className="fc-tag">
                          <MapPin size={13} />
                          {item.room || "Room TBA"}
                        </span>
                        {item.semester && (
                          <span className="fc-tag">Semester {item.semester}</span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="fc-upcoming-actions">
                    <button
                      type="button"
                      className="fc-btn-take-attendance"
                      onClick={() => navigate("/faculty/attendance")}
                    >
                      <CheckCircle2 size={16} />
                      <span>Take Attendance</span>
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      )}

      {/* Class Details Modal */}
      {detailsModalOpen && selectedOffering && (
        <div
          className="fc-modal-backdrop"
          onClick={handleCloseDetails}
          role="presentation"
        >
          <div
            className="fc-modal-dialog"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="fc-modal-title"
          >
            <header className="fc-modal-header">
              <div className="fc-modal-title-wrap">
                <div className="fc-modal-icon" aria-hidden="true">
                  <GraduationCap size={22} color="#0d6efd" />
                </div>
                <div>
                  <h2 id="fc-modal-title" className="fc-modal-title">
                    {selectedOffering.course_code} — {selectedOffering.course_name}
                  </h2>
                  <p className="fc-modal-subtitle">
                    Section {selectedOffering.section} · Semester{" "}
                    {selectedOffering.semester} ·{" "}
                    {formatAcademicYear(
                      selectedOffering.academic_year,
                      selectedOffering.semester
                    )}
                  </p>
                </div>
              </div>

              <button
                type="button"
                className="fc-modal-close-btn"
                onClick={handleCloseDetails}
                aria-label="Close modal"
              >
                <X size={20} />
              </button>
            </header>

            <div className="fc-modal-body">
              {/* Offering Summary Strip */}
              <div className="fc-modal-meta-grid">
                <div className="fc-meta-card">
                  <span className="fc-meta-label">Course Code</span>
                  <strong>{selectedOffering.course_code}</strong>
                </div>
                <div className="fc-meta-card">
                  <span className="fc-meta-label">Credits</span>
                  <strong>{selectedOffering.credits ?? "—"}</strong>
                </div>
                <div className="fc-meta-card">
                  <span className="fc-meta-label">Room / Lab</span>
                  <strong>{selectedOffering.room || "Room TBA"}</strong>
                </div>
                <div className="fc-meta-card">
                  <span className="fc-meta-label">Enrolled Students</span>
                  <strong>{selectedOffering.student_count ?? 0}</strong>
                </div>
              </div>

              {/* Schedule Section */}
              <div className="fc-modal-section">
                <h3 className="fc-section-title">Schedule &amp; Timings</h3>
                {selectedOffering.timetable_entries &&
                selectedOffering.timetable_entries.length > 0 ? (
                  <div className="fc-schedule-pills-list">
                    {selectedOffering.timetable_entries.map((entry) => (
                      <div
                        key={entry.timetable_entry_id}
                        className="fc-schedule-pill-item"
                      >
                        <Calendar size={14} />
                        <strong>{entry.day_of_week}</strong>
                        <span>
                          {formatTimeRange(entry.start_time, entry.end_time)}
                        </span>
                        {entry.room && <span className="fc-pill-room">{entry.room}</span>}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="fc-empty-text">No weekly schedule assigned.</p>
                )}
              </div>

              {/* Enrolled Students Roster */}
              <div className="fc-modal-section">
                <div className="fc-section-header-row">
                  <div className="fc-roster-title-group">
                    <h3 className="fc-section-title">Enrolled Students</h3>
                    <span className="fc-badge-count">
                      {courseDetails?.offerings?.find(
                        (o) => o.offering_id === selectedOffering.offering_id
                      )?.students?.length ??
                        selectedOffering.student_count ??
                        0}{" "}
                      Students
                    </span>
                  </div>
                  <div className="fc-roster-quick-export-actions">
                    <button
                      type="button"
                      className="fc-btn-quick-export"
                      onClick={() => handleExportRoster("xlsx")}
                      disabled={Boolean(exportingFormat)}
                      title="Export Roster as Excel (.xlsx)"
                    >
                      <FileSpreadsheet size={13} color="#16a34a" />
                      <span>Excel</span>
                    </button>
                    <button
                      type="button"
                      className="fc-btn-quick-export"
                      onClick={() => handleExportRoster("pdf")}
                      disabled={Boolean(exportingFormat)}
                      title="Export Roster as PDF (.pdf)"
                    >
                      <FileText size={13} color="#dc2626" />
                      <span>PDF</span>
                    </button>
                    <button
                      type="button"
                      className="fc-btn-quick-export"
                      onClick={() => handleExportRoster("csv")}
                      disabled={Boolean(exportingFormat)}
                      title="Export Roster as CSV (.csv)"
                    >
                      <Download size={13} color="#2563eb" />
                      <span>CSV</span>
                    </button>
                  </div>
                </div>

                {detailsLoading ? (
                  <div className="fc-loading-skeleton">
                    <div className="fc-skeleton-row" />
                    <div className="fc-skeleton-row" />
                  </div>
                ) : detailsError ? (
                  <p className="fc-error-text">{detailsError}</p>
                ) : (
                  (() => {
                    const matchedOffering = courseDetails?.offerings?.find(
                      (o) => o.offering_id === selectedOffering.offering_id
                    );
                    const students = matchedOffering?.students || [];

                    if (students.length === 0) {
                      return (
                        <p className="fc-empty-text">
                          No active students currently enrolled in this offering.
                        </p>
                      );
                    }

                    return (
                      <div className="fc-roster-table-wrap">
                        <table className="fc-roster-table">
                          <thead>
                            <tr>
                              <th>Student</th>
                              <th>Enrollment No</th>
                              <th>Email</th>
                              <th>Status</th>
                            </tr>
                          </thead>
                          <tbody>
                            {students.map((student) => (
                              <tr key={student.student_id}>
                                <td>
                                  <div className="fc-student-cell">
                                    <div className="fc-student-avatar">
                                      {getInitials(student.name)}
                                    </div>
                                    <span className="fc-student-name">
                                      {student.name}
                                    </span>
                                  </div>
                                </td>
                                <td>{student.enrollment_no || "—"}</td>
                                <td>{student.email || "—"}</td>
                                <td>
                                  <span className="fc-active-badge">
                                    {student.enrollment_status || "Active"}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    );
                  })()
                )}
              </div>
            </div>

            {/* Feedback notifications */}
            {exportSuccess && (
              <div className="fc-modal-feedback-strip fc-feedback-success" role="status">
                <Check size={14} />
                <span>{exportSuccess}</span>
              </div>
            )}
            {exportError && (
              <div className="fc-modal-feedback-strip fc-feedback-error" role="alert">
                <Info size={14} />
                <span>{exportError}</span>
              </div>
            )}

            <footer className="fc-modal-footer">
              <div className="fc-modal-footer-left">
                <div className="fc-export-dropdown-wrap" ref={exportMenuRef}>
                  <button
                    type="button"
                    className="fc-modal-export-btn"
                    onClick={() => setExportMenuOpen((prev) => !prev)}
                    disabled={Boolean(exportingFormat)}
                    aria-haspopup="true"
                    aria-expanded={exportMenuOpen}
                  >
                    <Download size={14} />
                    <span>
                      {exportingFormat
                        ? `Exporting ${exportingFormat.toUpperCase()}...`
                        : "Export Roster"}
                    </span>
                    <ChevronDown size={13} />
                  </button>

                  {exportMenuOpen && (
                    <div className="fc-export-menu" role="menu">
                      <button
                        type="button"
                        className="fc-export-menu-item"
                        role="menuitem"
                        onClick={() => handleExportRoster("xlsx")}
                      >
                        <FileSpreadsheet size={15} color="#16a34a" />
                        <span>Excel Spreadsheet (.xlsx)</span>
                      </button>
                      <button
                        type="button"
                        className="fc-export-menu-item"
                        role="menuitem"
                        onClick={() => handleExportRoster("pdf")}
                      >
                        <FileText size={15} color="#dc2626" />
                        <span>PDF Document (.pdf)</span>
                      </button>
                      <button
                        type="button"
                        className="fc-export-menu-item"
                        role="menuitem"
                        onClick={() => handleExportRoster("csv")}
                      >
                        <Download size={15} color="#2563eb" />
                        <span>CSV Spreadsheet (.csv)</span>
                      </button>
                    </div>
                  )}
                </div>

                <button
                  type="button"
                  className="fc-modal-link-btn"
                  onClick={() => {
                    handleCloseDetails();
                    navigate(`/faculty/reports?offering_id=${selectedOffering.offering_id}`);
                  }}
                  title="View and export full attendance reports for this offering"
                >
                  <FileText size={14} />
                  <span>Attendance Reports</span>
                </button>
              </div>

              <div className="fc-modal-footer-right">
                <button
                  type="button"
                  className="fc-modal-secondary-btn"
                  onClick={handleCloseDetails}
                >
                  Close
                </button>
                <button
                  type="button"
                  className="fc-modal-primary-btn"
                  onClick={() => {
                    handleCloseDetails();
                    navigate("/faculty/attendance");
                  }}
                >
                  <CheckCircle2 size={16} />
                  <span>Take Attendance</span>
                </button>
              </div>
            </footer>
          </div>
        </div>
      )}
    </div>
  );
}

export default Classes;
