import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useNavigate } from "react-router-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faArrowLeft,
  faArrowRight,
  faBookOpen,
  faCalendar,
  faCamera,
  faChartLine,
  faCircleCheck,
  faCircleExclamation,
  faCircleInfo,
  faClock,
  faMagnifyingGlass,
  faRotateRight,
  faSpinner,
  faUserCheck,
  faUsers,
  faXmark,
  faBolt,
  faFileLines,
  faPlay,
  faPause,
  faShieldHalved,
  faTriangleExclamation,
} from "@fortawesome/free-solid-svg-icons";

import "./Attendance.css";

import {
  closeFacultyAttendanceSession,
  getActiveFacultyAttendanceSession,
  getFacultyAttendanceOverview,
  getFacultyAttendanceRecords,
  getFacultyAttendanceSessions,
  getFacultyCourses,
  getFacultyStudents,
  getFacultyTimetable,
  getSystemHealth,
  recordVerifiedAttendance,
  requestLivenessChallenge,
  startFacultyAttendanceSession,
  verifyLiveness,
} from "../../services/facultyService";

const getErrorMessage = (error, fallback) =>
  error?.response?.data?.message || error?.message || fallback;

const getList = (result) =>
  Array.isArray(result?.data) ? result.data : [];

const isSameId = (left, right) =>
  left != null && right != null && String(left) === String(right);

const formatDate = (value) => {
  if (!value) return "N/A";

  const text = String(value);
  const date = /^\d{4}-\d{2}-\d{2}$/.test(text)
    ? new Date(`${text}T12:00:00`)
    : new Date(text);

  return Number.isNaN(date.getTime())
    ? text
    : date.toLocaleDateString();
};

const formatTime = (value) => {
  if (!value) return "N/A";

  const text = String(value);
  const timeOnly = text.match(/^(\d{1,2}):(\d{2})(?::\d{2})?$/);

  if (timeOnly) {
    const hours = Number(timeOnly[1]);
    const minutes = Number(timeOnly[2]);

    if (hours > 23 || minutes > 59) return text;

    return new Date(2000, 0, 1, hours, minutes).toLocaleTimeString(
      [],
      { hour: "2-digit", minute: "2-digit" }
    );
  }

  const date = new Date(text);

  return Number.isNaN(date.getTime())
    ? text
    : date.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });
};

const getClassScheduleStatus = (startTime, endTime, dayOfWeek = null) => {
  if (!startTime || !endTime) return { status: "SCHEDULED", label: "Scheduled", isToday: false };
  const todayWeekday = new Intl.DateTimeFormat("en-US", { weekday: "long" }).format(new Date());
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
  const sMatch = String(startTime).match(/^(\d{1,2}):(\d{2})/);
  const eMatch = String(endTime).match(/^(\d{1,2}):(\d{2})/);
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
};


const getTodayDate = () => {
  const today = new Date();

  return [
    today.getFullYear(),
    String(today.getMonth() + 1).padStart(2, "0"),
    String(today.getDate()).padStart(2, "0"),
  ].join("-");
};

const getCourseLabel = (course) => {
  const code = course?.course_code || "";
  const name = course?.course_name || course?.name || "";

  if (code && name) return `${code} – ${name}`;

  return code || name || `Offering ${course?.offering_id ?? "N/A"}`;
};

const getStudentName = (student) =>
  student?.name ||
  student?.full_name ||
  [student?.first_name, student?.last_name].filter(Boolean).join(" ") ||
  "Unknown Student";

const getAttendanceStatus = (record) =>
  record?.status || "NOT MARKED";

const getInitials = (name) =>
  String(name || "?")
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join("") || "?";

