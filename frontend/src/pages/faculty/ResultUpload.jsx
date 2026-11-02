import { useCallback, useEffect, useMemo, useState, useRef } from "react";
import {
  AlertCircle,
  AlertTriangle,
  Bookmark,
  Calendar,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Download,
  FileSpreadsheet,
  FileText,
  GraduationCap,
  Info,
  MoreVertical,
  RotateCcw,
  Send,
  Upload,
} from "lucide-react";

import {
  getFacultyCourses,
  getFacultyAssessments,
  getFacultyResultsSummary,
  getFacultyStudentsForEntry,
  saveFacultyDraftMarks,
  submitFacultyMarks,
  importFacultyMarks,
} from "../../services/facultyResultsService";
import PageState from "../../components/PageState";
import "./ResultUpload.css";

// UGC / AICTE 10-point scale grade calculator
function calculateClientGrade(marks, maxMarks = 30) {
  if (marks === null || marks === undefined || marks === "" || isNaN(Number(marks))) {
    return { grade: "-", status: "Pending", gradePoints: 0.0, percentage: null };
  }

  const num = Number(marks);
  const max = Number(maxMarks) > 0 ? Number(maxMarks) : 100.0;
  const pct = (num / max) * 100.0;

  let grade;
  let gradePoints;

  if (pct >= 95.0) {
    grade = "A+";
    gradePoints = 10.0;
  } else if (pct >= 90.0) {
    grade = "A+";
    gradePoints = 9.0;
  } else if (pct >= 80.0) {
    grade = "A";
    gradePoints = 8.0;
  } else if (pct >= 70.0) {
    grade = "B+";
    gradePoints = 7.0;
  } else if (pct >= 60.0) {
    grade = "B";
    gradePoints = 6.0;
  } else if (pct >= 50.0) {
    grade = "C+";
    gradePoints = 5.0;
  } else if (pct >= 45.0) {
    grade = "C";
    gradePoints = 5.0;
  } else if (pct >= 40.0) {
    grade = "D";
    gradePoints = 4.0;
  } else {
    grade = "F";
    gradePoints = 0.0;
  }

  return {
    grade,
    status: "Complete",
    gradePoints,
    percentage: Math.round(pct * 10) / 10,
  };
}

