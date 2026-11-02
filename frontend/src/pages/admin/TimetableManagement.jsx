import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faCalendarDays,
  faCheck,
  faCheckCircle,
  faCheckDouble,
  faChevronLeft,
  faChevronRight,
  faCloudArrowUp,
  faDownload,
  faFileExcel,
  faFileLines,
  faGraduationCap,
  faInfoCircle,
  faLayerGroup,
  faRotateRight,
  faSave,
  faSearch,
  faShieldHalved,
  faSpinner,
  faTriangleExclamation,
  faUserClock,
  faUsers,
  faXmark,
} from "@fortawesome/free-solid-svg-icons";

import {
  getAdminTimetable,
  getImportAcademicYears,
  getImportWorkbookSheets,
  analyzeTimetableImport,
  commitTimetableImport,
  getFacultyAdjustments,
  createFacultyAdjustment,
  cancelFacultyAdjustment,
  updateTimetableEntry,
} from "../../services/timetableService";
import EditTimetableModal from "../../components/EditTimetableModal";
import { getAdminFaculty } from "../../services/adminService";

import campusBannerImage from "../../../image/admin_campus_banner.jpg";
import { formatAcademicYear } from "../../utils/academicYearUtils";
import "./TimetableManagement.css";

const steps = [
  "Upload & Extract",
  "Preview & Validate",
  "Map & Resolve",
  "Review & Commit",
  "Import Summary",
];

const tabs = ["Timetable", "Courses", "Faculty", "Classrooms"];

const dayOrder = [
  "MONDAY",
  "TUESDAY",
  "WEDNESDAY",
  "THURSDAY",
  "FRIDAY",
  "SATURDAY",
  "SUNDAY",
];

const MAX_FILE_SIZE = 10 * 1024 * 1024;
const PAGE_SIZE = 10;

function titleCase(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function getPageNumbers(currentPage, totalPages) {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }
  if (currentPage <= 4) {
    return [1, 2, 3, 4, 5, "...", totalPages];
  }
  if (currentPage >= totalPages - 3) {
    return [
      1,
      "...",
      totalPages - 4,
      totalPages - 3,
      totalPages - 2,
      totalPages - 1,
      totalPages,
    ];
  }
  return [1, "...", currentPage - 1, currentPage, currentPage + 1, "...", totalPages];
}

function displayTime(value) {
  if (!value) return "—";
  const [hourText, minuteText] = String(value).split(":");
  const hour = Number(hourText);
  if (Number.isNaN(hour)) return String(value);
  return `${String(hour).padStart(2, "0")}:${String(minuteText || "00").padStart(2, "0")}`;
}

function mapTimetableEntry(item) {
  return {
    id: item.timetable_entry_id,
    offeringId: item.offering_id,
    day: titleCase(item.day_of_week),
    dayKey: String(item.day_of_week || "").toUpperCase(),
    startTime: item.start_time || "",
    endTime: item.end_time || "",
    room: item.room || "Not assigned",
    faculty: item.faculty_name || "Not assigned",
    facultyId: item.faculty_id || null,
    department: item.department_name || "",
    courseCode: item.course_code || "",
    courseName: item.course_name || "",
    section: item.section || "",
    semester: item.semester ?? "",
    academicYear: item.academic_year || "",
    activeAdjustment: item.active_adjustment || null,
    effectiveFaculty: item.effective_faculty_name || item.faculty_name || "Not assigned",
  };
}

function getErrorMessage(error, fallback) {
  return error?.response?.data?.message || error?.message || fallback;
}

function getMappingStatusLabel(status) {
  const labels = {
    pending: "Awaiting match",
    matched: "Auto-matched",
    warning: "With warning",
    unmatched: "Unmatched",
    ambiguous: "Ambiguous",
    conflict: "Conflict",
    duplicate: "Duplicate",
    selected: "Selected",
  };
  return labels[status] || "Needs review";
}

