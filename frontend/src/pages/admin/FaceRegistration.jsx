import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  faBuilding,
  faCamera,
  faCameraRotate,
  faCheck,
  faCircleExclamation,
  faMagnifyingGlass,
  faRotateRight,
  faSpinner,
  faUserGraduate,
  faUsers,
  faUserXmark,
  faXmark,
} from "@fortawesome/free-solid-svg-icons";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

import {
  getAdminDepartments,
  getAdminStudents,
  getAdminStudentsFilterOptions,
  getAdminStudentsSummary,
} from "../../services/adminService";

import { enrollStudentFace } from "../../services/faceService";
import LiveFaceCapture from "../../components/LiveFaceCapture";
import RemoveFaceModal from "../../components/RemoveFaceModal";

import "./FaceRegistration.css";

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
  invalid_image: "The captured image is invalid. Please capture another image.",
  no_face: "No face was detected. Please position the student clearly inside the camera frame.",
  multiple_faces: "Multiple faces were detected. Make sure exactly one face is visible.",
  encoding_failed: "Face processing failed. Please capture the face again.",
  invalid_encoding: "The generated face data was invalid. Please try again.",
};

function FaceRegistration() {
  // Data state
  const [students, setStudents] = useState([]);
  const [summary, setSummary] = useState(null);
  const [departmentOptions, setDepartmentOptions] = useState([]);

  const [loading, setLoading] = useState(true);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [error, setError] = useState("");

  // Filters
  const [statusTab, setStatusTab] = useState("all"); // "all", "pending", "registered"
  const [filterDepartment, setFilterDepartment] = useState("All");
  const [filterSemester, setFilterSemester] = useState("All");
  const [filterSection, setFilterSection] = useState("All");
  const [searchInput, setSearchInput] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [dbFilterOptions, setDbFilterOptions] = useState(null);

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  // Face Registration Modal State
  const [modalOpen, setModalOpen] = useState(false);
  const [enrollingStudent, setEnrollingStudent] = useState(null);
  const [capturedBlob, setCapturedBlob] = useState(null);
  const [submittingEnrollment, setSubmittingEnrollment] = useState(false);
  const [enrollmentError, setEnrollmentError] = useState("");
  const [enrollmentSuccess, setEnrollmentSuccess] = useState("");
  const [studentToRemove, setStudentToRemove] = useState(null);

  // Fetch summary counts
  const fetchSummary = useCallback(async () => {
    setSummaryLoading(true);
    try {
      const res = await getAdminStudentsSummary();
      if (res?.success && res.data) {
        setSummary(res.data);
      }
    } catch (err) {
      console.error("Summary error:", err);
    } finally {
      setSummaryLoading(false);
    }
  }, []);

  // Fetch students
  const fetchStudents = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await getAdminStudents();
      if (!res?.success) {
        throw new Error(res?.message || "Failed to load students.");
      }
      setStudents(Array.isArray(res.data) ? res.data : []);
    } catch (err) {
      setError(err?.response?.data?.message || err?.message || "Failed to load students.");
      setStudents([]);
    } finally {
      setLoading(false);
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
    const loadDepts = async () => {
      try {
        const res = await getAdminDepartments();
        if (res?.success && Array.isArray(res.data)) {
          setDepartmentOptions(res.data);
        }
      } catch (err) {
        console.error("Departments error:", err);
      }
    };
    loadDepts();
  }, []);

  // Load database filter options on mount
  useEffect(() => {
    let cancelled = false;
    const loadFilterOptions = async () => {
      try {
        const res = await getAdminStudentsFilterOptions();
        if (res?.success && res.data && !cancelled) {
          setDbFilterOptions(res.data);
        }
      } catch (err) {
        console.error("Filter options error:", err);
      }
    };
    loadFilterOptions();
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

  // Filtering
  const filteredStudents = useMemo(() => {
    const search = appliedSearch.trim().toLowerCase();

    return students.filter((student) => {
      // Tab filter
      if (statusTab === "pending" && student.face_registered) return false;
      if (statusTab === "registered" && !student.face_registered) return false;

      // Department filter
      if (
        filterDepartment !== "All" &&
        String(student.department_id) !== String(filterDepartment) &&
        student.department_name !== filterDepartment
      ) {
        return false;
      }

      // Semester filter
      if (filterSemester !== "All" && String(student.semester) !== String(filterSemester)) {
        return false;
      }

      // Section filter
      if (
        filterSection !== "All" &&
        String(student.section || "").trim().toUpperCase() !== String(filterSection).trim().toUpperCase()
      ) {
        return false;
      }

      // Search filter
      if (search) {
        const name = String(student.name || "").toLowerCase();
        const roll = String(student.roll_no || student.enrollment_no || "").toLowerCase();
        const email = String(student.email || "").toLowerCase();
        const dept = String(student.department_code || student.department_name || "").toLowerCase();

        return (
          name.includes(search) ||
          roll.includes(search) ||
          email.includes(search) ||
          dept.includes(search)
        );
      }

      return true;
    });
  }, [students, statusTab, filterDepartment, filterSemester, filterSection, appliedSearch]);

  const totalPages = Math.max(1, Math.ceil(filteredStudents.length / pageSize));
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const paginatedStudents = useMemo(() => {
    const start = (safeCurrentPage - 1) * pageSize;
    return filteredStudents.slice(start, start + pageSize);
  }, [filteredStudents, safeCurrentPage, pageSize]);

  // Quick count calculations
  const totalCount = students.length;
  const registeredCount = summary?.face_registered ?? students.filter((s) => s.face_registered).length;
  const pendingCount = Math.max(0, totalCount - registeredCount);
  const registeredPercent =
    summary?.face_registered_percentage ??
    (totalCount > 0 ? Math.round((registeredCount / totalCount) * 100) : 0);

  function handleSearchSubmit(e) {
    e.preventDefault();
    setAppliedSearch(searchInput);
    setCurrentPage(1);
  }

  function handleResetFilters() {
    setStatusTab("all");
    setFilterDepartment("All");
    setFilterSemester("All");
    setFilterSection("All");
    setSearchInput("");
    setAppliedSearch("");
    setCurrentPage(1);
  }

  // Modal actions
  function handleOpenEnrollment(student) {
    setEnrollingStudent(student);
    setCapturedBlob(null);
    setEnrollmentError("");
    setEnrollmentSuccess("");
    setModalOpen(true);
  }

  function handleCloseModal() {
    if (submittingEnrollment) return;
    setModalOpen(false);
    setEnrollingStudent(null);
    setCapturedBlob(null);
    setEnrollmentError("");
    setEnrollmentSuccess("");
  }

  function handleFaceCapture(blob) {
    setEnrollmentError("");
    setEnrollmentSuccess("");
    if (!blob) {
      setCapturedBlob(null);
      setEnrollmentError("Unable to capture face frame. Please try again.");
      return;
    }
    setCapturedBlob(blob);
  }

  async function handleEnrollSubmit(e) {
    e.preventDefault();
    if (!enrollingStudent?.student_id || !capturedBlob) {
      setEnrollmentError("Please capture student face before submitting.");
      return;
    }

    setSubmittingEnrollment(true);
    setEnrollmentError("");
    setEnrollmentSuccess("");

    try {
      const res = await enrollStudentFace(enrollingStudent.student_id, capturedBlob);
      if (!res?.success) {
        throw new Error(
          faceErrorMessages[res?.status] || res?.message || "Face enrollment failed."
        );
      }
      setEnrollmentSuccess(res.message || "Face biometric enrolled successfully!");
      await Promise.all([fetchStudents(), fetchSummary()]);
    } catch (err) {
      const backendStatus = err?.response?.data?.status || err?.status;
      setEnrollmentError(
        faceErrorMessages[backendStatus] ||
          err?.response?.data?.message ||
          err?.message ||
          "Face enrollment failed."
      );
    } finally {
      setSubmittingEnrollment(false);
    }
  }

  return (
    <div className="student-management-page">
      {/* =====================================================
          1. HEADER BANNER
      ====================================================== */}
      <section className="student-banner-card">
        <img
          src="/image/student-management-banner.png"
          alt=""
          className="student-banner-bg"
          aria-hidden="true"
        />
        <div className="student-banner-content">
          <div className="student-banner-icon">
            <FontAwesomeIcon icon={faCamera} />
          </div>
          <div className="student-banner-text">
            <h1>Face Biometric Registration</h1>
            <p>
              Capture, verify, and register high-precision facial recognition templates for student attendance.
            </p>
          </div>
        </div>
        <div className="student-banner-badge">
          <strong>Biometric Security</strong>
          <span>AI Recognition Enabled</span>
        </div>
      </section>

      {/* =====================================================
          2. SUMMARY CARDS (DECREASED VERTICAL HEIGHT)
      ====================================================== */}
      <section className="student-summary-grid" aria-label="Face registration summary statistics">
        {/* Total Students */}
        <div className="student-stat-card card-total">
          <img
            src="/image/student-total-card-bg.png"
            alt=""
            className="student-stat-card-bg"
            aria-hidden="true"
          />
          <div className="student-stat-card-content">
            <div className="student-stat-icon-wrapper icon-blue">
              <FontAwesomeIcon icon={faUsers} />
            </div>
            <div className="student-stat-data">
              <span className="student-stat-label">Total Students</span>
              <strong className="student-stat-value">
                {summaryLoading ? "—" : totalCount}
              </strong>
              <span className="student-stat-subtext">Registered in system</span>
            </div>
          </div>
        </div>

        {/* Face Registered */}
        <div className="student-stat-card card-face">
          <img
            src="/image/student-face-registered-card-bg.png"
            alt=""
            className="student-stat-card-bg"
            aria-hidden="true"
          />
          <div className="student-stat-card-content">
            <div className="student-stat-icon-wrapper icon-green">
              <FontAwesomeIcon icon={faCheck} />
            </div>
            <div className="student-stat-data">
              <span className="student-stat-label">Biometrics Registered</span>
              <strong className="student-stat-value">
                {summaryLoading ? "—" : registeredCount}
              </strong>
              <span className="student-stat-subtext">Ready for attendance</span>
            </div>
          </div>
        </div>

        {/* Pending Enrollment */}
        <div className="student-stat-card card-inactive">
          <img
            src="/image/student-inactive-card-bg.png"
            alt=""
            className="student-stat-card-bg"
            aria-hidden="true"
          />
          <div className="student-stat-card-content">
            <div className="student-stat-icon-wrapper icon-red">
              <FontAwesomeIcon icon={faUserXmark} />
            </div>
            <div className="student-stat-data">
              <span className="student-stat-label">Pending Registration</span>
              <strong className="student-stat-value">
                {summaryLoading ? "—" : pendingCount}
              </strong>
              <span className="student-stat-subtext">Needs face capture</span>
            </div>
          </div>
        </div>

        {/* Registration Rate */}
        <div className="student-stat-card card-active">
          <img
            src="/image/student-active-card-bg.png"
            alt=""
            className="student-stat-card-bg"
            aria-hidden="true"
          />
          <div className="student-stat-card-content">
            <div className="student-stat-icon-wrapper icon-purple">
              <FontAwesomeIcon icon={faCamera} />
            </div>
            <div className="student-stat-data">
              <span className="student-stat-label">Enrollment Rate</span>
              <strong className="student-stat-value">
                {summaryLoading ? "—" : `${registeredPercent}%`}
              </strong>
              <span className="student-stat-subtext">Overall coverage</span>
            </div>
          </div>
        </div>
      </section>

      {/* =====================================================
          3. FILTER TOOLBAR
      ====================================================== */}
      <section className="student-toolbar-card">
        <form className="student-filter-form" onSubmit={handleSearchSubmit}>
          {/* Quick Status Tabs */}
          <div className="face-reg-tabs">
            <button
              type="button"
              className={`face-reg-tab-btn ${statusTab === "all" ? "active" : ""}`}
              onClick={() => {
                setStatusTab("all");
                setCurrentPage(1);
              }}
            >
              All
              <span className="face-reg-tab-badge">{totalCount}</span>
            </button>
            <button
              type="button"
              className={`face-reg-tab-btn ${statusTab === "pending" ? "active" : ""}`}
              onClick={() => {
                setStatusTab("pending");
                setCurrentPage(1);
              }}
            >
              Pending
              <span className="face-reg-tab-badge">{pendingCount}</span>
            </button>
            <button
              type="button"
              className={`face-reg-tab-btn ${statusTab === "registered" ? "active" : ""}`}
              onClick={() => {
                setStatusTab("registered");
                setCurrentPage(1);
              }}
            >
              Registered
              <span className="face-reg-tab-badge">{registeredCount}</span>
            </button>
          </div>

          {/* Department Filter */}
          <div className="student-filter-select-group">
            <label htmlFor="dept-filter">
              <FontAwesomeIcon icon={faBuilding} />
              Department
            </label>
            <select
              id="dept-filter"
              value={filterDepartment}
              onChange={(e) => {
                setFilterDepartment(e.target.value);
                setCurrentPage(1);
              }}
            >
              <option value="All">All Departments</option>
              {departmentOptions.map((dept) => (
                <option key={dept.department_id} value={dept.department_id}>
                  {dept.department_code ? `${dept.department_code} - ` : ""}
                  {dept.department_name}
                </option>
              ))}
            </select>
          </div>

          {/* Semester Filter */}
          <div className="student-filter-select-group">
            <label htmlFor="sem-filter">
              <FontAwesomeIcon icon={faUserGraduate} />
              Semester
            </label>
            <select
              id="sem-filter"
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

          {/* Section Filter */}
          <div className="student-filter-select-group">
            <label htmlFor="sec-filter">
              Section
            </label>
            <select
              id="sec-filter"
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

          {/* Search Box */}
          <div className="student-search-group">
            <FontAwesomeIcon icon={faMagnifyingGlass} className="student-search-icon" />
            <input
              type="text"
              placeholder="Search by student name, roll no..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              aria-label="Search students"
            />
          </div>

          {/* Buttons */}
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

      {/* =====================================================
          4. STUDENTS BIOMETRICS TABLE
      ====================================================== */}
      <section className="student-table-card">
        <div className="student-table-header">
          <div className="student-table-title">
            <div className="student-table-title-icon">
              <FontAwesomeIcon icon={faCamera} />
            </div>
            <h2>
              Student Biometric Roster ({filteredStudents.length})
            </h2>
          </div>
        </div>

        {error && (
          <div className="student-table-alert error" role="alert">
            <FontAwesomeIcon icon={faCircleExclamation} />
            <span>{error}</span>
          </div>
        )}

        <div className="student-table-scroll">
          {loading ? (
            <div className="student-table-empty">
              <FontAwesomeIcon icon={faSpinner} spin size="2x" />
              <p>Loading student biometric records...</p>
            </div>
          ) : filteredStudents.length === 0 ? (
            <div className="student-table-empty">
              <FontAwesomeIcon icon={faCamera} size="2x" />
              <p>No student records match the selected biometric criteria.</p>
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
                  <th>Department</th>
                  <th>Semester & Section</th>
                  <th>Face Status</th>
                  <th style={{ textAlign: "center" }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {paginatedStudents.map((student, index) => {
                  const avatarPalette = getAvatarColor(student.name);
                  const serialNumber = (safeCurrentPage - 1) * pageSize + index + 1;

                  return (
                    <tr key={student.student_id}>
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
                          <small>{student.email || "No email"}</small>
                        </div>
                      </td>
                      <td className="student-mono-cell">
                        {student.roll_no || student.enrollment_no || "—"}
                      </td>
                      <td>
                        <span className="student-dept-tag">
                          {student.department_code || student.department_name || "—"}
                        </span>
                      </td>
                      <td>
                        Sem {student.semester != null ? student.semester : "—"} / Sec{" "}
                        {student.section || "—"}
                      </td>
                      <td>
                        <span
                          className={`student-face-badge ${
                            student.face_registered
                              ? "badge-registered"
                              : "badge-unregistered"
                          }`}
                        >
                          {student.face_registered ? "Registered" : "Not Registered"}
                        </span>
                      </td>
                      <td style={{ textAlign: "center" }}>
                        {student.face_registered ? (
                          <div className="face-reg-btn-group">
                            <button
                              type="button"
                              className="face-reg-action-btn btn-update"
                              onClick={() => handleOpenEnrollment(student)}
                              title="Replace existing biometric face template"
                            >
                              <FontAwesomeIcon icon={faCameraRotate} />
                              Replace Face
                            </button>
                            <button
                              type="button"
                              className="face-reg-action-btn btn-remove"
                              onClick={() => setStudentToRemove(student)}
                              title="Remove incorrect biometric face registration"
                            >
                              <FontAwesomeIcon icon={faUserXmark} />
                              Remove Face
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            className="face-reg-action-btn btn-register"
                            onClick={() => handleOpenEnrollment(student)}
                            title="Register student biometric face"
                          >
                            <FontAwesomeIcon icon={faCamera} />
                            Register Face
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Pagination Footer */}
        {filteredStudents.length > pageSize && (
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
                ‹ Previous
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
                disabled={safeCurrentPage >= totalPages}
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                aria-label="Next page"
              >
                Next ›
              </button>
            </div>
          </div>
        )}
      </section>

      {/* =====================================================
          5. FACE REGISTRATION MODAL
      ====================================================== */}
      {modalOpen && enrollingStudent && (
        <div
          className="student-modal-backdrop"
          role="presentation"
          onClick={() => {
            if (!submittingEnrollment) {
              handleCloseModal();
            }
          }}
        >
          <div
            className="student-dialog-box student-face-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="face-modal-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="student-dialog-header">
              <div className="student-dialog-header-left">
                <div className="student-dialog-header-icon icon-purple">
                  <FontAwesomeIcon icon={faCamera} />
                </div>
                <div>
                  <h2 id="face-modal-title">Face Biometric Registration</h2>
                  <div className="student-face-modal-meta">
                    <span className="student-face-modal-name">{enrollingStudent.name}</span>
                    <span className="student-face-modal-roll">
                      Roll: {enrollingStudent.roll_no || enrollingStudent.enrollment_no || "—"}
                    </span>
                    {enrollingStudent.department_name && (
                      <span className="student-face-modal-dept">
                        {enrollingStudent.department_name}
                      </span>
                    )}
                    <span
                      className={`student-face-modal-badge ${
                        enrollingStudent.face_registered ? "registered" : "unregistered"
                      }`}
                    >
                      {enrollingStudent.face_registered
                        ? "Update Biometrics"
                        : "New Enrollment"}
                    </span>
                  </div>
                </div>
              </div>
              <button
                type="button"
                className="student-dialog-close"
                onClick={handleCloseModal}
                disabled={submittingEnrollment}
                aria-label="Close modal"
              >
                <FontAwesomeIcon icon={faXmark} />
              </button>
            </div>

            {enrollingStudent.face_registered && (
              <div className="face-existing-preview-banner">
                <div className="face-existing-preview-info">
                  {enrollingStudent.photo_url ? (
                    <img
                      src={enrollingStudent.photo_url}
                      alt={enrollingStudent.name}
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
                      {getInitials(enrollingStudent.name)}
                    </div>
                  )}
                  <div className="face-existing-preview-text">
                    <strong>Active Face Biometric Registered</strong>
                    <span>You can replace the face template below, or remove it if incorrect.</span>
                  </div>
                </div>
                <button
                  type="button"
                  className="face-reg-action-btn btn-remove"
                  onClick={() => {
                    const target = enrollingStudent;
                    handleCloseModal();
                    setStudentToRemove(target);
                  }}
                  title="Remove existing biometric registration"
                >
                  <FontAwesomeIcon icon={faUserXmark} />
                  Remove Registration
                </button>
              </div>
            )}

            <form onSubmit={handleEnrollSubmit}>
              <div className="student-live-camera-wrap">
                <LiveFaceCapture
                  onCapture={handleFaceCapture}
                  onRetake={() => {
                    setCapturedBlob(null);
                    setEnrollmentError("");
                    setEnrollmentSuccess("");
                  }}
                  disabled={submittingEnrollment}
                  footerAction={
                    <button
                      type="submit"
                      className="btn-primary"
                      disabled={submittingEnrollment || !capturedBlob}
                    >
                      {submittingEnrollment ? (
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

              {enrollmentError && (
                <div className="student-dialog-alert error" role="alert">
                  <FontAwesomeIcon icon={faCircleExclamation} />
                  <span>{enrollmentError}</span>
                </div>
              )}

              {enrollmentSuccess && (
                <div className="student-dialog-alert success" role="status">
                  <FontAwesomeIcon icon={faCheck} />
                  <span>{enrollmentSuccess}</span>
                </div>
              )}

              <div className="student-dialog-footer">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={handleCloseModal}
                  disabled={submittingEnrollment}
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
        isOpen={Boolean(studentToRemove)}
        student={studentToRemove}
        onClose={() => setStudentToRemove(null)}
        onSuccess={async () => {
          await Promise.all([fetchStudents(), fetchSummary()]);
        }}
      />
    </div>
  );
}

export default FaceRegistration;
