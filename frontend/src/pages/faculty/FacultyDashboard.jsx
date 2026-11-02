import { useEffect, useState, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  BookOpen,
  CalendarDays,
  Camera,
  Users,
  ChevronDown,
  Building,
  User as UserIcon,
  Clock,
  Zap,
  Headphones,
  CheckCircle2,
  Calendar,
  SquareCheck,
  BarChart3,
  ChevronRight,
  ArrowRight,
  AlertCircle,
  X,
  RotateCw,
} from "lucide-react";

import "./FacultyDashboard.css";
import useAuth from "../../hooks/useAuth";
import { formatAcademicYear } from "../../utils/academicYearUtils";
import { getFacultyDashboard } from "../../services/portalService";
import { getFacultyAttendanceAnalytics } from "../../services/reportService";
import {
  getFacultyCourses,
  getFacultyAttendanceSessions,
  getActiveFacultyAttendanceSession,
  startFacultyAttendanceSession,
  getFacultyTimetable,
} from "../../services/facultyService";
import { invalidateApiCache } from "../../services/api";

// Card background illustrations
import assignedCoursesImg from "../../../image/Assigned Courses.png";
import todaysClassesImg from "../../../image/Today's Classes.png";
import activeSessionsImg from "../../../image/Active Sessions.png";
import avgAttendanceImg from "../../../image/Average Attendance.png";
import goodMorningBannerImg from "../../../image/opposite goodmorning card for faculty.png";

function getDisplayName(user) {
  if (!user || typeof user !== "object") return "Faculty Member";

  const fullName =
    user.full_name ||
    user.fullName ||
    user.name ||
    [user.first_name, user.last_name].filter(Boolean).join(" ") ||
    [user.firstName, user.lastName].filter(Boolean).join(" ");

  return typeof fullName === "string" && fullName.trim()
    ? fullName.trim()
    : "Faculty Member";
}

