import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  faBook,
  faBookOpen,
  faGraduationCap,
  faChalkboardTeacher,
  faPlus,
  faCheck,
  faCircleExclamation,
  faXmark,
  faSpinner,
  faTrash,
  faPen,
  faRotate,
} from "@fortawesome/free-solid-svg-icons";


import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

import {
  deleteAdminEnrollment,
  getAdminEnrollments,
  previewGroupEnrollment,
  bulkEnrollGroup,
} from "../../services/enrollmentService";

import {
  getAdminAcademicSummary,
  getAdminCourses,
  createAdminCourse,
  updateAdminCourse,
  deleteAdminCourse,
  getAdminDepartments,
  getAdminCourseOfferings,
  getAdminFaculty,
  getAdminStudents,
  createAdminCourseOffering,
  updateAdminCourseOffering,
  deleteAdminCourseOffering,
  getAdminBatches,
} from "../../services/adminService";

import coursesImage from "../../../image/Courses.png";
import activeCoursesImage from "../../../image/ActiveCourses.png";
import offeringsImage from "../../../image/Offerings.png";
import enrollmentsImage from "../../../image/Enrollments.png";

import {
  formatAcademicYear,
  toCanonicalAcademicYear,
  isSingleAcademicSession,
  getAcademicYearOptions,
  extractCohortStartYear,
} from "../../utils/academicYearUtils";
import ErrorBoundary from "../../components/ErrorBoundary";

import "./AcademicManagement.css";

const TABS = [
  { id: "courses", label: "Courses", icon: faBook },
  { id: "offerings", label: "Course Offerings to Faculty", icon: faBookOpen },
  { id: "enrollments", label: "Course Enrollments to Student", icon: faGraduationCap },
  { id: "assignments", label: "Assignments", icon: faChalkboardTeacher },
];

const EMPTY_COURSE_FORM = {
  course_code: "",
  course_name: "",
  department_id: "",
  semester: "",
  credits: "",
  batch: "",
  academic_year: "",
};

const EMPTY_OFFERING_FORM = {
  course_id: "",
  faculty_id: "",
  batch: "",
  academic_year: "",
  semester: "",
  section: "",
};

function getErrorMessage(error, fallback) {
  return (
    error?.response?.data?.message ||
    error?.message ||
    fallback
  );
}

function formatDate(value) {
  if (!value) return "N/A";

  const date = new Date(value);

  return Number.isNaN(date.getTime())
    ? String(value)
    : date.toLocaleString();
}

function getPaginationItems(currentPage, totalPages) {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }

  if (currentPage <= 2) {
    return [1, 2, 3, "...", totalPages];
  }

  if (currentPage === 3) {
    return [1, 2, 3, 4, "...", totalPages];
  }

  if (currentPage === totalPages - 2) {
    return [1, "...", totalPages - 3, totalPages - 2, totalPages - 1, totalPages];
  }

  if (currentPage >= totalPages - 1) {
    return [1, "...", totalPages - 2, totalPages - 1, totalPages];
  }

  return [1, "...", currentPage - 1, currentPage, currentPage + 1, "...", totalPages];
}

