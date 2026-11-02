import { useCallback, useEffect, useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faAward,
  faCheck,
  faChevronLeft,
  faChevronRight,
  faCircleCheck,
  faCircleExclamation,
  faClock,
  faEye,
  faFileLines,
  faFilter,
  faGraduationCap,
  faHistory,
  faPaperPlane,
  faPenToSquare,
  faPlus,
  faRotateLeft,
  faRotateRight,
  faShieldHalved,
  faSpinner,
  faTriangleExclamation,
  faUpload,
  faUserTie,
  faXmark,
} from "@fortawesome/free-solid-svg-icons";

import {
  getAdminResultsFilters,
  getAdminResultsOverview,
  getAdminSubmissions,
  getAdminSubmissionDetails,
  approveSubmission,
  returnSubmission,
  publishSubmission,
  recordResultCorrection,
  getAdminAuditHistory,
  createAssessment,
} from "../../services/adminAcademicResultsService";
import PageState from "../../components/PageState";
import "./AcademicResults.css";

export default function AcademicResults() {
  // Page data states
  const [loading, setLoading] = useState(true);
  const [tableLoading, setTableLoading] = useState(false);
  const [error, setError] = useState(null);

  // Filters and options
  const [filterOptions, setFilterOptions] = useState({
    academic_years: [],
    semesters: [],
    departments: [],
    courses: [],
    faculty: [],
    statuses: [],
  });

  const [filters, setFilters] = useState({
    academic_year: "all",
    semester: "all",
    department_id: "all",
    course_id: "all",
    faculty_id: "all",
    status: "all",
  });

  // Overview metrics
  const [overview, setOverview] = useState({
    cards: {
      pending_reviews: 0,
      submitted_results: 0,
      published_results: 0,
      returned_corrections: 0,
      draft_results: 0,
    },
    stats: {
      total_submissions: 0,
      total_students_evaluated: 0,
      passed_students: 0,
      overall_pass_rate: 0,
      average_marks: 0,
    },
  });

  // Submissions list & pagination
  const [submissions, setSubmissions] = useState([]);
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 10,
    total_count: 0,
    total_pages: 1,
  });

  // Modals state
  const [reviewModalOpen, setReviewModalOpen] = useState(false);
  const [selectedSubmission, setSelectedSubmission] = useState(null);
  const [reviewLoading, setReviewLoading] = useState(false);

  const [returnDialogOpen, setReturnDialogOpen] = useState(false);
  const [returnReason, setReturnReason] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  const [publishDialogOpen, setPublishDialogOpen] = useState(false);
  const [submissionToPublish, setSubmissionToPublish] = useState(null);

  const [correctionModalOpen, setCorrectionModalOpen] = useState(false);
  const [selectedResultForCorrection, setSelectedResultForCorrection] = useState(null);
  const [correctionForm, setCorrectionForm] = useState({ new_marks: "", reason: "" });

  const [auditModalOpen, setAuditModalOpen] = useState(false);
  const [auditEvents, setAuditEvents] = useState([]);
  const [auditLoading, setAuditLoading] = useState(false);

  const [createAssessmentModalOpen, setCreateAssessmentModalOpen] = useState(false);
  const [assessmentForm, setAssessmentForm] = useState({
    offering_id: "",
    assessment_name: "End-Semester Examination",
    assessment_type: "FINAL",
    max_marks: 100,
    weightage: 100,
  });

  const [toastMessage, setToastMessage] = useState(null);

  const showToast = (message, type = "success") => {
    setToastMessage({ message, type });
    setTimeout(() => setToastMessage(null), 4500);
  };

  // 1. Initial Load of Filter Options and Overview
  useEffect(() => {
    let active = true;

    async function initPage() {
      setLoading(true);
      setError(null);
      try {
        const [filtersRes, overviewRes] = await Promise.all([
          getAdminResultsFilters(),
          getAdminResultsOverview(),
        ]);

        if (active) {
          if (filtersRes?.success && filtersRes.data) {
            setFilterOptions(filtersRes.data);
          }
          if (overviewRes?.success && overviewRes.data) {
            setOverview(overviewRes.data);
          }
        }
      } catch (err) {
        if (active) {
          console.error("Error loading academic results:", err);
          setError(err?.response?.data?.message || "Failed to load academic results configuration.");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    initPage();

    return () => {
      active = false;
    };
  }, []);

  // 2. Fetch Submissions with Filters & Pagination
  const fetchSubmissions = useCallback(async (page = 1) => {
    setTableLoading(true);
    try {
      const params = {
        page,
        limit: pagination.limit,
        academic_year: filters.academic_year !== "all" ? filters.academic_year : undefined,
        semester: filters.semester !== "all" ? Number(filters.semester) : undefined,
        department_id: filters.department_id !== "all" ? Number(filters.department_id) : undefined,
        course_id: filters.course_id !== "all" ? Number(filters.course_id) : undefined,
        faculty_id: filters.faculty_id !== "all" ? Number(filters.faculty_id) : undefined,
        status: filters.status !== "all" ? filters.status : undefined,
      };

      const res = await getAdminSubmissions(params);
      if (res?.success && res.data) {
        setSubmissions(res.data.submissions || []);
        if (res.data.pagination) {
          setPagination(res.data.pagination);
        }
      }
    } catch (err) {
      console.error("Error fetching submissions:", err);
      showToast(err?.response?.data?.message || "Failed to load submissions", "error");
    } finally {
      setTableLoading(false);
    }
  }, [filters, pagination.limit]);

  useEffect(() => {
    let isMounted = true;

    const loadSubmissions = async () => {
      try {
        const params = {
          page: 1,
          limit: pagination.limit,
          academic_year: filters.academic_year !== "all" ? filters.academic_year : undefined,
          semester: filters.semester !== "all" ? Number(filters.semester) : undefined,
          department_id: filters.department_id !== "all" ? Number(filters.department_id) : undefined,
          course_id: filters.course_id !== "all" ? Number(filters.course_id) : undefined,
          faculty_id: filters.faculty_id !== "all" ? Number(filters.faculty_id) : undefined,
          status: filters.status !== "all" ? filters.status : undefined,
        };

        const res = await getAdminSubmissions(params);
        if (isMounted && res?.success && res.data) {
          setSubmissions(res.data.submissions || []);
          if (res.data.pagination) {
            setPagination(res.data.pagination);
          }
        }
      } catch (err) {
        if (isMounted) {
          console.error("Error fetching submissions:", err);
        }
      }
    };

    void loadSubmissions();

    return () => {
      isMounted = false;
    };
  }, [filters, pagination.limit]);

  // Handle Filter Changes
  const handleFilterChange = (field, value) => {
    setFilters((prev) => ({ ...prev, [field]: value }));
  };

  const handleResetFilters = () => {
    setFilters({
      academic_year: "all",
      semester: "all",
      department_id: "all",
      course_id: "all",
      faculty_id: "all",
      status: "all",
    });
  };

  // Open Review Details Modal
  const handleOpenReview = async (submissionId) => {
    setReviewLoading(true);
    setReviewModalOpen(true);
    try {
      const res = await getAdminSubmissionDetails(submissionId);
      if (res?.success && res.data) {
        setSelectedSubmission(res.data);
      }
    } catch (err) {
      console.error("Error loading submission details:", err);
      showToast(err?.response?.data?.message || "Failed to load submission details", "error");
      setReviewModalOpen(false);
    } finally {
      setReviewLoading(false);
    }
  };

  // Approve Submission
  const handleApprove = async (submissionId) => {
    setActionLoading(true);
    try {
      const res = await approveSubmission(submissionId, { remarks: "Approved by administration" });
      if (res?.success) {
        showToast(res.message || "Submission approved successfully");
        setReviewModalOpen(false);
        fetchSubmissions(pagination.page);
        // Refresh overview metrics
        getAdminResultsOverview().then((r) => r?.data && setOverview(r.data));
      }
    } catch (err) {
      console.error("Error approving submission:", err);
      showToast(err?.response?.data?.message || "Failed to approve submission", "error");
    } finally {
      setActionLoading(false);
    }
  };

  // Return Submission for Correction
  const handleReturn = async () => {
    if (!returnReason.trim()) {
      showToast("Please provide a reason to return the submission.", "error");
      return;
    }
    setActionLoading(true);
    try {
      const res = await returnSubmission(selectedSubmission.submission_id, { reason: returnReason.trim() });
      if (res?.success) {
        showToast(res.message || "Submission returned for correction");
        setReturnDialogOpen(false);
        setReturnReason("");
        setReviewModalOpen(false);
        fetchSubmissions(pagination.page);
        getAdminResultsOverview().then((r) => r?.data && setOverview(r.data));
      }
    } catch (err) {
      console.error("Error returning submission:", err);
      showToast(err?.response?.data?.message || "Failed to return submission", "error");
    } finally {
      setActionLoading(false);
    }
  };

  // Publish Submission
  const handlePublish = async () => {
    if (!submissionToPublish) return;
    setActionLoading(true);
    try {
      const res = await publishSubmission(submissionToPublish.submission_id);
      if (res?.success) {
        showToast(res.message || "Results published to Student Portal successfully!");
        setPublishDialogOpen(false);
        setSubmissionToPublish(null);
        setReviewModalOpen(false);
        fetchSubmissions(pagination.page);
        getAdminResultsOverview().then((r) => r?.data && setOverview(r.data));
      }
    } catch (err) {
      console.error("Error publishing submission:", err);
      showToast(err?.response?.data?.message || "Failed to publish submission", "error");
    } finally {
      setActionLoading(false);
    }
  };

  // Open Correction Modal
  const handleOpenCorrection = (studentResult) => {
    setSelectedResultForCorrection(studentResult);
    setCorrectionForm({
      new_marks: studentResult.marks_obtained !== null ? studentResult.marks_obtained : "",
      reason: "",
    });
    setCorrectionModalOpen(true);
  };

  // Submit Result Correction
  const handleSaveCorrection = async () => {
    if (correctionForm.new_marks === "" || !correctionForm.reason.trim()) {
      showToast("Please enter new marks and a required reason for the audit trail.", "error");
      return;
    }

    setActionLoading(true);
    try {
      const res = await recordResultCorrection({
        result_id: selectedResultForCorrection.result_id,
        new_marks: Number(correctionForm.new_marks),
        reason: correctionForm.reason.trim(),
      });

      if (res?.success) {
        showToast("Grade correction recorded successfully with audit history");
        setCorrectionModalOpen(false);
        // Refresh active review details
        if (selectedSubmission) {
          handleOpenReview(selectedSubmission.submission_id);
        }
        fetchSubmissions(pagination.page);
      }
    } catch (err) {
      console.error("Error recording correction:", err);
      showToast(err?.response?.data?.message || "Failed to record correction", "error");
    } finally {
      setActionLoading(false);
    }
  };

  // Open Audit History Modal
  const handleOpenAuditHistory = async () => {
    setAuditModalOpen(true);
    setAuditLoading(true);
    try {
      const res = await getAdminAuditHistory({ limit: 30 });
      if (res?.success && res.data) {
        setAuditEvents(res.data);
      }
    } catch (err) {
      console.error("Error loading audit history:", err);
    } finally {
      setAuditLoading(false);
    }
  };

  // Create Assessment
  const handleCreateAssessment = async (e) => {
    e.preventDefault();
    if (!assessmentForm.offering_id || !assessmentForm.assessment_name.trim()) {
      showToast("Course offering and assessment name are required", "error");
      return;
    }

    setActionLoading(true);
    try {
      const res = await createAssessment({
        offering_id: Number(assessmentForm.offering_id),
        assessment_name: assessmentForm.assessment_name.trim(),
        assessment_type: assessmentForm.assessment_type,
        max_marks: Number(assessmentForm.max_marks),
        weightage: Number(assessmentForm.weightage),
      });

      if (res?.success) {
        showToast("Assessment definition created successfully");
        setCreateAssessmentModalOpen(false);
        fetchSubmissions(1);
      }
    } catch (err) {
      console.error("Error creating assessment:", err);
      showToast(err?.response?.data?.message || "Failed to create assessment", "error");
    } finally {
      setActionLoading(false);
    }
  };

  // Format Status Badge
  const renderStatusBadge = (status) => {
    switch (status) {
      case "SUBMITTED":
        return <span className="status-pill pill-submitted">Submitted</span>;
      case "APPROVED":
        return <span className="status-pill pill-approved">Approved</span>;
      case "PUBLISHED":
        return <span className="status-pill pill-published">Published</span>;
      case "RETURNED":
        return <span className="status-pill pill-returned">Returned</span>;
      case "DRAFT":
      default:
        return <span className="status-pill pill-draft">Draft</span>;
    }
  };

  if (loading) {
    return (
      <div className="admin-results-page">
        <PageState type="loading" title="Loading Academic Results" message="Retrieving assessment submissions..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="admin-results-page">
        <PageState
          type="error"
          title="Unable to Load Academic Results"
          message={error}
          actionLabel="Try Again"
          onAction={() => window.location.reload()}
        />
      </div>
    );
  }

  return (
    <div className="admin-results-page">
      {/* Toast Notification */}
      {toastMessage && (
        <div className={`admin-toast toast-${toastMessage.type}`} role="status">
          <FontAwesomeIcon icon={toastMessage.type === "success" ? faCheck : faCircleExclamation} />
          <span>{toastMessage.message}</span>
        </div>
      )}

      {/* A. Page Header Banner */}
      <header className="results-header-banner">
        <div className="results-header-left">
          <div className="results-header-icon">
            <FontAwesomeIcon icon={faAward} />
          </div>
          <div>
            <h1 className="results-header-title">Academic Results</h1>
            <p className="results-header-subtitle">
              Manage assessments, review faculty submissions, approve results, and control publication.
            </p>
          </div>
        </div>

        <div className="results-header-actions">
          <button
            type="button"
            className="btn-header-secondary"
            onClick={handleOpenAuditHistory}
            aria-label="View Audit History"
          >
            <FontAwesomeIcon icon={faHistory} />
            <span>Audit History</span>
          </button>

          <button
            type="button"
            className="btn-header-primary"
            onClick={() => setCreateAssessmentModalOpen(true)}
            aria-label="Create New Assessment"
          >
            <FontAwesomeIcon icon={faPlus} />
            <span>New Assessment</span>
          </button>
        </div>
      </header>

      {/* B. Summary Cards (4 Cards) */}
      <section className="results-cards-grid" aria-label="Operational Summary Cards">
        {/* Card 1: Pending Reviews */}
        <div className="results-kpi-card card-pending">
          <div className="kpi-card-header">
            <div className="kpi-icon-box icon-amber">
              <FontAwesomeIcon icon={faClock} />
            </div>
            <div className="kpi-card-titles">
              <span className="kpi-label">Pending Reviews</span>
              <strong className="kpi-value text-amber">{overview.cards.pending_reviews}</strong>
            </div>
          </div>
          <p className="kpi-subtext">Awaiting administrative review</p>
        </div>

        {/* Card 2: Submitted Results */}
        <div className="results-kpi-card card-submitted">
          <div className="kpi-card-header">
            <div className="kpi-icon-box icon-blue">
              <FontAwesomeIcon icon={faUpload} />
            </div>
            <div className="kpi-card-titles">
              <span className="kpi-label">Submitted Results</span>
              <strong className="kpi-value text-blue">{overview.cards.submitted_results}</strong>
            </div>
          </div>
          <p className="kpi-subtext">Active faculty submissions</p>
        </div>

        {/* Card 3: Published Results */}
        <div className="results-kpi-card card-published">
          <div className="kpi-card-header">
            <div className="kpi-icon-box icon-green">
              <FontAwesomeIcon icon={faCircleCheck} />
            </div>
            <div className="kpi-card-titles">
              <span className="kpi-label">Published Results</span>
              <strong className="kpi-value text-green">{overview.cards.published_results}</strong>
            </div>
          </div>
          <p className="kpi-subtext">Visible on Student Portal</p>
        </div>

        {/* Card 4: Returned for Correction */}
        <div className="results-kpi-card card-returned">
          <div className="kpi-card-header">
            <div className="kpi-icon-box icon-coral">
              <FontAwesomeIcon icon={faRotateLeft} />
            </div>
            <div className="kpi-card-titles">
              <span className="kpi-label">Returned for Correction</span>
              <strong className="kpi-value text-coral">{overview.cards.returned_corrections}</strong>
            </div>
          </div>
          <p className="kpi-subtext">Sent back to faculty</p>
        </div>
      </section>

      {/* C. Filters Section */}
      <section className="results-filter-card" aria-label="Filters">
        <div className="filter-header">
          <span className="filter-title">
            <FontAwesomeIcon icon={faFilter} className="filter-icon" />
            Filter Submissions
          </span>
          <button
            type="button"
            className="btn-reset-filters"
            onClick={handleResetFilters}
            aria-label="Reset Filters"
          >
            <FontAwesomeIcon icon={faRotateRight} />
            <span>Reset</span>
          </button>
        </div>

        <div className="filter-controls-grid">
          {/* Academic Year */}
          <div className="filter-control">
            <label htmlFor="filter-acad-year">Academic Year</label>
            <select
              id="filter-acad-year"
              value={filters.academic_year}
              onChange={(e) => handleFilterChange("academic_year", e.target.value)}
            >
              <option value="all">All Years</option>
              {filterOptions.academic_years.map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>
          </div>

          {/* Semester */}
          <div className="filter-control">
            <label htmlFor="filter-semester">Semester</label>
            <select
              id="filter-semester"
              value={filters.semester}
              onChange={(e) => handleFilterChange("semester", e.target.value)}
            >
              <option value="all">All Semesters</option>
              {filterOptions.semesters.map((s) => (
                <option key={s} value={s}>
                  Semester {s}
                </option>
              ))}
            </select>
          </div>

          {/* Department */}
          <div className="filter-control">
            <label htmlFor="filter-dept">Department</label>
            <select
              id="filter-dept"
              value={filters.department_id}
              onChange={(e) => handleFilterChange("department_id", e.target.value)}
            >
              <option value="all">All Departments</option>
              {filterOptions.departments.map((d) => (
                <option key={d.department_id} value={d.department_id}>
                  {d.department_code} – {d.department_name}
                </option>
              ))}
            </select>
          </div>

          {/* Course */}
          <div className="filter-control">
            <label htmlFor="filter-course">Course</label>
            <select
              id="filter-course"
              value={filters.course_id}
              onChange={(e) => handleFilterChange("course_id", e.target.value)}
            >
              <option value="all">All Courses</option>
              {filterOptions.courses.map((c) => (
                <option key={c.course_id} value={c.course_id}>
                  {c.course_code} – {c.course_name}
                </option>
              ))}
            </select>
          </div>

          {/* Faculty */}
          <div className="filter-control">
            <label htmlFor="filter-faculty">Faculty</label>
            <select
              id="filter-faculty"
              value={filters.faculty_id}
              onChange={(e) => handleFilterChange("faculty_id", e.target.value)}
            >
              <option value="all">All Faculty</option>
              {filterOptions.faculty.map((f) => (
                <option key={f.faculty_id} value={f.faculty_id}>
                  {f.name}
                </option>
              ))}
            </select>
          </div>

          {/* Status */}
          <div className="filter-control">
            <label htmlFor="filter-status">Status</label>
            <select
              id="filter-status"
              value={filters.status}
              onChange={(e) => handleFilterChange("status", e.target.value)}
            >
              {filterOptions.statuses.map((st) => (
                <option key={st.value} value={st.value}>
                  {st.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {/* D. Results Management Table */}
      <section className="results-table-card" aria-label="Submissions List">
        <div className="table-card-top">
          <div className="table-top-left">
            <h2 className="table-card-title">Assessment Submissions</h2>
            <span className="table-records-badge">
              {pagination.total_count} {pagination.total_count === 1 ? "record" : "records"}
            </span>
          </div>

          {tableLoading && (
            <div className="table-spinner">
              <FontAwesomeIcon icon={faSpinner} spin />
              <span>Updating...</span>
            </div>
          )}
        </div>

        {submissions.length > 0 ? (
          <div className="table-responsive">
            <table className="results-data-table">
              <thead>
                <tr>
                  <th>Course Code</th>
                  <th>Course Name</th>
                  <th>Department</th>
                  <th>Faculty</th>
                  <th>Assessment</th>
                  <th>Term</th>
                  <th className="th-center">Students</th>
                  <th className="th-center">Avg Marks</th>
                  <th className="th-center">Status</th>
                  <th className="th-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {submissions.map((sub) => (
                  <tr key={sub.submission_id} className="submission-row">
                    <td className="td-course-code">{sub.course_code}</td>
                    <td className="td-course-name">{sub.course_name}</td>
                    <td>{sub.department_code || sub.department_name}</td>
                    <td className="td-faculty-name">
                      <FontAwesomeIcon icon={faUserTie} className="faculty-icon" />
                      {sub.faculty_name}
                    </td>
                    <td>
                      <strong>{sub.assessment_name}</strong>
                      <small className="assessment-type-pill">{sub.assessment_type}</small>
                    </td>
                    <td>
                      <div>Sem {sub.semester}</div>
                      <small className="academic-year-sub">{sub.academic_year}</small>
                    </td>
                    <td className="td-center">
                      <span className="student-count-badge">
                        {sub.passed_count}/{sub.student_count}
                      </span>
                    </td>
                    <td className="td-center">
                      {sub.average_marks !== null ? `${sub.average_marks}` : "—"}
                    </td>
                    <td className="td-center">{renderStatusBadge(sub.status)}</td>
                    <td className="td-right">
                      <div className="actions-cluster">
                        <button
                          type="button"
                          className="btn-action-view"
                          onClick={() => handleOpenReview(sub.submission_id)}
                          aria-label={`Review ${sub.course_code}`}
                          title="Review submission details"
                        >
                          <FontAwesomeIcon icon={faEye} />
                          <span>Review</span>
                        </button>

                        {sub.status === "APPROVED" && (
                          <button
                            type="button"
                            className="btn-action-publish"
                            onClick={() => {
                              setSubmissionToPublish(sub);
                              setPublishDialogOpen(true);
                            }}
                            title="Publish results to student portal"
                          >
                            <FontAwesomeIcon icon={faPaperPlane} />
                            <span>Publish</span>
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="results-empty-state">
            <FontAwesomeIcon icon={faFileLines} className="empty-icon" />
            <h3>No Assessment Submissions Found</h3>
            <p>
              No faculty result submissions match the active filters. Faculty submit marks through the
              course offering workflow.
            </p>
          </div>
        )}

        {/* Pagination Controls */}
        {pagination.total_pages > 1 && (
          <div className="results-pagination-bar">
            <span className="pagination-info">
              Page {pagination.page} of {pagination.total_pages} ({pagination.total_count} total)
            </span>
            <div className="pagination-buttons">
              <button
                type="button"
                className="btn-page"
                disabled={pagination.page <= 1}
                onClick={() => fetchSubmissions(pagination.page - 1)}
              >
                <FontAwesomeIcon icon={faChevronLeft} />
                <span>Prev</span>
              </button>
              <button
                type="button"
                className="btn-page"
                disabled={pagination.page >= pagination.total_pages}
                onClick={() => fetchSubmissions(pagination.page + 1)}
              >
                <span>Next</span>
                <FontAwesomeIcon icon={faChevronRight} />
              </button>
            </div>
          </div>
        )}
      </section>

      {/* =======================================================
          MODAL E: REVIEW DETAILS MODAL
         ======================================================= */}
      {reviewModalOpen && (
        <div className="results-modal-backdrop" onClick={() => setReviewModalOpen(false)}>
          <div className="results-modal-container" onClick={(e) => e.stopPropagation()}>
            {reviewLoading || !selectedSubmission ? (
              <div className="modal-spinner-wrap">
                <FontAwesomeIcon icon={faSpinner} spin className="large-spinner" />
                <p>Loading submission records...</p>
              </div>
            ) : (
              <>
                <div className="results-modal-header">
                  <div>
                    <div className="modal-header-top">
                      <h3 className="modal-title">
                        {selectedSubmission.course.course_code} – {selectedSubmission.course.course_name}
                      </h3>
                      {renderStatusBadge(selectedSubmission.status)}
                    </div>
                    <p className="modal-subtitle">
                      {selectedSubmission.assessment.assessment_name} • Faculty: {selectedSubmission.faculty.name} •
                      Semester {selectedSubmission.semester} ({selectedSubmission.academic_year})
                    </p>
                  </div>
                  <button
                    type="button"
                    className="btn-modal-close"
                    onClick={() => setReviewModalOpen(false)}
                    aria-label="Close review"
                  >
                    <FontAwesomeIcon icon={faXmark} />
                  </button>
                </div>

                {/* Return reason banner if returned */}
                {selectedSubmission.review_remarks && selectedSubmission.status === "RETURNED" && (
                  <div className="returned-notice-banner">
                    <FontAwesomeIcon icon={faTriangleExclamation} />
                    <div>
                      <strong>Returned for Correction Reason:</strong>
                      <p>{selectedSubmission.review_remarks}</p>
                    </div>
                  </div>
                )}

                {/* Missing marks warning if any */}
                {selectedSubmission.summary.missing_count > 0 && (
                  <div className="warning-notice-banner">
                    <FontAwesomeIcon icon={faCircleExclamation} />
                    <span>
                      {selectedSubmission.summary.missing_count} enrolled students are missing marks for this
                      assessment.
                    </span>
                  </div>
                )}

                {/* KPI Summary strip */}
                <div className="modal-kpi-strip">
                  <div className="modal-kpi-item">
                    <span className="strip-label">Enrolled</span>
                    <strong className="strip-val">{selectedSubmission.summary.total_enrolled}</strong>
                  </div>
                  <div className="modal-kpi-item">
                    <span className="strip-label">Evaluated</span>
                    <strong className="strip-val">{selectedSubmission.summary.evaluated_count}</strong>
                  </div>
                  <div className="modal-kpi-item">
                    <span className="strip-label">Passed</span>
                    <strong className="strip-val text-green">{selectedSubmission.summary.passed_count}</strong>
                  </div>
                  <div className="modal-kpi-item">
                    <span className="strip-label">Failed</span>
                    <strong className="strip-val text-coral">{selectedSubmission.summary.failed_count}</strong>
                  </div>
                  <div className="modal-kpi-item">
                    <span className="strip-label">Average Marks</span>
                    <strong className="strip-val">
                      {selectedSubmission.summary.average_marks !== null
                        ? selectedSubmission.summary.average_marks
                        : "N/A"}
                    </strong>
                  </div>
                </div>

                {/* Student Marks Table */}
                <div className="modal-table-wrap">
                  <table className="modal-students-table">
                    <thead>
                      <tr>
                        <th>#</th>
                        <th>Enrollment No</th>
                        <th>Student Name</th>
                        <th className="th-center">Marks Obtained</th>
                        <th className="th-center">Max Marks</th>
                        <th className="th-center">Grade</th>
                        <th className="th-center">Grade Points</th>
                        <th className="th-center">Status</th>
                        <th className="th-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedSubmission.students.map((st) => (
                        <tr key={st.student_id} className={st.is_missing ? "missing-row" : ""}>
                          <td>{st.index}</td>
                          <td className="td-enr">{st.enrollment_no}</td>
                          <td>{st.student_name}</td>
                          <td className="td-center font-bold">
                            {st.marks_obtained !== null ? st.marks_obtained : "Missing"}
                          </td>
                          <td className="td-center">{st.max_marks}</td>
                          <td className="td-center font-bold">{st.grade}</td>
                          <td className="td-center">{st.grade_points.toFixed(1)}</td>
                          <td className="td-center">
                            <span
                              className={`academic-status-pill ${
                                st.status === "Pass" ? "status-pass" : "status-fail"
                              }`}
                            >
                              {st.status}
                            </span>
                          </td>
                          <td className="td-right">
                            {st.result_id && (
                              <button
                                type="button"
                                className="btn-table-correct"
                                onClick={() => handleOpenCorrection(st)}
                                title="Authorize Result Correction"
                              >
                                <FontAwesomeIcon icon={faPenToSquare} />
                                <span>Correct</span>
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Modal Footer Workflow Actions */}
                <div className="results-modal-footer">
                  <button
                    type="button"
                    className="btn-modal-cancel"
                    onClick={() => setReviewModalOpen(false)}
                  >
                    Close
                  </button>

                  <div className="modal-footer-workflow-buttons">
                    {selectedSubmission.status === "SUBMITTED" && (
                      <>
                        <button
                          type="button"
                          className="btn-modal-return"
                          onClick={() => setReturnDialogOpen(true)}
                          disabled={actionLoading}
                        >
                          <FontAwesomeIcon icon={faRotateLeft} />
                          <span>Return for Correction</span>
                        </button>

                        <button
                          type="button"
                          className="btn-modal-approve"
                          onClick={() => handleApprove(selectedSubmission.submission_id)}
                          disabled={actionLoading}
                        >
                          <FontAwesomeIcon icon={faCheck} />
                          <span>{actionLoading ? "Processing..." : "Approve Results"}</span>
                        </button>
                      </>
                    )}

                    {selectedSubmission.status === "APPROVED" && (
                      <button
                        type="button"
                        className="btn-modal-publish"
                        onClick={() => {
                          setSubmissionToPublish(selectedSubmission);
                          setPublishDialogOpen(true);
                        }}
                        disabled={actionLoading}
                      >
                        <FontAwesomeIcon icon={faPaperPlane} />
                        <span>Publish to Student Portal</span>
                      </button>
                    )}

                    {selectedSubmission.status === "PUBLISHED" && (
                      <span className="published-stamp-badge">
                        <FontAwesomeIcon icon={faCircleCheck} />
                        Published on {selectedSubmission.published_at?.slice(0, 10)}
                      </span>
                    )}
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* =======================================================
          MODAL F: RETURN FOR CORRECTION DIALOG
         ======================================================= */}
      {returnDialogOpen && (
        <div className="results-modal-backdrop small-backdrop" onClick={() => setReturnDialogOpen(false)}>
          <div className="dialog-box" onClick={(e) => e.stopPropagation()}>
            <div className="dialog-header">
              <FontAwesomeIcon icon={faRotateLeft} className="dialog-icon-coral" />
              <h3>Return Submission to Faculty</h3>
            </div>
            <p className="dialog-body-text">
              Please provide a clear explanation for returning this submission. The assigned faculty member will
              see this reason and revise the marks accordingly.
            </p>
            <div className="dialog-form-group">
              <label htmlFor="return-reason-input">Reason for return (Required)</label>
              <textarea
                id="return-reason-input"
                rows="4"
                placeholder="e.g. Missing assessment scores for student CSE2024005, please recheck and resubmit."
                value={returnReason}
                onChange={(e) => setReturnReason(e.target.value)}
              />
            </div>
            <div className="dialog-actions">
              <button
                type="button"
                className="btn-dialog-cancel"
                onClick={() => setReturnDialogOpen(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-dialog-confirm-return"
                onClick={handleReturn}
                disabled={actionLoading || !returnReason.trim()}
              >
                {actionLoading ? "Returning..." : "Confirm Return"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* =======================================================
          MODAL G: PUBLICATION CONFIRMATION DIALOG
         ======================================================= */}
      {publishDialogOpen && (
        <div className="results-modal-backdrop small-backdrop" onClick={() => setPublishDialogOpen(false)}>
          <div className="dialog-box" onClick={(e) => e.stopPropagation()}>
            <div className="dialog-header">
              <FontAwesomeIcon icon={faPaperPlane} className="dialog-icon-blue" />
              <h3>Publish Results to Student Portal</h3>
            </div>
            <p className="dialog-body-text">
              You are about to publish the approved results for:
            </p>
            <div className="publish-summary-card">
              <div>
                <strong>Course:</strong> {submissionToPublish?.course_code || submissionToPublish?.course?.course_code}
              </div>
              <div>
                <strong>Assessment:</strong> {submissionToPublish?.assessment_name || submissionToPublish?.assessment?.assessment_name}
              </div>
              <div>
                <strong>Term:</strong> Semester {submissionToPublish?.semester} ({submissionToPublish?.academic_year})
              </div>
            </div>
            <p className="dialog-warning-text">
              Once published, all evaluated students will immediately be able to view their verified marks,
              grades, GPA, and CGPA calculations on their portal.
            </p>
            <div className="dialog-actions">
              <button
                type="button"
                className="btn-dialog-cancel"
                onClick={() => setPublishDialogOpen(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-dialog-confirm-publish"
                onClick={handlePublish}
                disabled={actionLoading}
              >
                {actionLoading ? "Publishing..." : "Confirm & Publish"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* =======================================================
          MODAL H: RESULT CORRECTION MODAL
         ======================================================= */}
      {correctionModalOpen && selectedResultForCorrection && (
        <div className="results-modal-backdrop small-backdrop" onClick={() => setCorrectionModalOpen(false)}>
          <div className="dialog-box" onClick={(e) => e.stopPropagation()}>
            <div className="dialog-header">
              <FontAwesomeIcon icon={faPenToSquare} className="dialog-icon-blue" />
              <h3>Authorize Grade Correction</h3>
            </div>
            <p className="dialog-body-text">
              Correcting marks for <strong>{selectedResultForCorrection.student_name}</strong> (
              {selectedResultForCorrection.enrollment_no}). All changes are recorded in the institutional audit log.
            </p>

            <div className="correction-fields">
              <div className="dialog-form-group">
                <label>Current Marks</label>
                <input
                  type="text"
                  disabled
                  value={selectedResultForCorrection.marks_obtained !== null ? selectedResultForCorrection.marks_obtained : "N/A"}
                />
              </div>

              <div className="dialog-form-group">
                <label htmlFor="new-marks-input">New Marks (0 – 100)</label>
                <input
                  id="new-marks-input"
                  type="number"
                  min="0"
                  max="100"
                  step="0.5"
                  placeholder="e.g. 88.5"
                  value={correctionForm.new_marks}
                  onChange={(e) => setCorrectionForm((prev) => ({ ...prev, new_marks: e.target.value }))}
                />
              </div>

              <div className="dialog-form-group">
                <label htmlFor="correction-reason-input">Reason for Correction (Required for Audit Trail)</label>
                <textarea
                  id="correction-reason-input"
                  rows="3"
                  placeholder="e.g. Scrutiny re-evaluation approved by Dean of Academics."
                  value={correctionForm.reason}
                  onChange={(e) => setCorrectionForm((prev) => ({ ...prev, reason: e.target.value }))}
                />
              </div>
            </div>

            <div className="dialog-actions">
              <button
                type="button"
                className="btn-dialog-cancel"
                onClick={() => setCorrectionModalOpen(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-dialog-confirm-publish"
                onClick={handleSaveCorrection}
                disabled={actionLoading || correctionForm.new_marks === "" || !correctionForm.reason.trim()}
              >
                {actionLoading ? "Saving..." : "Save Correction"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* =======================================================
          MODAL I: AUDIT HISTORY TIMELINE MODAL
         ======================================================= */}
      {auditModalOpen && (
        <div className="results-modal-backdrop" onClick={() => setAuditModalOpen(false)}>
          <div className="audit-modal-container" onClick={(e) => e.stopPropagation()}>
            <div className="results-modal-header">
              <div className="modal-header-top">
                <FontAwesomeIcon icon={faShieldHalved} className="audit-shield-icon" />
                <h3 className="modal-title">Institutional Academic Audit History</h3>
              </div>
              <button
                type="button"
                className="btn-modal-close"
                onClick={() => setAuditModalOpen(false)}
                aria-label="Close audit"
              >
                <FontAwesomeIcon icon={faXmark} />
              </button>
            </div>

            <div className="audit-timeline-body">
              {auditLoading ? (
                <div className="modal-spinner-wrap">
                  <FontAwesomeIcon icon={faSpinner} spin className="large-spinner" />
                  <p>Loading audit timeline...</p>
                </div>
              ) : auditEvents.length > 0 ? (
                <div className="audit-timeline-list">
                  {auditEvents.map((evt) => (
                    <div key={evt.id} className="audit-timeline-item">
                      <div className="timeline-node">
                        <span className={`timeline-dot dot-${evt.type.toLowerCase()}`} />
                        <div className="timeline-line" />
                      </div>
                      <div className="timeline-content">
                        <div className="timeline-meta">
                          <span className="timeline-user">
                            {evt.actor_name} ({evt.actor_role})
                          </span>
                          <span className="timeline-time">
                            {evt.timestamp ? new Date(evt.timestamp).toLocaleString() : ""}
                          </span>
                        </div>
                        <p className="timeline-desc">{evt.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="results-empty-state">
                  <FontAwesomeIcon icon={faHistory} className="empty-icon" />
                  <p>No audit trail records logged yet.</p>
                </div>
              )}
            </div>

            <div className="results-modal-footer">
              <button
                type="button"
                className="btn-modal-cancel"
                onClick={() => setAuditModalOpen(false)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* =======================================================
          MODAL J: CREATE ASSESSMENT DEFINITION
         ======================================================= */}
      {createAssessmentModalOpen && (
        <div className="results-modal-backdrop small-backdrop" onClick={() => setCreateAssessmentModalOpen(false)}>
          <div className="dialog-box" onClick={(e) => e.stopPropagation()}>
            <div className="dialog-header">
              <FontAwesomeIcon icon={faGraduationCap} className="dialog-icon-blue" />
              <h3>Create Assessment Definition</h3>
            </div>
            <form onSubmit={handleCreateAssessment} className="assessment-create-form">
              <div className="dialog-form-group">
                <label htmlFor="assessment-offering-select">Course Offering (Required)</label>
                <select
                  id="assessment-offering-select"
                  value={assessmentForm.offering_id}
                  onChange={(e) => setAssessmentForm((p) => ({ ...p, offering_id: e.target.value }))}
                  required
                >
                  <option value="">Select a Course Offering</option>
                  {filterOptions.courses.map((c) => (
                    <option key={c.course_id} value={c.course_id}>
                      {c.course_code} – {c.course_name} (Sem {c.semester})
                    </option>
                  ))}
                </select>
              </div>

              <div className="dialog-form-group">
                <label htmlFor="assessment-name-input">Assessment Name (Required)</label>
                <input
                  id="assessment-name-input"
                  type="text"
                  placeholder="e.g. End-Semester Examination"
                  value={assessmentForm.assessment_name}
                  onChange={(e) => setAssessmentForm((p) => ({ ...p, assessment_name: e.target.value }))}
                  required
                />
              </div>

              <div className="form-row-2">
                <div className="dialog-form-group">
                  <label htmlFor="assessment-type-select">Type</label>
                  <select
                    id="assessment-type-select"
                    value={assessmentForm.assessment_type}
                    onChange={(e) => setAssessmentForm((p) => ({ ...p, assessment_type: e.target.value }))}
                  >
                    <option value="FINAL">Final Theory Exam</option>
                    <option value="MIDTERM">Midterm Assessment</option>
                    <option value="INTERNAL">Internal Evaluation</option>
                    <option value="PRACTICAL">Lab / Practical</option>
                  </select>
                </div>

                <div className="dialog-form-group">
                  <label htmlFor="assessment-max-marks">Maximum Marks</label>
                  <input
                    id="assessment-max-marks"
                    type="number"
                    min="10"
                    max="500"
                    value={assessmentForm.max_marks}
                    onChange={(e) => setAssessmentForm((p) => ({ ...p, max_marks: e.target.value }))}
                  />
                </div>
              </div>

              <div className="dialog-actions">
                <button
                  type="button"
                  className="btn-dialog-cancel"
                  onClick={() => setCreateAssessmentModalOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-dialog-confirm-publish"
                  disabled={actionLoading}
                >
                  {actionLoading ? "Creating..." : "Create Assessment"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
