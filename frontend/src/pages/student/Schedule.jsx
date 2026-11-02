import { useEffect, useMemo, useState, useCallback } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faCalendarDays,
  faCalendarDay,
  faClock,
  faLocationDot,
  faUserTie,
  faGraduationCap,
  faBook,
  faChevronLeft,
  faChevronRight,
  faUtensils,
  faCheckCircle,
  faCircleInfo,
  faChartPie,
  faSpinner,
  faTriangleExclamation,
  faRotateRight,
  faXmark,
  faLayerGroup,
} from "@fortawesome/free-solid-svg-icons";
import PageState from "../../components/PageState";
import { getStudentTimetable } from "../../services/timetableService";
import { getStudentProfile } from "../../services/studentService";
import { getStudentAttendanceSummary } from "../../services/attendanceService";
import "./Schedule.css";

const WEEK_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];

// Standard institutional time slots (fallback & baseline)
const STANDARD_SLOTS = [
  { start: "08:40", end: "09:40" },
  { start: "09:40", end: "10:40" },
  { start: "10:40", end: "11:40" },
  { start: "11:40", end: "12:40" },
  { start: "12:40", end: "13:40" },
  { start: "13:40", end: "14:40" },
  { start: "14:40", end: "15:40" },
];

// Curated pastel palettes for course cards, dots, and legend
const PASTEL_PALETTES = [
  {
    id: "blue",
    cardBg: "#f0f7ff",
    cardBorder: "#bae6fd",
    codeColor: "#0284c7",
    badgeBg: "#e0f2fe",
    dotColor: "#0284c7",
  },
  {
    id: "green",
    cardBg: "#f0fdf4",
    cardBorder: "#bbf7d0",
    codeColor: "#16a34a",
    badgeBg: "#dcfce7",
    dotColor: "#16a34a",
  },
  {
    id: "purple",
    cardBg: "#faf5ff",
    cardBorder: "#e9d5ff",
    codeColor: "#9333ea",
    badgeBg: "#f3e8ff",
    dotColor: "#9333ea",
  },
  {
    id: "pink",
    cardBg: "#fdf2f8",
    cardBorder: "#fbcfe8",
    codeColor: "#db2777",
    badgeBg: "#fce7f3",
    dotColor: "#db2777",
  },
  {
    id: "amber",
    cardBg: "#fffbeb",
    cardBorder: "#fde68a",
    codeColor: "#d97706",
    badgeBg: "#fef3c7",
    dotColor: "#d97706",
  },
  {
    id: "cyan",
    cardBg: "#ecfeff",
    cardBorder: "#a5f3fc",
    codeColor: "#0891b2",
    badgeBg: "#cffafe",
    dotColor: "#0891b2",
  },
  {
    id: "indigo",
    cardBg: "#eef2ff",
    cardBorder: "#c7d2fe",
    codeColor: "#4f46e5",
    badgeBg: "#e0e7ff",
    dotColor: "#4f46e5",
  },
];

function formatTime12(timeStr) {
  if (!timeStr) return "--:--";
  const match = String(timeStr).match(/^(\d{1,2}):(\d{2})/);
  if (!match) return timeStr;
  const hours = Number(match[1]);
  const minutes = match[2];
  const ampm = hours >= 12 ? "PM" : "AM";
  const h12 = hours % 12 || 12;
  const padH = String(h12).padStart(2, "0");
  return `${padH}:${minutes} ${ampm}`;
}

function getMondayOfDate(d) {
  const date = new Date(d);
  const day = date.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  date.setDate(date.getDate() + diff);
  date.setHours(0, 0, 0, 0);
  return date;
}

function getISOWeekNumber(d) {
  const target = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  const dayNr = target.getUTCDay() || 7;
  target.setUTCDate(target.getUTCDate() + 4 - dayNr);
  const yearStart = new Date(Date.UTC(target.getUTCFullYear(), 0, 1));
  return Math.ceil(((target - yearStart) / 86400000 + 1) / 7);
}