function getInitials(name) {
  if (!name || name === "Faculty Member") return "RK";
  // Remove common prefixes / titles: Dr., Dr, Prof., Prof, Mr., Mrs., Ms.
  const cleanName = name
    .replace(/^(dr\.|dr|prof\.|prof|mr\.|mr|mrs\.|mrs|ms\.|ms)\s+/i, "")
    .trim();
  const parts = cleanName.split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "RK";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function formatTime(value) {
  if (!value) return "TBD";
  const match = String(value).match(/^(\d{2}):(\d{2})/);
  if (!match) return String(value);

  const date = new Date();
  date.setHours(Number(match[1]), Number(match[2]), 0, 0);

  return new Intl.DateTimeFormat("en-IN", {
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

const ALL_WEEKDAYS = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

function getClassScheduleStatus(startTime, endTime, dayOfWeek = null) {
  if (!startTime || !endTime) return { status: "SCHEDULED", label: "Scheduled", isToday: false };
  const todayWeekday = getTodayWeekday();
  const isToday = !dayOfWeek || String(dayOfWeek).trim().toLowerCase() === todayWeekday.toLowerCase();

  const formattedStart = formatTime(startTime);
  const formattedEnd = formatTime(endTime);

  if (!isToday) {
    const formattedDay = dayOfWeek ? String(dayOfWeek).trim() : "Scheduled Day";
    return {
      status: "SCHEDULED",
      label: `Scheduled for ${formattedDay}`,
      formattedStart,
      formattedEnd,
      isToday: false,
    };
  }

  const now = new Date();
  const sMatch = String(startTime).match(/^(\d{2}):(\d{2})/);
  const eMatch = String(endTime).match(/^(\d{2}):(\d{2})/);
  if (!sMatch || !eMatch) return { status: "SCHEDULED", label: "Scheduled", isToday: true };

  const start = new Date(now);
  start.setHours(Number(sMatch[1]), Number(sMatch[2]), 0, 0);

  const end = new Date(now);
  end.setHours(Number(eMatch[1]), Number(eMatch[2]), 0, 0);
  if (end <= start) {
    end.setDate(end.getDate() + 1);
  }

  if (now < start) {
    return {
      status: "UPCOMING",
      label: `Upcoming • Starts at ${formattedStart}`,
      formattedStart,
      formattedEnd,
      isToday: true,
    };
  } else if (now >= end) {
    return {
      status: "ENDED",
      label: "Ended",
      formattedStart,
      formattedEnd,
      isToday: true,
    };
  } else {
    return {
      status: "ACTIVE",
      label: "Active",
      formattedStart,
      formattedEnd,
      isToday: true,
    };
  }
}

function formatElapsedTimer(totalSeconds) {
  const hrs = Math.floor(totalSeconds / 3600);
  const mins = Math.floor((totalSeconds % 3600) / 60);
  const secs = totalSeconds % 60;
  return [hrs, mins, secs]
    .map((v) => String(v).padStart(2, "0"))
    .join(":");
}

function getTodayWeekday() {
  return new Intl.DateTimeFormat("en-US", { weekday: "long" }).format(new Date());
}

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

function FacultyDashboard() {
  const navigate = useNavigate();
  const auth = useAuth();
  const user = auth?.user;
  const displayName = getDisplayName(user);
  const initials = getInitials(displayName);
  const greeting = getGreeting();

  // Status trackers
  const [backendStatus, setBackendStatus] = useState("loading"); // loading, connected, error
  const [coursesStatus, setCoursesStatus] = useState("loading"); // loading, loaded, error
  const [sessionStatus, setSessionStatus] = useState("loading"); // loading, loaded, error
  const [timetableStatus, setTimetableStatus] = useState("loading"); // loading, loaded, error
  const [analyticsStatus, setAnalyticsStatus] = useState("loading"); // loading, loaded, error

  // Real backend data states (NO fake data)
  const [courses, setCourses] = useState([]);
  const [activeSession, setActiveSession] = useState(null);
  const [timetable, setTimetable] = useState([]);
  const [recentSessions, setRecentSessions] = useState([]);
  const [analytics, setAnalytics] = useState(null);

  // Day filter for schedule view ("TODAY", "ALL", or individual weekday)
  const [selectedScheduleDay, setSelectedScheduleDay] = useState("TODAY");
  const [isReloadingTimetable, setIsReloadingTimetable] = useState(false);

  // Live timer for active session
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  // Start Session Modal
  const [showStartDialog, setShowStartDialog] = useState(false);
  const [selectedOfferingId, setSelectedOfferingId] = useState("");
  const [selectedTimetableEntryId, setSelectedTimetableEntryId] = useState("");
  const [startingSession, setStartingSession] = useState(false);
  const [startError, setStartError] = useState("");

  // Lock body scroll and close on Escape key when Start Attendance modal is open
  useEffect(() => {
    if (!showStartDialog) return;
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    function handleKeyDown(e) {
      if (e.key === "Escape" && !startingSession) {
        setShowStartDialog(false);
      }
    }
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = originalOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [showStartDialog, startingSession]);


  // Live ticker for active session elapsed time
  useEffect(() => {
    let timer;
    if (activeSession) {
      timer = setInterval(() => {
        setElapsedSeconds((prev) => prev + 1);
      }, 1000);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [activeSession]);

  // Reload handlers with cache invalidation and retry support
  const reloadCourses = useCallback(async () => {
    setCoursesStatus("loading");
    try {
      invalidateApiCache("courses");
      const result = await getFacultyCourses();
      if (result?.success && Array.isArray(result.data)) {
        setCourses(result.data);
        setCoursesStatus("loaded");
        if (result.data.length > 0) {
          const preferred =
            result.data.find((c) => Number(c.student_count || c.enrolled_students || 0) > 0) ||
            result.data[0];
          setSelectedOfferingId((prev) => (prev ? prev : String(preferred.offering_id)));
        }
      } else {
        setCourses([]);
        setCoursesStatus("error");
      }
    } catch {
      setCourses([]);
      setCoursesStatus("error");
    }
  }, []);

  const reloadTimetable = useCallback(async () => {
    setIsReloadingTimetable(true);
    setTimetableStatus((prev) => (prev === "loaded" ? prev : "loading"));
    try {
      invalidateApiCache("timetable");
      const result = await getFacultyTimetable();
      if (result?.success) {
        const items = Array.isArray(result.data)
          ? result.data
          : Array.isArray(result.data?.timetable)
          ? result.data.timetable
          : [];
        setTimetable(items);
        setTimetableStatus("loaded");
      } else {
        setTimetable([]);
        setTimetableStatus("error");
      }
    } catch {
      setTimetableStatus((prev) => (prev === "loaded" ? prev : "error"));
    } finally {
      setIsReloadingTimetable(false);
    }
  }, []);

  const reloadSessions = useCallback(async () => {
    setSessionStatus("loading");
    try {
      invalidateApiCache("session");
      const [activeRes, sessionsRes] = await Promise.allSettled([
        getActiveFacultyAttendanceSession(),
        getFacultyAttendanceSessions(),
      ]);

      if (activeRes.status === "fulfilled" && activeRes.value?.success && activeRes.value?.data) {
        const s = activeRes.value.data;
        if (s?.session_id && String(s?.status).toUpperCase() === "ACTIVE" && s?.is_eligible_for_attendance !== false) {
          setActiveSession(s);
          setElapsedSeconds(0);
        } else {
          setActiveSession(null);
        }
        setSessionStatus("loaded");
      } else {
        setActiveSession(null);
        setSessionStatus(activeRes.status === "fulfilled" ? "loaded" : "error");
      }

      if (sessionsRes.status === "fulfilled" && sessionsRes.value?.success && Array.isArray(sessionsRes.value.data)) {
        setRecentSessions(sessionsRes.value.data);
      } else {
        setRecentSessions([]);
      }
    } catch {
      setActiveSession(null);
      setRecentSessions([]);
      setSessionStatus("error");
    }
  }, []);

  const reloadAnalytics = useCallback(async () => {
    setAnalyticsStatus("loading");
    try {
      invalidateApiCache("analytics");
      const result = await getFacultyAttendanceAnalytics();
      if (result?.success && result?.data) {
        setAnalytics(result.data);
        setAnalyticsStatus("loaded");
      } else {
        setAnalytics(null);
        setAnalyticsStatus("error");
      }
    } catch {
      setAnalytics(null);
      setAnalyticsStatus("error");
    }
  }, []);

  // Fetch all dashboard data from backend APIs on mount
  useEffect(() => {
    let cancelled = false;

    async function fetchDashboardData() {
      // 1. Backend Verification
      try {
        const result = await getFacultyDashboard();
        if (cancelled) return;
        setBackendStatus(result?.success ? "connected" : "error");
      } catch {
        if (!cancelled) setBackendStatus("error");
      }

      // 2. Fetch all modules in parallel
      if (!cancelled) {
        reloadCourses();
        reloadTimetable();
        reloadSessions();
        reloadAnalytics();
      }
    }

    fetchDashboardData();

    return () => {
      cancelled = true;
    };
  }, [reloadCourses, reloadTimetable, reloadSessions, reloadAnalytics]);

  // Periodic active session status revalidation (every 25 seconds)
  useEffect(() => {
    let cancelled = false;
    const interval = setInterval(async () => {
      try {
        const res = await getActiveFacultyAttendanceSession();
        if (cancelled) return;
        if (res?.success && res.data) {
          const s = res.data;
          if (s?.session_id && String(s?.status).toUpperCase() === "ACTIVE" && s?.is_eligible_for_attendance !== false) {
            setActiveSession(s);
          } else {
            setActiveSession(null);
          }
        } else {
          setActiveSession(null);
        }
      } catch {
        // preserve current state on transient network error
      }
    }, 25000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  // Listen to cross-tab updates, custom timetable update events, and window focus
  useEffect(() => {
    function handleTimetableUpdate() {
      reloadTimetable();
    }
    function handleStorage(e) {
      if (e.key === "sams_timetable_last_updated") {
        reloadTimetable();
      }
    }
    function handleFocus() {
      reloadTimetable();
    }

    window.addEventListener("sams:timetable-updated", handleTimetableUpdate);
    window.addEventListener("storage", handleStorage);
    window.addEventListener("focus", handleFocus);

    return () => {
      window.removeEventListener("sams:timetable-updated", handleTimetableUpdate);
      window.removeEventListener("storage", handleStorage);
      window.removeEventListener("focus", handleFocus);
    };
  }, [reloadTimetable]);

  // Revalidate session eligibility before entering live attendance page
  const handleViewLiveAttendance = async () => {
    try {
      const activeRes = await getActiveFacultyAttendanceSession();
      if (activeRes?.success && activeRes?.data && activeRes?.data?.is_eligible_for_attendance !== false) {
        navigate("/faculty/attendance");
      } else {
        setActiveSession(null);
        alert(
          activeRes?.data?.message ||
          "Session is not currently active or eligible for attendance. Please check the scheduled class hours."
        );
      }
    } catch {
      navigate("/faculty/attendance");
    }
  };

  // Filter timetable for today
  const todayWeekday = getTodayWeekday();
  const todaysClasses = timetable.filter(
    (entry) =>
      String(entry.day_of_week || "").trim().toLowerCase() ===
      todayWeekday.toLowerCase()
  );

  // Filter timetable based on selected schedule view (TODAY, ALL, or specific weekday)
  const displayedClasses = timetable.filter((entry) => {
    if (selectedScheduleDay === "ALL") return true;
    const targetDay = selectedScheduleDay === "TODAY" ? todayWeekday : selectedScheduleDay;
    return (
      String(entry.day_of_week || "").trim().toLowerCase() ===
      targetDay.toLowerCase()
    );
  });

  // Group other days with scheduled classes for the quick-switch pills in empty state
  const otherDaysWithClasses = useMemo(() => {
    const dayCounts = {};
    timetable.forEach((entry) => {
      const rawDay = (entry.day_of_week || "").trim();
      if (rawDay) {
        const canonicalDay =
          ALL_WEEKDAYS.find((wd) => wd.toLowerCase() === rawDay.toLowerCase()) || rawDay;
        dayCounts[canonicalDay] = (dayCounts[canonicalDay] || 0) + 1;
      }
    });
    return Object.entries(dayCounts).map(([dayName, count]) => ({
      day: dayName,
      count,
    }));
  }, [timetable]);

  // Find currently active scheduled class in progress today
  const activeScheduledClass = todaysClasses.find((entry) => {
    const s = getClassScheduleStatus(entry.start_time, entry.end_time, entry.day_of_week);
    return s.status === "ACTIVE";
  });

  // Find next upcoming class if no session is actively running
  const upcomingClass = todaysClasses.find((entry) => {
    const s = getClassScheduleStatus(entry.start_time, entry.end_time, entry.day_of_week);
    return s.status === "UPCOMING";
  });

  // Open Start Attendance modal with intelligent slot pre-selection
  const openStartDialog = (slot = null) => {
    setStartError("");
    if (slot) {
      setSelectedOfferingId(String(slot.offering_id));
      setSelectedTimetableEntryId(String(slot.timetable_entry_id));
    } else {
      let targetOfferingId = selectedOfferingId;
      if (activeScheduledClass) {
        targetOfferingId = String(activeScheduledClass.offering_id);
      } else if (upcomingClass) {
        targetOfferingId = String(upcomingClass.offering_id);
      } else if (!targetOfferingId && courses.length > 0) {
        targetOfferingId = String(courses[0].offering_id);
      }
      setSelectedOfferingId(targetOfferingId);

      const offeringTodaySlots = timetable.filter(
        (e) =>
          String(e.offering_id) === String(targetOfferingId) &&
          String(e.day_of_week || "").trim().toLowerCase() === todayWeekday.toLowerCase()
      );
      const allOfferingSlots = timetable.filter(
        (e) => String(e.offering_id) === String(targetOfferingId)
      );
      const candidateSlots = offeringTodaySlots.length > 0 ? offeringTodaySlots : allOfferingSlots;
      const activeSlot = candidateSlots.find(
        (s) => getClassScheduleStatus(s.start_time, s.end_time, s.day_of_week).status === "ACTIVE"
      );
      const upcomingSlot = candidateSlots.find(
        (s) => getClassScheduleStatus(s.start_time, s.end_time, s.day_of_week).status === "UPCOMING"
      );
      const bestSlot = activeSlot || upcomingSlot || candidateSlots[0];
      setSelectedTimetableEntryId(bestSlot ? String(bestSlot.timetable_entry_id) : "");
    }
    setShowStartDialog(true);
  };

  // Offering selection change in Start Attendance modal
  const handleOfferingChange = (newOfferingId) => {
    setSelectedOfferingId(newOfferingId);
    setStartError("");

    const offeringTodaySlots = timetable.filter(
      (e) =>
        String(e.offering_id) === String(newOfferingId) &&
        String(e.day_of_week || "").trim().toLowerCase() === todayWeekday.toLowerCase()
    );
    const allOfferingSlots = timetable.filter(
      (e) => String(e.offering_id) === String(newOfferingId)
    );
    const candidateSlots = offeringTodaySlots.length > 0 ? offeringTodaySlots : allOfferingSlots;

    const activeSlot = candidateSlots.find(
      (s) => getClassScheduleStatus(s.start_time, s.end_time, s.day_of_week).status === "ACTIVE"
    );
    const upcomingSlot = candidateSlots.find(
      (s) => getClassScheduleStatus(s.start_time, s.end_time, s.day_of_week).status === "UPCOMING"
    );
    const bestSlot = activeSlot || upcomingSlot || candidateSlots[0];
    setSelectedTimetableEntryId(bestSlot ? String(bestSlot.timetable_entry_id) : "");
  };

  // Handle Starting Attendance
  const handleStartAttendance = async (e) => {
    e.preventDefault();
    setStartError("");

    if (!selectedOfferingId) {
      setStartError("Please select a course offering.");
      return;
    }

    setStartingSession(true);
    try {
      let entryIdToSubmit = selectedTimetableEntryId;
      if (!entryIdToSubmit && selectedOfferingId) {
        const offeringTodaySlots = timetable.filter(
          (e) =>
            String(e.offering_id) === String(selectedOfferingId) &&
            String(e.day_of_week || "").trim().toLowerCase() === todayWeekday.toLowerCase()
        );
        const allOfferingSlots = timetable.filter(
          (t) => String(t.offering_id) === String(selectedOfferingId)
        );
        const candidateSlots = offeringTodaySlots.length > 0 ? offeringTodaySlots : allOfferingSlots;
        const activeSlot = candidateSlots.find(
          (s) => getClassScheduleStatus(s.start_time, s.end_time).status === "ACTIVE"
        );
        const upcomingSlot = candidateSlots.find(
          (s) => getClassScheduleStatus(s.start_time, s.end_time).status === "UPCOMING"
        );
        const bestSlot = activeSlot || upcomingSlot || candidateSlots[0];
        if (bestSlot) {
          entryIdToSubmit = String(bestSlot.timetable_entry_id);
        }
      }

      const payload = {
        offering_id: Number(selectedOfferingId),
      };
      if (entryIdToSubmit) {
        payload.timetable_entry_id = Number(entryIdToSubmit);
      }
      const result = await startFacultyAttendanceSession(payload);
      if (result?.success && result?.data) {
        setActiveSession(result.data);
        setShowStartDialog(false);
      } else {
        throw new Error(result?.message || "Failed to start attendance session.");
      }
    } catch (err) {
      setStartError(err?.response?.data?.message || err?.message || "Unable to start session.");
    } finally {
      setStartingSession(false);
    }
  };


  // Distinct offerings grouped by course + semester + section, prioritizing active timetable/students
  const distinctOfferings = useMemo(() => {
    if (!Array.isArray(courses)) return [];
    const map = new Map();
    for (const c of courses) {
      const key = `${c.course_id || c.course_code}_${c.semester}_${c.section}`;
      const existing = map.get(key);
      if (!existing) {
        map.set(key, c);
      } else {
        const hasTimetable = timetable.some(
          (t) => String(t.offering_id) === String(c.offering_id)
        );
        const existingHasTimetable = timetable.some(
          (t) => String(t.offering_id) === String(existing.offering_id)
        );
        const cStudents = Number(c.enrolled_students || c.student_count || 0);
        const existingStudents = Number(
          existing.enrolled_students || existing.student_count || 0
        );

        if (hasTimetable && !existingHasTimetable) {
          map.set(key, c);
        } else if (
          cStudents > existingStudents &&
          (!existingHasTimetable || hasTimetable)
        ) {
          map.set(key, c);
        }
      }
    }
    return Array.from(map.values());
  }, [courses, timetable]);

  // Attendance history flag
  const hasAttendanceHistory =
    analyticsStatus === "loaded" &&
    analytics?.total_sessions != null &&
    Number(analytics.total_sessions) > 0;

  // Metrics from real backend data
  const assignedCoursesDisplay =
    coursesStatus === "loaded"
      ? String(distinctOfferings.length)
      : coursesStatus === "loading"
      ? "..."
      : "—";

  const todaysClassesDisplay =
    timetableStatus === "loaded"
      ? String(todaysClasses.length)
      : timetableStatus === "loading"
      ? "..."
      : "—";

  const activeSessionsDisplay =
    sessionStatus === "loaded"
      ? activeSession && activeSession.is_eligible_for_attendance !== false
        ? "1"
        : "0"
      : sessionStatus === "loading"
      ? "..."
      : "—";

  const attendanceRateDisplay =
    analyticsStatus === "loading"
      ? "..."
      : analyticsStatus === "error"
      ? "—"
      : hasAttendanceHistory && analytics?.overall_attendance_percentage != null
      ? `${Number(analytics.overall_attendance_percentage).toFixed(1)}%`
      : "0%";

  const attendanceRateDescription =
    analyticsStatus === "loading"
      ? "Loading attendance..."
      : analyticsStatus === "error"
      ? "Failed to load analytics"
      : hasAttendanceHistory
      ? "Attendance across closed sessions"
      : "No attendance data yet";

  // Donut chart calculation from real analytics
  const donutPercentage =
    hasAttendanceHistory && analytics?.overall_attendance_percentage != null
      ? Math.max(0, Math.min(100, Number(analytics.overall_attendance_percentage)))
      : 0;
  const circumference = 2 * Math.PI * 45; // r=45
  const strokeOffset = circumference - (circumference * donutPercentage) / 100;

  return (
    <div className="faculty-dashboard-container">
      {/* 1. Welcome Banner Card */}
      <section className="faculty-welcome-card" aria-label="Welcome Banner">
        <div className="faculty-welcome-left">
          <div className="faculty-welcome-avatar" aria-hidden="true">
            {initials}
          </div>

          <div className="faculty-welcome-text">
            <h1 className="faculty-welcome-title">
              {greeting}, {displayName}
            </h1>
            <p className="faculty-welcome-subtitle">
              Manage your classes, monitor attendance, and access your teaching tools from one place.
            </p>
          </div>
        </div>

        <div className="faculty-welcome-right">
          <div className="faculty-welcome-quote-block">
            <p className="faculty-welcome-quote">
              “Education is not the filling of a pail,
              <br />
              but the lighting of a fire.”
            </p>
            <span className="faculty-welcome-author">— W.B. Yeats</span>
          </div>

          <div className="faculty-welcome-image-wrap">
            <img
              src={goodMorningBannerImg || "/image/opposite goodmorning card for faculty.png"}
              alt="Faculty workspace banner desk"
              className="faculty-welcome-banner-img"
            />
          </div>
        </div>
      </section>

      {/* 2. Top Summary Stat Cards (4 Cards) */}
      <section className="faculty-stat-cards-grid" aria-label="Quick metrics">
        {/* Card 1: Assigned Courses */}
        <div
          className="faculty-stat-card faculty-stat-blue"
          style={{
            backgroundImage: `url("${assignedCoursesImg || "/image/Assigned Courses.png"}")`,
          }}
        >
          <div className="faculty-stat-header">
            <div className="faculty-stat-header-main">
              <div className="faculty-stat-icon-wrap faculty-icon-blue">
                <BookOpen size={20} strokeWidth={2.4} />
              </div>
              <div className="faculty-stat-title-wrap">
                <span className="faculty-stat-title">Assigned Courses</span>
                {coursesStatus === "error" && (
                  <button
                    type="button"
                    className="faculty-stat-retry-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      reloadCourses();
                    }}
                    title="Retry loading courses"
                  >
                    <RotateCw size={11} /> Retry
                  </button>
                )}
              </div>
            </div>
            <ChevronRight size={16} className="faculty-stat-chevron faculty-chevron-blue" />
          </div>

          <div className="faculty-stat-body">
            <span className="faculty-stat-value">{assignedCoursesDisplay}</span>
            <span className="faculty-stat-description">
              {coursesStatus === "error" ? "Failed to load offerings" : "Assigned course offerings"}
            </span>
          </div>
        </div>

        {/* Card 2: Today's Classes */}
        <div
          className="faculty-stat-card faculty-stat-green"
          style={{
            backgroundImage: `url("${todaysClassesImg || "/image/Today's Classes.png"}")`,
          }}
        >
          <div className="faculty-stat-header">
            <div className="faculty-stat-header-main">
              <div className="faculty-stat-icon-wrap faculty-icon-green">
                <CalendarDays size={20} strokeWidth={2.4} />
              </div>
              <div className="faculty-stat-title-wrap">
                <span className="faculty-stat-title">Today's Classes</span>
                {timetableStatus === "error" && (
                  <button
                    type="button"
                    className="faculty-stat-retry-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      reloadTimetable();
                    }}
                    title="Retry loading schedule"
                  >
                    <RotateCw size={11} /> Retry
                  </button>
                )}
              </div>
            </div>
            <ChevronRight size={16} className="faculty-stat-chevron faculty-chevron-green" />
          </div>

          <div className="faculty-stat-body">
            <span className="faculty-stat-value">{todaysClassesDisplay}</span>
            <span className="faculty-stat-description">
              {timetableStatus === "error" ? "Failed to load schedule" : "Today's teaching schedule"}
            </span>
          </div>
        </div>

        {/* Card 3: Active Sessions */}
        <div
          className="faculty-stat-card faculty-stat-purple"
          style={{
            backgroundImage: `url("${activeSessionsImg || "/image/Active Sessions.png"}")`,
          }}
        >
          <div className="faculty-stat-header">
            <div className="faculty-stat-header-main">
              <div className="faculty-stat-icon-wrap faculty-icon-purple">
                <Camera size={20} strokeWidth={2.4} />
              </div>
              <div className="faculty-stat-title-wrap">
                <span className="faculty-stat-title">Active Sessions</span>
                {sessionStatus === "error" && (
                  <button
                    type="button"
                    className="faculty-stat-retry-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      reloadSessions();
                    }}
                    title="Retry checking session status"
                  >
                    <RotateCw size={11} /> Retry
                  </button>
                )}
              </div>
            </div>
            <ChevronRight size={16} className="faculty-stat-chevron faculty-chevron-purple" />
          </div>

          <div className="faculty-stat-body">
            <span className="faculty-stat-value">{activeSessionsDisplay}</span>
            <span className="faculty-stat-description">
              {sessionStatus === "error" ? "Failed to check status" : "Confirmed active session"}
            </span>
          </div>
        </div>

        {/* Card 4: Average Attendance */}
        <div
          className="faculty-stat-card faculty-stat-amber"
          style={{
            backgroundImage: `url("${avgAttendanceImg || "/image/Average Attendance.png"}")`,
          }}
        >
          <div className="faculty-stat-header">
            <div className="faculty-stat-header-main">
              <div className="faculty-stat-icon-wrap faculty-icon-amber">
                <Users size={20} strokeWidth={2.4} />
              </div>
              <div className="faculty-stat-title-wrap">
                <span className="faculty-stat-title">Average Attendance</span>
                {analyticsStatus === "error" && (
                  <button
                    type="button"
                    className="faculty-stat-retry-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      reloadAnalytics();
                    }}
                    title="Retry loading analytics"
                  >
                    <RotateCw size={11} /> Retry
                  </button>
                )}
              </div>
            </div>
            <ChevronRight size={16} className="faculty-stat-chevron faculty-chevron-amber" />
          </div>

          <div className="faculty-stat-body">
            <div className="faculty-stat-value-row">
              <span className="faculty-stat-value">{attendanceRateDisplay}</span>
              {hasAttendanceHistory && (
                <ArrowRight size={20} strokeWidth={2.8} className="faculty-stat-arrow-right" />
              )}
            </div>
            <span className="faculty-stat-description">
              {attendanceRateDescription}
            </span>
          </div>
        </div>
      </section>

      {/* 3. Main Dashboard 3-Column Content Layout */}
      <div className="faculty-columns-grid">
        {/* Column 1: Left */}
        <div className="faculty-col faculty-col-left">
          {/* Card: Today's Schedule */}
          <div className="faculty-panel-card">
            <div className="faculty-panel-header">
              <div className="faculty-panel-header-left">
                <div className="faculty-panel-header-icon faculty-icon-blue">
                  <Calendar size={18} />
                </div>
                <div>
                  <h2 className="faculty-panel-title">
                    {selectedScheduleDay === "TODAY"
                      ? "Today's Schedule"
                      : selectedScheduleDay === "ALL"
                      ? "Weekly Schedule"
                      : `${selectedScheduleDay}'s Schedule`}
                  </h2>
                  <p className="faculty-panel-subtitle">
                    {selectedScheduleDay === "TODAY"
                      ? `Your classes and teaching sessions for today (${todayWeekday}).`
                      : selectedScheduleDay === "ALL"
                      ? "All teaching sessions across your weekly timetable."
                      : `Your classes and teaching sessions scheduled for ${selectedScheduleDay}.`}
                  </p>
                </div>
              </div>

              <div className="faculty-schedule-header-actions">
                <div className="faculty-dropdown-pill faculty-dropdown-pill-interactive" title="Select day to view schedule">
                  <Calendar size={13} className="faculty-dropdown-cal-icon" />
                  <select
                    className="faculty-schedule-day-native-select"
                    value={selectedScheduleDay}
                    onChange={(e) => setSelectedScheduleDay(e.target.value)}
                    aria-label="Select schedule day"
                  >
                    <option value="TODAY">Today ({todayWeekday})</option>
                    <option value="ALL">All Days (Full Week)</option>
                    <option disabled>──────────</option>
                    {ALL_WEEKDAYS.map((d) => (
                      <option key={d} value={d}>
                        {d} {d.toLowerCase() === todayWeekday.toLowerCase() ? "(Today)" : ""}
                      </option>
                    ))}
                  </select>
                  <ChevronDown size={14} className="faculty-dropdown-chevron" />
                </div>

                <button
                  type="button"
                  className="faculty-schedule-refresh-icon-btn"
                  onClick={reloadTimetable}
                  title="Refresh timetable schedule"
                  aria-label="Refresh timetable schedule"
                >
                  <RotateCw size={13} className={isReloadingTimetable ? "faculty-spin" : ""} />
                </button>
              </div>
            </div>

            {timetableStatus === "loading" ? (
              <div className="faculty-empty-state">
                <p>Loading schedule from backend...</p>
              </div>
            ) : timetableStatus === "error" ? (
              <div className="faculty-empty-state">
                <AlertCircle size={22} className="text-amber" />
                <strong>Unable to load schedule</strong>
                <p>Could not retrieve your teaching timetable from the server.</p>
                <button
                  type="button"
                  className="faculty-retry-btn"
                  onClick={reloadTimetable}
                >
                  <RotateCw size={14} /> Retry
                </button>
              </div>
            ) : displayedClasses.length === 0 ? (
              <div className="faculty-empty-state">
                <Calendar size={22} className="text-muted" />
                <strong>
                  {selectedScheduleDay === "TODAY"
                    ? "No classes scheduled for today"
                    : `No classes scheduled for ${selectedScheduleDay}`}
                </strong>
                <p>
                  {selectedScheduleDay === "TODAY"
                    ? `Your timetable contains no teaching sessions for ${todayWeekday}.`
                    : `Your timetable contains no teaching sessions for ${selectedScheduleDay}.`}
                </p>
                {otherDaysWithClasses.length > 0 && (
                  <div className="faculty-other-days-box">
                    <span className="faculty-other-days-label">You have classes scheduled on:</span>
                    <div className="faculty-other-days-pills">
                      {otherDaysWithClasses.map(({ day: dayName, count }) => (
                        <button
                          key={dayName}
                          type="button"
                          className="faculty-day-quick-pill"
                          onClick={() => setSelectedScheduleDay(dayName)}
                        >
                          {dayName} ({count})
                        </button>
                      ))}
                      <button
                        type="button"
                        className="faculty-day-quick-pill faculty-day-quick-pill-all"
                        onClick={() => setSelectedScheduleDay("ALL")}
                      >
                        View Full Week
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="faculty-schedule-list">
                {displayedClasses.map((item, index) => {
                  const schedStatus = getClassScheduleStatus(item.start_time, item.end_time, item.day_of_week);
                  return (
                    <div
                      key={item.timetable_entry_id || index}
                      className="faculty-schedule-row"
                      style={{ cursor: !activeSession ? "pointer" : "default" }}
                      title={!activeSession ? "Click to configure or start attendance for this class" : undefined}
                      onClick={() => {
                        if (!activeSession) {
                          openStartDialog(item);
                        }
                      }}
                    >
                      <div className="faculty-schedule-time">
                        {formatTime(item.start_time)} – {formatTime(item.end_time)}
                      </div>

                      <div className="faculty-schedule-details">
                        <div className="faculty-schedule-course">
                          <strong>{item.course_code || "Course"}</strong>
                          <span>{item.course_name || ""}</span>
                        </div>
                        <div className="faculty-schedule-meta">
                          {selectedScheduleDay === "ALL" && (
                            <span className="faculty-schedule-day-tag">{item.day_of_week}</span>
                          )}
                          {item.section ? `Section ${item.section}` : ""}
                          {item.semester ? ` • Sem ${item.semester}` : ""}
                        </div>
                      </div>

                      <div className="faculty-schedule-right">
                        {item.room && (
                          <div className="faculty-schedule-room">
                            <Building size={14} className="faculty-room-icon" />
                            <span>{item.room}</span>
                          </div>
                        )}
                        <span className={`faculty-badge faculty-badge-${schedStatus.status.toLowerCase()}`}>
                          {schedStatus.label}
                        </span>
                      </div>
                    </div>

                  );
                })}
              </div>
            )}
          </div>

          {/* Card: Attendance Overview */}
          <div className="faculty-panel-card">
            <div className="faculty-panel-header">
              <div className="faculty-panel-header-left">
                <div className="faculty-panel-header-icon faculty-icon-blue">
                  <SquareCheck size={18} />
                </div>
                <div>
                  <h2 className="faculty-panel-title">Attendance Overview</h2>
                  <p className="faculty-panel-subtitle">Attendance statistics across closed sessions.</p>
                </div>
              </div>
              <button
                type="button"
                className="faculty-schedule-refresh-icon-btn"
                onClick={reloadAnalytics}
                title="Refresh attendance analytics"
                aria-label="Refresh attendance analytics"
              >
                <RotateCw size={13} className={analyticsStatus === "loading" ? "faculty-spin" : ""} />
              </button>
            </div>

            {analyticsStatus === "loading" ? (
              <div className="faculty-empty-state">
                <p>Loading attendance analytics from backend...</p>
              </div>
            ) : analyticsStatus === "error" ? (
              <div className="faculty-empty-state">
                <AlertCircle size={22} className="text-amber" />
                <strong>Unable to load attendance analytics</strong>
                <p>Could not retrieve attendance analytics from the server.</p>
                <button
                  type="button"
                  className="faculty-retry-btn"
                  onClick={reloadAnalytics}
                >
                  <RotateCw size={14} /> Retry
                </button>
              </div>
            ) : (
              <>
                <div className="faculty-overview-content">
                  {/* Circular SVG Donut Chart */}
                  <div className="faculty-donut-wrap">
                    <svg className="faculty-donut-svg" viewBox="0 0 110 110">
                      <circle
                        className="faculty-donut-bg"
                        cx="55"
                        cy="55"
                        r="45"
                        strokeWidth="9"
                      />
                      <circle
                        className="faculty-donut-fill"
                        cx="55"
                        cy="55"
                        r="45"
                        strokeWidth="9"
                        strokeDasharray={circumference}
                        strokeDashoffset={strokeOffset}
                        strokeLinecap="round"
                        transform="rotate(-90 55 55)"
                      />
                      <text x="55" y="52" className="faculty-donut-text-val" textAnchor="middle">
                        {hasAttendanceHistory && analytics?.overall_attendance_percentage != null
                          ? `${Number(analytics.overall_attendance_percentage).toFixed(1)}%`
                          : "0%"}
                      </text>
                      <text x="55" y="66" className="faculty-donut-text-sub" textAnchor="middle">
                        {hasAttendanceHistory ? "Overall Attendance" : "No data yet"}
                      </text>
                    </svg>
                  </div>

                  {/* Legend List */}
                  <div className="faculty-overview-legend">
                    <div className="faculty-legend-item">
                      <div className="faculty-legend-label">
                        <span className="faculty-legend-dot dot-green" />
                        <span>Present</span>
                      </div>
                      <strong className="faculty-legend-val">
                        {analytics?.total_present ?? 0}
                      </strong>
                    </div>

                    <div className="faculty-legend-item">
                      <div className="faculty-legend-label">
                        <span className="faculty-legend-dot dot-red" />
                        <span>Absent</span>
                      </div>
                      <strong className="faculty-legend-val">
                        {analytics?.total_absent ?? 0}
                      </strong>
                    </div>

                    <div className="faculty-legend-item">
                      <div className="faculty-legend-label">
                        <span className="faculty-legend-dot dot-blue" />
                        <span>Closed Sessions</span>
                      </div>
                      <strong className="faculty-legend-val">
                        {analytics?.total_sessions ?? 0}
                      </strong>
                    </div>
                  </div>
                </div>

                {!hasAttendanceHistory && (
                  <p className="faculty-overview-empty-note">
                    No attendance data yet
                  </p>
                )}
              </>
            )}
          </div>

          {/* Card: My Courses */}
          <div className="faculty-panel-card">
            <div className="faculty-panel-header">
              <div className="faculty-panel-header-left">
                <div className="faculty-panel-header-icon faculty-icon-blue">
                  <BookOpen size={18} />
                </div>
                <div>
                  <h2 className="faculty-panel-title">My Courses</h2>
                  <p className="faculty-panel-subtitle">Your assigned courses and class offerings.</p>
                </div>
              </div>
            </div>

            {coursesStatus === "loading" ? (
              <div className="faculty-empty-state">
                <p>Loading course offerings from backend...</p>
              </div>
            ) : coursesStatus === "error" ? (
              <div className="faculty-empty-state">
                <AlertCircle size={22} className="text-amber" />
                <strong>Unable to load course offerings</strong>
                <p>Could not retrieve your assigned courses from the server.</p>
                <button
                  type="button"
                  className="faculty-retry-btn"
                  onClick={reloadCourses}
                >
                  <RotateCw size={14} /> Retry
                </button>
              </div>
            ) : courses.length === 0 ? (
              <div className="faculty-empty-state">
                <BookOpen size={22} className="text-muted" />
                <strong>No assigned courses</strong>
                <p>No course offerings are currently assigned to your account.</p>
              </div>
            ) : (
              <div className="faculty-my-courses-grid">
                {distinctOfferings.slice(0, 3).map((c) => (
                  <div key={c.offering_id || c.course_id} className="faculty-course-mini-card">
                    <strong className="faculty-mini-code">{c.course_code || "Course"}</strong>
                    <span className="faculty-mini-name">{c.course_name || "Unnamed"}</span>
                    <span className="faculty-mini-sec">
                      {c.section ? `Sec ${c.section}` : ""}{c.semester ? ` • Sem ${c.semester}` : ""}
                      {c.academic_year ? ` • ${formatAcademicYear(c.academic_year, c.semester)}` : ""}
                    </span>

                    <div className="faculty-mini-footer">
                      <span className="faculty-mini-room">
                        <Building size={12} /> {c.room || "TBD"}
                      </span>
                      <span className="faculty-mini-students">
                        <Users size={12} /> {c.enrolled_students || c.student_count || 0}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <button
              type="button"
              className="faculty-panel-link-btn"
              onClick={() => navigate("/faculty/classes")}
            >
              View my classes <ArrowRight size={15} />
            </button>
          </div>
        </div>

        {/* Column 2: Center */}
        <div className="faculty-col faculty-col-center">
          {/* Card: Active Attendance Session */}
          <div className="faculty-panel-card">
            <div className="faculty-panel-header">
              <div className="faculty-panel-header-left">
                <div className="faculty-panel-header-icon faculty-icon-green">
                  <Camera size={18} />
                </div>
                <div>
                  <h2 className="faculty-panel-title">Active Attendance Session</h2>
                  <p className="faculty-panel-subtitle">Current session status confirmed by the backend.</p>
                </div>
              </div>
            </div>

            {sessionStatus === "loading" ? (
              <div className="faculty-empty-state">
                <p>Checking active session status...</p>
              </div>
            ) : sessionStatus === "error" ? (
              <div className="faculty-empty-state">
                <AlertCircle size={22} className="text-amber" />
                <strong>Unable to check session status</strong>
                <p>Could not verify current attendance session status from the server.</p>
                <button
                  type="button"
                  className="faculty-retry-btn"
                  onClick={reloadSessions}
                >
                  <RotateCw size={14} /> Retry
                </button>
              </div>
            ) : activeSession && activeSession.is_eligible_for_attendance !== false ? (
              <div className="faculty-active-session-box">
                <div className="faculty-active-cam-circle">
                  <Camera size={26} strokeWidth={2.4} />
                </div>

                <h3 className="faculty-active-course-title">
                  {activeSession.course_code ? `${activeSession.course_code} – ${activeSession.course_name || ""}` : `Session #${activeSession.session_id}`}
                </h3>
                <p className="faculty-active-course-sub">
                  Session #{activeSession.session_id} {activeSession.section ? `• Section ${activeSession.section}` : ""} {activeSession.room ? `• Room ${activeSession.room}` : ""}
                </p>

                <div className="faculty-active-status-row">
                  <div className="faculty-session-live-pill">
                    <span className="faculty-pulse-dot" />
                    <span>Session Active</span>
                  </div>

                  <div className="faculty-session-live-timer">
                    {formatElapsedTimer(elapsedSeconds)}
                  </div>
                </div>

                <button
                  type="button"
                  className="faculty-view-live-btn"
                  onClick={handleViewLiveAttendance}
                >
                  <Camera size={17} />
                  <span>View Live Attendance</span>
                </button>
              </div>
            ) : activeScheduledClass ? (
              <div className="faculty-active-session-box" style={{ borderColor: "#10b981", background: "linear-gradient(135deg, rgba(236, 253, 245, 0.7) 0%, rgba(255, 255, 255, 0.95) 100%)" }}>
                <div className="faculty-active-cam-circle" style={{ background: "rgba(16, 185, 129, 0.15)", color: "#10b981" }}>
                  <Camera size={26} strokeWidth={2.4} />
                </div>

                <h3 className="faculty-active-course-title">
                  {activeScheduledClass.course_code ? `${activeScheduledClass.course_code} – ${activeScheduledClass.course_name || ""}` : "Current Class in Session"}
                </h3>
                <p className="faculty-active-course-sub">
                  {activeScheduledClass.section ? `Section ${activeScheduledClass.section} • ` : ""}
                  {activeScheduledClass.room ? `Room ${activeScheduledClass.room} • ` : ""}
                  Scheduled {formatTime(activeScheduledClass.start_time)} – {formatTime(activeScheduledClass.end_time)}
                </p>

                <div className="faculty-active-status-row">
                  <div className="faculty-session-live-pill" style={{ background: "#ecfdf5", color: "#059669", border: "1px solid #a7f3d0" }}>
                    <span className="faculty-pulse-dot" style={{ background: "#10b981" }} />
                    <span>Class in Session • Attendance Ready</span>
                  </div>
                </div>

                <button
                  type="button"
                  className="faculty-start-session-btn"
                  style={{ width: "100%", justifyContent: "center", marginTop: "14px" }}
                  onClick={() => openStartDialog(activeScheduledClass)}
                >
                  <Camera size={16} />
                  <span>Start Attendance for this Class</span>
                </button>
              </div>
            ) : upcomingClass ? (
              <div className="faculty-upcoming-session-box">
                <div className="faculty-upcoming-cam-circle">
                  <Clock size={26} strokeWidth={2.2} />
                </div>

                <h3 className="faculty-active-course-title">
                  {upcomingClass.course_code ? `${upcomingClass.course_code} – ${upcomingClass.course_name || ""}` : "Next Scheduled Class"}
                </h3>
                <p className="faculty-active-course-sub">
                  {upcomingClass.section ? `Section ${upcomingClass.section} • ` : ""}
                  {upcomingClass.room ? `Room ${upcomingClass.room} • ` : ""}
                  Scheduled {formatTime(upcomingClass.start_time)} – {formatTime(upcomingClass.end_time)}
                </p>

                <div className="faculty-active-status-row">
                  <div className="faculty-session-upcoming-pill">
                    <Clock size={13} />
                    <span>Upcoming • Starts at {formatTime(upcomingClass.start_time)}</span>
                  </div>
                </div>

                <button
                  type="button"
                  className="faculty-view-live-btn faculty-btn-disabled"
                  disabled
                  title={`Attendance opens at ${formatTime(upcomingClass.start_time)}`}
                >
                  <Clock size={16} />
                  <span>Attendance Not Started</span>
                </button>
                <span className="faculty-upcoming-hint">
                  Attendance cannot be accessed before the scheduled start time ({formatTime(upcomingClass.start_time)}).
                </span>
              </div>
            ) : (
              <div className="faculty-no-active-box">
                <div className="faculty-inactive-cam-circle">
                  <Camera size={26} strokeWidth={1.8} />
                </div>
                <h3>No active attendance session</h3>
                <p>
                  {todaysClasses.length > 0 && todaysClasses.every((c) => getClassScheduleStatus(c.start_time, c.end_time).status === "ENDED")
                    ? "All scheduled classes for today have ended."
                    : "Choose an assigned course and start attendance when your class is scheduled."}
                </p>

                <button
                  type="button"
                  className="faculty-start-session-btn"
                  onClick={() => openStartDialog()}
                  disabled={courses.length === 0}
                >
                  <Camera size={16} />
                  <span>Start Attendance</span>
                </button>
              </div>
            )}

          </div>

          {/* Card: Recent Attendance Activity */}
          <div className="faculty-panel-card">
            <div className="faculty-panel-header">
              <div className="faculty-panel-header-left">
                <div className="faculty-panel-header-icon faculty-icon-blue">
                  <Clock size={18} />
                </div>
                <div>
                  <h2 className="faculty-panel-title">Recent Attendance Activity</h2>
                  <p className="faculty-panel-subtitle">Recent session history and attendance changes.</p>
                </div>
              </div>

              <button
                type="button"
                className="faculty-header-link"
                onClick={() => navigate("/faculty/attendance")}
              >
                View all
              </button>
            </div>

            {sessionStatus === "loading" ? (
              <div className="faculty-empty-state">
                <p>Loading session history from backend...</p>
              </div>
            ) : sessionStatus === "error" ? (
              <div className="faculty-empty-state">
                <AlertCircle size={22} className="text-amber" />
                <strong>Unable to load session history</strong>
                <p>Could not retrieve recent session history from the server.</p>
                <button
                  type="button"
                  className="faculty-retry-btn"
                  onClick={reloadSessions}
                >
                  <RotateCw size={14} /> Retry
                </button>
              </div>
            ) : recentSessions.length === 0 ? (
              <div className="faculty-empty-state">
                <Clock size={22} className="text-muted" />
                <strong>No attendance sessions yet</strong>
                <p>Your recent sessions will appear here after attendance has been recorded.</p>
              </div>
            ) : (
              <div className="faculty-timeline-list">
                {recentSessions.slice(0, 4).map((s) => (
                  <div key={s.session_id} className="faculty-timeline-item">
                    <div className="faculty-timeline-bullet bullet-blue" />

                    <div className="faculty-timeline-content">
                      <strong className="faculty-timeline-title">
                        {s.course_code ? `${s.course_code} – ${s.course_name || ""}` : `Session #${s.session_id}`}
                      </strong>
                      <span className="faculty-timeline-meta">
                        Session #{s.session_id} • {s.session_date} {s.start_time ? `• ${formatTime(s.start_time)}` : ""}
                      </span>
                    </div>

                    <span className="faculty-closed-badge">{s.status || "Closed"}</span>
                  </div>
                ))}
              </div>
            )}

            <button
              type="button"
              className="faculty-text-arrow-btn"
              onClick={() => navigate("/faculty/attendance")}
            >
              View attendance history <ArrowRight size={15} />
            </button>
          </div>
        </div>

        {/* Column 3: Right */}
        <div className="faculty-col faculty-col-right">
          {/* Card: Quick Actions */}
          <div className="faculty-panel-card">
            <div className="faculty-panel-header">
              <div className="faculty-panel-header-left">
                <div className="faculty-panel-header-icon faculty-icon-blue">
                  <Zap size={18} />
                </div>
                <div>
                  <h2 className="faculty-panel-title">Quick Actions</h2>
                  <p className="faculty-panel-subtitle">Jump to a faculty workspace.</p>
                </div>
              </div>
            </div>

            <div className="faculty-quick-actions-list">
              {/* 1. Start Attendance */}
              <button
                type="button"
                className="faculty-quick-action-row"
                onClick={() => openStartDialog()}
              >
                <div className="faculty-action-icon-box bg-emerald">
                  <Camera size={18} />
                </div>
                <div className="faculty-action-copy">
                  <strong className="faculty-action-name">Start Attendance</strong>
                  <span className="faculty-action-desc">Start a session for an assigned course</span>
                </div>
                <ChevronRight size={16} className="faculty-action-chevron" />
              </button>

              {/* 2. Attendance */}
              <button
                type="button"
                className="faculty-quick-action-row"
                onClick={() => navigate("/faculty/attendance")}
              >
                <div className="faculty-action-icon-box bg-blue">
                  <SquareCheck size={18} />
                </div>
                <div className="faculty-action-copy">
                  <strong className="faculty-action-name">Attendance</strong>
                  <span className="faculty-action-desc">Open attendance management</span>
                </div>
                <ChevronRight size={16} className="faculty-action-chevron" />
              </button>

              {/* 3. My Classes */}
              <button
                type="button"
                className="faculty-quick-action-row"
                onClick={() => navigate("/faculty/classes")}
              >
                <div className="faculty-action-icon-box bg-purple">
                  <Calendar size={18} />
                </div>
                <div className="faculty-action-copy">
                  <strong className="faculty-action-name">My Classes</strong>
                  <span className="faculty-action-desc">View assigned class offerings</span>
                </div>
                <ChevronRight size={16} className="faculty-action-chevron" />
              </button>

              {/* 4. Students */}
              <button
                type="button"
                className="faculty-quick-action-row"
                onClick={() => navigate("/faculty/students")}
              >
                <div className="faculty-action-icon-box bg-teal">
                  <Users size={18} />
                </div>
                <div className="faculty-action-copy">
                  <strong className="faculty-action-name">Students</strong>
                  <span className="faculty-action-desc">View enrolled students</span>
                </div>
                <ChevronRight size={16} className="faculty-action-chevron" />
              </button>

              {/* 5. Reports */}
              <button
                type="button"
                className="faculty-quick-action-row"
                onClick={() => navigate("/faculty/reports")}
              >
                <div className="faculty-action-icon-box bg-coral">
                  <BarChart3 size={18} />
                </div>
                <div className="faculty-action-copy">
                  <strong className="faculty-action-name">Reports</strong>
                  <span className="faculty-action-desc">Open attendance reports</span>
                </div>
                <ChevronRight size={16} className="faculty-action-chevron" />
              </button>

              {/* 6. My Profile */}
              <button
                type="button"
                className="faculty-quick-action-row"
                onClick={() => navigate("/faculty/profile")}
              >
                <div className="faculty-action-icon-box bg-indigo">
                  <UserIcon size={18} />
                </div>
                <div className="faculty-action-copy">
                  <strong className="faculty-action-name">My Profile</strong>
                  <span className="faculty-action-desc">View faculty profile details</span>
                </div>
                <ChevronRight size={16} className="faculty-action-chevron" />
              </button>
            </div>
          </div>

          {/* Card: Faculty Help */}
          <div className="faculty-panel-card faculty-help-card">
            <div className="faculty-help-header">
              <div className="faculty-help-circle-icon">
                <Headphones size={20} />
              </div>
              <h2 className="faculty-panel-title">Faculty Help</h2>
            </div>

            <p className="faculty-help-text">
              If your courses, timetable, or attendance data are missing, contact your administrator to verify the relevant records.
            </p>

            <button
              type="button"
              className="faculty-help-btn"
              onClick={() => navigate("/faculty/profile")}
            >
              View faculty profile <ArrowRight size={14} />
            </button>
          </div>

          {/* Card: Faculty access confirmed */}
          <div className="faculty-panel-card faculty-status-confirmed-card">
            <div className="faculty-status-confirmed-inner">
              <div className="faculty-confirmed-circle-icon">
                <CheckCircle2 size={24} strokeWidth={2.4} />
              </div>

              <div className="faculty-confirmed-text">
                <strong className="faculty-confirmed-title">
                  {backendStatus === "connected"
                    ? "Faculty access confirmed"
                    : "Backend connection status"}
                </strong>
                <span className="faculty-confirmed-desc">
                  {backendStatus === "connected"
                    ? "All systems are connected and active."
                    : "Connecting to faculty backend service..."}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Start Attendance Dialog Modal */}
      {showStartDialog && (() => {
        const selectedOffering =
          courses.find((c) => String(c.offering_id) === String(selectedOfferingId)) ||
          distinctOfferings.find((c) => String(c.offering_id) === String(selectedOfferingId));
        const availableSlots = timetable.filter(
          (t) =>
            String(t.offering_id) === String(selectedOfferingId) &&
            String(t.day_of_week || "").trim().toLowerCase() === todayWeekday.toLowerCase()
        );
        const allOfferingSlots = timetable.filter(
          (t) => String(t.offering_id) === String(selectedOfferingId)
        );
        const displaySlots = availableSlots.length > 0 ? availableSlots : allOfferingSlots;
        const activeSlot = displaySlots.find(
          (s) => getClassScheduleStatus(s.start_time, s.end_time, s.day_of_week).status === "ACTIVE"
        );
        const upcomingSlot = displaySlots.find(
          (s) => getClassScheduleStatus(s.start_time, s.end_time, s.day_of_week).status === "UPCOMING"
        );
        const currentSlot =
          displaySlots.find(
            (t) => String(t.timetable_entry_id) === String(selectedTimetableEntryId)
          ) ||
          activeSlot ||
          upcomingSlot ||
          displaySlots[0];
        const slotStatus = currentSlot
          ? getClassScheduleStatus(currentSlot.start_time, currentSlot.end_time, currentSlot.day_of_week)
          : null;
        const isSlotToday = currentSlot
          ? String(currentSlot.day_of_week || "").trim().toLowerCase() === todayWeekday.toLowerCase()
          : false;
        const isSlotEnded = isSlotToday && slotStatus?.status === "ENDED";
        const isSlotUpcoming = isSlotToday && slotStatus?.status === "UPCOMING";

        return (
          <div
            className="faculty-dialog-backdrop"
            onClick={(e) => {
              if (e.target === e.currentTarget && !startingSession) {
                setShowStartDialog(false);
              }
            }}
            role="presentation"
          >
            <div
              className="faculty-modal-card"
              role="dialog"
              aria-modal="true"
              aria-labelledby="start-attendance-title"
            >
              <div className="faculty-modal-header">
                <div className="faculty-modal-header-main">
                  <div className="faculty-modal-header-icon" aria-hidden="true">
                    <Camera size={20} />
                  </div>
                  <div className="faculty-modal-header-text">
                    <span className="faculty-modal-eyebrow">Attendance Session</span>
                    <h3 id="start-attendance-title" className="faculty-modal-title">
                      Start Attendance
                    </h3>
                    <p className="faculty-modal-sub">
                      Select the assigned course offering and scheduled timetable slot.
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  className="faculty-modal-close"
                  onClick={() => setShowStartDialog(false)}
                  disabled={startingSession}
                  aria-label="Close dialog"
                >
                  <X size={18} />
                </button>
              </div>

              <form onSubmit={handleStartAttendance}>
                <div className="faculty-modal-field">
                  <label htmlFor="course-select-input" className="faculty-modal-label">
                    Course offering
                  </label>
                  <div className="faculty-modal-select-wrapper">
                    <select
                      id="course-select-input"
                      className="faculty-modal-select"
                      value={selectedOfferingId}
                      onChange={(e) => handleOfferingChange(e.target.value)}
                      disabled={startingSession || distinctOfferings.length === 0}
                    >
                      {distinctOfferings.length === 0 ? (
                        <option value="">No assigned courses available</option>
                      ) : (
                        distinctOfferings.map((c) => (
                          <option key={c.offering_id} value={c.offering_id}>
                            {c.course_code} — {c.course_name}
                            {c.section ? ` · Section ${c.section}` : ""}
                            {c.semester ? ` (Sem ${c.semester})` : ""}
                            {c.academic_year ? ` · ${formatAcademicYear(c.academic_year, c.semester)}` : ""}
                          </option>
                        ))
                      )}
                    </select>
                    <ChevronDown className="faculty-modal-select-chevron" size={16} aria-hidden="true" />
                  </div>
                </div>

                {displaySlots.length > 0 && (
                  <div className="faculty-modal-field">
                    <label htmlFor="slot-select-input" className="faculty-modal-label">
                      Scheduled timetable slot
                    </label>
                    <div className="faculty-modal-select-wrapper">
                      <select
                        id="slot-select-input"
                        className="faculty-modal-select"
                        value={selectedTimetableEntryId || (currentSlot ? String(currentSlot.timetable_entry_id) : "")}
                        onChange={(e) => {
                          setSelectedTimetableEntryId(e.target.value);
                          setStartError("");
                        }}
                        disabled={startingSession}
                      >
                        {displaySlots.map((slot) => {
                          const st = getClassScheduleStatus(slot.start_time, slot.end_time, slot.day_of_week);
                          return (
                            <option key={slot.timetable_entry_id} value={slot.timetable_entry_id}>
                              {slot.day_of_week} {formatTime(slot.start_time)} – {formatTime(slot.end_time)}
                              {slot.room ? ` · Room ${slot.room}` : ""} — [{st.label}]
                            </option>
                          );
                        })}
                      </select>
                      <ChevronDown className="faculty-modal-select-chevron" size={16} aria-hidden="true" />
                    </div>
                  </div>
                )}

                {currentSlot && (
                  <div className="faculty-modal-details-card">
                    <div className="faculty-modal-details-header">
                      <div className="faculty-modal-details-title-wrap">
                        <Calendar size={15} className="faculty-modal-details-icon" aria-hidden="true" />
                        <strong className="faculty-modal-details-title">Scheduled Class Details</strong>
                      </div>
                      <span
                        className={`faculty-modal-details-badge ${
                          slotStatus?.status === "ACTIVE"
                            ? "is-active"
                            : slotStatus?.status === "UPCOMING"
                            ? "is-upcoming"
                            : "is-ended"
                        }`}
                      >
                        {slotStatus?.label || "SCHEDULED"}
                      </span>
                    </div>
                    <div className="faculty-modal-details-grid">
                      <div className="faculty-modal-details-item">
                        <span className="faculty-modal-details-label">Date</span>
                        <span className="faculty-modal-details-value">
                          {currentSlot.day_of_week} {isSlotToday ? `(${todayWeekday})` : "(Scheduled)"}
                        </span>
                      </div>
                      <div className="faculty-modal-details-item">
                        <span className="faculty-modal-details-label">Section</span>
                        <span className="faculty-modal-details-value">{selectedOffering?.section || "N/A"}</span>
                      </div>
                      <div className="faculty-modal-details-item">
                        <span className="faculty-modal-details-label">Time</span>
                        <span className="faculty-modal-details-value">
                          {formatTime(currentSlot.start_time)} – {formatTime(currentSlot.end_time)}
                        </span>
                      </div>
                      <div className="faculty-modal-details-item">
                        <span className="faculty-modal-details-label">Room</span>
                        <span className="faculty-modal-details-value">
                          {currentSlot.room || selectedOffering?.room || "Not assigned"}
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {!isSlotToday && (
                  <div className="faculty-modal-banner is-warning" role="alert">
                    <Clock size={16} className="faculty-modal-banner-icon" aria-hidden="true" />
                    <span>
                      This timetable slot is scheduled for {currentSlot.day_of_week}. Attendance sessions can only be started during class hours on {currentSlot.day_of_week}.
                    </span>
                  </div>
                )}

                {isSlotEnded && (
                  <div className="faculty-modal-banner is-error" role="alert">
                    <AlertCircle size={16} className="faculty-modal-banner-icon" aria-hidden="true" />
                    <span>Cannot start attendance: scheduled class window ended at {formatTime(currentSlot.end_time)}.</span>
                  </div>
                )}

                {isSlotUpcoming && (
                  <div className="faculty-modal-banner is-warning" role="alert">
                    <Clock size={16} className="faculty-modal-banner-icon" aria-hidden="true" />
                    <span>Cannot start attendance yet: scheduled class starts at {formatTime(currentSlot.start_time)}.</span>
                  </div>
                )}

                {startError && (
                  <div className="faculty-modal-banner is-error" role="alert">
                    <AlertCircle size={16} className="faculty-modal-banner-icon" aria-hidden="true" />
                    <span>{startError}</span>
                  </div>
                )}

                <div className="faculty-modal-note">
                  <Zap size={14} className="faculty-modal-note-icon" aria-hidden="true" />
                  <span>
                    This initializes the attendance session. Camera face recognition controls will be available on the Attendance page.
                  </span>
                </div>

                <div className="faculty-modal-actions">
                  <button
                    type="button"
                    className="faculty-modal-cancel"
                    onClick={() => setShowStartDialog(false)}
                    disabled={startingSession}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="faculty-modal-confirm"
                    disabled={
                      startingSession ||
                      courses.length === 0 ||
                      isSlotEnded ||
                      isSlotUpcoming ||
                      !isSlotToday
                    }
                    title={
                      !isSlotToday
                        ? `Slot is scheduled for ${currentSlot?.day_of_week}, not today (${todayWeekday})`
                        : isSlotEnded
                        ? "Class has already ended"
                        : isSlotUpcoming
                        ? "Class has not started yet"
                        : "Start session"
                    }
                  >
                    {startingSession ? (
                      <>
                        <span className="faculty-modal-spinner" aria-hidden="true" />
                        <span>Starting...</span>
                      </>
                    ) : (
                      "Confirm & Start"
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>
        );
      })()}

    </div>
  );
}

export default FacultyDashboard;