function Attendance() {
  const navigate = useNavigate();

  const [sessions, setSessions] = useState([]);
  const [activeSession, setActiveSession] = useState(null);
  const [courses, setCourses] = useState([]);
  const [students, setStudents] = useState([]);
  const [attendanceRecords, setAttendanceRecords] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [overviewData, setOverviewData] = useState(null);
  const [systemHealth, setSystemHealth] = useState({
    loading: true,
    connected: false,
    message: "",
  });

  const [loading, setLoading] = useState(true);
  const [coursesLoading, setCoursesLoading] = useState(true);
  const [studentsLoading, setStudentsLoading] = useState(true);
  const [recordsLoading, setRecordsLoading] = useState(false);

  const [error, setError] = useState("");
  const [coursesError, setCoursesError] = useState("");
  const [studentsError, setStudentsError] = useState("");
  const [recordsError, setRecordsError] = useState("");
  const [startError, setStartError] = useState("");
  const [closeError, setCloseError] = useState("");
  const [faceAttendanceError, setFaceAttendanceError] = useState("");

  const [showStartModal, setShowStartModal] = useState(false);
  const [selectedOfferingId, setSelectedOfferingId] = useState("");
  const [selectedTimetableEntryId, setSelectedTimetableEntryId] = useState("");
  const [startingSession, setStartingSession] = useState(false);
  const [closingSession, setClosingSession] = useState(false);


  const [showFaceAttendance, setShowFaceAttendance] = useState(false);
  const [cameraReady, setCameraReady] = useState(false);
  const [recognizingFace, setRecognizingFace] = useState(false);
  const [autoScanActive, setAutoScanActive] = useState(true);
  const [lastRecognizedStudent, setLastRecognizedStudent] = useState(null);
  const [recentDetections, setRecentDetections] = useState([]);
  const [scanStatusMessage, setScanStatusMessage] = useState("Position your face in the frame");
  const [livenessState, setLivenessState] = useState("POSITION_FACE");
  const [currentChallenge, setCurrentChallenge] = useState(null);

  const [searchTerm, setSearchTerm] = useState("");
  const [studentSearch, setStudentSearch] = useState("");
  const [selectedClass, setSelectedClass] = useState("All Classes");
  const [date, setDate] = useState("");
  const [status, setStatus] = useState("All");
  const [activeTab, setActiveTab] = useState("attendance");
  const [scheduleExpanded, setScheduleExpanded] = useState(true);
  const [timetableEntries, setTimetableEntries] = useState([]);
  const [timetableLoading, setTimetableLoading] = useState(true);
  const [timetableError, setTimetableError] = useState("");
  const [page, setPage] = useState(1);

  const pageSize = 5;

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const cameraStreamRef = useRef(null);
  const recordsRequestRef = useRef(0);
  const recognitionRequestRef = useRef(false);
  const selectedSessionRef = useRef(null);
  const currentChallengeRef = useRef(null);

  const handleRetryChallenge = useCallback(() => {
    currentChallengeRef.current = null;
    setCurrentChallenge(null);
    setLivenessState("POSITION_FACE");
    setScanStatusMessage("Position your face in the frame");
  }, []);

  const stopCamera = useCallback(() => {
    if (cameraStreamRef.current) {
      cameraStreamRef.current.getTracks().forEach((track) => track.stop());
      cameraStreamRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.pause();
      videoRef.current.srcObject = null;
    }

    setCameraReady(false);
  }, []);

  const checkSystemHealth = useCallback(async () => {
    setSystemHealth((prev) => ({ ...prev, loading: true }));
    try {
      const res = await getSystemHealth();
      if (res?.database === "ok") {
        setSystemHealth({
          loading: false,
          connected: true,
          message: "Database & Backend Connected",
        });
      } else {
        setSystemHealth({
          loading: false,
          connected: false,
          message: res?.message || "Database connection degraded",
        });
      }
    } catch (err) {
      setSystemHealth({
        loading: false,
        connected: false,
        message: getErrorMessage(err, "Backend connection failed"),
      });
    }
  }, []);

  useEffect(() => {
    let isCancelled = false;

    async function loadHealth() {
      try {
        const res = await getSystemHealth();
        if (isCancelled) return;
        if (res?.database === "ok") {
          setSystemHealth({
            loading: false,
            connected: true,
            message: "Database & Backend Connected",
          });
        } else {
          setSystemHealth({
            loading: false,
            connected: false,
            message: res?.message || "Database connection degraded",
          });
        }
      } catch (err) {
        if (isCancelled) return;
        setSystemHealth({
          loading: false,
          connected: false,
          message: getErrorMessage(err, "Backend connection failed"),
        });
      }
    }

    void loadHealth();

    return () => {
      isCancelled = true;
    };
  }, []);

  const loadAttendanceRecords = useCallback(async (session) => {
    const requestId = ++recordsRequestRef.current;

    if (!session?.session_id) {
      selectedSessionRef.current = null;
      setSelectedSession(null);
      setAttendanceRecords([]);
      setRecordsError("");
      setRecordsLoading(false);
      return;
    }

    selectedSessionRef.current = session;
    setSelectedSession(session);
    setRecordsLoading(true);
    setRecordsError("");

    try {
      const [recordsResult, overviewResult, studentsResult] = await Promise.all([
        getFacultyAttendanceRecords(session.session_id),
        getFacultyAttendanceOverview({ session_id: session.session_id }),
        session.offering_id
          ? getFacultyStudents({ offering_id: session.offering_id })
          : Promise.resolve(null),
      ]);

      if (requestId !== recordsRequestRef.current) return;

      if (!recordsResult?.success) {
        throw new Error(
          recordsResult?.message || "Unable to load attendance records."
        );
      }

      setAttendanceRecords(getList(recordsResult));

      if (overviewResult?.success && overviewResult?.data) {
        setOverviewData(overviewResult.data);
      }

      if (studentsResult?.success && Array.isArray(studentsResult.data)) {
        setStudents((prev) => {
          const incoming = studentsResult.data;
          const map = new Map(prev.map((s) => [String(s.student_id), s]));
          for (const s of incoming) {
            map.set(String(s.student_id), s);
          }
          return Array.from(map.values());
        });
      }
    } catch (requestError) {
      if (requestId !== recordsRequestRef.current) return;

      setAttendanceRecords([]);
      setRecordsError(
        getErrorMessage(requestError, "Unable to load attendance records.")
      );
    } finally {
      if (requestId === recordsRequestRef.current) {
        setRecordsLoading(false);
      }
    }
  }, []);

  const refreshSessions = useCallback(async (preserveSessionId = null) => {
    setLoading(true);
    setError("");

    try {
      const targetId = preserveSessionId || selectedSessionRef.current?.session_id;
      const [sessionsResult, activeResult, overviewResult] = await Promise.all([
        getFacultyAttendanceSessions(),
        getActiveFacultyAttendanceSession(),
        getFacultyAttendanceOverview(targetId ? { session_id: targetId } : {}),
      ]);

      if (!sessionsResult?.success) {
        throw new Error(
          sessionsResult?.message || "Unable to load attendance sessions."
        );
      }

      if (!activeResult?.success) {
        throw new Error(
          activeResult?.message || "Unable to load the active session."
        );
      }

      const sessionList = getList(sessionsResult);
      const active = activeResult.data || null;

      setSessions(sessionList);
      setActiveSession(active);

      if (overviewResult?.success && overviewResult?.data) {
        setOverviewData(overviewResult.data);
      }

      // Determine target session synchronously
      let target = null;
      if (targetId) {
        target = sessionList.find((item) => isSameId(item.session_id, targetId)) || null;
      }
      if (!target) {
        target = active || sessionList[0] || null;
      }

      selectedSessionRef.current = target;
      setSelectedSession(target);

      if (target?.session_id) {
        await loadAttendanceRecords(target);
      } else {
        setAttendanceRecords([]);
      }
    } catch (requestError) {
      setError(
        getErrorMessage(requestError, "Unable to load attendance sessions.")
      );
    } finally {
      setLoading(false);
    }
  }, [loadAttendanceRecords]);

  useEffect(
    () => () => {
      if (cameraStreamRef.current) {
        cameraStreamRef.current.getTracks().forEach((track) => track.stop());
        cameraStreamRef.current = null;
      }
    },
    []
  );

  useEffect(() => {
    let mounted = true;
    const loadTimetable = async () => {
      setTimetableLoading(true);
      setTimetableError("");
      try {
        const result = await getFacultyTimetable();
        if (!result?.success) {
          throw new Error(
            result?.message || "Unable to load the faculty timetable."
          );
        }
        if (mounted) {
          setTimetableEntries(
            Array.isArray(result.data) ? result.data : []
          );
        }
      } catch (err) {
        if (mounted) {
          setTimetableError(
            getErrorMessage(err, "Unable to load the timetable.")
          );
        }
      } finally {
        if (mounted) {
          setTimetableLoading(false);
        }
      }
    };
    loadTimetable();
    return () => {
      mounted = false;
    };
  }, []);
  useEffect(() => {
    if (!showFaceAttendance || !cameraStreamRef.current || !videoRef.current) {
      return undefined;
    }

    const video = videoRef.current;
    video.srcObject = cameraStreamRef.current;

    let cancelled = false;

    const startVideo = async () => {
      try {
        await video.play();

        if (!cancelled) {
          setCameraReady(true);
          setFaceAttendanceError("");
        }
      } catch (playError) {
        if (!cancelled) {
          setCameraReady(false);
          setFaceAttendanceError(
            getErrorMessage(playError, "Unable to start the camera preview.")
          );
        }
      }
    };

    if (video.readyState >= 2) {
      startVideo();
    } else {
      video.addEventListener("loadeddata", startVideo, { once: true });
    }

    return () => {
      cancelled = true;
      video.removeEventListener("loadeddata", startVideo);
    };
  }, [showFaceAttendance]);

  // Automated real-time face recognition and liveness verification scanner loop
  useEffect(() => {
    if (!showFaceAttendance || !cameraReady || !autoScanActive) {
      return undefined;
    }

    const session = activeSession || selectedSession;
    if (!session || session.status !== "ACTIVE") {
      return undefined;
    }

    let isCancelled = false;
    let timerId = null;

    const captureCanvasBlob = async (video, canvas) => {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d");
      if (!ctx) throw new Error("Unable to get 2d context");
      // Mirror horizontally to match what the user sees in the mirrored webcam preview
      ctx.save();
      ctx.translate(canvas.width, 0);
      ctx.scale(-1, 1);
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      ctx.restore();
      return new Promise((resolve, reject) => {
        canvas.toBlob(
          (blob) => (blob ? resolve(blob) : reject(new Error("Unable to capture frame"))),
          "image/jpeg",
          0.90
        );
      });
    };

    const performScanCycle = async () => {
      if (
        isCancelled ||
        recognitionRequestRef.current ||
        !videoRef.current ||
        !canvasRef.current
      ) {
        return;
      }

      const video = videoRef.current;
      const canvas = canvasRef.current;

      if (!video.videoWidth || !video.videoHeight || video.readyState < 2) {
        timerId = setTimeout(performScanCycle, 400);
        return;
      }

      recognitionRequestRef.current = true;
      setRecognizingFace(true);

      try {
        // Step 1: Ensure we have an active randomized liveness challenge
        let challenge = currentChallengeRef.current;
        if (!challenge) {
          setLivenessState("PERFORMING_CHECK");
          setScanStatusMessage("Requesting randomized liveness challenge…");

          const challengeRes = await requestLivenessChallenge(session.session_id);
          if (isCancelled) return;

          challenge = challengeRes;
          currentChallengeRef.current = challenge;
          setCurrentChallenge(challenge);
          setLivenessState("FOLLOW_INSTRUCTION");
          setScanStatusMessage(challenge.instruction || "Follow the randomized instruction");

          // Brief pause for user to view guidance instruction before baseline capture
          await new Promise((resolve) => setTimeout(resolve, 900));
          if (isCancelled) return;
        }

        // Step 2: Capture multi-frame evidence across the challenge movement
        // Frame 0: Baseline capture (neutral face looking at camera)
        const frame0Blob = await captureCanvasBlob(video, canvas);
        const t0 = 0;

        // Interval for action movement (1200ms allows natural human response and peak amplitude)
        await new Promise((resolve) => setTimeout(resolve, 1200));
        if (isCancelled) return;

        // Frame 1: Action movement frame
        const frame1Blob = await captureCanvasBlob(video, canvas);
        const t1 = 1200;

        // Interval for return / completion (800ms)
        await new Promise((resolve) => setTimeout(resolve, 800));
        if (isCancelled) return;

        // Frame 2: Completion frame
        const frame2Blob = await captureCanvasBlob(video, canvas);
        const t2 = 2000;

        setLivenessState("VERIFYING_IDENTITY");
        setScanStatusMessage("Verifying facial liveness & identity…");

        const formData = new FormData();
        formData.append("session_id", String(session.session_id));
        formData.append("challenge_id", challenge.challenge_id);
        formData.append("frames", frame0Blob, "frame_0.jpg");
        formData.append("frames", frame1Blob, "frame_1.jpg");
        formData.append("frames", frame2Blob, "frame_2.jpg");
        formData.append("timestamps", JSON.stringify([t0, t1, t2]));
        formData.append("mirrored", "true");

        const verifyResult = await verifyLiveness(formData);
        if (isCancelled) return;

        if (verifyResult?.status === "verified" && verifyResult.verification_token) {
          // Liveness and identity match passed on server!
          // Now mark attendance atomically using the issued single-use token:
          const attResult = await recordVerifiedAttendance(
            session.session_id,
            verifyResult.verification_token,
            verifyResult.student_id
          );

          if (isCancelled) return;

          if (attResult?.success && attResult.data) {
            const confirmedRecord = attResult.data;
            setAttendanceRecords((current) => {
              const updated = [...current];
              if (confirmedRecord.student_id) {
                const idx = updated.findIndex((item) => isSameId(item.student_id, confirmedRecord.student_id));
                if (idx >= 0) {
                  updated[idx] = { ...updated[idx], ...confirmedRecord };
                } else {
                  updated.push(confirmedRecord);
                }
              }
              return updated;
            });

            setLastRecognizedStudent(confirmedRecord);
            setLivenessState("VERIFIED_SUCCESS");

            if (confirmedRecord.is_new) {
              setScanStatusMessage(
                `✅ Marked: ${confirmedRecord.name || confirmedRecord.student_name} (${confirmedRecord.enrollment_no})`
              );
            } else {
              setScanStatusMessage(
                `ℹ️ ${confirmedRecord.name || confirmedRecord.student_name} — Already Present`
              );
            }

            setRecentDetections((prev) => {
              const items = [confirmedRecord, ...prev];
              const seen = new Set();
              const deduplicated = [];
              for (const item of items) {
                if (item.student_id && !seen.has(item.student_id)) {
                  seen.add(item.student_id);
                  deduplicated.push(item);
                }
              }
              return deduplicated.slice(0, 6);
            });

            // Reset challenge for the next student
            currentChallengeRef.current = null;
            setCurrentChallenge(null);

            // Wait 2.8s before scanning next student
            timerId = setTimeout(() => {
              setLivenessState("POSITION_FACE");
              setScanStatusMessage("Position your face in the frame");
              performScanCycle();
            }, 2800);
            return;
          }
        } else if (verifyResult?.status === "not_recognized") {
          setLivenessState("POSITION_FACE");
          setScanStatusMessage("Face detected — verifying registered profile…");
          currentChallengeRef.current = null;
          setCurrentChallenge(null);
          timerId = setTimeout(performScanCycle, 1500);
          return;
        } else if (verifyResult?.status === "no_face") {
          setLivenessState("POSITION_FACE");
          setScanStatusMessage("Position your face in the frame");
          timerId = setTimeout(performScanCycle, 900);
          return;
        } else if (verifyResult?.status === "multiple_faces") {
          setLivenessState("POSITION_FACE");
          setScanStatusMessage("Multiple faces detected — exactly one person at a time");
          timerId = setTimeout(performScanCycle, 1500);
          return;
        }
      } catch (scanError) {
        if (isCancelled) return;

        const statusNum = scanError?.response?.status;
        const resData = scanError?.response?.data;
        const msg = resData?.message || scanError?.message || "Verification failed";

        if (statusNum === 503 || resData?.status === "liveness_model_unavailable") {
          setLivenessState("MODEL_UNAVAILABLE");
          setScanStatusMessage("Liveness verification model is unavailable. Attendance fail-safe active.");
          currentChallengeRef.current = null;
          setCurrentChallenge(null);
          return;
        }

        if (resData?.status === "quality_warning") {
          setLivenessState("QUALITY_WARNING");
          setScanStatusMessage(`ℹ️ ${msg}`);
          currentChallengeRef.current = null;
          setCurrentChallenge(null);
          timerId = setTimeout(() => {
            setLivenessState("POSITION_FACE");
            setScanStatusMessage("Position your face in the frame");
            performScanCycle();
          }, 1800);
          return;
        }

        if (resData?.status === "spoof_suspected") {
          setLivenessState("SPOOF_SUSPECTED");
          setScanStatusMessage(`⚠️ Photo/screen spoof suspected: ${msg}`);
          currentChallengeRef.current = null;
          setCurrentChallenge(null);
          timerId = setTimeout(() => {
            setLivenessState("POSITION_FACE");
            setScanStatusMessage("Position your face in the frame");
            performScanCycle();
          }, 3000);
          return;
        }

        if (resData?.status === "challenge_failed" || resData?.status === "challenge_expired") {
          setLivenessState("CHALLENGE_EXPIRED");
          setScanStatusMessage(resData?.status === "challenge_expired" ? "Challenge expired; generating new prompt…" : `Liveness instruction incomplete: ${msg}`);
          currentChallengeRef.current = null;
          setCurrentChallenge(null);
          timerId = setTimeout(() => {
            setLivenessState("POSITION_FACE");
            setScanStatusMessage("Position your face in the frame");
            performScanCycle();
          }, 2000);
          return;
        }

        if (resData?.status === "ineligible") {
          setLivenessState("POSITION_FACE");
          setScanStatusMessage(`⚠️ ${msg}`);
          currentChallengeRef.current = null;
          setCurrentChallenge(null);
          timerId = setTimeout(() => {
            setLivenessState("POSITION_FACE");
            setScanStatusMessage("Position your face in the frame");
            performScanCycle();
          }, 2500);
          return;
        }

        if (statusNum === 409) {
          setScanStatusMessage(msg);
          setFaceAttendanceError(msg);
          stopCamera();
          setShowFaceAttendance(false);
          void refreshSessions();
          return;
        }

        if (statusNum === 401 || statusNum === 403) {
          const authMsg = resData?.message || "Session expired or access unauthorized.";
          setScanStatusMessage(authMsg);
          currentChallengeRef.current = null;
          setCurrentChallenge(null);
          return;
        }

        if (statusNum === 400) {
          setScanStatusMessage(msg);
          currentChallengeRef.current = null;
          setCurrentChallenge(null);
          timerId = setTimeout(performScanCycle, 2000);
          return;
        }

        console.debug("Live liveness scan error:", msg);
        timerId = setTimeout(performScanCycle, 1200);
      } finally {
        recognitionRequestRef.current = false;
        if (!isCancelled) {
          setRecognizingFace(false);
        }
      }
    };

    timerId = setTimeout(performScanCycle, 450);

    return () => {
      isCancelled = true;
      if (timerId) clearTimeout(timerId);
      recognitionRequestRef.current = false;
      setRecognizingFace(false);
    };
  }, [showFaceAttendance, cameraReady, autoScanActive, activeSession, selectedSession, refreshSessions, stopCamera]);

  useEffect(() => {
    const timerId = setTimeout(() => {
      void refreshSessions();
    }, 0);

    return () => clearTimeout(timerId);
  }, [refreshSessions]);

  useEffect(() => {
    let mounted = true;

    const loadCourses = async () => {
      setCoursesLoading(true);
      setCoursesError("");

      try {
        const result = await getFacultyCourses();

        if (!result?.success) {
          throw new Error(result?.message || "Unable to load courses.");
        }

        const courseList = getList(result);
        if (!mounted) return;

        setCourses(courseList);

        setSelectedOfferingId((current) => {
          if (
            current &&
            courseList.some((course) =>
              isSameId(course.offering_id, current)
            )
          ) {
            return current;
          }

          return courseList[0]?.offering_id != null
            ? String(courseList[0].offering_id)
            : "";
        });
      } catch (requestError) {
        if (!mounted) return;

        setCourses([]);
        setCoursesError(
          getErrorMessage(requestError, "Unable to load faculty courses.")
        );
      } finally {
        if (mounted) setCoursesLoading(false);
      }
    };

    loadCourses();

    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    let mounted = true;

    const loadStudents = async () => {
      setStudentsLoading(true);
      setStudentsError("");

      try {
        const result = await getFacultyStudents();

        if (!result?.success) {
          throw new Error(result?.message || "Unable to load students.");
        }

        if (mounted) setStudents(getList(result));
      } catch (requestError) {
        if (!mounted) return;

        setStudents([]);
        setStudentsError(
          getErrorMessage(requestError, "Unable to load faculty students.")
        );
      } finally {
        if (mounted) setStudentsLoading(false);
      }
    };

    loadStudents();

    return () => {
      mounted = false;
    };
  }, []);

  const offeringIdToLoad = selectedSession?.offering_id || activeSession?.offering_id || null;

  useEffect(() => {
    let mounted = true;
    if (!offeringIdToLoad) return undefined;

    const loadOfferingStudents = async () => {
      try {
        const result = await getFacultyStudents({ offering_id: offeringIdToLoad });
        if (mounted && result?.success && Array.isArray(result.data)) {
          setStudents((prev) => {
            const incoming = result.data;
            const map = new Map(prev.map((s) => [String(s.student_id), s]));
            for (const s of incoming) {
              map.set(String(s.student_id), s);
            }
            return Array.from(map.values());
          });
        }
      } catch {
        // gracefully handle
      }
    };

    loadOfferingStudents();

    return () => {
      mounted = false;
    };
  }, [offeringIdToLoad]);

  const courseMap = useMemo(
    () =>
      new Map(
        courses.map((course) => [String(course.offering_id), course])
      ),
    [courses]
  );

  const getSessionClassName = useCallback(
    (session) =>
      courseMap.has(String(session?.offering_id))
        ? getCourseLabel(courseMap.get(String(session.offering_id)))
        : `Offering ${session?.offering_id ?? "N/A"}`,
    [courseMap]
  );

  const classOptions = useMemo(() => {
    const labels = sessions
      .map(getSessionClassName)
      .filter(Boolean);

    return ["All Classes", ...Array.from(new Set(labels)).sort()];
  }, [sessions, getSessionClassName]);

  const filteredSessions = useMemo(() => {
    const query = searchTerm.trim().toLowerCase();

    return sessions.filter((session) => {
      const courseName = getSessionClassName(session);

      return (
        (!query || courseName.toLowerCase().includes(query)) &&
        (selectedClass === "All Classes" || courseName === selectedClass) &&
        (!date || String(session.session_date || "").slice(0, 10) === date) &&
        (status === "All" || session.status === status)
      );
    });
  }, [
    sessions,
    searchTerm,
    selectedClass,
    date,
    status,
    getSessionClassName,
  ]);

  const todaySessions = useMemo(() => {
    if (overviewData?.today_sessions != null) {
      return overviewData.today_sessions;
    }
    const today = getTodayDate();
    return sessions.filter(
      (session) => String(session.session_date || "").slice(0, 10) === today
    ).length;
  }, [overviewData, sessions]);

  const activeSessionsCount = useMemo(() => {
    if (overviewData?.active_sessions != null) {
      return overviewData.active_sessions;
    }
    return activeSession ? 1 : 0;
  }, [overviewData, activeSession]);

  const attendanceRecordMap = useMemo(
    () =>
      new Map(
        attendanceRecords.map((record) => [
          String(record.student_id),
          record,
        ])
      ),
    [attendanceRecords]
  );

  const displayedRecentDetections = useMemo(() => {
    if (recentDetections.length > 0) return recentDetections;
    return attendanceRecords
      .filter((r) => r.status === "PRESENT" || r.status === "LATE")
      .sort((a, b) => new Date(b.marked_at) - new Date(a.marked_at))
      .slice(0, 6)
      .map((r) => {
        const student = students.find((s) => isSameId(s.student_id, r.student_id));
        return {
          student_id: r.student_id,
          name: student ? getStudentName(student) : (r.student_name || `Student #${r.student_id}`),
          marked_at: r.marked_at,
          recognition_method: r.recognition_method,
        };
      });
  }, [recentDetections, attendanceRecords, students]);

  const studentsPresent = useMemo(() => {
    if (
      overviewData?.students_present != null &&
      isSameId(overviewData?.selected_session?.session_id, selectedSession?.session_id)
    ) {
      return overviewData.students_present;
    }
    return attendanceRecords.filter((record) => record.status === "PRESENT" || record.status === "LATE").length;
  }, [overviewData, selectedSession, attendanceRecords]);

  const sessionStudents = useMemo(() => {
    if (!selectedSession) return [];

    const enrolled = students.filter(
      (student) =>
        (student.offering_id != null &&
          isSameId(student.offering_id, selectedSession.offering_id)) ||
        (Array.isArray(student.offering_ids) &&
          student.offering_ids.some((id) =>
            isSameId(id, selectedSession.offering_id)
          ))
    );

    const studentIdMap = new Map(enrolled.map((s) => [String(s.student_id), s]));
    for (const rec of attendanceRecords) {
      if (rec.student_id && !studentIdMap.has(String(rec.student_id))) {
        const studentObj = students.find((s) => isSameId(s.student_id, rec.student_id)) || {
          student_id: rec.student_id,
          name: rec.student_name || `Student #${rec.student_id}`,
          enrollment_no: rec.enrollment_no || "N/A",
          offering_id: selectedSession.offering_id,
        };
        enrolled.push(studentObj);
        studentIdMap.set(String(rec.student_id), studentObj);
      }
    }

    return enrolled;
  }, [students, selectedSession, attendanceRecords]);

  const unrecordedStudentsCount = useMemo(() => {
    if (!selectedSession) return 0;
    return Math.max(0, sessionStudents.length - studentsPresent);
  }, [selectedSession, sessionStudents.length, studentsPresent]);

  const studentsAbsent = useMemo(() => {
    if (
      overviewData?.students_absent != null &&
      isSameId(overviewData?.selected_session?.session_id, selectedSession?.session_id)
    ) {
      if (selectedSession?.status === "ACTIVE") {
        return unrecordedStudentsCount;
      }
      return overviewData.students_absent;
    }
    if (selectedSession?.status === "ACTIVE") {
      return unrecordedStudentsCount;
    }
    return attendanceRecords.filter((record) => record.status === "ABSENT").length;
  }, [overviewData, selectedSession, unrecordedStudentsCount, attendanceRecords]);

  const attendanceRate = useMemo(() => {
    if (
      overviewData?.attendance_rate != null &&
      isSameId(overviewData?.selected_session?.session_id, selectedSession?.session_id)
    ) {
      return overviewData.attendance_rate;
    }
    const total = studentsPresent + studentsAbsent;

    if (!selectedSession || total === 0) return null;

    return Math.round((studentsPresent / total) * 100);
  }, [overviewData, selectedSession, studentsPresent, studentsAbsent]);

  const filteredStudents = useMemo(() => {
    const query = studentSearch.trim().toLowerCase();

    return sessionStudents.filter((student) => {
      const record = attendanceRecordMap.get(String(student.student_id));
      const name = getStudentName(student).toLowerCase();
      const enrollment = String(student.enrollment_no || "").toLowerCase();

      return (
        !query ||
        name.includes(query) ||
        enrollment.includes(query) ||
        String(student.student_id).includes(query) ||
        String(record?.status || "").toLowerCase().includes(query)
      );
    });
  }, [sessionStudents, studentSearch, attendanceRecordMap]);

  const totalPages = Math.max(
    1,
    Math.ceil(filteredStudents.length / pageSize)
  );

  const currentPage = Math.min(page, totalPages);

  const paginatedStudents = useMemo(() => {
    const start = (currentPage - 1) * pageSize;

    return filteredStudents.slice(start, start + pageSize);
  }, [filteredStudents, currentPage]);
  const handleSessionSelect = (session) => {
    void loadAttendanceRecords(session);
    setActiveTab("attendance");
  };

  const handleStartFaceAttendance = async () => {
    const session = activeSession || selectedSession;

    if (!session?.session_id) {
      setFaceAttendanceError("Start or select an attendance session first.");
      return;
    }

    if (session.status !== "ACTIVE" || session.is_eligible_for_attendance === false) {
      setFaceAttendanceError(
        session.schedule_status === "UPCOMING"
          ? (session.schedule_message || "Attendance cannot be started or recorded before the scheduled class start time.")
          : session.schedule_status === "ENDED"
          ? (session.schedule_message || "Class scheduled window has ended. Attendance recording is closed.")
          : "Face attendance is available only for active sessions within scheduled class hours."
      );
      return;
    }

    if (
      !isSameId(selectedSession?.session_id, session.session_id)
    ) {
      await loadAttendanceRecords(session);
    }

    if (!navigator.mediaDevices?.getUserMedia) {
      setFaceAttendanceError(
        "Camera access is unavailable. Use HTTPS or localhost in a supported browser."
      );
      return;
    }

    setFaceAttendanceError("");
    setCameraReady(false);

    try {
      stopCamera();

      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user" },
        audio: false,
      });

      cameraStreamRef.current = stream;
      setShowFaceAttendance(true);
    } catch (cameraError) {
      setFaceAttendanceError(
        cameraError?.name === "NotAllowedError"
          ? "Camera permission was denied. Allow camera access in your browser settings."
          : getErrorMessage(
              cameraError,
              "Unable to access the camera. Check that it is connected and not being used by another application."
            )
      );
    }
  };

  const handleCloseFaceAttendance = () => {
    stopCamera();
    recognitionRequestRef.current = false;
    setRecognizingFace(false);
    setFaceAttendanceError("");
    setShowFaceAttendance(false);
    setScanStatusMessage("Camera stopped");
  };

  const handleStartAttendance = async () => {
    if (!selectedOfferingId) {
      setStartError("Please select a course before starting attendance.");
      return;
    }

    setStartingSession(true);
    setStartError("");

    try {
      let entryIdToSubmit = selectedTimetableEntryId;
      if (!entryIdToSubmit && selectedOfferingId) {
        const dayNames = [
          "Sunday",
          "Monday",
          "Tuesday",
          "Wednesday",
          "Thursday",
          "Friday",
          "Saturday",
        ];
        const today = dayNames[new Date().getDay()];
        const offeringTodaySlots = timetableEntries.filter(
          (t) =>
            String(t.offering_id) === String(selectedOfferingId) &&
            String(t.day_of_week || "").trim().toLowerCase() === today.toLowerCase()
        );
        const allOfferingSlots = timetableEntries.filter(
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

      if (!result?.success || !result.data) {
        throw new Error(
          result?.message || "Unable to start attendance session."
        );
      }

      const newSession = result.data;

      setSessions((current) => [
        newSession,
        ...current.filter(
          (session) => !isSameId(session.session_id, newSession.session_id)
        ),
      ]);

      setActiveSession(newSession);
      selectedSessionRef.current = newSession;
      setSelectedSession(newSession);
      setAttendanceRecords([]);
      setRecordsError("");
      setShowStartModal(false);

      await loadAttendanceRecords(newSession);
      void refreshSessions(newSession.session_id);
    } catch (requestError) {
      setStartError(
        getErrorMessage(requestError, "Unable to start attendance session.")
      );
    } finally {
      setStartingSession(false);
    }
  };

  const handleCloseAttendance = async () => {
    if (!activeSession?.session_id) return;

    setClosingSession(true);
    setCloseError("");

    try {
      const result = await closeFacultyAttendanceSession(
        activeSession.session_id
      );

      if (!result?.success) {
        throw new Error(
          result?.message || "Unable to close attendance session."
        );
      }

      const closedSession = result.data || {
        ...activeSession,
        status: "CLOSED",
      };

      setSessions((current) =>
        current.map((session) =>
          isSameId(session.session_id, closedSession.session_id)
            ? { ...session, ...closedSession, status: "CLOSED" }
            : session
        )
      );

      setActiveSession(null);
      stopCamera();
      setShowFaceAttendance(false);

      await loadAttendanceRecords({
        ...closedSession,
        status: "CLOSED",
      });
      void refreshSessions(closedSession.session_id);
    } catch (requestError) {
      setCloseError(
        getErrorMessage(requestError, "Unable to close attendance session.")
      );
    } finally {
      setClosingSession(false);
    }
  };

  const handleOpenStartModal = (entry = null) => {
    setStartError("");

    const dayNames = [
      "Sunday",
      "Monday",
      "Tuesday",
      "Wednesday",
      "Thursday",
      "Friday",
      "Saturday",
    ];
    const today = dayNames[new Date().getDay()];

    if (entry) {
      setSelectedOfferingId(String(entry.offering_id));
      setSelectedTimetableEntryId(String(entry.timetable_entry_id));
    } else {
      const initialOfferingId = selectedOfferingId || (courses.length > 0 ? String(courses[0].offering_id) : "");
      setSelectedOfferingId(initialOfferingId);
      if (initialOfferingId) {
        const offeringTodaySlots = timetableEntries.filter(
          (t) =>
            String(t.offering_id) === String(initialOfferingId) &&
            String(t.day_of_week || "").trim().toLowerCase() === today.toLowerCase()
        );
        const activeSlot = offeringTodaySlots.find(
          (s) => getClassScheduleStatus(s.start_time, s.end_time).status === "ACTIVE"
        );
        const upcomingSlot = offeringTodaySlots.find(
          (s) => getClassScheduleStatus(s.start_time, s.end_time).status === "UPCOMING"
        );
        const bestSlot = activeSlot || upcomingSlot || offeringTodaySlots[0];
        setSelectedTimetableEntryId(bestSlot ? String(bestSlot.timetable_entry_id) : "");
      }
    }

    setShowStartModal(true);
  };

  const handleModalOfferingChange = (newOfferingId) => {
    setSelectedOfferingId(newOfferingId);
    setStartError("");

    const dayNames = [
      "Sunday",
      "Monday",
      "Tuesday",
      "Wednesday",
      "Thursday",
      "Friday",
      "Saturday",
    ];
    const today = dayNames[new Date().getDay()];
    const offeringTodaySlots = timetableEntries.filter(
      (t) =>
        String(t.offering_id) === String(newOfferingId) &&
        String(t.day_of_week || "").trim().toLowerCase() === today.toLowerCase()
    );
    const activeSlot = offeringTodaySlots.find(
      (s) => getClassScheduleStatus(s.start_time, s.end_time).status === "ACTIVE"
    );
    const upcomingSlot = offeringTodaySlots.find(
      (s) => getClassScheduleStatus(s.start_time, s.end_time).status === "UPCOMING"
    );
    const bestSlot = activeSlot || upcomingSlot || offeringTodaySlots[0];
    setSelectedTimetableEntryId(bestSlot ? String(bestSlot.timetable_entry_id) : "");
  };


  const clearFilters = () => {
    setSearchTerm("");
    setSelectedClass("All Classes");
    setDate("");
    setStatus("All");
  };

  const hasFilters =
    Boolean(searchTerm) ||
    selectedClass !== "All Classes" ||
    Boolean(date) ||
    status !== "All";

  const metrics = [
    {
      label: "Today's Sessions",
      value: loading ? "…" : todaySessions,
      note: "From session history",
      icon: faCalendar,
      tone: "blue",
    },
    {
      label: "Students Present",
      value: recordsLoading
        ? "…"
        : selectedSession
          ? studentsPresent
          : "N/A",
      note: selectedSession
        ? "Selected session"
        : "Select a session",
      icon: faCircleCheck,
      tone: "green",
    },
    {
      label: "Students Absent",
      value: recordsLoading
        ? "…"
        : selectedSession
          ? selectedSession.status === "ACTIVE"
            ? unrecordedStudentsCount
            : studentsAbsent
          : "N/A",
      note: selectedSession
        ? selectedSession.status === "ACTIVE"
          ? "Unmarked in progress"
          : "Selected session"
        : "Select a session",
      icon: faUsers,
      tone: "pink",
    },
    {
      label: "Active Sessions",
      value: loading ? "…" : activeSessionsCount,
      note: activeSession ? "Currently active" : "No active session",
      icon: faClock,
      tone: "purple",
    },
  ];

  const displayStudents = activeTab === "attendance"
    ? paginatedStudents
    : [];

  return (
    <div className="faculty-attendance-page attendance-dashboard-layout">
      <main className="attendance-main-column">
        <header className="attendance-page-header">
          <div>
            <span className="attendance-eyebrow">FACULTY WORKSPACE</span>
            <h1>Attendance</h1>
            <p>
              Mark attendance, view session details and track student presence
              in real time.
            </p>
          </div>

          <button
            type="button"
            className="attendance-primary-button"
            onClick={handleOpenStartModal}
            disabled={
              coursesLoading ||
              courses.length === 0 ||
              Boolean(activeSession)
            }
            title={
              activeSession
                ? "Close the active session before starting another session"
                : courses.length === 0
                  ? "No course offerings are available"
                  : "Start attendance"
            }
          >
            <FontAwesomeIcon icon={faCalendar} />
            Start Attendance
          </button>
        </header>

        {error && (
          <section className="attendance-integration-notice" role="alert">
            <div className="attendance-notice-icon">
              <FontAwesomeIcon icon={faCircleExclamation} />
            </div>
            <div>
              <strong>Unable to load attendance sessions</strong>
              <p>{error}</p>
              <button
                type="button"
                className="attendance-outline-button"
                onClick={refreshSessions}
              >
                <FontAwesomeIcon icon={faRotateRight} />
                Retry
              </button>
            </div>
          </section>
        )}

        <section className="attendance-metrics-grid">
          {metrics.map((metric) => (
            <article className="attendance-metric-card" key={metric.label}>
              <div className={`attendance-metric-icon ${metric.tone}`}>
                <FontAwesomeIcon icon={metric.icon} />
              </div>
              <div className="attendance-metric-content">
                <span>{metric.label}</span>
                <strong>{metric.value}</strong>
                <small>{metric.note}</small>
              </div>
            </article>
          ))}
        </section>

        <section className="active-attendance-card">
          <div className="active-attendance-heading">
            <div>
              <h2>
                <FontAwesomeIcon icon={faCalendar} />
                Live Attendance Session
              </h2>
              <p>
                {activeSession
                  ? getSessionClassName(activeSession)
                  : "No active attendance session"}
              </p>
            </div>

            <span
              className={`session-status ${
                activeSession ? "active" : "pending"
              }`}
            >
              {activeSession ? "Active" : "Inactive"}
            </span>
          </div>

          {activeSession ? (
            <>
              <div className="attendance-session-meta">
                <span>{formatDate(activeSession.session_date)}</span>
                <span>
                  {formatTime(activeSession.start_time)} –{" "}
                  {formatTime(activeSession.end_time)}
                </span>
                <span>
                  {activeSession.session_id
                    ? `Session #${activeSession.session_id}`
                    : "Session details"}
                </span>
                {activeSession.course_code && (
                  <span>
                    <strong>{activeSession.course_code}</strong>
                    {activeSession.course_name ? ` – ${activeSession.course_name}` : ""}
                  </span>
                )}
                {activeSession.semester && (
                  <span>Semester {activeSession.semester}</span>
                )}
                {activeSession.section && (
                  <span>Section {activeSession.section}</span>
                )}
                {activeSession.room && (
                  <span>Room {activeSession.room}</span>
                )}
              </div>

              {closeError && (
                <p className="attendance-error-text" role="alert">
                  {closeError}
                </p>
              )}

              {faceAttendanceError && !showFaceAttendance && (
                <p className="attendance-error-text" role="alert">
                  {faceAttendanceError}
                </p>
              )}

              <div className="attendance-live-grid">
                <div className="attendance-live-camera">
                  {showFaceAttendance ? (
                    <div className="attendance-camera-scanner-frame">
                      <video
                        ref={videoRef}
                        autoPlay
                        playsInline
                        muted
                        className="attendance-camera-video"
                      />
                      <canvas
                        ref={canvasRef}
                        className="attendance-camera-canvas"
                        style={{ display: "none" }}
                        aria-hidden="true"
                      />
                      <div className="attendance-scanner-viewfinder">
                        <div className="attendance-scanner-corner top-left" />
                        <div className="attendance-scanner-corner top-right" />
                        <div className="attendance-scanner-corner bottom-left" />
                        <div className="attendance-scanner-corner bottom-right" />
                        {autoScanActive && <div className="attendance-scanner-laser" />}
                      </div>

                      {currentChallenge && livenessState === "FOLLOW_INSTRUCTION" && (
                        <div className="attendance-liveness-instruction-badge">
                          <FontAwesomeIcon icon={faShieldHalved} />
                          <span>{currentChallenge.instruction}</span>
                        </div>
                      )}

                      <span className="attendance-live-badge">
                        <span /> LIVE SCANNER
                      </span>
                      <div
                        className={`attendance-scanner-status-toast ${
                          livenessState === "SPOOF_SUSPECTED"
                            ? "spoof"
                            : livenessState === "CHALLENGE_EXPIRED" || livenessState === "QUALITY_WARNING"
                            ? "warning"
                            : livenessState === "MODEL_UNAVAILABLE"
                            ? "danger"
                            : livenessState === "VERIFIED_SUCCESS"
                            ? "success"
                            : ""
                        }`}
                      >
                        <FontAwesomeIcon
                          icon={
                            recognizingFace ||
                            livenessState === "VERIFYING_IDENTITY" ||
                            livenessState === "PERFORMING_CHECK"
                              ? faSpinner
                              : livenessState === "SPOOF_SUSPECTED" ||
                                livenessState === "MODEL_UNAVAILABLE" ||
                                livenessState === "QUALITY_WARNING"
                              ? faTriangleExclamation
                              : livenessState === "VERIFIED_SUCCESS"
                              ? faCircleCheck
                              : faCircleInfo
                          }
                          spin={
                            recognizingFace ||
                            livenessState === "VERIFYING_IDENTITY" ||
                            livenessState === "PERFORMING_CHECK"
                          }
                        />
                        <span>{scanStatusMessage}</span>
                        {(livenessState === "SPOOF_SUSPECTED" ||
                          livenessState === "CHALLENGE_EXPIRED" ||
                          livenessState === "QUALITY_WARNING" ||
                          livenessState === "MODEL_UNAVAILABLE") && (
                          <button
                            type="button"
                            className="attendance-scanner-retry-btn"
                            onClick={handleRetryChallenge}
                          >
                            Retry
                          </button>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="attendance-camera-placeholder">
                      <FontAwesomeIcon icon={faCamera} />
                      <strong>Continuous Face Recognition</strong>
                      <span>
                        Start camera to automatically detect and mark attendance for enrolled students. No capture button required.
                      </span>
                      {(() => {
                        const sched = activeSession ? getClassScheduleStatus(activeSession.start_time, activeSession.end_time) : null;
                        const isInactiveWindow = activeSession && (activeSession.is_eligible_for_attendance === false || sched?.status === "UPCOMING" || sched?.status === "ENDED");
                        return (
                          <>
                            <button
                              type="button"
                              className={`attendance-primary-button ${isInactiveWindow ? "disabled-btn" : ""}`}
                              onClick={handleStartFaceAttendance}
                              disabled={closingSession || isInactiveWindow}
                              title={isInactiveWindow ? "Attendance is only allowed during scheduled class hours" : undefined}
                            >
                              <FontAwesomeIcon icon={faCamera} />
                              Start Live Attendance
                            </button>
                            {isInactiveWindow && (
                              <p className="attendance-warning-text" style={{ color: "#d97706", marginTop: "10px", fontSize: "0.85rem", display: "flex", alignItems: "center", gap: "6px" }}>
                                <FontAwesomeIcon icon={faCircleExclamation} />
                                {sched?.status === "UPCOMING"
                                  ? `Class scheduled for ${sched.formattedStart || activeSession.start_time}. Attendance cannot start before scheduled time.`
                                  : "Scheduled class window has ended. Attendance is closed."}
                              </p>
                            )}
                          </>
                        );
                      })()}
                    </div>
                  )}
                </div>

                <div className="attendance-recognition-panel">
                  <div className="attendance-scanner-header">
                    <h3>Live Recognition</h3>
                    {showFaceAttendance && (
                      <span className="attendance-scanner-status-pill">
                        <span className={`attendance-pulse-dot ${autoScanActive ? "active" : "paused"}`} />
                        {autoScanActive ? "Auto-Scanning" : "Paused"}
                      </span>
                    )}
                  </div>

                  {showFaceAttendance && lastRecognizedStudent ? (
                    <div className="attendance-recognized-card">
                      <div className="attendance-recognized-avatar">
                        {getInitials(lastRecognizedStudent.name || lastRecognizedStudent.student_name)}
                      </div>
                      <div className="attendance-recognized-info">
                        <strong>{lastRecognizedStudent.name || lastRecognizedStudent.student_name}</strong>
                        <span>Enrollment: {lastRecognizedStudent.enrollment_no}</span>
                        <div className="attendance-recognized-tags">
                          {lastRecognizedStudent.is_eligible === false ||
                          lastRecognizedStudent.status === "INELIGIBLE" ||
                          !lastRecognizedStudent.attendance_id ? (
                            <span className="attendance-tag rejected" style={{ background: "rgba(239, 68, 68, 0.15)", color: "#dc2626", borderColor: "#fca5a5" }}>
                              <FontAwesomeIcon icon={faCircleExclamation} />
                              Ineligible for Class
                            </span>
                          ) : (
                            <span className={`attendance-tag ${lastRecognizedStudent.is_new ? "new" : "existing"}`}>
                              <FontAwesomeIcon icon={faCircleCheck} />
                              {lastRecognizedStudent.is_new ? "Present Marked" : "Already Marked"}
                            </span>
                          )}
                          {lastRecognizedStudent.confidence_score && (
                            <span className="attendance-tag score">
                              {Math.round(lastRecognizedStudent.confidence_score * 100)}% Match
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="attendance-scanner-idle">
                      <div className="attendance-recognition-symbol">
                        <FontAwesomeIcon
                          icon={recognizingFace ? faSpinner : faUserCheck}
                          spin={recognizingFace}
                        />
                      </div>
                      <strong>
                        {recognizingFace
                          ? "Verifying identity…"
                          : showFaceAttendance && cameraReady
                            ? "Camera Active & Scanning"
                            : "Waiting for Camera"}
                      </strong>
                      <p>
                        {showFaceAttendance
                          ? scanStatusMessage
                          : "Activate camera to automatically scan and mark student attendance."}
                      </p>
                    </div>
                  )}

                  {displayedRecentDetections.length > 0 && (
                    <div className="attendance-recent-stream">
                      <div className="attendance-recent-title">Recent Recognitions</div>
                      <div className="attendance-recent-chips">
                        {displayedRecentDetections.map((item, idx) => {
                          const isIneligible =
                            item.is_eligible === false ||
                            item.status === "INELIGIBLE" ||
                            !item.attendance_id;
                          return (
                            <div
                              key={item.student_id || idx}
                              className={`attendance-recent-chip ${isIneligible ? "ineligible" : ""}`}
                              style={isIneligible ? { borderColor: "#fca5a5", background: "#fef2f2", color: "#991b1b" } : undefined}
                            >
                              <FontAwesomeIcon
                                icon={isIneligible ? faCircleExclamation : faCircleCheck}
                                style={{ color: isIneligible ? "#dc2626" : undefined }}
                              />
                              <span>
                                {item.name ||
                                  item.student_name ||
                                  getStudentName(
                                    students.find((s) =>
                                      isSameId(s.student_id, item.student_id)
                                    )
                                  ) ||
                                  `Student #${item.student_id}`}
                                {isIneligible ? " (Ineligible)" : ""}
                              </span>
                              <small>{isIneligible ? "Rejected" : formatTime(item.marked_at)}</small>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {showFaceAttendance && (
                    <div className="attendance-scanner-controls">
                      <button
                        type="button"
                        className="attendance-secondary-button"
                        onClick={() => setAutoScanActive((prev) => !prev)}
                      >
                        <FontAwesomeIcon icon={autoScanActive ? faPause : faPlay} />
                        {autoScanActive ? "Pause" : "Resume"}
                      </button>
                      <button
                        type="button"
                        className="attendance-primary-button danger"
                        onClick={handleCloseFaceAttendance}
                      >
                        <FontAwesomeIcon icon={faXmark} />
                        Stop Camera
                      </button>
                    </div>
                  )}

                  {faceAttendanceError && (
                    <p className="attendance-error-text" role="alert" style={{ marginTop: "10px" }}>
                      {faceAttendanceError}
                    </p>
                  )}
                </div>

                <div className="attendance-session-stats">
                  <h3>Session Stats</h3>
                  {[
                    {
                      label: "Total Recorded",
                      value: recordsLoading
                        ? "…"
                        : attendanceRecords.length,
                      icon: faUsers,
                      tone: "blue",
                    },
                    {
                      label: "Marked Present",
                      value: recordsLoading ? "…" : studentsPresent,
                      icon: faCircleCheck,
                      tone: "green",
                    },
                    {
                      label: "Marked Absent",
                      value: recordsLoading ? "…" : studentsAbsent,
                      icon: faCircleExclamation,
                      tone: "orange",
                    },
                    {
                      label: "Attendance Rate",
                      value: attendanceRate === null
                        ? "N/A"
                        : `${attendanceRate}%`,
                      icon: faChartLine,
                      tone: "purple",
                    },
                  ].map((item) => (
                    <div className="attendance-stat-row" key={item.label}>
                      <span className={`attendance-stat-icon ${item.tone}`}>
                        <FontAwesomeIcon icon={item.icon} />
                      </span>
                      <div>
                        <small>{item.label}</small>
                        <strong>{item.value}</strong>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="attendance-action-row">
                <button
                  type="button"
                  className="attendance-outline-button"
                  onClick={() => loadAttendanceRecords(selectedSession || activeSession)}
                  disabled={recordsLoading}
                >
                  <FontAwesomeIcon
                    icon={recordsLoading ? faSpinner : faRotateRight}
                    spin={recordsLoading}
                  />
                  Refresh Records
                </button>

                <button
                  type="button"
                  className="attendance-danger-button"
                  onClick={handleCloseAttendance}
                  disabled={closingSession}
                >
                  {closingSession ? (
                    <FontAwesomeIcon icon={faSpinner} spin />
                  ) : (
                    <FontAwesomeIcon icon={faXmark} />
                  )}
                  {closingSession ? "Ending Session…" : "End Session"}
                </button>
              </div>
            </>
          ) : (
            <div className="active-attendance-empty">
              <div className="active-attendance-icon">
                <FontAwesomeIcon icon={faBookOpen} />
              </div>
              <h3>No active attendance session</h3>
              <p>
                Start a session for one of your assigned course offerings to
                mark or recognize attendance.
              </p>
              <button
                type="button"
                className="attendance-primary-button"
                onClick={handleOpenStartModal}
                disabled={coursesLoading || courses.length === 0}
              >
                <FontAwesomeIcon icon={faCalendar} />
                Start Attendance
              </button>
            </div>
          )}
        </section>

        <section className="attendance-records-section">
          <div className="attendance-table-card">
            <div className="attendance-table-toolbar">
              <div className="attendance-tabs" role="tablist">
                <button
                  type="button"
                  role="tab"
                  aria-selected={activeTab === "attendance"}
                  className={activeTab === "attendance" ? "active" : ""}
                  onClick={() => setActiveTab("attendance")}
                >
                  Recent Attendance
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={activeTab === "history"}
                  className={activeTab === "history" ? "active" : ""}
                  onClick={() => setActiveTab("history")}
                >
                  Session History
                </button>
              </div>

              {activeTab === "attendance" && selectedSession && (
                <div className="attendance-search-wrapper">
                  <FontAwesomeIcon
                    icon={faMagnifyingGlass}
                    aria-hidden="true"
                  />
                  <input
                    type="search"
                    aria-label="Search students"
                    value={studentSearch}
                    onChange={(event) => setStudentSearch(event.target.value)}
                    placeholder="Search students…"
                  />
                </div>
              )}
            </div>

            {activeTab === "history" && (
              <>
                <div className="attendance-filters-card">
                  <div className="attendance-filter search-filter">
                    <label htmlFor="attendance-search">Search course</label>
                    <div className="attendance-search-wrapper">
                      <FontAwesomeIcon icon={faMagnifyingGlass} />
                      <input
                        id="attendance-search"
                        type="search"
                        value={searchTerm}
                        onChange={(event) => {
                          setSearchTerm(event.target.value);
                          setPage(1);
                        }}
                        placeholder="Search courses…"
                      />
                    </div>
                  </div>

                  <div className="attendance-filter">
                    <label htmlFor="attendance-class">Class</label>
                    <select
                      id="attendance-class"
                      value={selectedClass}
                      onChange={(event) => setSelectedClass(event.target.value)}
                    >
                      {classOptions.map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="attendance-filter">
                    <label htmlFor="attendance-date">Date</label>
                    <input
                      id="attendance-date"
                      type="date"
                      value={date}
                      onChange={(event) => setDate(event.target.value)}
                    />
                  </div>

                  <div className="attendance-filter">
                    <label htmlFor="attendance-status">Status</label>
                    <select
                      id="attendance-status"
                      value={status}
                      onChange={(event) => setStatus(event.target.value)}
                    >
                      <option value="All">All</option>
                      <option value="ACTIVE">Active</option>
                      <option value="CLOSED">Closed</option>
                    </select>
                  </div>

                  <button
                    type="button"
                    className="attendance-clear-button"
                    onClick={clearFilters}
                    disabled={!hasFilters}
                  >
                    <FontAwesomeIcon icon={faRotateRight} />
                    Clear
                  </button>
                </div>

                {loading ? (
                  <div className="attendance-empty-state">
                    <FontAwesomeIcon icon={faSpinner} spin />
                    <h3>Loading sessions…</h3>
                  </div>
                ) : filteredSessions.length === 0 ? (
                  <div className="attendance-empty-state">
                    <FontAwesomeIcon icon={faBookOpen} />
                    <h3>
                      {sessions.length
                        ? "No matching sessions"
                        : "No attendance sessions"}
                    </h3>
                    <p>
                      {sessions.length
                        ? "Try changing your search or filters."
                        : "Sessions will appear here after you start attendance."}
                    </p>
                  </div>
                ) : (
                  <div className="attendance-table-wrapper">
                    <table className="attendance-table">
                      <thead>
                        <tr>
                          <th>Course</th>
                          <th>Date</th>
                          <th>Start Time</th>
                          <th>End Time</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredSessions.map((session) => (
                          <tr
                            key={session.session_id}
                            tabIndex={0}
                            aria-selected={isSameId(
                              selectedSession?.session_id,
                              session.session_id
                            )}
                            className={
                              isSameId(
                                selectedSession?.session_id,
                                session.session_id
                              )
                                ? "selected"
                                : ""
                            }
                            onClick={() => handleSessionSelect(session)}
                            onKeyDown={(event) => {
                              if (
                                event.key === "Enter" ||
                                event.key === " "
                              ) {
                                event.preventDefault();
                                handleSessionSelect(session);
                              }
                            }}
                          >
                            <td>{getSessionClassName(session)}</td>
                            <td>{formatDate(session.session_date)}</td>
                            <td>{formatTime(session.start_time)}</td>
                            <td>{formatTime(session.end_time)}</td>
                            <td>
                              <span
                                className={`attendance-status ${
                                  session.status?.toLowerCase() || "unknown"
                                }`}
                              >
                                {session.status || "N/A"}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                <div className="attendance-list-footer">
                  <span>
                    Showing {filteredSessions.length} of {sessions.length}{" "}
                    sessions
                  </span>
                </div>
              </>
            )}

            {activeTab === "attendance" && (
              <>
                {!selectedSession ? (
                  <div className="attendance-empty-state">
                    <FontAwesomeIcon icon={faCalendar} />
                    <h3>Select an attendance session</h3>
                    <p>
                      Open Session History and select a session to view its
                      attendance records.
                    </p>
                    <button
                      type="button"
                      className="attendance-outline-button"
                      onClick={() => setActiveTab("history")}
                    >
                      View Session History
                    </button>
                  </div>
                ) : recordsLoading || studentsLoading ? (
                  <div className="attendance-empty-state">
                    <FontAwesomeIcon icon={faSpinner} spin />
                    <h3>
                      {recordsLoading
                        ? "Loading attendance records…"
                        : "Loading students…"}
                    </h3>
                  </div>
                ) : recordsError ? (
                  <div className="attendance-empty-state" role="alert">
                    <FontAwesomeIcon icon={faCircleExclamation} />
                    <h3>Unable to load attendance</h3>
                    <p>{recordsError}</p>
                    <button
                      type="button"
                      className="attendance-outline-button"
                      onClick={() => loadAttendanceRecords(selectedSession)}
                    >
                      <FontAwesomeIcon icon={faRotateRight} />
                      Retry
                    </button>
                  </div>
                ) : studentsError ? (
                  <div className="attendance-empty-state" role="alert">
                    <FontAwesomeIcon icon={faCircleExclamation} />
                    <h3>Student data unavailable</h3>
                    <p>{studentsError}</p>
                  </div>
                ) : sessionStudents.length === 0 ? (
                  <div className="attendance-empty-state">
                    <FontAwesomeIcon icon={faUsers} />
                    <h3>No enrolled students in this course</h3>
                    <p>
                      There are currently no active students enrolled in this course offering.
                    </p>
                  </div>
                ) : (
                  <>
                    <div className="attendance-table-wrapper">
                      <table className="attendance-table">
                        <thead>
                          <tr>
                            <th>#</th>
                            <th>Student Name</th>
                            <th>Enrollment No.</th>
                            <th>Status</th>
                            <th>Marked At</th>
                            <th>Method</th>
                          </tr>
                        </thead>
                        <tbody>
                          {displayStudents.map((student, index) => {
                            const record = attendanceRecordMap.get(
                              String(student.student_id)
                            );

                            return (
                              <tr key={student.student_id}>
                                <td>{(page - 1) * pageSize + index + 1}</td>
                                <td>
                                  <div className="attendance-student-cell">
                                    <span className="attendance-student-avatar">
                                      {getInitials(getStudentName(student))}
                                    </span>
                                    <span>{getStudentName(student)}</span>
                                  </div>
                                </td>
                                <td>{student.enrollment_no || "N/A"}</td>
                                <td>
                                  <span
                                    className={`attendance-status ${
                                      record?.status?.toLowerCase() || "unknown"
                                    }`}
                                  >
                                    {getAttendanceStatus(record)}
                                  </span>
                                </td>
                                <td>{formatTime(record?.marked_at)}</td>
                                <td>{record?.recognition_method || "N/A"}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>

                    <div className="attendance-list-footer">
                      <span>
                        Showing{" "}
                        {filteredStudents.length === 0
                          ? 0
                          : (page - 1) * pageSize + 1}
                        –
                        {Math.min(page * pageSize, filteredStudents.length)} of{" "}
                        {filteredStudents.length} students
                      </span>

                      <div className="attendance-pagination">
                        <button
                          type="button"
                          onClick={() => setPage((current) => current - 1)}
                          disabled={page <= 1}
                          aria-label="Previous page"
                        >
                          <FontAwesomeIcon icon={faArrowLeft} />
                        </button>
                        <span>
                          {page} / {totalPages}
                        </span>
                        <button
                          type="button"
                          onClick={() => setPage((current) => current + 1)}
                          disabled={page >= totalPages}
                          aria-label="Next page"
                        >
                          <FontAwesomeIcon icon={faArrowRight} />
                        </button>
                      </div>
                    </div>
                  </>
                )}
              </>
            )}
          </div>
        </section>

      {coursesError && (
        <section className="attendance-integration-notice" role="alert">
          <div className="attendance-notice-icon">
            <FontAwesomeIcon icon={faCircleExclamation} />
          </div>
          <div>
            <strong>Course data unavailable</strong>
            <p>{coursesError}</p>
          </div>
        </section>
      )}
    </main>

    <aside className="attendance-side-column">
      <section className="attendance-side-card">
        <h2>
          <FontAwesomeIcon icon={faBolt} />
          Quick Actions
        </h2>

        <button
          type="button"
          className="attendance-quick-action primary"
          onClick={handleOpenStartModal}
          disabled={
            coursesLoading ||
            courses.length === 0 ||
            Boolean(activeSession)
          }
        >
          <span className="attendance-quick-icon">
            <FontAwesomeIcon icon={faCamera} />
          </span>
          <span>
            <strong>Start Attendance</strong>
            <small>Begin a session for a course</small>
          </span>
        </button>

        <button
          type="button"
          className="attendance-quick-action"
          onClick={() => {
            const offeringParam = selectedSession?.offering_id || selectedOfferingId || "";
            navigate(offeringParam ? `/faculty/students?offering_id=${offeringParam}` : "/faculty/students");
          }}
        >
          <span className="attendance-quick-icon">
            <FontAwesomeIcon icon={faUsers} />
          </span>
          <span>
            <strong>View Students</strong>
            <small>View available course attendance</small>
          </span>
        </button>

        <button
          type="button"
          className="attendance-quick-action"
          onClick={() => {
            const offeringParam = selectedSession?.offering_id || selectedOfferingId || "";
            navigate(offeringParam ? `/faculty/reports?offering_id=${offeringParam}` : "/faculty/reports");
          }}
        >
          <span className="attendance-quick-icon">
            <FontAwesomeIcon icon={faFileLines} />
          </span>
          <span>
            <strong>Attendance Reports</strong>
            <small>View reports & analytics</small>
          </span>
        </button>
      </section>

      <section className="attendance-side-card">
        <div className="attendance-side-heading">
          <h2>
            <FontAwesomeIcon icon={faCalendar} />
            Today's Schedule
          </h2>
          <button
            type="button"
            onClick={() => setScheduleExpanded((current) => !current)}
          >
            {scheduleExpanded ? "Collapse" : "Expand"}
          </button>
        </div>

        {scheduleExpanded && (
          <div className="attendance-schedule-pending">
            {timetableLoading ? (
              <p>Loading timetable...</p>
            ) : timetableError ? (
              <div className="attendance-schedule-pending">
                <FontAwesomeIcon icon={faCircleExclamation} />
                <p>{timetableError}</p>
              </div>
            ) : (
              (() => {
                const dayNames = [
                  "Sunday",
                  "Monday",
                  "Tuesday",
                  "Wednesday",
                  "Thursday",
                  "Friday",
                  "Saturday",
                ];
                const today = dayNames[new Date().getDay()];
                const todayEntries = timetableEntries.filter(
                  (entry) =>
                    String(entry.day_of_week || "").trim().toLowerCase() ===
                    today.toLowerCase()
                );
                if (todayEntries.length === 0) {
                  return <p>No timetable entries found for {today}.</p>;
                }
                return (
                  <div className="attendance-schedule-list">
                    {todayEntries.map((entry) => (
                      <div
                        className="attendance-schedule-item clickable"
                        key={entry.timetable_entry_id}
                        role="button"
                        tabIndex={0}
                        title="Click to start attendance for this class"
                        onClick={() => {
                          if (!activeSession) {
                            handleOpenStartModal(entry);
                          }
                        }}
                        onKeyDown={(e) => {
                          if ((e.key === "Enter" || e.key === " ") && !activeSession) {
                            handleOpenStartModal(entry);
                          }
                        }}

                      >
                        <strong>
                          {entry.course_code} - {entry.course_name}
                        </strong>
                        <p>
                          {formatTime(entry.start_time)} -{" "}
                          {formatTime(entry.end_time)}
                        </p>
                        <p>
                          Section: {entry.section || "N/A"} · Room:{" "}
                          {entry.room || "N/A"}
                        </p>
                      </div>
                    ))}
                  </div>
                );
              })()
            )}
          </div>
        )}
      </section>

      <section className="attendance-side-card attendance-help-card">
        <h2>
          <FontAwesomeIcon icon={faCircleInfo} />
          System Status
        </h2>
        <p>
          {systemHealth.loading
            ? "Verifying backend and database connectivity…"
            : systemHealth.connected
              ? "Live database connected. All attendance records, facial recognitions, and sessions are persisted to MySQL in real time."
              : `Connection error: ${systemHealth.message}. Check that the backend server is running.`}
        </p>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap", marginTop: "8px" }}>
          <span
            className={`attendance-status-badge ${
              systemHealth.loading
                ? "pending"
                : systemHealth.connected
                  ? "live"
                  : "error"
            }`}
          >
            <FontAwesomeIcon
              icon={
                systemHealth.loading
                  ? faSpinner
                  : systemHealth.connected
                    ? faCircleCheck
                    : faCircleExclamation
              }
              spin={systemHealth.loading}
            />{" "}
            {systemHealth.loading
              ? "Checking…"
              : systemHealth.connected
                ? "Live Backend Connected"
                : "Backend Offline"}
          </span>
          {!systemHealth.connected && !systemHealth.loading && (
            <button
              type="button"
              className="attendance-outline-button"
              style={{ padding: "3px 8px", fontSize: "11px" }}
              onClick={checkSystemHealth}
              title="Retry connecting to backend"
            >
              <FontAwesomeIcon icon={faRotateRight} /> Retry
            </button>
          )}
        </div>
      </section>
    </aside>

    {showStartModal && (() => {
      const dayNames = [
        "Sunday",
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
      ];
      const today = dayNames[new Date().getDay()];
      const selectedOffering = courses.find((c) => String(c.offering_id) === String(selectedOfferingId));
      const availableSlots = timetableEntries.filter(
        (t) =>
          String(t.offering_id) === String(selectedOfferingId) &&
          String(t.day_of_week || "").trim().toLowerCase() === today.toLowerCase()
      );
      const allOfferingSlots = timetableEntries.filter(
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
        ? String(currentSlot.day_of_week || "").trim().toLowerCase() === today.toLowerCase()
        : false;
      const isSlotEnded = isSlotToday && slotStatus?.status === "ENDED";
      const isSlotUpcoming = isSlotToday && slotStatus?.status === "UPCOMING";

      return (
        <div
          className="attendance-modal-backdrop"
          role="presentation"
          onMouseDown={(event) => {
            if (
              event.target === event.currentTarget &&
              !startingSession
            ) {
              setShowStartModal(false);
            }
          }}
        >
          <div
            className="attendance-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="start-attendance-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="attendance-modal-header">
              <div>
                <span className="attendance-eyebrow">ATTENDANCE</span>
                <h2 id="start-attendance-title">Start Attendance</h2>
              </div>
              <button
                type="button"
                className="attendance-modal-close"
                onClick={() => setShowStartModal(false)}
                disabled={startingSession}
                aria-label="Close"
              >
                <FontAwesomeIcon icon={faXmark} />
              </button>
            </div>

            <div className="attendance-modal-body">
              <div className="attendance-form-group">
                <label htmlFor="start-class">Course Offering</label>
                <select
                  id="start-class"
                  value={selectedOfferingId}
                  onChange={(event) =>
                    handleModalOfferingChange(event.target.value)
                  }
                  disabled={
                    coursesLoading || courses.length === 0 || startingSession
                  }
                >
                  {courses.length === 0 ? (
                    <option value="">No course offerings available</option>
                  ) : (
                    courses.map((course) => (
                      <option
                        key={course.offering_id}
                        value={course.offering_id}
                      >
                        {getCourseLabel(course)}
                        {course.section ? ` · Section ${course.section}` : ""}
                        {course.semester ? ` (Sem ${course.semester})` : ""}
                      </option>
                    ))
                  )}
                </select>
              </div>

              {displaySlots.length > 0 && (
                <div className="attendance-form-group">
                  <label htmlFor="start-slot">Scheduled Timetable Slot</label>
                  <select
                    id="start-slot"
                    value={selectedTimetableEntryId || (currentSlot ? String(currentSlot.timetable_entry_id) : "")}
                    onChange={(event) => {
                      setSelectedTimetableEntryId(event.target.value);
                      setStartError("");
                    }}
                    disabled={startingSession}
                  >
                    {displaySlots.map((slot) => {
                      const st = getClassScheduleStatus(slot.start_time, slot.end_time, slot.day_of_week);
                      return (
                        <option
                          key={slot.timetable_entry_id}
                          value={slot.timetable_entry_id}
                        >
                          {slot.day_of_week} {formatTime(slot.start_time)} – {formatTime(slot.end_time)}
                          {slot.room ? ` · Room ${slot.room}` : ""} — [{st.label}]
                        </option>
                      );
                    })}
                  </select>
                </div>
              )}

              {currentSlot && (
                <div
                  style={{
                    background: "#f8fafc",
                    border: "1px solid #e2e8f0",
                    borderRadius: "8px",
                    padding: "12px 14px",
                    marginBottom: "12px",
                    fontSize: "12.5px",
                    color: "#334155",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                    <strong style={{ fontSize: "13px", color: "#0f172a" }}>Scheduled Class Details</strong>
                    <span
                      style={{
                        fontSize: "11px",
                        fontWeight: "700",
                        padding: "2px 8px",
                        borderRadius: "6px",
                        background: slotStatus?.status === "ACTIVE" ? "#ecfdf5" : slotStatus?.status === "UPCOMING" ? "#fffbeb" : "#f1f5f9",
                        color: slotStatus?.status === "ACTIVE" ? "#059669" : slotStatus?.status === "UPCOMING" ? "#d97706" : "#64748b",
                      }}
                    >
                      {slotStatus?.label || "SCHEDULED"}
                    </span>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px" }}>
                    <div><span style={{ color: "#64748b" }}>Date:</span> {currentSlot.day_of_week} {isSlotToday ? `(${today})` : "(Scheduled)"}</div>
                    <div><span style={{ color: "#64748b" }}>Section:</span> {selectedOffering?.section || "N/A"}</div>
                    <div><span style={{ color: "#64748b" }}>Time:</span> {formatTime(currentSlot.start_time)} – {formatTime(currentSlot.end_time)}</div>
                    <div><span style={{ color: "#64748b" }}>Room:</span> {currentSlot.room || selectedOffering?.room || "Not assigned"}</div>
                  </div>
                </div>
              )}

              {!isSlotToday && (
                <div className="attendance-session-pending" role="alert" style={{ background: "#eff6ff", borderColor: "#bfdbfe", color: "#1e40af" }}>
                  <div className="attendance-pending-dot">
                    <FontAwesomeIcon icon={faClock} style={{ color: "#2563eb" }} />
                  </div>
                  <div>
                    <strong>Scheduled for {currentSlot.day_of_week}</strong>
                    <p>Cannot start attendance session today: this slot is scheduled for {currentSlot.day_of_week}. Attendance sessions can only be started during the scheduled class hours.</p>
                  </div>
                </div>
              )}

              {isSlotEnded && (
                <div className="attendance-session-pending" role="alert" style={{ background: "#fef2f2", borderColor: "#fecaca", color: "#991b1b" }}>
                  <div className="attendance-pending-dot">
                    <FontAwesomeIcon icon={faCircleExclamation} style={{ color: "#dc2626" }} />
                  </div>
                  <div>
                    <strong>Scheduled window ended</strong>
                    <p>Cannot start attendance after the scheduled class window has ended ({formatTime(currentSlot.end_time)}).</p>
                  </div>
                </div>
              )}

              {isSlotUpcoming && (
                <div className="attendance-session-pending" role="alert" style={{ background: "#fffbeb", borderColor: "#fde68a", color: "#92400e" }}>
                  <div className="attendance-pending-dot">
                    <FontAwesomeIcon icon={faClock} style={{ color: "#d97706" }} />
                  </div>
                  <div>
                    <strong>Upcoming class slot</strong>
                    <p>Cannot start attendance before the scheduled start time ({formatTime(currentSlot.start_time)}).</p>
                  </div>
                </div>
              )}

              {startError && (
                <div className="attendance-session-pending" role="alert">
                  <div className="attendance-pending-dot">
                    <FontAwesomeIcon icon={faCircleExclamation} />
                  </div>
                  <div>
                    <strong>Unable to start session</strong>
                    <p>{startError}</p>
                  </div>
                </div>
              )}
            </div>

            <div className="attendance-modal-footer">
              <button
                type="button"
                className="attendance-secondary-button"
                onClick={() => setShowStartModal(false)}
                disabled={startingSession}
              >
                <FontAwesomeIcon icon={faXmark} />
                Cancel
              </button>
              <button
                type="button"
                className="attendance-primary-button"
                onClick={handleStartAttendance}
                disabled={
                  startingSession ||
                  !selectedOfferingId ||
                  courses.length === 0 ||
                  isSlotEnded ||
                  isSlotUpcoming ||
                  !isSlotToday
                }
              >
                {startingSession ? (
                  <>
                    <FontAwesomeIcon icon={faSpinner} spin />
                    Starting…
                  </>
                ) : (
                  <>
                    <FontAwesomeIcon icon={faCalendar} />
                    Start Attendance
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      );
    })()}

  </div>
  );
}

export default Attendance;