function TimetableManagement() {
  const location = useLocation();
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const adjustmentSectionRef = useRef(null);

  // Workflow steps: 1: Upload, 2: Preview, 3: Map, 4: Review, 5: Summary
  const [activeStep, setActiveStep] = useState(1);
  const [file, setFile] = useState(null);
  const [academicYears, setAcademicYears] = useState(["2026-2027", "2025-2026", "2024-2025"]);
  const [academicYear, setAcademicYear] = useState("2026-2027");
  const [customAcademicYear, setCustomAcademicYear] = useState("");
  const [availableSheets, setAvailableSheets] = useState([]);
  const [selectedSheet, setSelectedSheet] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState("");

  // Extraction results
  const [analysisResult, setAnalysisResult] = useState(null);
  const [entryOverrides, setEntryOverrides] = useState({});
  const [selectedRows, setSelectedRows] = useState({});
  const [importMode, setImportMode] = useState("add_missing");
  const [confirmCommit, setConfirmCommit] = useState(false);
  const [commitLoading, setCommitLoading] = useState(false);
  const [commitResult, setCommitResult] = useState(null);
  const [commitError, setCommitError] = useState("");
  const [notice, setNotice] = useState("");

  // Edit Timetable Entry Modal
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [selectedEntryForEdit, setSelectedEntryForEdit] = useState(null);

  // Persisted Database Timetable
  const [activeTab, setActiveTab] = useState("Timetable");
  const [entries, setEntries] = useState([]);
  const [timetableLoading, setTimetableLoading] = useState(true);
  const [timetableError, setTimetableError] = useState("");
  const [semesterFilter, setSemesterFilter] = useState("All");
  const [sectionFilter, setSectionFilter] = useState("All");
  const [dayFilter, setDayFilter] = useState("All");
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);

  // Step 2 Preview pagination
  const [previewPage, setPreviewPage] = useState(1);

  // Step 3 Map & Resolve filters & pagination
  const [mappingSearch, setMappingSearch] = useState("");
  const [mappingStatusFilter, setMappingStatusFilter] = useState("All");
  const [mappingSemesterFilter, setMappingSemesterFilter] = useState("All");
  const [mappingSectionFilter, setMappingSectionFilter] = useState("All");
  const [mappingPage, setMappingPage] = useState(1);

  // Faculty list for adjustment
  const [allFaculty, setAllFaculty] = useState([]);
  const [adjustmentsList, setAdjustmentsList] = useState([]);
  const [adjustmentOpen, setAdjustmentOpen] = useState(false);
  const [selectedCurrentFaculty, setSelectedCurrentFaculty] = useState("");
  const [adjustmentTargetId, setAdjustmentTargetId] = useState("");
  const [substituteSearch, setSubstituteSearch] = useState("");
  const [selectedSubstituteId, setSelectedSubstituteId] = useState("");
  const [adjustmentReason, setAdjustmentReason] = useState("Faculty unavailable");
  const [customAdjustmentReason, setCustomAdjustmentReason] = useState("");
  const [effectiveDate, setEffectiveDate] = useState(() => new Date().toLocaleDateString("en-CA"));
  const [requestApproval, setRequestApproval] = useState(false);
  const [adjustmentLoading, setAdjustmentLoading] = useState(false);
  const [adjustmentMessage, setAdjustmentMessage] = useState("");
  const [adjustmentError, setAdjustmentError] = useState("");

  const effectiveAcademicYear =
    academicYear === "CUSTOM" ? customAcademicYear.trim() : academicYear;

  // Auto-scroll or open faculty adjustment if navigated via /admin/timetable/faculty-adjustment
  useEffect(() => {
    if (location.pathname.includes("faculty-adjustment")) {
      const timer = setTimeout(() => {
        setAdjustmentOpen(true);
        adjustmentSectionRef.current?.scrollIntoView({ behavior: "smooth" });
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [location.pathname]);

  const loadTimetable = useCallback(async () => {
    setTimetableLoading(true);
    setTimetableError("");
    try {
      const response = await getAdminTimetable();
      if (!response?.success || !Array.isArray(response.data)) {
        throw new Error("Unexpected timetable response from the server.");
      }
      setEntries(response.data.map(mapTimetableEntry));
    } catch (error) {
      setTimetableError(getErrorMessage(error, "Could not load the saved timetable."));
    } finally {
      setTimetableLoading(false);
    }
  }, []);

  const loadAdjustments = useCallback(async () => {
    try {
      const res = await getFacultyAdjustments();
      if (res?.success && Array.isArray(res.data)) {
        setAdjustmentsList(res.data);
      }
    } catch (err) {
      console.debug("Could not load faculty adjustments:", err?.message);
    }
  }, []);

  const loadFaculty = useCallback(async () => {
    try {
      const res = await getAdminFaculty();
      if (res?.success && Array.isArray(res.data)) {
        setAllFaculty(res.data);
      }
    } catch (err) {
      console.debug("Could not load faculty list:", err?.message);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      void loadTimetable();
      void loadAdjustments();
      void loadFaculty();
    }, 0);
    return () => clearTimeout(timer);
  }, [loadTimetable, loadAdjustments, loadFaculty]);

  useEffect(() => {
    const timer = setTimeout(() => {
      async function loadYears() {
        try {
          const res = await getImportAcademicYears();
          if (res?.success && Array.isArray(res.academic_years) && res.academic_years.length > 0) {
            setAcademicYears(res.academic_years);
            if (res.default) setAcademicYear(res.default);
          }
        } catch (err) {
          console.debug("Could not load academic years:", err?.message);
        }
      }
      void loadYears();
    }, 0);
    return () => clearTimeout(timer);
  }, []);

  // Filter options
  const semesters = useMemo(
    () =>
      [
        ...new Set(
          entries
            .map((entry) => String(entry.semester))
            .filter((value) => value && value !== "undefined")
        ),
      ].sort((a, b) => Number(a) - Number(b)),
    [entries]
  );

  const sections = useMemo(
    () =>
      [
        ...new Set(
          entries
            .filter(
              (entry) =>
                semesterFilter === "All" || String(entry.semester) === semesterFilter
            )
            .map((entry) => String(entry.section))
            .filter((value) => value && value !== "undefined")
        ),
      ].sort(),
    [entries, semesterFilter]
  );

  const days = useMemo(
    () =>
      [
        ...new Set(
          entries
            .map((entry) => entry.day)
            .filter(Boolean)
        ),
      ].sort((a, b) => dayOrder.indexOf(a.toUpperCase()) - dayOrder.indexOf(b.toUpperCase())),
    [entries]
  );

  const filteredEntries = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();

    return entries
      .filter(
        (entry) =>
          semesterFilter === "All" || String(entry.semester) === semesterFilter
      )
      .filter(
        (entry) =>
          sectionFilter === "All" || String(entry.section) === sectionFilter
      )
      .filter(
        (entry) =>
          dayFilter === "All" || entry.day.toLowerCase() === dayFilter.toLowerCase()
      )
      .filter((entry) =>
        [
          entry.day,
          entry.courseCode,
          entry.courseName,
          entry.faculty,
          entry.effectiveFaculty,
          entry.room,
          entry.section,
          entry.academicYear,
        ].some((value) => String(value || "").toLowerCase().includes(query))
      )
      .sort((a, b) => {
        const aDay = dayOrder.indexOf(a.dayKey);
        const bDay = dayOrder.indexOf(b.dayKey);
        return (
          (aDay === -1 ? 99 : aDay) - (bDay === -1 ? 99 : bDay) ||
          a.startTime.localeCompare(b.startTime)
        );
      });
  }, [entries, semesterFilter, sectionFilter, dayFilter, searchQuery]);

  const totalPages = Math.max(1, Math.ceil(filteredEntries.length / PAGE_SIZE));
  const paginatedEntries = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE;
    return filteredEntries.slice(start, start + PAGE_SIZE);
  }, [filteredEntries, currentPage]);

  const distinctCourses = useMemo(() => {
    const courses = new Map();
    entries.forEach((entry) => {
      const key = entry.courseCode || entry.courseName;
      if (key && !courses.has(key)) courses.set(key, entry);
    });
    return [...courses.values()];
  }, [entries]);

  const distinctFaculty = useMemo(
    () =>
      [
        ...new Set(
          entries
            .map((entry) => entry.faculty)
            .filter((name) => name && name !== "Not assigned")
        ),
      ].sort(),
    [entries]
  );

  const distinctRooms = useMemo(
    () =>
      [
        ...new Set(
          entries
            .map((entry) => entry.room)
            .filter((room) => room && room !== "Not assigned")
        ),
      ].sort(),
    [entries]
  );

  // Merge analysis entries with admin overrides
  const processedRows = useMemo(() => {
    if (!analysisResult?.entries) return [];

    return analysisResult.entries.map((item) => {
      const override = entryOverrides[item.index] || {};
      const courseId =
        override.course_id !== undefined ? override.course_id : item.course_id;
      const facultyId =
        override.faculty_id !== undefined ? override.faculty_id : item.faculty_id;
      const room = override.room !== undefined ? override.room : item.room;
      const sectionVal =
        override.section !== undefined ? override.section : item.section;
      const semesterVal =
        override.semester !== undefined ? override.semester : item.semester;
      const dayOfWeek =
        override.day_of_week !== undefined ? override.day_of_week : item.day_of_week;
      const startTime =
        override.start_time !== undefined ? override.start_time : item.start_time;
      const endTime =
        override.end_time !== undefined ? override.end_time : item.end_time;

      const courseObj = (analysisResult.available_courses || []).find(
        (c) => c.course_id === Number(courseId)
      );
      const facultyObj = (analysisResult.available_faculty || []).find(
        (f) => f.faculty_id === Number(facultyId)
      );

      let effectiveStatus = item.status;
      if (override.course_id) {
        effectiveStatus = "matched";
      }

      return {
        ...item,
        day_of_week: dayOfWeek,
        start_time: startTime,
        end_time: endTime,
        course_id: courseId,
        course_code: courseObj ? courseObj.course_code : item.course_code,
        course_name: courseObj ? courseObj.course_name : item.course_name,
        semester: courseObj ? courseObj.semester : semesterVal,
        faculty_id: facultyId,
        faculty_name: facultyObj ? facultyObj.name : item.faculty_name,
        room: room,
        section: sectionVal,
        status: effectiveStatus,
        isSelected: selectedRows[item.index] !== false,
      };
    });
  }, [analysisResult, entryOverrides, selectedRows]);

  const mappingCounts = useMemo(() => {
    const counts = {
      total: processedRows.length,
      matched: 0,
      warning: 0,
      ambiguous: 0,
      unmatched: 0,
      conflict: 0,
      duplicate: 0,
      selected: 0,
    };

    processedRows.forEach((row) => {
      if (Object.hasOwn(counts, row.status)) counts[row.status] += 1;
      if (row.isSelected) counts.selected += 1;
    });

    return counts;
  }, [processedRows]);

  const mappingFilterOptions = useMemo(
    () => ({
      semesters: [
        ...new Set(processedRows.map((row) => String(row.semester)).filter(Boolean)),
      ].sort((a, b) => Number(a) - Number(b)),
      sections: [
        ...new Set(processedRows.map((row) => String(row.section)).filter(Boolean)),
      ].sort(),
    }),
    [processedRows]
  );

  const filteredProcessedRows = useMemo(() => {
    const query = mappingSearch.trim().toLowerCase();

    return processedRows.filter((row) => {
      const matchesStatus =
        mappingStatusFilter === "All" || row.status === mappingStatusFilter;
      const matchesSemester =
        mappingSemesterFilter === "All" ||
        String(row.semester) === mappingSemesterFilter;
      const matchesSection =
        mappingSectionFilter === "All" ||
        String(row.section) === mappingSectionFilter;

      const matchesSearch = [
        row.course_code,
        row.course_name,
        row.faculty_name,
        row.room,
        row.section,
        row.day_of_week,
        row.raw_cell,
      ].some((val) => String(val || "").toLowerCase().includes(query));

      return matchesStatus && matchesSemester && matchesSection && matchesSearch;
    });
  }, [
    processedRows,
    mappingSearch,
    mappingStatusFilter,
    mappingSemesterFilter,
    mappingSectionFilter,
  ]);

  // Step 2 Pagination
  const totalPreviewPages = Math.max(1, Math.ceil(processedRows.length / PAGE_SIZE));
  const safePreviewPage = Math.min(previewPage, totalPreviewPages);
  const paginatedPreviewRows = useMemo(() => {
    const start = (safePreviewPage - 1) * PAGE_SIZE;
    return processedRows.slice(start, start + PAGE_SIZE);
  }, [processedRows, safePreviewPage]);

  // Step 3 Pagination
  const totalMappingPages = Math.max(1, Math.ceil(filteredProcessedRows.length / PAGE_SIZE));
  const safeMappingPage = Math.min(mappingPage, totalMappingPages);
  const paginatedMappingRows = useMemo(() => {
    const start = (safeMappingPage - 1) * PAGE_SIZE;
    return filteredProcessedRows.slice(start, start + PAGE_SIZE);
  }, [filteredProcessedRows, safeMappingPage]);

  // File validation and handling
  function processFileSelection(selectedFile) {
    if (!selectedFile) return;

    setPreviewError("");
    setNotice("");
    setAnalysisResult(null);
    setEntryOverrides({});
    setSelectedRows({});
    setCommitResult(null);
    setCommitError("");
    setAvailableSheets([]);
    setSelectedSheet("");
    setPreviewPage(1);
    setMappingPage(1);

    const name = selectedFile.name.toLowerCase();

    if (selectedFile.size === 0) {
      setFile(null);
      setPreviewError("The selected file is empty. Please choose a valid timetable file.");
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    if (selectedFile.size > MAX_FILE_SIZE) {
      setFile(null);
      setPreviewError("The workbook must be 10 MB or smaller.");
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    if (name.endsWith(".xls")) {
      setFile(null);
      setPreviewError("Older Excel (.xls) format detected. Please save your file as modern Excel (.xlsx) workbook before importing.");
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    if (name.endsWith(".pdf")) {
      setFile(null);
      setPreviewError("Timetable extraction requires structured tabular columns. Please convert or export your timetable into Excel (.xlsx) format before importing.");
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    if (!name.endsWith(".xlsx")) {
      setFile(null);
      setPreviewError("Unsupported file type. Please upload an Excel (.xlsx) workbook.");
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    setFile(selectedFile);
    setActiveStep(1);

    // Auto-discover worksheets
    getImportWorkbookSheets(selectedFile)
      .then((sheetsRes) => {
        if (sheetsRes?.success && Array.isArray(sheetsRes.sheets)) {
          setAvailableSheets(sheetsRes.sheets);
          if (sheetsRes.recommended) {
            setSelectedSheet(sheetsRes.recommended);
          } else if (sheetsRes.sheets.length > 0) {
            setSelectedSheet(sheetsRes.sheets[0]);
          }
        }
      })
      .catch(() => {
        // Worksheet auto-discovery handles fallback gracefully
      });
  }

  function handleFileChange(event) {
    const selectedFile = event.target.files?.[0];
    processFileSelection(selectedFile);
  }

  function handleDrop(event) {
    event.preventDefault();
    setIsDragging(false);
    const droppedFile = event.dataTransfer.files?.[0];
    processFileSelection(droppedFile);
  }

  function handleDragOver(event) {
    event.preventDefault();
    setIsDragging(true);
  }

  function handleDragLeave(event) {
    event.preventDefault();
    setIsDragging(false);
  }

  function handleClearFile() {
    setFile(null);
    setAnalysisResult(null);
    setEntryOverrides({});
    setSelectedRows({});
    setAvailableSheets([]);
    setSelectedSheet("");
    setPreviewError("");
    setNotice("");
    setPreviewPage(1);
    setMappingPage(1);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  async function handleAnalyze() {
    if (!file) {
      setPreviewError("Please choose a timetable file first.");
      return;
    }

    if (!effectiveAcademicYear) {
      setPreviewError("Please select or enter a valid academic year.");
      return;
    }

    setPreviewLoading(true);
    setPreviewError("");
    setNotice("");
    setCommitResult(null);
    setCommitError("");

    try {
      const res = await analyzeTimetableImport(
        file,
        effectiveAcademicYear,
        selectedSheet
      );

      if (!res?.success || !Array.isArray(res.entries)) {
        throw new Error(res?.message || "Could not analyze this timetable workbook.");
      }

      setAnalysisResult(res);
      setEntryOverrides({});

      // Pre-select rows that do not have critical conflicts
      const initialSelection = {};
      res.entries.forEach((item) => {
        initialSelection[item.index] =
          item.status !== "conflict" && item.status !== "duplicate";
      });
      setSelectedRows(initialSelection);

      setActiveStep(2);
      setPreviewPage(1);
      setMappingPage(1);
      if (res.total_rows === 0) {
        const errorDetail = res.parse_errors?.length ? ` (${res.parse_errors[0]})` : "";
        setPreviewError(
          `Parsed 0 entries from sheet "${res.source_sheet}". Please verify the worksheet contains scheduled teaching periods and standard headers.${errorDetail}`
        );
      } else {
        setNotice(
          `Parsed ${res.total_rows} entries from sheet "${res.source_sheet}". Review the extracted records below.`
        );
      }
    } catch (error) {
      setPreviewError(getErrorMessage(error, "Timetable extraction and analysis failed."));
    } finally {
      setPreviewLoading(false);
    }
  }

  function downloadPreviewCsv() {
    if (!processedRows.length) return;

    const columns = [
      "source_row",
      "day_of_week",
      "period",
      "start_time",
      "end_time",
      "class_group",
      "course_code",
      "course_name",
      "faculty_name",
      "room",
      "status",
      "raw_cell",
    ];

    const escapeCsv = (value) =>
      `"${String(value ?? "").replace(/"/g, '""')}"`;

    const lines = [
      columns.map(escapeCsv).join(","),
      ...processedRows.map((entry) =>
        columns.map((column) => escapeCsv(entry[column])).join(",")
      ),
    ];

    const blob = new Blob(["\uFEFF" + lines.join("\r\n")], {
      type: "text/csv;charset=utf-8;",
    });

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `timetable-preview-${effectiveAcademicYear}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  function toggleRowSelection(index) {
    setSelectedRows((prev) => ({
      ...prev,
      [index]: !prev[index],
    }));
  }

  function toggleSelectAll(select) {
    setSelectedRows((prev) => {
      const updated = { ...prev };
      const targets =
        filteredProcessedRows.length < processedRows.length
          ? filteredProcessedRows
          : processedRows;
      targets.forEach((r) => {
        updated[r.index] = select;
      });
      return updated;
    });
  }

  function updateEntryOverride(index, updates) {
    setEntryOverrides((prev) => ({
      ...prev,
      [index]: {
        ...(prev[index] || {}),
        ...updates,
      },
    }));
  }

  async function handleCommitImport() {
    const selectedEntries = processedRows.filter(
      (r) => r.isSelected && r.course_id
    );

    if (!selectedEntries.length) {
      setCommitError("Select at least one valid row with an assigned course to import.");
      return;
    }

    setCommitLoading(true);
    setCommitError("");

    const payload = {
      academic_year: effectiveAcademicYear,
      import_mode: importMode,
      entries: selectedEntries.map((r) => ({
        course_id: r.course_id,
        faculty_id: r.faculty_id || null,
        semester: r.semester || 1,
        section: r.section || "A",
        room: r.room || null,
        day_of_week: r.day_of_week,
        start_time: r.start_time,
        end_time: r.end_time,
      })),
    };

    try {
      const res = await commitTimetableImport(payload);
      if (!res?.success) {
        throw new Error(res?.message || "Import failed on the server.");
      }

      setCommitResult(res.data);
      setActiveStep(5);
      setNotice(res.message);
      void loadTimetable();
      void loadAdjustments();
    } catch (err) {
      setCommitError(getErrorMessage(err, "Failed to commit timetable import. All changes rolled back."));
    } finally {
      setCommitLoading(false);
    }
  }

  function resetWizard() {
    setActiveStep(1);
    setFile(null);
    setAnalysisResult(null);
    setEntryOverrides({});
    setSelectedRows({});
    setCommitResult(null);
    setCommitError("");
    setPreviewError("");
    setNotice("");
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  function goToStep(targetStep) {
    if (targetStep === 1) {
      setActiveStep(1);
      return;
    }
    if (!analysisResult) {
      setPreviewError("Upload a workbook and run analysis first.");
      return;
    }
    if (targetStep <= 4 || (targetStep === 5 && commitResult)) {
      setActiveStep(targetStep);
    }
  }

  // Edit Timetable Entry Modal handlers
  function handleOpenEditModal(targetRow) {
    setSelectedEntryForEdit(targetRow);
    setEditModalOpen(true);
  }

  function handleCloseEditModal() {
    setEditModalOpen(false);
    setSelectedEntryForEdit(null);
  }

  async function handleSaveTimetableEdit({ day, startTime, endTime, room, entry, isPersisted }) {
    if (isPersisted) {
      const payload = {
        day_of_week: day,
        start_time: startTime,
        end_time: endTime,
        room: room.trim() || null,
        offering_id: entry.offeringId || entry.offering_id || null,
      };

      const res = await updateTimetableEntry(entry.id, payload);
      if (!res?.success) {
        throw new Error(res?.message || "Failed to update timetable entry.");
      }

      setEntries((prev) =>
        prev.map((e) => (e.id === entry.id ? mapTimetableEntry(res.data) : e))
      );
      void loadTimetable();

      setNotice(
        `Timetable entry updated successfully (${titleCase(day)} ${startTime}–${endTime}, Room ${room.trim() || "Not assigned"}).`
      );
    } else {
      const dayName = titleCase(day);
      updateEntryOverride(entry.index, {
        day_of_week: dayName,
        start_time: startTime,
        end_time: endTime,
        room: room.trim(),
      });

      setNotice(
        `Extracted timetable entry updated for import (${dayName} ${startTime}–${endTime}, Room ${room.trim() || "Not assigned"}).`
      );
    }
  }

  // Emergency Faculty Replacement handlers
  function openAdjustment(entry = null) {
    setAdjustmentOpen(true);
    setAdjustmentMessage("");
    setAdjustmentError("");

    if (entry) {
      setSelectedCurrentFaculty(entry.faculty || "");
      setAdjustmentTargetId(String(entry.id));
    } else {
      setSelectedCurrentFaculty("");
      setAdjustmentTargetId("");
    }

    setSubstituteSearch("");
    setSelectedSubstituteId("");
    setAdjustmentReason("Faculty unavailable");
    setCustomAdjustmentReason("");
    setEffectiveDate(new Date().toLocaleDateString("en-CA"));
    setRequestApproval(false);

    setTimeout(() => {
      adjustmentSectionRef.current?.scrollIntoView({ behavior: "smooth" });
    }, 100);
  }

  function cancelAdjustmentForm() {
    setAdjustmentOpen(false);
    setAdjustmentMessage("");
    setAdjustmentError("");
  }

  async function submitAdjustment(event) {
    event.preventDefault();
    setAdjustmentMessage("");
    setAdjustmentError("");

    if (!selectedCurrentFaculty) {
      setAdjustmentError("Select the current assigned faculty member.");
      return;
    }

    if (!adjustmentTargetId) {
      setAdjustmentError("Select the affected class to reassign.");
      return;
    }

    const selectedEntry = entries.find((e) => String(e.id) === String(adjustmentTargetId));
    if (!selectedEntry) {
      setAdjustmentError("Selected timetable entry was not found.");
      return;
    }

    if (!selectedSubstituteId) {
      setAdjustmentError("Select a substitute faculty member from the list.");
      return;
    }

    if (String(selectedSubstituteId) === String(selectedEntry.facultyId)) {
      setAdjustmentError("The substitute faculty member must be different from the currently assigned faculty.");
      return;
    }

    if (!effectiveDate) {
      setAdjustmentError("Specify an effective date for the adjustment.");
      return;
    }

    const reason =
      adjustmentReason === "Other"
        ? customAdjustmentReason.trim()
        : adjustmentReason;

    if (!reason) {
      setAdjustmentError("Enter a reason for the faculty replacement.");
      return;
    }

    setAdjustmentLoading(true);

    try {
      const payload = {
        timetable_entry_id: Number(adjustmentTargetId),
        substitute_faculty_id: Number(selectedSubstituteId),
        effective_date: effectiveDate,
        reason: reason,
        request_approval: requestApproval,
      };

      const res = await createFacultyAdjustment(payload);
      if (!res?.success) {
        throw new Error(res?.message || "Failed to create faculty adjustment.");
      }

      setAdjustmentMessage(res.message);
      void loadTimetable();
      void loadAdjustments();
      setAdjustmentTargetId("");
      setSubstituteSearch("");
      setSelectedSubstituteId("");
    } catch (err) {
      setAdjustmentError(getErrorMessage(err, "Faculty adjustment failed."));
    } finally {
      setAdjustmentLoading(false);
    }
  }

  async function handleCancelExistingAdjustment(adjId) {
    if (!window.confirm("Cancel this faculty adjustment and revert to the original assignment?")) return;
    try {
      const res = await cancelFacultyAdjustment(adjId);
      if (res?.success) {
        void loadTimetable();
        void loadAdjustments();
      }
    } catch (err) {
      alert(getErrorMessage(err, "Could not cancel adjustment."));
    }
  }

  // Filtered substitute faculty options (excluding current)
  const substituteFacultyOptions = useMemo(() => {
    const query = substituteSearch.trim().toLowerCase();
    return allFaculty.filter((f) => {
      const name = f.name || f.user?.name || "";
      return (
        name !== selectedCurrentFaculty &&
        name.toLowerCase().includes(query)
      );
    });
  }, [allFaculty, selectedCurrentFaculty, substituteSearch]);

  const resetFilters = () => {
    setSemesterFilter("All");
    setSectionFilter("All");
    setDayFilter("All");
    setSearchQuery("");
    setCurrentPage(1);
  };

  return (
    <section className="timetable-page">
      {/* 1. Header Banner matching reference design */}
      <header
        className="timetable-banner-card"
        style={{ backgroundImage: `url(${campusBannerImage})` }}
      >
        <div className="timetable-banner-overlay" />
        <div className="timetable-banner-content">
          <div className="timetable-banner-left">
            <div className="timetable-banner-icon">
              <FontAwesomeIcon icon={faCalendarDays} />
            </div>
            <div>
              <h2>Timetable Management</h2>
              <p>Upload timetable, extract data, validate and manage academic schedule.</p>
              <small>Automate faculty assignments and keep your academic data up to date.</small>
            </div>
          </div>
          <div className="timetable-banner-quote">
            <span>Better Timetable</span>
            <span>Better Learning</span>
          </div>
        </div>
      </header>

      {/* 2. Five-Step Import Pipeline */}
      <nav
        className="timetable-stepper-row"
        aria-label="Timetable import pipeline"
      >
        {steps.map((label, index) => {
          const stepNumber = index + 1;
          const isComplete = stepNumber < activeStep;
          const isActive = stepNumber === activeStep;

          return (
            <button
              type="button"
              key={label}
              className={`timetable-step-item ${isActive ? "is-active" : ""} ${isComplete ? "is-complete" : ""}`}
              onClick={() => goToStep(stepNumber)}
            >
              <span className="timetable-step-badge">
                {isComplete ? <FontAwesomeIcon icon={faCheck} /> : stepNumber}
              </span>
              <span className="timetable-step-name">{label}</span>
            </button>
          );
        })}
      </nav>

      {/* 3. STEP 1: 4-Cards Grid Header */}
      {activeStep === 1 && (
        <section className="timetable-cards-grid">
          {/* Card 1: Upload Timetable File */}
          <div className="timetable-card-box">
            <div className="timetable-card-header">
              <span className="timetable-card-badge-icon">
                <FontAwesomeIcon icon={faCloudArrowUp} />
              </span>
              <div>
                <h4>Upload Timetable File</h4>
                <p>Supports Excel (.xlsx) workbook files</p>
              </div>
            </div>

            <div
              className={`timetable-dropzone ${isDragging ? "is-dragging" : ""}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click();
              }}
            >
              <input
                ref={fileInputRef}
                type="file"
                className="timetable-hidden-input"
                accept=".xlsx"
                onChange={handleFileChange}
              />
              <button
                type="button"
                className="timetable-primary-button"
                onClick={(e) => {
                  e.stopPropagation();
                  fileInputRef.current?.click();
                }}
              >
                <FontAwesomeIcon icon={faCloudArrowUp} />
                Upload File
              </button>
              <span className="timetable-dropzone-caption">
                Drag & drop your file here or click to browse
              </span>
            </div>
          </div>

          {/* Card 2: File Details & Extract & Analyse */}
          <div className="timetable-card-box">
            {file ? (
              <div className="timetable-selected-file-details">
                <div className="timetable-file-meta-top">
                  <div className="timetable-file-badge-green">
                    <FontAwesomeIcon icon={faFileExcel} />
                  </div>
                  <div className="timetable-file-meta-text">
                    <strong>{file.name}</strong>
                    <span>
                      {(file.size / (1024 * 1024)).toFixed(1)} MB • Excel File
                    </span>
                  </div>
                  <button
                    type="button"
                    className="timetable-file-remove-btn"
                    onClick={handleClearFile}
                    title="Remove selected file"
                    aria-label="Remove file"
                  >
                    <FontAwesomeIcon icon={faXmark} />
                  </button>
                </div>

                <div className="timetable-uploaded-success-tag">
                  <FontAwesomeIcon icon={faCheckCircle} />
                  <span>File uploaded successfully</span>
                </div>

                <div className="timetable-sheet-select-row">
                  <label htmlFor="academic-year-input">Year:</label>
                  <select
                    id="academic-year-input"
                    value={academicYear}
                    onChange={(e) => setAcademicYear(e.target.value)}
                  >
                    {academicYears.map((yr) => (
                      <option key={yr} value={yr}>
                        {yr}
                      </option>
                    ))}
                    <option value="CUSTOM">+ Custom Year</option>
                  </select>

                  {availableSheets.length > 0 && (
                    <>
                      <label htmlFor="sheet-input">Sheet:</label>
                      <select
                        id="sheet-input"
                        value={selectedSheet}
                        onChange={(e) => setSelectedSheet(e.target.value)}
                      >
                        {availableSheets.map((s) => (
                          <option key={s} value={s}>
                            {s}
                          </option>
                        ))}
                      </select>
                    </>
                  )}
                </div>

                {academicYear === "CUSTOM" && (
                  <input
                    type="text"
                    className="timetable-custom-year-input"
                    placeholder="e.g. 2027-28"
                    value={customAcademicYear}
                    onChange={(e) => setCustomAcademicYear(e.target.value)}
                  />
                )}

                <button
                  type="button"
                  className="timetable-extract-action-btn"
                  onClick={handleAnalyze}
                  disabled={previewLoading || !file || !effectiveAcademicYear}
                >
                  <FontAwesomeIcon
                    icon={previewLoading ? faSpinner : faFileLines}
                    spin={previewLoading}
                  />
                  <span>
                    {previewLoading ? "Extracting & Analysing..." : "Extract & Analyse"}
                  </span>
                </button>
              </div>
            ) : (
              <div className="timetable-empty-file-slot">
                <FontAwesomeIcon icon={faFileExcel} className="faint-excel-icon" />
                <strong>No file selected</strong>
                <span>Upload a timetable workbook to unlock extraction & analysis.</span>
                <div className="timetable-sheet-select-row" style={{ marginTop: 8 }}>
                  <label htmlFor="academic-year-slot">Academic Year:</label>
                  <select
                    id="academic-year-slot"
                    value={academicYear}
                    onChange={(e) => setAcademicYear(e.target.value)}
                  >
                    {academicYears.map((yr) => (
                      <option key={yr} value={yr}>
                        {formatAcademicYear(yr)}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            )}
          </div>

          {/* Card 3: Data Extraction Checklist */}
          <div className="timetable-card-box">
            <div className="timetable-card-header">
              <h4>
                Data Extraction{" "}
                <span className="timetable-card-subtitle">
                  ({analysisResult ? "Completed" : previewLoading ? "Processing" : "Pending"})
                </span>
              </h4>
              <span
                className={`timetable-badge-pill ${analysisResult ? "is-success" : previewLoading ? "is-loading" : "is-muted"
                  }`}
              >
                {analysisResult ? "Completed" : previewLoading ? "In Progress" : "Pending"}
              </span>
            </div>

            <ul className="timetable-checklist">
              <li className={analysisResult || previewLoading ? "is-done" : ""}>
                <FontAwesomeIcon icon={faCheckCircle} />
                <span>Reading file...</span>
              </li>
              <li className={analysisResult || previewLoading ? "is-done" : ""}>
                <FontAwesomeIcon icon={faCheckCircle} />
                <span>Extracting timetable data...</span>
              </li>
              <li className={analysisResult ? "is-done" : ""}>
                <FontAwesomeIcon icon={faCheckCircle} />
                <span>Validating entries...</span>
              </li>
              <li className={analysisResult ? "is-done" : ""}>
                <FontAwesomeIcon icon={faCheckCircle} />
                <span>Processing faculty & course mapping...</span>
              </li>
              <li className={analysisResult ? "is-done" : ""}>
                <FontAwesomeIcon icon={faCheckCircle} />
                <span>Preparing preview...</span>
              </li>
            </ul>
          </div>

          {/* Card 4: Extracted Data Summary */}
          <div className="timetable-card-box">
            <div className="timetable-card-header">
              <h4>Extracted Data Summary</h4>
            </div>

            <div className="timetable-extracted-summary-stats">
              <div className="timetable-ext-stat-row">
                <span>
                  <FontAwesomeIcon icon={faLayerGroup} style={{ color: "#005fb8", marginRight: 6 }} />
                  Total Entries
                </span>
                <strong>{analysisResult ? mappingCounts.total : "—"}</strong>
              </div>
              <div className="timetable-ext-stat-row">
                <span>
                  <FontAwesomeIcon icon={faCheckCircle} style={{ color: "#16a34a", marginRight: 6 }} />
                  Valid Entries
                </span>
                <strong style={{ color: "#16a34a" }}>
                  {analysisResult ? mappingCounts.matched + mappingCounts.warning : "—"}
                </strong>
              </div>
              <div className="timetable-ext-stat-row">
                <span>
                  <FontAwesomeIcon icon={faTriangleExclamation} style={{ color: "#d97706", marginRight: 6 }} />
                  Warnings
                </span>
                <strong style={{ color: "#d97706" }}>
                  {analysisResult ? mappingCounts.warning : "—"}
                </strong>
              </div>
              <div className="timetable-ext-stat-row">
                <span>
                  <FontAwesomeIcon icon={faTriangleExclamation} style={{ color: "#dc2626", marginRight: 6 }} />
                  Errors / Conflicts
                </span>
                <strong style={{ color: "#dc2626" }}>
                  {analysisResult ? mappingCounts.conflict : "—"}
                </strong>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Global Alerts */}
      {previewError && (
        <div className="timetable-alert timetable-alert-error" role="alert">
          <FontAwesomeIcon icon={faTriangleExclamation} />
          <span>{previewError}</span>
        </div>
      )}

      {notice && (
        <div className="timetable-alert timetable-alert-info" role="status">
          <FontAwesomeIcon icon={faInfoCircle} />
          <span>{notice}</span>
        </div>
      )}

      {/* STEP 2: Extract & Preview */}
      {activeStep === 2 && analysisResult && (
        <section className="timetable-stage-card">
          <div className="timetable-preview-toolbar">
            <div>
              <h3>Extracted Timetable Preview</h3>
              <p>
                Found {analysisResult.total_rows} periods in sheet &quot;{analysisResult.source_sheet}&quot; for academic year <strong>{effectiveAcademicYear}</strong>. No database records written yet.
              </p>
            </div>
            <button
              type="button"
              className="timetable-outline-button"
              onClick={downloadPreviewCsv}
              disabled={!processedRows.length}
            >
              <FontAwesomeIcon icon={faDownload} />
              Download Preview CSV
            </button>
          </div>

          <div className="timetable-review-stats">
            <div className="timetable-review-stat-box">
              <span>Total Periods</span>
              <strong>{mappingCounts.total}</strong>
            </div>
            <div className="timetable-review-stat-box">
              <span>Auto-Matched</span>
              <strong style={{ color: "#0b7d3b" }}>{mappingCounts.matched}</strong>
            </div>
            <div className="timetable-review-stat-box">
              <span>Warnings</span>
              <strong style={{ color: "#a46c03" }}>{mappingCounts.warning}</strong>
            </div>
            <div className="timetable-review-stat-box">
              <span>Ambiguous</span>
              <strong style={{ color: "#6929c4" }}>{mappingCounts.ambiguous}</strong>
            </div>
            <div className="timetable-review-stat-box">
              <span>Conflicts</span>
              <strong style={{ color: "#b81414" }}>{mappingCounts.conflict}</strong>
            </div>
            <div className="timetable-review-stat-box">
              <span>Existing Duplicates</span>
              <strong style={{ color: "#52637a" }}>{mappingCounts.duplicate}</strong>
            </div>
          </div>

          <div className="timetable-table-wrapper" style={{ marginTop: 14 }}>
            <table className="timetable-table">
              <thead>
                <tr>
                  <th>Day</th>
                  <th>Period</th>
                  <th>Time</th>
                  <th>Class Group</th>
                  <th>Course</th>
                  <th>Faculty</th>
                  <th>Room</th>
                  <th>Extracted Raw Cell</th>
                  <th style={{ width: 80, textAlign: "center" }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {paginatedPreviewRows.map((row) => (
                  <tr key={`${row.source_row}-${row.index}`}>
                    <td>{titleCase(row.day_of_week)}</td>
                    <td>{row.period || "—"}</td>
                    <td>
                      {displayTime(row.start_time)} – {displayTime(row.end_time)}
                    </td>
                    <td>{row.class_group}</td>
                    <td>
                      <strong>{row.course_code || "—"}</strong>
                      {row.course_name ? ` · ${row.course_name}` : ""}
                    </td>
                    <td>{row.faculty_name || "—"}</td>
                    <td>{row.room || "—"}</td>
                    <td>
                      <small>{row.raw_cell}</small>
                    </td>
                    <td style={{ textAlign: "center" }}>
                      <button
                        type="button"
                        id={`edit-preview-row-${row.index}`}
                        className="timetable-row-edit-btn"
                        onClick={() => handleOpenEditModal(row)}
                        title="Edit extracted time and room"
                      >
                        Edit
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {processedRows.length > 0 && (
            <div className="timetable-pagination-bar">
              <span className="timetable-pagination-info">
                Showing {(safePreviewPage - 1) * PAGE_SIZE + 1}–{Math.min(safePreviewPage * PAGE_SIZE, processedRows.length)} of {processedRows.length} entries
              </span>
              <div className="timetable-pagination-pages">
                <button
                  type="button"
                  disabled={safePreviewPage === 1}
                  onClick={() => setPreviewPage((p) => Math.max(1, p - 1))}
                  className="timetable-page-nav-btn"
                  aria-label="Previous preview page"
                >
                  <FontAwesomeIcon icon={faChevronLeft} /> Previous
                </button>
                {getPageNumbers(safePreviewPage, totalPreviewPages).map((p, idx) =>
                  p === "..." ? (
                    <span key={`prev-ellipsis-${idx}`} className="timetable-page-ellipsis">
                      ...
                    </span>
                  ) : (
                    <button
                      type="button"
                      key={p}
                      className={`timetable-page-num-btn ${safePreviewPage === p ? "is-current" : ""}`}
                      onClick={() => setPreviewPage(p)}
                    >
                      {p}
                    </button>
                  )
                )}
                <button
                  type="button"
                  disabled={safePreviewPage === totalPreviewPages}
                  onClick={() => setPreviewPage((p) => Math.min(totalPreviewPages, p + 1))}
                  className="timetable-page-nav-btn"
                  aria-label="Next preview page"
                >
                  Next <FontAwesomeIcon icon={faChevronRight} />
                </button>
              </div>
            </div>
          )}
        </section>
      )}

      {/* STEP 3: Map & Resolve */}
      {activeStep === 3 && analysisResult && (
        <section className="timetable-stage-card timetable-mapping-card">
          <div className="timetable-preview-toolbar timetable-mapping-header">
            <div>
              <h3>Map & Resolve Timetable Entities</h3>
              <p>
                Review matched courses, assign ambiguous faculty or courses, and verify section assignments.
              </p>
            </div>
            <div className="timetable-mapping-actions">
              <button
                type="button"
                className="timetable-action-btn"
                onClick={() => toggleSelectAll(true)}
                title="Select all matching entries for import"
              >
                <FontAwesomeIcon icon={faCheckDouble} />
                Select All
              </button>
              <button
                type="button"
                className="timetable-action-btn"
                onClick={() => toggleSelectAll(false)}
                title="Deselect all entries"
              >
                <FontAwesomeIcon icon={faXmark} />
                Deselect All
              </button>
            </div>
          </div>

          <div className="timetable-mapping-filter-toolbar">
            <div className="timetable-mapping-filter-group">
              <label htmlFor="mapping-status-filter">Mapping Status</label>
              <select
                id="mapping-status-filter"
                value={mappingStatusFilter}
                onChange={(e) => {
                  setMappingStatusFilter(e.target.value);
                  setMappingPage(1);
                }}
              >
                <option value="All">All statuses ({processedRows.length})</option>
                <option value="matched">Auto-matched ({mappingCounts.matched})</option>
                <option value="warning">With warnings ({mappingCounts.warning})</option>
                <option value="ambiguous">Ambiguous ({mappingCounts.ambiguous})</option>
                <option value="conflict">Conflicts ({mappingCounts.conflict})</option>
                <option value="duplicate">Duplicates ({mappingCounts.duplicate})</option>
                <option value="unmatched">Unmatched ({mappingCounts.unmatched})</option>
              </select>
            </div>

            <div className="timetable-mapping-filter-group">
              <label htmlFor="mapping-semester-filter">Semester</label>
              <select
                id="mapping-semester-filter"
                value={mappingSemesterFilter}
                onChange={(e) => {
                  setMappingSemesterFilter(e.target.value);
                  setMappingPage(1);
                }}
              >
                <option value="All">All semesters</option>
                {mappingFilterOptions.semesters.map((s) => (
                  <option key={s} value={s}>
                    Semester {s}
                  </option>
                ))}
              </select>
            </div>

            <div className="timetable-mapping-filter-group">
              <label htmlFor="mapping-section-filter">Section / Group</label>
              <select
                id="mapping-section-filter"
                value={mappingSectionFilter}
                onChange={(e) => {
                  setMappingSectionFilter(e.target.value);
                  setMappingPage(1);
                }}
              >
                <option value="All">All sections</option>
                {mappingFilterOptions.sections.map((sec) => (
                  <option key={sec} value={sec}>
                    {sec}
                  </option>
                ))}
              </select>
            </div>

            <div className="timetable-mapping-filter-group timetable-mapping-search-group">
              <label htmlFor="mapping-search-input">Search entries</label>
              <div className="timetable-search-input-wrapper">
                <FontAwesomeIcon icon={faSearch} className="timetable-search-icon" />
                <input
                  id="mapping-search-input"
                  value={mappingSearch}
                  onChange={(e) => {
                    setMappingSearch(e.target.value);
                    setMappingPage(1);
                  }}
                  placeholder="Search by course, faculty, room..."
                />
                {mappingSearch && (
                  <button
                    type="button"
                    className="timetable-search-clear-btn"
                    onClick={() => {
                      setMappingSearch("");
                      setMappingPage(1);
                    }}
                    title="Clear search"
                  >
                    <FontAwesomeIcon icon={faXmark} />
                  </button>
                )}
              </div>
            </div>
          </div>

          <div className="timetable-mapping-summary-bar">
            <div className="timetable-summary-pills">
              <span className="timetable-summary-pill pill-total">
                <strong>{filteredProcessedRows.length}</strong> of {processedRows.length} entries shown
              </span>
              <span className="timetable-summary-pill pill-selected">
                <strong>{mappingCounts.selected}</strong> selected for import
              </span>
              {mappingCounts.conflict > 0 && (
                <span className="timetable-summary-pill pill-conflict">
                  <strong>{mappingCounts.conflict}</strong> conflicts
                </span>
              )}
              {mappingCounts.warning > 0 && (
                <span className="timetable-summary-pill pill-warning">
                  <strong>{mappingCounts.warning}</strong> warnings
                </span>
              )}
            </div>
          </div>

          <div className="timetable-table-wrapper timetable-mapping-table-wrapper">
            <table className="timetable-table timetable-mapping-table">
              <thead>
                <tr>
                  <th style={{ width: 48, textAlign: "center" }}>Import</th>
                  <th style={{ width: 120 }}>Day / Time</th>
                  <th style={{ width: 90 }}>Section</th>
                  <th style={{ minWidth: 260 }}>Course Assignment</th>
                  <th style={{ minWidth: 220 }}>Faculty Assignment</th>
                  <th style={{ width: 110 }}>Room</th>
                  <th style={{ width: 140 }}>Offering Action</th>
                  <th style={{ minWidth: 220 }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {paginatedMappingRows.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="timetable-table-empty">
                      No timetable records match the selected filters.
                    </td>
                  </tr>
                ) : (
                  paginatedMappingRows.map((row) => (
                    <tr
                      key={`${row.source_row}-${row.index}`}
                      className={row.isSelected ? "row-is-selected" : ""}
                    >
                      <td style={{ textAlign: "center" }}>
                        <input
                          type="checkbox"
                          className="timetable-row-checkbox"
                          checked={row.isSelected}
                          onChange={() => toggleRowSelection(row.index)}
                          aria-label={`Select row ${row.index + 1}`}
                        />
                      </td>
                      <td>
                        <div className="timetable-cell-day">
                          <strong>{titleCase(row.day_of_week)}</strong>
                          <div className="timetable-cell-time">
                            {displayTime(row.start_time)} – {displayTime(row.end_time)}
                          </div>
                          {row.period && (
                            <span className="timetable-period-pill">Period {row.period}</span>
                          )}
                          <button
                            type="button"
                            id={`edit-mapping-row-${row.index}`}
                            className="timetable-cell-adjust-link"
                            onClick={() => handleOpenEditModal(row)}
                            title="Edit extracted day, time, or room"
                          >
                            Edit Time/Room
                          </button>
                        </div>
                      </td>
                      <td>
                        <input
                          type="text"
                          className="timetable-cell-input timetable-section-input"
                          value={row.section}
                          onChange={(e) =>
                            updateEntryOverride(row.index, { section: e.target.value })
                          }
                          aria-label={`Section for period ${row.period || row.index}`}
                        />
                      </td>
                      <td>
                        <div className="timetable-course-cell">
                          <select
                            className="timetable-cell-select timetable-course-select"
                            value={row.course_id || ""}
                            onChange={(e) =>
                              updateEntryOverride(row.index, {
                                course_id: Number(e.target.value) || null,
                              })
                            }
                            aria-label={`Course assignment for period ${row.period || row.index}`}
                          >
                            <option value="">Select course...</option>
                            {(analysisResult.available_courses || []).map((c) => (
                              <option key={c.course_id} value={c.course_id}>
                                {c.course_code} - {c.course_name} (Sem {c.semester})
                              </option>
                            ))}
                          </select>
                          <div
                            className="timetable-raw-cell-hint"
                            title={`Extracted raw cell: ${row.raw_cell}`}
                          >
                            <span className="raw-cell-prefix">Raw:</span> {row.raw_cell}
                          </div>
                        </div>
                      </td>
                      <td>
                        <select
                          className="timetable-cell-select timetable-faculty-select"
                          value={row.faculty_id || ""}
                          onChange={(e) =>
                            updateEntryOverride(row.index, {
                              faculty_id: Number(e.target.value) || null,
                            })
                          }
                          aria-label={`Faculty assignment for period ${row.period || row.index}`}
                        >
                          <option value="">Not assigned</option>
                          {(analysisResult.available_faculty || []).map((f) => (
                            <option key={f.faculty_id} value={f.faculty_id}>
                              {f.name} ({f.employee_id})
                            </option>
                          ))}
                        </select>
                      </td>
                      <td>
                        <input
                          type="text"
                          className="timetable-cell-input timetable-room-input"
                          value={row.room}
                          onChange={(e) =>
                            updateEntryOverride(row.index, { room: e.target.value })
                          }
                          placeholder="e.g. Room-302"
                          aria-label={`Room for period ${row.period || row.index}`}
                        />
                      </td>
                      <td>
                        {row.offering_id ? (
                          <span
                            className="timetable-offering-badge is-reuse"
                            title={`Reuses existing offering ID ${row.offering_id}`}
                          >
                            Reuses Offering #{row.offering_id}
                          </span>
                        ) : (
                          <span
                            className="timetable-offering-badge is-create"
                            title="A new course offering will be created upon commit"
                          >
                            Will Create Offering
                          </span>
                        )}
                      </td>
                      <td>
                        <div className="timetable-status-cell">
                          <span
                            className="timetable-status-tag"
                            data-status={row.status}
                          >
                            {getMappingStatusLabel(row.status)}
                          </span>
                          {row.conflicts?.map((msg, i) => (
                            <div key={`conflict-${i}`} className="timetable-row-message is-conflict">
                              <FontAwesomeIcon icon={faTriangleExclamation} /> <span>{msg}</span>
                            </div>
                          ))}
                          {row.warnings?.map((msg, i) => (
                            <div key={`warning-${i}`} className="timetable-row-message is-warning">
                              <FontAwesomeIcon icon={faInfoCircle} /> <span>{msg}</span>
                            </div>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {filteredProcessedRows.length > 0 && (
            <div className="timetable-pagination-bar">
              <span className="timetable-pagination-info">
                Showing {(safeMappingPage - 1) * PAGE_SIZE + 1}–{Math.min(safeMappingPage * PAGE_SIZE, filteredProcessedRows.length)} of {filteredProcessedRows.length} entries
                {filteredProcessedRows.length < processedRows.length && (
                  <span className="filtered-subset-note"> (filtered from {processedRows.length} total)</span>
                )}
              </span>

              <div className="timetable-pagination-pages">
                <button
                  type="button"
                  disabled={safeMappingPage === 1}
                  onClick={() => setMappingPage((p) => Math.max(1, p - 1))}
                  className="timetable-page-nav-btn"
                  aria-label="Previous mapping page"
                >
                  <FontAwesomeIcon icon={faChevronLeft} /> Previous
                </button>
                {getPageNumbers(safeMappingPage, totalMappingPages).map((p, idx) =>
                  p === "..." ? (
                    <span key={`mapping-ellipsis-${idx}`} className="timetable-page-ellipsis">
                      ...
                    </span>
                  ) : (
                    <button
                      type="button"
                      key={p}
                      className={`timetable-page-num-btn ${safeMappingPage === p ? "is-current" : ""}`}
                      onClick={() => setMappingPage(p)}
                    >
                      {p}
                    </button>
                  )
                )}
                <button
                  type="button"
                  disabled={safeMappingPage === totalMappingPages}
                  onClick={() => setMappingPage((p) => Math.min(totalMappingPages, p + 1))}
                  className="timetable-page-nav-btn"
                  aria-label="Next mapping page"
                >
                  Next <FontAwesomeIcon icon={faChevronRight} />
                </button>
              </div>
            </div>
          )}
        </section>
      )}

      {/* STEP 4: Review & Commit */}
      {activeStep === 4 && analysisResult && (
        <section className="timetable-stage-card">
          <div className="timetable-review-card">
            <div className="timetable-preview-toolbar">
              <div>
                <h3>Import Review & Commit Plan</h3>
                <p>
                  Target Academic Year: <strong>{effectiveAcademicYear}</strong>. Review planned changes before committing to MySQL database.
                </p>
              </div>
            </div>

            <div className="timetable-review-stats">
              <div className="timetable-review-stat-box">
                <span>Selected for Import</span>
                <strong style={{ color: "#005fb8" }}>{mappingCounts.selected}</strong>
              </div>
              <div className="timetable-review-stat-box">
                <span>Entries to Create</span>
                <strong style={{ color: "#0b7d3b" }}>
                  {processedRows.filter((r) => r.isSelected && r.course_id && r.status !== "duplicate").length}
                </strong>
              </div>
              <div className="timetable-review-stat-box">
                <span>Duplicates to Skip</span>
                <strong style={{ color: "#52637a" }}>{mappingCounts.duplicate}</strong>
              </div>
              <div className="timetable-review-stat-box">
                <span>Detected Conflicts</span>
                <strong style={{ color: "#b81414" }}>{mappingCounts.conflict}</strong>
              </div>
            </div>

            <div className="timetable-mode-section">
              <strong>Select Import Mode</strong>

              <label
                className={`timetable-mode-option ${importMode === "add_missing" ? "is-selected" : ""}`}
              >
                <input
                  type="radio"
                  name="importMode"
                  value="add_missing"
                  checked={importMode === "add_missing"}
                  onChange={(e) => setImportMode(e.target.value)}
                />
                <div className="timetable-mode-option-text">
                  <strong>Add Missing Entries Only (Recommended)</strong>
                  <span>
                    Safely creates new timetable entries and offerings. Existing identical entries are skipped without creating duplicate records.
                  </span>
                </div>
              </label>

              <label
                className={`timetable-mode-option ${importMode === "update_matched" ? "is-selected" : ""}`}
              >
                <input
                  type="radio"
                  name="importMode"
                  value="update_matched"
                  checked={importMode === "update_matched"}
                  onChange={(e) => setImportMode(e.target.value)}
                />
                <div className="timetable-mode-option-text">
                  <strong>Update Matched Entries</strong>
                  <span>
                    Updates classroom and timings for existing entries that match the same course offering and day.
                  </span>
                </div>
              </label>

              <label
                className={`timetable-mode-option ${importMode === "review_conflicts" ? "is-selected" : ""}`}
              >
                <input
                  type="radio"
                  name="importMode"
                  value="review_conflicts"
                  checked={importMode === "review_conflicts"}
                  onChange={(e) => setImportMode(e.target.value)}
                />
                <div className="timetable-mode-option-text">
                  <strong>Strict Validation</strong>
                  <span>
                    Skips any entries with unresolved warnings or scheduling conflicts.
                  </span>
                </div>
              </label>
            </div>

            {commitError && (
              <div className="timetable-alert timetable-alert-error" role="alert">
                <FontAwesomeIcon icon={faTriangleExclamation} />
                <span>{commitError}</span>
              </div>
            )}

            <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 8 }}>
              <input
                type="checkbox"
                id="confirm-import-check"
                checked={confirmCommit}
                onChange={(e) => setConfirmCommit(e.target.checked)}
              />
              <label htmlFor="confirm-import-check" style={{ fontSize: 13, color: "#16345f", cursor: "pointer" }}>
                I have reviewed the entity mappings and confirm importing{" "}
                <strong>{mappingCounts.selected}</strong> entries into academic year{" "}
                <strong>{effectiveAcademicYear}</strong>.
              </label>
            </div>
          </div>
        </section>
      )}

      {/* STEP 5: Import Results Summary */}
      {activeStep === 5 && commitResult && (
        <section className="timetable-stage-card">
          <div className="timetable-result-banner">
            <div className="timetable-result-icon">
              <FontAwesomeIcon icon={faCheckCircle} />
            </div>
            <div className="timetable-result-copy">
              <h3>Timetable Import Successfully Committed!</h3>
              <p>
                Database transaction committed for Academic Year <strong>{commitResult.academic_year}</strong>.
              </p>
            </div>
          </div>

          <div className="timetable-review-stats" style={{ marginTop: 14 }}>
            <div className="timetable-review-stat-box">
              <span>Timetable Entries Created</span>
              <strong style={{ color: "#0b7d3b" }}>{commitResult.created_entries}</strong>
            </div>
            <div className="timetable-review-stat-box">
              <span>Offerings Created</span>
              <strong style={{ color: "#005fb8" }}>{commitResult.created_offerings}</strong>
            </div>
            <div className="timetable-review-stat-box">
              <span>Entries Updated</span>
              <strong style={{ color: "#a46c03" }}>{commitResult.updated_entries}</strong>
            </div>
            <div className="timetable-review-stat-box">
              <span>Duplicates Skipped</span>
              <strong style={{ color: "#52637a" }}>{commitResult.skipped_entries}</strong>
            </div>
          </div>

          <div style={{ display: "flex", gap: 12, marginTop: 16 }}>
            <button
              type="button"
              className="timetable-primary-button"
              onClick={() => {
                setActiveTab("Timetable");
                void loadTimetable();
              }}
            >
              <FontAwesomeIcon icon={faCalendarDays} />
              View Saved Timetable
            </button>
            <button
              type="button"
              className="timetable-outline-button"
              onClick={resetWizard}
            >
              <FontAwesomeIcon icon={faRotateRight} />
              Import Another Timetable
            </button>
          </div>
        </section>
      )}

      {/* Wizard Step Footer */}
      {activeStep > 1 && activeStep < 5 && (
        <footer className="timetable-wizard-footer">
          <button
            type="button"
            className="timetable-outline-button"
            onClick={() => setActiveStep((curr) => Math.max(1, curr - 1))}
          >
            Back
          </button>

          {activeStep === 2 && (
            <button
              type="button"
              className="timetable-primary-button"
              onClick={() => setActiveStep(3)}
            >
              Next: Map & Resolve
              <FontAwesomeIcon icon={faChevronRight} />
            </button>
          )}

          {activeStep === 3 && (
            <button
              type="button"
              className="timetable-primary-button"
              onClick={() => setActiveStep(4)}
            >
              Next: Review & Commit
              <FontAwesomeIcon icon={faChevronRight} />
            </button>
          )}

          {activeStep === 4 && (
            <button
              type="button"
              className="timetable-primary-button"
              disabled={!confirmCommit || commitLoading || mappingCounts.selected === 0}
              onClick={handleCommitImport}
            >
              <FontAwesomeIcon icon={commitLoading ? faSpinner : faSave} spin={commitLoading} />
              {commitLoading ? "Committing Transaction..." : "Confirm & Commit Timetable"}
            </button>
          )}
        </footer>
      )}

      {/* 4. MAIN SPLIT LAYOUT: Filter + Table + Right Sidebar */}
      <div className="timetable-layout-container">
        {/* Left Column: Filter Bar & Saved Records */}
        <div className="timetable-main-column">
          {/* Filter Bar */}
          <div className="timetable-toolbar-filter-card">
            <div className="timetable-filter-select-group">
              <label htmlFor="filter-semester">Semester</label>
              <select
                id="filter-semester"
                value={semesterFilter}
                onChange={(e) => {
                  setSemesterFilter(e.target.value);
                  setSectionFilter("All");
                  setCurrentPage(1);
                }}
              >
                <option value="All">All Semesters</option>
                {semesters.map((s) => (
                  <option key={s} value={s}>
                    Semester {s}
                  </option>
                ))}
              </select>
            </div>

            <div className="timetable-filter-select-group">
              <label htmlFor="filter-section">Section</label>
              <select
                id="filter-section"
                value={sectionFilter}
                onChange={(e) => {
                  setSectionFilter(e.target.value);
                  setCurrentPage(1);
                }}
              >
                <option value="All">All Sections</option>
                {sections.map((sec) => (
                  <option key={sec} value={sec}>
                    {sec}
                  </option>
                ))}
              </select>
            </div>

            <div className="timetable-filter-select-group">
              <label htmlFor="filter-day">Day</label>
              <select
                id="filter-day"
                value={dayFilter}
                onChange={(e) => {
                  setDayFilter(e.target.value);
                  setCurrentPage(1);
                }}
              >
                <option value="All">All Days</option>
                {days.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </div>

            <div className="timetable-filter-search-box">
              <FontAwesomeIcon icon={faSearch} />
              <input
                type="text"
                placeholder="Search by course code, course name, faculty or room..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setCurrentPage(1);
                }}
              />
            </div>

            <button
              type="button"
              className="timetable-filter-reset-btn"
              onClick={resetFilters}
            >
              <FontAwesomeIcon icon={faRotateRight} />
              Reset
            </button>
          </div>

          {/* Database Records Card */}
          <div className="timetable-records-card">
            <div className="timetable-records-header">
              <div className="timetable-records-title">
                <span className="timetable-header-blue-icon">
                  <FontAwesomeIcon icon={faCalendarDays} />
                </span>
                <h3>Timetable Entries</h3>
                <span className="timetable-count-badge">
                  Total Entries: {filteredEntries.length}
                </span>
              </div>

              <div className="timetable-header-right">
                <nav className="timetable-record-tabs">
                  {tabs.map((tab) => (
                    <button
                      type="button"
                      key={tab}
                      className={`timetable-tab-btn ${activeTab === tab ? "is-active" : ""}`}
                      onClick={() => setActiveTab(tab)}
                    >
                      {tab}
                    </button>
                  ))}
                </nav>

                <button
                  type="button"
                  className="timetable-refresh-icon-btn"
                  onClick={loadTimetable}
                  disabled={timetableLoading}
                  title="Refresh persisted timetable records"
                >
                  <FontAwesomeIcon
                    icon={faRotateRight}
                    spin={timetableLoading}
                  />
                </button>
              </div>
            </div>

            {timetableError && (
              <div className="timetable-alert timetable-alert-error" role="alert">
                <span>{timetableError}</span>
                <button type="button" onClick={loadTimetable}>
                  Retry
                </button>
              </div>
            )}

            {/* TAB: Timetable */}
            {activeTab === "Timetable" && (
              <div className="timetable-table-container">
                <table className="timetable-records-table">
                  <thead>
                    <tr>
                      <th>Day</th>
                      <th>Period</th>
                      <th>Time</th>
                      <th>Course Code</th>
                      <th>Course Name</th>
                      <th>Semester</th>
                      <th>Section</th>
                      <th>Faculty</th>
                      <th>Room</th>
                      <th>Status</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {timetableLoading ? (
                      <tr>
                        <td colSpan={11} className="timetable-table-center">
                          <FontAwesomeIcon icon={faSpinner} spin /> Loading saved timetable...
                        </td>
                      </tr>
                    ) : paginatedEntries.length ? (
                      paginatedEntries.map((entry) => (
                        <tr key={entry.id}>
                          <td><strong>{entry.day}</strong></td>
                          <td>—</td>
                          <td>
                            {displayTime(entry.startTime)} – {displayTime(entry.endTime)}
                          </td>
                          <td><strong>{entry.courseCode || "—"}</strong></td>
                          <td>{entry.courseName || "—"}</td>
                          <td>{entry.semester || "—"}</td>
                          <td>{entry.section || "—"}</td>
                          <td>
                            {entry.activeAdjustment ? (
                              <div>
                                <span style={{ textDecoration: "line-through", color: "#8a9eb8", fontSize: 11 }}>
                                  {entry.faculty}
                                </span>
                                <div style={{ color: "#005fb8", fontWeight: 600 }}>
                                  {entry.effectiveFaculty}
                                </div>
                              </div>
                            ) : (
                              entry.faculty
                            )}
                          </td>
                          <td>{entry.room}</td>
                          <td>
                            {entry.activeAdjustment ? (
                              <span className="timetable-pill-tag is-adjusted">
                                Substituted
                              </span>
                            ) : (
                              <span className="timetable-pill-tag is-active">
                                Active
                              </span>
                            )}
                          </td>
                          <td className="timetable-actions-cell">
                            <button
                              type="button"
                              id={`edit-entry-${entry.id}`}
                              className="timetable-row-edit-btn"
                              onClick={() => handleOpenEditModal(entry)}
                              title="Edit time, room, and schedule"
                            >
                              Edit
                            </button>
                            <button
                              type="button"
                              id={`adjust-entry-${entry.id}`}
                              className="timetable-row-adjust-btn"
                              onClick={() => openAdjustment(entry)}
                              title="Faculty adjustment / replacement"
                            >
                              Adjust
                            </button>
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={11} className="timetable-table-center">
                          No timetable entries match the selected filters.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>

                {/* Pagination */}
                {filteredEntries.length > 0 && (
                  <div className="timetable-pagination-bar">
                    <span className="timetable-pagination-info">
                      Showing {(currentPage - 1) * PAGE_SIZE + 1} to{" "}
                      {Math.min(currentPage * PAGE_SIZE, filteredEntries.length)} of{" "}
                      {filteredEntries.length} entries
                    </span>

                    <div className="timetable-pagination-pages">
                      <button
                        type="button"
                        disabled={currentPage === 1}
                        onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                        className="timetable-page-nav-btn"
                        aria-label="Previous page"
                      >
                        <FontAwesomeIcon icon={faChevronLeft} />
                      </button>
                      {getPageNumbers(currentPage, totalPages).map((p, idx) =>
                        p === "..." ? (
                          <span key={`db-ellipsis-${idx}`} className="timetable-page-ellipsis">
                            ...
                          </span>
                        ) : (
                          <button
                            type="button"
                            key={p}
                            className={`timetable-page-num-btn ${currentPage === p ? "is-current" : ""}`}
                            onClick={() => setCurrentPage(p)}
                          >
                            {p}
                          </button>
                        )
                      )}
                      <button
                        type="button"
                        disabled={currentPage === totalPages}
                        onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                        className="timetable-page-nav-btn"
                        aria-label="Next page"
                      >
                        <FontAwesomeIcon icon={faChevronRight} />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* TAB: Courses */}
            {activeTab === "Courses" && (
              <div className="timetable-table-container">
                <table className="timetable-records-table">
                  <thead>
                    <tr>
                      <th>Course Code</th>
                      <th>Course Name</th>
                      <th>Department</th>
                      <th>Semester</th>
                      <th>Section</th>
                      <th>Academic Year</th>
                    </tr>
                  </thead>
                  <tbody>
                    {distinctCourses.map((c) => (
                      <tr key={c.courseCode || c.courseName}>
                        <td><strong>{c.courseCode || "—"}</strong></td>
                        <td>{c.courseName || "—"}</td>
                        <td>{c.department || "—"}</td>
                        <td>{c.semester || "—"}</td>
                        <td>{c.section || "—"}</td>
                        <td>{c.academicYear || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* TAB: Faculty */}
            {activeTab === "Faculty" && (
              <div className="timetable-table-container">
                <table className="timetable-records-table">
                  <thead>
                    <tr>
                      <th>Faculty Name</th>
                      <th>Assigned Courses</th>
                      <th>Total Periods / Classes</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {distinctFaculty.map((name) => {
                      const facultyEntries = entries.filter((e) => e.faculty === name);
                      const assignedCourses = new Set(
                        facultyEntries.map((e) => e.courseCode || e.courseName).filter(Boolean)
                      );
                      return (
                        <tr key={name}>
                          <td><strong>{name}</strong></td>
                          <td>{assignedCourses.size}</td>
                          <td>{facultyEntries.length}</td>
                          <td>
                            <button
                              type="button"
                              className="timetable-row-adjust-btn"
                              onClick={() => {
                                setSelectedCurrentFaculty(name);
                                setAdjustmentOpen(true);
                                setTimeout(() => {
                                  adjustmentSectionRef.current?.scrollIntoView({ behavior: "smooth" });
                                }, 100);
                              }}
                            >
                              Emergency Replace
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {/* TAB: Classrooms */}
            {activeTab === "Classrooms" && (
              <div className="timetable-table-container">
                <table className="timetable-records-table">
                  <thead>
                    <tr>
                      <th>Classroom</th>
                      <th>Scheduled Classes</th>
                      <th>Days Used</th>
                      <th>Courses</th>
                    </tr>
                  </thead>
                  <tbody>
                    {distinctRooms.map((room) => {
                      const roomEntries = entries.filter((e) => e.room === room);
                      const daysCount = new Set(roomEntries.map((e) => e.dayKey)).size;
                      const coursesCount = new Set(
                        roomEntries.map((e) => e.courseCode || e.courseName).filter(Boolean)
                      ).size;
                      return (
                        <tr key={room}>
                          <td><strong>{room}</strong></td>
                          <td>{roomEntries.length}</td>
                          <td>{daysCount}</td>
                          <td>{coursesCount}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Right Sidebar: Quick Actions + Statistics + Efficient Card */}
        <aside className="timetable-sidebar-column">
          {/* Quick Actions Card */}
          <div className="timetable-quick-actions-card">
            <div className="timetable-sidebar-title">
              <span className="timetable-sidebar-icon">
                <FontAwesomeIcon icon={faLayerGroup} />
              </span>
              <h4>Quick Actions</h4>
            </div>

            <div className="timetable-quick-actions-list">
              <button
                type="button"
                className="timetable-quick-action-item"
                onClick={() => {
                  setActiveTab("Timetable");
                  window.scrollTo({ top: 380, behavior: "smooth" });
                }}
              >
                <div className="timetable-action-icon-circle is-blue">
                  <FontAwesomeIcon icon={faCalendarDays} />
                </div>
                <div className="timetable-action-copy">
                  <strong>View Timetable</strong>
                  <span>Check your class schedule</span>
                </div>
                <FontAwesomeIcon icon={faChevronRight} className="timetable-action-chevron" />
              </button>

              <button
                type="button"
                className="timetable-quick-action-item"
                onClick={() => {
                  setActiveTab("Faculty");
                  window.scrollTo({ top: 380, behavior: "smooth" });
                }}
              >
                <div className="timetable-action-icon-circle is-purple">
                  <FontAwesomeIcon icon={faUsers} />
                </div>
                <div className="timetable-action-copy">
                  <strong>Faculty Assignment</strong>
                  <span>View assigned faculty</span>
                </div>
                <FontAwesomeIcon icon={faChevronRight} className="timetable-action-chevron" />
              </button>

              <button
                type="button"
                className="timetable-quick-action-item"
                onClick={() => navigate("/admin/academic-management/course-offerings")}
              >
                <div className="timetable-action-icon-circle is-green">
                  <FontAwesomeIcon icon={faGraduationCap} />
                </div>
                <div className="timetable-action-copy">
                  <strong>Course Offerings</strong>
                  <span>View course offerings</span>
                </div>
                <FontAwesomeIcon icon={faChevronRight} className="timetable-action-chevron" />
              </button>

              <button
                type="button"
                className="timetable-quick-action-item"
                onClick={() => openAdjustment()}
              >
                <div className="timetable-action-icon-circle is-orange">
                  <FontAwesomeIcon icon={faUserClock} />
                </div>
                <div className="timetable-action-copy">
                  <strong>Adjustment</strong>
                  <span>Modify faculty / room / time</span>
                </div>
                <FontAwesomeIcon icon={faChevronRight} className="timetable-action-chevron" />
              </button>
            </div>
          </div>

          {/* Timetable Statistics Card */}
          <div className="timetable-statistics-card">
            <div className="timetable-sidebar-title">
              <h4>Timetable Statistics</h4>
              <small>Based on latest import</small>
            </div>

            <div className="timetable-stat-quad-grid">
              <div className="timetable-stat-tile">
                <div className="timetable-tile-icon is-blue">
                  <FontAwesomeIcon icon={faCalendarDays} />
                </div>
                <div className="timetable-tile-text">
                  <span>Total Entries</span>
                  <strong>{entries.length}</strong>
                </div>
              </div>

              <div className="timetable-stat-tile">
                <div className="timetable-tile-icon is-purple">
                  <FontAwesomeIcon icon={faUsers} />
                </div>
                <div className="timetable-tile-text">
                  <span>Active Faculty</span>
                  <strong>{distinctFaculty.length}</strong>
                </div>
              </div>

              <div className="timetable-stat-tile">
                <div className="timetable-tile-icon is-green">
                  <FontAwesomeIcon icon={faFileLines} />
                </div>
                <div className="timetable-tile-text">
                  <span>Total Courses</span>
                  <strong>{distinctCourses.length}</strong>
                </div>
              </div>

              <div className="timetable-stat-tile">
                <div className="timetable-tile-icon is-orange">
                  <FontAwesomeIcon icon={faLayerGroup} />
                </div>
                <div className="timetable-tile-text">
                  <span>Sections</span>
                  <strong>{sections.length}</strong>
                </div>
              </div>
            </div>
          </div>

          {/* Manage Timetable Efficiently Banner */}
          <div
            className="timetable-efficiently-card"
            style={{ backgroundImage: `url(${campusBannerImage})` }}
          >
            <div className="timetable-efficient-overlay" />
            <div className="timetable-efficient-content">
              <span className="timetable-efficient-icon">
                <FontAwesomeIcon icon={faGraduationCap} />
              </span>
              <h4>Manage Timetable Efficiently</h4>
              <p>Upload, validate and keep your academic schedule updated with ease.</p>
            </div>
          </div>
        </aside>
      </div>

      {/* 5. FACULTY ADJUSTMENT SECTION & AUDIT TRAIL */}
      <section
        ref={adjustmentSectionRef}
        className="timetable-adjustment-section"
      >
        <div className="timetable-adjustment-heading">
          <div className="timetable-heading-icon">
            <FontAwesomeIcon icon={faUserClock} />
          </div>
          <div className="timetable-adjustment-heading-copy">
            <h3>Faculty Adjustment & Substitution</h3>
            <p>
              Temporarily replace assigned faculty for an affected class with full conflict validation and permanent audit trail.
            </p>
          </div>
          <button
            type="button"
            className="timetable-primary-button"
            onClick={() => setAdjustmentOpen((prev) => !prev)}
          >
            <FontAwesomeIcon icon={faUsers} />
            {adjustmentOpen ? "Hide Adjustment Form" : "New Faculty Adjustment"}
          </button>
        </div>

        {adjustmentOpen && (
          <form
            className="timetable-adjustment-form"
            onSubmit={submitAdjustment}
          >
            <h4>Emergency Faculty Replacement</h4>

            {adjustmentError && (
              <div className="timetable-alert timetable-alert-error" role="alert">
                <FontAwesomeIcon icon={faTriangleExclamation} />
                <span>{adjustmentError}</span>
              </div>
            )}

            {adjustmentMessage && (
              <div className="timetable-alert timetable-alert-info" role="status">
                <FontAwesomeIcon icon={faCheckCircle} />
                <span>{adjustmentMessage}</span>
              </div>
            )}

            <div className="timetable-adjustment-faculty-grid">
              {/* Box 1: Current Assigned Faculty */}
              <div className="timetable-adjustment-box">
                <h4>1. Current Assigned Faculty & Class</h4>

                <label>
                  <span>Faculty Name</span>
                  <select
                    value={selectedCurrentFaculty}
                    onChange={(event) => {
                      const val = event.target.value;
                      setSelectedCurrentFaculty(val);
                      setAdjustmentTargetId("");
                      setAdjustmentError("");
                      setAdjustmentMessage("");
                    }}
                    required
                  >
                    <option value="">Select current faculty...</option>
                    {distinctFaculty.map((name) => (
                      <option key={name} value={name}>
                        {name}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  <span>Select Affected Class / Period</span>
                  <select
                    value={adjustmentTargetId}
                    onChange={(event) => {
                      setAdjustmentTargetId(event.target.value);
                      setAdjustmentError("");
                      setAdjustmentMessage("");
                    }}
                    disabled={!selectedCurrentFaculty}
                    required
                  >
                    <option value="">
                      {selectedCurrentFaculty
                        ? "Select an affected class"
                        : "Choose current faculty first"}
                    </option>
                    {entries
                      .filter((e) => e.faculty === selectedCurrentFaculty)
                      .map((entry) => (
                        <option key={entry.id} value={entry.id}>
                          {entry.day} · {displayTime(entry.startTime)}–{displayTime(entry.endTime)} ·{" "}
                          {entry.courseCode} ({entry.section || "Sec A"}) · {entry.room}
                        </option>
                      ))}
                  </select>
                </label>
              </div>

              {/* Box 2: Substitute Faculty */}
              <div className="timetable-adjustment-box">
                <h4>2. Substitute Faculty Member</h4>

                <label>
                  <span>Search Registered Faculty</span>
                  <input
                    type="text"
                    value={substituteSearch}
                    onChange={(e) => setSubstituteSearch(e.target.value)}
                    placeholder="Type to filter substitute faculty..."
                  />
                </label>

                <label>
                  <span>Select Substitute Faculty</span>
                  <select
                    value={selectedSubstituteId}
                    onChange={(event) => {
                      const facId = event.target.value;
                      setSelectedSubstituteId(facId);
                      setAdjustmentError("");
                      setAdjustmentMessage("");
                    }}
                    required
                  >
                    <option value="">Select substitute faculty...</option>
                    {substituteFacultyOptions.map((f) => (
                      <option key={f.faculty_id} value={f.faculty_id}>
                        {f.name || f.user?.name} ({f.employee_id || f.designation || `ID: ${f.faculty_id}`})
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </div>

            {/* Box 3: Reason & Effective Date */}
            <div className="timetable-adjustment-box" style={{ marginTop: 12 }}>
              <h4>3. Adjustment Reason & Effective Date</h4>

              <div className="timetable-adjustment-request-grid">
                <label>
                  <span>Reason for Adjustment</span>
                  <select
                    value={adjustmentReason}
                    onChange={(event) => {
                      setAdjustmentReason(event.target.value);
                      setAdjustmentError("");
                    }}
                  >
                    <option value="Faculty unavailable">Faculty unavailable</option>
                    <option value="Schedule conflict">Schedule conflict</option>
                    <option value="Approved leave">Approved leave</option>
                    <option value="Official duty / Conference">Official duty / Conference</option>
                    <option value="Other">Other</option>
                  </select>
                </label>

                <label>
                  <span>Effective Date</span>
                  <input
                    type="date"
                    value={effectiveDate}
                    onChange={(event) => {
                      setEffectiveDate(event.target.value);
                      setAdjustmentError("");
                    }}
                    required
                  />
                </label>
              </div>

              {adjustmentReason === "Other" && (
                <label style={{ marginTop: 8 }}>
                  <span>Custom Reason</span>
                  <textarea
                    value={customAdjustmentReason}
                    onChange={(event) => {
                      setCustomAdjustmentReason(event.target.value);
                      setAdjustmentError("");
                    }}
                    placeholder="Provide detailed explanation for this emergency faculty substitution..."
                    required
                  />
                </label>
              )}

              <div className="timetable-form-actions" style={{ marginTop: 14 }}>
                <button
                  type="button"
                  className="timetable-outline-button"
                  onClick={cancelAdjustmentForm}
                  disabled={adjustmentLoading}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="timetable-primary-button"
                  disabled={adjustmentLoading}
                >
                  <FontAwesomeIcon icon={adjustmentLoading ? faSpinner : faCheck} spin={adjustmentLoading} />
                  <span>{adjustmentLoading ? "Saving Adjustment..." : "Assign Faculty Substitute"}</span>
                </button>
              </div>
            </div>
          </form>
        )}

        {/* Audit Trail Table */}
        <div className="timetable-audit-card" style={{ marginTop: 16 }}>
          <div className="timetable-audit-header">
            <span className="timetable-header-blue-icon">
              <FontAwesomeIcon icon={faShieldHalved} />
            </span>
            <div>
              <h4>Faculty Adjustments & Substitution Audit History</h4>
              <p>Permanent record of all emergency substitutions and historical adjustments.</p>
            </div>
          </div>

          <div className="timetable-table-wrapper" style={{ marginTop: 10 }}>
            <table className="timetable-table">
              <thead>
                <tr>
                  <th>Effective Date</th>
                  <th>Affected Class</th>
                  <th>Day & Time</th>
                  <th>Original Faculty</th>
                  <th>Substitute Faculty</th>
                  <th>Reason</th>
                  <th>Adjusted By</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {adjustmentsList.length ? (
                  adjustmentsList.map((adj) => (
                    <tr key={adj.adjustment_id}>
                      <td><strong>{adj.effective_date}</strong></td>
                      <td>
                        <strong>{adj.course_code || "Class"}</strong>
                        <div>{adj.course_name} ({adj.section || "Sec A"})</div>
                      </td>
                      <td>
                        {adj.day_of_week}
                        <div>{displayTime(adj.start_time)} – {displayTime(adj.end_time)}</div>
                      </td>
                      <td>{adj.original_faculty_name}</td>
                      <td>
                        <strong style={{ color: "#005fb8" }}>
                          {adj.substitute_faculty_name}
                        </strong>
                      </td>
                      <td>{adj.reason}</td>
                      <td>{adj.adjusted_by_name}</td>
                      <td>
                        <span
                          className={`timetable-pill-tag ${adj.status === "APPROVED"
                              ? "is-active"
                              : adj.status === "CANCELLED"
                                ? "is-cancelled"
                                : "is-pending"
                            }`}
                        >
                          {adj.status}
                        </span>
                      </td>
                      <td>
                        {adj.status !== "CANCELLED" ? (
                          <button
                            type="button"
                            className="timetable-action-cancel-btn"
                            onClick={() => handleCancelExistingAdjustment(adj.adjustment_id)}
                          >
                            Cancel
                          </button>
                        ) : (
                          <span style={{ color: "#8a9eb8", fontSize: 11 }}>Reverted</span>
                        )}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={9} className="timetable-table-center">
                      No faculty adjustments recorded yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Edit Timetable Entry Modal */}
      <EditTimetableModal
        isOpen={editModalOpen}
        entry={selectedEntryForEdit}
        onClose={handleCloseEditModal}
        onSave={handleSaveTimetableEdit}
      />
    </section>
  );
}

export default TimetableManagement;