export default function ResultUpload() {
  // Page states
  const [pageLoading, setPageLoading] = useState(true);
  const [tableLoading, setTableLoading] = useState(false);
  const [pageError, setPageError] = useState(null);

  // Courses & selection options
  const [courses, setCourses] = useState([]);
  const [selectedOfferingId, setSelectedOfferingId] = useState("");
  const [academicYears, setAcademicYears] = useState([]);
  const [selectedYear, setSelectedYear] = useState("");
  const [semesters, setSemesters] = useState([]);
  const [selectedSemester, setSelectedSemester] = useState("");

  // Assessments & types
  const [assessments, setAssessments] = useState([]);
  const [selectedAssessmentId, setSelectedAssessmentId] = useState("");
  const [selectedAssessmentType, setSelectedAssessmentType] = useState("INTERNAL");

  // Summary Metrics (4 Top Cards)
  const [summary, setSummary] = useState({
    total_students: 0,
    draft: 0,
    submitted: 0,
    published: 0,
    submission_status: "NOT_STARTED",
    review_remarks: null,
    submitted_at: null,
    published_at: null,
  });

  // Student Marks Entry Roster
  const [students, setStudents] = useState([]);
  const [selectedRows, setSelectedRows] = useState(new Set());
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [validationErrors, setValidationErrors] = useState({});

  // Pagination (10 per page default)
  const [currentPage, setCurrentPage] = useState(1);
  const rowsPerPage = 10;

  // Active Row Context Menu
  const [activeMenuId, setActiveMenuId] = useState(null);

  // Modals & Action States
  const [submitModalOpen, setSubmitModalOpen] = useState(false);
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [importFile, setImportFile] = useState(null);
  const [importStatus, setImportStatus] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [toast, setToast] = useState(null);

  const fileInputRef = useRef(null);

  const showToast = (message, type = "success") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  // 1. Initial Load: Fetch Assigned Courses
  useEffect(() => {
    let isMounted = true;

    async function loadInitialCourses() {
      setPageLoading(true);
      setPageError(null);
      try {
        const res = await getFacultyCourses();
        if (!isMounted) return;

        if (res?.success && Array.isArray(res.data)) {
          setCourses(res.data);

          // Populate distinct academic years and semesters
          const years = Array.from(new Set(res.data.map((c) => c.academic_year).filter(Boolean)));
          const sems = Array.from(new Set(res.data.map((c) => c.semester).filter(Boolean))).sort((a, b) => a - b);
          setAcademicYears(years);
          setSemesters(sems);

          if (res.data.length > 0) {
            const first = res.data[0];
            setSelectedOfferingId(String(first.offering_id));
            setSelectedYear(first.academic_year || "");
            setSelectedSemester(String(first.semester || ""));
          }
        } else {
          setCourses([]);
        }
      } catch (err) {
        if (!isMounted) return;
        console.error("Failed to load faculty courses:", err);
        setPageError(err?.response?.data?.message || "Failed to load assigned courses.");
      } finally {
        if (isMounted) {
          setPageLoading(false);
        }
      }
    }

    void loadInitialCourses();

    return () => {
      isMounted = false;
    };
  }, []);

  // 2. Fetch Assessments when Offering changes
  useEffect(() => {
    if (!selectedOfferingId) return;

    let isMounted = true;

    async function loadAssessments() {
      try {
        const res = await getFacultyAssessments(Number(selectedOfferingId));
        if (!isMounted) return;

        if (res?.success && Array.isArray(res.data) && res.data.length > 0) {
          setAssessments(res.data);
          setSelectedAssessmentId(String(res.data[0].assessment_id));
          setSelectedAssessmentType(res.data[0].assessment_type || "INTERNAL");
        } else {
          setAssessments([]);
          setSelectedAssessmentId("");
        }
      } catch (err) {
        if (!isMounted) return;
        console.error("Failed to load assessments:", err);
      }
    }

    void loadAssessments();

    return () => {
      isMounted = false;
    };
  }, [selectedOfferingId]);

  // Current active assessment object
  const currentAssessment = useMemo(() => {
    if (!selectedAssessmentId) {
      return assessments[0] || { assessment_name: "Test 1", max_marks: 30 };
    }
    return assessments.find((a) => String(a.assessment_id) === String(selectedAssessmentId)) || assessments[0] || { assessment_name: "Test 1", max_marks: 30 };
  }, [assessments, selectedAssessmentId]);

  // Current active offering object
  const currentOffering = useMemo(() => {
    if (!selectedOfferingId) return courses[0] || null;
    return courses.find((c) => String(c.offering_id) === String(selectedOfferingId)) || courses[0] || null;
  }, [courses, selectedOfferingId]);

  // 3. Load Student Roster and Summary Metrics
  const loadRosterAndSummary = useCallback(async () => {
    if (!selectedOfferingId) return;

    setTableLoading(true);
    setValidationErrors({});
    setSelectedRows(new Set());

    try {
      const [rosterRes, summaryRes] = await Promise.all([
        getFacultyStudentsForEntry(Number(selectedOfferingId), selectedAssessmentId ? Number(selectedAssessmentId) : undefined),
        getFacultyResultsSummary(Number(selectedOfferingId), selectedAssessmentId ? Number(selectedAssessmentId) : undefined),
      ]);

      if (rosterRes?.success && rosterRes.data?.students) {
        const maxMarks = currentAssessment?.max_marks || 30;
        const normalized = rosterRes.data.students.map((st) => {
          const calc = calculateClientGrade(st.marks_obtained, maxMarks);
          return {
            ...st,
            max_marks: maxMarks,
            grade: st.grade || calc.grade,
            status: calc.status,
            remarks: st.remarks || (calc.status === "Pending" ? "No marks entered" : "-"),
          };
        });
        setStudents(normalized);
        setHasUnsavedChanges(false);
      }

      if (summaryRes?.success && summaryRes.data) {
        setSummary(summaryRes.data);
      }
    } catch (err) {
      console.error("Failed to load students and summary:", err);
      showToast(err?.response?.data?.message || "Failed to load student roster", "error");
    } finally {
      setTableLoading(false);
    }
  }, [selectedOfferingId, selectedAssessmentId, currentAssessment]);

  // Auto-load student roster on initial selection
  useEffect(() => {
    if (!selectedOfferingId || !selectedAssessmentId) return;

    let isMounted = true;

    async function fetchRosterData() {
      try {
        const [rosterRes, summaryRes] = await Promise.all([
          getFacultyStudentsForEntry(Number(selectedOfferingId), Number(selectedAssessmentId)),
          getFacultyResultsSummary(Number(selectedOfferingId), Number(selectedAssessmentId)),
        ]);

        if (!isMounted) return;

        if (rosterRes?.success && rosterRes.data?.students) {
          const maxMarks = currentAssessment?.max_marks || 30;
          const normalized = rosterRes.data.students.map((st) => {
            const calc = calculateClientGrade(st.marks_obtained, maxMarks);
            return {
              ...st,
              max_marks: maxMarks,
              grade: st.grade || calc.grade,
              status: calc.status,
              remarks: st.remarks || (calc.status === "Pending" ? "No marks entered" : "-"),
            };
          });
          setStudents(normalized);
          setHasUnsavedChanges(false);
        }

        if (summaryRes?.success && summaryRes.data) {
          setSummary(summaryRes.data);
        }
      } catch (err) {
        if (!isMounted) return;
        console.error("Failed to load students and summary:", err);
      }
    }

    void fetchRosterData();

    return () => {
      isMounted = false;
    };
  }, [selectedOfferingId, selectedAssessmentId, currentAssessment]);

  // Handle Mark input change
  const handleMarkChange = (studentId, rawValue) => {
    const maxMarks = currentAssessment?.max_marks || 30;

    setStudents((prev) =>
      prev.map((st) => {
        if (st.student_id !== studentId) return st;

        if (rawValue === "") {
          return {
            ...st,
            marks_obtained: "",
            grade: "-",
            status: "Pending",
            remarks: "No marks entered",
          };
        }

        const num = Number(rawValue);
        const calc = calculateClientGrade(num, maxMarks);

        return {
          ...st,
          marks_obtained: rawValue,
          grade: calc.grade,
          status: calc.status,
          remarks: "-",
        };
      })
    );

    setHasUnsavedChanges(true);

    // Validate range
    if (rawValue !== "") {
      const num = Number(rawValue);
      if (isNaN(num) || num < 0 || num > maxMarks) {
        setValidationErrors((prev) => ({
          ...prev,
          [studentId]: `Must be 0 – ${maxMarks}`,
        }));
      } else {
        setValidationErrors((prev) => {
          const copy = { ...prev };
          delete copy[studentId];
          return copy;
        });
      }
    } else {
      setValidationErrors((prev) => {
        const copy = { ...prev };
        delete copy[studentId];
        return copy;
      });
    }
  };

  // Row selection toggling
  const handleToggleSelectAll = (e) => {
    if (e.target.checked) {
      setSelectedRows(new Set(students.map((s) => s.student_id)));
    } else {
      setSelectedRows(new Set());
    }
  };

  const handleToggleRow = (studentId) => {
    setSelectedRows((prev) => {
      const next = new Set(prev);
      if (next.has(studentId)) {
        next.delete(studentId);
      } else {
        next.add(studentId);
      }
      return next;
    });
  };

  // Row context menu action
  const handleRowAction = (action, student) => {
    setActiveMenuId(null);
    const maxMarks = currentAssessment?.max_marks || 30;

    if (action === "CLEAR") {
      handleMarkChange(student.student_id, "");
    } else if (action === "FULL") {
      handleMarkChange(student.student_id, String(maxMarks));
    } else if (action === "ABSENT") {
      setStudents((prev) =>
        prev.map((s) =>
          s.student_id === student.student_id
            ? {
                ...s,
                marks_obtained: "0",
                grade: "F",
                status: "Complete",
                remarks: "Absent",
              }
            : s
        )
      );
      setHasUnsavedChanges(true);
    }
  };

  // 4. Save Draft
  const handleSaveDraft = async () => {
    if (!selectedOfferingId) return;

    setActionLoading(true);
    try {
      const scoresPayload = students.map((s) => ({
        student_id: s.student_id,
        marks_obtained: s.marks_obtained !== "" && s.marks_obtained !== null ? Number(s.marks_obtained) : null,
        remarks: s.remarks,
      }));

      const res = await saveFacultyDraftMarks({
        offering_id: Number(selectedOfferingId),
        assessment_id: selectedAssessmentId ? Number(selectedAssessmentId) : undefined,
        scores: scoresPayload,
      });

      if (res?.success) {
        showToast(res.message || "Draft marks saved successfully!");
        setHasUnsavedChanges(false);
        // Refresh summary counters
        const sumRes = await getFacultyResultsSummary(Number(selectedOfferingId), Number(selectedAssessmentId));
        if (sumRes?.success && sumRes.data) {
          setSummary(sumRes.data);
        }
      }
    } catch (err) {
      console.error("Failed to save draft:", err);
      showToast(err?.response?.data?.message || "Failed to save draft marks.", "error");
    } finally {
      setActionLoading(false);
    }
  };

  // 5. Submit Results Workflow
  const handleOpenSubmitModal = () => {
    // Check missing marks
    const missing = students.filter((s) => s.marks_obtained === "" || s.marks_obtained === null);
    if (missing.length > 0) {
      // Highlight validation errors on missing rows
      const errors = {};
      missing.forEach((s) => {
        errors[s.student_id] = "Mark is required";
      });
      setValidationErrors(errors);
    }
    setSubmitModalOpen(true);
  };

  const handleConfirmSubmit = async () => {
    setActionLoading(true);
    try {
      const scoresPayload = students.map((s) => ({
        student_id: s.student_id,
        marks_obtained: s.marks_obtained !== "" && s.marks_obtained !== null ? Number(s.marks_obtained) : null,
        remarks: s.remarks,
      }));

      const res = await submitFacultyMarks({
        offering_id: Number(selectedOfferingId),
        assessment_id: selectedAssessmentId ? Number(selectedAssessmentId) : undefined,
        scores: scoresPayload,
      });

      if (res?.success) {
        showToast("Results submitted to administration for review!", "success");
        setSubmitModalOpen(false);
        setHasUnsavedChanges(false);
        void loadRosterAndSummary();
      }
    } catch (err) {
      console.error("Failed to submit results:", err);
      showToast(err?.response?.data?.message || "Submission failed. Please check marks.", "error");
    } finally {
      setActionLoading(false);
    }
  };

  // 6. Download CSV Template
  const handleDownloadTemplate = () => {
    if (!students.length) {
      showToast("No students available to export template.", "error");
      return;
    }

    const courseCode = currentOffering?.course_code || "COURSE";
    const maxMarks = currentAssessment?.max_marks || 30;

    let csvContent = "data:text/csv;charset=utf-8,";
    csvContent += "Roll No,Student Name,Max Marks,Marks Obtained,Remarks\n";

    students.forEach((s) => {
      const marksVal = s.marks_obtained !== null && s.marks_obtained !== "" ? s.marks_obtained : "";
      const remarksVal = s.remarks && s.remarks !== "No marks entered" ? s.remarks : "";
      csvContent += `"${s.roll_no}","${s.student_name}",${maxMarks},"${marksVal}","${remarksVal}"\n`;
    });

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `Marks_Template_${courseCode}_${currentAssessment?.assessment_name || "Assessment"}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast("Template downloaded successfully");
  };

  // 7. Import CSV Marks
  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setImportFile(file);
      setImportStatus(null);
    }
  };

  const handleProcessImport = async () => {
    if (!importFile) {
      showToast("Please choose a CSV file first.", "error");
      return;
    }

    setActionLoading(true);
    setImportStatus(null);

    const reader = new FileReader();
    reader.onload = async (event) => {
      try {
        const text = event.target?.result;
        const lines = String(text).split(/\r\n|\n/).filter((l) => l.trim().length > 0);

        if (lines.length <= 1) {
          showToast("CSV file is empty or missing data rows.", "error");
          setActionLoading(false);
          return;
        }

        const headers = lines[0].split(",").map((h) => h.replace(/["']/g, "").trim().toLowerCase());
        const rollIdx = headers.findIndex((h) => h.includes("roll") || h.includes("enroll"));
        const marksIdx = headers.findIndex((h) => h.includes("mark") || h.includes("score"));
        const remarksIdx = headers.findIndex((h) => h.includes("remark"));

        if (rollIdx === -1 || marksIdx === -1) {
          showToast("CSV header must contain 'Roll No' and 'Marks Obtained'.", "error");
          setActionLoading(false);
          return;
        }

        const rows = [];
        for (let i = 1; i < lines.length; i++) {
          const cells = lines[i].split(",").map((c) => c.replace(/["']/g, "").trim());
          if (cells[rollIdx]) {
            rows.push({
              roll_no: cells[rollIdx],
              marks_obtained: cells[marksIdx] || "",
              remarks: remarksIdx !== -1 ? cells[remarksIdx] : "-",
            });
          }
        }

        const res = await importFacultyMarks({
          offering_id: Number(selectedOfferingId),
          assessment_id: Number(selectedAssessmentId),
          rows,
        });

        if (res?.success && res.data) {
          const { valid_records, errors } = res.data;

          if (valid_records.length > 0) {
            const marksMap = new Map();
            valid_records.forEach((vr) => {
              marksMap.set(vr.roll_no.trim().toUpperCase(), vr);
            });

            const maxMarks = currentAssessment?.max_marks || 30;

            setStudents((prev) =>
              prev.map((s) => {
                const imported = marksMap.get(s.roll_no.trim().toUpperCase());
                if (imported) {
                  const calc = calculateClientGrade(imported.marks_obtained, maxMarks);
                  return {
                    ...s,
                    marks_obtained: imported.marks_obtained,
                    grade: calc.grade,
                    status: calc.status,
                    remarks: imported.remarks || "-",
                  };
                }
                return s;
              })
            );

            setHasUnsavedChanges(true);
            setImportStatus({
              successCount: valid_records.length,
              errorCount: errors.length,
              errors,
            });
            showToast(`Imported marks for ${valid_records.length} students!`, "success");
          } else {
            setImportStatus({
              successCount: 0,
              errorCount: errors.length,
              errors,
            });
            showToast("No valid rows were imported.", "error");
          }
        }
      } catch (err) {
        console.error("Import error:", err);
        showToast(err?.response?.data?.message || "Error processing CSV file.", "error");
      } finally {
        setActionLoading(false);
      }
    };

    reader.readAsText(importFile);
  };

  // Reset filter selections
  const handleResetFilters = () => {
    if (courses.length > 0) {
      const first = courses[0];
      setSelectedOfferingId(String(first.offering_id));
      setSelectedYear(first.academic_year || "");
      setSelectedSemester(String(first.semester || ""));
      void loadRosterAndSummary();
    }
  };

  // Pagination calculation
  const totalPages = Math.ceil(students.length / rowsPerPage) || 1;
  const paginatedStudents = useMemo(() => {
    const start = (currentPage - 1) * rowsPerPage;
    return students.slice(start, start + rowsPerPage);
  }, [students, currentPage, rowsPerPage]);

  const isAllSelected = students.length > 0 && selectedRows.size === students.length;
  const isSubmissionLocked = summary.submission_status === "SUBMITTED" || summary.submission_status === "PUBLISHED";

  if (pageLoading) {
    return (
      <div className="result-upload-page">
        <PageState type="loading" title="Loading Result Upload" message="Fetching course assignments and assessments..." />
      </div>
    );
  }

  if (pageError) {
    return (
      <div className="result-upload-page">
        <PageState
          type="error"
          title="Unable to Access Results"
          message={pageError}
          actionLabel="Try Again"
          onAction={() => window.location.reload()}
        />
      </div>
    );
  }

  return (
    <div className="result-upload-page">
      {/* Toast Notification */}
      {toast && (
        <div className={`faculty-toast toast-${toast.type}`} role="status">
          {toast.type === "success" ? <Check size={18} /> : <AlertCircle size={18} />}
          <span>{toast.message}</span>
        </div>
      )}

      {/* A. Page Header Banner */}
      <header className="result-upload-header-banner">
        <div className="header-banner-left">
          <div className="header-banner-icon">
            <FileSpreadsheet size={28} color="#ffffff" strokeWidth={2.4} />
          </div>
          <div>
            <h1 className="header-banner-title">Result Upload</h1>
            <p className="header-banner-subtitle">
              Enter and manage marks for your assigned courses. Submit results for admin review.
            </p>
          </div>
        </div>

        <div className="header-banner-right">
          <div className="academic-badge-card">
            <Calendar size={18} className="badge-icon-blue" />
            <div className="badge-text">
              <span className="badge-label">Academic Year</span>
              <strong className="badge-value">{currentOffering?.academic_year || selectedYear || "2024 - 2025"}</strong>
            </div>
          </div>

          <div className="academic-badge-card">
            <GraduationCap size={18} className="badge-icon-blue" />
            <div className="badge-text">
              <span className="badge-label">Semester</span>
              <strong className="badge-value">
                {currentOffering?.semester ? `Semester ${currentOffering.semester}` : "Spring Semester"}
              </strong>
            </div>
          </div>
        </div>
      </header>

      {/* B. Course and Assessment Selection Filter Bar */}
      <section className="result-filter-card" aria-label="Course and Assessment Selectors">
        <div className="filter-grid">
          {/* Course */}
          <div className="filter-group">
            <label htmlFor="select-course">Course</label>
            <select
              id="select-course"
              value={selectedOfferingId}
              onChange={(e) => setSelectedOfferingId(e.target.value)}
            >
              {courses.map((c) => (
                <option key={c.offering_id} value={c.offering_id}>
                  {c.course_name} ({c.course_code})
                </option>
              ))}
            </select>
          </div>

          {/* Academic Year */}
          <div className="filter-group">
            <label htmlFor="select-year">Academic Year</label>
            <select
              id="select-year"
              value={selectedYear}
              onChange={(e) => setSelectedYear(e.target.value)}
            >
              {academicYears.map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>
          </div>

          {/* Semester */}
          <div className="filter-group">
            <label htmlFor="select-semester">Semester</label>
            <select
              id="select-semester"
              value={selectedSemester}
              onChange={(e) => setSelectedSemester(e.target.value)}
            >
              {semesters.map((s) => (
                <option key={s} value={s}>
                  Semester {s}
                </option>
              ))}
            </select>
          </div>

          {/* Assessment Type */}
          <div className="filter-group">
            <label htmlFor="select-type">Assessment Type</label>
            <select
              id="select-type"
              value={selectedAssessmentType}
              onChange={(e) => setSelectedAssessmentType(e.target.value)}
            >
              <option value="INTERNAL">Internal Test</option>
              <option value="MIDTERM">Midterm Exam</option>
              <option value="PRACTICAL">Practical Exam</option>
              <option value="FINAL">Final Semester Exam</option>
            </select>
          </div>

          {/* Assessment */}
          <div className="filter-group">
            <label htmlFor="select-assessment">Assessment</label>
            <select
              id="select-assessment"
              value={selectedAssessmentId}
              onChange={(e) => setSelectedAssessmentId(e.target.value)}
            >
              {assessments.map((a) => (
                <option key={a.assessment_id} value={a.assessment_id}>
                  {a.assessment_name} (Max: {a.max_marks})
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="filter-actions">
          <button
            type="button"
            className="btn-filter-primary"
            onClick={loadRosterAndSummary}
            disabled={tableLoading}
            aria-label="Load Students"
          >
            <RotateCcw size={15} className={tableLoading ? "spin" : ""} />
            <span>Load Students</span>
          </button>

          <button
            type="button"
            className="btn-filter-secondary"
            onClick={handleResetFilters}
            aria-label="Reset Filter"
          >
            <RotateCcw size={15} />
            <span>Reset</span>
          </button>
        </div>
      </section>

      {/* C. 4 Summary Cards */}
      <section className="result-cards-grid" aria-label="Course Assessment Summary">
        {/* Card 1: Total Students */}
        <div className="result-summary-card">
          <div className="summary-card-inner">
            <div className="summary-icon-box icon-blue">
              <FileText size={22} />
            </div>
            <div className="summary-details">
              <span className="summary-title">Total Students</span>
              <strong className="summary-number">{summary.total_students}</strong>
              <span className="summary-subtext">Enrolled in this course</span>
            </div>
          </div>
        </div>

        {/* Card 2: Draft */}
        <div className="result-summary-card">
          <div className="summary-card-inner">
            <div className="summary-icon-box icon-amber">
              <Bookmark size={22} />
            </div>
            <div className="summary-details">
              <span className="summary-title">Draft</span>
              <strong className="summary-number">{summary.draft}</strong>
              <span className="summary-subtext">Saved but not submitted</span>
            </div>
          </div>
        </div>

        {/* Card 3: Submitted */}
        <div className="result-summary-card">
          <div className="summary-card-inner">
            <div className="summary-icon-box icon-blue">
              <Send size={22} />
            </div>
            <div className="summary-details">
              <span className="summary-title">Submitted</span>
              <strong className="summary-number">{summary.submitted}</strong>
              <span className="summary-subtext">Waiting for admin review</span>
            </div>
          </div>
        </div>

        {/* Card 4: Published */}
        <div className="result-summary-card">
          <div className="summary-card-inner">
            <div className="summary-icon-box icon-green">
              <CheckCircle2 size={22} />
            </div>
            <div className="summary-details">
              <span className="summary-title">Published</span>
              <strong className="summary-number">{summary.published}</strong>
              <span className="summary-subtext">Visible to students</span>
            </div>
          </div>
        </div>
      </section>

      {/* Status Notice Banners */}
      {summary.submission_status === "RETURNED" && summary.review_remarks && (
        <div className="workflow-status-banner banner-returned">
          <AlertTriangle size={20} className="banner-icon-returned" />
          <div className="banner-content">
            <strong>Returned for Revision by Administration</strong>
            <p>{summary.review_remarks}</p>
          </div>
        </div>
      )}

      {summary.submission_status === "SUBMITTED" && (
        <div className="workflow-status-banner banner-submitted">
          <Info size={20} className="banner-icon-submitted" />
          <div className="banner-content">
            <strong>Results Submitted for Review</strong>
            <p>
              Marks were submitted on {summary.submitted_at?.slice(0, 10)}. Awaiting administrator approval before publication.
            </p>
          </div>
        </div>
      )}

      {summary.submission_status === "PUBLISHED" && (
        <div className="workflow-status-banner banner-published">
          <CheckCircle2 size={20} className="banner-icon-published" />
          <div className="banner-content">
            <strong>Results Published</strong>
            <p>These marks are verified and currently visible on student academic cards.</p>
          </div>
        </div>
      )}

      {/* D. Student Marks Table Section */}
      <section className="student-marks-section">
        {/* Table Top Header and Workflow Actions */}
        <div className="marks-table-header">
          <h2 className="marks-table-title">Student Marks</h2>

          <div className="marks-table-actions">
            <button
              type="button"
              className="btn-table-action"
              onClick={handleDownloadTemplate}
              title="Download CSV Marks Template"
            >
              <Download size={15} />
              <span>Download Template</span>
            </button>

            <button
              type="button"
              className="btn-table-action"
              onClick={() => setImportModalOpen(true)}
              disabled={isSubmissionLocked}
              title="Import Marks from CSV"
            >
              <Upload size={15} />
              <span>Import Marks</span>
            </button>

            <button
              type="button"
              className="btn-table-action"
              onClick={handleSaveDraft}
              disabled={actionLoading || isSubmissionLocked}
              title="Save Progress as Draft"
            >
              <Bookmark size={15} />
              <span>{hasUnsavedChanges ? "Save Draft *" : "Save Draft"}</span>
            </button>

            <button
              type="button"
              className="btn-table-submit"
              onClick={handleOpenSubmitModal}
              disabled={actionLoading || isSubmissionLocked}
              title="Submit Marks to Administration"
            >
              <Send size={15} />
              <span>Submit Results</span>
            </button>
          </div>
        </div>

        {/* Responsive Table */}
        <div className="table-responsive-wrapper">
          <table className="faculty-marks-table">
            <thead>
              <tr>
                <th className="th-checkbox">
                  <input
                    type="checkbox"
                    checked={isAllSelected}
                    onChange={handleToggleSelectAll}
                    aria-label="Select all students"
                  />
                </th>
                <th className="th-index">#</th>
                <th className="th-roll">Roll No</th>
                <th className="th-name">Student Name</th>
                <th className="th-center">Max Marks</th>
                <th className="th-center">Marks Obtained</th>
                <th className="th-center">Grade</th>
                <th className="th-center">Status</th>
                <th>Remarks</th>
                <th className="th-actions">Actions</th>
              </tr>
            </thead>
            <tbody>
              {paginatedStudents.length > 0 ? (
                paginatedStudents.map((st) => {
                  const hasError = Boolean(validationErrors[st.student_id]);
                  const isPending = st.status === "Pending";
                  const isSelected = selectedRows.has(st.student_id);

                  return (
                    <tr key={st.student_id} className={isSelected ? "row-selected" : ""}>
                      <td className="td-checkbox">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => handleToggleRow(st.student_id)}
                          aria-label={`Select ${st.student_name}`}
                        />
                      </td>
                      <td className="td-index">{st.index}</td>
                      <td className="td-roll font-mono">{st.roll_no}</td>
                      <td className="td-name font-medium">{st.student_name}</td>
                      <td className="td-center text-muted">{st.max_marks}</td>
                      <td className="td-center">
                        <div className="marks-input-wrapper">
                          <input
                            type="text"
                            className={`marks-input ${hasError ? "input-error" : ""}`}
                            value={st.marks_obtained !== null && st.marks_obtained !== undefined ? st.marks_obtained : ""}
                            onChange={(e) => handleMarkChange(st.student_id, e.target.value)}
                            disabled={isSubmissionLocked}
                            placeholder="—"
                            aria-label={`Marks for ${st.student_name}`}
                          />
                          {hasError && <span className="inline-error-text">{validationErrors[st.student_id]}</span>}
                        </div>
                      </td>
                      <td className="td-center">
                        <span className={`grade-tag grade-${String(st.grade).toLowerCase().replace("+", "-plus")}`}>
                          {st.grade}
                        </span>
                      </td>
                      <td className="td-center">
                        <span className={`status-pill pill-${st.status?.toLowerCase()}`}>
                          {st.status}
                        </span>
                      </td>
                      <td className="td-remarks">
                        {isPending ? (
                          <span className="remarks-pending">No marks entered</span>
                        ) : (
                          <span className="remarks-normal">{st.remarks || "-"}</span>
                        )}
                      </td>
                      <td className="td-actions">
                        <div className="row-action-menu-anchor">
                          <button
                            type="button"
                            className="btn-row-menu"
                            onClick={() => setActiveMenuId(activeMenuId === st.student_id ? null : st.student_id)}
                            aria-label="Row actions"
                          >
                            <MoreVertical size={16} />
                          </button>

                          {activeMenuId === st.student_id && (
                            <div className="row-action-dropdown">
                              <button
                                type="button"
                                onClick={() => handleRowAction("FULL", st)}
                              >
                                Full Marks ({st.max_marks})
                              </button>
                              <button
                                type="button"
                                onClick={() => handleRowAction("ABSENT", st)}
                              >
                                Mark Absent
                              </button>
                              <button
                                type="button"
                                onClick={() => handleRowAction("CLEAR", st)}
                              >
                                Clear Marks
                              </button>
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan="10" className="table-empty-row">
                    No enrolled students found for the selected course offering.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Table Pagination Bar */}
        <div className="marks-pagination-bar">
          <div className="pagination-count-label">
            Showing {students.length === 0 ? 0 : (currentPage - 1) * rowsPerPage + 1} -{" "}
            {Math.min(currentPage * rowsPerPage, students.length)} of {students.length} students
          </div>

          <div className="pagination-nav-buttons">
            <button
              type="button"
              className="pagination-btn-arrow"
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage <= 1}
              aria-label="Previous Page"
            >
              <ChevronLeft size={16} />
            </button>

            {Array.from({ length: totalPages }, (_, i) => i + 1).map((num) => (
              <button
                key={num}
                type="button"
                className={`pagination-btn-num ${currentPage === num ? "active" : ""}`}
                onClick={() => setCurrentPage(num)}
              >
                {num}
              </button>
            ))}

            <button
              type="button"
              className="pagination-btn-arrow"
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage >= totalPages}
              aria-label="Next Page"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>

        {/* Bottom Instructional Alert */}
        <div className="bottom-guidance-notice">
          <Info size={18} className="guidance-icon" />
          <span>
            <strong>Note:</strong> Ensure all marks are entered correctly before submitting. You can save your
            progress as a draft and submit once all marks are verified.
          </span>
        </div>
      </section>

      {/* =======================================================
          MODAL 1: SUBMISSION CONFIRMATION
         ======================================================= */}
      {submitModalOpen && (
        <div className="faculty-modal-backdrop" onClick={() => setSubmitModalOpen(false)}>
          <div className="faculty-dialog-box" onClick={(e) => e.stopPropagation()}>
            <div className="dialog-header">
              <Send size={22} className="dialog-icon-blue" />
              <h3>Submit Results for Review</h3>
            </div>

            <p className="dialog-body-copy">
              You are submitting the results for <strong>{currentOffering?.course_name}</strong> (
              {currentOffering?.course_code}) – <strong>{currentAssessment?.assessment_name}</strong>.
            </p>

            <div className="dialog-summary-strip">
              <div>
                <span>Total Enrolled:</span>
                <strong>{students.length}</strong>
              </div>
              <div>
                <span>Marks Entered:</span>
                <strong>{students.filter((s) => s.marks_obtained !== "" && s.marks_obtained !== null).length}</strong>
              </div>
              <div>
                <span>Missing Scores:</span>
                <strong className={students.filter((s) => s.marks_obtained === "" || s.marks_obtained === null).length > 0 ? "text-error" : ""}>
                  {students.filter((s) => s.marks_obtained === "" || s.marks_obtained === null).length}
                </strong>
              </div>
            </div>

            <div className="dialog-warning-callout">
              <AlertCircle size={16} />
              <span>
                Once submitted, marks will be submitted to the institution administrators for review. Faculty edits
                will be locked until reviewed.
              </span>
            </div>

            <div className="dialog-actions">
              <button
                type="button"
                className="btn-dialog-outline"
                onClick={() => setSubmitModalOpen(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-dialog-primary"
                onClick={handleConfirmSubmit}
                disabled={actionLoading}
              >
                {actionLoading ? "Submitting..." : "Confirm & Submit"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* =======================================================
          MODAL 2: CSV IMPORT MODAL
         ======================================================= */}
      {importModalOpen && (
        <div className="faculty-modal-backdrop" onClick={() => setImportModalOpen(false)}>
          <div className="faculty-dialog-box" onClick={(e) => e.stopPropagation()}>
            <div className="dialog-header">
              <Upload size={22} className="dialog-icon-blue" />
              <h3>Import Marks from CSV</h3>
            </div>

            <p className="dialog-body-copy">
              Upload a CSV file containing columns <code>Roll No</code> and <code>Marks Obtained</code>.
            </p>

            <div
              className="dropzone-box"
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload size={32} className="dropzone-icon" />
              <p>Click to select CSV file or drag & drop</p>
              <small>{importFile ? importFile.name : "CSV files only"}</small>
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                style={{ display: "none" }}
                onChange={handleFileSelect}
              />
            </div>

            {importStatus && (
              <div className="import-status-summary">
                <span className="text-success">
                  ✓ {importStatus.successCount} valid rows ready to import
                </span>
                {importStatus.errorCount > 0 && (
                  <span className="text-error">
                    ⚠ {importStatus.errorCount} rows rejected
                  </span>
                )}
                {importStatus.errors?.length > 0 && (
                  <ul className="import-error-list">
                    {importStatus.errors.slice(0, 3).map((err, idx) => (
                      <li key={idx}>{err}</li>
                    ))}
                    {importStatus.errors.length > 3 && (
                      <li>...and {importStatus.errors.length - 3} more errors</li>
                    )}
                  </ul>
                )}
              </div>
            )}

            <div className="dialog-actions">
              <button
                type="button"
                className="btn-dialog-outline"
                onClick={() => {
                  setImportModalOpen(false);
                  setImportFile(null);
                  setImportStatus(null);
                }}
              >
                Close
              </button>
              <button
                type="button"
                className="btn-dialog-primary"
                onClick={handleProcessImport}
                disabled={!importFile || actionLoading}
              >
                {actionLoading ? "Processing..." : "Process Import"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
