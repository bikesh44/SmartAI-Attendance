import { useEffect, useMemo, useState } from "react";

import { faXmark } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

import "./Students.css";

import {
  getFacultyCourses,
  getFacultyStudents,
} from "../../services/facultyService";
import { formatAcademicYear } from "../../utils/academicYearUtils";

const EMPTY_METRICS = {
  activeStudents: null,
  attendanceRate: null,
};

const formatMetric = (value) => {
  if (value === null || value === undefined) {
    return "N/A";
  }

  return value;
};

const getInitials = (name = "") => {
  const words = name.trim().split(/\s+/).filter(Boolean);

  if (!words.length) {
    return "S";
  }

  return words
    .slice(0, 2)
    .map((word) => word[0].toUpperCase())
    .join("");
};

const normalizeStudent = (student) => ({
  studentId: String(student.student_id ?? ""),
  userId: student.user_id ?? null,
  fullName: student.name ?? "",
  email: student.email ?? "",
  enrollmentNo: student.enrollment_no ?? "",
  semester:
    student.semester !== null && student.semester !== undefined
      ? String(student.semester)
      : "",
  section: student.section ?? "",
  academicYear: student.academic_year ?? "",
  batchYear: student.batch_year ?? student.batch_name ?? "",
  departmentId: student.department?.department_id ?? null,
  department:
    student.department?.department_name ??
    student.department?.department_code ??
    "",
  departmentCode: student.department?.department_code ?? "",
});

