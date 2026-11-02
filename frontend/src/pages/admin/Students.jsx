import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  faBookOpen,
  faBuilding,
  faCalendarDays,
  faCamera,
  faCheck,
  faCircleExclamation,
  faCircleInfo,
  faEnvelope,
  faLocationDot,
  faMagnifyingGlass,
  faPhone,
  faPlus,
  faRotateRight,
  faSchool,
  faSpinner,
  faUser,
  faUserCheck,
  faUserGraduate,
  faUsers,
  faUserXmark,
  faXmark,
} from "@fortawesome/free-solid-svg-icons";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Eye, Pencil, Trash2 } from "lucide-react";

import {
  createAdminStudent,
  deleteAdminStudent,
  getAdminBatches,
  getAdminDepartments,
  getAdminStudents,
  getAdminStudentsFilterOptions,
  getAdminStudentsSummary,
  getUsers,
  updateAdminStudent,
} from "../../services/adminService";

import { enrollStudentFace } from "../../services/faceService";
import LiveFaceCapture from "../../components/LiveFaceCapture";
import RemoveFaceModal from "../../components/RemoveFaceModal";

import "./Student.css";

function getInitials(name) {
  if (!name) return "ST";
  return name
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function getAvatarColor(name) {
  const colors = [
    { bg: "#dbeafe", text: "#1e40af" },
    { bg: "#dcfce7", text: "#166534" },
    { bg: "#fef3c7", text: "#92400e" },
    { bg: "#ede9fe", text: "#5b21b6" },
    { bg: "#fee2e2", text: "#991b1b" },
    { bg: "#ccfbf1", text: "#115e59" },
    { bg: "#fae8ff", text: "#86198f" },
  ];
  if (!name) return colors[0];
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
}

const faceErrorMessages = {
  invalid_image:
    "The captured image is invalid. Please capture another image.",
  no_face:
    "No face was detected. Please position the student clearly inside the camera frame.",
  multiple_faces:
    "Multiple faces were detected. Make sure exactly one face is visible.",
  encoding_failed:
    "Face processing failed. Please capture the face again.",
  invalid_encoding:
    "The generated face data was invalid. Please try again.",
};

function Students() {
  // =========================================================
  // DATA STATE
  // =========================================================
  const [students, setStudents] = useState([]);
  const [summary, setSummary] = useState(null);
  const [studentUsers, setStudentUsers] = useState([]);
  const [departmentOptions, setDepartmentOptions] = useState([]);
  const [batchOptions, setBatchOptions] = useState([]);
  const [dbFilterOptions, setDbFilterOptions] = useState(null);

  const [loading, setLoading] = useState(true);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [error, setError] = useState("");
  const [summaryError, setSummaryError] = useState("");
  const [departmentsLoading, setDepartmentsLoading] = useState(false);
  const [batchesLoading, setBatchesLoading] = useState(false);

  // Selected student for right details panel
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [detailsTab, setDetailsTab] = useState("profile"); // profile, academic, attendance, face


  // Filter state
  const [filterDepartment, setFilterDepartment] = useState("All");
  const [filterSemester, setFilterSemester] = useState("All");
  const [filterSection, setFilterSection] = useState("All");
  const [filterBatch, setFilterBatch] = useState("All");
  const [filterStatus, setFilterStatus] = useState("All");
  const [searchInput, setSearchInput] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  // Modals
  const [showCreateStudent, setShowCreateStudent] = useState(false);
  const [createStudentLoading, setCreateStudentLoading] = useState(false);
  const [createStudentError, setCreateStudentError] = useState("");
  const [createStudentForm, setCreateStudentForm] = useState({
    user_id: "",
    enrollment_no: "",
    semester: "",
    section: "",
    academic_year: "",
    department_id: "",
    batch_id: "",
  });

  const [editingStudent, setEditingStudent] = useState(null);
  const [editStudentLoading, setEditStudentLoading] = useState(false);
  const [editStudentError, setEditStudentError] = useState("");
  const [editStudentSuccess, setEditStudentSuccess] = useState("");
  const [editStudentForm, setEditStudentForm] = useState({
    enrollment_no: "",
    semester: "",
    section: "",
    academic_year: "",
    department_id: "",
    batch_id: "",
  });

  const [deletingStudentId, setDeletingStudentId] = useState(null);
  const [deleteFeedback, setDeleteFeedback] = useState(null);

  // Face registration modal
  const [showFaceRegistrationView, setShowFaceRegistrationView] = useState(false);
  const [faceEnrollmentStudent, setFaceEnrollmentStudent] = useState(null);
  const [faceCaptureBlob, setFaceCaptureBlob] = useState(null);
  const [faceEnrollmentLoading, setFaceEnrollmentLoading] = useState(false);
  const [faceEnrollmentError, setFaceEnrollmentError] = useState("");
  const [faceEnrollmentSuccess, setFaceEnrollmentSuccess] = useState("");
  const [studentToRemoveFace, setStudentToRemoveFace] = useState(null);

  // =========================================================
  // FETCH SUMMARY
  // =========================================================
  const fetchSummary = useCallback(async () => {
    setSummaryLoading(true);
    setSummaryError("");
    try {
      const response = await getAdminStudentsSummary();
      if (response?.success && response.data) {
        setSummary(response.data);
      } else {
        throw new Error(response?.message || "Failed to load summary statistics.");
      }
    } catch (err) {
      setSummaryError(err?.response?.data?.message || err?.message || "Summary unavailable");
    } finally {
      setSummaryLoading(false);
    }
  }, []);

  // =========================================================
  // FETCH STUDENTS
  // =========================================================
  const fetchStudents = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [studentsRes, usersRes] = await Promise.all([
        getAdminStudents(),
        getUsers(),
      ]);

      if (!studentsRes?.success) {
        throw new Error(studentsRes?.message || "Failed to load students.");
      }

      const studentList = Array.isArray(studentsRes.data) ? studentsRes.data : [];
      setStudents(studentList);

      // Preserve selection only if user already explicitly clicked to view a student; do NOT auto-select by default
      setSelectedStudent((prev) => {
        if (prev) {
          const updated = studentList.find((s) => s.student_id === prev.student_id);
          return updated || null;
        }
        return null;
      });

      // Filter available users for student creation
      const userList = Array.isArray(usersRes?.data) ? usersRes.data : [];
      const existingUserIds = new Set(
        studentList
          .map((s) => s?.user_id)
          .filter(Boolean)
          .map((id) => String(id))
      );

      const available = userList.filter(
        (u) =>
          String(u?.role || "").toUpperCase() === "STUDENT" &&
          !existingUserIds.has(String(u?.user_id))
      );
      setStudentUsers(available);
    } catch (err) {
      setError(
        err?.response?.data?.message || err?.message || "Failed to load student data."
      );
      setStudents([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Clean up any residual URL query parameters (like ?view=face-registration) so refreshing NEVER auto-opens modals
  useEffect(() => {
    if (window.location.search) {
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  // Initial load
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      if (!cancelled) {
        await Promise.all([fetchSummary(), fetchStudents()]);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [fetchSummary, fetchStudents]);

  // Load departments
  useEffect(() => {
    let cancelled = false;
    const loadDepts = async () => {
      setDepartmentsLoading(true);
      try {
        const res = await getAdminDepartments();
        if (res?.success && Array.isArray(res.data) && !cancelled) {
          setDepartmentOptions(res.data);
        }
      } catch (err) {
        console.error("Departments error:", err);
      } finally {
        if (!cancelled) setDepartmentsLoading(false);
      }
    };
    loadDepts();
    return () => {
      cancelled = true;
    };
  }, []);

  // Load batches
  useEffect(() => {
    let cancelled = false;
    const loadBatches = async () => {
      setBatchesLoading(true);
      try {
        const res = await getAdminBatches();
        if (res?.success && Array.isArray(res.data) && !cancelled) {
          setBatchOptions(res.data.filter((b) => b.is_active === true));
        }
      } catch (err) {
        console.error("Batches error:", err);
      } finally {
        if (!cancelled) setBatchesLoading(false);
      }
    };
    loadBatches();
    return () => {
      cancelled = true;
    };
  }, []);

  // Dynamic Semester & Section options from backend and database
  const semesterOptions = useMemo(() => {
    if (Array.isArray(dbFilterOptions?.semesters) && dbFilterOptions.semesters.length > 0) {
      return dbFilterOptions.semesters;
    }
    if (Array.isArray(summary?.semesters) && summary.semesters.length > 0) {
      return summary.semesters;
    }
    const sems = new Set();
    students.forEach((s) => {
      if (s.semester != null) sems.add(Number(s.semester));
    });
    return Array.from(sems).sort((a, b) => a - b);
  }, [dbFilterOptions, summary, students]);

  const sectionOptions = useMemo(() => {
    if (Array.isArray(dbFilterOptions?.sections) && dbFilterOptions.sections.length > 0) {
      return dbFilterOptions.sections;
    }
    if (Array.isArray(summary?.sections) && summary.sections.length > 0) {
      return summary.sections;
    }
    const secs = new Set();
    students.forEach((s) => {
      if (s.section) secs.add(String(s.section).trim());
    });
    return Array.from(secs).sort();
  }, [dbFilterOptions, summary, students]);

  // Load database filter options on mount
  const fetchFilterOptions = useCallback(async () => {
    try {
      const res = await getAdminStudentsFilterOptions();
      if (res?.success && res.data) {
        setDbFilterOptions(res.data);
      }
    } catch (err) {
      console.error("Filter options error:", err);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;

    const loadFilterOptions = async () => {
      try {
        const res = await getAdminStudentsFilterOptions();
        if (isMounted && res?.success && res.data) {
          setDbFilterOptions(res.data);
        }
      } catch (err) {
        if (isMounted) {
          console.error("Filter options error:", err);
        }
      }
    };

    void loadFilterOptions();

    return () => {
      isMounted = false;
    };
  }, []);


  // =========================================================
  // FILTERING & PAGINATION
  // =========================================================
  const filteredStudents = useMemo(() => {
    const search = appliedSearch.trim().toLowerCase();

    return students.filter((student) => {
      const name = String(student?.name || "").toLowerCase();
      const email = String(student?.email || "").toLowerCase();
      const rollNo = String(student?.roll_no || student?.enrollment_no || "").toLowerCase();
      const enrollmentNo = String(student?.enrollment_no || "").toLowerCase();
      const deptName = String(student?.department_name || "").toLowerCase();
      const deptCode = String(student?.department_code || "").toLowerCase();

      const matchesSearch =
        !search ||
        name.includes(search) ||
        email.includes(search) ||
        rollNo.includes(search) ||
        enrollmentNo.includes(search) ||
        deptName.includes(search) ||
        deptCode.includes(search);

      const matchesDept =
        filterDepartment === "All" ||
        String(student?.department_id) === String(filterDepartment) ||
        student?.department_name === filterDepartment;

      const matchesSem =
        filterSemester === "All" ||
        String(student?.semester) === String(filterSemester);

      const matchesSec =
        filterSection === "All" ||
        String(student?.section || "").toUpperCase() === filterSection.toUpperCase();

      const matchesStatus =
        filterStatus === "All" ||
        (filterStatus === "Active" && student?.is_active === true) ||
        (filterStatus === "Inactive" && student?.is_active === false);

      const matchesBatch =
        filterBatch === "All" ||
        String(student?.batch_id) === String(filterBatch) ||
        String(student?.batch_year) === String(filterBatch) ||
        String(student?.batch_name) === String(filterBatch);

      return matchesSearch && matchesDept && matchesSem && matchesSec && matchesStatus && matchesBatch;
    });
  }, [students, appliedSearch, filterDepartment, filterSemester, filterSection, filterStatus, filterBatch]);

  const totalPages = Math.max(1, Math.ceil(filteredStudents.length / pageSize));
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const paginatedStudents = useMemo(() => {
    const start = (safeCurrentPage - 1) * pageSize;
    return filteredStudents.slice(start, start + pageSize);
  }, [filteredStudents, safeCurrentPage, pageSize]);

  function handleSearchSubmit(e) {
    e.preventDefault();
    setAppliedSearch(searchInput);
    setCurrentPage(1);
  }

  function handleResetFilters() {
    setFilterDepartment("All");
    setFilterSemester("All");
    setFilterSection("All");
    setFilterBatch("All");
    setFilterStatus("All");
    setSearchInput("");
    setAppliedSearch("");
    setCurrentPage(1);
  }


  // =========================================================
  // ACTIONS: ADD STUDENT
  // =========================================================
  function handleOpenCreateStudent() {
    setCreateStudentError("");
    setCreateStudentForm({
      user_id: "",
      enrollment_no: "",
      semester: "",
      section: "",
      academic_year:
        dbFilterOptions?.current_academic_year ||
        new Date().getFullYear() + "-" + (new Date().getFullYear() + 1),
      department_id: "",
      batch_id: "",
    });
    setShowCreateStudent(true);
  }

  function handleCloseCreateStudent() {
    if (createStudentLoading) return;
    setShowCreateStudent(false);
    setCreateStudentError("");
  }

  function handleCreateStudentChange(e) {
    const { name, value } = e.target;
    setCreateStudentForm((prev) => ({ ...prev, [name]: value }));
  }

  async function handleCreateStudentSubmit(e) {
    e.preventDefault();
    setCreateStudentError("");

    const userId = Number(createStudentForm.user_id);
    const departmentId = Number(createStudentForm.department_id);
    const enrollmentNo = String(createStudentForm.enrollment_no || "").trim();
    const academicYear = String(createStudentForm.academic_year || "").trim();
    const semesterRaw = String(createStudentForm.semester || "").trim();
    const section = String(createStudentForm.section || "").trim();

    if (!userId || !departmentId || !enrollmentNo || !academicYear || !semesterRaw || !section) {
      setCreateStudentError("Please fill in all required fields.");
      return;
    }

    const semester = Number(semesterRaw);
    if (!/^\d+$/.test(semesterRaw) || !Number.isInteger(semester) || semester < 1 || semester > 8) {
      setCreateStudentError("Semester must be a valid number between 1 and 8.");
      return;
    }

    if (section.length > 20) {
      setCreateStudentError("Section must not exceed 20 characters.");
      return;
    }

    const payload = {
      user_id: userId,
      enrollment_no: enrollmentNo,
      semester,
      section,
      academic_year: academicYear,
      department_id: departmentId,
      batch_id: createStudentForm.batch_id ? Number(createStudentForm.batch_id) : null,
    };

    setCreateStudentLoading(true);
    try {
      const res = await createAdminStudent(payload);
      if (!res?.success) {
        throw new Error(res?.message || "Failed to create student.");
      }
      setShowCreateStudent(false);
      await Promise.all([fetchStudents(), fetchSummary(), fetchFilterOptions()]);
    } catch (err) {
      setCreateStudentError(
        err?.response?.data?.message || err?.message || "Failed to create student."
      );
    } finally {
      setCreateStudentLoading(false);
    }
  }

  // =========================================================
  // ACTIONS: EDIT STUDENT
  // =========================================================
  function handleOpenEditStudent(student) {
    setEditStudentError("");
    setEditStudentSuccess("");
    setEditStudentForm({
      enrollment_no: student.enrollment_no || student.roll_no || "",
      semester: String(student.semester ?? ""),
      section: student.section || "",
      academic_year: student.academic_year || "",
      department_id: String(student.department_id || ""),
      batch_id: String(student.batch_id || ""),
    });
    setEditingStudent(student);
  }

  function handleCloseEditStudent() {
    if (editStudentLoading) return;
    setEditingStudent(null);
    setEditStudentError("");
    setEditStudentSuccess("");
  }

  function handleEditStudentChange(e) {
    const { name, value } = e.target;
    setEditStudentForm((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSaveStudent(e) {
    e.preventDefault();
    if (!editingStudent) return;

    const semester = Number(editStudentForm.semester);
    const departmentId = Number(editStudentForm.department_id);

    if (!editStudentForm.enrollment_no.trim() || !semester || !departmentId) {
      setEditStudentError("Roll number, semester, and department are required.");
      return;
    }

    setEditStudentLoading(true);
    setEditStudentError("");
    try {
      const res = await updateAdminStudent(editingStudent.student_id, {
        enrollment_no: editStudentForm.enrollment_no.trim(),
        semester,
        section: editStudentForm.section.trim(),
        academic_year: editStudentForm.academic_year.trim(),
        department_id: departmentId,
        batch_id: editStudentForm.batch_id ? Number(editStudentForm.batch_id) : null,
      });

      if (!res?.success) {
        throw new Error(res?.message || "Unable to update student.");
      }

      setEditingStudent(null);
      await Promise.all([fetchStudents(), fetchSummary()]);
    } catch (err) {
      setEditStudentError(
        err?.response?.data?.message || err?.message || "Failed to update student."
      );
    } finally {
      setEditStudentLoading(false);
    }
  }

  // =========================================================
  // ACTIONS: DELETE STUDENT
  // =========================================================
  async function handleDeleteStudent(student) {
    const confirmed = window.confirm(
      `Are you sure you want to delete ${student.name || "this student"}? This action cannot be undone.`
    );
    if (!confirmed) return;

    setDeletingStudentId(student.student_id);
    setDeleteFeedback(null);
    try {
      const res = await deleteAdminStudent(student.student_id);
      if (!res?.success) {
        throw new Error(res?.message || "Failed to delete student.");
      }
      setDeleteFeedback({ type: "success", message: res.message || "Student deleted successfully." });
      await Promise.all([fetchStudents(), fetchSummary()]);
    } catch (err) {
      setDeleteFeedback({
        type: "error",
        message: err?.response?.data?.message || err?.message || "Unable to delete student.",
      });
    } finally {
      setDeletingStudentId(null);
    }
  }

  // =========================================================
  // ACTIONS: FACE REGISTRATION
  // =========================================================
  function handleOpenFaceEnrollment(student) {
    setFaceEnrollmentStudent(student);
    setFaceCaptureBlob(null);
    setFaceEnrollmentError("");
    setFaceEnrollmentSuccess("");
    setShowFaceRegistrationView(true);
  }

  function handleFaceCapture(blob) {
    setFaceEnrollmentError("");
    setFaceEnrollmentSuccess("");
    if (!blob) {
      setFaceCaptureBlob(null);
      setFaceEnrollmentError("Unable to capture student face. Please try again.");
      return;
    }
    setFaceCaptureBlob(blob);
  }

  async function handleEnrollFaceSubmit(e) {
    e.preventDefault();
    if (!faceEnrollmentStudent?.student_id || !faceCaptureBlob) {
      setFaceEnrollmentError("Please capture student face before saving.");
      return;
    }

    setFaceEnrollmentLoading(true);
    setFaceEnrollmentError("");
    setFaceEnrollmentSuccess("");
    try {
      const res = await enrollStudentFace(faceEnrollmentStudent.student_id, faceCaptureBlob);
      if (!res?.success) {
        throw new Error(
          faceErrorMessages[res?.status] || res?.message || "Face enrollment failed."
        );
      }
      setFaceEnrollmentSuccess(res.message || "Face registered successfully!");
      await Promise.all([fetchStudents(), fetchSummary()]);
    } catch (err) {
      const backendStatus = err?.response?.data?.status || err?.status;
      setFaceEnrollmentError(
        faceErrorMessages[backendStatus] ||
          err?.response?.data?.message ||
          err?.message ||
          "Face enrollment failed."
      );
    } finally {
      setFaceEnrollmentLoading(false);
    }
  }

  // Calculate authoritative display numbers
  const totalCount = summary?.total_students ?? students.length;
  const activeCount = summary?.active_students ?? students.filter((s) => s.is_active).length;
  const inactiveCount = summary?.inactive_students ?? students.filter((s) => !s.is_active).length;
  const faceRegisteredCount =
    summary?.face_registered ?? students.filter((s) => s.face_registered).length;
  const faceRegisteredPct =
    summary?.face_registered_percentage ??
    (totalCount > 0 ? Math.round((faceRegisteredCount / totalCount) * 1000) / 10 : 0);

  return (
    <div className="student-management-page">
      {/* =====================================================
          HEADER BANNER
      ====================================================== */}
      <section className="student-banner-card">
        <div className="student-banner-bg" aria-hidden="true">
          <img
            src="/image/student-management-banner.png"
            alt=""
            className="student-banner-img"
            onError={(e) => {
              e.currentTarget.style.display = "none";
            }}
          />
        </div>

        <div className="student-banner-left">
          <div className="student-banner-icon-box">
            <FontAwesomeIcon icon={faUserGraduate} />
          </div>

          <div className="student-banner-titles">
            <h1>Student Management</h1>
            <p>
              Manage student profiles, enrollment, face registration and academic details.
            </p>
          </div>
        </div>

        <div className="student-banner-badge">
          <strong>Today&apos;s Students Tomorrow&apos;s Innovators</strong>
          <span>A smarter campus with smarter attendance.</span>
        </div>
      </section>

      {/* =====================================================
          SUMMARY CARDS
      ====================================================== */}
      <section className="student-summary-grid">
        {/* Card 1: Total Students */}
        <div className="student-stat-card card-total">
          <img
            src="/image/student-total-card-bg.png"
            alt=""
            className="student-stat-card-bg"
            onError={(e) => {
              e.currentTarget.style.display = "none";
            }}
          />
          <div className="student-stat-card-content">
            <div className="student-stat-icon-wrapper icon-blue">
              <FontAwesomeIcon icon={faUsers} />
            </div>
            <div className="student-stat-data">
              <span className="student-stat-label">Total Students</span>
              <strong className="student-stat-value">
                {summaryLoading ? "..." : totalCount}
              </strong>
              <span className="student-stat-subtext">Active students</span>
            </div>
          </div>
        </div>

        {/* Card 2: Active Students */}
        <div className="student-stat-card card-active">
          <img
            src="/image/student-active-card-bg.png"
            alt=""
            className="student-stat-card-bg"
            onError={(e) => {
              e.currentTarget.style.display = "none";
            }}
          />
          <div className="student-stat-card-content">
            <div className="student-stat-icon-wrapper icon-green">
              <FontAwesomeIcon icon={faUserCheck} />
            </div>
            <div className="student-stat-data">
              <span className="student-stat-label">Active Students</span>
              <strong className="student-stat-value">
                {summaryLoading ? "..." : activeCount}
              </strong>
              <span className="student-stat-subtext">Currently enrolled</span>
            </div>
          </div>
        </div>

        {/* Card 3: Inactive Students */}
        <div className="student-stat-card card-inactive">
          <img
            src="/image/student-inactive-card-bg.png"
            alt=""
            className="student-stat-card-bg"
            onError={(e) => {
              e.currentTarget.style.display = "none";
            }}
          />
          <div className="student-stat-card-content">
            <div className="student-stat-icon-wrapper icon-red">
              <FontAwesomeIcon icon={faUserXmark} />
            </div>
            <div className="student-stat-data">
              <span className="student-stat-label">Inactive Students</span>
              <strong className="student-stat-value">
                {summaryLoading ? "..." : inactiveCount}
              </strong>
              <span className="student-stat-subtext">Not enrolled / on hold</span>
            </div>
          </div>
        </div>

        {/* Card 4: Face Registered */}
        <div className="student-stat-card card-face">
          <img
            src="/image/student-face-registered-card-bg.png"
            alt=""
            className="student-stat-card-bg"
            onError={(e) => {
              e.currentTarget.style.display = "none";
            }}
          />
          <div className="student-stat-card-content">
            <div className="student-stat-icon-wrapper icon-purple">
              <FontAwesomeIcon icon={faCamera} />
            </div>
            <div className="student-stat-data">
              <span className="student-stat-label">Face Registered</span>
              <strong className="student-stat-value">
                {summaryLoading ? "..." : faceRegisteredCount}
              </strong>
              <span className="student-stat-subtext">
                {summaryLoading ? "..." : `${faceRegisteredPct}% of total`}
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* =====================================================
          FILTER TOOLBAR
      ====================================================== */}
      <section className="student-toolbar-card">
        <form className="student-filter-form" onSubmit={handleSearchSubmit}>
          <div className="student-filter-select-group">
            <label htmlFor="filter-dept">Department</label>
            <select
              id="filter-dept"
              value={filterDepartment}
              onChange={(e) => {
                setFilterDepartment(e.target.value);
                setCurrentPage(1);
              }}
            >
              <option value="All">All Departments</option>
              {departmentOptions.map((dept) => (
                <option key={dept.department_id} value={dept.department_id}>
                  {dept.department_name}
                </option>
              ))}
            </select>
          </div>

          <div className="student-filter-select-group">
            <label htmlFor="filter-sem">Semester</label>
            <select
              id="filter-sem"
              value={filterSemester}
              onChange={(e) => {
                setFilterSemester(e.target.value);
                setCurrentPage(1);
              }}
            >
              <option value="All">All Semesters</option>
              {semesterOptions.map((s) => (
                <option key={s} value={String(s)}>
                  Semester {s}
                </option>
              ))}
            </select>
          </div>

          <div className="student-filter-select-group">
            <label htmlFor="filter-sec">Section</label>
            <select
              id="filter-sec"
              value={filterSection}
              onChange={(e) => {
                setFilterSection(e.target.value);
                setCurrentPage(1);
              }}
            >
              <option value="All">All Sections</option>
              {sectionOptions.map((sec) => (
                <option key={sec} value={sec}>
                  Section {sec}
                </option>
              ))}
            </select>
          </div>

          <div className="student-filter-select-group">
            <label htmlFor="filter-batch">Batch Year</label>
            <select
              id="filter-batch"
              value={filterBatch}
              onChange={(e) => {
                setFilterBatch(e.target.value);
                setCurrentPage(1);
              }}
            >
              <option value="All">All Batches</option>
              {batchOptions.map((b) => (
                <option key={b.batch_id} value={b.batch_id}>
                  {b.batch_name}
                </option>
              ))}
            </select>
          </div>

          <div className="student-filter-select-group">
            <label htmlFor="filter-status">Status</label>
            <select
              id="filter-status"
              value={filterStatus}
              onChange={(e) => {
                setFilterStatus(e.target.value);
                setCurrentPage(1);
              }}
            >
              <option value="All">All Status</option>
              <option value="Active">Active</option>
              <option value="Inactive">Inactive</option>
            </select>
          </div>

          <div className="student-search-group">
            <FontAwesomeIcon icon={faMagnifyingGlass} className="student-search-icon" />
            <input
              type="text"
              placeholder="Search by name, roll no, email..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
            />
          </div>

          <div className="student-filter-actions">
            <button type="submit" className="student-search-btn">
              <FontAwesomeIcon icon={faMagnifyingGlass} />
              Search
            </button>
            <button
              type="button"
              className="student-reset-btn"
              onClick={handleResetFilters}
              title="Reset all filters"
            >
              <FontAwesomeIcon icon={faRotateRight} />
              Reset
            </button>
          </div>
        </form>
      </section>

      {/* Feedback banner */}
      {summaryError && (
        <div className="student-feedback-alert error" role="alert">
          <FontAwesomeIcon icon={faCircleExclamation} />
          <span>Summary Statistics: {summaryError}</span>
        </div>
      )}

      {deleteFeedback && (
        <div className={`student-feedback-alert ${deleteFeedback.type}`} role="alert">
          <FontAwesomeIcon
            icon={deleteFeedback.type === "success" ? faCheck : faCircleExclamation}
          />
          <span>{deleteFeedback.message}</span>
          <button
            type="button"
            onClick={() => setDeleteFeedback(null)}
            className="student-feedback-close"
          >
            ×
          </button>
        </div>
      )}

      {/* =====================================================
          MAIN WORKSPACE: TABLE + DETAILS PANEL
      ====================================================== */}
      <div
        className={`student-workspace-layout ${
          selectedStudent ? "with-details-panel" : "full-width-table"
        }`}
      >
        {/* LEFT: STUDENT TABLE CARD */}
        <section className="student-table-card">
          <div className="student-table-header">
            <div className="student-table-title">
              <div className="student-table-title-icon">
                <FontAwesomeIcon icon={faUserGraduate} />
              </div>
              <h2>Student List ({filteredStudents.length})</h2>
            </div>

            <div className="student-table-actions">
              <button
                type="button"
                className="student-add-btn"
                onClick={handleOpenCreateStudent}
              >
                <FontAwesomeIcon icon={faPlus} />
                Add Student
              </button>
              {/* UPLOAD STUDENTS IS PURPOSEFULLY REMOVED */}
            </div>
          </div>

          <div className="student-table-responsive">
            {loading ? (
              <div className="student-state-loading">
                <FontAwesomeIcon icon={faSpinner} spin size="2x" />
                <p>Loading student records...</p>
              </div>
            ) : error ? (
              <div className="student-state-error">
                <FontAwesomeIcon icon={faCircleExclamation} size="2x" />
                <h3>Unable to load students</h3>
                <p>{error}</p>
              </div>
            ) : paginatedStudents.length === 0 ? (
              <div className="student-state-empty">
                <FontAwesomeIcon icon={faUserGraduate} size="2x" />
                <h3>No students match your criteria</h3>
                <p>Try clearing your search query or filters.</p>
                <button
                  type="button"
                  className="student-reset-btn"
                  onClick={handleResetFilters}
                >
                  Clear Filters
                </button>
              </div>
            ) : (
              <table className="student-data-table">
                <thead>
                  <tr>
                    <th style={{ width: 48, textAlign: "center" }}>S.N.</th>
                    <th>Photo</th>
                    <th>Name</th>
                    <th>Roll No.</th>
                    <th>Semester</th>
                    <th>Section</th>
                    <th>Department</th>
                    <th>Status</th>
                    <th>Face Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedStudents.map((student, index) => {
                    const isSelected = selectedStudent?.student_id === student.student_id;
                    const avatarPalette = getAvatarColor(student.name);
                    const serialNumber = (safeCurrentPage - 1) * pageSize + index + 1;

                    return (
                      <tr
                        key={student.student_id}
                        className={isSelected ? "row-selected" : ""}
                      >
                        <td className="student-sn-cell">{serialNumber}</td>
                        <td>
                          {student.photo_url ? (
                            <img
                              src={student.photo_url}
                              alt={student.name || "Student"}
                              className="student-table-avatar-img"
                              onError={(e) => {
                                e.currentTarget.style.display = "none";
                              }}
                            />
                          ) : (
                            <div
                              className="student-table-avatar"
                              style={{
                                backgroundColor: avatarPalette.bg,
                                color: avatarPalette.text,
                              }}
                            >
                              {getInitials(student.name)}
                            </div>
                          )}
                        </td>
                        <td>
                          <div className="student-name-cell">
                            <strong>{student.name || "Unnamed Student"}</strong>
                            <small>
                              {student.email || "No email"}
                              {student.batch_year ? ` • Batch ${student.batch_year}` : ""}
                            </small>
                          </div>
                        </td>
                        <td className="student-mono-cell">
                          {student.roll_no || student.enrollment_no || "—"}
                        </td>
                        <td>{student.semester != null ? student.semester : "—"}</td>
                        <td>{student.section || "—"}</td>
                        <td>
                          <span className="student-dept-tag">
                            {student.department_code || student.department_name || "—"}
                          </span>
                        </td>
                        <td>
                          <span
                            className={`student-status-badge ${
                              student.is_active ? "badge-active" : "badge-inactive"
                            }`}
                          >
                            {student.status || (student.is_active ? "Active" : "Inactive")}
                          </span>
                        </td>
                        <td>
                          <span
                            className={`student-face-badge ${
                              student.face_registered ? "badge-registered" : "badge-unregistered"
                            }`}
                          >
                            {student.face_status ||
                              (student.face_registered ? "Registered" : "Not Registered")}
                          </span>
                        </td>
                        <td onClick={(e) => e.stopPropagation()}>
                          <div className="student-action-buttons">
                            <button
                              type="button"
                              className={`action-icon-btn btn-view ${isSelected ? "active" : ""}`}
                              title={isSelected ? "Hide student details" : "View student details"}
                              aria-label={`View details for ${student.name}`}
                              onClick={() =>
                                setSelectedStudent((prev) =>
                                  prev?.student_id === student.student_id ? null : student
                                )
                              }
                            >
                              <Eye size={16} />
                            </button>
                            <button
                              type="button"
                              className="action-icon-btn btn-edit"
                              title="Edit student"
                              aria-label={`Edit ${student.name}`}
                              onClick={() => handleOpenEditStudent(student)}
                            >
                              <Pencil size={16} />
                            </button>
                            <button
                              type="button"
                              className="action-icon-btn btn-camera"
                              title="Register face"
                              aria-label={`Register face for ${student.name}`}
                              onClick={() => handleOpenFaceEnrollment(student)}
                            >
                              <FontAwesomeIcon icon={faCamera} />
                            </button>
                            <button
                              type="button"
                              className="action-icon-btn btn-delete"
                              title="Delete student"
                              aria-label={`Delete ${student.name}`}
                              disabled={deletingStudentId === student.student_id}
                              onClick={() => handleDeleteStudent(student)}
                            >
                              <Trash2 size={16} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>

          {/* Pagination */}
          {!loading && filteredStudents.length > 0 && (
            <div className="student-pagination-footer">
              <span className="student-pagination-info">
                Showing {(safeCurrentPage - 1) * pageSize + 1} to{" "}
                {Math.min(safeCurrentPage * pageSize, filteredStudents.length)} of{" "}
                {filteredStudents.length} students
              </span>

              <div className="student-pagination-btns">
                <button
                  type="button"
                  className="page-nav-btn"
                  disabled={safeCurrentPage === 1}
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  aria-label="Previous page"
                >
                  ‹
                </button>

                {Array.from({ length: totalPages }, (_, i) => i + 1)
                  .filter((p) => {
                    if (totalPages <= 7) return true;
                    if (p === 1 || p === totalPages) return true;
                    return Math.abs(p - safeCurrentPage) <= 1;
                  })
                  .reduce((acc, p, idx, arr) => {
                    if (idx > 0 && p - arr[idx - 1] > 1) {
                      acc.push(-1); // ellipsis
                    }
                    acc.push(p);
                    return acc;
                  }, [])
                  .map((p, idx) =>
                    p === -1 ? (
                      <span key={`ellipsis-${idx}`} className="page-ellipsis">
                        ...
                      </span>
                    ) : (
                      <button
                        key={p}
                        type="button"
                        className={`page-num-btn ${p === safeCurrentPage ? "active" : ""}`}
                        onClick={() => setCurrentPage(p)}
                      >
                        {p}
                      </button>
                    )
                  )}

                <button
                  type="button"
                  className="page-nav-btn"
                  disabled={safeCurrentPage === totalPages}
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  aria-label="Next page"
                >
                  ›
                </button>
              </div>
            </div>
          )}
        </section>

        {/* RIGHT: STUDENT DETAILS PANEL (Visible only when View eye icon is clicked) */}
        {selectedStudent && (
          <aside className="student-details-panel" aria-label="Student details">
            <div className="student-panel-top-bar">
              <span className="student-panel-top-title">Student Details</span>
              <button
                type="button"
                className="student-panel-close-btn"
                onClick={() => setSelectedStudent(null)}
                title="Close details panel"
                aria-label="Close details panel"
              >
                <FontAwesomeIcon icon={faXmark} />
              </button>
            </div>

            {/* Profile Card Header */}
              <div className="student-panel-profile-header">
                {selectedStudent.photo_url ? (
                  <img
                    src={selectedStudent.photo_url}
                    alt={selectedStudent.name || "Student"}
                    className="student-panel-avatar-img"
                    onError={(e) => {
                      e.currentTarget.style.display = "none";
                    }}
                  />
                ) : (
                  <div
                    className="student-panel-avatar"
                    style={{
                      backgroundColor: getAvatarColor(selectedStudent.name).bg,
                      color: getAvatarColor(selectedStudent.name).text,
                    }}
                  >
                    {getInitials(selectedStudent.name)}
                  </div>
                )}

                <div className="student-panel-identity">
                  <div className="student-panel-name-row">
                    <h3>{selectedStudent.name || "Unnamed Student"}</h3>
                    <span
                      className={`student-status-badge ${
                        selectedStudent.is_active ? "badge-active" : "badge-inactive"
                      }`}
                    >
                      {selectedStudent.status || (selectedStudent.is_active ? "Active" : "Inactive")}
                    </span>
                  </div>

                  <p className="student-panel-id-line">
                    Roll No: <strong>{selectedStudent.roll_no || selectedStudent.enrollment_no || "—"}</strong>
                  </p>
                  <p className="student-panel-id-line">
                    Enrollment: <strong>{selectedStudent.enrollment_no || "—"}</strong>
                  </p>
                  <p className="student-panel-dept-line">
                    {selectedStudent.department_name || "Department not assigned"}
                  </p>
                </div>
              </div>

              {/* Tabs */}
              <div className="student-panel-tabs" role="tablist">
                <button
                  type="button"
                  role="tab"
                  aria-selected={detailsTab === "profile"}
                  className={`panel-tab-btn ${detailsTab === "profile" ? "active" : ""}`}
                  onClick={() => setDetailsTab("profile")}
                >
                  Profile
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={detailsTab === "academic"}
                  className={`panel-tab-btn ${detailsTab === "academic" ? "active" : ""}`}
                  onClick={() => setDetailsTab("academic")}
                >
                  Academic
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={detailsTab === "attendance"}
                  className={`panel-tab-btn ${detailsTab === "attendance" ? "active" : ""}`}
                  onClick={() => setDetailsTab("attendance")}
                >
                  Attendance
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={detailsTab === "face"}
                  className={`panel-tab-btn ${detailsTab === "face" ? "active" : ""}`}
                  onClick={() => setDetailsTab("face")}
                >
                  Face Data
                </button>
              </div>

              {/* Tab Contents */}
              <div className="student-panel-tab-content">
                {/* 1. Profile Tab */}
                {detailsTab === "profile" && (
                  <div className="panel-info-list">
                    <div className="panel-info-item">
                      <div className="panel-info-icon">
                        <FontAwesomeIcon icon={faEnvelope} />
                      </div>
                      <div className="panel-info-text">
                        <span className="panel-info-label">Email</span>
                        <strong className="panel-info-val">
                          {selectedStudent.email || "—"}
                        </strong>
                      </div>
                    </div>

                    <div className="panel-info-item">
                      <div className="panel-info-icon">
                        <FontAwesomeIcon icon={faPhone} />
                      </div>
                      <div className="panel-info-text">
                        <span className="panel-info-label">Phone</span>
                        <strong className="panel-info-val">
                          {selectedStudent.phone || "—"}
                        </strong>
                      </div>
                    </div>

                    <div className="panel-info-item">
                      <div className="panel-info-icon">
                        <FontAwesomeIcon icon={faCalendarDays} />
                      </div>
                      <div className="panel-info-text">
                        <span className="panel-info-label">Date of Birth</span>
                        <strong className="panel-info-val">
                          {selectedStudent.date_of_birth || "—"}
                        </strong>
                      </div>
                    </div>

                    <div className="panel-info-item">
                      <div className="panel-info-icon">
                        <FontAwesomeIcon icon={faUser} />
                      </div>
                      <div className="panel-info-text">
                        <span className="panel-info-label">Gender</span>
                        <strong className="panel-info-val">
                          {selectedStudent.gender || "—"}
                        </strong>
                      </div>
                    </div>

                    <div className="panel-info-item">
                      <div className="panel-info-icon">
                        <FontAwesomeIcon icon={faLocationDot} />
                      </div>
                      <div className="panel-info-text">
                        <span className="panel-info-label">Address</span>
                        <strong className="panel-info-val">
                          {selectedStudent.address ||
                            (selectedStudent.city
                              ? `${selectedStudent.city}${
                                  selectedStudent.state ? ", " + selectedStudent.state : ""
                                }`
                              : "—")}
                        </strong>
                      </div>
                    </div>

                    <div className="panel-info-item">
                      <div className="panel-info-icon">
                        <FontAwesomeIcon icon={faSchool} />
                      </div>
                      <div className="panel-info-text">
                        <span className="panel-info-label">Admission Year</span>
                        <strong className="panel-info-val">
                          {selectedStudent.admission_year ||
                            selectedStudent.academic_year ||
                            "—"}
                        </strong>
                      </div>
                    </div>

                    <div className="panel-info-item">
                      <div className="panel-info-icon">
                        <FontAwesomeIcon icon={faUsers} />
                      </div>
                      <div className="panel-info-text">
                        <span className="panel-info-label">Guardian</span>
                        <strong className="panel-info-val">
                          {selectedStudent.father_name
                            ? `${selectedStudent.father_name} (Father)`
                            : selectedStudent.mother_name
                            ? `${selectedStudent.mother_name} (Mother)`
                            : "—"}
                        </strong>
                        {selectedStudent.guardian_phone && (
                          <small className="panel-info-sub">
                            {selectedStudent.guardian_phone}
                          </small>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* 2. Academic Tab */}
                {detailsTab === "academic" && (
                  <div className="panel-info-list">
                    <div className="panel-info-item">
                      <div className="panel-info-icon">
                        <FontAwesomeIcon icon={faBuilding} />
                      </div>
                      <div className="panel-info-text">
                        <span className="panel-info-label">Department</span>
                        <strong className="panel-info-val">
                          {selectedStudent.department_name || "—"}{" "}
                          {selectedStudent.department_code && (
                            `(${selectedStudent.department_code})`
                          )}
                        </strong>
                      </div>
                    </div>

                    <div className="panel-info-item">
                      <div className="panel-info-icon">
                        <FontAwesomeIcon icon={faBookOpen} />
                      </div>
                      <div className="panel-info-text">
                        <span className="panel-info-label">Semester & Section</span>
                        <strong className="panel-info-val">
                          Semester {selectedStudent.semester ?? "—"}, Section{" "}
                          {selectedStudent.section || "—"}
                        </strong>
                      </div>
                    </div>

                    <div className="panel-info-item">
                      <div className="panel-info-icon">
                        <FontAwesomeIcon icon={faSchool} />
                      </div>
                      <div className="panel-info-text">
                        <span className="panel-info-label">Academic Year</span>
                        <strong className="panel-info-val">
                          {selectedStudent.academic_year || "—"}
                        </strong>
                        <small className="panel-info-sub">Current Academic Session</small>
                      </div>
                    </div>

                    <div className="panel-info-item">
                      <div className="panel-info-icon">
                        <FontAwesomeIcon icon={faUsers} />
                      </div>
                      <div className="panel-info-text">
                        <span className="panel-info-label">Batch Year</span>
                        <strong className="panel-info-val">
                          {selectedStudent.batch_year || selectedStudent.batch_name || "—"}
                        </strong>
                        <small className="panel-info-sub">Cohort Program Duration</small>
                      </div>
                    </div>
                  </div>
                )}

                {/* 3. Attendance Tab */}
                {detailsTab === "attendance" && (
                  <div className="panel-attendance-box">
                    <div className="panel-attendance-metric">
                      <span className="panel-metric-number">
                        {selectedStudent.attendance_summary?.attendance_percentage ?? 0}%
                      </span>
                      <span className="panel-metric-title">Overall Attendance</span>
                    </div>

                    <div className="panel-attendance-stats-grid">
                      <div className="panel-attendance-stat">
                        <span>Total Sessions</span>
                        <strong>
                          {selectedStudent.attendance_summary?.total_sessions ?? 0}
                        </strong>
                      </div>
                      <div className="panel-attendance-stat text-success">
                        <span>Attended</span>
                        <strong>
                          {selectedStudent.attendance_summary?.present_sessions ?? 0}
                        </strong>
                      </div>
                      <div className="panel-attendance-stat text-danger">
                        <span>Absent</span>
                        <strong>
                          {selectedStudent.attendance_summary?.absent_sessions ?? 0}
                        </strong>
                      </div>
                    </div>
                  </div>
                )}

                {/* 4. Face Data Tab */}
                {detailsTab === "face" && (
                  <div className="panel-face-box">
                    <div className="panel-face-status-badge-row">
                      <span
                        className={`student-face-badge ${
                          selectedStudent.face_registered
                            ? "badge-registered"
                            : "badge-unregistered"
                        }`}
                      >
                        {selectedStudent.face_registered
                          ? "Face Profile Registered"
                          : "Face Not Registered"}
                      </span>
                    </div>

                    <p className="panel-face-desc">
                      {selectedStudent.face_registered
                        ? "Student face biometric data is enrolled in the facial recognition system."
                        : "No biometric face data found. Register face via camera to enable attendance."}
                    </p>

                    {selectedStudent.face_registered ? (
                      <>
                        <button
                          type="button"
                          className="student-panel-face-btn"
                          onClick={() => handleOpenFaceEnrollment(selectedStudent)}
                        >
                          <FontAwesomeIcon icon={faCamera} />
                          Replace Face
                        </button>
                        <button
                          type="button"
                          className="student-panel-face-remove-btn"
                          onClick={() => setStudentToRemoveFace(selectedStudent)}
                        >
                          <FontAwesomeIcon icon={faUserXmark} />
                          Remove Face Registration
                        </button>
                      </>
                    ) : (
                      <button
                        type="button"
                        className="student-panel-face-btn"
                        onClick={() => handleOpenFaceEnrollment(selectedStudent)}
                      >
                        <FontAwesomeIcon icon={faCamera} />
                        Register Face
                      </button>
                    )}
                  </div>
                )}
              </div>

              {/* Bottom Action */}
              <div className="student-panel-footer">
                <button
                  type="button"
                  className="student-edit-profile-btn"
                  onClick={() => handleOpenEditStudent(selectedStudent)}
                >
                  <Pencil size={15} />
                  Edit Student Profile
                </button>
              </div>
          </aside>
        )}
      </div>

      {/* =====================================================
          ADD STUDENT MODAL
      ====================================================== */}
      {showCreateStudent && (
        <div
          className="student-modal-backdrop"
          role="presentation"
          onClick={handleCloseCreateStudent}
        >
          <div
            className="student-dialog-box"
            role="dialog"
            aria-modal="true"
            aria-labelledby="create-student-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="student-dialog-header">
              <div className="student-dialog-header-left">
                <div className="student-dialog-header-icon">
                  <FontAwesomeIcon icon={faUserGraduate} />
                </div>
                <div>
                  <h2 id="create-student-title">Add Student</h2>
                  <p>Enroll an existing student account into an academic department</p>
                </div>
              </div>
              <button
                type="button"
                className="student-dialog-close"
                onClick={handleCloseCreateStudent}
                disabled={createStudentLoading}
                aria-label="Close modal"
              >
                <FontAwesomeIcon icon={faXmark} />
              </button>
            </div>

            <div className="student-dialog-note">
              <FontAwesomeIcon icon={faCircleInfo} />
              <span>
                Select an existing User account with the STUDENT role. User accounts are created in User Management.
              </span>
            </div>

            <form onSubmit={handleCreateStudentSubmit}>
              <div className="student-dialog-grid">
                <div className="student-field-full">
                  <label htmlFor="create-user">Student User Account *</label>
                  <select
                    id="create-user"
                    name="user_id"
                    value={createStudentForm.user_id}
                    onChange={handleCreateStudentChange}
                    disabled={createStudentLoading}
                    required
                  >
                    <option value="">Select a Student User</option>
                    {studentUsers.map((u) => (
                      <option key={u.user_id} value={u.user_id}>
                        {u.full_name || u.name} ({u.email})
                      </option>
                    ))}
                  </select>
                  {studentUsers.length === 0 && (
                    <small className="field-hint text-amber">
                      No unassigned STUDENT users found. Create one in User Management first.
                    </small>
                  )}
                </div>

                <div>
                  <label htmlFor="create-roll">Roll / Enrollment No. *</label>
                  <input
                    id="create-roll"
                    name="enrollment_no"
                    type="text"
                    placeholder="e.g. CSE2026001"
                    value={createStudentForm.enrollment_no}
                    onChange={handleCreateStudentChange}
                    disabled={createStudentLoading}
                    required
                  />
                </div>

                <div>
                  <label htmlFor="create-dept">Department *</label>
                  <select
                    id="create-dept"
                    name="department_id"
                    value={createStudentForm.department_id}
                    onChange={handleCreateStudentChange}
                    disabled={createStudentLoading || departmentsLoading}
                    required
                  >
                    <option value="">Select a Department</option>
                    {departmentOptions.map((d) => (
                      <option key={d.department_id} value={d.department_id}>
                        {d.department_name} ({d.department_code})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label htmlFor="create-sem">Semester *</label>
                  <input
                    id="create-sem"
                    name="semester"
                    type="text"
                    placeholder="e.g. 1"
                    value={createStudentForm.semester}
                    onChange={handleCreateStudentChange}
                    disabled={createStudentLoading}
                    required
                  />
                </div>

                <div>
                  <label htmlFor="create-sec">Section *</label>
                  <input
                    id="create-sec"
                    name="section"
                    type="text"
                    placeholder="e.g. A"
                    value={createStudentForm.section}
                    onChange={handleCreateStudentChange}
                    disabled={createStudentLoading}
                    required
                  />
                </div>

                <div>
                  <label htmlFor="create-year">Academic Year *</label>
                  <input
                    id="create-year"
                    name="academic_year"
                    type="text"
                    placeholder="e.g. 2026-2027"
                    value={createStudentForm.academic_year}
                    onChange={handleCreateStudentChange}
                    disabled={createStudentLoading}
                    required
                  />
                  <small style={{ fontSize: "11px", color: "#6b7280" }}>
                    Current academic session (e.g. 2026-2027)
                  </small>
                </div>

                <div>
                  <label htmlFor="create-batch">Batch Year / Cohort</label>
                  <select
                    id="create-batch"
                    name="batch_id"
                    value={createStudentForm.batch_id}
                    onChange={handleCreateStudentChange}
                    disabled={createStudentLoading || batchesLoading}
                  >
                    <option value="">Select Batch (e.g. 2024-2028)</option>
                    {batchOptions.map((b) => (
                      <option key={b.batch_id} value={b.batch_id}>
                        {b.batch_name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {createStudentError && (
                <div className="student-dialog-alert error" role="alert">
                  <FontAwesomeIcon icon={faCircleExclamation} />
                  <span>{createStudentError}</span>
                </div>
              )}

              <div className="student-dialog-footer">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={handleCloseCreateStudent}
                  disabled={createStudentLoading}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={createStudentLoading || studentUsers.length === 0}
                >
                  {createStudentLoading ? (
                    <>
                      <FontAwesomeIcon icon={faSpinner} spin />
                      Creating...
                    </>
                  ) : (
                    "Create Student"
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* =====================================================
          EDIT STUDENT MODAL
      ====================================================== */}
      {editingStudent && (
        <div
          className="student-modal-backdrop"
          role="presentation"
          onClick={handleCloseEditStudent}
        >
          <div
            className="student-dialog-box"
            role="dialog"
            aria-modal="true"
            aria-labelledby="edit-student-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="student-dialog-header">
              <div className="student-dialog-header-left">
                <div className="student-dialog-header-icon">
                  <Pencil size={20} />
                </div>
                <div>
                  <h2 id="edit-student-title">Edit Student Profile</h2>
                  <p>
                    {editingStudent.name} (ID: {editingStudent.student_id})
                  </p>
                </div>
              </div>
              <button
                type="button"
                className="student-dialog-close"
                onClick={handleCloseEditStudent}
                disabled={editStudentLoading}
                aria-label="Close modal"
              >
                <FontAwesomeIcon icon={faXmark} />
              </button>
            </div>

            <form onSubmit={handleSaveStudent}>
              <div className="student-dialog-grid">
                <div>
                  <label htmlFor="edit-roll">Roll / Enrollment No. *</label>
                  <input
                    id="edit-roll"
                    name="enrollment_no"
                    type="text"
                    value={editStudentForm.enrollment_no}
                    onChange={handleEditStudentChange}
                    disabled={editStudentLoading}
                    required
                  />
                </div>

                <div>
                  <label htmlFor="edit-dept">Department *</label>
                  <select
                    id="edit-dept"
                    name="department_id"
                    value={editStudentForm.department_id}
                    onChange={handleEditStudentChange}
                    disabled={editStudentLoading || departmentsLoading}
                    required
                  >
                    <option value="">Select Department</option>
                    {departmentOptions.map((d) => (
                      <option key={d.department_id} value={d.department_id}>
                        {d.department_name} ({d.department_code})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label htmlFor="edit-sem">Semester *</label>
                  <select
                    id="edit-sem"
                    name="semester"
                    value={editStudentForm.semester}
                    onChange={handleEditStudentChange}
                    disabled={editStudentLoading}
                    required
                  >
                    <option value="">Select Semester</option>
                    {semesterOptions.map((s) => (
                      <option key={s} value={s}>
                        Semester {s}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label htmlFor="edit-sec">Section</label>
                  <select
                    id="edit-sec"
                    name="section"
                    value={editStudentForm.section}
                    onChange={handleEditStudentChange}
                    disabled={editStudentLoading}
                  >
                    <option value="">Select Section</option>
                    {sectionOptions.map((sec) => (
                      <option key={sec} value={sec}>
                        Section {sec}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label htmlFor="edit-year">Academic Year *</label>
                  <input
                    id="edit-year"
                    name="academic_year"
                    type="text"
                    placeholder="e.g. 2026-2027"
                    value={editStudentForm.academic_year}
                    onChange={handleEditStudentChange}
                    disabled={editStudentLoading}
                    required
                  />
                  <small style={{ fontSize: "11px", color: "#6b7280" }}>
                    Current academic session (e.g. 2026-2027)
                  </small>
                </div>

                <div>
                  <label htmlFor="edit-batch">Batch Year / Cohort</label>
                  <select
                    id="edit-batch"
                    name="batch_id"
                    value={editStudentForm.batch_id}
                    onChange={handleEditStudentChange}
                    disabled={editStudentLoading || batchesLoading}
                  >
                    <option value="">Select Batch (e.g. 2024-2028)</option>
                    {batchOptions.map((b) => (
                      <option key={b.batch_id} value={b.batch_id}>
                        {b.batch_name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {editStudentError && (
                <div className="student-dialog-alert error" role="alert">
                  <FontAwesomeIcon icon={faCircleExclamation} />
                  <span>{editStudentError}</span>
                </div>
              )}

              {editStudentSuccess && (
                <div className="student-dialog-alert success" role="status">
                  <FontAwesomeIcon icon={faCheck} />
                  <span>{editStudentSuccess}</span>
                </div>
              )}

              <div className="student-dialog-footer">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={handleCloseEditStudent}
                  disabled={editStudentLoading}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={editStudentLoading}
                >
                  {editStudentLoading ? (
                    <>
                      <FontAwesomeIcon icon={faSpinner} spin />
                      Saving...
                    </>
                  ) : (
                    "Save Changes"
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* =====================================================
          FACE REGISTRATION MODAL (LIVE CAMERA)
      ====================================================== */}
      {showFaceRegistrationView && faceEnrollmentStudent && (
        <div
          className="student-modal-backdrop"
          role="presentation"
          onClick={() => {
            if (!faceEnrollmentLoading) {
              setShowFaceRegistrationView(false);
              setFaceCaptureBlob(null);
            }
          }}
        >
          <div
            className="student-dialog-box student-face-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="face-reg-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="student-dialog-header">
              <div className="student-dialog-header-left">
                <div className="student-dialog-header-icon icon-purple">
                  <FontAwesomeIcon icon={faCamera} />
                </div>
                <div>
                  <h2 id="face-reg-title">Face Biometric Registration</h2>
                  <div className="student-face-modal-meta">
                    <span className="student-face-modal-name">{faceEnrollmentStudent.name}</span>
                    <span className="student-face-modal-roll">
                      Roll: {faceEnrollmentStudent.roll_no || faceEnrollmentStudent.enrollment_no || "—"}
                    </span>
                    {faceEnrollmentStudent.department_name && (
                      <span className="student-face-modal-dept">{faceEnrollmentStudent.department_name}</span>
                    )}
                    <span
                      className={`student-face-modal-badge ${
                        faceEnrollmentStudent.face_registered ? "registered" : "unregistered"
                      }`}
                    >
                      {faceEnrollmentStudent.face_registered ? "Update Biometrics" : "New Enrollment"}
                    </span>
                  </div>
                </div>
              </div>
              <button
                type="button"
                className="student-dialog-close"
                onClick={() => {
                  if (!faceEnrollmentLoading) {
                    setShowFaceRegistrationView(false);
                    setFaceCaptureBlob(null);
                  }
                }}
                disabled={faceEnrollmentLoading}
                aria-label="Close modal"
              >
                <FontAwesomeIcon icon={faXmark} />
              </button>
            </div>

            {faceEnrollmentStudent.face_registered && (
              <div className="face-existing-preview-banner">
                <div className="face-existing-preview-info">
                  {faceEnrollmentStudent.photo_url ? (
                    <img
                      src={faceEnrollmentStudent.photo_url}
                      alt={faceEnrollmentStudent.name}
                      style={{
                        width: 44,
                        height: 44,
                        borderRadius: "50%",
                        objectFit: "cover",
                        border: "2px solid #e2e8f0",
                        flexShrink: 0,
                      }}
                      onError={(e) => {
                        e.currentTarget.style.display = "none";
                      }}
                    />
                  ) : (
                    <div
                      style={{
                        width: 44,
                        height: 44,
                        borderRadius: "50%",
                        background: "#dbeafe",
                        color: "#1e40af",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontWeight: 700,
                        fontSize: 14,
                        flexShrink: 0,
                      }}
                    >
                      {getInitials(faceEnrollmentStudent.name)}
                    </div>
                  )}
                  <div className="face-existing-preview-text">
                    <strong>Active Face Biometric Registered</strong>
                    <span>Replace the face biometric below, or remove it entirely.</span>
                  </div>
                </div>
                <button
                  type="button"
                  className="face-reg-action-btn btn-remove"
                  onClick={() => {
                    const target = faceEnrollmentStudent;
                    setShowFaceRegistrationView(false);
                    setFaceCaptureBlob(null);
                    setStudentToRemoveFace(target);
                  }}
                  title="Remove existing biometric registration"
                >
                  <FontAwesomeIcon icon={faUserXmark} />
                  Remove Registration
                </button>
              </div>
            )}

            <form onSubmit={handleEnrollFaceSubmit}>
              <div className="student-live-camera-wrap">
                <LiveFaceCapture
                  onCapture={handleFaceCapture}
                  onRetake={() => {
                    setFaceCaptureBlob(null);
                    setFaceEnrollmentError("");
                    setFaceEnrollmentSuccess("");
                  }}
                  disabled={faceEnrollmentLoading}
                  footerAction={
                    <button
                      type="submit"
                      className="btn-primary"
                      disabled={faceEnrollmentLoading || !faceCaptureBlob}
                    >
                      {faceEnrollmentLoading ? (
                        <>
                          <FontAwesomeIcon icon={faSpinner} spin />
                          Processing & Enrolling...
                        </>
                      ) : (
                        <>
                          <FontAwesomeIcon icon={faCheck} />
                          Save Face Registration
                        </>
                      )}
                    </button>
                  }
                />
              </div>

              {faceEnrollmentError && (
                <div className="student-dialog-alert error" role="alert">
                  <FontAwesomeIcon icon={faCircleExclamation} />
                  <span>{faceEnrollmentError}</span>
                </div>
              )}

              {faceEnrollmentSuccess && (
                <div className="student-dialog-alert success" role="status">
                  <FontAwesomeIcon icon={faCheck} />
                  <span>{faceEnrollmentSuccess}</span>
                </div>
              )}

              <div className="student-dialog-footer">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    setShowFaceRegistrationView(false);
                    setFaceCaptureBlob(null);
                  }}
                  disabled={faceEnrollmentLoading}
                >
                  Close
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Confirmation Dialog for Face Removal */}
      <RemoveFaceModal
        isOpen={Boolean(studentToRemoveFace)}
        student={studentToRemoveFace}
        onClose={() => setStudentToRemoveFace(null)}
        onSuccess={async () => {
          setSelectedStudent((prev) =>
            prev && prev.student_id === studentToRemoveFace?.student_id
              ? { ...prev, face_registered: false }
              : prev
          );
          await Promise.all([fetchStudents(), fetchSummary()]);
        }}
      />
    </div>
  );
}

export default Students;