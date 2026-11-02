import { useState, useEffect, useMemo, useCallback } from "react";
import {
  FileText,
  BookOpen,
  Users,
  Clock,
  Plus,
  Search,
  Download,
  CheckCircle2,
  AlertCircle,
  Trash2,
  Edit3,
  MoreVertical,
  UploadCloud,
  Layers,
  X,
  FileCheck,
  ChevronRight,
  RefreshCw,
  FolderOpen,
} from "lucide-react";
import {
  getAssignmentSummary,
  getFacultyClasses,
  getAssignments,
  createAssignment,
  updateAssignment,
  deleteAssignment,
  toggleAssignmentStatus,
  downloadAssignmentAttachment,
  getAssignmentSubmissions,
  evaluateSubmission,
  downloadSubmissionFile,
  getStudyMaterials,
  uploadStudyMaterial,
  deleteStudyMaterial,
  downloadStudyMaterial,
  getClassOverview,
  getRecentUploads,
} from "../../services/facultyAssignmentService";
import "./AssignmentsNotes.css";

export default function AssignmentsNotes() {
  // Navigation tabs: 'assignments' | 'notes' | 'submissions' | 'overview'
  const [activeTab, setActiveTab] = useState("assignments");

  // Summary Metrics
  const [summary, setSummary] = useState({
    total_assignments: 0,
    total_notes: 0,
    total_submissions: 0,
    pending_review: 0,
    classes_count: 0,
  });

  // Offerings list
  const [classes, setClasses] = useState([]);

  // Data lists
  const [assignments, setAssignments] = useState([]);
  const [notes, setNotes] = useState([]);
  const [classOverview, setClassOverview] = useState([]);
  const [recentUploads, setRecentUploads] = useState([]);

  // Loading & error states
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState(null); // { type: 'success' | 'error', text: '' }

  // Filters for Assignments Tab
  const [assignmentSearch, setAssignmentSearch] = useState("");
  const [assignmentClassFilter, setAssignmentClassFilter] = useState("all");
  const [assignmentStatusFilter, setAssignmentStatusFilter] = useState("all");

  // Filters for Notes Tab
  const [noteSearch, setNoteSearch] = useState("");
  const [noteClassFilter, setNoteClassFilter] = useState("all");
  const [noteCategoryFilter, setNoteCategoryFilter] = useState("all");

  // Submissions Tab states
  const [selectedSubmissionAssignmentId, setSelectedSubmissionAssignmentId] = useState("");
  const [submissionsRoster, setSubmissionsRoster] = useState([]);
  const [submissionsLoading, setSubmissionsLoading] = useState(false);
  const [currentGradingSubmission, setCurrentGradingSubmission] = useState(null);
  const [gradeInput, setGradeInput] = useState("");
  const [feedbackInput, setFeedbackInput] = useState("");

  // Modals state
  const [isAssignmentModalOpen, setIsAssignmentModalOpen] = useState(false);
  const [editingAssignment, setEditingAssignment] = useState(null);
  const [assignmentFormData, setAssignmentFormData] = useState({
    offering_id: "",
    title: "",
    description: "",
    assignment_type: "File Upload",
    maximum_marks: "100",
    submission_type: "FILE_UPLOAD",
    allowed_file_types: "pdf,doc,docx,zip",
    maximum_file_size_mb: "10",
    due_date: "",
    allow_late_submission: false,
    status: "PUBLISHED",
    file: null,
  });

  const [isNoteModalOpen, setIsNoteModalOpen] = useState(false);
  const [noteFormData, setNoteFormData] = useState({
    offering_id: "",
    title: "",
    description: "",
    category: "LECTURE_NOTES",
    visibility: "PUBLISHED",
    file: null,
  });

  // Action menu dropdown toggle per assignment
  const [openActionMenuId, setOpenActionMenuId] = useState(null);

  // Close feedback message after 5 seconds
  useEffect(() => {
    if (feedbackMsg) {
      const timer = setTimeout(() => setFeedbackMsg(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [feedbackMsg]);

  // Submissions roster loader
  const reloadSubmissions = useCallback(async (assignmentId) => {
    if (!assignmentId) return;
    setSubmissionsLoading(true);
    try {
      const res = await getAssignmentSubmissions(assignmentId);
      if (res?.submissions) {
        setSubmissionsRoster(res.submissions);
      }
    } catch (err) {
      console.error("Error loading submissions:", err);
      setFeedbackMsg({ type: "error", text: "Failed to load student submissions roster." });
    } finally {
      setSubmissionsLoading(false);
    }
  }, []);

  // Dashboard reloader (for manual refresh button and post-mutation updates)
  const reloadDashboard = useCallback(async () => {
    setLoading(true);
    try {
      const [sumRes, classesRes, asgnRes, notesRes, ovRes, recentRes] = await Promise.all([
        getAssignmentSummary().catch(() => ({ summary: {} })),
        getFacultyClasses().catch(() => ({ classes: [] })),
        getAssignments().catch(() => ({ assignments: [] })),
        getStudyMaterials().catch(() => ({ notes: [] })),
        getClassOverview().catch(() => ({ classes: [] })),
        getRecentUploads().catch(() => ({ recent_uploads: [] })),
      ]);

      if (sumRes?.summary) setSummary(sumRes.summary);
      if (classesRes?.classes) setClasses(classesRes.classes);
      if (asgnRes?.assignments) setAssignments(asgnRes.assignments);
      if (notesRes?.notes) setNotes(notesRes.notes);
      if (ovRes?.classes) setClassOverview(ovRes.classes);
      if (recentRes?.recent_uploads) setRecentUploads(recentRes.recent_uploads);

      if (asgnRes?.assignments?.length > 0) {
        setSelectedSubmissionAssignmentId((prev) => prev || String(asgnRes.assignments[0].assignment_id));
      }
    } catch (err) {
      console.error("Error loading assignments data:", err);
      setFeedbackMsg({ type: "error", text: "Failed to load dashboard data. Please try again." });
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial Data Fetch Effect
  useEffect(() => {
    let ignore = false;

    async function fetchData() {
      setLoading(true);
      try {
        const [sumRes, classesRes, asgnRes, notesRes, ovRes, recentRes] = await Promise.all([
          getAssignmentSummary().catch(() => ({ summary: {} })),
          getFacultyClasses().catch(() => ({ classes: [] })),
          getAssignments().catch(() => ({ assignments: [] })),
          getStudyMaterials().catch(() => ({ notes: [] })),
          getClassOverview().catch(() => ({ classes: [] })),
          getRecentUploads().catch(() => ({ recent_uploads: [] })),
        ]);

        if (!ignore) {
          if (sumRes?.summary) setSummary(sumRes.summary);
          if (classesRes?.classes) setClasses(classesRes.classes);
          if (asgnRes?.assignments) setAssignments(asgnRes.assignments);
          if (notesRes?.notes) setNotes(notesRes.notes);
          if (ovRes?.classes) setClassOverview(ovRes.classes);
          if (recentRes?.recent_uploads) setRecentUploads(recentRes.recent_uploads);

          if (asgnRes?.assignments?.length > 0) {
            setSelectedSubmissionAssignmentId((prev) => prev || String(asgnRes.assignments[0].assignment_id));
          }
        }
      } catch (err) {
        console.error("Error loading assignments data:", err);
        if (!ignore) {
          setFeedbackMsg({ type: "error", text: "Failed to load dashboard data. Please try again." });
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

  // Load Submissions when selected assignment changes in Submissions tab
  useEffect(() => {
    let ignore = false;

    async function fetchSubmissions() {
      if (activeTab !== "submissions" || !selectedSubmissionAssignmentId) return;
      setSubmissionsLoading(true);
      try {
        const res = await getAssignmentSubmissions(selectedSubmissionAssignmentId);
        if (!ignore && res?.submissions) {
          setSubmissionsRoster(res.submissions);
        }
      } catch (err) {
        console.error("Error loading submissions:", err);
        if (!ignore) {
          setFeedbackMsg({ type: "error", text: "Failed to load student submissions roster." });
        }
      } finally {
        if (!ignore) {
          setSubmissionsLoading(false);
        }
      }
    }

    fetchSubmissions();

    return () => {
      ignore = true;
    };
  }, [activeTab, selectedSubmissionAssignmentId]);

  // Filtered Assignments
  const filteredAssignments = useMemo(() => {
    return assignments.filter((a) => {
      // Class filter
      if (assignmentClassFilter !== "all" && String(a.offering_id) !== String(assignmentClassFilter)) {
        return false;
      }
      // Status filter
      if (assignmentStatusFilter !== "all") {
        const eff = (a.effective_status || "").toLowerCase();
        const stat = (a.status || "").toLowerCase();
        const target = assignmentStatusFilter.toLowerCase();
        if (target === "active" && eff !== "active") return false;
        if (target === "upcoming" && eff !== "upcoming") return false;
        if (target === "closed" && eff !== "closed" && stat !== "closed") return false;
        if (target === "draft" && stat !== "draft") return false;
      }
      // Search
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

  // Open Create Assignment Modal
  const openCreateAssignmentModal = () => {
    setEditingAssignment(null);
    setAssignmentFormData({
      offering_id: classes[0]?.offering_id ? String(classes[0].offering_id) : "",
      title: "",
      description: "",
      assignment_type: "File Upload",
      maximum_marks: "100",
      submission_type: "FILE_UPLOAD",
      allowed_file_types: "pdf,doc,docx,zip",
      maximum_file_size_mb: "10",
      due_date: "",
      allow_late_submission: false,
      status: "PUBLISHED",
      file: null,
    });
    setIsAssignmentModalOpen(true);
  };

  // Open Edit Assignment Modal
  const openEditAssignmentModal = (assignment) => {
    setEditingAssignment(assignment);
    const formattedDue = assignment.due_date ? assignment.due_date.substring(0, 16) : "";
    setAssignmentFormData({
      offering_id: String(assignment.offering_id),
      title: assignment.title || "",
      description: assignment.description || "",
      assignment_type: assignment.assignment_type || "File Upload",
      maximum_marks: String(assignment.maximum_marks || 100),
      submission_type: assignment.submission_type || "FILE_UPLOAD",
      allowed_file_types: assignment.allowed_file_types || "pdf,doc,docx,zip",
      maximum_file_size_mb: String(assignment.maximum_file_size_mb || 10),
      due_date: formattedDue,
      allow_late_submission: Boolean(assignment.allow_late_submission),
      status: assignment.status || "PUBLISHED",
      file: null,
    });
    setOpenActionMenuId(null);
    setIsAssignmentModalOpen(true);
  };

  // Save Assignment (Create or Update)
  const handleSaveAssignment = async (e) => {
    e.preventDefault();
    if (!assignmentFormData.title.trim()) {
      setFeedbackMsg({ type: "error", text: "Please enter an assignment title." });
      return;
    }
    if (!assignmentFormData.offering_id) {
      setFeedbackMsg({ type: "error", text: "Please select a class." });
      return;
    }
    if (!assignmentFormData.due_date) {
      setFeedbackMsg({ type: "error", text: "Please specify a due date and time." });
      return;
    }

    setActionLoading(true);
    try {
      const data = new FormData();
      data.append("offering_id", assignmentFormData.offering_id);
      data.append("title", assignmentFormData.title.trim());
      data.append("description", assignmentFormData.description.trim());
      data.append("assignment_type", assignmentFormData.assignment_type);
      data.append("maximum_marks", assignmentFormData.maximum_marks);
      data.append("submission_type", assignmentFormData.submission_type);
      data.append("allowed_file_types", assignmentFormData.allowed_file_types);
      data.append("maximum_file_size_mb", assignmentFormData.maximum_file_size_mb);
      data.append("due_date", assignmentFormData.due_date);
      data.append("allow_late_submission", assignmentFormData.allow_late_submission ? "true" : "false");
      data.append("status", assignmentFormData.status);

      if (assignmentFormData.file) {
        data.append("file", assignmentFormData.file);
      }

      if (editingAssignment) {
        await updateAssignment(editingAssignment.assignment_id, data);
        setFeedbackMsg({ type: "success", text: "Assignment updated successfully!" });
      } else {
        await createAssignment(data);
        setFeedbackMsg({ type: "success", text: "Assignment created successfully!" });
      }

      setIsAssignmentModalOpen(false);
      reloadDashboard();
    } catch (err) {
      console.error("Error saving assignment:", err);
      const errMsg = err?.response?.data?.message || "Failed to save assignment. Please verify inputs.";
      setFeedbackMsg({ type: "error", text: errMsg });
    } finally {
      setActionLoading(false);
    }
  };

  // Delete Assignment
  const handleDeleteAssignment = async (assignmentId) => {
    if (!window.confirm("Are you sure you want to delete this assignment? All submissions and student records for it will be removed.")) {
      return;
    }
    setActionLoading(true);
    try {
      await deleteAssignment(assignmentId);
      setFeedbackMsg({ type: "success", text: "Assignment deleted successfully." });
      setOpenActionMenuId(null);
      reloadDashboard();
    } catch (err) {
      console.error("Error deleting assignment:", err);
      setFeedbackMsg({ type: "error", text: "Failed to delete assignment." });
    } finally {
      setActionLoading(false);
    }
  };

  // Toggle Assignment Status
  const handleToggleStatus = async (assignmentId, currentStatus) => {
    const nextStatus = currentStatus === "PUBLISHED" ? "CLOSED" : "PUBLISHED";
    setActionLoading(true);
    try {
      await toggleAssignmentStatus(assignmentId, nextStatus);
      setFeedbackMsg({ type: "success", text: `Assignment status changed to ${nextStatus}.` });
      setOpenActionMenuId(null);
      reloadDashboard();
    } catch (err) {
      console.error("Error toggling status:", err);
      setFeedbackMsg({ type: "error", text: "Failed to update assignment status." });
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

  // Open Upload Note Modal
  const openUploadNoteModal = () => {
    setNoteFormData({
      offering_id: classes[0]?.offering_id ? String(classes[0].offering_id) : "",
      title: "",
      description: "",
      category: "LECTURE_NOTES",
      visibility: "PUBLISHED",
      file: null,
    });
    setIsNoteModalOpen(true);
  };

  // Save Note Upload
  const handleUploadNote = async (e) => {
    e.preventDefault();
    if (!noteFormData.title.trim()) {
      setFeedbackMsg({ type: "error", text: "Please enter a title for the study material." });
      return;
    }
    if (!noteFormData.offering_id) {
      setFeedbackMsg({ type: "error", text: "Please select a course offering." });
      return;
    }
    if (!noteFormData.file) {
      setFeedbackMsg({ type: "error", text: "Please choose a document file to upload." });
      return;
    }

    setActionLoading(true);
    try {
      const data = new FormData();
      data.append("offering_id", noteFormData.offering_id);
      data.append("title", noteFormData.title.trim());
      data.append("description", noteFormData.description.trim());
      data.append("category", noteFormData.category);
      data.append("visibility", noteFormData.visibility);
      data.append("file", noteFormData.file);

      await uploadStudyMaterial(data);
      setFeedbackMsg({ type: "success", text: "Study material uploaded successfully!" });
      setIsNoteModalOpen(false);
      reloadDashboard();
    } catch (err) {
      console.error("Error uploading study material:", err);
      const errMsg = err?.response?.data?.message || "Failed to upload study material.";
      setFeedbackMsg({ type: "error", text: errMsg });
    } finally {
      setActionLoading(false);
    }
  };

  // Delete Note
  const handleDeleteNote = async (materialId) => {
    if (!window.confirm("Are you sure you want to delete this study material document?")) {
      return;
    }
    setActionLoading(true);
    try {
      await deleteStudyMaterial(materialId);
      setFeedbackMsg({ type: "success", text: "Study material deleted." });
      reloadDashboard();
    } catch (err) {
      console.error("Error deleting note:", err);
      setFeedbackMsg({ type: "error", text: "Failed to delete note." });
    } finally {
      setActionLoading(false);
    }
  };

  // Download Note
  const handleDownloadNote = async (materialId, fileName) => {
    try {
      const response = await downloadStudyMaterial(materialId);
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", fileName || "document.pdf");
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Error downloading note:", err);
      setFeedbackMsg({ type: "error", text: "Note file could not be downloaded." });
    }
  };

  // Open Grading Drawer / Modal
  const openGradingModal = (submission) => {
    setCurrentGradingSubmission(submission);
    setGradeInput(submission.marks_obtained !== null && submission.marks_obtained !== undefined ? String(submission.marks_obtained) : "");
    setFeedbackInput(submission.feedback || "");
  };

  // Submit Grade
  const handleSaveGrade = async (e) => {
    e.preventDefault();
    if (!currentGradingSubmission || !currentGradingSubmission.submission_id) return;

    const numGrade = parseFloat(gradeInput);
    if (isNaN(numGrade) || numGrade < 0 || numGrade > (currentGradingSubmission.maximum_marks || 100)) {
      setFeedbackMsg({
        type: "error",
        text: `Marks must be a valid number between 0 and ${currentGradingSubmission.maximum_marks || 100}.`,
      });
      return;
    }

    setActionLoading(true);
    try {
      await evaluateSubmission(currentGradingSubmission.submission_id, {
        marks_obtained: numGrade,
        feedback: feedbackInput.trim(),
      });
      setFeedbackMsg({ type: "success", text: "Grade & feedback recorded successfully!" });
      setCurrentGradingSubmission(null);
      reloadSubmissions(selectedSubmissionAssignmentId);
      reloadDashboard();
    } catch (err) {
      console.error("Error evaluating submission:", err);
      setFeedbackMsg({ type: "error", text: "Failed to save submission grade." });
    } finally {
      setActionLoading(false);
    }
  };

  // Download Student Submitted File
  const handleDownloadSubmissionFile = async (submissionId, fileName) => {
    try {
      const response = await downloadSubmissionFile(submissionId);
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", fileName || "submission_file");
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Error downloading submission file:", err);
      setFeedbackMsg({ type: "error", text: "Submission file could not be downloaded." });
    }
  };

  // Switch to submissions tab for a specific assignment
  const handleViewAssignmentSubmissions = (assignmentId) => {
    setSelectedSubmissionAssignmentId(String(assignmentId));
    setActiveTab("submissions");
    setOpenActionMenuId(null);
  };

  return (
    <div className="assignments-notes-page">
      {/* Toast Alert Feedback */}
      {feedbackMsg && (
        <div className={`an-alert-toast ${feedbackMsg.type}`}>
          {feedbackMsg.type === "success" ? (
            <CheckCircle2 size={18} className="an-alert-icon" />
          ) : (
            <AlertCircle size={18} className="an-alert-icon" />
          )}
          <span>{feedbackMsg.text}</span>
          <button
            type="button"
            className="an-alert-close"
            onClick={() => setFeedbackMsg(null)}
            aria-label="Dismiss message"
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* Breadcrumb Navigation */}
      <nav className="an-breadcrumb" aria-label="Breadcrumb">
        <span className="an-breadcrumb-item">Home</span>
        <ChevronRight size={14} className="an-breadcrumb-sep" />
        <span className="an-breadcrumb-item">Faculty</span>
        <ChevronRight size={14} className="an-breadcrumb-sep" />
        <span className="an-breadcrumb-item active">Assignment & Notes</span>
      </nav>

      {/* Page Header */}
      <div className="an-header">
        <div className="an-header-copy">
          <h1 className="an-title">Assignment & Notes</h1>
          <p className="an-subtitle">
            Create, upload and manage assignments and study materials for your classes.
          </p>
        </div>

        <button
          type="button"
          className="an-refresh-btn"
          onClick={reloadDashboard}
          disabled={loading}
          title="Refresh Data"
        >
          <RefreshCw size={16} className={loading ? "spin" : ""} />
          <span>Refresh</span>
        </button>
      </div>

      {/* 4 Summary Stat Cards */}
      <div className="an-stats-grid">
        {/* Total Assignments */}
        <div className="an-stat-card">
          <div className="an-stat-icon-wrap blue">
            <FileText size={22} strokeWidth={2.3} />
          </div>
          <div className="an-stat-content">
            <span className="an-stat-label">Total Assignments</span>
            <strong className="an-stat-value">{summary.total_assignments}</strong>
            <span className="an-stat-subtext">Across all classes</span>
          </div>
        </div>

        {/* Total Notes */}
        <div className="an-stat-card">
          <div className="an-stat-icon-wrap green">
            <BookOpen size={22} strokeWidth={2.3} />
          </div>
          <div className="an-stat-content">
            <span className="an-stat-label">Total Notes</span>
            <strong className="an-stat-value">{summary.total_notes}</strong>
            <span className="an-stat-subtext">Study materials uploaded</span>
          </div>
        </div>

        {/* Total Submissions */}
        <div className="an-stat-card">
          <div className="an-stat-icon-wrap purple">
            <Users size={22} strokeWidth={2.3} />
          </div>
          <div className="an-stat-content">
            <span className="an-stat-label">Total Submissions</span>
            <strong className="an-stat-value">{summary.total_submissions}</strong>
            <span className="an-stat-subtext">
              From {summary.classes_count || classes.length} classes
            </span>
          </div>
        </div>

        {/* Pending Review */}
        <div className="an-stat-card">
          <div className="an-stat-icon-wrap amber">
            <Clock size={22} strokeWidth={2.3} />
          </div>
          <div className="an-stat-content">
            <span className="an-stat-label">Pending Review</span>
            <strong className="an-stat-value">{summary.pending_review}</strong>
            <span className="an-stat-subtext">Needs grading</span>
          </div>
        </div>
      </div>

      {/* Main Two-Column Layout */}
      <div className="an-main-container">
        {/* Left Column (Main Tabs & Tables) */}
        <div className="an-main-column">
          {/* Tab Navigation */}
          <div className="an-tabs-bar">
            <button
              type="button"
              className={`an-tab-btn${activeTab === "assignments" ? " active" : ""}`}
              onClick={() => setActiveTab("assignments")}
            >
              Assignments
            </button>
            <button
              type="button"
              className={`an-tab-btn${activeTab === "notes" ? " active" : ""}`}
              onClick={() => setActiveTab("notes")}
            >
              Notes
            </button>
            <button
              type="button"
              className={`an-tab-btn${activeTab === "submissions" ? " active" : ""}`}
              onClick={() => setActiveTab("submissions")}
            >
              Submissions
            </button>
            <button
              type="button"
              className={`an-tab-btn${activeTab === "overview" ? " active" : ""}`}
              onClick={() => setActiveTab("overview")}
            >
              Class Overview
            </button>
          </div>

          {/* TAB 1: ASSIGNMENTS */}
          {activeTab === "assignments" && (
            <div className="an-tab-pane">
              {/* Filter Bar */}
              <div className="an-filter-bar">
                <div className="an-search-box">
                  <Search size={16} className="an-search-icon" />
                  <input
                    type="text"
                    placeholder="Search assignments..."
                    value={assignmentSearch}
                    onChange={(e) => setAssignmentSearch(e.target.value)}
                    className="an-search-input"
                  />
                </div>

                <div className="an-filters-group">
                  {/* Class Filter */}
                  <select
                    className="an-select"
                    value={assignmentClassFilter}
                    onChange={(e) => setAssignmentClassFilter(e.target.value)}
                  >
                    <option value="all">All Classes</option>
                    {classes.map((c) => (
                      <option key={c.offering_id} value={c.offering_id}>
                        {c.course_code} - {c.course_name} (Sec {c.section})
                      </option>
                    ))}
                  </select>

                  {/* Status Filter */}
                  <select
                    className="an-select"
                    value={assignmentStatusFilter}
                    onChange={(e) => setAssignmentStatusFilter(e.target.value)}
                  >
                    <option value="all">All Status</option>
                    <option value="active">Active</option>
                    <option value="upcoming">Upcoming</option>
                    <option value="closed">Closed</option>
                    <option value="draft">Draft</option>
                  </select>
                </div>

                <button
                  type="button"
                  className="an-btn-primary"
                  onClick={openCreateAssignmentModal}
                >
                  <Plus size={16} strokeWidth={2.4} />
                  <span>Create Assignment</span>
                </button>
              </div>

              {/* Assignments Table Card */}
              <div className="an-table-card">
                <div className="an-table-header">
                  <h2 className="an-section-title">Recent Assignments</h2>
                  <span className="an-section-count">
                    Showing {filteredAssignments.length} assignment
                    {filteredAssignments.length === 1 ? "" : "s"}
                  </span>
                </div>

                {filteredAssignments.length === 0 ? (
                  <div className="an-empty-state">
                    <FolderOpen size={44} className="an-empty-icon" />
                    <h3>No assignments found</h3>
                    <p>
                      {assignmentSearch || assignmentClassFilter !== "all" || assignmentStatusFilter !== "all"
                        ? "Try adjusting your search criteria or class filters."
                        : "You haven't created any assignments yet. Click '+ Create Assignment' to start."}
                    </p>
                    <button
                      type="button"
                      className="an-btn-primary"
                      onClick={openCreateAssignmentModal}
                    >
                      <Plus size={16} />
                      <span>Create Assignment</span>
                    </button>
                  </div>
                ) : (
                  <div className="an-table-responsive">
                    <table className="an-table">
                      <thead>
                        <tr>
                          <th>Title</th>
                          <th>Class</th>
                          <th>Type</th>
                          <th>Due Date</th>
                          <th>Submissions</th>
                          <th>Status</th>
                          <th className="text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredAssignments.map((a) => (
                          <tr key={a.assignment_id}>
                            {/* Title & Desc */}
                            <td className="an-col-title">
                              <strong className="an-item-title">{a.title}</strong>
                              <span className="an-item-desc" title={a.description}>
                                {a.description
                                  ? a.description.length > 55
                                    ? `${a.description.substring(0, 55)}...`
                                    : a.description
                                  : "No description provided"}
                              </span>
                            </td>

                            {/* Class */}
                            <td className="an-col-class">
                              <span className="an-class-code">{a.course_code || "Class"}</span>
                              <span className="an-class-sub">
                                {a.course_name ? `${a.course_name}` : `Sec ${a.section}`}
                              </span>
                            </td>

                            {/* Type */}
                            <td>
                              <span
                                className={`an-badge-type ${
                                  a.assignment_type?.toLowerCase().includes("text")
                                    ? "purple"
                                    : "blue"
                                }`}
                              >
                                {a.assignment_type || "File Upload"}
                              </span>
                            </td>

                            {/* Due Date */}
                            <td className="an-col-date">
                              <span className="an-date-text">{a.formatted_due_date}</span>
                              <span
                                className={`an-time-label ${
                                  a.effective_status === "Overdue" ? "danger" : ""
                                }`}
                              >
                                ({a.time_label || a.effective_status})
                              </span>
                            </td>

                            {/* Submissions Progress */}
                            <td className="an-col-progress">
                              <div className="an-progress-wrap">
                                <div className="an-progress-text">
                                  <span>
                                    <strong>{a.submissions_count}</strong> / {a.total_enrolled}
                                  </span>
                                  <span className="an-progress-pct">{a.submission_rate}%</span>
                                </div>
                                <div className="an-progress-track">
                                  <div
                                    className="an-progress-bar"
                                    style={{ width: `${Math.min(100, a.submission_rate)}%` }}
                                  />
                                </div>
                              </div>
                            </td>

                            {/* Status */}
                            <td>
                              <span
                                className={`an-badge-status ${
                                  a.status === "DRAFT"
                                    ? "draft"
                                    : a.effective_status === "Active"
                                    ? "active"
                                    : a.effective_status === "Upcoming"
                                    ? "upcoming"
                                    : "closed"
                                }`}
                              >
                                {a.status === "DRAFT" ? "Draft" : a.effective_status}
                              </span>
                            </td>

                            {/* Actions Dropdown */}
                            <td className="an-col-actions text-right">
                              <div className="an-actions-menu-wrap">
                                <button
                                  type="button"
                                  className="an-icon-action-btn"
                                  onClick={() =>
                                    setOpenActionMenuId(
                                      openActionMenuId === a.assignment_id ? null : a.assignment_id
                                    )
                                  }
                                  aria-label="Actions"
                                >
                                  <MoreVertical size={16} />
                                </button>

                                {openActionMenuId === a.assignment_id && (
                                  <div className="an-dropdown-menu">
                                    <button
                                      type="button"
                                      className="an-dropdown-item"
                                      onClick={() => handleViewAssignmentSubmissions(a.assignment_id)}
                                    >
                                      <FileCheck size={14} className="mr-2 text-blue-600" />
                                      <span>View Submissions ({a.submissions_count})</span>
                                    </button>

                                    {a.has_attachment && (
                                      <button
                                        type="button"
                                        className="an-dropdown-item"
                                        onClick={() => {
                                          handleDownloadAttachment(a.assignment_id, a.title);
                                          setOpenActionMenuId(null);
                                        }}
                                      >
                                        <Download size={14} className="mr-2 text-emerald-600" />
                                        <span>Download Attachment</span>
                                      </button>
                                    )}

                                    <button
                                      type="button"
                                      className="an-dropdown-item"
                                      onClick={() => openEditAssignmentModal(a)}
                                    >
                                      <Edit3 size={14} className="mr-2 text-indigo-600" />
                                      <span>Edit Assignment</span>
                                    </button>

                                    <button
                                      type="button"
                                      className="an-dropdown-item"
                                      onClick={() => handleToggleStatus(a.assignment_id, a.status)}
                                    >
                                      <Clock size={14} className="mr-2 text-amber-600" />
                                      <span>
                                        {a.status === "PUBLISHED" ? "Mark as Closed" : "Publish"}
                                      </span>
                                    </button>

                                    <div className="an-dropdown-divider" />

                                    <button
                                      type="button"
                                      className="an-dropdown-item danger"
                                      onClick={() => handleDeleteAssignment(a.assignment_id)}
                                    >
                                      <Trash2 size={14} className="mr-2 text-rose-600" />
                                      <span>Delete</span>
                                    </button>
                                  </div>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Bottom Informational Banner */}
              <div className="an-info-banner">
                <AlertCircle size={20} className="an-info-icon" />
                <span>
                  Track student progress, manage submissions, and keep your classes organized — all
                  in one place.
                </span>
              </div>
            </div>
          )}

          {/* TAB 2: NOTES & STUDY MATERIALS */}
          {activeTab === "notes" && (
            <div className="an-tab-pane">
              <div className="an-filter-bar">
                <div className="an-search-box">
                  <Search size={16} className="an-search-icon" />
                  <input
                    type="text"
                    placeholder="Search study materials..."
                    value={noteSearch}
                    onChange={(e) => setNoteSearch(e.target.value)}
                    className="an-search-input"
                  />
                </div>

                <div className="an-filters-group">
                  <select
                    className="an-select"
                    value={noteClassFilter}
                    onChange={(e) => setNoteClassFilter(e.target.value)}
                  >
                    <option value="all">All Classes</option>
                    {classes.map((c) => (
                      <option key={c.offering_id} value={c.offering_id}>
                        {c.course_code} - {c.course_name}
                      </option>
                    ))}
                  </select>

                  <select
                    className="an-select"
                    value={noteCategoryFilter}
                    onChange={(e) => setNoteCategoryFilter(e.target.value)}
                  >
                    <option value="all">All Categories</option>
                    <option value="LECTURE_NOTES">Lecture Notes</option>
                    <option value="REFERENCE">Reference Material</option>
                    <option value="PRACTICAL">Practical / Lab Manual</option>
                    <option value="TUTORIAL">Tutorial</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>

                <button
                  type="button"
                  className="an-btn-primary green"
                  onClick={openUploadNoteModal}
                >
                  <UploadCloud size={16} strokeWidth={2.4} />
                  <span>Upload Notes</span>
                </button>
              </div>

              {/* Notes Grid */}
              <div className="an-notes-grid">
                {filteredNotes.length === 0 ? (
                  <div className="an-empty-state full-width">
                    <BookOpen size={44} className="an-empty-icon" />
                    <h3>No study materials found</h3>
                    <p>
                      Share lecture notes, reference material, syllabus slides, and lab guides with
                      your enrolled students.
                    </p>
                    <button
                      type="button"
                      className="an-btn-primary green"
                      onClick={openUploadNoteModal}
                    >
                      <UploadCloud size={16} />
                      <span>Upload Notes</span>
                    </button>
                  </div>
                ) : (
                  filteredNotes.map((note) => (
                    <div key={note.material_id} className="an-note-card">
                      <div className="an-note-card-header">
                        <div className="an-file-badge">
                          <BookOpen size={18} />
                          <span>{(note.file_type || "pdf").toUpperCase()}</span>
                        </div>
                        <span className="an-note-category-pill">
                          {note.category ? note.category.replace("_", " ") : "Notes"}
                        </span>
                      </div>

                      <div className="an-note-card-body">
                        <h3 className="an-note-title" title={note.title}>
                          {note.title}
                        </h3>
                        <p className="an-note-course">
                          {note.course_code} • {note.course_name} (Sec {note.section})
                        </p>
                        {note.description && (
                          <p className="an-note-desc">{note.description}</p>
                        )}
                      </div>

                      <div className="an-note-card-footer">
                        <div className="an-note-meta">
                          <span>{note.formatted_size}</span>
                          <span>•</span>
                          <span>{note.formatted_date}</span>
                        </div>

                        <div className="an-note-actions">
                          <button
                            type="button"
                            className="an-btn-download-sm"
                            onClick={() => handleDownloadNote(note.material_id, note.file_name)}
                            title="Download document"
                          >
                            <Download size={14} />
                            <span>Download</span>
                          </button>

                          <button
                            type="button"
                            className="an-btn-del-sm"
                            onClick={() => handleDeleteNote(note.material_id)}
                            title="Delete note"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* TAB 3: SUBMISSIONS & EVALUATION */}
          {activeTab === "submissions" && (
            <div className="an-tab-pane">
              <div className="an-submissions-filter-bar">
                <label className="an-sub-selector-label" htmlFor="assignment-picker">
                  Select Assignment:
                </label>
                <select
                  id="assignment-picker"
                  className="an-select wide"
                  value={selectedSubmissionAssignmentId}
                  onChange={(e) => setSelectedSubmissionAssignmentId(e.target.value)}
                >
                  {assignments.map((a) => (
                    <option key={a.assignment_id} value={a.assignment_id}>
                      {a.course_code} - {a.title} ({a.submissions_count}/{a.total_enrolled} submitted)
                    </option>
                  ))}
                </select>
              </div>

              {/* Submissions Roster */}
              <div className="an-table-card">
                <div className="an-table-header">
                  <h2 className="an-section-title">Student Submissions Roster</h2>
                  <span className="an-section-count">
                    {submissionsRoster.filter((s) => s.submitted).length} of{" "}
                    {submissionsRoster.length} students submitted
                  </span>
                </div>

                {submissionsLoading ? (
                  <div className="an-loading-state">
                    <RefreshCw size={24} className="spin" />
                    <span>Loading student submission roster...</span>
                  </div>
                ) : submissionsRoster.length === 0 ? (
                  <div className="an-empty-state">
                    <Users size={40} className="an-empty-icon" />
                    <h3>No students enrolled or no assignment selected</h3>
                  </div>
                ) : (
                  <div className="an-table-responsive">
                    <table className="an-table">
                      <thead>
                        <tr>
                          <th>Roll Number</th>
                          <th>Student Name</th>
                          <th>Submission Status</th>
                          <th>Submitted File / Text</th>
                          <th>Marks</th>
                          <th>Review Status</th>
                          <th className="text-right">Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {submissionsRoster.map((sub) => (
                          <tr key={sub.student_id}>
                            <td>
                              <strong>{sub.roll_number}</strong>
                            </td>
                            <td>
                              <span className="an-student-name">{sub.name}</span>
                              <span className="an-student-email">{sub.email}</span>
                            </td>
                            <td>
                              {sub.submitted ? (
                                <span className={`an-sub-status-badge ${sub.is_late ? "late" : "submitted"}`}>
                                  {sub.is_late ? "Late Submitted" : "Submitted"}
                                </span>
                              ) : (
                                <span className="an-sub-status-badge not-submitted">
                                  Not Submitted
                                </span>
                              )}
                            </td>
                            <td>
                              {sub.has_file ? (
                                <button
                                  type="button"
                                  className="an-link-btn"
                                  onClick={() =>
                                    handleDownloadSubmissionFile(sub.submission_id, sub.file_name)
                                  }
                                >
                                  <Download size={14} className="mr-1 inline" />
                                  <span>{sub.file_name || "Download File"}</span>
                                </button>
                              ) : sub.submission_text ? (
                                <span className="an-text-preview" title={sub.submission_text}>
                                  Text submitted
                                </span>
                              ) : (
                                <span className="text-slate-400 text-xs">—</span>
                              )}
                            </td>
                            <td>
                              {sub.marks_obtained !== null && sub.marks_obtained !== undefined ? (
                                <strong className="an-marks-display">
                                  {sub.marks_obtained} / {sub.maximum_marks}
                                </strong>
                              ) : (
                                <span className="text-slate-400 text-xs">—</span>
                              )}
                            </td>
                            <td>
                              <span
                                className={`an-review-pill ${
                                  sub.review_status === "REVIEWED"
                                    ? "reviewed"
                                    : sub.submitted
                                    ? "pending"
                                    : "none"
                                }`}
                              >
                                {sub.review_status === "REVIEWED"
                                  ? "Graded"
                                  : sub.submitted
                                  ? "Needs Review"
                                  : "Not Submitted"}
                              </span>
                            </td>
                            <td className="text-right">
                              {sub.submitted ? (
                                <button
                                  type="button"
                                  className="an-btn-grade"
                                  onClick={() => openGradingModal(sub)}
                                >
                                  {sub.review_status === "REVIEWED" ? "Edit Grade" : "Grade"}
                                </button>
                              ) : (
                                <span className="text-slate-300 text-xs">Pending</span>
                              )}
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

          {/* TAB 4: CLASS OVERVIEW */}
          {activeTab === "overview" && (
            <div className="an-tab-pane">
              <div className="an-overview-grid">
                {classOverview.length === 0 ? (
                  <div className="an-empty-state full-width">
                    <Layers size={44} className="an-empty-icon" />
                    <h3>No classes assigned</h3>
                  </div>
                ) : (
                  classOverview.map((item) => (
                    <div key={item.offering_id} className="an-overview-card">
                      <div className="an-overview-header">
                        <div>
                          <h3 className="an-overview-code">{item.course_code}</h3>
                          <p className="an-overview-name">{item.course_name}</p>
                        </div>
                        <span className="an-overview-sec">Sec {item.section}</span>
                      </div>

                      <div className="an-overview-stats">
                        <div className="an-stat-item">
                          <span className="an-stat-num">{item.assignments_count}</span>
                          <span className="an-stat-desc">Assignments</span>
                        </div>
                        <div className="an-stat-item">
                          <span className="an-stat-num">{item.notes_count}</span>
                          <span className="an-stat-desc">Notes</span>
                        </div>
                        <div className="an-stat-item">
                          <span className="an-stat-num">{item.total_enrolled}</span>
                          <span className="an-stat-desc">Students</span>
                        </div>
                      </div>

                      <div className="an-overview-progress">
                        <div className="an-overview-prog-copy">
                          <span>Submissions Rate</span>
                          <strong>{item.completion_rate}%</strong>
                        </div>
                        <div className="an-progress-track">
                          <div
                            className="an-progress-bar"
                            style={{ width: `${Math.min(100, item.completion_rate)}%` }}
                          />
                        </div>
                      </div>

                      <div className="an-overview-footer">
                        <button
                          type="button"
                          className="an-btn-view-class"
                          onClick={() => {
                            setAssignmentClassFilter(String(item.offering_id));
                            setActiveTab("assignments");
                          }}
                        >
                          <span>Manage Assignments</span>
                          <ChevronRight size={15} />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* Right Sidebar Column (Quick Actions, Recent Uploads, Class Summary) */}
        <aside className="an-sidebar-column">
          {/* Quick Actions Card */}
          <div className="an-side-card">
            <h3 className="an-side-title">Quick Actions</h3>
            <div className="an-quick-actions-list">
              <button
                type="button"
                className="an-quick-action-item"
                onClick={openCreateAssignmentModal}
              >
                <div className="an-qa-icon blue">
                  <UploadCloud size={18} />
                </div>
                <div className="an-qa-copy">
                  <strong>Upload Assignment</strong>
                  <span>Add a new assignment</span>
                </div>
              </button>

              <button
                type="button"
                className="an-quick-action-item"
                onClick={openUploadNoteModal}
              >
                <div className="an-qa-icon green">
                  <BookOpen size={18} />
                </div>
                <div className="an-qa-copy">
                  <strong>Upload Notes</strong>
                  <span>Share study materials</span>
                </div>
              </button>

              <button
                type="button"
                className="an-quick-action-item"
                onClick={openCreateAssignmentModal}
              >
                <div className="an-qa-icon purple">
                  <Plus size={18} strokeWidth={2.4} />
                </div>
                <div className="an-qa-copy">
                  <strong>Create Assignment</strong>
                  <span>Set up with due date & limits</span>
                </div>
              </button>

              <button
                type="button"
                className="an-quick-action-item"
                onClick={() => setActiveTab("submissions")}
              >
                <div className="an-qa-icon sky">
                  <FileCheck size={18} />
                </div>
                <div className="an-qa-copy">
                  <strong>View All Submissions</strong>
                  <span>Check and grade submissions</span>
                </div>
              </button>
            </div>
          </div>

          {/* Recent Uploads Card */}
          <div className="an-side-card">
            <h3 className="an-side-title">Recent Uploads</h3>
            <div className="an-recent-list">
              {recentUploads.length === 0 ? (
                <p className="an-recent-empty">No recent uploads yet.</p>
              ) : (
                recentUploads.map((item, idx) => (
                  <div key={idx} className="an-recent-item">
                    <div
                      className={`an-recent-icon ${
                        item.file_type === "pdf" ? "pdf" : "doc"
                      }`}
                    >
                      <FileText size={16} />
                    </div>
                    <div className="an-recent-copy">
                      <strong className="an-recent-item-title" title={item.title}>
                        {item.title}
                      </strong>
                      <span className="an-recent-item-sub">
                        {item.course_code} • {item.date_label}
                        {item.extra_info ? ` • ${item.extra_info}` : ""}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
            <button
              type="button"
              className="an-card-footer-link"
              onClick={() => setActiveTab("notes")}
            >
              View All Notes
            </button>
          </div>

          {/* Class Summary Card */}
          <div className="an-side-card">
            <h3 className="an-side-title">Class Summary</h3>
            <div className="an-class-summary-list">
              {classOverview.slice(0, 4).map((c) => (
                <div key={c.offering_id} className="an-cs-item">
                  <div className="an-cs-icon">
                    <BookOpen size={16} />
                  </div>
                  <div className="an-cs-copy">
                    <strong>
                      {c.course_code} - {c.course_name}
                    </strong>
                    <span>
                      {c.assignments_count} assignment{c.assignments_count === 1 ? "" : "s"} •{" "}
                      {c.notes_count} note{c.notes_count === 1 ? "" : "s"} •{" "}
                      {c.submissions_count}/{c.total_enrolled} submitted
                    </span>
                  </div>
                </div>
              ))}
            </div>
            <button
              type="button"
              className="an-card-footer-link"
              onClick={() => setActiveTab("overview")}
            >
              View All Classes
            </button>
          </div>
        </aside>
      </div>

      {/* MODAL 1: Create / Edit Assignment */}
      {isAssignmentModalOpen && (
        <div className="an-modal-overlay">
          <div className="an-modal-container">
            <div className="an-modal-header">
              <h2>{editingAssignment ? "Edit Assignment" : "Create New Assignment"}</h2>
              <button
                type="button"
                className="an-modal-close-btn"
                onClick={() => setIsAssignmentModalOpen(false)}
                aria-label="Close modal"
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSaveAssignment} className="an-modal-form">
              <div className="an-form-grid">
                {/* Title */}
                <div className="an-form-group full-width">
                  <label htmlFor="asgn-title">
                    Assignment Title <span className="text-red-500">*</span>
                  </label>
                  <input
                    id="asgn-title"
                    type="text"
                    required
                    placeholder="e.g. Data Structures Assignment 1"
                    value={assignmentFormData.title}
                    onChange={(e) =>
                      setAssignmentFormData({ ...assignmentFormData, title: e.target.value })
                    }
                  />
                </div>

                {/* Class */}
                <div className="an-form-group">
                  <label htmlFor="asgn-class">
                    Course Offering / Class <span className="text-red-500">*</span>
                  </label>
                  <select
                    id="asgn-class"
                    required
                    value={assignmentFormData.offering_id}
                    onChange={(e) =>
                      setAssignmentFormData({ ...assignmentFormData, offering_id: e.target.value })
                    }
                  >
                    <option value="">Select Class</option>
                    {classes.map((c) => (
                      <option key={c.offering_id} value={c.offering_id}>
                        {c.course_code} - {c.course_name} (Sec {c.section})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Assignment Type */}
                <div className="an-form-group">
                  <label htmlFor="asgn-type">Assignment Type</label>
                  <select
                    id="asgn-type"
                    value={assignmentFormData.assignment_type}
                    onChange={(e) =>
                      setAssignmentFormData({
                        ...assignmentFormData,
                        assignment_type: e.target.value,
                      })
                    }
                  >
                    <option value="File Upload">File Upload</option>
                    <option value="Text Submission">Text Submission</option>
                    <option value="Both">Both (File or Text)</option>
                    <option value="Homework">Homework</option>
                    <option value="Lab Report">Lab Report</option>
                    <option value="Project">Project</option>
                    <option value="Essay">Essay</option>
                  </select>
                </div>

                {/* Due Date */}
                <div className="an-form-group">
                  <label htmlFor="asgn-due">
                    Due Date & Time <span className="text-red-500">*</span>
                  </label>
                  <input
                    id="asgn-due"
                    type="datetime-local"
                    required
                    value={assignmentFormData.due_date}
                    onChange={(e) =>
                      setAssignmentFormData({ ...assignmentFormData, due_date: e.target.value })
                    }
                  />
                </div>

                {/* Maximum Marks */}
                <div className="an-form-group">
                  <label htmlFor="asgn-marks">Maximum Marks</label>
                  <input
                    id="asgn-marks"
                    type="number"
                    min="1"
                    max="1000"
                    value={assignmentFormData.maximum_marks}
                    onChange={(e) =>
                      setAssignmentFormData({
                        ...assignmentFormData,
                        maximum_marks: e.target.value,
                      })
                    }
                  />
                </div>

                {/* Allowed File Types */}
                <div className="an-form-group">
                  <label htmlFor="asgn-filetypes">Allowed File Types</label>
                  <input
                    id="asgn-filetypes"
                    type="text"
                    placeholder="pdf,doc,docx,zip"
                    value={assignmentFormData.allowed_file_types}
                    onChange={(e) =>
                      setAssignmentFormData({
                        ...assignmentFormData,
                        allowed_file_types: e.target.value,
                      })
                    }
                  />
                </div>

                {/* Max File Size MB */}
                <div className="an-form-group">
                  <label htmlFor="asgn-size">Max File Size (MB)</label>
                  <input
                    id="asgn-size"
                    type="number"
                    min="1"
                    max="100"
                    value={assignmentFormData.maximum_file_size_mb}
                    onChange={(e) =>
                      setAssignmentFormData({
                        ...assignmentFormData,
                        maximum_file_size_mb: e.target.value,
                      })
                    }
                  />
                </div>

                {/* Status */}
                <div className="an-form-group">
                  <label htmlFor="asgn-status">Publication Status</label>
                  <select
                    id="asgn-status"
                    value={assignmentFormData.status}
                    onChange={(e) =>
                      setAssignmentFormData({ ...assignmentFormData, status: e.target.value })
                    }
                  >
                    <option value="PUBLISHED">Published (Visible to students)</option>
                    <option value="DRAFT">Draft (Hidden)</option>
                    <option value="CLOSED">Closed (Submissions ended)</option>
                  </select>
                </div>

                {/* Allow Late Submissions */}
                <div className="an-form-group checkbox-wrap">
                  <label className="an-checkbox-label">
                    <input
                      type="checkbox"
                      checked={assignmentFormData.allow_late_submission}
                      onChange={(e) =>
                        setAssignmentFormData({
                          ...assignmentFormData,
                          allow_late_submission: e.target.checked,
                        })
                      }
                    />
                    <span>Allow Late Submissions</span>
                  </label>
                </div>

                {/* Optional Attachment File */}
                <div className="an-form-group full-width">
                  <label htmlFor="asgn-attachment">
                    Worksheet / Reference Attachment (Optional)
                  </label>
                  <input
                    id="asgn-attachment"
                    type="file"
                    onChange={(e) =>
                      setAssignmentFormData({
                        ...assignmentFormData,
                        file: e.target.files[0] || null,
                      })
                    }
                  />
                  {editingAssignment?.has_attachment && !assignmentFormData.file && (
                    <span className="an-attachment-note">
                      Current attachment: {editingAssignment.attachment_name || "Attachment on file"}
                    </span>
                  )}
                </div>

                {/* Description */}
                <div className="an-form-group full-width">
                  <label htmlFor="asgn-desc">Instructions & Description</label>
                  <textarea
                    id="asgn-desc"
                    rows={4}
                    placeholder="Provide detailed instructions for your students..."
                    value={assignmentFormData.description}
                    onChange={(e) =>
                      setAssignmentFormData({
                        ...assignmentFormData,
                        description: e.target.value,
                      })
                    }
                  />
                </div>
              </div>

              <div className="an-modal-actions">
                <button
                  type="button"
                  className="an-btn-secondary"
                  onClick={() => setIsAssignmentModalOpen(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="an-btn-primary" disabled={actionLoading}>
                  {actionLoading ? "Saving..." : editingAssignment ? "Update Assignment" : "Create Assignment"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: Upload Notes */}
      {isNoteModalOpen && (
        <div className="an-modal-overlay">
          <div className="an-modal-container">
            <div className="an-modal-header">
              <h2>Upload Study Material / Notes</h2>
              <button
                type="button"
                className="an-modal-close-btn"
                onClick={() => setIsNoteModalOpen(false)}
                aria-label="Close modal"
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleUploadNote} className="an-modal-form">
              <div className="an-form-grid">
                <div className="an-form-group full-width">
                  <label htmlFor="note-title">
                    Document Title <span className="text-red-500">*</span>
                  </label>
                  <input
                    id="note-title"
                    type="text"
                    required
                    placeholder="e.g. Chapter 4 - Tree Traversals Notes"
                    value={noteFormData.title}
                    onChange={(e) =>
                      setNoteFormData({ ...noteFormData, title: e.target.value })
                    }
                  />
                </div>

                <div className="an-form-group">
                  <label htmlFor="note-class">
                    Course Offering / Class <span className="text-red-500">*</span>
                  </label>
                  <select
                    id="note-class"
                    required
                    value={noteFormData.offering_id}
                    onChange={(e) =>
                      setNoteFormData({ ...noteFormData, offering_id: e.target.value })
                    }
                  >
                    <option value="">Select Class</option>
                    {classes.map((c) => (
                      <option key={c.offering_id} value={c.offering_id}>
                        {c.course_code} - {c.course_name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="an-form-group">
                  <label htmlFor="note-cat">Category</label>
                  <select
                    id="note-cat"
                    value={noteFormData.category}
                    onChange={(e) =>
                      setNoteFormData({ ...noteFormData, category: e.target.value })
                    }
                  >
                    <option value="LECTURE_NOTES">Lecture Notes</option>
                    <option value="REFERENCE">Reference Material</option>
                    <option value="PRACTICAL">Practical / Lab Manual</option>
                    <option value="TUTORIAL">Tutorial</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>

                <div className="an-form-group full-width">
                  <label htmlFor="note-file">
                    Upload File (PDF, DOCX, PPTX, ZIP) <span className="text-red-500">*</span>
                  </label>
                  <input
                    id="note-file"
                    type="file"
                    required
                    onChange={(e) =>
                      setNoteFormData({ ...noteFormData, file: e.target.files[0] || null })
                    }
                  />
                </div>

                <div className="an-form-group full-width">
                  <label htmlFor="note-desc">Description / Outline</label>
                  <textarea
                    id="note-desc"
                    rows={3}
                    placeholder="Brief description or lecture outline..."
                    value={noteFormData.description}
                    onChange={(e) =>
                      setNoteFormData({ ...noteFormData, description: e.target.value })
                    }
                  />
                </div>
              </div>

              <div className="an-modal-actions">
                <button
                  type="button"
                  className="an-btn-secondary"
                  onClick={() => setIsNoteModalOpen(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="an-btn-primary green" disabled={actionLoading}>
                  {actionLoading ? "Uploading..." : "Upload Material"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 3: Grade / Evaluate Submission */}
      {currentGradingSubmission && (
        <div className="an-modal-overlay">
          <div className="an-modal-container grading">
            <div className="an-modal-header">
              <h2>Grade Submission</h2>
              <button
                type="button"
                className="an-modal-close-btn"
                onClick={() => setCurrentGradingSubmission(null)}
                aria-label="Close modal"
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSaveGrade} className="an-modal-form">
              <div className="an-grading-info-box">
                <div className="an-grading-row">
                  <span>Student:</span>
                  <strong>
                    {currentGradingSubmission.name} ({currentGradingSubmission.roll_number})
                  </strong>
                </div>
                <div className="an-grading-row">
                  <span>Submitted At:</span>
                  <span>{currentGradingSubmission.submitted_at || "N/A"}</span>
                </div>
                {currentGradingSubmission.is_late && (
                  <div className="an-grading-row">
                    <span>Late Submission:</span>
                    <strong className="text-amber-600">Yes (Late)</strong>
                  </div>
                )}
                {currentGradingSubmission.has_file && (
                  <div className="an-grading-row">
                    <span>Submitted File:</span>
                    <button
                      type="button"
                      className="an-btn-download-sm"
                      onClick={() =>
                        handleDownloadSubmissionFile(
                          currentGradingSubmission.submission_id,
                          currentGradingSubmission.file_name
                        )
                      }
                    >
                      <Download size={14} className="mr-1 inline" />
                      <span>{currentGradingSubmission.file_name || "Download"}</span>
                    </button>
                  </div>
                )}
                {currentGradingSubmission.submission_text && (
                  <div className="an-grading-text-box">
                    <span>Student Answer / Notes:</span>
                    <p>{currentGradingSubmission.submission_text}</p>
                  </div>
                )}
              </div>

              <div className="an-form-grid">
                <div className="an-form-group">
                  <label htmlFor="grade-marks">
                    Marks Awarded (out of {currentGradingSubmission.maximum_marks || 100})
                  </label>
                  <input
                    id="grade-marks"
                    type="number"
                    step="0.5"
                    min="0"
                    max={currentGradingSubmission.maximum_marks || 100}
                    required
                    placeholder="e.g. 85"
                    value={gradeInput}
                    onChange={(e) => setGradeInput(e.target.value)}
                  />
                </div>

                <div className="an-form-group full-width">
                  <label htmlFor="grade-feedback">Feedback & Comments</label>
                  <textarea
                    id="grade-feedback"
                    rows={4}
                    placeholder="Provide constructive feedback for the student..."
                    value={feedbackInput}
                    onChange={(e) => setFeedbackInput(e.target.value)}
                  />
                </div>
              </div>

              <div className="an-modal-actions">
                <button
                  type="button"
                  className="an-btn-secondary"
                  onClick={() => setCurrentGradingSubmission(null)}
                >
                  Cancel
                </button>
                <button type="submit" className="an-btn-primary" disabled={actionLoading}>
                  {actionLoading ? "Saving..." : "Save Grade & Feedback"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
