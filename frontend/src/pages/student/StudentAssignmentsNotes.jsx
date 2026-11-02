import { useState, useEffect, useMemo, useCallback } from "react";
import {
  FileText,
  Clock,
  CheckCircle2,
  BookOpen,
  Search,
  Download,
  AlertCircle,
  X,
  RefreshCw,
  ChevronRight,
  ChevronLeft,
  MoreVertical,
  UploadCloud,
  FileCheck,
  Calendar,
  Award,
  ExternalLink,
} from "lucide-react";
import {
  getStudentAssignmentSummary,
  getStudentEnrolledClasses,
  getStudentAssignments,
  getStudentAssignmentDetail,
  downloadAssignmentAttachment,
  submitAssignment,
  getStudentSubmissions,
  downloadStudentSubmissionFile,
  getStudentNotes,
  downloadStudentNote,
  getStudentDeadlines,
  getStudentResults,
} from "../../services/studentAssignmentService";
import "./StudentAssignmentsNotes.css";

export default function StudentAssignmentsNotes() {
  // Active Tab: 'assignments' | 'submissions' | 'notes' | 'deadlines' | 'results'
  const [activeTab, setActiveTab] = useState("assignments");

  // Summary Cards State
  const [summary, setSummary] = useState({
    total_assignments: 0,
    pending_assignments: 0,
    submitted_assignments: 0,
    notes_available: 0,
    enrolled_classes_count: 0,
  });

  // Enrolled Classes / Subjects for dropdowns
  const [enrolledClasses, setEnrolledClasses] = useState([]);

  // Data lists
  const [assignments, setAssignments] = useState([]);
  const [submissions, setSubmissions] = useState([]);
  const [notes, setNotes] = useState([]);
  const [deadlines, setDeadlines] = useState([]);
  const [results, setResults] = useState([]);

  // Loading & Action State
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState(null); // { type: 'success' | 'error', text: '' }

  // Filters for Assignments Tab
  const [assignmentSearch, setAssignmentSearch] = useState("");
  const [assignmentClassFilter, setAssignmentClassFilter] = useState("all");
  const [assignmentStatusFilter, setAssignmentStatusFilter] = useState("all");
  const [assignmentPage, setAssignmentPage] = useState(1);
  const assignmentsPerPage = 6;

  // Filters for Notes Tab
  const [noteSearch, setNoteSearch] = useState("");
  const [noteClassFilter, setNoteClassFilter] = useState("all");
  const [noteCategoryFilter, setNoteCategoryFilter] = useState("all");
  const [notePage, setNotePage] = useState(1);
  const notesPerPage = 5;

  // Active Menu Dropdown for assignment action
  const [openActionMenuId, setOpenActionMenuId] = useState(null);

  // Modals state
  const [detailModalAssignment, setDetailModalAssignment] = useState(null);
  const [submitModalAssignment, setSubmitModalAssignment] = useState(null);
  const [submissionFeedbackModal, setSubmissionFeedbackModal] = useState(null);

  // Submission Form State
  const [submissionFile, setSubmissionFile] = useState(null);
  const [submissionText, setSubmissionText] = useState("");
  const [submissionConfirmed, setSubmissionConfirmed] = useState(false);
  const [isResubmitting, setIsResubmitting] = useState(false);

  // Auto-dismiss alert feedback
  useEffect(() => {
    if (feedbackMsg) {
      const timer = setTimeout(() => setFeedbackMsg(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [feedbackMsg]);

  // Main Dashboard Data Fetch
  const reloadData = useCallback(async () => {
    setLoading(true);
    try {
      const [sumRes, clsRes, asgnRes, subRes, notesRes, dlRes, resRes] = await Promise.all([
        getStudentAssignmentSummary().catch(() => ({ summary: {} })),
        getStudentEnrolledClasses().catch(() => ({ classes: [] })),
        getStudentAssignments().catch(() => ({ assignments: [] })),
        getStudentSubmissions().catch(() => ({ submissions: [] })),
        getStudentNotes().catch(() => ({ notes: [] })),
        getStudentDeadlines().catch(() => ({ deadlines: [] })),
        getStudentResults().catch(() => ({ results: [] })),
      ]);

      if (sumRes?.summary) setSummary(sumRes.summary);
      if (clsRes?.classes) setEnrolledClasses(clsRes.classes);
      if (asgnRes?.assignments) setAssignments(asgnRes.assignments);
      if (subRes?.submissions) setSubmissions(subRes.submissions);
      if (notesRes?.notes) setNotes(notesRes.notes);
      if (dlRes?.deadlines) setDeadlines(dlRes.deadlines);
      if (resRes?.results) setResults(resRes.results);
    } catch (err) {
      console.error("Error loading student assignments data:", err);
      setFeedbackMsg({ type: "error", text: "Failed to load dashboard data. Please try again." });
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial Load with cleanup guard
  useEffect(() => {
    let ignore = false;

    async function fetchData() {
      setLoading(true);
      try {
        const [sumRes, clsRes, asgnRes, subRes, notesRes, dlRes, resRes] = await Promise.all([
          getStudentAssignmentSummary().catch(() => ({ summary: {} })),
          getStudentEnrolledClasses().catch(() => ({ classes: [] })),
          getStudentAssignments().catch(() => ({ assignments: [] })),
          getStudentSubmissions().catch(() => ({ submissions: [] })),
          getStudentNotes().catch(() => ({ notes: [] })),
          getStudentDeadlines().catch(() => ({ deadlines: [] })),
          getStudentResults().catch(() => ({ results: [] })),
        ]);

        if (!ignore) {
          if (sumRes?.summary) setSummary(sumRes.summary);
          if (clsRes?.classes) setEnrolledClasses(clsRes.classes);
          if (asgnRes?.assignments) setAssignments(asgnRes.assignments);
          if (subRes?.submissions) setSubmissions(subRes.submissions);
          if (notesRes?.notes) setNotes(notesRes.notes);
          if (dlRes?.deadlines) setDeadlines(dlRes.deadlines);
          if (resRes?.results) setResults(resRes.results);
        }
      } catch (err) {
        console.error("Error loading student assignments data:", err);
        if (!ignore) {
          setFeedbackMsg({ type: "error", text: "Failed to load dashboard data." });
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
  }, []);

  // Filtered Assignments
  const filteredAssignments = useMemo(() => {
    return assignments.filter((a) => {
      if (assignmentClassFilter !== "all" && String(a.offering_id) !== String(assignmentClassFilter)) {
        return false;
      }
      if (assignmentStatusFilter !== "all") {
        const stat = (a.student_status || "").toLowerCase();
        const target = assignmentStatusFilter.toLowerCase();
        if (target === "pending" && !stat.includes("pending")) return false;
        if (target === "submitted" && !stat.includes("submitted")) return false;
        if (target === "overdue" && !stat.includes("overdue")) return false;
        if (target === "reviewed" && !stat.includes("reviewed")) return false;
      }
      if (assignmentSearch.trim()) {
        const q = assignmentSearch.toLowerCase();
        const matchTitle = (a.title || "").toLowerCase().includes(q);
        const matchCourse = (a.course_code || "").toLowerCase().includes(q) || (a.course_name || "").toLowerCase().includes(q);
        const matchDesc = (a.description || "").toLowerCase().includes(q);
        if (!matchTitle && !matchCourse && !matchDesc) return false;
      }
      return true;
    });
  }, [assignments, assignmentClassFilter, assignmentStatusFilter, assignmentSearch]);

  // Paginated Assignments
  const totalAssignmentPages = Math.ceil(filteredAssignments.length / assignmentsPerPage) || 1;
  const paginatedAssignments = useMemo(() => {
    const startIndex = (assignmentPage - 1) * assignmentsPerPage;
    return filteredAssignments.slice(startIndex, startIndex + assignmentsPerPage);
  }, [filteredAssignments, assignmentPage]);

  // Filtered Notes
  const filteredNotes = useMemo(() => {
    return notes.filter((n) => {
      if (noteClassFilter !== "all" && String(n.offering_id) !== String(noteClassFilter)) {
        return false;
      }
      if (noteCategoryFilter !== "all" && n.category !== noteCategoryFilter) {
        return false;
      }
      if (noteSearch.trim()) {
        const q = noteSearch.toLowerCase();
        const matchTitle = (n.title || "").toLowerCase().includes(q);
        const matchCourse = (n.course_code || "").toLowerCase().includes(q) || (n.course_name || "").toLowerCase().includes(q);
        if (!matchTitle && !matchCourse) return false;
      }
      return true;
    });
  }, [notes, noteClassFilter, noteCategoryFilter, noteSearch]);

  // Paginated Notes
  const totalNotePages = Math.ceil(filteredNotes.length / notesPerPage) || 1;
  const paginatedNotes = useMemo(() => {
    const startIndex = (notePage - 1) * notesPerPage;
    return filteredNotes.slice(startIndex, startIndex + notesPerPage);
  }, [filteredNotes, notePage]);

  // Open Assignment Detail Modal
  const openDetailModal = async (assignment) => {
    setOpenActionMenuId(null);
    try {
      const res = await getStudentAssignmentDetail(assignment.assignment_id);
      if (res?.assignment) {
        setDetailModalAssignment(res.assignment);
      } else {
        setDetailModalAssignment(assignment);
      }
    } catch {
      setDetailModalAssignment(assignment);
    }
  };

  // Open Submit Modal
  const openSubmitModal = (assignment, resubmit = false) => {
    setOpenActionMenuId(null);
    setDetailModalAssignment(null);
    setSubmitModalAssignment(assignment);
    setIsResubmitting(resubmit);
    setSubmissionFile(null);
    setSubmissionText("");
    setSubmissionConfirmed(false);
  };

  // Handle Assignment Submission
  const handleSubmitWork = async (e) => {
    e.preventDefault();
    if (!submitModalAssignment) return;

    const subType = (submitModalAssignment.submission_type || "FILE_UPLOAD").toUpperCase();
    if (subType === "FILE_UPLOAD" && !submissionFile) {
      setFeedbackMsg({ type: "error", text: "Please select a file to upload." });
      return;
    }
    if (subType === "TEXT_SUBMISSION" && !submissionText.trim()) {
      setFeedbackMsg({ type: "error", text: "Please enter your submission text." });
      return;
    }
    if (subType === "BOTH" && !submissionFile && !submissionText.trim()) {
      setFeedbackMsg({ type: "error", text: "Please provide either a file upload or text response." });
      return;
    }
    if (!submissionConfirmed) {
      setFeedbackMsg({ type: "error", text: "Please check the confirmation box before submitting." });
      return;
    }

    setActionLoading(true);
    try {
      const formData = new FormData();
      if (submissionFile) {
        formData.append("file", submissionFile);
      }
      if (submissionText.trim()) {
        formData.append("submission_text", submissionText.trim());
      }
      if (isResubmitting) {
        formData.append("resubmit", "true");
      }

      const res = await submitAssignment(submitModalAssignment.assignment_id, formData);
      setFeedbackMsg({
        type: "success",
        text: res?.message || "Assignment submitted successfully!",
      });
      setSubmitModalAssignment(null);
      reloadData();
    } catch (err) {
      console.error("Error submitting assignment:", err);
      const errMsg = err?.response?.data?.message || "Failed to submit assignment. Please check file format and deadline.";
      setFeedbackMsg({ type: "error", text: errMsg });
    } finally {
      setActionLoading(false);
    }
  };

  // Download Assignment Attachment
  const handleDownloadAttachment = async (assignmentId, title) => {
    try {
      const response = await downloadAssignmentAttachment(assignmentId);
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `${title.replace(/\s+/g, "_")}_worksheet.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Error downloading attachment:", err);
      setFeedbackMsg({ type: "error", text: "Attachment file could not be downloaded." });
    }
  };

  // Download Student's Own Submitted File
  const handleDownloadSubmission = async (submissionId, fileName) => {
    try {
      const response = await downloadStudentSubmissionFile(submissionId);
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", fileName || "submitted_assignment");
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Error downloading submission file:", err);
      setFeedbackMsg({ type: "error", text: "Submitted file could not be downloaded." });
    }
  };

  // Download Note Document
  const handleDownloadNote = async (materialId, fileName) => {
    try {
      const response = await downloadStudentNote(materialId);
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", fileName || "study_material.pdf");
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Error downloading note:", err);
      setFeedbackMsg({ type: "error", text: "Study material file could not be downloaded." });
    }
  };

  // Helper color for assignment file icon
  const getFileIconColorClass = (index) => {
    const colors = ["icon-green", "icon-blue", "icon-purple", "icon-red"];
    return colors[index % colors.length];
  };

  return (
    <div className="student-assignments-page">
      {/* Toast Alert Feedback */}
      {feedbackMsg && (
        <div className={`san-alert-toast ${feedbackMsg.type}`}>
          {feedbackMsg.type === "success" ? (
            <CheckCircle2 size={18} className="san-alert-icon" />
          ) : (
            <AlertCircle size={18} className="san-alert-icon" />
          )}
          <span>{feedbackMsg.text}</span>
          <button
            type="button"
            className="san-alert-close"
            onClick={() => setFeedbackMsg(null)}
            aria-label="Dismiss message"
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* Breadcrumb Navigation */}
      <nav className="san-breadcrumb" aria-label="Breadcrumb">
        <span className="san-breadcrumb-item">Home</span>
        <ChevronRight size={14} className="san-breadcrumb-sep" />
        <span className="san-breadcrumb-item active">Assignments & Notes</span>
      </nav>

      {/* Header */}
      <div className="san-header">
        <div className="san-header-copy">
          <h1 className="san-title">Assignments & Notes</h1>
          <p className="san-subtitle">
            View your assignments, study materials and track your progress.
          </p>
        </div>

        <button
          type="button"
          className="san-refresh-btn"
          onClick={reloadData}
          disabled={loading}
          title="Refresh Data"
        >
          <RefreshCw size={15} className={loading ? "spin" : ""} />
          <span>Refresh</span>
        </button>
      </div>

      {/* 4 Summary Stat Cards */}
      <div className="san-stats-grid">
        {/* Total Assignments */}
        <div className="san-stat-card">
          <div className="san-stat-icon-wrap blue">
            <FileText size={22} strokeWidth={2.3} />
          </div>
          <div className="san-stat-content">
            <span className="san-stat-label">Total Assignments</span>
            <strong className="san-stat-value">{summary.total_assignments}</strong>
            <span className="san-stat-subtext">Across all enrolled classes</span>
          </div>
        </div>

        {/* Pending Assignments */}
        <div className="san-stat-card">
          <div className="san-stat-icon-wrap amber">
            <Clock size={22} strokeWidth={2.3} />
          </div>
          <div className="san-stat-content">
            <span className="san-stat-label">Pending Assignments</span>
            <strong className="san-stat-value">{summary.pending_assignments}</strong>
            <span className="san-stat-subtext">Not yet submitted</span>
          </div>
        </div>

        {/* Submitted */}
        <div className="san-stat-card">
          <div className="san-stat-icon-wrap green">
            <CheckCircle2 size={22} strokeWidth={2.3} />
          </div>
          <div className="san-stat-content">
            <span className="san-stat-label">Submitted</span>
            <strong className="san-stat-value">{summary.submitted_assignments}</strong>
            <span className="san-stat-subtext">Successfully submitted</span>
          </div>
        </div>

        {/* Notes Available */}
        <div className="san-stat-card">
          <div className="san-stat-icon-wrap purple">
            <BookOpen size={22} strokeWidth={2.3} />
          </div>
          <div className="san-stat-content">
            <span className="san-stat-label">Notes Available</span>
            <strong className="san-stat-value">{summary.notes_available}</strong>
            <span className="san-stat-subtext">Study materials & notes</span>
          </div>
        </div>
      </div>

      {/* 5 Main Tabs Bar */}
      <div className="san-tabs-bar">
        <button
          type="button"
          className={`san-tab-btn${activeTab === "assignments" ? " active" : ""}`}
          onClick={() => setActiveTab("assignments")}
        >
          <FileText size={17} />
          <span>Assignments</span>
        </button>

        <button
          type="button"
          className={`san-tab-btn${activeTab === "submissions" ? " active" : ""}`}
          onClick={() => setActiveTab("submissions")}
        >
          <FileCheck size={17} />
          <span>My Submissions</span>
        </button>

        <button
          type="button"
          className={`san-tab-btn${activeTab === "notes" ? " active" : ""}`}
          onClick={() => setActiveTab("notes")}
        >
          <BookOpen size={17} />
          <span>Notes & Study Materials</span>
        </button>

        <button
          type="button"
          className={`san-tab-btn${activeTab === "deadlines" ? " active" : ""}`}
          onClick={() => setActiveTab("deadlines")}
        >
          <Calendar size={17} />
          <span>Upcoming Deadlines</span>
        </button>

        <button
          type="button"
          className={`san-tab-btn${activeTab === "results" ? " active" : ""}`}
          onClick={() => setActiveTab("results")}
        >
          <Award size={17} />
          <span>Results & Feedback</span>
        </button>
      </div>

      {/* TAB 1: ASSIGNMENTS */}
      {activeTab === "assignments" && (
        <div className="san-tab-pane">
          <div className="san-panel-card">
            <div className="san-panel-header">
              <div className="san-panel-icon-wrap blue">
                <FileText size={20} />
              </div>
              <div className="san-panel-copy">
                <h2>Assignments</h2>
                <p>View and submit your assignments. Track deadlines and status.</p>
              </div>
            </div>

            {/* Filter Bar */}
            <div className="san-filter-bar">
              <div className="san-search-box">
                <Search size={16} className="san-search-icon" />
                <input
                  type="text"
                  placeholder="Search assignments..."
                  value={assignmentSearch}
                  onChange={(e) => {
                    setAssignmentSearch(e.target.value);
                    setAssignmentPage(1);
                  }}
                  className="san-search-input"
                />
              </div>

              <div className="san-filters-group">
                {/* Class Filter */}
                <select
                  className="san-select"
                  value={assignmentClassFilter}
                  onChange={(e) => {
                    setAssignmentClassFilter(e.target.value);
                    setAssignmentPage(1);
                  }}
                >
                  <option value="all">All Classes</option>
                  {enrolledClasses.map((c) => (
                    <option key={c.offering_id} value={c.offering_id}>
                      {c.course_code} - {c.course_name}
                    </option>
                  ))}
                </select>

                {/* Status Filter */}
                <select
                  className="san-select"
                  value={assignmentStatusFilter}
                  onChange={(e) => {
                    setAssignmentStatusFilter(e.target.value);
                    setAssignmentPage(1);
                  }}
                >
                  <option value="all">All Status</option>
                  <option value="pending">Pending</option>
                  <option value="submitted">Submitted</option>
                  <option value="reviewed">Reviewed / Graded</option>
                  <option value="overdue">Overdue</option>
                </select>
              </div>
            </div>

            {/* Table */}
            {filteredAssignments.length === 0 ? (
              <div className="san-empty-state">
                <FileText size={44} className="san-empty-icon" />
                <h3>No assignments found</h3>
                <p>
                  {assignmentSearch || assignmentClassFilter !== "all" || assignmentStatusFilter !== "all"
                    ? "Try adjusting your search criteria or class filters."
                    : "No published assignments available for your enrolled courses right now."}
                </p>
              </div>
            ) : (
              <div className="san-table-responsive">
                <table className="san-table">
                  <thead>
                    <tr>
                      <th>Title</th>
                      <th>Class / Subject</th>
                      <th>Type</th>
                      <th>Due Date</th>
                      <th>Max Marks</th>
                      <th>Status</th>
                      <th>Submission</th>
                      <th className="text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedAssignments.map((a, idx) => (
                      <tr key={a.assignment_id}>
                        {/* Title with file icon */}
                        <td className="san-col-title">
                          <div className="san-title-wrap">
                            <div className={`san-doc-icon ${getFileIconColorClass(idx)}`}>
                              <FileText size={16} />
                            </div>
                            <div className="san-title-text">
                              <strong className="san-item-title">{a.title}</strong>
                              <span className="san-item-desc" title={a.description}>
                                {a.description
                                  ? a.description.length > 55
                                    ? `${a.description.substring(0, 55)}...`
                                    : a.description
                                  : "Assignment instructions and guidelines"}
                              </span>
                            </div>
                          </div>
                        </td>

                        {/* Class / Subject */}
                        <td className="san-col-class">
                          <span className="san-class-code">{a.course_code || "Course"}</span>
                          <span className="san-class-sub">{a.course_name}</span>
                        </td>

                        {/* Type Badge */}
                        <td>
                          <span
                            className={`san-type-badge ${
                              a.assignment_type?.toLowerCase().includes("text")
                                ? "purple"
                                : "blue"
                            }`}
                          >
                            {a.assignment_type || "File Upload"}
                          </span>
                        </td>

                        {/* Due Date */}
                        <td className="san-col-date">
                          <span className="san-date-text">{a.formatted_due_date}</span>
                          <span
                            className={`san-time-label ${
                              a.is_overdue && !a.has_submitted ? "danger" : ""
                            }`}
                          >
                            ({a.time_label || "Active"})
                          </span>
                        </td>

                        {/* Max Marks */}
                        <td className="san-col-marks">
                          <strong>{a.maximum_marks}</strong>
                        </td>

                        {/* Status Badge */}
                        <td>
                          <span
                            className={`san-status-pill ${
                              a.has_submitted
                                ? a.review_status === "REVIEWED"
                                ? "reviewed"
                                : "submitted"
                                : a.is_overdue
                                ? "overdue"
                                : "pending"
                            }`}
                          >
                            {a.student_status}
                          </span>
                        </td>

                        {/* Class Submissions Progress */}
                        <td className="san-col-progress">
                          <div className="san-prog-text">
                            <span>
                              {a.class_submissions_count} / {a.total_enrolled}
                            </span>
                            <span className="san-prog-pct">{a.class_submission_rate}%</span>
                          </div>
                          <div className="san-prog-track">
                            <div
                              className="san-prog-bar"
                              style={{ width: `${Math.min(100, a.class_submission_rate)}%` }}
                            />
                          </div>
                        </td>

                        {/* Action Buttons */}
                        <td className="san-col-actions text-right">
                          <div className="san-action-buttons-wrap">
                            {a.has_submitted ? (
                              <button
                                type="button"
                                className="san-btn-action view"
                                onClick={() => openDetailModal(a)}
                              >
                                View
                              </button>
                            ) : a.can_submit ? (
                              <button
                                type="button"
                                className="san-btn-action submit"
                                onClick={() => openSubmitModal(a)}
                              >
                                Submit
                              </button>
                            ) : (
                              <button
                                type="button"
                                className="san-btn-action view"
                                onClick={() => openDetailModal(a)}
                              >
                                View
                              </button>
                            )}

                            {/* More Options */}
                            <div className="san-more-menu-wrap">
                              <button
                                type="button"
                                className="san-btn-more"
                                onClick={() =>
                                  setOpenActionMenuId(
                                    openActionMenuId === a.assignment_id ? null : a.assignment_id
                                  )
                                }
                                aria-label="More options"
                              >
                                <MoreVertical size={16} />
                              </button>

                              {openActionMenuId === a.assignment_id && (
                                <div className="san-dropdown-menu">
                                  <button
                                    type="button"
                                    className="san-dropdown-item"
                                    onClick={() => openDetailModal(a)}
                                  >
                                    <ExternalLink size={14} className="mr-2" />
                                    <span>View Instructions</span>
                                  </button>

                                  {a.has_attachment && (
                                    <button
                                      type="button"
                                      className="san-dropdown-item"
                                      onClick={() => {
                                        handleDownloadAttachment(a.assignment_id, a.title);
                                        setOpenActionMenuId(null);
                                      }}
                                    >
                                      <Download size={14} className="mr-2" />
                                      <span>Download Attachment</span>
                                    </button>
                                  )}

                                  {a.has_submitted && (
                                    <button
                                      type="button"
                                      className="san-dropdown-item"
                                      onClick={() => openSubmitModal(a, true)}
                                    >
                                      <UploadCloud size={14} className="mr-2 text-blue-600" />
                                      <span>Resubmit Work</span>
                                    </button>
                                  )}
                                </div>
                              )}
                            </div>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Pagination */}
            {filteredAssignments.length > assignmentsPerPage && (
              <div className="san-pagination-bar">
                <span className="san-page-info">
                  Showing {(assignmentPage - 1) * assignmentsPerPage + 1} -{" "}
                  {Math.min(assignmentPage * assignmentsPerPage, filteredAssignments.length)} of{" "}
                  {filteredAssignments.length} assignments
                </span>

                <div className="san-page-buttons">
                  <button
                    type="button"
                    className="san-page-btn"
                    disabled={assignmentPage === 1}
                    onClick={() => setAssignmentPage((p) => Math.max(1, p - 1))}
                  >
                    <ChevronLeft size={16} />
                  </button>
                  {Array.from({ length: totalAssignmentPages }, (_, i) => i + 1).map((num) => (
                    <button
                      key={num}
                      type="button"
                      className={`san-page-btn ${num === assignmentPage ? "active" : ""}`}
                      onClick={() => setAssignmentPage(num)}
                    >
                      {num}
                    </button>
                  ))}
                  <button
                    type="button"
                    className="san-page-btn"
                    disabled={assignmentPage === totalAssignmentPages}
                    onClick={() => setAssignmentPage((p) => Math.min(totalAssignmentPages, p + 1))}
                  >
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: MY SUBMISSIONS */}
      {activeTab === "submissions" && (
        <div className="san-tab-pane">
          <div className="san-panel-card">
            <div className="san-panel-header">
              <div className="san-panel-icon-wrap green">
                <FileCheck size={20} />
              </div>
              <div className="san-panel-copy">
                <h2>My Submissions</h2>
                <p>Your complete history of submitted assignments, files, and review statuses.</p>
              </div>
            </div>

            {submissions.length === 0 ? (
              <div className="san-empty-state">
                <FileCheck size={44} className="san-empty-icon" />
                <h3>No submissions found</h3>
                <p>You haven't submitted any assignments yet. Switch to the Assignments tab to submit.</p>
              </div>
            ) : (
              <div className="san-table-responsive">
                <table className="san-table">
                  <thead>
                    <tr>
                      <th>Assignment Title</th>
                      <th>Subject</th>
                      <th>Submitted Date</th>
                      <th>Submission Type</th>
                      <th>Status</th>
                      <th>Marks Obtained</th>
                      <th>Review Status</th>
                      <th className="text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {submissions.map((sub) => (
                      <tr key={sub.submission_id}>
                        <td className="san-col-title">
                          <strong className="san-item-title">{sub.assignment_title}</strong>
                        </td>
                        <td>
                          <span className="san-class-code">{sub.course_code}</span>
                          <span className="san-class-sub">{sub.course_name}</span>
                        </td>
                        <td>
                          <span className="san-date-text">{sub.formatted_submitted_date}</span>
                        </td>
                        <td>
                          <span className="san-type-badge blue">
                            {sub.has_file ? "File Upload" : "Text Submission"}
                          </span>
                        </td>
                        <td>
                          <span className={`san-status-pill ${sub.is_late ? "overdue" : "submitted"}`}>
                            {sub.is_late ? "Late Submitted" : "On Time"}
                          </span>
                        </td>
                        <td>
                          {sub.marks_obtained !== null && sub.marks_obtained !== undefined ? (
                            <strong className="san-marks-highlight">
                              {sub.marks_obtained} / {sub.maximum_marks}
                            </strong>
                          ) : (
                            <span className="text-slate-400 text-xs">Pending grading</span>
                          )}
                        </td>
                        <td>
                          <span
                            className={`san-review-pill ${
                              sub.review_status === "REVIEWED" ? "graded" : "pending"
                            }`}
                          >
                            {sub.review_status === "REVIEWED" ? "Graded" : "Under Review"}
                          </span>
                        </td>
                        <td className="text-right">
                          <div className="san-action-buttons-wrap">
                            {sub.has_file && (
                              <button
                                type="button"
                                className="san-btn-action view"
                                onClick={() =>
                                  handleDownloadSubmission(sub.submission_id, sub.file_name)
                                }
                                title="Download submitted file"
                              >
                                <Download size={13} className="mr-1 inline" />
                                File
                              </button>
                            )}
                            <button
                              type="button"
                              className="san-btn-action submit"
                              onClick={() => setSubmissionFeedbackModal(sub)}
                            >
                              Details
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: NOTES & STUDY MATERIALS */}
      {activeTab === "notes" && (
        <div className="san-tab-pane">
          <div className="san-panel-card">
            <div className="san-panel-header">
              <div className="san-panel-icon-wrap purple">
                <BookOpen size={20} />
              </div>
              <div className="san-panel-copy">
                <h2>Notes & Study Materials</h2>
                <p>Access lecture notes, reference resources, practical guides, and presentation slides.</p>
              </div>
            </div>

            {/* Filter Bar */}
            <div className="san-filter-bar">
              <div className="san-search-box">
                <Search size={16} className="san-search-icon" />
                <input
                  type="text"
                  placeholder="Search notes..."
                  value={noteSearch}
                  onChange={(e) => {
                    setNoteSearch(e.target.value);
                    setNotePage(1);
                  }}
                  className="san-search-input"
                />
              </div>

              <div className="san-filters-group">
                <select
                  className="san-select"
                  value={noteClassFilter}
                  onChange={(e) => {
                    setNoteClassFilter(e.target.value);
                    setNotePage(1);
                  }}
                >
                  <option value="all">All Classes</option>
                  {enrolledClasses.map((c) => (
                    <option key={c.offering_id} value={c.offering_id}>
                      {c.course_code} - {c.course_name}
                    </option>
                  ))}
                </select>

                <select
                  className="san-select"
                  value={noteCategoryFilter}
                  onChange={(e) => {
                    setNoteCategoryFilter(e.target.value);
                    setNotePage(1);
                  }}
                >
                  <option value="all">All Categories</option>
                  <option value="LECTURE_NOTES">Lecture Notes</option>
                  <option value="REFERENCE">Reference Material</option>
                  <option value="PRACTICAL">Practical / Lab Manual</option>
                  <option value="TUTORIAL">Tutorial</option>
                  <option value="OTHER">Other</option>
                </select>
              </div>
            </div>

            {filteredNotes.length === 0 ? (
              <div className="san-empty-state">
                <BookOpen size={44} className="san-empty-icon" />
                <h3>No study materials available</h3>
                <p>
                  {noteSearch || noteClassFilter !== "all" || noteCategoryFilter !== "all"
                    ? "Try adjusting your search criteria or category filter."
                    : "Your professors haven't uploaded any study materials for your enrolled classes yet."}
                </p>
              </div>
            ) : (
              <div className="san-table-responsive">
                <table className="san-table">
                  <thead>
                    <tr>
                      <th>Title</th>
                      <th>Subject</th>
                      <th>Category</th>
                      <th>File Type</th>
                      <th>Upload Date</th>
                      <th>Visibility</th>
                      <th className="text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedNotes.map((note, idx) => (
                      <tr key={note.material_id}>
                        <td className="san-col-title">
                          <div className="san-title-wrap">
                            <div className={`san-doc-icon ${getFileIconColorClass(idx)}`}>
                              <BookOpen size={16} />
                            </div>
                            <div className="san-title-text">
                              <strong className="san-item-title">{note.title}</strong>
                              <span className="san-item-desc" title={note.description}>
                                {note.description || "Course study material document"}
                              </span>
                            </div>
                          </div>
                        </td>

                        <td>
                          <span className="san-class-code">{note.course_code}</span>
                          <span className="san-class-sub">{note.course_name}</span>
                        </td>

                        <td>
                          <span className="san-note-category-pill">
                            {note.category ? note.category.replace("_", " ") : "Notes"}
                          </span>
                        </td>

                        <td>
                          <span className="san-file-type-pill">
                            {(note.file_type || "pdf").toUpperCase()} • {note.formatted_size}
                          </span>
                        </td>

                        <td>
                          <span className="san-date-text">{note.formatted_date}</span>
                        </td>

                        <td>
                          <span className="san-status-pill submitted">Published</span>
                        </td>

                        <td className="text-right">
                          <button
                            type="button"
                            className="san-btn-action submit"
                            onClick={() => handleDownloadNote(note.material_id, note.file_name)}
                          >
                            <Download size={13} className="mr-1 inline" />
                            Download
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Notes Pagination */}
            {filteredNotes.length > notesPerPage && (
              <div className="san-pagination-bar">
                <span className="san-page-info">
                  Showing {(notePage - 1) * notesPerPage + 1} -{" "}
                  {Math.min(notePage * notesPerPage, filteredNotes.length)} of {filteredNotes.length}{" "}
                  notes
                </span>

                <div className="san-page-buttons">
                  <button
                    type="button"
                    className="san-page-btn"
                    disabled={notePage === 1}
                    onClick={() => setNotePage((p) => Math.max(1, p - 1))}
                  >
                    <ChevronLeft size={16} />
                  </button>
                  {Array.from({ length: totalNotePages }, (_, i) => i + 1).map((num) => (
                    <button
                      key={num}
                      type="button"
                      className={`san-page-btn ${num === notePage ? "active" : ""}`}
                      onClick={() => setNotePage(num)}
                    >
                      {num}
                    </button>
                  ))}
                  <button
                    type="button"
                    className="san-page-btn"
                    disabled={notePage === totalNotePages}
                    onClick={() => setNotePage((p) => Math.min(totalNotePages, p + 1))}
                  >
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 4: UPCOMING DEADLINES */}
      {activeTab === "deadlines" && (
        <div className="san-tab-pane">
          <div className="san-panel-card">
            <div className="san-panel-header">
              <div className="san-panel-icon-wrap amber">
                <Calendar size={20} />
              </div>
              <div className="san-panel-copy">
                <h2>Upcoming Deadlines</h2>
                <p>Chronological breakdown of assignment deadlines across your enrolled subjects.</p>
              </div>
            </div>

            {deadlines.length === 0 ? (
              <div className="san-empty-state">
                <Calendar size={44} className="san-empty-icon" />
                <h3>No upcoming deadlines</h3>
                <p>You have no active deadlines pending. Great job staying ahead!</p>
              </div>
            ) : (
              <div className="san-deadlines-list">
                {deadlines.map((item) => (
                  <div
                    key={item.assignment_id}
                    className={`san-deadline-item ${item.is_overdue ? "overdue" : ""}`}
                  >
                    <div className="san-deadline-date-box">
                      <span className="san-dl-due">{item.formatted_due_date}</span>
                      <span className={`san-dl-time ${item.is_overdue ? "danger" : ""}`}>
                        {item.time_label}
                      </span>
                    </div>

                    <div className="san-deadline-info">
                      <strong className="san-dl-title">{item.title}</strong>
                      <span className="san-dl-course">
                        {item.course_code} - {item.course_name} • Faculty: {item.faculty_name}
                      </span>
                      <span className="san-dl-marks">Max Marks: {item.maximum_marks}</span>
                    </div>

                    <div className="san-deadline-actions">
                      <span
                        className={`san-status-pill ${
                          item.has_submitted
                            ? "submitted"
                            : item.is_overdue
                            ? "overdue"
                            : "pending"
                        }`}
                      >
                        {item.submission_status}
                      </span>

                      {item.can_submit && (
                        <button
                          type="button"
                          className="san-btn-action submit"
                          onClick={() => openSubmitModal(item)}
                        >
                          Submit Work
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 5: RESULTS & FEEDBACK */}
      {activeTab === "results" && (
        <div className="san-tab-pane">
          <div className="san-panel-card">
            <div className="san-panel-header">
              <div className="san-panel-icon-wrap purple">
                <Award size={20} />
              </div>
              <div className="san-panel-copy">
                <h2>Results & Feedback</h2>
                <p>Evaluated assignments, marks scored, and individualized feedback from your professors.</p>
              </div>
            </div>

            {results.length === 0 ? (
              <div className="san-empty-state">
                <Award size={44} className="san-empty-icon" />
                <h3>No evaluated assignments yet</h3>
                <p>
                  As soon as faculty members grade your submissions, your scores and feedback will
                  appear right here.
                </p>
              </div>
            ) : (
              <div className="san-results-grid">
                {results.map((res) => (
                  <div key={res.submission_id} className="san-result-card">
                    <div className="san-result-header">
                      <div>
                        <strong className="san-result-title">{res.assignment_title}</strong>
                        <span className="san-result-course">
                          {res.course_code} - {res.course_name}
                        </span>
                      </div>
                      <div className="san-score-badge">
                        <strong>{res.marks_obtained}</strong>
                        <span>/ {res.maximum_marks}</span>
                      </div>
                    </div>

                    <div className="san-score-pct-bar">
                      <div className="san-score-pct-copy">
                        <span>Score Percentage</span>
                        <strong>{res.percentage}%</strong>
                      </div>
                      <div className="san-prog-track">
                        <div
                          className="san-prog-bar"
                          style={{
                            width: `${Math.min(100, res.percentage)}%`,
                            backgroundColor: res.percentage >= 75 ? "#059669" : res.percentage >= 50 ? "#2563eb" : "#d97706",
                          }}
                        />
                      </div>
                    </div>

                    <div className="san-feedback-box">
                      <span className="san-feedback-label">Faculty Feedback:</span>
                      <p className="san-feedback-text">"{res.feedback}"</p>
                    </div>

                    <div className="san-result-footer">
                      <span>Evaluated on {res.formatted_reviewed_date}</span>
                      {res.has_file && (
                        <button
                          type="button"
                          className="san-btn-action view"
                          onClick={() => handleDownloadSubmission(res.submission_id, res.file_name)}
                        >
                          <Download size={13} className="mr-1 inline" />
                          File
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* MODAL 1: Assignment Details */}
      {detailModalAssignment && (
        <div className="san-modal-overlay">
          <div className="san-modal-container">
            <div className="san-modal-header">
              <h2>{detailModalAssignment.title}</h2>
              <button
                type="button"
                className="san-modal-close"
                onClick={() => setDetailModalAssignment(null)}
                aria-label="Close modal"
              >
                <X size={20} />
              </button>
            </div>

            <div className="san-modal-body">
              <div className="san-detail-meta-grid">
                <div>
                  <span>Course:</span>
                  <strong>
                    {detailModalAssignment.course_code} - {detailModalAssignment.course_name}
                  </strong>
                </div>
                <div>
                  <span>Faculty:</span>
                  <strong>{detailModalAssignment.faculty_name}</strong>
                </div>
                <div>
                  <span>Due Date:</span>
                  <strong className={detailModalAssignment.is_overdue ? "text-red-600" : ""}>
                    {detailModalAssignment.formatted_due_date} ({detailModalAssignment.time_label})
                  </strong>
                </div>
                <div>
                  <span>Max Marks:</span>
                  <strong>{detailModalAssignment.maximum_marks}</strong>
                </div>
                <div>
                  <span>Submission Type:</span>
                  <strong>{detailModalAssignment.submission_type || "File Upload"}</strong>
                </div>
                <div>
                  <span>Allowed Types:</span>
                  <strong>{detailModalAssignment.allowed_file_types || "pdf, doc, zip"}</strong>
                </div>
              </div>

              {detailModalAssignment.has_attachment && (
                <div className="san-attachment-card">
                  <div className="flex items-center gap-2">
                    <FileText size={18} className="text-blue-600" />
                    <span className="text-sm font-semibold text-slate-800">
                      Faculty Reference Worksheet / Brief
                    </span>
                  </div>
                  <button
                    type="button"
                    className="san-btn-action submit"
                    onClick={() =>
                      handleDownloadAttachment(
                        detailModalAssignment.assignment_id,
                        detailModalAssignment.title
                      )
                    }
                  >
                    <Download size={14} className="mr-1 inline" />
                    Download Brief
                  </button>
                </div>
              )}

              <div className="san-desc-box">
                <h4>Instructions & Guidelines</h4>
                <p>
                  {detailModalAssignment.description ||
                    "Please follow all standard academic integrity rules when submitting your solution."}
                </p>
              </div>

              {detailModalAssignment.has_submitted && (
                <div className="san-submission-status-card">
                  <CheckCircle2 size={18} className="text-emerald-600" />
                  <span>
                    You have already submitted this assignment on{" "}
                    {detailModalAssignment.submitted_at || "file"}.
                  </span>
                </div>
              )}
            </div>

            <div className="san-modal-footer">
              <button
                type="button"
                className="san-btn-secondary"
                onClick={() => setDetailModalAssignment(null)}
              >
                Close
              </button>
              {detailModalAssignment.can_submit && (
                <button
                  type="button"
                  className="san-btn-primary"
                  onClick={() => openSubmitModal(detailModalAssignment)}
                >
                  Proceed to Submit
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: Submit Assignment Work */}
      {submitModalAssignment && (
        <div className="san-modal-overlay">
          <div className="san-modal-container">
            <div className="san-modal-header">
              <h2>
                {isResubmitting ? "Resubmit Work:" : "Submit Work:"}{" "}
                {submitModalAssignment.title}
              </h2>
              <button
                type="button"
                className="san-modal-close"
                onClick={() => setSubmitModalAssignment(null)}
                aria-label="Close modal"
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSubmitWork} className="san-modal-form">
              <div className="san-submit-info-box">
                <div className="flex justify-between text-xs text-slate-600 mb-1">
                  <span>Course:</span>
                  <strong>{submitModalAssignment.course_code}</strong>
                </div>
                <div className="flex justify-between text-xs text-slate-600 mb-1">
                  <span>Due Date:</span>
                  <strong className={submitModalAssignment.is_overdue ? "text-amber-600" : ""}>
                    {submitModalAssignment.formatted_due_date}
                  </strong>
                </div>
                {submitModalAssignment.is_overdue && (
                  <div className="san-late-warning">
                    <AlertCircle size={15} />
                    <span>This assignment is overdue. Your submission will be marked Late.</span>
                  </div>
                )}
              </div>

              {/* File Upload Input if applicable */}
              {(submitModalAssignment.submission_type?.toUpperCase() === "FILE_UPLOAD" ||
                submitModalAssignment.submission_type?.toUpperCase() === "BOTH") && (
                <div className="san-form-group">
                  <label htmlFor="submit-file">
                    Upload Solution Document (Allowed:{" "}
                    {submitModalAssignment.allowed_file_types || "pdf, doc, docx, zip"}, Max:{" "}
                    {submitModalAssignment.maximum_file_size_mb || 10} MB)
                  </label>
                  <input
                    id="submit-file"
                    type="file"
                    onChange={(e) => setSubmissionFile(e.target.files[0] || null)}
                  />
                  {submissionFile && (
                    <span className="san-file-chosen-text">
                      Selected: <strong>{submissionFile.name}</strong> (
                      {(submissionFile.size / 1024).toFixed(1)} KB)
                    </span>
                  )}
                </div>
              )}

              {/* Text Input if applicable */}
              {(submitModalAssignment.submission_type?.toUpperCase() === "TEXT_SUBMISSION" ||
                submitModalAssignment.submission_type?.toUpperCase() === "BOTH") && (
                <div className="san-form-group">
                  <label htmlFor="submit-text">Online Text Submission / Comments</label>
                  <textarea
                    id="submit-text"
                    rows={4}
                    placeholder="Type or paste your answer or notes here..."
                    value={submissionText}
                    onChange={(e) => setSubmissionText(e.target.value)}
                  />
                </div>
              )}

              {/* Confirmation Checkbox */}
              <div className="san-confirm-box">
                <label className="san-checkbox-label">
                  <input
                    type="checkbox"
                    checked={submissionConfirmed}
                    onChange={(e) => setSubmissionConfirmed(e.target.checked)}
                  />
                  <span>
                    I confirm that this work is entirely my own and complies with academic integrity guidelines.
                  </span>
                </label>
              </div>

              <div className="san-modal-footer">
                <button
                  type="button"
                  className="san-btn-secondary"
                  onClick={() => setSubmitModalAssignment(null)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="san-btn-primary"
                  disabled={actionLoading || !submissionConfirmed}
                >
                  {actionLoading ? "Submitting..." : isResubmitting ? "Confirm Resubmission" : "Submit Assignment"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 3: View Submission & Feedback Details */}
      {submissionFeedbackModal && (
        <div className="san-modal-overlay">
          <div className="san-modal-container">
            <div className="san-modal-header">
              <h2>Submission Details: {submissionFeedbackModal.assignment_title}</h2>
              <button
                type="button"
                className="san-modal-close"
                onClick={() => setSubmissionFeedbackModal(null)}
                aria-label="Close modal"
              >
                <X size={20} />
              </button>
            </div>

            <div className="san-modal-body">
              <div className="san-detail-meta-grid">
                <div>
                  <span>Submitted At:</span>
                  <strong>{submissionFeedbackModal.formatted_submitted_date}</strong>
                </div>
                <div>
                  <span>Late Submission:</span>
                  <strong className={submissionFeedbackModal.is_late ? "text-amber-600" : "text-emerald-600"}>
                    {submissionFeedbackModal.is_late ? "Yes (Late)" : "No (On Time)"}
                  </strong>
                </div>
                <div>
                  <span>Review Status:</span>
                  <strong className="text-blue-600">{submissionFeedbackModal.review_status}</strong>
                </div>
                <div>
                  <span>Marks Awarded:</span>
                  <strong>
                    {submissionFeedbackModal.marks_obtained !== null &&
                    submissionFeedbackModal.marks_obtained !== undefined
                      ? `${submissionFeedbackModal.marks_obtained} / ${submissionFeedbackModal.maximum_marks}`
                      : "Pending evaluation"}
                  </strong>
                </div>
              </div>

              {submissionFeedbackModal.has_file && (
                <div className="san-attachment-card">
                  <div className="flex items-center gap-2">
                    <FileCheck size={18} className="text-emerald-600" />
                    <span className="text-sm font-semibold text-slate-800">
                      {submissionFeedbackModal.file_name || "Submitted File"}
                    </span>
                  </div>
                  <button
                    type="button"
                    className="san-btn-action view"
                    onClick={() =>
                      handleDownloadSubmission(
                        submissionFeedbackModal.submission_id,
                        submissionFeedbackModal.file_name
                      )
                    }
                  >
                    <Download size={14} className="mr-1 inline" />
                    Download File
                  </button>
                </div>
              )}

              {submissionFeedbackModal.submission_text && (
                <div className="san-desc-box">
                  <h4>Submitted Text Response</h4>
                  <p>{submissionFeedbackModal.submission_text}</p>
                </div>
              )}

              {submissionFeedbackModal.feedback && (
                <div className="san-feedback-box">
                  <span className="san-feedback-label">Faculty Feedback Comments:</span>
                  <p className="san-feedback-text">"{submissionFeedbackModal.feedback}"</p>
                </div>
              )}
            </div>

            <div className="san-modal-footer">
              <button
                type="button"
                className="san-btn-secondary"
                onClick={() => setSubmissionFeedbackModal(null)}
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