function AcademicManagement() {
  const location = useLocation();
  const navigate = useNavigate();

  const academicBasePath = "/admin/academic-management";

  const getTabFromPath = () => {
    const path = location.pathname
      .replace(`${academicBasePath}/`, "")
      .replace(`${academicBasePath}`, "");

    const tabMap = {
      courses: "courses",
      "course-offerings": "offerings",
      "course-enrollments": "enrollments",
      assignments: "assignments",
    };

    return tabMap[path] || "courses";
  };

  const activeTab = getTabFromPath();


  // Summary card statistics
  const [summaryStats, setSummaryStats] = useState({
    totalCourses: null,
    activeCourses: null,
    courseOfferings: null,
    enrollments: null,
  });
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [summaryErrors, setSummaryErrors] = useState({
    totalCourses: null,
    activeCourses: null,
    courseOfferings: null,
    enrollments: null,
  });

  // Course data
  const [courses, setCourses] = useState([]);
  const [coursesLoading, setCoursesLoading] = useState(false);
  const [coursesError, setCoursesError] = useState("");
  const [departments, setDepartments] = useState([]);
  const [departmentsLoading, setDepartmentsLoading] = useState(false);
  const [departmentError, setDepartmentError] = useState("");

  const [showCourseModal, setShowCourseModal] = useState(false);
  const [editingCourseId, setEditingCourseId] = useState(null);
  const [deletingCourseId, setDeletingCourseId] = useState(null);
  const [updatingCourseStatusId, setUpdatingCourseStatusId] = useState(null);
  const [savingCourse, setSavingCourse] = useState(false);
  const [courseActionError, setCourseActionError] = useState("");
  const [courseActionMessage, setCourseActionMessage] = useState("");
  const [courseForm, setCourseForm] = useState({ ...EMPTY_COURSE_FORM });

  const [currentPage, setCurrentPage] = useState(1);
  const PAGE_SIZE = 10;
  const [offeringPage, setOfferingPage] = useState(1);
  const OFFERINGS_PAGE_SIZE = 10;
  const [enrollmentPage, setEnrollmentPage] = useState(1);
  const ENROLLMENTS_PAGE_SIZE = 10;

  // Course offering data
  const [offerings, setOfferings] = useState([]);
  const [offeringsLoading, setOfferingsLoading] = useState(false);
  const [offeringsError, setOfferingsError] = useState("");
  const [faculty, setFaculty] = useState([]);
  const [offeringDropdownLoading, setOfferingDropdownLoading] = useState(false);
  const [offeringDropdownError, setOfferingDropdownError] = useState("");

  const [showOfferingModal, setShowOfferingModal] = useState(false);
  const [editingOfferingId, setEditingOfferingId] = useState(null);
  const [savingOffering, setSavingOffering] = useState(false);
  const [deletingOfferingId, setDeletingOfferingId] = useState(null);
  const [offeringActionError, setOfferingActionError] = useState("");
  const [offeringActionMessage, setOfferingActionMessage] = useState("");
  const [offeringForm, setOfferingForm] = useState({
    ...EMPTY_OFFERING_FORM,
  });

  const [batches, setBatches] = useState([]);
  const [batchesLoading, setBatchesLoading] = useState(true);

  const academicYearOptions = useMemo(() => getAcademicYearOptions(), []);

  useEffect(() => {
    let cancelled = false;
    getAdminBatches()
      .then((result) => {
        if (!cancelled && result?.success && Array.isArray(result.data)) {
          setBatches(result.data);
        }
      })
      .catch(() => {
        // Fallback handled in batchOptions
      })
      .finally(() => {
        if (!cancelled) {
          setBatchesLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const batchOptions = useMemo(() => {
    const list = [];
    if (Array.isArray(batches) && batches.length > 0) {
      batches.forEach((b) => {
        const val = b.raw_name || b.batch_name;
        const lbl = b.batch_name || b.raw_name;
        if (val && !list.some((item) => item.value === val)) {
          list.push({ value: val, label: lbl });
        }
      });
    }
    ["2023", "2024", "2025", "2026", "2027", "2028"].forEach((y) => {
      if (!list.some((item) => item.value === y)) {
        list.push({ value: y, label: y });
      }
    });
    return list;
  }, [batches]);

  // Enrollment data
  const [enrollments, setEnrollments] = useState([]);
  const [enrollmentsLoading, setEnrollmentsLoading] = useState(false);
  const [enrollmentsLoaded, setEnrollmentsLoaded] = useState(false);
  const [enrollmentsError, setEnrollmentsError] = useState("");
  const [students, setStudents] = useState([]);
  const [studentsLoading, setStudentsLoading] = useState(false);
  const [, setStudentsError] = useState("");

  const [deletingEnrollmentId, setDeletingEnrollmentId] = useState(null);
  const [enrollmentActionError, setEnrollmentActionError] = useState("");
  const [enrollmentActionMessage, setEnrollmentActionMessage] = useState("");
  const [showGroupEnrollment, setShowGroupEnrollment] = useState(false);

  const [groupEnrollment, setGroupEnrollment] = useState({
    department_id: "",
    academic_year: "",
    semester: "",
    section: "",
  });

  const [groupPreview, setGroupPreview] = useState(null);
  const [groupPreviewLoading, setGroupPreviewLoading] = useState(false);

  // Assignment API has not yet been verified.
  const [assignmentNotice, setAssignmentNotice] = useState("");

  const loadAcademicSummary = useCallback(async (options = {}) => {
    setSummaryLoading(true);

    try {
      const result = await getAdminAcademicSummary(options);

      if (result?.success && result?.data) {
        setSummaryStats({
          totalCourses: result.data.total_courses,
          activeCourses: result.data.active_courses,
          courseOfferings: result.data.course_offerings,
          enrollments: result.data.enrollments,
        });
        setSummaryErrors({
          totalCourses:
            result.data.total_courses === null ? "Unable to load count" : null,
          activeCourses:
            result.data.active_courses === null ? "Unable to load count" : null,
          courseOfferings:
            result.data.course_offerings === null
              ? "Unable to load count"
              : null,
          enrollments:
            result.data.enrollments === null ? "Unable to load count" : null,
        });
      } else {
        throw new Error(
          result?.message || "Unable to load academic summary statistics."
        );
      }
    } catch (error) {
      const errorMsg = getErrorMessage(error, "Unable to load statistics.");
      setSummaryErrors({
        totalCourses: errorMsg,
        activeCourses: errorMsg,
        courseOfferings: errorMsg,
        enrollments: errorMsg,
      });
    } finally {
      setSummaryLoading(false);
    }
  }, []);

  // Fetch all 4 statistics whenever Academic Management mounts.
  useEffect(() => {
    let cancelled = false;

    const fetchSummary = async () => {
      setSummaryLoading(true);

      try {
        const result = await getAdminAcademicSummary();
        if (cancelled) return;

        if (result?.success && result?.data) {
          setSummaryStats({
            totalCourses: result.data.total_courses,
            activeCourses: result.data.active_courses,
            courseOfferings: result.data.course_offerings,
            enrollments: result.data.enrollments,
          });
          setSummaryErrors({
            totalCourses:
              result.data.total_courses === null
                ? "Unable to load count"
                : null,
            activeCourses:
              result.data.active_courses === null
                ? "Unable to load count"
                : null,
            courseOfferings:
              result.data.course_offerings === null
                ? "Unable to load count"
                : null,
            enrollments:
              result.data.enrollments === null
                ? "Unable to load count"
                : null,
          });
        } else {
          throw new Error(
            result?.message || "Unable to load academic summary statistics."
          );
        }
      } catch (error) {
        if (!cancelled) {
          const errorMsg = getErrorMessage(error, "Unable to load statistics.");
          setSummaryErrors({
            totalCourses: errorMsg,
            activeCourses: errorMsg,
            courseOfferings: errorMsg,
            enrollments: errorMsg,
          });
        }
      } finally {
        if (!cancelled) {
          setSummaryLoading(false);
        }
      }
    };

    void fetchSummary();

    return () => {
      cancelled = true;
    };
  }, []);

  // Load courses whenever the Courses tab is opened.
  const loadCourses = useCallback(async () => {
    setCoursesLoading(true);
    setCoursesError("");

    try {
      const [result] = await Promise.all([
        getAdminCourses(),
        loadAcademicSummary({ params: { _nocache: true } }),
      ]);

      if (!result?.success || !Array.isArray(result.data)) {
        throw new Error(result?.message || "Unable to load courses.");
      }

      setCourses(result.data);
    } catch (error) {
      setCoursesError(getErrorMessage(error, "Unable to load courses."));
    } finally {
      setCoursesLoading(false);
    }
  }, [loadAcademicSummary]);

  useEffect(() => {
    if (activeTab !== "courses") return;

    let cancelled = false;

    const load = async () => {
      setCoursesLoading(true);
      setCoursesError("");

      try {
        const result = await getAdminCourses();

        if (!result?.success || !Array.isArray(result.data)) {
          throw new Error(
            result?.message || "Unable to load courses."
          );
        }

        if (!cancelled) {
          setCourses(result.data);
        }
      } catch (error) {
        if (!cancelled) {
          setCoursesError(
            getErrorMessage(error, "Unable to load courses.")
          );
        }
      } finally {
        if (!cancelled) {
          setCoursesLoading(false);
        }
      }
    };

    void load();

    return () => {
      cancelled = true;
    };
  }, [activeTab]);

  // Load offerings, courses, and faculty together for the offering screen.
  const loadOfferingData = useCallback(async () => {
    setOfferingsLoading(true);
    setOfferingsError("");
    setOfferingActionError("");
    setOfferingActionMessage("");

    try {
      const [offeringResult, courseResult, facultyResult] =
        await Promise.all([
          getAdminCourseOfferings(),
          getAdminCourses(),
          getAdminFaculty(),
          loadAcademicSummary({ params: { _nocache: true } }),
        ]);

      if (!offeringResult?.success || !Array.isArray(offeringResult.data)) {
        throw new Error(
          offeringResult?.message || "Unable to load course offerings."
        );
      }

      if (!courseResult?.success || !Array.isArray(courseResult.data)) {
        throw new Error(courseResult?.message || "Unable to load courses.");
      }

      if (!facultyResult?.success || !Array.isArray(facultyResult.data)) {
        throw new Error(facultyResult?.message || "Unable to load faculty.");
      }

      setOfferings(offeringResult.data);
      setCourses(courseResult.data);
      setFaculty(facultyResult.data);
    } catch (error) {
      setOfferingsError(
        getErrorMessage(error, "Unable to load course offering data.")
      );
    } finally {
      setOfferingsLoading(false);
    }
  }, [loadAcademicSummary]);

  useEffect(() => {
    if (activeTab !== "offerings") return;

    let cancelled = false;

    const load = async () => {
      setOfferingsLoading(true);
      setOfferingsError("");
      setOfferingActionError("");
      setOfferingActionMessage("");

      try {
        const [offeringResult, courseResult, facultyResult] =
          await Promise.all([
            getAdminCourseOfferings(),
            getAdminCourses(),
            getAdminFaculty(),
          ]);

        if (
          !offeringResult?.success ||
          !Array.isArray(offeringResult.data)
        ) {
          throw new Error(
            offeringResult?.message ||
              "Unable to load course offerings."
          );
        }

        if (
          !courseResult?.success ||
          !Array.isArray(courseResult.data)
        ) {
          throw new Error(
            courseResult?.message || "Unable to load courses."
          );
        }

        if (
          !facultyResult?.success ||
          !Array.isArray(facultyResult.data)
        ) {
          throw new Error(
            facultyResult?.message || "Unable to load faculty."
          );
        }

        if (cancelled) return;

        setOfferings(offeringResult.data);
        setCourses(courseResult.data);
        setFaculty(facultyResult.data);
      } catch (error) {
        if (!cancelled) {
          setOfferingsError(
            getErrorMessage(
              error,
              "Unable to load course offering data."
            )
          );
        }
      } finally {
        if (!cancelled) {
          setOfferingsLoading(false);
        }
      }
    };

    void load();

    return () => {
      cancelled = true;
    };
  }, [activeTab]);


  // Load enrollment records and the data needed by the enrollment form.
  useEffect(() => {
    if (activeTab !== "enrollments") return;

    let cancelled = false;

    async function loadEnrollments() {
      setEnrollmentsLoading(true);
      setEnrollmentsError("");
      setStudentsLoading(true);
      setStudentsError("");
      setEnrollmentActionError("");
      setEnrollmentActionMessage("");

      try {
        const [
          enrollmentResult,
          studentResult,
          offeringResult,
          departmentResult,
        ] = await Promise.allSettled([
          getAdminEnrollments(),
          getAdminStudents(),
          getAdminCourseOfferings(),
          getAdminDepartments(),
        ]);

        if (cancelled) return;

        if (
          enrollmentResult.status === "fulfilled" &&
          enrollmentResult.value?.success &&
          Array.isArray(enrollmentResult.value.data)
        ) {
          setEnrollments(enrollmentResult.value.data);
          setEnrollmentsLoaded(true);
        } else {
          const error =
            enrollmentResult.status === "rejected"
              ? enrollmentResult.reason
              : new Error(
                  enrollmentResult.value?.message ||
                    "Unable to load enrollments."
                );

          setEnrollments([]);
          setEnrollmentsLoaded(true);
          setEnrollmentsError(
            getErrorMessage(error, "Unable to load enrollments.")
          );
        }

        if (
          studentResult.status === "fulfilled" &&
          studentResult.value?.success &&
          Array.isArray(studentResult.value.data)
        ) {
          setStudents(studentResult.value.data);
        } else {
          const error =
            studentResult.status === "rejected"
              ? studentResult.reason
              : new Error(
                  studentResult.value?.message ||
                    "Unable to load students."
                );

          setStudents([]);
          setStudentsError(
            getErrorMessage(error, "Unable to load students.")
          );
        }

        if (
          offeringResult.status === "fulfilled" &&
          offeringResult.value?.success &&
          Array.isArray(offeringResult.value.data)
        ) {
          setOfferings(offeringResult.value.data);
        }

        if (
          departmentResult.status === "fulfilled" &&
          departmentResult.value?.success &&
          Array.isArray(departmentResult.value.data)
        ) {
          setDepartments(departmentResult.value.data);
        } else {
          const error =
            departmentResult.status === "rejected"
              ? departmentResult.reason
              : new Error(
                  departmentResult.value?.message ||
                    "Unable to load departments."
                );

          setDepartmentError(
            getErrorMessage(error, "Unable to load departments.")
          );
        }

      } catch (error) {
        if (!cancelled) {
          setEnrollmentsError(
            getErrorMessage(error, "Unable to load enrollment data.")
          );
        }
      } finally {
        if (!cancelled) {
          setEnrollmentsLoading(false);
          setStudentsLoading(false);
        }
      }
    }

    loadEnrollments();

    return () => {
      cancelled = true;
    };
  }, [activeTab]);

  // Summary values are derived from academic summary statistics,
  // falling back to local table state if available.
  const metrics = useMemo(() => {
    const totalCourses =
      summaryStats.totalCourses !== null
        ? summaryStats.totalCourses
        : courses.length > 0
        ? courses.length
        : null;

    const activeCourses =
      summaryStats.activeCourses !== null
        ? summaryStats.activeCourses
        : courses.length > 0
        ? courses.filter(
            (course) =>
              course.is_active === true ||
              course.is_active === 1 ||
              course.status?.toLowerCase() === "active"
          ).length
        : null;

    const offeringsCount =
      summaryStats.courseOfferings !== null
        ? summaryStats.courseOfferings
        : offerings.length > 0
        ? offerings.length
        : null;

    const enrollmentsCount =
      summaryStats.enrollments !== null
        ? summaryStats.enrollments
        : enrollmentsLoaded
        ? enrollments.length
        : null;

    return {
      totalCourses,
      activeCourses,
      offerings: offeringsCount,
      enrollments: enrollmentsCount,
    };
  }, [summaryStats, courses, offerings, enrollments, enrollmentsLoaded]);

  const handleToggleCourseStatus = async (course) => {
    const courseId = course.course_id;

    if (!courseId || updatingCourseStatusId !== null) return;

    const nextIsActive = !(
      course.is_active === true ||
      course.is_active === 1 ||
      course.status?.toLowerCase() === "active"
    );

    setUpdatingCourseStatusId(courseId);
    setCourseActionError("");
    setCourseActionMessage("");

    try {
      const result = await updateAdminCourse(courseId, {
        is_active: nextIsActive,
      });

      if (!result?.success) {
        throw new Error(
          result?.message || "Unable to update course status."
        );
      }

      setCourses((currentCourses) =>
        currentCourses.map((item) =>
          item.course_id === courseId
            ? { ...item, is_active: nextIsActive }
            : item
        )
      );

      setSummaryStats((prev) => ({
        ...prev,
        activeCourses:
          prev.activeCourses !== null
            ? Math.max(0, prev.activeCourses + (nextIsActive ? 1 : -1))
            : null,
      }));

      setCourseActionMessage(
        `${course.course_code || "Course"} ${
          nextIsActive ? "activated" : "deactivated"
        } successfully.`
      );

      void loadAcademicSummary({ params: { _nocache: true } });
    } catch (error) {
      setCourseActionError(
        getErrorMessage(error, "Unable to update course status.")
      );
    } finally {
      setUpdatingCourseStatusId(null);
    }
  };

  const handleTabChange = (tabId) => {
    const tabPaths = {
      courses: "",
      offerings: "course-offerings",
      enrollments: "course-enrollments",
      assignments: "assignments",
    };

    const tabPath = tabPaths[tabId];

    if (tabPath === undefined) {
      return;
    }

    navigate(
      tabPath
        ? `${academicBasePath}/${tabPath}`
        : academicBasePath
    );

    setAssignmentNotice("");
    setCourseActionError("");
    setCourseActionMessage("");
  };

  // Open the course modal even if department loading fails.
  // The error is displayed inside the modal and the admin can retry.
  const handleOpenCourseModal = async (course = null) => {
    setCourseActionError("");
    setCourseActionMessage("");
    setDepartmentError("");

    setEditingCourseId(course?.course_id ?? null);

    const initialBatch = course?.batch || "";
    const initialSem = course?.semester ? Number(course.semester) : 1;
    const initialAY = course?.academic_year || (initialBatch ? toCanonicalAcademicYear(initialBatch, initialSem) : "");

    setCourseForm(
      course
        ? {
            course_code: course.course_code || "",
            course_name: course.course_name || "",
            department_id: String(course.department_id ?? ""),
            semester: String(course.semester ?? ""),
            credits: String(course.credits ?? ""),
            batch: initialBatch,
            academic_year: initialAY,
          }
        : { ...EMPTY_COURSE_FORM }
    );

    setShowCourseModal(true);

    if (departments.length === 0) {
      setDepartmentsLoading(true);

      try {
        const result = await getAdminDepartments();

        if (!result?.success || !Array.isArray(result.data)) {
          throw new Error(
            result?.message || "Unable to load departments."
          );
        }

        setDepartments(result.data);
      } catch (error) {
        setDepartments([]);
        setDepartmentError(
          getErrorMessage(error, "Unable to load departments.")
        );
      } finally {
        setDepartmentsLoading(false);
      }
    }
  };

  const handleDeleteCourse = async (course) => {
    if (savingCourse || deletingCourseId !== null) return;

    const courseId = course.course_id;

    if (!courseId) {
      setCourseActionError("Unable to identify the course to delete.");
      return;
    }

    const confirmed = window.confirm(
      `Delete course "${course.course_code} — ${course.course_name}"?\n\n` +
        "Courses with existing course offerings cannot be deleted."
    );

    if (!confirmed) return;

    setDeletingCourseId(courseId);
    setCourseActionError("");
    setCourseActionMessage("");

    try {
      const result = await deleteAdminCourse(courseId);

      if (!result?.success) {
        throw new Error(result?.message || "Unable to delete course.");
      }

      setCourses((current) =>
        current.filter((item) => item.course_id !== courseId)
      );

      setCourseActionMessage(
        result.message || "Course deleted successfully."
      );

      // Re-fetch to keep the table synchronized with the backend.
      await loadCourses();
    } catch (error) {
      setCourseActionError(
        getErrorMessage(error, "Unable to delete course.")
      );
    } finally {
      setDeletingCourseId(null);
    }
  };

  const handleSaveCourse = async (event) => {
    event.preventDefault();

    const semester = Number(courseForm.semester);
    const credits = Number(courseForm.credits);
    const departmentId = Number(courseForm.department_id);
    const isEditing = editingCourseId !== null;
    const selectedBatch = courseForm.batch.trim();
    const canonAcademicYear = courseForm.academic_year.trim()
      ? toCanonicalAcademicYear(courseForm.academic_year.trim(), semester)
      : (selectedBatch ? toCanonicalAcademicYear(selectedBatch, semester) : "");

    const payload = {
      course_code: courseForm.course_code.trim(),
      course_name: courseForm.course_name.trim(),
      department_id: departmentId,
      semester,
      credits,
      batch: selectedBatch || extractCohortStartYear(canonAcademicYear),
      academic_year: canonAcademicYear,
    };

    if (
      !payload.course_code ||
      !payload.course_name ||
      !payload.batch ||
      !Number.isInteger(departmentId) ||
      departmentId <= 0 ||
      !Number.isInteger(semester) ||
      semester < 1 ||
      !Number.isInteger(credits) ||
      credits < 1
    ) {
      setCourseActionError(
        "Complete all course fields with valid values."
      );
      return;
    }

    setSavingCourse(true);
    setCourseActionError("");
    setCourseActionMessage("");

    try {
      const result = isEditing
        ? await updateAdminCourse(editingCourseId, payload)
        : await createAdminCourse(payload);

      if (!result?.success) {
        throw new Error(
          result?.message ||
            (isEditing
              ? "Unable to update course."
              : "Unable to create course.")
        );
      }

      setShowCourseModal(false);
      setEditingCourseId(null);
      setCourseForm({ ...EMPTY_COURSE_FORM });

      setCourseActionMessage(
        result.message ||
          (isEditing
            ? "Course updated successfully."
            : "Course created successfully.")
      );

      await loadCourses();
    } catch (error) {
      setCourseActionError(
        getErrorMessage(
          error,
          isEditing
            ? "Unable to update course."
            : "Unable to create course."
        )
      );
    } finally {
      setSavingCourse(false);
    }
  };

  const loadOfferingDropdowns = useCallback(async () => {
    setOfferingDropdownLoading(true);
    setOfferingDropdownError("");

    try {
      const [courseResult, facultyResult] = await Promise.allSettled([
        getAdminCourses(),
        getAdminFaculty(),
      ]);

      let errorMsg = "";

      if (
        courseResult.status === "fulfilled" &&
        courseResult.value?.success &&
        Array.isArray(courseResult.value.data)
      ) {
        setCourses(courseResult.value.data);
      } else {
        const err =
          courseResult.status === "rejected"
            ? courseResult.reason
            : new Error(courseResult.value?.message || "Unable to load courses.");
        errorMsg = getErrorMessage(err, "Unable to load courses.");
      }

      if (
        facultyResult.status === "fulfilled" &&
        facultyResult.value?.success &&
        Array.isArray(facultyResult.value.data)
      ) {
        setFaculty(facultyResult.value.data);
      } else {
        const err =
          facultyResult.status === "rejected"
            ? facultyResult.reason
            : new Error(facultyResult.value?.message || "Unable to load faculty.");
        const fMsg = getErrorMessage(err, "Unable to load faculty.");
        errorMsg = errorMsg ? `${errorMsg} ${fMsg}` : fMsg;
      }

      if (errorMsg && (courses.length === 0 || faculty.length === 0)) {
        setOfferingDropdownError(errorMsg);
      }
    } catch (err) {
      setOfferingDropdownError(
        getErrorMessage(err, "Unable to load course or faculty options.")
      );
    } finally {
      setOfferingDropdownLoading(false);
    }
  }, [courses.length, faculty.length]);

  const handleOpenOfferingModal = async (offering = null) => {
    setOfferingActionError("");
    setOfferingActionMessage("");
    setOfferingDropdownError("");
    setEditingOfferingId(offering?.offering_id ?? null);

    const initialBatch =
      offering?.batch ||
      (courses.find((c) => String(c.course_id) === String(offering?.course_id))?.batch || "");

    setOfferingForm(
      offering
        ? {
            course_id: String(offering.course_id ?? ""),
            faculty_id: String(offering.faculty_id ?? ""),
            batch: initialBatch,
            academic_year: offering.academic_year
              ? toCanonicalAcademicYear(formatAcademicYear(offering.academic_year, offering.semester, offering.batch || initialBatch))
              : "",
            semester: String(offering.semester ?? ""),
            section: offering.section || "",
          }
        : { ...EMPTY_OFFERING_FORM }
    );

    setShowOfferingModal(true);

    if (courses.length === 0 || faculty.length === 0) {
      await loadOfferingDropdowns();
    }
  };

  const handleSaveOffering = async (event) => {
    event.preventDefault();

    const isEditing = editingOfferingId !== null;

    const canonAcademicYear = toCanonicalAcademicYear(
      offeringForm.academic_year.trim(),
      Number(offeringForm.semester)
    );

    if (!isSingleAcademicSession(canonAcademicYear)) {
      setOfferingActionError(
        "Academic Year must be a 1-year academic session consisting of two consecutive calendar years (e.g. 2025-2026)."
      );
      return;
    }

    const payload = {
      course_id: Number(offeringForm.course_id),
      batch: offeringForm.batch.trim(),
      academic_year: canonAcademicYear,
      semester: Number(offeringForm.semester),
      section: offeringForm.section.trim(),
    };

    // Faculty is required only when creating a new offering.
    if (!isEditing) {
      payload.faculty_id = Number(offeringForm.faculty_id);
    }

    if (
      !Number.isInteger(payload.course_id) ||
      payload.course_id <= 0 ||
      (!isEditing &&
        (!Number.isInteger(payload.faculty_id) ||
          payload.faculty_id <= 0)) ||
      !Number.isInteger(payload.semester) ||
      payload.semester < 1 ||
      !payload.academic_year ||
      !payload.section
    ) {
      setOfferingActionError(
        isEditing
          ? "Please provide a valid course, academic year, semester, and section."
          : "Please provide valid course, faculty, academic year, semester, and section details."
      );
      return;
    }

    setSavingOffering(true);
    setOfferingActionError("");
    setOfferingActionMessage("");

    try {
      const result = isEditing
        ? await updateAdminCourseOffering(editingOfferingId, payload)
        : await createAdminCourseOffering(payload);

      if (!result?.success) {
        throw new Error(
          result?.message ||
            (isEditing
              ? "Unable to update course offering."
              : "Unable to create course offering.")
        );
      }

      setOfferingActionMessage(
        result?.message ||
          (isEditing
            ? "Course offering updated successfully."
            : "Course offering created successfully.")
      );

      setShowOfferingModal(false);
      setEditingOfferingId(null);
      setOfferingForm({ ...EMPTY_OFFERING_FORM });

      // Refresh the list using the component's existing refresh logic.
      await loadOfferingData();
    } catch (error) {
      setOfferingActionError(
        getErrorMessage(
          error,
          isEditing
            ? "Unable to update course offering."
            : "Unable to create course offering."
        )
      );
    } finally {
      setSavingOffering(false);
    }
  };

  const handleDeleteOffering = async (offering) => {
    const confirmed = window.confirm(
      `Delete offering #${offering.offering_id} (${offering.course_code || "course"})?`
    );

    if (!confirmed) return;

    setDeletingOfferingId(offering.offering_id);
    setOfferingActionError("");
    setOfferingActionMessage("");

    try {
      const result = await deleteAdminCourseOffering(offering.offering_id);

      if (!result?.success) {
        throw new Error(result?.message || "Unable to delete course offering.");
      }

      setOfferings((current) =>
        current.filter(
          (item) => item.offering_id !== offering.offering_id
        )
      );

      setOfferingActionMessage(
        result.message || "Course offering deleted successfully."
      );

      void loadAcademicSummary({ params: { _nocache: true } });
    } catch (error) {
      setOfferingActionError(
        getErrorMessage(error, "Unable to delete course offering.")
      );
    } finally {
      setDeletingOfferingId(null);
    }
  };


  const handleRefreshEnrollments = async () => {
    setEnrollmentsLoading(true);
    setEnrollmentsError("");
    setEnrollmentActionError("");

    try {
      const [result] = await Promise.all([
        getAdminEnrollments(),
        loadAcademicSummary({ params: { _nocache: true } }),
      ]);

      if (!result?.success || !Array.isArray(result.data)) {
        throw new Error(result?.message || "Unable to refresh enrollments.");
      }

      setEnrollments(result.data);
      setEnrollmentsLoaded(true);
      setEnrollmentPage(1);
    } catch (error) {
      setEnrollmentsError(
        getErrorMessage(error, "Unable to refresh enrollments.")
      );
    } finally {
      setEnrollmentsLoading(false);
    }
  };

  const handlePreviewGroupEnrollment = async () => {
    const { department_id, academic_year, semester, section } =
      groupEnrollment;

    if (!department_id || !academic_year || !semester || !section) {
      setEnrollmentActionError(
        "Select a department, cohort, semester, and section first."
      );
      return;
    }

    setGroupPreviewLoading(true);
    setEnrollmentActionError("");
    setEnrollmentActionMessage("");

    try {
      // First load all matching offerings for the selected group.
      // Load the full set of matching offerings. The checkbox selection is
      // managed locally and must not filter the preview response.
      const result = await previewGroupEnrollment(groupEnrollment, []);

      if (!result?.success) {
        throw new Error(
          result?.message || "Unable to preview group enrollment."
        );
      }

      const previewData = result.data ?? result;

      setGroupPreview(previewData);

    } catch (error) {
      setEnrollmentActionError(
        getErrorMessage(error, "Unable to preview group enrollment.")
      );
    } finally {
      setGroupPreviewLoading(false);
    }
  };

  const handleBulkEnrollGroup = async () => {
    if (!groupPreview) {
      setEnrollmentActionError("Preview the group before enrolling students.");
      return;
    }

    const studentCount = groupPreview.eligible_students ?? 0;
    const courseCount =
      groupPreview.courses?.length ??
      groupPreview.offerings?.length ??
      0;

    if (studentCount === 0 || courseCount === 0) {
      setEnrollmentActionError(
        "No eligible students or active courses were found."
      );
      return;
    }

    const confirmed = window.confirm(
      `Enroll ${studentCount} eligible students in all ${courseCount} active courses for this group? Missing course offerings may be created without faculty assignments.`
    );

    if (!confirmed) return;

    setGroupPreviewLoading(true);
    setEnrollmentActionError("");
    setEnrollmentActionMessage("");

    try {
      const result = await bulkEnrollGroup(groupEnrollment);

      if (!result?.success) {
        throw new Error(result?.message || "Bulk enrollment failed.");
      }

      const summary = result.data ?? {};

      // Refresh both lists in parallel after the successful operation.
      const [offeringResult, enrollmentResult] = await Promise.all([
        getAdminCourseOfferings(),
        getAdminEnrollments(),
      ]);

      if (
        !offeringResult?.success ||
        !Array.isArray(offeringResult.data)
      ) {
        throw new Error(
          "Enrollment succeeded, but course offerings could not be refreshed."
        );
      }

      if (
        !enrollmentResult?.success ||
        !Array.isArray(enrollmentResult.data)
      ) {
        throw new Error(
          "Enrollment succeeded, but enrollment records could not be refreshed."
        );
      }

      // Update React state immediately; no browser refresh is needed.
      setOfferings(offeringResult.data);
      setEnrollments(enrollmentResult.data);
      setEnrollmentsLoaded(true);

      setEnrollmentActionMessage(
        `Enrollment completed. Created ${summary.created ?? 0} enrollments, ` +
        `skipped ${summary.already_enrolled ?? 0} existing enrollments, and ` +
        `created ${summary.created_offerings ?? 0} course offerings.`
      );

      // Refresh the group preview as well.
      await handlePreviewGroupEnrollment();
      void loadAcademicSummary({ params: { _nocache: true } });
    } catch (error) {
      setEnrollmentActionError(
        getErrorMessage(error, "Unable to complete bulk enrollment.")
      );
    } finally {
      setGroupPreviewLoading(false);
    }
  };

  const handleGroupEnrollmentChange = (field, value) => {
    setGroupEnrollment((current) => ({
      ...current,
      [field]: value,
    }));

    setGroupPreview(null);
    setEnrollmentActionError("");
    setEnrollmentActionMessage("");
  };

  const handleDeleteEnrollment = async (enrollmentId) => {
    if (!window.confirm(`Remove enrollment #${enrollmentId}?`)) return;

    setDeletingEnrollmentId(enrollmentId);
    setEnrollmentActionError("");
    setEnrollmentActionMessage("");

    try {
      const result = await deleteAdminEnrollment(enrollmentId);

      if (!result?.success) {
        throw new Error(result?.message || "Unable to remove enrollment.");
      }

      setEnrollments((current) =>
        current.filter(
          (enrollment) => enrollment.enrollment_id !== enrollmentId
        )
      );
      setEnrollmentPage(1);

      setEnrollmentActionMessage(
        result.message || "Enrollment removed successfully."
      );

      void loadAcademicSummary({ params: { _nocache: true } });
    } catch (error) {
      setEnrollmentActionError(
        getErrorMessage(error, "Unable to remove enrollment.")
      );
    } finally {
      setDeletingEnrollmentId(null);
    }
  };

  const renderNotice = (title, message, isError = false) => {
    if (!message) return null;

    return (
      <div
        className="academic-integration-notice"
        role={isError ? "alert" : "status"}
      >
        <div className="academic-integration-icon" aria-hidden="true">
          <FontAwesomeIcon icon={isError ? faCircleExclamation : faCheck} />
        </div>
        <div>
          <strong>{title}</strong>
          <span>{message}</span>
        </div>
      </div>
    );
  };

  const totalCourses = courses.length;

  const totalPages = Math.max(
    1,
    Math.ceil(totalCourses / PAGE_SIZE)
  );

  const safeCurrentPage = Math.min(currentPage, totalPages);

  const paginatedCourses = useMemo(() => {
    const startIndex = (safeCurrentPage - 1) * PAGE_SIZE;

    return courses.slice(startIndex, startIndex + PAGE_SIZE);
  }, [courses, safeCurrentPage]);

  const totalOfferingPages = Math.max(
    1,
    Math.ceil(offerings.length / OFFERINGS_PAGE_SIZE)
  );

  const safeOfferingPage = Math.min(
    offeringPage,
    totalOfferingPages
  );

  const paginatedOfferings = useMemo(() => {
    const startIndex =
      (safeOfferingPage - 1) * OFFERINGS_PAGE_SIZE;

    return offerings.slice(
      startIndex,
      startIndex + OFFERINGS_PAGE_SIZE
    );
  }, [offerings, safeOfferingPage]);

  const totalEnrollmentPages = Math.max(
    1,
    Math.ceil(enrollments.length / ENROLLMENTS_PAGE_SIZE)
  );

  const safeEnrollmentPage = Math.min(
    enrollmentPage,
    totalEnrollmentPages
  );

  const paginatedEnrollments = enrollments.slice(
    (safeEnrollmentPage - 1) * ENROLLMENTS_PAGE_SIZE,
    safeEnrollmentPage * ENROLLMENTS_PAGE_SIZE
  );

  return (
    <ErrorBoundary>
      <section className="academic-management-page">
      <header className="academic-page-header">
        <div>
          <span className="academic-eyebrow">Admin Portal</span>
          <h1>Academic Management</h1>
          <p>
            Manage courses, course offerings, enrollments and assignments.
          </p>
        </div>

        {activeTab === "enrollments" && (
          <button
            type="button"
            className="academic-primary-button"
            onClick={() => {
              setShowGroupEnrollment(true);
              setEnrollmentActionError("");
              setEnrollmentActionMessage("");
            }}
            disabled={groupPreviewLoading}
          >
            <FontAwesomeIcon icon={faPlus} />
            Add Enrollment Student
          </button>
        )}

        {activeTab === "courses" && (
          <button
            type="button"
            className="academic-primary-button"
            onClick={handleOpenCourseModal}
          >
            <FontAwesomeIcon icon={faPlus} />
            Add Course
          </button>
        )}

        {activeTab === "offerings" && (
          <button
            type="button"
            className="academic-primary-button"
            onClick={() => handleOpenOfferingModal()}
          >
            <FontAwesomeIcon icon={faPlus} />
            Add Offering
          </button>
        )}

        {activeTab === "assignments" && (
          <button
            type="button"
            className="academic-primary-button"
            onClick={() =>
              setAssignmentNotice(
                "Assignment creation is not connected yet. A verified assignment API and request format are required before this action can save data."
              )
            }
          >
            <FontAwesomeIcon icon={faPlus} />
            Add Assignment
          </button>
        )}
      </header>

      {activeTab === "courses" && (
        <>
          {renderNotice("Course action failed", courseActionError, true)}
          {renderNotice("Course updated", courseActionMessage)}
        </>
      )}

      <div className="academic-summary-grid">
        <article
          className="academic-summary-card academic-summary-blue"
          onClick={() => handleTabChange("courses")}
          role="button"
          tabIndex={0}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              handleTabChange("courses");
            }
          }}
        >
          <div className="academic-summary-content">
            <div className="academic-summary-top">
              <div className="academic-summary-icon" aria-hidden="true">
                <FontAwesomeIcon icon={faBookOpen} />
              </div>
              <span className="academic-summary-badge">All Courses</span>
            </div>
            <strong>
              {summaryErrors.totalCourses && metrics.totalCourses === null ? (
                <span
                  className="academic-summary-stat-error"
                  title={summaryErrors.totalCourses}
                >
                  Error
                  <button
                    type="button"
                    className="academic-summary-retry-btn"
                    title="Retry loading count"
                    onClick={(e) => {
                      e.stopPropagation();
                      void loadAcademicSummary({ params: { _nocache: true } });
                    }}
                  >
                    <FontAwesomeIcon icon={faRotate} />
                  </button>
                </span>
              ) : summaryLoading && metrics.totalCourses === null ? (
                <span
                  className="academic-summary-skeleton"
                  aria-label="Loading total courses"
                />
              ) : (
                metrics.totalCourses ?? 0
              )}
            </strong>
            <span>Total Courses</span>
            <span className="academic-summary-link">
              View all courses <span aria-hidden="true">→</span>
            </span>
          </div>
          <img
            className="academic-summary-art"
            src={coursesImage}
            alt=""
            aria-hidden="true"
          />
        </article>

        <article
          className="academic-summary-card academic-summary-green"
          onClick={() => handleTabChange("courses")}
          role="button"
          tabIndex={0}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              handleTabChange("courses");
            }
          }}
        >
          <div className="academic-summary-content">
            <div className="academic-summary-top">
              <div className="academic-summary-icon" aria-hidden="true">
                <FontAwesomeIcon icon={faCheck} />
              </div>
              <span className="academic-summary-badge">Active</span>
            </div>
            <strong>
              {summaryErrors.activeCourses && metrics.activeCourses === null ? (
                <span
                  className="academic-summary-stat-error"
                  title={summaryErrors.activeCourses}
                >
                  Error
                  <button
                    type="button"
                    className="academic-summary-retry-btn"
                    title="Retry loading count"
                    onClick={(e) => {
                      e.stopPropagation();
                      void loadAcademicSummary({ params: { _nocache: true } });
                    }}
                  >
                    <FontAwesomeIcon icon={faRotate} />
                  </button>
                </span>
              ) : summaryLoading && metrics.activeCourses === null ? (
                <span
                  className="academic-summary-skeleton"
                  aria-label="Loading active courses"
                />
              ) : (
                metrics.activeCourses ?? 0
              )}
            </strong>
            <span>Active Courses</span>
            <span className="academic-summary-link">
              View active courses <span aria-hidden="true">→</span>
            </span>
          </div>
          <img
            className="academic-summary-art"
            src={activeCoursesImage}
            alt=""
            aria-hidden="true"
          />
        </article>

        <article
          className="academic-summary-card academic-summary-purple"
          onClick={() => handleTabChange("offerings")}
          role="button"
          tabIndex={0}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              handleTabChange("offerings");
            }
          }}
        >
          <div className="academic-summary-content">
            <div className="academic-summary-top">
              <div className="academic-summary-icon" aria-hidden="true">
                <FontAwesomeIcon icon={faBookOpen} />
              </div>
              <span className="academic-summary-badge">Schedule</span>
            </div>
            <strong>
              {summaryErrors.courseOfferings && metrics.offerings === null ? (
                <span
                  className="academic-summary-stat-error"
                  title={summaryErrors.courseOfferings}
                >
                  Error
                  <button
                    type="button"
                    className="academic-summary-retry-btn"
                    title="Retry loading count"
                    onClick={(e) => {
                      e.stopPropagation();
                      void loadAcademicSummary({ params: { _nocache: true } });
                    }}
                  >
                    <FontAwesomeIcon icon={faRotate} />
                  </button>
                </span>
              ) : summaryLoading && metrics.offerings === null ? (
                <span
                  className="academic-summary-skeleton"
                  aria-label="Loading course offerings"
                />
              ) : (
                metrics.offerings ?? 0
              )}
            </strong>
            <span>Course Offerings</span>
            <span className="academic-summary-link">
              Manage offerings <span aria-hidden="true">→</span>
            </span>
          </div>
          <img
            className="academic-summary-art"
            src={offeringsImage}
            alt=""
            aria-hidden="true"
          />
        </article>

        <article
          className="academic-summary-card academic-summary-orange"
          onClick={() => handleTabChange("enrollments")}
          role="button"
          tabIndex={0}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              handleTabChange("enrollments");
            }
          }}
        >
          <div className="academic-summary-content">
            <div className="academic-summary-top">
              <div className="academic-summary-icon" aria-hidden="true">
                <FontAwesomeIcon icon={faGraduationCap} />
              </div>
              <span className="academic-summary-badge">Students</span>
            </div>
            <strong>
              {summaryErrors.enrollments && metrics.enrollments === null ? (
                <span
                  className="academic-summary-stat-error"
                  title={summaryErrors.enrollments}
                >
                  Error
                  <button
                    type="button"
                    className="academic-summary-retry-btn"
                    title="Retry loading count"
                    onClick={(e) => {
                      e.stopPropagation();
                      void loadAcademicSummary({ params: { _nocache: true } });
                    }}
                  >
                    <FontAwesomeIcon icon={faRotate} />
                  </button>
                </span>
              ) : summaryLoading && metrics.enrollments === null ? (
                <span
                  className="academic-summary-skeleton"
                  aria-label="Loading enrollments"
                />
              ) : (
                metrics.enrollments ?? 0
              )}
            </strong>
            <span>Enrollments</span>
            <span className="academic-summary-link">
              View enrollments <span aria-hidden="true">→</span>
            </span>
          </div>
          <img
            className="academic-summary-art"
            src={enrollmentsImage}
            alt=""
            aria-hidden="true"
          />
        </article>
      </div>

      <div className="academic-tabs" role="tablist" aria-label="Academic sections">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.id}
            className={`academic-tab ${
              activeTab === tab.id ? "academic-tab-active" : ""
            }`}
            onClick={() => handleTabChange(tab.id)}
          >
            <FontAwesomeIcon icon={tab.icon} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* COURSES */}
      {activeTab === "courses" && (
        <div className="academic-table-card">
          <div className="academic-section-header">
            <div className="academic-section-heading">
              <span className="academic-section-eyebrow">
                ACADEMIC MANAGEMENT
              </span>

              <h2>Courses</h2>

              <p>
                Manage course details, departments, credits, and
                academic structure.
              </p>
            </div>

            <button
              type="button"
              className="academic-refresh-button"
              onClick={loadCourses}
              disabled={coursesLoading}
            >
              <FontAwesomeIcon
                icon={faRotate}
                spin={coursesLoading}
              />
              <span>{coursesLoading ? "Refreshing..." : "Refresh"}</span>
            </button>
          </div>

          {coursesLoading ? (
            <div className="academic-empty-state">
              <div className="academic-empty-icon" aria-hidden="true">
                <FontAwesomeIcon icon={faSpinner} spin />
              </div>
              <h2>Loading courses</h2>
              <p>Fetching courses from the backend.</p>
            </div>
          ) : coursesError ? (
            <div className="academic-empty-state">
              <div className="academic-empty-icon" aria-hidden="true">
                <FontAwesomeIcon icon={faCircleExclamation} />
              </div>
              <h2>Unable to load courses</h2>
              <p>{coursesError}</p>
              <button
                type="button"
                className="academic-primary-button"
                onClick={loadCourses}
              >
                <FontAwesomeIcon icon={faRotate} />
                Retry
              </button>
            </div>
          ) : courses.length === 0 ? (
            <div className="academic-empty-state">
              <div className="academic-empty-icon" aria-hidden="true">
                <FontAwesomeIcon icon={faBook} />
              </div>
              <h2>No courses yet</h2>
              <p>Create your first course to enable course offerings.</p>
              <button
                type="button"
                className="academic-primary-button"
                onClick={handleOpenCourseModal}
              >
                <FontAwesomeIcon icon={faPlus} />
                Add Course
              </button>
            </div>
          ) : (
            <div className="academic-table-wrapper">
              <table className="academic-table">
                <thead>
                  <tr>
                    <th>Course ID</th>
                    <th>Course Code</th>
                    <th>Course Name</th>
                    <th>Department</th>
                    <th>Semester</th>
                    <th>Credits</th>
                    <th>Batch</th>
                    <th>Academic Year</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedCourses.map((course, index) => {
                    const courseId = course.course_id;
                    const isDeleting = deletingCourseId === courseId;
                    const actionsDisabled =
                      savingCourse || deletingCourseId !== null;

                    return (
                      <tr
                        key={
                          courseId ??
                          course.id ??
                          `${course.course_code}-${index}`
                        }
                      >
                        <td>{courseId ?? course.id ?? "—"}</td>
                        <td>
                          <strong>{course.course_code || "—"}</strong>
                        </td>
                        <td>{course.course_name || "—"}</td>
                        <td>
                          {course.department_code ||
                            course.department_name ||
                            course.department_id ||
                            "—"}
                        </td>
                        <td>{course.semester ?? "—"}</td>
                        <td>{course.credits ?? "—"}</td>
                        <td>{course.batch || "—"}</td>
                        <td>
                          {formatAcademicYear(
                            course.academic_year || course.batch,
                            course.semester
                          )}
                        </td>
                        <td>
                          <button
                            type="button"
                            className={`academic-course-status-toggle ${
                              course.is_active === true ||
                              course.is_active === 1 ||
                              course.status?.toLowerCase() === "active"
                                ? "is-active"
                                : "is-inactive"
                            }`}
                            onClick={() => handleToggleCourseStatus(course)}
                            disabled={
                              savingCourse ||
                              deletingCourseId !== null ||
                              updatingCourseStatusId !== null
                            }
                            aria-label={`Change status of ${course.course_code}`}
                          >
                            {updatingCourseStatusId === course.course_id
                              ? "Updating..."
                              : course.is_active === true ||
                                  course.is_active === 1 ||
                                  course.status?.toLowerCase() === "active"
                                ? "Deactivate"
                                : "Activate"}
                          </button>
                        </td>
                        <td>
                          <div className="academic-action-group">
                            <button
                              type="button"
                              className="academic-action-button"
                              title="Edit course"
                              aria-label={`Edit ${course.course_name}`}
                              onClick={() => handleOpenCourseModal(course)}
                              disabled={savingCourse || deletingCourseId !== null}
                            >
                              <FontAwesomeIcon icon={faPen} />
                            </button>

                            <button
                              type="button"
                              className="academic-action-button danger"
                              title="Delete course"
                              aria-label={`Delete ${course.course_name}`}
                              onClick={() => handleDeleteCourse(course)}
                              disabled={actionsDisabled}
                            >
                              <FontAwesomeIcon
                                icon={isDeleting ? faSpinner : faTrash}
                                spin={isDeleting}
                              />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <div className="academic-pagination">
                <div className="academic-pagination-info">
                  Showing{" "}
                  {totalCourses === 0
                    ? 0
                    : (safeCurrentPage - 1) * PAGE_SIZE + 1}
                  {"–"}
                  {Math.min(safeCurrentPage * PAGE_SIZE, totalCourses)}
                  {" of "}
                  {totalCourses} courses
                </div>

                <div className="academic-pagination-controls">
                  <button
                    type="button"
                    className="academic-page-button"
                    disabled={safeCurrentPage === 1}
                    onClick={() =>
                      setCurrentPage((page) => Math.max(1, page - 1))
                    }
                  >
                    Previous
                  </button>

                  {getPaginationItems(safeCurrentPage, totalPages).map((item, index) =>
                    item === "..." ? (
                      <span key={`ellipsis-${index}`} className="academic-page-ellipsis">
                        ...
                      </span>
                    ) : (
                      <button
                        type="button"
                        key={item}
                        className={`academic-page-button ${
                          safeCurrentPage === item ? "active" : ""
                        }`}
                        aria-current={
                          safeCurrentPage === item ? "page" : undefined
                        }
                        onClick={() => setCurrentPage(item)}
                      >
                        {item}
                      </button>
                    )
                  )}

                  <button
                    type="button"
                    className="academic-page-button"
                    disabled={safeCurrentPage === totalPages}
                    onClick={() =>
                      setCurrentPage((page) =>
                        Math.min(totalPages, page + 1)
                      )
                    }
                  >
                    Next
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* COURSE OFFERINGS */}
      {activeTab === "offerings" && (
        <div className="academic-table-card">
          <div className="academic-section-header">
            <div className="academic-section-heading">
              <span className="academic-section-eyebrow">
                ACADEMIC MANAGEMENT
              </span>

              <h2>Course Offerings to Faculty</h2>

              <p>
                Assign courses to faculty for an academic year,
                semester, and section.
              </p>
            </div>

            <button
              type="button"
              className="academic-refresh-button"
              onClick={loadOfferingData}
              disabled={offeringsLoading}
            >
              <FontAwesomeIcon
                icon={faRotate}
                spin={offeringsLoading}
              />
              <span>
                {offeringsLoading ? "Refreshing..." : "Refresh"}
              </span>
            </button>
          </div>

          {offeringsLoading ? (
            <div className="academic-empty-state">
              <FontAwesomeIcon icon={faSpinner} spin />
              <h2>Loading course offerings</h2>
            </div>
          ) : offeringsError ? (
            <div className="academic-empty-state">
              <FontAwesomeIcon icon={faCircleExclamation} />
              <h2>Unable to load course offerings</h2>
              <p>{offeringsError}</p>
            </div>
          ) : offerings.length === 0 ? (
            <div className="academic-empty-state">
              <div className="academic-empty-icon" aria-hidden="true">
                <FontAwesomeIcon icon={faBookOpen} />
              </div>
              <h2>No course offerings yet</h2>
              <p>
                Course offerings and faculty assignments are automatically generated and synchronized
                when timetables are imported via Timetable Management.
              </p>
            </div>
          ) : (
            <div className="academic-table-wrapper">
              <table className="academic-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Course</th>
                    <th>Faculty</th>
                    <th>Batch</th>
                    <th>Academic Year</th>
                    <th>Semester</th>
                    <th>Section</th>
                    <th>Enrollments</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedOfferings.map((offering) => (
                    <tr key={offering.offering_id}>
                      <td>{offering.offering_id}</td>
                      <td>
                        <strong>{offering.course_code || "—"}</strong>
                        <br />
                        {offering.course_name || "—"}
                      </td>
                      <td>
                        {offering.faculty_name ||
                          `Faculty #${offering.faculty_id}`}
                      </td>
                      <td>{offering.batch || "—"}</td>
                      <td>
                        {formatAcademicYear(
                          offering.academic_year,
                          offering.semester,
                          offering.batch
                        )}
                      </td>
                      <td>{offering.semester ?? "—"}</td>
                      <td>{offering.section || "—"}</td>
                      <td>{offering.enrollment_count ?? 0}</td>
                      <td>
                        <div className="academic-action-group">
                          <button
                            type="button"
                            className="academic-action-button"
                            title="Edit offering"
                            aria-label="Edit offering"
                            onClick={() => handleOpenOfferingModal(offering)}
                          >
                            <FontAwesomeIcon icon={faPen} />
                          </button>

                          <button
                            type="button"
                            className="academic-action-button danger"
                            title="Delete offering"
                            aria-label="Delete offering"
                            disabled={deletingOfferingId === offering.offering_id}
                            onClick={() => handleDeleteOffering(offering)}
                          >
                            <FontAwesomeIcon
                              icon={
                                deletingOfferingId === offering.offering_id
                                  ? faSpinner
                                  : faTrash
                              }
                              spin={deletingOfferingId === offering.offering_id}
                            />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="academic-pagination">
                <div className="academic-pagination-info">
                  Showing{" "}
                  {offerings.length === 0
                    ? 0
                    : (safeOfferingPage - 1) * OFFERINGS_PAGE_SIZE + 1}
                  {"–"}
                  {Math.min(
                    safeOfferingPage * OFFERINGS_PAGE_SIZE,
                    offerings.length
                  )}
                  {" of "}
                  {offerings.length} offerings
                </div>

                <div className="academic-pagination-controls">
                  <button
                    type="button"
                    className="academic-page-button"
                    disabled={safeOfferingPage === 1}
                    onClick={() =>
                      setOfferingPage((page) => Math.max(1, page - 1))
                    }
                  >
                    Previous
                  </button>

                  {getPaginationItems(safeOfferingPage, totalOfferingPages).map((item, index) =>
                    item === "..." ? (
                      <span key={`ellipsis-${index}`} className="academic-page-ellipsis">
                        ...
                      </span>
                    ) : (
                      <button
                        type="button"
                        key={item}
                        className={`academic-page-button ${
                          safeOfferingPage === item ? "active" : ""
                        }`}
                        aria-current={
                          safeOfferingPage === item ? "page" : undefined
                        }
                        onClick={() => setOfferingPage(item)}
                      >
                        {item}
                      </button>
                    )
                  )}

                  <button
                    type="button"
                    className="academic-page-button"
                    disabled={safeOfferingPage === totalOfferingPages}
                    onClick={() =>
                      setOfferingPage((page) =>
                        Math.min(totalOfferingPages, page + 1)
                      )
                    }
                  >
                    Next
                  </button>
                </div>
              </div>
            </div>
          )}

          {renderNotice("Course offering updated", offeringActionMessage)}
          {renderNotice("Course offering action failed", offeringActionError, true)}
        </div>
      )}

      {/* ENROLLMENTS */}
      {activeTab === "enrollments" && (
        <div className="academic-table-card">
          <div className="enrollments-header-actions">
            <button
              type="button"
              className="enrollments-refresh-btn"
              onClick={handleRefreshEnrollments}
              disabled={enrollmentsLoading || groupPreviewLoading}
            >
              <span
                className={
                  enrollmentsLoading ? "refresh-icon spinning" : "refresh-icon"
                }
              >
                {"↻"}
              </span>
              {enrollmentsLoading ? "Refreshing..." : "Refresh"}
            </button>
          </div>

          
          {showGroupEnrollment && (
            <div className="group-enrollment-panel">
              <div className="academic-section-header">
                <div className="academic-section-heading">
                  <h3>Enroll a Student Group</h3>
                  <p>
                    Select a department, cohort, semester, and section to review
                    matching course offerings. This screen is preview-only until
                    the backend enrollment-write endpoint is verified.
                  </p>
                </div>

                <button
                  type="button"
                  className="academic-secondary-button"
                  onClick={() => {
                    setShowGroupEnrollment(false);
                    setGroupPreview(null);
                    setEnrollmentActionError("");
                    setEnrollmentActionMessage("");
                  }}
                >
                  Close
                </button>
              </div>

              <div className="academic-form-grid">
                <div className="academic-form-field">
                  <label htmlFor="group-department">Department *</label>
                  <select
                    id="group-department"
                    value={groupEnrollment.department_id}
                    onChange={(event) =>
                      handleGroupEnrollmentChange("department_id", event.target.value)
                    }
                    disabled={groupPreviewLoading}
                  >
                    <option value="">Select department</option>
                    {departments.map((department) => (
                      <option
                        key={department.department_id}
                        value={department.department_id}
                      >
                        {department.department_code || department.department_id}
                        {" — "}
                        {department.department_name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="academic-form-field">
                  <label htmlFor="group-cohort">Batch Year / Cohort</label>
                  <select
                    id="group-cohort"
                    value={groupEnrollment.academic_year}
                    onChange={(event) =>
                      handleGroupEnrollmentChange("academic_year", event.target.value)
                    }
                    disabled={groupPreviewLoading || studentsLoading}
                  >
                    <option value="">Select Batch (e.g. 2024-2028)</option>
                    {[...new Set(
                      students
                        .filter(
                          (student) =>
                            String(student.department_id) ===
                            String(groupEnrollment.department_id)
                        )
                        .map((student) => student.batch_year || student.batch_name || student.academic_year)
                        .filter(Boolean)
                    )]
                      .sort()
                      .map((cohort) => (
                        <option key={cohort} value={cohort}>
                          {cohort}
                        </option>
                      ))}
                  </select>
                </div>

                <div className="academic-form-field">
                  <label htmlFor="group-semester">Semester </label>
                  <select
                    id="group-semester"
                    value={groupEnrollment.semester}
                    onChange={(event) =>
                      handleGroupEnrollmentChange("semester", event.target.value)
                    }
                    disabled={groupPreviewLoading || studentsLoading}
                  >
                    <option value="">Select semester</option>
                    {[...new Set(
                      students
                        .filter(
                          (student) => {
                            if (
                              String(student.department_id) !==
                              String(groupEnrollment.department_id)
                            )
                              return false;
                            const studentCohort =
                              student.batch_year ||
                              student.batch_name ||
                              student.academic_year;
                            return (
                              String(studentCohort) ===
                              String(groupEnrollment.academic_year)
                            );
                          }
                        )
                        .map((student) => student.semester)
                        .filter((semester) => semester != null)
                    )]
                      .sort((a, b) => Number(a) - Number(b))
                      .map((semester) => (
                        <option key={semester} value={semester}>
                          Semester {semester}
                        </option>
                      ))}
                  </select>
                </div>

                <div className="academic-form-field">
                  <label htmlFor="group-section">Section </label>
                  <select
                    id="group-section"
                    value={groupEnrollment.section}
                    onChange={(event) =>
                      handleGroupEnrollmentChange("section", event.target.value)
                    }
                    disabled={groupPreviewLoading || studentsLoading}
                  >
                    <option value="">Select section</option>
                    {[...new Set(
                      students
                        .filter(
                          (student) => {
                            if (
                              String(student.department_id) !==
                              String(groupEnrollment.department_id)
                            )
                              return false;
                            const studentCohort =
                              student.batch_year ||
                              student.batch_name ||
                              student.academic_year;
                            return (
                              String(studentCohort) ===
                                String(groupEnrollment.academic_year) &&
                              String(student.semester) ===
                                String(groupEnrollment.semester)
                            );
                          }
                        )
                        .map((student) => student.section)
                        .filter(Boolean)
                    )]
                      .sort()
                      .map((section) => (
                        <option key={section} value={section}>
                          Section {section}
                        </option>
                      ))}
                  </select>
                </div>
              </div>

              {renderNotice("Preview failed", enrollmentActionError, true)}
              {renderNotice("Enrollment status", enrollmentActionMessage)}

              <div className="enrollments-header-actions">
                <button
                  type="button"
                  className="academic-primary-button"
                  onClick={handlePreviewGroupEnrollment}
                  disabled={
                    groupPreviewLoading ||
                    studentsLoading ||
                    !groupEnrollment.department_id ||
                    !groupEnrollment.academic_year ||
                    !groupEnrollment.semester ||
                    !groupEnrollment.section
                  }
                >
                  <FontAwesomeIcon
                    icon={groupPreviewLoading ? faSpinner : faCheck}
                    spin={groupPreviewLoading}
                  />
                  {groupPreviewLoading ? "Loading Preview..." : "Preview Courses"}
                </button>
              </div>

              {groupPreview && (
                <div className="group-enrollment-preview">
                  <div className="group-preview-heading">
                    <div>
                      <span className="group-preview-eyebrow">GROUP SUMMARY</span>
                      <h3>Enrollment Preview</h3>
                      <p className="group-preview-context">
                        Batch {groupEnrollment.academic_year}
                        {" · Semester "}
                        {groupEnrollment.semester}
                        {" · Section "}
                        {groupEnrollment.section}
                      </p>
                    </div>
                    <span className="group-preview-ready">
                      <FontAwesomeIcon icon={faCheck} /> Preview ready
                    </span>
                  </div>

                  <div className="group-preview-stats">
                    <div className="group-preview-stat">
                      <span className="group-preview-stat-icon group-preview-stat-blue">
                        <FontAwesomeIcon icon={faGraduationCap} />
                      </span>
                      <div>
                        <strong>{groupPreview.eligible_students ?? 0}</strong>
                        <span>Eligible students</span>
                      </div>
                    </div>
                    <div className="group-preview-stat">
                      <span className="group-preview-stat-icon group-preview-stat-violet">
                        <FontAwesomeIcon icon={faBookOpen} />
                      </span>
                      <div>
                        <strong>
                          {(groupPreview.courses || []).length ||
                            (groupPreview.offerings || []).length}
                        </strong>
                        <span>Active courses</span>
                      </div>
                    </div>
                    <div className="group-preview-stat">
                      <span className="group-preview-stat-icon group-preview-stat-green">
                        <FontAwesomeIcon icon={faCheck} />
                      </span>
                      <div>
                        <strong>
                          {(groupPreview.courses || []).filter(
                            (course) => course.has_offering ?? Boolean(course.offering_id)
                          ).length || (groupPreview.offerings || []).length}
                        </strong>
                        <span>Existing offerings</span>
                      </div>
                    </div>
                  </div>

                  <div className="group-preview-course-heading">
                    <div>
                      <h4>Course offerings</h4>
                      <p>Existing offerings are reused; missing ones will be created automatically.</p>
                    </div>
                    <span className="group-preview-course-count">
                      {(groupPreview.courses || []).length ||
                        (groupPreview.offerings || []).length} courses
                    </span>
                  </div>

                  {(groupPreview.courses || []).length > 0 ? (
                    <div className="group-enrollment-course-list">
                      {groupPreview.courses.map((course) => {
                        const hasOffering = course.has_offering ?? Boolean(course.offering_id);
                        const facultyAssigned = course.faculty_assigned ?? false;

                        return (
                          <article
                            key={course.course_id}
                            className={`group-enrollment-course-option ${
                              hasOffering ? "is-existing" : "is-new"
                            }`}
                          >
                            <span className="group-course-icon">
                              <FontAwesomeIcon icon={faBookOpen} />
                            </span>
                            <div className="group-course-content">
                              <strong className="group-course-title">
                                <span>{course.course_code}</span>
                                <span className="group-course-dash"> — </span>
                                {course.course_name}
                              </strong>
                              <p className="group-course-description">
                                {hasOffering
                                  ? `Course offering #${course.offering_id} will be reused.`
                                  : "A new course offering will be created automatically."}
                              </p>
                              <div className="group-course-badges">
                                <span className={`group-course-badge ${hasOffering ? "badge-existing" : "badge-new"}`}>
                                  {hasOffering ? "Existing offering" : "New offering"}
                                </span>
                                {hasOffering ? (
                                  <span className={`group-course-badge ${facultyAssigned ? "badge-faculty" : "badge-pending"}`}>
                                    {facultyAssigned ? "Faculty assigned" : "Faculty assignment pending"}
                                  </span>
                                ) : (
                                  <span className="group-course-badge badge-pending">
                                    No Faculty Assign
                                  </span>
                                )}
                              </div>
                            </div>
                          </article>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="group-preview-empty">
                      <FontAwesomeIcon icon={faCircleExclamation} />
                      <p>No course details were returned. Refresh the preview or check the backend response.</p>
                    </div>
                  )}

                  <div className="group-preview-note">
                    <FontAwesomeIcon icon={faCircleExclamation} />
                    <p>
                      <strong>Preview only.</strong> No enrollment records have been created yet.
                      Faculty assignments on existing offerings will be preserved.
                    </p>
                  </div>

                  <div className="group-preview-footer">
                    <span>Review the group details before confirming enrollment.</span>
                    <button
                      type="button"
                      className="academic-primary-button group-preview-enroll-button"
                      onClick={handleBulkEnrollGroup}
                      disabled={
                        groupPreviewLoading ||
                        (groupPreview.eligible_students ?? 0) === 0 ||
                        (
                          (groupPreview.courses || []).length === 0 &&
                          (groupPreview.offerings || []).length === 0
                        )
                      }
                    >
                      <FontAwesomeIcon
                        icon={groupPreviewLoading ? faSpinner : faCheck}
                        spin={groupPreviewLoading}
                      />
                      {groupPreviewLoading
                        ? "Processing..."
                        : "Enroll All Eligible Students"}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {enrollmentsLoading ? (
            <div className="academic-empty-state">
              <FontAwesomeIcon icon={faSpinner} spin />
              <h2>Loading enrollments</h2>
            </div>
          ) : enrollmentsError ? (
            <div className="academic-empty-state">
              <FontAwesomeIcon icon={faCircleExclamation} />
              <h2>Unable to load enrollments</h2>
              <p>{enrollmentsError}</p>
            </div>
          ) : (
            <>
              <div className="academic-table-wrapper">
                <table className="academic-table">
                  <thead>
                    <tr>
                      <th>Enrollment ID</th>
                      <th>Student ID</th>
                      <th>Offering ID</th>
                      <th>Status</th>
                      <th>Enrolled At</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedEnrollments.length > 0 ? (
                      paginatedEnrollments.map((enrollment) => (
                        <tr key={enrollment.enrollment_id}>
                          <td>{enrollment.enrollment_id}</td>
                          <td>{enrollment.student_id}</td>
                          <td>{enrollment.offering_id}</td>
                          <td>
                            <span
                              className={`academic-status academic-status-${(
                                enrollment.status || "unknown"
                              ).toLowerCase()}`}
                            >
                              {enrollment.status || "N/A"}
                            </span>
                          </td>
                          <td>{formatDate(enrollment.enrolled_at)}</td>
                          <td className="enrollment-actions">
                            <button
                              type="button"
                              className="academic-action-button enrollment-delete-button"
                              title="Remove enrollment"
                              aria-label={`Remove enrollment ${enrollment.enrollment_id}`}
                              disabled={
                                deletingEnrollmentId === enrollment.enrollment_id
                              }
                              onClick={() =>
                                handleDeleteEnrollment(enrollment.enrollment_id)
                              }
                            >
                              <FontAwesomeIcon
                                icon={
                                  deletingEnrollmentId === enrollment.enrollment_id
                                    ? faSpinner
                                    : faTrash
                                }
                                spin={
                                  deletingEnrollmentId === enrollment.enrollment_id
                                }
                              />
                            </button>
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={6} className="academic-no-records">
                          No course enrollments found.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {enrollments.length > 0 && (
                <div className="academic-pagination">
                  <div className="academic-pagination-info">
                    Showing{" "}
                    {(safeEnrollmentPage - 1) * ENROLLMENTS_PAGE_SIZE + 1}
                    {"–"}
                    {Math.min(
                      safeEnrollmentPage * ENROLLMENTS_PAGE_SIZE,
                      enrollments.length
                    )}{" "}
                    of {enrollments.length} enrollments
                  </div>

                  <div className="academic-pagination-controls">
                    <button
                      type="button"
                      className="academic-page-button"
                      disabled={safeEnrollmentPage === 1}
                      onClick={() =>
                        setEnrollmentPage((page) => Math.max(1, page - 1))
                      }
                    >
                      Previous
                    </button>

                    {getPaginationItems(safeEnrollmentPage, totalEnrollmentPages).map((item, index) =>
                      item === "..." ? (
                        <span key={`ellipsis-${index}`} className="academic-page-ellipsis">
                          ...
                        </span>
                      ) : (
                        <button
                          type="button"
                          key={item}
                          className={`academic-page-button ${
                            safeEnrollmentPage === item ? "active" : ""
                          }`}
                          aria-current={
                            safeEnrollmentPage === item ? "page" : undefined
                          }
                          onClick={() => setEnrollmentPage(item)}
                        >
                          {item}
                        </button>
                      )
                    )}

                    <button
                      type="button"
                      className="academic-page-button"
                      disabled={safeEnrollmentPage === totalEnrollmentPages}
                      onClick={() =>
                        setEnrollmentPage((page) =>
                          Math.min(totalEnrollmentPages, page + 1)
                        )
                      }
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </>
          )}

          {renderNotice("Enrollment created", enrollmentActionMessage)}
          {renderNotice(
            "Enrollment action failed",
            enrollmentActionError,
            true
          )}
        </div>
      )}

      {/* ASSIGNMENTS */}
      {activeTab === "assignments" && (
        <div className="academic-table-card academic-future-tab">
          <div className="academic-empty-state">
            <div className="academic-empty-icon" aria-hidden="true">
              <FontAwesomeIcon icon={faChalkboardTeacher} />
            </div>
            <h2>Assignments are not connected yet</h2>
            <p>
              The Add Assignment button is visible, but saving and listing
              assignments require a verified backend endpoint and request format.
            </p>
          </div>
          {renderNotice("Assignment feature unavailable", assignmentNotice, true)}
        </div>
      )}

      {/* COURSE MODAL */}
      {showCourseModal && (
        <div
          className="academic-modal-overlay"
          role="presentation"
          onMouseDown={(event) => {
            if (
              event.target === event.currentTarget &&
              !savingCourse
            ) {
              setShowCourseModal(false);
            }
          }}
        >
          <div
            className="academic-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="course-modal-title"
          >
            <div className="academic-modal-header">
              <div>
                <span className="academic-eyebrow">Academic Management</span>
                <h2 id="course-modal-title">
                  {editingCourseId ? "Edit Course" : "Add Course"}
                </h2>
                <p>Enter the course information below.</p>
              </div>
              <button
                type="button"
                className="academic-modal-close"
                onClick={() => {
                  setShowCourseModal(false);
                  setEditingCourseId(null);
                  setCourseActionError("");
                }}
                disabled={savingCourse}
                aria-label="Close course dialog"
              >
                <FontAwesomeIcon icon={faXmark} />
              </button>
            </div>

            <form onSubmit={handleSaveCourse}>
              {renderNotice(
                editingCourseId ? "Unable to update course" : "Unable to create course",
                courseActionError,
                true
              )}
              {renderNotice(
                editingCourseId ? "Course updated" : "Course created",
                courseActionMessage
              )}

              <div className="academic-form-section">
                <h3>Course Information</h3>

                <div className="academic-form-grid">
                  <div className="academic-form-field">
                    <label htmlFor="course-code">Course Code *</label>
                    <input
                      id="course-code"
                      name="course_code"
                      value={courseForm.course_code}
                      onChange={(event) =>
                        setCourseForm((current) => ({
                          ...current,
                          course_code: event.target.value,
                        }))
                      }
                      maxLength={30}
                      required
                      disabled={savingCourse}
                    />
                  </div>

                  <div className="academic-form-field">
                    <label htmlFor="course-name">Course Name *</label>
                    <input
                      id="course-name"
                      name="course_name"
                      value={courseForm.course_name}
                      onChange={(event) =>
                        setCourseForm((current) => ({
                          ...current,
                          course_name: event.target.value,
                        }))
                      }
                      maxLength={150}
                      required
                      disabled={savingCourse}
                    />
                  </div>

                  <div className="academic-form-field">
                    <label htmlFor="course-department">Department *</label>
                    <select
                      id="course-department"
                      name="department_id"
                      value={courseForm.department_id}
                      onChange={(event) =>
                        setCourseForm((current) => ({
                          ...current,
                          department_id: event.target.value,
                        }))
                      }
                      required
                      disabled={savingCourse || departmentsLoading}
                    >
                      <option value="">
                        {departmentsLoading
                          ? "Loading departments..."
                          : "Select department"}
                      </option>
                      {departments.map((department) => (
                        <option
                          key={department.department_id}
                          value={department.department_id}
                        >
                          {department.department_code} — {department.department_name}
                        </option>
                      ))}
                    </select>
                    {departmentError && (
                      <div className="academic-form-error" role="alert">
                        {departmentError}
                        <button
                          type="button"
                          className="academic-secondary-button"
                          onClick={async () => {
                            setDepartmentError("");
                            setDepartmentsLoading(true);
                            try {
                              const result = await getAdminDepartments();
                              if (
                                !result?.success ||
                                !Array.isArray(result.data)
                              ) {
                                throw new Error(
                                  result?.message ||
                                    "Unable to load departments."
                                );
                              }
                              setDepartments(result.data);
                            } catch (error) {
                              setDepartmentError(
                                getErrorMessage(
                                  error,
                                  "Unable to load departments."
                                )
                              );
                            } finally {
                              setDepartmentsLoading(false);
                            }
                          }}
                          disabled={departmentsLoading}
                        >
                          <FontAwesomeIcon
                            icon={departmentsLoading ? faSpinner : faRotate}
                            spin={departmentsLoading}
                          />
                          Retry
                        </button>
                      </div>
                    )}
                  </div>

                  <div className="academic-form-field">
                    <label htmlFor="course-semester">Semester *</label>
                    <input
                      id="course-semester"
                      name="semester"
                      type="number"
                      min="1"
                      step="1"
                      value={courseForm.semester}
                      onChange={(event) =>
                        setCourseForm((current) => ({
                          ...current,
                          semester: event.target.value,
                        }))
                      }
                      required
                      disabled={savingCourse}
                    />
                  </div>

                  <div className="academic-form-field">
                    <label htmlFor="course-credits">Credits *</label>
                    <input
                      id="course-credits"
                      name="credits"
                      type="number"
                      min="1"
                      step="1"
                      value={courseForm.credits}
                      onChange={(event) =>
                        setCourseForm((current) => ({
                          ...current,
                          credits: event.target.value,
                        }))
                      }
                      required
                      disabled={savingCourse}
                    />
                  </div>
                  <div className="academic-form-field">
                    <label htmlFor="course-batch">Batch *</label>
                    <select
                      id="course-batch"
                      name="batch"
                      value={courseForm.batch}
                      onChange={(event) => {
                        const newBatch = event.target.value;
                        const semNum = Number(courseForm.semester) || 1;
                        const autoAY = newBatch ? toCanonicalAcademicYear(newBatch, semNum) : "";
                        setCourseForm((current) => ({
                          ...current,
                          batch: newBatch,
                          academic_year: current.academic_year || autoAY,
                        }));
                      }}
                      required
                      disabled={savingCourse || batchesLoading}
                    >
                      <option value="">{batchesLoading ? "Loading batches..." : "Select batch"}</option>
                      {batchOptions.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                      {courseForm.batch &&
                        !batchOptions.some((opt) => opt.value === courseForm.batch) && (
                          <option value={courseForm.batch}>
                            {courseForm.batch}
                          </option>
                        )}
                    </select>
                    <small style={{ fontSize: "11px", color: "#6b7280" }}>
                      Admission cohort (e.g. 2024, 2025, 2026)
                    </small>
                  </div>

                  <div className="academic-form-field">
                    <label htmlFor="course-academic-year">Academic Year *</label>
                    <select
                      id="course-academic-year"
                      name="academic_year"
                      value={courseForm.academic_year}
                      onChange={(event) =>
                        setCourseForm((current) => ({
                          ...current,
                          academic_year: event.target.value,
                        }))
                      }
                      required
                      disabled={savingCourse}
                    >
                      <option value="">Select academic year</option>
                      {academicYearOptions.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                      {courseForm.academic_year &&
                        !academicYearOptions.some((opt) => opt.value === courseForm.academic_year) && (
                          <option value={courseForm.academic_year}>
                            {formatAcademicYear(courseForm.academic_year)}
                          </option>
                        )}
                    </select>
                    <small style={{ fontSize: "11px", color: "#6b7280" }}>
                      1-year teaching session (e.g. 2025–2026)
                    </small>
                  </div>
                </div>
              </div>

              <div className="academic-modal-footer">
                <button
                  type="button"
                  className="academic-secondary-button"
                  onClick={() => setShowCourseModal(false)}
                  disabled={savingCourse}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="academic-primary-button"
                  disabled={
                    savingCourse ||
                    deletingCourseId !== null ||
                    departmentsLoading ||
                    departments.length === 0
                  }
                >
                  <FontAwesomeIcon
                    icon={savingCourse ? faSpinner : faCheck}
                    spin={savingCourse}
                  />
                  {savingCourse
                    ? "Saving..."
                    : editingCourseId !== null
                      ? "Update Course"
                      : "Create Course"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* COURSE OFFERING MODAL */}
      {showOfferingModal && (
        <div
          className="academic-modal-overlay"
          role="presentation"
          onMouseDown={(event) => {
            if (
              event.target === event.currentTarget &&
              !savingOffering
            ) {
              setShowOfferingModal(false);
            }
          }}
        >
          <div
            className="academic-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="offering-modal-title"
          >
            <div className="academic-modal-header">
              <div>
                <span className="academic-eyebrow">Academic Management</span>
                <h2 id="offering-modal-title">
                  {editingOfferingId !== null
                    ? "Edit Course Offering"
                    : "Add Course Offering"}
                </h2>
                <p>Enter the course, faculty, and semester details.</p>
              </div>
              <button
                type="button"
                className="academic-modal-close"
                onClick={() => setShowOfferingModal(false)}
                disabled={savingOffering}
                aria-label="Close offering dialog"
              >
                <FontAwesomeIcon icon={faXmark} />
              </button>
            </div>

            <form onSubmit={handleSaveOffering}>
              <div className="academic-form-section">
                <h3>Offering Information</h3>

                <div className="academic-form-grid">
                  <div className="academic-form-field">
                    <label htmlFor="offering-course">Course *</label>
                    <select
                      id="offering-course"
                      value={offeringForm.course_id}
                      onChange={(event) => {
                        const cid = event.target.value;
                        const selectedCourse = courses.find((c) => String(c.course_id) === String(cid));
                        setOfferingForm((current) => ({
                          ...current,
                          course_id: cid,
                          batch: current.batch || selectedCourse?.batch || "",
                        }));
                      }}
                      required
                      disabled={savingOffering || offeringDropdownLoading}
                    >
                      <option value="">
                        {offeringDropdownLoading ? "Loading courses..." : "Select course"}
                      </option>
                      {(Array.isArray(courses) ? courses : []).map((course) => (
                        <option
                          key={course.course_id}
                          value={course.course_id}
                        >
                          {course.course_code} — {course.course_name}
                        </option>
                      ))}
                    </select>
                  </div>

                  {editingOfferingId === null && (
                    <div className="academic-form-field">
                      <label htmlFor="offering-faculty">Faculty *</label>
                      <select
                        id="offering-faculty"
                        value={offeringForm.faculty_id}
                        onChange={(event) =>
                          setOfferingForm((current) => ({
                            ...current,
                            faculty_id: event.target.value,
                          }))
                        }
                        required
                        disabled={savingOffering || offeringDropdownLoading}
                      >
                        <option value="">
                          {offeringDropdownLoading ? "Loading faculty..." : "Select faculty"}
                        </option>
                        {(Array.isArray(faculty) ? faculty : []).map((member) => (
                          <option
                            key={member.faculty_id}
                            value={member.faculty_id}
                          >
                            {member.name ||
                              member.employee_id ||
                              `Faculty #${member.faculty_id}`}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  <div className="academic-form-field">
                    <label htmlFor="offering-batch">Batch</label>
                    <select
                      id="offering-batch"
                      value={offeringForm.batch}
                      onChange={(event) =>
                        setOfferingForm((current) => ({
                          ...current,
                          batch: event.target.value,
                        }))
                      }
                      disabled={savingOffering || batchesLoading}
                    >
                      <option value="">{batchesLoading ? "Loading batches..." : "Select batch"}</option>
                      {batchOptions.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                      {offeringForm.batch &&
                        !batchOptions.some((opt) => opt.value === offeringForm.batch) && (
                          <option value={offeringForm.batch}>
                            {offeringForm.batch}
                          </option>
                        )}
                    </select>
                    <small style={{ fontSize: "11px", color: "#6b7280" }}>
                      Admission cohort (e.g. 2024, 2025, 2026)
                    </small>
                  </div>

                  <div className="academic-form-field">
                    <label htmlFor="offering-year">Academic Year *</label>
                    <select
                      id="offering-year"
                      value={offeringForm.academic_year}
                      onChange={(event) =>
                        setOfferingForm((current) => ({
                          ...current,
                          academic_year: event.target.value,
                        }))
                      }
                      required
                      disabled={savingOffering}
                    >
                      <option value="">Select academic year</option>
                      {academicYearOptions.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                      {offeringForm.academic_year &&
                        !academicYearOptions.some((opt) => opt.value === offeringForm.academic_year) && (
                          <option value={offeringForm.academic_year}>
                            {formatAcademicYear(offeringForm.academic_year)}
                          </option>
                        )}
                    </select>
                    <small style={{ fontSize: "11px", color: "#6b7280" }}>
                      1-year academic session (e.g. 2025-2026), not student batch range
                    </small>
                  </div>

                  <div className="academic-form-field">
                    <label htmlFor="offering-semester">Semester *</label>
                    <input
                      id="offering-semester"
                      type="number"
                      min="1"
                      step="1"
                      value={offeringForm.semester}
                      onChange={(event) =>
                        setOfferingForm((current) => ({
                          ...current,
                          semester: event.target.value,
                        }))
                      }
                      required
                      disabled={savingOffering}
                    />
                  </div>

                  <div className="academic-form-field">
                    <label htmlFor="offering-section">Section *</label>
                    <input
                      id="offering-section"
                      value={offeringForm.section}
                      onChange={(event) =>
                        setOfferingForm((current) => ({
                          ...current,
                          section: event.target.value,
                        }))
                      }
                      placeholder="e.g. A"
                      required
                      disabled={savingOffering}
                    />
                  </div>

                  {offeringDropdownError && (
                    <div
                      className="academic-form-error"
                      role="alert"
                      style={{
                        gridColumn: "1 / -1",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        padding: "8px 12px",
                        backgroundColor: "#fef2f2",
                        border: "1px solid #fee2e2",
                        borderRadius: "6px",
                        color: "#991b1b",
                        fontSize: "13px",
                      }}
                    >
                      <span>{offeringDropdownError}</span>
                      <button
                        type="button"
                        className="academic-secondary-button"
                        onClick={loadOfferingDropdowns}
                        disabled={offeringDropdownLoading}
                        style={{ padding: "4px 8px", fontSize: "12px" }}
                      >
                        <FontAwesomeIcon
                          icon={offeringDropdownLoading ? faSpinner : faRotate}
                          spin={offeringDropdownLoading}
                        />{" "}
                        Retry
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {renderNotice("Unable to save offering", offeringActionError, true)}

              <div className="academic-modal-footer">
                <button
                  type="button"
                  className="academic-secondary-button"
                  onClick={() => setShowOfferingModal(false)}
                  disabled={savingOffering}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="academic-primary-button"
                  disabled={
                    savingOffering ||
                    offeringDropdownLoading ||
                    courses.length === 0 ||
                    (!editingOfferingId && faculty.length === 0)
                  }
                >
                  <FontAwesomeIcon
                    icon={savingOffering ? faSpinner : faCheck}
                    spin={savingOffering}
                  />
                  {savingOffering
                    ? "Saving..."
                    : editingOfferingId !== null
                      ? "Save Changes"
                      : "Create Offering"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      </section>
    </ErrorBoundary>
  );
}

export default AcademicManagement;
