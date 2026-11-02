import { useState, useEffect, useMemo, useCallback } from "react";
import {
  GraduationCap,
  Clock,
  Users,
  Search,
  Plus,
  ArrowRight,
  Trash2,
  RotateCw,
  Check,
  X,
  AlertCircle,
  FileText,
} from "lucide-react";
import totalEnrollmentsImg from "../../../image/total-enrollments.png";
import activeEnrollmentsImg from "../../../image/active-enrollments.png";
import pendingEnrollmentsImg from "../../../image/pending-enrollments.png";
import studentGroupsImg from "../../../image/student-groups.png";
import {
  getAdminEnrollments,
  getAdminEnrollmentsSummary,
  previewGroupEnrollment,
  bulkEnrollGroup,
  deleteAdminEnrollment,
} from "../../services/enrollmentService";
import {
  getAdminDepartments,
  getAdminBatches,
} from "../../services/adminService";
import {
  formatAcademicYear,
  getAcademicYearOptions,
  normalizeBatchCohort,
  suggestBatchForSemester,
  extractCohortStartYear,
} from "../../utils/academicYearUtils";
import "./CourseEnrollments.css";

const RECORDS_PER_PAGE = 10;

export default function CourseEnrollments() {
  // Navigation tabs: "groups" (default) or "records"
  const [activeTab, setActiveTab] = useState("groups");

  // Summary Metrics State
  const [summaryData, setSummaryData] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [summaryError, setSummaryError] = useState("");

  // Student Groups Data
  const [studentGroups, setStudentGroups] = useState([]);
  const [groupSearchQuery, setGroupSearchQuery] = useState("");
  const [selectedBatchFilter, setSelectedBatchFilter] = useState("ALL");
  const [selectedSemesterFilter, setSelectedSemesterFilter] = useState("ALL");

  // Enrollment Records Data
  const [enrollmentRecords, setEnrollmentRecords] = useState([]);
  const [recordsLoading, setRecordsLoading] = useState(false);
  const [recordsError, setRecordsError] = useState("");
  const [recordSearchQuery, setRecordSearchQuery] = useState("");
  const [recordStatusFilter, setRecordStatusFilter] = useState("ALL");
  const [recordSemesterFilter, setRecordSemesterFilter] = useState("ALL");
  const [recordSectionFilter, setRecordSectionFilter] = useState("ALL");
  const [recordsPage, setRecordsPage] = useState(1);

  // Deletion Modal State
  const [deletingRecord, setDeletingRecord] = useState(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  // Add Enrollment / Manage Group Modal State (Locked Design - Screenshot 3)
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [departments, setDepartments] = useState([]);
  const [batches, setBatches] = useState([]);

  // Form State
  const [formGroup, setFormGroup] = useState({
    department_id: "",
    batch_year: "",
    academic_year: "",
    semester: "",
    section: "",
  });
  const [isBatchUserSelected, setIsBatchUserSelected] = useState(false);

  // Preview Data State
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [previewError, setPreviewError] = useState("");

  // Course Selection in Modal (Step 2)
  const [selectedCourseIds, setSelectedCourseIds] = useState([]);

  // Student Selection in Modal (Step 3)
  const [studentFilterTab, setStudentFilterTab] = useState("PENDING"); // "PENDING", "ENROLLED", "ALL"
  const [selectedStudentIds, setSelectedStudentIds] = useState([]);

  // Enrollment Submission State
  const [submittingEnrollment, setSubmittingEnrollment] = useState(false);
  const [enrollmentSuccessMessage, setEnrollmentSuccessMessage] = useState("");
  const [enrollmentErrorMessage, setEnrollmentErrorMessage] = useState("");

  // Refresh summary and groups on demand
  const loadSummaryAndGroups = useCallback(async () => {
    try {
      setSummaryLoading(true);
      setSummaryError("");
      const res = await getAdminEnrollmentsSummary();
      if (res?.success && res.data) {
        setSummaryData(res.data);
        setStudentGroups(res.data.groups || []);
      } else {
        setSummaryError("Unable to load summary metrics");
      }
    } catch (err) {
      setSummaryError(err.response?.data?.message || err.message || "Failed to load enrollment summary");
    } finally {
      setSummaryLoading(false);
    }
  }, []);

  // Refresh enrollment records on demand
  const loadEnrollmentRecords = useCallback(async () => {
    try {
      setRecordsLoading(true);
      setRecordsError("");
      const res = await getAdminEnrollments();
      if (res?.success && Array.isArray(res.data)) {
        setEnrollmentRecords(res.data);
      } else {
        setRecordsError("Unable to load enrollment records");
      }
    } catch (err) {
      setRecordsError(err.response?.data?.message || err.message || "Failed to load enrollment records");
    } finally {
      setRecordsLoading(false);
    }
  }, []);

  // Initial load on mount
  useEffect(() => {
    let isMounted = true;

    const initializeData = async () => {
      try {
        const [sumRes, deptRes, batchRes] = await Promise.allSettled([
          getAdminEnrollmentsSummary(),
          getAdminDepartments(),
          getAdminBatches(),
        ]);

        if (!isMounted) return;

        if (sumRes.status === "fulfilled" && sumRes.value?.success && sumRes.value.data) {
          setSummaryData(sumRes.value.data);
          setStudentGroups(sumRes.value.data.groups || []);
          setSummaryError("");
        } else if (sumRes.status === "rejected") {
          setSummaryError(sumRes.reason?.response?.data?.message || sumRes.reason?.message || "Failed to load summary");
        }

        if (deptRes.status === "fulfilled" && deptRes.value?.success && Array.isArray(deptRes.value.data)) {
          setDepartments(deptRes.value.data);
        }

        if (batchRes.status === "fulfilled" && batchRes.value?.success && Array.isArray(batchRes.value.data)) {
          setBatches(batchRes.value.data);
        }
      } finally {
        if (isMounted) {
          setSummaryLoading(false);
        }
      }
    };

    void initializeData();

    return () => {
      isMounted = false;
    };
  }, []);

  // Load records when switching to records tab
  useEffect(() => {
    if (activeTab !== "records") return;
    let isMounted = true;

    const fetchRecords = async () => {
      try {
        const res = await getAdminEnrollments();
        if (!isMounted) return;
        if (res?.success && Array.isArray(res.data)) {
          setEnrollmentRecords(res.data);
          setRecordsError("");
        } else {
          setRecordsError("Unable to load enrollment records");
        }
      } catch (err) {
        if (!isMounted) return;
        setRecordsError(err.response?.data?.message || err.message || "Failed to load enrollment records");
      }
    };

    void fetchRecords();

    return () => {
      isMounted = false;
    };
  }, [activeTab]);

  // Derived filter options for Student Groups
  const availableGroupBatches = useMemo(() => {
    const set = new Set();
    studentGroups.forEach((g) => {
      const b = g.cohort || g.batch;
      if (b) set.add(String(b));
    });
    return Array.from(set).sort();
  }, [studentGroups]);

  const availableGroupSemesters = useMemo(() => {
    const set = new Set();
    studentGroups.forEach((g) => {
      if (g.semester != null) set.add(Number(g.semester));
    });
    return Array.from(set).sort((a, b) => a - b);
  }, [studentGroups]);

  // Filtered Student Groups
  const filteredStudentGroups = useMemo(() => {
    return studentGroups.filter((group) => {
      // Batch filter
      if (selectedBatchFilter !== "ALL") {
        const filterStart = extractCohortStartYear(selectedBatchFilter);
        const groupStart = extractCohortStartYear(group.cohort || group.batch);
        if (filterStart && groupStart) {
          if (filterStart !== groupStart) return false;
        } else if (String(group.batch) !== String(selectedBatchFilter)) {
          return false;
        }
      }
      // Semester filter
      if (selectedSemesterFilter !== "ALL" && String(group.semester) !== String(selectedSemesterFilter)) {
        return false;
      }
      // Search query
      if (groupSearchQuery.trim()) {
        const query = groupSearchQuery.toLowerCase();
        const deptMatch =
          group.department_code?.toLowerCase().includes(query) ||
          group.department_name?.toLowerCase().includes(query);
        const batchMatch = String(group.batch).toLowerCase().includes(query);
        const semMatch = `semester ${group.semester}`.includes(query) || `sem ${group.semester}`.includes(query);
        const secMatch = `section ${group.section}`.toLowerCase().includes(query) || group.section?.toLowerCase().includes(query);
        const ayMatch = group.academic_year?.toLowerCase().includes(query);

        if (!deptMatch && !batchMatch && !semMatch && !secMatch && !ayMatch) {
          return false;
        }
      }
      return true;
    });
  }, [studentGroups, selectedBatchFilter, selectedSemesterFilter, groupSearchQuery]);

  // Filtered Enrollment Records
  const filteredRecords = useMemo(() => {
    return enrollmentRecords.filter((record) => {
      if (recordStatusFilter !== "ALL" && record.status !== recordStatusFilter) {
        return false;
      }
      if (recordSemesterFilter !== "ALL" && String(record.semester) !== String(recordSemesterFilter)) {
        return false;
      }
      if (recordSectionFilter !== "ALL" && String(record.section) !== String(recordSectionFilter)) {
        return false;
      }
      if (recordSearchQuery.trim()) {
        const query = recordSearchQuery.toLowerCase();
        const nameMatch = record.student_name?.toLowerCase().includes(query);
        const enrMatch = record.enrollment_no?.toLowerCase().includes(query);
        const courseMatch =
          record.course_code?.toLowerCase().includes(query) ||
          record.course_name?.toLowerCase().includes(query);
        const deptMatch = record.department_code?.toLowerCase().includes(query);
        const batchMatch = record.batch_name?.toLowerCase().includes(query);
        const idMatch = String(record.enrollment_id).includes(query);

        if (!nameMatch && !enrMatch && !courseMatch && !deptMatch && !batchMatch && !idMatch) {
          return false;
        }
      }
      return true;
    });
  }, [enrollmentRecords, recordStatusFilter, recordSemesterFilter, recordSectionFilter, recordSearchQuery]);

  // Paginated Enrollment Records
  const totalRecordsPages = Math.max(1, Math.ceil(filteredRecords.length / RECORDS_PER_PAGE));
  const currentRecordsPage = Math.min(recordsPage, totalRecordsPages);
  const paginatedRecords = useMemo(() => {
    const start = (currentRecordsPage - 1) * RECORDS_PER_PAGE;
    return filteredRecords.slice(start, start + RECORDS_PER_PAGE);
  }, [filteredRecords, currentRecordsPage]);

  // Handle Enrollment Record Deletion
  const confirmDeleteRecord = async () => {
    if (!deletingRecord) return;
    try {
      setDeleteLoading(true);
      await deleteAdminEnrollment(deletingRecord.enrollment_id);
      setDeletingRecord(null);
      await Promise.all([loadEnrollmentRecords(), loadSummaryAndGroups()]);
    } catch (err) {
      alert(err.response?.data?.message || err.message || "Failed to remove enrollment record");
    } finally {
      setDeleteLoading(false);
    }
  };

  // Trigger Preview in Add Enrollment Modal / Manage Group
  const fetchGroupPreview = useCallback(async (targetGroup) => {
    if (
      !targetGroup.department_id ||
      !targetGroup.batch_year ||
      !targetGroup.semester ||
      !targetGroup.section
    ) {
      setPreviewData(null);
      return;
    }

    try {
      setPreviewLoading(true);
      setPreviewError("");
      setEnrollmentSuccessMessage("");
      setEnrollmentErrorMessage("");

      const normalizedCohort = normalizeBatchCohort(targetGroup.batch_year, batches);
      const payload = {
        department_id: targetGroup.department_id,
        cohort: normalizedCohort,
        academic_year: targetGroup.academic_year || "2026-2027",
        semester: targetGroup.semester,
        section: targetGroup.section,
      };

      const res = await previewGroupEnrollment(payload);
      if (res && res.success && res.data) {
        setPreviewData(res.data);

        // Pre-select all available courses by default
        const courses = res.data.courses || [];
        const courseIds = courses.map((c) => c.course_id);
        setSelectedCourseIds(courseIds);

        // Pre-select pending students by default
        const students = res.data.students || [];
        const pendingStudentIds = students
          .filter((s) => !s.is_enrolled)
          .map((s) => s.student_id);
        setSelectedStudentIds(pendingStudentIds.length > 0 ? pendingStudentIds : students.map((s) => s.student_id));
      } else {
        setPreviewError(res?.message || "Failed to load group details");
      }
    } catch (err) {
      setPreviewError(err.response?.data?.message || err.message || "Unable to fetch group preview");
    } finally {
      setPreviewLoading(false);
    }
  }, [batches]);

  // Open Modal via Primary "+ Add Enrollment" Button
  const handleOpenAddEnrollment = () => {
    const defaultDept = departments[0]?.department_id || (studentGroups[0]?.department_id || "");
    const defaultAy = getAcademicYearOptions()[2]?.value || "2026-2027";
    const defaultSem = "5";
    const suggestedBatch = suggestBatchForSemester(defaultSem, defaultAy, batches) || batches[0]?.batch_name || "2024-2028";
    const initialGroup = {
      department_id: String(defaultDept),
      batch_year: String(suggestedBatch),
      academic_year: String(defaultAy),
      semester: defaultSem,
      section: "A",
    };
    setIsBatchUserSelected(false);
    setFormGroup(initialGroup);
    setIsModalOpen(true);
    setEnrollmentSuccessMessage("");
    setEnrollmentErrorMessage("");
    fetchGroupPreview(initialGroup);
  };

  // Open Modal via "Manage Group" Button on a Group Card
  const handleManageGroup = (group) => {
    const normalizedCohort = normalizeBatchCohort(group.cohort || group.batch, batches);
    const initialGroup = {
      department_id: String(group.department_id),
      batch_year: String(normalizedCohort),
      academic_year: String(group.academic_year || "2026-2027"),
      semester: String(group.semester),
      section: String(group.section),
    };
    setIsBatchUserSelected(true);
    setFormGroup(initialGroup);
    setIsModalOpen(true);
    setEnrollmentSuccessMessage("");
    setEnrollmentErrorMessage("");
    fetchGroupPreview(initialGroup);
  };

  // Handle cascading form input changes
  const handleFormChange = (field, value) => {
    let updated = { ...formGroup, [field]: value };

    if (field === "batch_year") {
      setIsBatchUserSelected(Boolean(value));
    } else if (field === "semester") {
      if (!isBatchUserSelected || !formGroup.batch_year) {
        const suggested = suggestBatchForSemester(value, updated.academic_year, batches);
        if (suggested) {
          updated.batch_year = suggested;
        }
      }
    } else if (field === "academic_year") {
      if (!isBatchUserSelected || !formGroup.batch_year) {
        const suggested = suggestBatchForSemester(updated.semester, value, batches);
        if (suggested) {
          updated.batch_year = suggested;
        }
      }
    }

    setFormGroup(updated);
    fetchGroupPreview(updated);
  };

  // Handle Course Checkbox Toggle in Step 2
  const toggleCourseSelection = (courseId) => {
    setSelectedCourseIds((prev) =>
      prev.includes(courseId)
        ? prev.filter((id) => id !== courseId)
        : [...prev, courseId]
    );
  };

  // Select / Deselect All Courses in Step 2
  const handleToggleSelectAllCourses = () => {
    const allIds = (previewData?.courses || []).map((c) => c.course_id);
    if (selectedCourseIds.length === allIds.length) {
      setSelectedCourseIds([]);
    } else {
      setSelectedCourseIds(allIds);
    }
  };

  // Handle Student Checkbox Toggle in Step 3
  const toggleStudentSelection = (studentId) => {
    setSelectedStudentIds((prev) =>
      prev.includes(studentId)
        ? prev.filter((id) => id !== studentId)
        : [...prev, studentId]
    );
  };

  // Filter students based on sub-tab in Step 3
  const displayedStudents = useMemo(() => {
    const all = previewData?.students || [];
    if (studentFilterTab === "PENDING") {
      return all.filter((s) => !s.is_enrolled);
    }
    if (studentFilterTab === "ENROLLED") {
      return all.filter((s) => s.is_enrolled);
    }
    return all;
  }, [previewData, studentFilterTab]);

  // Submit Bulk Enrollment
  const handleConfirmEnrollment = async () => {
    if (!formGroup.department_id || !formGroup.batch_year || !formGroup.semester || !formGroup.section) {
      setEnrollmentErrorMessage("Please complete all student group selections.");
      return;
    }

    if (selectedCourseIds.length === 0) {
      setEnrollmentErrorMessage("Please select at least one course to enroll.");
      return;
    }

    if (selectedStudentIds.length === 0) {
      setEnrollmentErrorMessage("Please select at least one student to enroll.");
      return;
    }

    try {
      setSubmittingEnrollment(true);
      setEnrollmentErrorMessage("");
      setEnrollmentSuccessMessage("");

      const payload = {
        department_id: Number(formGroup.department_id),
        cohort: formGroup.batch_year,
        academic_year: formGroup.academic_year || formGroup.batch_year,
        semester: Number(formGroup.semester),
        section: formGroup.section,
        course_ids: selectedCourseIds,
        student_ids: selectedStudentIds,
      };

      const res = await bulkEnrollGroup(payload);
      if (res && res.success) {
        const createdCount = res.data?.created ?? 0;
        setEnrollmentSuccessMessage(
          `Successfully processed enrollment! Created ${createdCount} registration(s).`
        );
        // Refresh preview data and page summaries
        await Promise.all([
          fetchGroupPreview(formGroup),
          loadSummaryAndGroups(),
          loadEnrollmentRecords(),
        ]);
      } else {
        setEnrollmentErrorMessage(res?.message || "Failed to complete enrollment");
      }
    } catch (err) {
      setEnrollmentErrorMessage(err.response?.data?.message || err.message || "An unexpected error occurred during enrollment.");
    } finally {
      setSubmittingEnrollment(false);
    }
  };

  return (
    <div className="course-enrollments-page">
      {/* 1. Page Header */}
      <header className="course-enrollments-header">
        <div>
          <div className="course-enrollments-eyebrow">
            ADMIN PORTAL / ACADEMIC MANAGEMENT
          </div>
          <h1>Course Enrollments</h1>
          <p>Manage student course registrations by academic group.</p>
        </div>
        <button
          type="button"
          className="primary-add-btn"
          onClick={handleOpenAddEnrollment}
        >
          <Plus size={16} />
          Add Enrollment
        </button>
      </header>

      {/* 2. Top Summary Cards (4 Compact Cards with Decorative Illustrations) */}
      <div className="course-enrollments-summary-grid">
        {/* Card 1: Total Enrollments */}
        <div className="summary-card summary-card-blue">
          <div className="summary-card-content">
            <div className="summary-card-top">
              <div className="summary-badge-icon summary-badge-blue">
                <Users size={16} />
              </div>
              <span className="summary-card-title">Total Enrollments</span>
            </div>
            <div className="summary-card-value">
              {summaryLoading ? (
                <span className="summary-skeleton" />
              ) : (
                (summaryData?.total_enrollments ?? 0).toLocaleString()
              )}
            </div>
            <span className="summary-card-subtext">Across all course offerings</span>
          </div>
          <img
            className="summary-card-art"
            src={totalEnrollmentsImg || "/image/total-enrollments.png"}
            alt=""
            aria-hidden="true"
          />
        </div>

        {/* Card 2: Active Enrollments */}
        <div className="summary-card summary-card-green">
          <div className="summary-card-accent-badge summary-accent-green">
            <Check size={14} />
          </div>
          <div className="summary-card-content">
            <div className="summary-card-top">
              <div className="summary-badge-icon summary-badge-green">
                <Check size={16} />
              </div>
              <span className="summary-card-title">Active Enrollments</span>
            </div>
            <div className="summary-card-value">
              {summaryLoading ? (
                <span className="summary-skeleton" />
              ) : (
                (summaryData?.active_enrollments ?? 0).toLocaleString()
              )}
            </div>
            <span className="summary-card-subtext">Currently active</span>
          </div>
          <img
            className="summary-card-art"
            src={activeEnrollmentsImg || "/image/active-enrollments.png"}
            alt=""
            aria-hidden="true"
          />
        </div>

        {/* Card 3: Pending Enrollments */}
        <div className="summary-card summary-card-amber">
          <div className="summary-card-content">
            <div className="summary-card-top">
              <div className="summary-badge-icon summary-badge-amber">
                <Clock size={16} />
              </div>
              <span className="summary-card-title">Pending Enrollments</span>
            </div>
            <div className="summary-card-value">
              {summaryLoading ? (
                <span className="summary-skeleton" />
              ) : (
                (summaryData?.pending_enrollments ?? 0).toLocaleString()
              )}
            </div>
            <span className="summary-card-subtext">Awaiting enrollment</span>
          </div>
          <img
            className="summary-card-art"
            src={pendingEnrollmentsImg || "/image/pending-enrollments.png"}
            alt=""
            aria-hidden="true"
          />
        </div>

        {/* Card 4: Student Groups */}
        <div className="summary-card summary-card-purple">
          <div className="summary-card-content">
            <div className="summary-card-top">
              <div className="summary-badge-icon summary-badge-purple">
                <Users size={16} />
              </div>
              <span className="summary-card-title">Student Groups</span>
            </div>
            <div className="summary-card-value">
              {summaryLoading ? (
                <span className="summary-skeleton" />
              ) : (
                (summaryData?.total_groups ?? studentGroups.length).toLocaleString()
              )}
            </div>
            <span className="summary-card-subtext">Program / semester / section</span>
          </div>
          <img
            className="summary-card-art"
            src={studentGroupsImg || "/image/student-groups.png"}
            alt=""
            aria-hidden="true"
          />
        </div>
      </div>

      {/* Summary Error banner if API fails */}
      {summaryError && (
        <div className="feedback-banner feedback-error">
          <AlertCircle size={18} />
          <span>{summaryError}</span>
          <button
            type="button"
            className="select-all-btn"
            style={{ marginLeft: "auto" }}
            onClick={loadSummaryAndGroups}
          >
            Retry
          </button>
        </div>
      )}

      {/* 3. Main Content Tabs */}
      <div className="content-nav-tabs-wrapper" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "groups"}
          className={`content-nav-tab ${activeTab === "groups" ? "active" : ""}`}
          onClick={() => setActiveTab("groups")}
        >
          <Users size={16} />
          By Student Group
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "records"}
          className={`content-nav-tab ${activeTab === "records" ? "active" : ""}`}
          onClick={() => setActiveTab("records")}
        >
          <FileText size={16} />
          Enrollment Records
        </button>
      </div>

      {/* 4. Tab 1: BY STUDENT GROUP TAB (Default View) */}
      {activeTab === "groups" && (
        <div className="groups-section">
          {/* Section Header */}
          <div className="groups-section-header">
            <div>
              <h2>Student Groups</h2>
              <p>Choose a group to manage its course enrollments.</p>
            </div>
            <button
              type="button"
              className="primary-add-btn"
              onClick={handleOpenAddEnrollment}
            >
              <Plus size={16} />
              Add Enrollment
            </button>
          </div>

          {/* Filter Bar */}
          <div className="groups-filters-container">
            <div className="groups-search-input-wrapper">
              <Search className="groups-search-icon" size={18} />
              <input
                type="text"
                className="groups-search-input"
                placeholder="Search program, batch, or section..."
                value={groupSearchQuery}
                onChange={(e) => setGroupSearchQuery(e.target.value)}
              />
            </div>
            <div className="groups-dropdown-filters">
              <select
                className="groups-select"
                value={selectedBatchFilter}
                onChange={(e) => setSelectedBatchFilter(e.target.value)}
              >
                <option value="ALL">All batches</option>
                {availableGroupBatches.map((b) => (
                  <option key={b} value={b}>
                    Batch {b}
                  </option>
                ))}
              </select>

              <select
                className="groups-select"
                value={selectedSemesterFilter}
                onChange={(e) => setSelectedSemesterFilter(e.target.value)}
              >
                <option value="ALL">All semesters</option>
                {availableGroupSemesters.map((s) => (
                  <option key={s} value={s}>
                    Semester {s}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Group Cards List */}
          {summaryLoading && studentGroups.length === 0 ? (
            <div style={{ textAlign: "center", padding: "40px 0", color: "#64748b" }}>
              <RotateCw className="spinning" size={24} style={{ marginBottom: "8px" }} />
              <p>Loading student groups...</p>
            </div>
          ) : filteredStudentGroups.length === 0 ? (
            <div style={{ textAlign: "center", padding: "48px 0", color: "#64748b" }}>
              <Users size={36} style={{ color: "#cbd5e1", marginBottom: "12px" }} />
              <p style={{ fontWeight: 600, color: "#1e293b", margin: "0 0 4px 0" }}>
                No student groups match your filters
              </p>
              <p style={{ fontSize: "13.5px", margin: 0 }}>
                Try adjusting the search query or selecting "All batches" / "All semesters".
              </p>
            </div>
          ) : (
            <div className="groups-cards-list">
              {filteredStudentGroups.map((group) => {
                const isComplete = group.status === "Complete";
                return (
                  <div key={group.group_id} className="student-group-card">
                    {/* Header */}
                    <div className="group-card-top-row">
                      <div className="group-card-header-left">
                        <div className="group-card-avatar">
                          <GraduationCap size={22} />
                        </div>
                        <div>
                          <h3 className="group-card-title">
                            {group.department_code} · Section {group.section}
                          </h3>
                          <p className="group-card-subtitle">
                            Batch {group.cohort || group.batch} · Semester {group.semester}
                          </p>
                          <p className="group-card-subtitle">
                            Academic year {formatAcademicYear(group.academic_year, group.semester)}
                          </p>
                        </div>
                      </div>
                      <span className={isComplete ? "badge-complete" : "badge-incomplete"}>
                        {isComplete ? <Check size={13} className="badge-icon" /> : <Clock size={13} className="badge-icon" />}
                        {isComplete ? "Complete" : "Incomplete"}
                      </span>
                    </div>

                    {/* Metrics and Manage Group Action */}
                    <div className="group-card-bottom-row">
                      <div className="group-card-metrics-grid">
                        <div className="group-metric-col">
                          <span className="group-metric-label">Students</span>
                          <span className="group-metric-value">{group.total_students}</span>
                        </div>
                        <div className="group-metric-col">
                          <span className="group-metric-label">Enrolled</span>
                          <span className="group-metric-value">{group.enrolled_students}</span>
                        </div>
                        <div className="group-metric-col">
                          <span className="group-metric-label">Courses</span>
                          <span className="group-metric-value">{group.courses_count}</span>
                        </div>
                      </div>

                      <div className="group-card-action-wrapper">
                        {group.pending_students > 0 && (
                          <span className="pending-count-text has-pending">
                            {group.pending_students} student{group.pending_students === 1 ? "" : "s"} pending
                          </span>
                        )}
                        <button
                          type="button"
                          className="manage-group-btn"
                          onClick={() => handleManageGroup(group)}
                        >
                          Manage Group <ArrowRight size={14} />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* 5. Tab 2: ENROLLMENT RECORDS TAB */}
      {activeTab === "records" && (
        <div className="records-tab-container">
          {/* Filters Bar */}
          <div className="records-filter-bar">
            <div className="records-search-group">
              <div className="groups-search-input-wrapper" style={{ flex: 1 }}>
                <Search className="groups-search-icon" size={16} />
                <input
                  type="text"
                  className="groups-search-input"
                  placeholder="Search by student name, enrollment no, course code..."
                  value={recordSearchQuery}
                  onChange={(e) => {
                    setRecordSearchQuery(e.target.value);
                    setRecordsPage(1);
                  }}
                />
              </div>

              <select
                className="groups-select"
                value={recordStatusFilter}
                onChange={(e) => {
                  setRecordStatusFilter(e.target.value);
                  setRecordsPage(1);
                }}
              >
                <option value="ALL">All Statuses</option>
                <option value="ACTIVE">ACTIVE</option>
                <option value="DROPPED">DROPPED</option>
              </select>

              <select
                className="groups-select"
                value={recordSemesterFilter}
                onChange={(e) => {
                  setRecordSemesterFilter(e.target.value);
                  setRecordsPage(1);
                }}
              >
                <option value="ALL">All Semesters</option>
                {[1, 2, 3, 4, 5, 6, 7, 8].map((s) => (
                  <option key={s} value={String(s)}>
                    Semester {s}
                  </option>
                ))}
              </select>

              <select
                className="groups-select"
                value={recordSectionFilter}
                onChange={(e) => {
                  setRecordSectionFilter(e.target.value);
                  setRecordsPage(1);
                }}
              >
                <option value="ALL">All Sections</option>
                {["A", "B", "C", "D"].map((sec) => (
                  <option key={sec} value={sec}>
                    Section {sec}
                  </option>
                ))}
              </select>
            </div>

            <div className="records-actions-group">
              <button
                type="button"
                className="select-all-btn"
                onClick={loadEnrollmentRecords}
                disabled={recordsLoading}
              >
                <RotateCw size={14} className={recordsLoading ? "spinning" : ""} /> Refresh
              </button>
            </div>
          </div>

          {recordsError && (
            <div className="feedback-banner feedback-error">
              <AlertCircle size={16} />
              <span>{recordsError}</span>
            </div>
          )}

          {/* Table */}
          <div className="records-table-container">
            <table className="records-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Student Name</th>
                  <th>Enrollment No</th>
                  <th>Program</th>
                  <th>Batch</th>
                  <th>Academic Year</th>
                  <th>Sem</th>
                  <th>Sec</th>
                  <th>Course Code & Name</th>
                  <th>Enrolled Date</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {recordsLoading ? (
                  <tr>
                    <td colSpan={12} style={{ textAlign: "center", padding: "32px 0" }}>
                      Loading enrollment records...
                    </td>
                  </tr>
                ) : paginatedRecords.length === 0 ? (
                  <tr>
                    <td colSpan={12} style={{ textAlign: "center", padding: "40px 0", color: "#64748b" }}>
                      No enrollment records found matching your filters.
                    </td>
                  </tr>
                ) : (
                  paginatedRecords.map((rec) => (
                    <tr key={rec.enrollment_id}>
                      <td>#{rec.enrollment_id}</td>
                      <td className="table-student-name">{rec.student_name || "N/A"}</td>
                      <td>{rec.enrollment_no || "N/A"}</td>
                      <td>{rec.department_code || "CSE"}</td>
                      <td>{rec.batch_name || "N/A"}</td>
                      <td>{formatAcademicYear(rec.academic_year, rec.semester)}</td>
                      <td>{rec.semester ?? "N/A"}</td>
                      <td>{rec.section || "N/A"}</td>
                      <td>
                        <div className="table-course-code">{rec.course_code || "N/A"}</div>
                        <div className="table-course-name">{rec.course_name || ""}</div>
                      </td>
                      <td>
                        {rec.enrolled_at
                          ? new Date(rec.enrolled_at).toLocaleDateString()
                          : "N/A"}
                      </td>
                      <td>
                        <span
                          className={
                            rec.status === "ACTIVE" ? "badge-complete" : "badge-incomplete"
                          }
                        >
                          {rec.status}
                        </span>
                      </td>
                      <td>
                        <button
                          type="button"
                          className="delete-action-btn"
                          title="Remove enrollment"
                          onClick={() => setDeletingRecord(rec)}
                        >
                          <Trash2 size={14} />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {filteredRecords.length > 0 && (
            <div className="records-pagination-container">
              <span>
                Showing {(currentRecordsPage - 1) * RECORDS_PER_PAGE + 1}–
                {Math.min(currentRecordsPage * RECORDS_PER_PAGE, filteredRecords.length)} of{" "}
                {filteredRecords.length} records
              </span>
              <div className="pagination-controls">
                <button
                  type="button"
                  className="page-btn"
                  disabled={currentRecordsPage <= 1}
                  onClick={() => setRecordsPage((p) => Math.max(1, p - 1))}
                >
                  Previous
                </button>
                <span className="page-btn active">{currentRecordsPage}</span>
                <button
                  type="button"
                  className="page-btn"
                  disabled={currentRecordsPage >= totalRecordsPages}
                  onClick={() => setRecordsPage((p) => Math.min(totalRecordsPages, p + 1))}
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 6. Locked Add Enrollment & Manage Group Modal (Screenshot 3) */}
      {isModalOpen && (
        <div className="management-modal-overlay" onClick={() => setIsModalOpen(false)}>
          <div className="management-modal-card" onClick={(e) => e.stopPropagation()}>
            {/* Modal Header */}
            <div className="management-modal-header">
              <div>
                <h2>Course Enrollment Management</h2>
                <p>Manage student enrollments by batch, semester, section, and curriculum.</p>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setIsModalOpen(false)}
              >
                <X size={20} />
              </button>
            </div>

            {/* Top 4 Mini Statistics (Screenshot 3) */}
            <div className="modal-mini-stats-grid">
              <div className="modal-mini-stat-box">
                <div className="modal-mini-stat-label">Eligible Students</div>
                <div className="modal-mini-stat-value">
                  {previewLoading ? "..." : (previewData?.eligible_students ?? 0)}
                </div>
              </div>
              <div className="modal-mini-stat-box">
                <div className="modal-mini-stat-label">Already Enrolled</div>
                <div className="modal-mini-stat-value enrolled-color">
                  {previewLoading ? "..." : (previewData?.already_enrolled ?? 0)}
                </div>
              </div>
              <div className="modal-mini-stat-box">
                <div className="modal-mini-stat-label">Pending Enrollment</div>
                <div className="modal-mini-stat-value pending-color">
                  {previewLoading ? "..." : (previewData?.pending_enrollment ?? 0)}
                </div>
              </div>
              <div className="modal-mini-stat-box">
                <div className="modal-mini-stat-label">Available Courses</div>
                <div className="modal-mini-stat-value">
                  {previewLoading ? "..." : (previewData?.available_courses ?? 0)}
                </div>
              </div>
            </div>

            {/* Alerts */}
            {enrollmentSuccessMessage && (
              <div className="feedback-banner feedback-success">
                <Check size={18} />
                <span>{enrollmentSuccessMessage}</span>
              </div>
            )}
            {enrollmentErrorMessage && (
              <div className="feedback-banner feedback-error">
                <AlertCircle size={18} />
                <span>{enrollmentErrorMessage}</span>
              </div>
            )}
            {previewError && (
              <div className="feedback-banner feedback-warning">
                <AlertCircle size={18} />
                <span>{previewError}</span>
              </div>
            )}

            {/* Step 1. Select Student Group */}
            <div className="wizard-section">
              <h3 className="wizard-section-title">1. Select Student Group</h3>

              <div className="form-field-group">
                <label htmlFor="modal-dept-select">Degree / Program</label>
                <select
                  id="modal-dept-select"
                  value={formGroup.department_id}
                  onChange={(e) => handleFormChange("department_id", e.target.value)}
                >
                  <option value="">Select Degree / Program</option>
                  {departments.map((d) => (
                    <option key={d.department_id} value={d.department_id}>
                      {d.department_code} — {d.department_name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-grid-2col">
                <div className="form-field-group">
                  <label htmlFor="modal-batch-select">Admission Batch</label>
                  <select
                    id="modal-batch-select"
                    value={normalizeBatchCohort(formGroup.batch_year, batches)}
                    onChange={(e) => handleFormChange("batch_year", e.target.value)}
                  >
                    <option value="">Select Batch</option>
                    {batches.length > 0 ? (
                      batches.map((b) => (
                        <option key={b.batch_id} value={b.batch_name}>
                          {b.batch_name} Batch
                        </option>
                      ))
                    ) : (
                      ["2023-2027", "2024-2028", "2025-2029", "2026-2030"].map((y) => (
                        <option key={y} value={y}>
                          {y} Batch
                        </option>
                      ))
                    )}
                  </select>
                </div>

                <div className="form-field-group">
                  <label htmlFor="modal-ay-select">Academic Year</label>
                  <select
                    id="modal-ay-select"
                    value={formGroup.academic_year}
                    onChange={(e) => handleFormChange("academic_year", e.target.value)}
                  >
                    {getAcademicYearOptions().map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="form-grid-2col">
                <div className="form-field-group">
                  <label htmlFor="modal-sem-select">Semester</label>
                  <select
                    id="modal-sem-select"
                    value={formGroup.semester}
                    onChange={(e) => handleFormChange("semester", e.target.value)}
                  >
                    <option value="">Select Semester</option>
                    {[1, 2, 3, 4, 5, 6, 7, 8].map((s) => (
                      <option key={s} value={String(s)}>
                        Semester {s}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-field-group">
                  <label htmlFor="modal-sec-select">Section</label>
                  <select
                    id="modal-sec-select"
                    value={formGroup.section}
                    onChange={(e) => handleFormChange("section", e.target.value)}
                  >
                    <option value="">Select Section</option>
                    {["A", "B", "C", "D"].map((sec) => (
                      <option key={sec} value={sec}>
                        Section {sec}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Selected Group Preview Box (Screenshot 3) */}
              <div className="selected-group-preview-box">
                <div className="selected-group-preview-tag">Selected group</div>
                <div className="selected-group-preview-title">
                  {departments.find((d) => String(d.department_id) === String(formGroup.department_id))
                    ?.department_code || "Program"}{" "}
                  · Batch {normalizeBatchCohort(formGroup.batch_year, batches) || "YYYY"} · Semester {formGroup.semester || "S"} · Section{" "}
                  {formGroup.section || "Sec"}
                </div>
                <div className="selected-group-preview-sub">
                  Academic year {formGroup.academic_year || "YYYY–YYYY"}
                </div>
                <div className="selected-group-preview-sub" style={{ marginTop: "4px", fontSize: "12px", color: "#94a3b8" }}>
                  Actual student counts and course eligibility loaded from backend.
                </div>
              </div>
            </div>

            {/* Step 2. Assign Courses to This Group (Screenshot 3) */}
            <div className="wizard-section">
              <h3 className="wizard-section-title">2. Assign Courses to This Group</h3>
              <p className="wizard-section-subtitle">
                Select the courses that belong to this section's curriculum.
              </p>

              <div className="courses-header-row">
                <span className="courses-header-title">Available courses</span>
                <span className="courses-header-count">
                  {selectedCourseIds.length} selected
                </span>
              </div>

              {/* Courses List */}
              <div className="available-courses-list">
                {previewLoading ? (
                  <p style={{ color: "#64748b", fontSize: "13px" }}>Loading curriculum courses...</p>
                ) : (previewData?.courses || []).length === 0 ? (
                  <p style={{ color: "#64748b", fontSize: "13.5px" }}>
                    No active courses found for this group and semester.
                  </p>
                ) : (
                  (previewData?.courses || []).map((course) => {
                    const isSelected = selectedCourseIds.includes(course.course_id);
                    return (
                      <div
                        key={course.course_id}
                        className={`course-select-card ${isSelected ? "selected" : ""}`}
                        onClick={() => toggleCourseSelection(course.course_id)}
                      >
                        <div className="course-card-left">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => {}} // Controlled by card click
                            style={{ cursor: "pointer", width: "16px", height: "16px" }}
                          />
                          <div className="course-card-details">
                            <span className="course-card-name">{course.course_name}</span>
                            <span className="course-card-meta">
                              {course.course_code} · {course.credits} credit{course.credits === 1 ? "" : "s"}
                            </span>
                          </div>
                        </div>
                        {isSelected && (
                          <span className="course-selected-pill">Selected</span>
                        )}
                      </div>
                    );
                  })
                )}
              </div>

              {/* Courses Footer with Select All */}
              {(previewData?.courses || []).length > 0 && (
                <div className="courses-footer-row">
                  <span style={{ fontSize: "13px", color: "#64748b" }}>
                    {selectedCourseIds.length} courses selected
                  </span>
                  <button
                    type="button"
                    className="select-all-btn"
                    onClick={handleToggleSelectAllCourses}
                  >
                    {selectedCourseIds.length === (previewData?.courses || []).length
                      ? "Deselect all"
                      : "Select all"}
                  </button>
                </div>
              )}
            </div>

            {/* Step 3. Review Students (Screenshot 3) */}
            <div className="wizard-section">
              <h3 className="wizard-section-title">3. Review Students</h3>

              {/* Sub-Tabs: Pending, Enrolled, All Students */}
              <div className="student-review-tabs">
                <button
                  type="button"
                  className={`student-sub-tab ${studentFilterTab === "PENDING" ? "active" : ""}`}
                  onClick={() => setStudentFilterTab("PENDING")}
                >
                  Pending (
                  {(previewData?.students || []).filter((s) => !s.is_enrolled).length}
                  )
                </button>
                <button
                  type="button"
                  className={`student-sub-tab ${studentFilterTab === "ENROLLED" ? "active" : ""}`}
                  onClick={() => setStudentFilterTab("ENROLLED")}
                >
                  Enrolled (
                  {(previewData?.students || []).filter((s) => s.is_enrolled).length}
                  )
                </button>
                <button
                  type="button"
                  className={`student-sub-tab ${studentFilterTab === "ALL" ? "active" : ""}`}
                  onClick={() => setStudentFilterTab("ALL")}
                >
                  All Students ({(previewData?.students || []).length})
                </button>
              </div>

              {/* Student Review List */}
              <div className="students-review-card-list">
                {previewLoading ? (
                  <p style={{ padding: "16px", color: "#64748b", fontSize: "13px" }}>
                    Loading students...
                  </p>
                ) : displayedStudents.length === 0 ? (
                  <p style={{ padding: "16px", color: "#64748b", fontSize: "13px" }}>
                    No students in this tab category.
                  </p>
                ) : (
                  displayedStudents.map((stu) => {
                    const isSelected = selectedStudentIds.includes(stu.student_id);
                    return (
                      <div key={stu.student_id} className="student-review-item">
                        <div className="student-review-item-left">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleStudentSelection(stu.student_id)}
                            style={{ cursor: "pointer", width: "16px", height: "16px" }}
                          />
                          <div>
                            <div className="student-review-name">{stu.name}</div>
                            <div className="student-review-meta">
                              {stu.enrollment_no} · {stu.is_enrolled ? "Enrolled in section" : "Awaiting registration"}
                            </div>
                          </div>
                        </div>
                        <span
                          className={
                            stu.is_enrolled ? "badge-complete" : "badge-incomplete"
                          }
                        >
                          {stu.is_enrolled ? "Enrolled" : "Pending"}
                        </span>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Bottom Modal Actions */}
            <div className="modal-bottom-actions">
              <button
                type="button"
                className="modal-cancel-btn"
                onClick={() => setIsModalOpen(false)}
                disabled={submittingEnrollment}
              >
                Cancel
              </button>
              <button
                type="button"
                className="modal-confirm-enroll-btn"
                onClick={handleConfirmEnrollment}
                disabled={
                  submittingEnrollment ||
                  selectedCourseIds.length === 0 ||
                  selectedStudentIds.length === 0
                }
              >
                {submittingEnrollment ? (
                  <>
                    <RotateCw className="spinning" size={16} /> Enrolling...
                  </>
                ) : (
                  `Enroll ${selectedStudentIds.length} Student${selectedStudentIds.length === 1 ? "" : "s"}`
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 7. Delete Confirmation Safeguard Modal */}
      {deletingRecord && (
        <div className="confirm-modal-overlay" onClick={() => setDeletingRecord(null)}>
          <div className="confirm-modal-card" onClick={(e) => e.stopPropagation()}>
            <h3>Remove Enrollment Record?</h3>
            <p>
              Are you sure you want to remove the enrollment for{" "}
              <strong>{deletingRecord.student_name}</strong> in course{" "}
              <strong>{deletingRecord.course_code}</strong>? This does not delete the student account.
            </p>
            <div className="confirm-modal-actions">
              <button
                type="button"
                className="modal-cancel-btn"
                onClick={() => setDeletingRecord(null)}
                disabled={deleteLoading}
              >
                Cancel
              </button>
              <button
                type="button"
                className="delete-action-btn"
                style={{ padding: "8px 16px", fontWeight: 600 }}
                onClick={confirmDeleteRecord}
                disabled={deleteLoading}
              >
                {deleteLoading ? "Removing..." : "Confirm Removal"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