function Schedule() {
  const [timetable, setTimetable] = useState([]);
  const [profile, setProfile] = useState(null);
  const [attendanceSummary, setAttendanceSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  // View state
  const [viewMode, setViewMode] = useState("week"); // 'week' | 'day'
  const [currentWeekStart, setCurrentWeekStart] = useState(() => getMondayOfDate(new Date()));
  const [selectedDay, setSelectedDay] = useState(() => {
    const todayName = new Intl.DateTimeFormat("en-US", { weekday: "long" }).format(new Date());
    return WEEK_DAYS.includes(todayName) ? todayName : "Monday";
  });
  const [selectedClassModal, setSelectedClassModal] = useState(null);

  // Current real-time weekday
  const todayWeekday = useMemo(() => {
    return new Intl.DateTimeFormat("en-US", { weekday: "long" }).format(new Date());
  }, []);

  // Fetch timetable, profile, and attendance data concurrently
  useEffect(() => {
    let ignore = false;

    async function fetchData() {
      try {
        setLoading(true);
        setError("");

        const [timetableRes, profileRes, attendanceRes] = await Promise.allSettled([
          getStudentTimetable(),
          getStudentProfile(),
          getStudentAttendanceSummary(),
        ]);

        if (ignore) return;

        if (timetableRes.status === "fulfilled" && timetableRes.value?.success) {
          setTimetable(Array.isArray(timetableRes.value.data) ? timetableRes.value.data : []);
        } else {
          const errMsg =
            timetableRes.status === "rejected"
              ? timetableRes.reason?.response?.data?.message || timetableRes.reason?.message
              : timetableRes.value?.message;
          throw new Error(errMsg || "Failed to load class timetable.");
        }

        if (profileRes.status === "fulfilled" && profileRes.value?.success) {
          setProfile(profileRes.value.data || null);
        }

        if (attendanceRes.status === "fulfilled" && attendanceRes.value?.success) {
          setAttendanceSummary(attendanceRes.value || null);
        }
      } catch (err) {
        if (!ignore) {
          setError(
            err?.response?.data?.message ||
              err?.message ||
              "Unable to load your schedule. Please try again later."
          );
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    }

    fetchData();

    return () => {
      ignore = true;
    };
  }, [reloadKey]);

  const handleRetry = () => {
    setReloadKey((prev) => prev + 1);
  };

  // Week navigation handlers
  const handlePrevWeek = () => {
    setCurrentWeekStart((prev) => {
      const d = new Date(prev);
      d.setDate(d.getDate() - 7);
      return d;
    });
  };

  const handleNextWeek = () => {
    setCurrentWeekStart((prev) => {
      const d = new Date(prev);
      d.setDate(d.getDate() + 7);
      return d;
    });
  };

  const handleToday = () => {
    setCurrentWeekStart(getMondayOfDate(new Date()));
    if (WEEK_DAYS.includes(todayWeekday)) {
      setSelectedDay(todayWeekday);
    }
  };

  // Calculate the dates for the 5 weekdays of the currently selected week
  const weekDayDates = useMemo(() => {
    return WEEK_DAYS.map((dayName, idx) => {
      const d = new Date(currentWeekStart);
      d.setDate(currentWeekStart.getDate() + idx);
      const isToday = d.toDateString() === new Date().toDateString();
      return {
        dayName,
        date: d,
        dateFormatted: d.toLocaleDateString("en-US", { month: "short", day: "numeric" }),
        isToday,
      };
    });
  }, [currentWeekStart]);

  // Formatted date range: e.g. "May 12 – May 18, 2025"
  const weekDateRangeString = useMemo(() => {
    const monday = new Date(currentWeekStart);
    const sunday = new Date(currentWeekStart);
    sunday.setDate(monday.getDate() + 6);
    const fmt = (d) => d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
    return `${fmt(monday)} – ${fmt(sunday)}, ${sunday.getFullYear()}`;
  }, [currentWeekStart]);

  // Week number calculation
  const weekNumber = useMemo(() => {
    return getISOWeekNumber(currentWeekStart);
  }, [currentWeekStart]);

  // Map each unique course code to a distinct pastel palette
  const coursePalettesMap = useMemo(() => {
    const map = new Map();
    let paletteIdx = 0;

    timetable.forEach((entry) => {
      const code = (entry.course_code || "").trim();
      if (code && !map.has(code)) {
        map.set(code, PASTEL_PALETTES[paletteIdx % PASTEL_PALETTES.length]);
        paletteIdx++;
      }
    });

    return map;
  }, [timetable]);

  const getCoursePalette = useCallback(
    (courseCode) => {
      const code = (courseCode || "").trim();
      return (
        coursePalettesMap.get(code) ||
        PASTEL_PALETTES[0]
      );
    },
    [coursePalettesMap]
  );

  // Group timetable entries by weekday
  const groupedByDay = useMemo(() => {
    const map = {};
    WEEK_DAYS.forEach((d) => {
      map[d] = [];
    });

    timetable.forEach((entry) => {
      const entryDay = entry.day_of_week;
      const matchedDay = WEEK_DAYS.find(
        (d) => d.toLowerCase() === String(entryDay).toLowerCase()
      );
      if (matchedDay) {
        map[matchedDay].push(entry);
      }
    });

    // Sort entries for each day chronologically
    Object.keys(map).forEach((d) => {
      map[d].sort((a, b) => String(a.start_time || "").localeCompare(String(b.start_time || "")));
    });

    return map;
  }, [timetable]);

  // Extract distinct time slots dynamically (merging with standard slots)
  const timeSlots = useMemo(() => {
    const slotMap = new Map();

    // Seed standard institutional slots
    STANDARD_SLOTS.forEach((slot) => {
      const key = `${slot.start}-${slot.end}`;
      slotMap.set(key, {
        start: slot.start,
        end: slot.end,
        label: `${formatTime12(slot.start)} – ${formatTime12(slot.end)}`,
      });
    });

    // Merge any additional custom slots from actual entries
    timetable.forEach((entry) => {
      if (entry.start_time && entry.end_time) {
        const s = entry.start_time.slice(0, 5);
        const e = entry.end_time.slice(0, 5);
        const key = `${s}-${e}`;
        if (!slotMap.has(key)) {
          slotMap.set(key, {
            start: s,
            end: e,
            label: `${formatTime12(s)} – ${formatTime12(e)}`,
          });
        }
      }
    });

    const sorted = Array.from(slotMap.values()).sort((a, b) =>
      a.start.localeCompare(b.start)
    );

    // Identify if any midday slot has zero classes across Monday-Friday -> Lunch Break
    return sorted.map((slot, index) => {
      const classesInSlot = timetable.filter((entry) => {
        const s = (entry.start_time || "").slice(0, 5);
        return s === slot.start;
      });

      const isMidday =
        (slot.start >= "11:30" && slot.start <= "13:30") ||
        (slot.end >= "12:30" && slot.end <= "14:00");

      const hasClassesBefore = sorted.slice(0, index).some((prevSlot) =>
        timetable.some((e) => (e.start_time || "").slice(0, 5) === prevSlot.start)
      );

      const hasClassesAfter = sorted.slice(index + 1).some((nextSlot) =>
        timetable.some((e) => (e.start_time || "").slice(0, 5) === nextSlot.start)
      );

      const isLunchBreak =
        classesInSlot.length === 0 && isMidday && hasClassesBefore && hasClassesAfter;

      return {
        ...slot,
        isLunchBreak,
      };
    });
  }, [timetable]);

  // Dynamic course legend
  const courseLegend = useMemo(() => {
    const seen = new Set();
    const list = [];

    timetable.forEach((entry) => {
      const code = (entry.course_code || "").trim();
      if (code && !seen.has(code)) {
        seen.add(code);
        list.push({
          course_code: code,
          course_name: entry.course_name || "Course",
          department_name: entry.department_name || "",
          palette: getCoursePalette(code),
        });
      }
    });

    return list.sort((a, b) => a.course_code.localeCompare(b.course_code));
  }, [timetable, getCoursePalette]);

  // Today's classes (or selected day classes)
  const todaysClassesList = useMemo(() => {
    const targetDay = WEEK_DAYS.includes(todayWeekday) ? todayWeekday : "Monday";
    return groupedByDay[targetDay] || [];
  }, [groupedByDay, todayWeekday]);

  // Quick Info statistics (accurately calculated without fabricated data)
  const quickInfoStats = useMemo(() => {
    const totalClassesThisWeek = timetable.length;

    // Completed classes: only count if backend recorded closed attendance sessions for this student
    const completedSessions = attendanceSummary?.overall?.total_sessions ?? 0;

    // Upcoming classes
    const upcomingCount = Math.max(0, totalClassesThisWeek - completedSessions);

    // Attendance rate
    const rawRate =
      attendanceSummary?.overall?.attendance_percentage ??
      profile?.stats?.attendance_percentage;

    const hasRealAttendance =
      attendanceSummary?.overall?.total_sessions > 0 ||
      (profile?.stats?.total_attendance_records || 0) > 0;

    const attendanceRateDisplay = hasRealAttendance && rawRate != null ? `${rawRate}%` : "N/A";

    return {
      totalClassesThisWeek,
      completedSessions,
      upcomingCount,
      attendanceRateDisplay,
      hasRealAttendance,
    };
  }, [timetable, attendanceSummary, profile]);

  const hasAnyClasses = timetable.length > 0;

  // Render class card inside slot
  const renderClassCard = (entry) => {
    const palette = getCoursePalette(entry.course_code);
    return (
      <article
        key={entry.timetable_entry_id}
        className="tt-class-card"
        style={{
          backgroundColor: palette.cardBg,
          borderColor: palette.cardBorder,
        }}
        onClick={() => setSelectedClassModal(entry)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            setSelectedClassModal(entry);
          }
        }}
        aria-label={`View details for ${entry.course_name} (${entry.course_code})`}
      >
        <div className="tt-card-header">
          <span
            className="tt-card-code"
            style={{ color: palette.codeColor, backgroundColor: palette.badgeBg }}
          >
            <FontAwesomeIcon icon={faBook} className="tt-card-book-icon" />
            {entry.course_code}
          </span>

          {entry.active_adjustment && (
            <span
              className="tt-card-substitute-dot"
              title="Substitute faculty assigned"
              aria-label="Substitute faculty assigned"
            />
          )}
        </div>

        <h4 className="tt-card-name" title={entry.course_name}>
          {entry.course_name}
        </h4>

        <div className="tt-card-footer">
          <span className="tt-card-room">
            Room: {entry.room || "TBA"}
          </span>
          {(entry.effective_faculty_name || entry.faculty_name) && (
            <span className="tt-card-faculty" title={entry.effective_faculty_name || entry.faculty_name}>
              {entry.effective_faculty_name || entry.faculty_name}
            </span>
          )}
        </div>
      </article>
    );
  };

  return (
    <div className="timetable-page">
      {/* ========================================================
          A. TIMETABLE PAGE BANNER
          ======================================================== */}
      <section className="timetable-banner">
        <img
          src="/image/student_timetable_card.png"
          alt="Student Timetable Banner"
          className="timetable-banner-bg-img"
          aria-hidden="true"
        />

        <div className="timetable-banner-content">
          <div className="timetable-banner-left">
            <div className="timetable-banner-icon">
              <FontAwesomeIcon icon={faCalendarDays} />
            </div>

            <div className="timetable-banner-titles">
              <h1 className="timetable-title">Timetable</h1>
              <p className="timetable-subtitle">
                View your class schedule for the current week.
              </p>
            </div>
          </div>

          {/* Center illustration spacer to keep middle clear for background illustration */}
          <div className="timetable-banner-illustration" aria-hidden="true" />

          {/* Right academic details cards */}
          <div className="timetable-banner-right">
            <div className="timetable-badge-card">
              <div className="badge-card-icon">
                <FontAwesomeIcon icon={faCalendarDays} />
              </div>
              <div className="badge-card-info">
                <span className="badge-card-label">Academic Year</span>
                <strong className="badge-card-value">
                  {profile?.academic_year || "2026 - 2027"}
                </strong>
              </div>
            </div>

            <div className="timetable-badge-card">
              <div className="badge-card-info">
                <span className="badge-card-label">Semester</span>
                <strong className="badge-card-value">
                  {profile?.semester ? `Semester ${profile.semester}` : "Current Semester"}
                </strong>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ========================================================
          B. WEEK NAVIGATION AND VIEW CONTROLS TOOLBAR
          ======================================================== */}
      <nav className="timetable-controls" aria-label="Timetable controls toolbar">
        <div className="timetable-controls-left">
          <button
            type="button"
            className="tt-nav-arrow"
            onClick={handlePrevWeek}
            aria-label="Previous week"
            title="Previous week"
          >
            <FontAwesomeIcon icon={faChevronLeft} />
          </button>

          <div className="tt-week-info">
            <strong className="tt-week-range">{weekDateRangeString}</strong>
            <span className="tt-week-number">Week {weekNumber}</span>
          </div>

          <button
            type="button"
            className="tt-nav-arrow"
            onClick={handleNextWeek}
            aria-label="Next week"
            title="Next week"
          >
            <FontAwesomeIcon icon={faChevronRight} />
          </button>
        </div>

        <div className="timetable-controls-right">
          <div className="tt-view-toggle" role="group" aria-label="View toggle">
            <button
              type="button"
              className={`tt-toggle-btn ${viewMode === "week" ? "active" : ""}`}
              onClick={() => setViewMode("week")}
            >
              Week View
            </button>
            <button
              type="button"
              className={`tt-toggle-btn ${viewMode === "day" ? "active" : ""}`}
              onClick={() => setViewMode("day")}
            >
              Day View
            </button>
          </div>

          <button
            type="button"
            className="tt-today-btn"
            onClick={handleToday}
            title="Jump to current week and today"
          >
            <FontAwesomeIcon icon={faCalendarDay} />
            <span>Today</span>
          </button>
        </div>
      </nav>

      {/* ========================================================
          LOADING / ERROR / EMPTY STATES
          ======================================================== */}
      {loading && (
        <div className="timetable-loading-card">
          <FontAwesomeIcon icon={faSpinner} spin className="tt-spin-icon" />
          <h3>Loading Timetable</h3>
          <p>Retrieving your enrolled class schedule and academic timings...</p>
        </div>
      )}

      {!loading && error && (
        <div className="timetable-error-card" role="alert">
          <FontAwesomeIcon icon={faTriangleExclamation} className="tt-error-icon" />
          <div className="tt-error-content">
            <h3>Unable to load timetable</h3>
            <p>{error}</p>
          </div>
          <button type="button" className="tt-retry-btn" onClick={handleRetry}>
            <FontAwesomeIcon icon={faRotateRight} /> Retry
          </button>
        </div>
      )}

      {!loading && !error && !hasAnyClasses && (
        <div className="timetable-empty-card">
          <PageState
            title="No Timetable Available"
            message="No class timetable entries were found for your active course enrollments. If you recently enrolled, please contact your academic administrator or department coordinator."
          />
        </div>
      )}

      {/* ========================================================
          MAIN TWO-COLUMN CONTENT AREA
          ======================================================== */}
      {!loading && !error && hasAnyClasses && (
        <div className="timetable-layout-grid">
          {/* LEFT COLUMN: TIMETABLE VIEW */}
          <main className="timetable-main-column">
            {/* 1. WEEK VIEW */}
            {viewMode === "week" && (
              <div className="tt-grid-container">
                <table className="tt-weekly-table">
                  <thead>
                    <tr>
                      <th className="tt-time-head">Time</th>
                      {weekDayDates.map((col) => (
                        <th
                          key={col.dayName}
                          className={`tt-day-head ${col.isToday ? "tt-day-head-today" : ""}`}
                        >
                          <span className="tt-head-day">{col.dayName}</span>
                          <span className="tt-head-date">{col.dateFormatted}</span>
                          {col.isToday && <span className="tt-today-pill">Today</span>}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {timeSlots.map((slot) => {
                      if (slot.isLunchBreak) {
                        return (
                          <tr key={`break-${slot.start}`} className="tt-break-row">
                            <td className="tt-time-cell">
                              <span className="tt-time-text">
                                <FontAwesomeIcon icon={faClock} /> {slot.label}
                              </span>
                            </td>
                            <td colSpan={5} className="tt-break-cell">
                              <div className="tt-break-badge">
                                <FontAwesomeIcon icon={faUtensils} />
                                <span>Lunch Break</span>
                              </div>
                            </td>
                          </tr>
                        );
                      }

                      return (
                        <tr key={`slot-${slot.start}`} className="tt-slot-row">
                          <td className="tt-time-cell">
                            <span className="tt-time-text">
                              <FontAwesomeIcon icon={faClock} /> {slot.label}
                            </span>
                          </td>

                          {weekDayDates.map((col) => {
                            const entriesInSlot = (groupedByDay[col.dayName] || []).filter(
                              (e) => (e.start_time || "").slice(0, 5) === slot.start
                            );

                            return (
                              <td
                                key={`${slot.start}-${col.dayName}`}
                                className={`tt-entry-cell ${col.isToday ? "tt-col-today" : ""}`}
                              >
                                {entriesInSlot.length === 0 ? (
                                  <div className="tt-empty-slot" aria-hidden="true" />
                                ) : (
                                  entriesInSlot.map((entry) => renderClassCard(entry))
                                )}
                              </td>
                            );
                          })}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {/* 2. DAY VIEW */}
            {viewMode === "day" && (
              <div className="tt-day-view-container">
                {/* Day Selector Pills */}
                <div className="tt-day-selector" role="tablist" aria-label="Select day">
                  {weekDayDates.map((col) => {
                    const count = (groupedByDay[col.dayName] || []).length;
                    const isSelected = selectedDay === col.dayName;
                    return (
                      <button
                        key={col.dayName}
                        type="button"
                        role="tab"
                        aria-selected={isSelected}
                        className={`tt-day-tab ${isSelected ? "active" : ""} ${
                          col.isToday ? "is-today" : ""
                        }`}
                        onClick={() => setSelectedDay(col.dayName)}
                      >
                        <div className="day-tab-inner">
                          <span className="day-tab-title">{col.dayName}</span>
                          <span className="day-tab-date">{col.dateFormatted}</span>
                        </div>
                        {count > 0 && <span className="day-tab-count">{count}</span>}
                      </button>
                    );
                  })}
                </div>

                {/* Selected Day Classes */}
                <div className="tt-day-classes-list">
                  <div className="tt-day-header-summary">
                    <h2>
                      {selectedDay} Schedule
                      <span className="day-summary-date">
                        ({weekDayDates.find((w) => w.dayName === selectedDay)?.dateFormatted})
                      </span>
                    </h2>
                    <span className="day-classes-badge">
                      {(groupedByDay[selectedDay] || []).length} Classes
                    </span>
                  </div>

                  {(groupedByDay[selectedDay] || []).length === 0 ? (
                    <div className="tt-day-empty-state">
                      <PageState
                        title="No classes scheduled"
                        message={`You have no class sessions scheduled on ${selectedDay}.`}
                      />
                    </div>
                  ) : (
                    <div className="tt-day-cards-stack">
                      {(groupedByDay[selectedDay] || []).map((entry) => {
                        const palette = getCoursePalette(entry.course_code);
                        return (
                          <article
                            key={entry.timetable_entry_id}
                            className="tt-day-detail-card"
                            style={{
                              borderLeftColor: palette.dotColor,
                            }}
                            onClick={() => setSelectedClassModal(entry)}
                            role="button"
                            tabIndex={0}
                            onKeyDown={(e) => {
                              if (e.key === "Enter" || e.key === " ") {
                                setSelectedClassModal(entry);
                              }
                            }}
                          >
                            <div className="day-card-time-col">
                              <span className="day-card-time-slot">
                                <FontAwesomeIcon icon={faClock} />
                                {formatTime12(entry.start_time)} – {formatTime12(entry.end_time)}
                              </span>
                              <span
                                className="day-card-code"
                                style={{
                                  color: palette.codeColor,
                                  backgroundColor: palette.badgeBg,
                                }}
                              >
                                {entry.course_code}
                              </span>
                            </div>

                            <div className="day-card-info-col">
                              <h3 className="day-card-title">{entry.course_name}</h3>
                              <div className="day-card-meta-row">
                                <span className="day-card-meta-pill">
                                  <FontAwesomeIcon icon={faLocationDot} /> Room: {entry.room || "TBA"}
                                </span>
                                {(entry.effective_faculty_name || entry.faculty_name) && (
                                  <span className="day-card-meta-pill">
                                    <FontAwesomeIcon icon={faUserTie} /> Faculty:{" "}
                                    {entry.effective_faculty_name || entry.faculty_name}
                                  </span>
                                )}
                                {entry.section && (
                                  <span className="day-card-meta-pill">Sec {entry.section}</span>
                                )}
                              </div>

                              {entry.active_adjustment && (
                                <div className="day-card-adjustment-banner">
                                  <span>
                                    Substitute Assigned: {entry.effective_faculty_name}
                                  </span>
                                </div>
                              )}
                            </div>
                          </article>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            )}
          </main>

          {/* RIGHT COLUMN: INFORMATION PANELS */}
          <aside className="timetable-sidebar-column">
            {/* 1. TODAY'S CLASSES */}
            <section className="tt-panel tt-panel-today" aria-labelledby="todays-classes-title">
              <div className="tt-panel-header">
                <div className="panel-title-group">
                  <div className="panel-title-icon today-icon">
                    <FontAwesomeIcon icon={faCalendarDays} />
                  </div>
                  <h3 id="todays-classes-title" className="panel-title">
                    Today&apos;s Classes
                  </h3>
                </div>
              </div>

              <span className="today-panel-date">
                {new Date().toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                })}{" "}
                ({todayWeekday})
              </span>

              {todaysClassesList.length === 0 ? (
                <div className="today-empty-state">
                  <p>No classes scheduled for today.</p>
                </div>
              ) : (
                <div className="today-classes-list">
                  {todaysClassesList.map((entry) => {
                    const palette = getCoursePalette(entry.course_code);
                    return (
                      <div
                        key={entry.timetable_entry_id}
                        className="today-class-item"
                        onClick={() => setSelectedClassModal(entry)}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            setSelectedClassModal(entry);
                          }
                        }}
                      >
                        <span
                          className="today-class-dot"
                          style={{ backgroundColor: palette.dotColor }}
                        />
                        <div className="today-class-content">
                          <span className="today-class-time">
                            {formatTime12(entry.start_time)} – {formatTime12(entry.end_time)}
                          </span>
                          <strong className="today-class-name">
                            {entry.course_name}{" "}
                            <span className="today-class-code">({entry.course_code})</span>
                          </strong>
                          <span className="today-class-room">
                            Room: {entry.room || "TBA"}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </section>

            {/* 2. QUICK INFO */}
            <section className="tt-panel tt-panel-quickinfo" aria-labelledby="quick-info-title">
              <div className="tt-panel-header">
                <div className="panel-title-group">
                  <div className="panel-title-icon quickinfo-icon">
                    <FontAwesomeIcon icon={faCircleInfo} />
                  </div>
                  <h3 id="quick-info-title" className="panel-title">
                    Quick Info
                  </h3>
                </div>
              </div>

              <div className="quick-info-items">
                <div className="quick-info-row">
                  <div className="quick-info-label">
                    <FontAwesomeIcon icon={faCalendarDays} className="quick-info-icon" />
                    <span>Total Classes (This Week)</span>
                  </div>
                  <strong className="quick-info-value">{quickInfoStats.totalClassesThisWeek}</strong>
                </div>

                <div className="quick-info-row">
                  <div className="quick-info-label">
                    <FontAwesomeIcon icon={faCheckCircle} className="quick-info-icon" />
                    <span>Completed</span>
                  </div>
                  <strong className="quick-info-value">{quickInfoStats.completedSessions}</strong>
                </div>

                <div className="quick-info-row">
                  <div className="quick-info-label">
                    <FontAwesomeIcon icon={faClock} className="quick-info-icon" />
                    <span>Upcoming</span>
                  </div>
                  <strong className="quick-info-value">{quickInfoStats.upcomingCount}</strong>
                </div>

                <div className="quick-info-row">
                  <div className="quick-info-label">
                    <FontAwesomeIcon icon={faChartPie} className="quick-info-icon" />
                    <span>Attendance Rate</span>
                  </div>
                  <strong className="quick-info-value highlight-value">
                    {quickInfoStats.attendanceRateDisplay}
                  </strong>
                </div>
              </div>
            </section>

            {/* 3. LEGEND */}
            <section className="tt-panel tt-panel-legend" aria-labelledby="course-legend-title">
              <div className="tt-panel-header">
                <div className="panel-title-group">
                  <div className="panel-title-icon legend-icon">
                    <FontAwesomeIcon icon={faLayerGroup} />
                  </div>
                  <h3 id="course-legend-title" className="panel-title">
                    Legend
                  </h3>
                </div>
              </div>

              <div className="legend-items-list">
                {courseLegend.map((item) => (
                  <div key={item.course_code} className="legend-item">
                    <span
                      className="legend-dot"
                      style={{ backgroundColor: item.palette.dotColor }}
                    />
                    <span className="legend-text">
                      <strong>{item.course_code}</strong>
                      <span className="legend-sep">-</span>
                      <span className="legend-name">{item.course_name}</span>
                    </span>
                  </div>
                ))}
              </div>
            </section>
          </aside>
        </div>
      )}

      {/* ========================================================
          CLASS DETAILS MODAL
          ======================================================== */}
      {selectedClassModal && (
        <div
          className="tt-modal-backdrop"
          onClick={() => setSelectedClassModal(null)}
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-course-name"
        >
          <div
            className="tt-modal-card"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="tt-modal-header">
              <div className="modal-header-left">
                <span
                  className="modal-course-badge"
                  style={{
                    backgroundColor: getCoursePalette(selectedClassModal.course_code).badgeBg,
                    color: getCoursePalette(selectedClassModal.course_code).codeColor,
                  }}
                >
                  {selectedClassModal.course_code}
                </span>
                <h3 id="modal-course-name" className="modal-title">
                  {selectedClassModal.course_name}
                </h3>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setSelectedClassModal(null)}
                aria-label="Close details"
              >
                <FontAwesomeIcon icon={faXmark} />
              </button>
            </div>

            <div className="tt-modal-body">
              <div className="modal-info-grid">
                <div className="modal-info-item">
                  <div className="modal-item-icon">
                    <FontAwesomeIcon icon={faClock} />
                  </div>
                  <div className="modal-item-content">
                    <span className="modal-item-label">Day & Timing</span>
                    <strong className="modal-item-value">
                      {selectedClassModal.day_of_week},{" "}
                      {formatTime12(selectedClassModal.start_time)} –{" "}
                      {formatTime12(selectedClassModal.end_time)}
                    </strong>
                  </div>
                </div>

                <div className="modal-info-item">
                  <div className="modal-item-icon">
                    <FontAwesomeIcon icon={faLocationDot} />
                  </div>
                  <div className="modal-item-content">
                    <span className="modal-item-label">Classroom / Room</span>
                    <strong className="modal-item-value">
                      {selectedClassModal.room || "Room Not Assigned"}
                    </strong>
                  </div>
                </div>

                <div className="modal-info-item">
                  <div className="modal-item-icon">
                    <FontAwesomeIcon icon={faUserTie} />
                  </div>
                  <div className="modal-item-content">
                    <span className="modal-item-label">Faculty In-Charge</span>
                    <strong className="modal-item-value">
                      {selectedClassModal.effective_faculty_name ||
                        selectedClassModal.faculty_name ||
                        "Faculty Not Assigned"}
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
                      Semester {selectedClassModal.semester || profile?.semester || "1"}
                      {selectedClassModal.section ? ` • Sec ${selectedClassModal.section}` : ""}{" "}
                      ({selectedClassModal.academic_year || profile?.academic_year || "2026-2027"})
                    </strong>
                  </div>
                </div>
              </div>

              {selectedClassModal.active_adjustment && (
                <div className="modal-adjustment-box">
                  <FontAwesomeIcon icon={faCircleInfo} className="adjustment-icon" />
                  <div>
                    <strong>Substitute Faculty Assigned</strong>
                    <p>
                      {selectedClassModal.active_adjustment.substitute_faculty_name} is
                      conducting this class on behalf of{" "}
                      {selectedClassModal.active_adjustment.original_faculty_name}.
                    </p>
                  </div>
                </div>
              )}
            </div>

            <div className="tt-modal-footer">
              <button
                type="button"
                className="modal-action-btn"
                onClick={() => setSelectedClassModal(null)}
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

export default Schedule;