function Students() {
  const [students, setStudents] = useState([]);
  const [courseCount, setCourseCount] = useState(null);

  const [loading, setLoading] = useState(true);
  const [coursesLoading, setCoursesLoading] = useState(true);

  const [error, setError] = useState("");
  const [coursesError, setCoursesError] = useState("");

  const [searchTerm, setSearchTerm] = useState("");
  const [selectedClass, setSelectedClass] = useState("All Classes");
  const [department, setDepartment] = useState("All");
  const [semester, setSemester] = useState("All");
  const [selectedStudent, setSelectedStudent] = useState(null);

  useEffect(() => {
    let isMounted = true;

    const loadStudents = async () => {
      setLoading(true);
      setError("");

      try {
        const result = await getFacultyStudents();

        if (!isMounted) {
          return;
        }

        if (!result?.success) {
          throw new Error(
            result?.message || "Unable to load students."
          );
        }

        const studentData = Array.isArray(result.data)
          ? result.data.map(normalizeStudent)
          : [];

        setStudents(studentData);
      } catch (requestError) {
        if (!isMounted) {
          return;
        }

        setStudents([]);

        setError(
          requestError?.response?.data?.message ||
            requestError?.message ||
            "Unable to load students."
        );
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    loadStudents();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    let isMounted = true;

    const loadCourses = async () => {
      setCoursesLoading(true);
      setCoursesError("");

      try {
        const result = await getFacultyCourses();

        if (!isMounted) {
          return;
        }

        if (!result?.success) {
          throw new Error(
            result?.message || "Unable to load course offerings."
          );
        }

        const courses = Array.isArray(result.data)
          ? result.data
          : [];

        setCourseCount(courses.length);
      } catch (requestError) {
        if (!isMounted) {
          return;
        }

        setCourseCount(null);

        setCoursesError(
          requestError?.response?.data?.message ||
            requestError?.message ||
            "Unable to load course offerings."
        );
      } finally {
        if (isMounted) {
          setCoursesLoading(false);
        }
      }
    };

    loadCourses();

    return () => {
      isMounted = false;
    };
  }, []);

  const departmentOptions = useMemo(() => {
    const values = students
      .map((student) => student.department)
      .filter(Boolean);

    return [
      "All",
      ...Array.from(new Set(values)).sort(),
    ];
  }, [students]);

  const semesterOptions = useMemo(() => {
    const values = students
      .map((student) => student.semester)
      .filter(Boolean);

    return [
      "All",
      ...Array.from(new Set(values)).sort(),
    ];
  }, [students]);

  const classOptions = useMemo(() => {
    const values = students
      .map((student) => student.section)
      .filter(Boolean);

    return [
      "All Classes",
      ...Array.from(new Set(values)).sort(),
    ];
  }, [students]);

  const filteredStudents = useMemo(() => {
    const normalizedSearch = searchTerm.trim().toLowerCase();

    return students.filter((student) => {
      const searchableValues = [
        student.studentId,
        student.enrollmentNo,
        student.fullName,
        student.email,
      ].map((value) => value.toLowerCase());

      const matchesSearch =
        !normalizedSearch ||
        searchableValues.some((value) =>
          value.includes(normalizedSearch)
        );

      const matchesClass =
        selectedClass === "All Classes" ||
        student.section === selectedClass;

      const matchesDepartment =
        department === "All" ||
        student.department === department;

      const matchesSemester =
        semester === "All" ||
        student.semester === semester;

      return (
        matchesSearch &&
        matchesClass &&
        matchesDepartment &&
        matchesSemester
      );
    });
  }, [
    students,
    searchTerm,
    selectedClass,
    department,
    semester,
  ]);

  const clearFilters = () => {
    setSearchTerm("");
    setSelectedClass("All Classes");
    setDepartment("All");
    setSemester("All");
  };

  const hasFilters =
    Boolean(searchTerm) ||
    selectedClass !== "All Classes" ||
    department !== "All" ||
    semester !== "All";

  const handleViewStudent = (student) => {
    setSelectedStudent(student);
  };

  const closeStudentModal = () => {
    setSelectedStudent(null);
  };

  const metrics = [
    {
      label: "Total Students",
      value: formatMetric(
        loading ? null : students.length
      ),
      icon: (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path
            d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />

          <circle
            cx="9"
            cy="7"
            r="4"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
          />

          <path
            d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </svg>
      ),
      tone: "blue",
    },
    {
      label: "Active Students",
      value: formatMetric(
        EMPTY_METRICS.activeStudents
      ),
      icon: (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle
            cx="12"
            cy="12"
            r="9"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
          />

          <path
            d="m8 12 2.5 2.5L16 9"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      ),
      tone: "green",
    },
    {
      label: "Course Offerings",
      value: formatMetric(
        coursesLoading ? null : courseCount
      ),
      icon: (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <rect
            x="3"
            y="4"
            width="18"
            height="16"
            rx="2"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
          />

          <path
            d="M8 4v4M16 4v4M3 10h18"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </svg>
      ),
      tone: "purple",
    },
    {
      label: "Attendance Rate",
      value: formatMetric(
        EMPTY_METRICS.attendanceRate
      ),
      icon: (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path
            d="M4 19V5M4 19h17"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />

          <path
            d="m7 15 4-4 3 2 5-6"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      ),
      tone: "orange",
    },
  ];

  return (
    <div className="faculty-students-page">
      <section className="students-page-header">
        <div>
          <span className="students-eyebrow">
            FACULTY PORTAL
          </span>

          <h1>Students</h1>

          <p>
            View students enrolled in your assigned classes
            and monitor their academic information.
          </p>
        </div>

        <button
          type="button"
          className="students-primary-button"
          disabled
          title="Attendance view is not connected to a student-specific attendance API yet"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path
              d="M4 5h16v14H4z"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinejoin="round"
            />

            <path
              d="M8 9h8M8 13h5"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
            />
          </svg>

          View Attendance
        </button>
      </section>

      <section className="students-metrics-grid">
        {metrics.map((metric) => (
          <article
            className="students-metric-card"
            key={metric.label}
          >
            <div
              className={`students-metric-icon ${metric.tone}`}
            >
              {metric.icon}
            </div>

            <div className="students-metric-content">
              <span>{metric.label}</span>
              <strong>{metric.value}</strong>
            </div>
          </article>
        ))}
      </section>

      <section className="students-filters-card">
        <div className="students-filter search-filter">
          <label htmlFor="student-search">
            Search Students
          </label>

          <div className="students-search-wrapper">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <circle
                cx="11"
                cy="11"
                r="7"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
              />

              <path
                d="m20 20-4-4"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
              />
            </svg>

            <input
              id="student-search"
              type="search"
              value={searchTerm}
              onChange={(event) =>
                setSearchTerm(event.target.value)
              }
              placeholder="Search by ID, enrollment no., name or email..."
            />
          </div>
        </div>

        <div className="students-filter">
          <label htmlFor="student-class">
            Section
          </label>

          <select
            id="student-class"
            value={selectedClass}
            onChange={(event) =>
              setSelectedClass(event.target.value)
            }
          >
            {classOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </div>

        <div className="students-filter">
          <label htmlFor="student-department">
            Department
          </label>

          <select
            id="student-department"
            value={department}
            onChange={(event) =>
              setDepartment(event.target.value)
            }
          >
            {departmentOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </div>

        <div className="students-filter">
          <label htmlFor="student-semester">
            Semester
          </label>

          <select
            id="student-semester"
            value={semester}
            onChange={(event) =>
              setSemester(event.target.value)
            }
          >
            {semesterOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </div>

        <button
          type="button"
          className="students-clear-button"
          onClick={clearFilters}
          disabled={!hasFilters}
        >
          <span aria-hidden="true">↻</span>
          Clear Filters
        </button>
      </section>

      <section className="students-list-section">
        <div className="students-section-heading">
          <div>
            <h2>Students</h2>

            <p>
              Students enrolled in your assigned classes.
            </p>
          </div>
        </div>

        <div className="students-table-card">
          {loading ? (
            <div className="students-empty-state">
              <div className="students-empty-icon">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <circle
                    cx="12"
                    cy="12"
                    r="9"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                  />

                  <path
                    d="M12 7v5l3 2"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                  />
                </svg>
              </div>

              <h3>Loading students...</h3>

              <p>
                Student information is being loaded from the
                faculty backend.
              </p>
            </div>
          ) : error ? (
            <div className="students-empty-state">
              <div className="students-empty-icon">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <circle
                    cx="12"
                    cy="12"
                    r="9"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                  />

                  <path
                    d="M12 7v6M12 16v1"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                  />
                </svg>
              </div>

              <h3>Unable to load students</h3>

              <p>{error}</p>
            </div>
          ) : students.length === 0 ? (
            <div className="students-empty-state">
              <div className="students-empty-icon">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                  />

                  <circle
                    cx="9"
                    cy="7"
                    r="4"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                  />

                  <path
                    d="M17 8h5M19.5 5.5v5"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                  />
                </svg>
              </div>

              <h3>No students available</h3>

              <p>
                No students are currently enrolled in your
                assigned course offerings.
              </p>
            </div>
          ) : filteredStudents.length === 0 ? (
            <div className="students-empty-state compact">
              <div className="students-empty-icon">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <circle
                    cx="11"
                    cy="11"
                    r="7"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                  />

                  <path
                    d="m20 20-4-4"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                  />
                </svg>
              </div>

              <h3>No matching students</h3>

              <p>
                Try changing your search or filters.
              </p>
            </div>
          ) : (
            <div className="students-table-wrapper">
              <table className="students-table">
                <thead>
                  <tr>
                    <th>Student</th>
                    <th>Enrollment No.</th>
                    <th>Section</th>
                    <th>Department</th>
                    <th>Semester</th>
                    <th>Academic Year</th>
                    <th>Actions</th>
                  </tr>
                </thead>

                <tbody>
                  {filteredStudents.map((student) => (
                    <tr key={student.studentId}>
                      <td>
                        <div className="student-identity">
                          <div className="student-avatar">
                            {getInitials(student.fullName)}
                          </div>

                          <div>
                            <strong>
                              {student.fullName || "N/A"}
                            </strong>

                            <span>
                              {student.email || "N/A"}
                            </span>
                          </div>
                        </div>
                      </td>

                      <td>
                        {student.enrollmentNo || "N/A"}
                      </td>

                      <td>
                        {student.section || "N/A"}
                      </td>

                      <td>
                        {student.department || "N/A"}
                      </td>

                      <td>
                        {student.semester || "N/A"}
                      </td>

                      <td>
                        {formatAcademicYear(
                          student.academicYear,
                          student.semester
                        )}
                      </td>

                      <td>
                        <button
                          type="button"
                          className="student-view-button"
                          onClick={() =>
                            handleViewStudent(student)
                          }
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="students-list-footer">
          <span>
            Showing {filteredStudents.length} of{" "}
            {students.length} students
          </span>

          <div className="students-pagination">
            <button type="button" disabled>
              ‹ Previous
            </button>

            <button
              type="button"
              className="active"
              disabled
            >
              1
            </button>

            <button type="button" disabled>
              Next ›
            </button>
          </div>
        </div>
      </section>

      <div className="students-integration-notice">
        <div className="students-notice-icon">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path
              d="M12 3v18M3 12h18"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
            />
          </svg>
        </div>

        <div>
          <strong>Student data connected</strong>

          <p>
            Student enrollment information is loaded from the
            Flask faculty student API. Attendance-specific
            statistics are not available from this endpoint yet.
          </p>
        </div>
      </div>

      {coursesError && (
        <div className="students-integration-notice">
          <div className="students-notice-icon">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path
                d="M12 3v18M3 12h18"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
              />
            </svg>
          </div>

          <div>
            <strong>Course data unavailable</strong>

            <p>{coursesError}</p>
          </div>
        </div>
      )}

      {selectedStudent && (
        <div
          className="students-modal-backdrop"
          role="presentation"
          onMouseDown={closeStudentModal}
        >
          <div
            className="students-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="faculty-student-profile-title"
            onMouseDown={(event) =>
              event.stopPropagation()
            }
          >
            <div className="students-modal-header">
              <div>
                <span className="students-eyebrow">
                  STUDENT PROFILE
                </span>

                <h2 id="faculty-student-profile-title">
                  Student Overview
                </h2>
              </div>

              <button
                type="button"
                className="students-modal-close"
                onClick={closeStudentModal}
                aria-label="Close student profile"
              >
                <FontAwesomeIcon icon={faXmark} />
              </button>
            </div>

            <div className="student-profile-summary">
              <div className="student-profile-avatar">
                {getInitials(selectedStudent.fullName)}
              </div>

              <div>
                <h3>
                  {selectedStudent.fullName || "N/A"}
                </h3>

                <p>
                  Student ID:{" "}
                  {selectedStudent.studentId || "N/A"}
                </p>

                <span>
                  {selectedStudent.email || "N/A"}
                </span>
              </div>
            </div>

            <div className="student-profile-grid">
              <div>
                <span>Enrollment No.</span>

                <strong>
                  {selectedStudent.enrollmentNo || "N/A"}
                </strong>
              </div>

              <div>
                <span>Department</span>

                <strong>
                  {selectedStudent.department || "N/A"}
                </strong>
              </div>

              <div>
                <span>Department Code</span>

                <strong>
                  {selectedStudent.departmentCode || "N/A"}
                </strong>
              </div>

              <div>
                <span>Semester</span>

                <strong>
                  {selectedStudent.semester || "N/A"}
                </strong>
              </div>

              <div>
                <span>Section</span>

                <strong>
                  {selectedStudent.section || "N/A"}
                </strong>
              </div>

              <div>
                <span>Academic Year</span>

                <strong>
                  {formatAcademicYear(
                    selectedStudent.academicYear,
                    selectedStudent.semester
                  )}
                </strong>
              </div>

              <div>
                <span>Batch Year</span>

                <strong>
                  {selectedStudent.batchYear || "N/A"}
                </strong>
              </div>
            </div>

            <div className="student-profile-section">
              <h3>Enrollment Information</h3>

              <div className="student-profile-empty">
                <strong>
                  Course-specific enrollment details
                </strong>

                <p>
                  This student is included in the faculty
                  student list. The current student API does
                  not return individual course enrollment
                  details.
                </p>
              </div>
            </div>

            <div className="student-profile-section">
              <h3>Attendance Summary</h3>

              <div className="student-attendance-summary">
                <div>
                  <span>Overall Attendance</span>
                  <strong>N/A</strong>
                </div>

                <div>
                  <span>Present</span>
                  <strong>N/A</strong>
                </div>

                <div>
                  <span>Absent</span>
                  <strong>N/A</strong>
                </div>

                <div>
                  <span>Late</span>
                  <strong>N/A</strong>
                </div>
              </div>

              <div className="student-profile-empty">
                Attendance summary is not returned by the
                current faculty student API.
              </div>
            </div>

            <div className="students-modal-footer">
              <button
                type="button"
                className="students-secondary-button"
                onClick={closeStudentModal}
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

export default Students;