import { useCallback, useEffect, useMemo, useState } from "react";
import {
  faBookOpen,
  faBuildingColumns,
  faCalendar,
  faCalendarDays,
  faChalkboardUser,
  faCircleExclamation,
  faEnvelope,
  faFloppyDisk,
  faIdCard,
  faMagnifyingGlass,
  faPhone,
  faPlus,
  faRotateRight,
  faSpinner,
  faUserTie,
  faUsers,
  faXmark,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  Clock,
  ExternalLink,
  Eye,
  MapPin,
  Pencil,
  Trash2,
} from "lucide-react";

import {
  createAdminFaculty,
  deleteAdminFaculty,
  getAdminFaculty,
  getAdminFacultyById,
  getAdminFacultyFilterOptions,
  getAdminFacultySummary,
  getUsers,
  updateAdminFaculty,
} from "../../services/adminService";

import "./Faculty.css";

function getInitials(name) {
  if (!name) return "FC";
  return name
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function formatFacultyId(member) {
  if (!member) return "FAC000";
  if (member.employee_id && /^FAC\d+$/i.test(member.employee_id)) {
    return member.employee_id.toUpperCase();
  }
  return `FAC${String(member.faculty_id || member.id || 0).padStart(3, "0")}`;
}

const PAGE_SIZE = 10;

function Faculty() {
  // Primary datasets
  const [faculty, setFaculty] = useState([]);
  const [summary, setSummary] = useState(null);
  const [filterOptions, setFilterOptions] = useState({
    departments: [],
    semesters: [],
    courses: [],
  });
  const [availableUsers, setAvailableUsers] = useState([]);

  // Load states
  const [loading, setLoading] = useState(true);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [error, setError] = useState("");

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState("");
  const [activeSearch, setActiveSearch] = useState("");
  const [selectedDept, setSelectedDept] = useState("All");
  const [selectedSemester, setSelectedSemester] = useState("All");
  const [selectedCourse, setSelectedCourse] = useState("All");

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);

  // Selected faculty for right-side details panel
  const [showDetails, setShowDetails] = useState(false);
  const [selectedFacultyId, setSelectedFacultyId] = useState(null);
  const [selectedFacultyDetail, setSelectedFacultyDetail] = useState(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [detailsTab, setDetailsTab] = useState("Profile"); // "Profile" | "Classes" | "Schedule"

  // Modals
  const [showFacultyModal, setShowFacultyModal] = useState(false);
  const [editingFaculty, setEditingFaculty] = useState(null);
  const [showFullProfileModal, setShowFullProfileModal] = useState(false);

  // Form state
  const [formLoading, setFormLoading] = useState(false);
  const [formError, setFormError] = useState("");
  const [facultyForm, setFacultyForm] = useState({
    user_id: "",
    employee_id: "",
    designation: "Assistant Professor",
    department_id: "",
    phone: "",
    date_of_joining: "",
    qualification: "",
    specialization: "",
    office_cabin: "",
  });

  // Fetch full details for a selected faculty member
  const loadFacultyDetails = useCallback(async (facultyId) => {
    if (!facultyId) return;
    setDetailsLoading(true);
    try {
      const res = await getAdminFacultyById(facultyId);
      if (res?.success && res.data) {
        setSelectedFacultyDetail(res.data);
      }
    } catch (err) {
      console.error("Failed to load faculty details:", err);
    } finally {
      setDetailsLoading(false);
    }
  }, []);

  // Load faculty dataset
  const fetchData = useCallback(
    async (isRefresh = false) => {
      if (isRefresh) {
        setLoading(true);
        setSummaryLoading(true);
      }
      setError("");

      try {
        const [facRes, sumRes, optRes, usersRes] = await Promise.allSettled([
          getAdminFaculty(),
          getAdminFacultySummary(),
          getAdminFacultyFilterOptions(),
          getUsers(),
        ]);

        if (facRes.status === "fulfilled" && facRes.value?.success) {
          const facList = Array.isArray(facRes.value.data) ? facRes.value.data : [];
          setFaculty(facList);
        } else {
          throw new Error(facRes.value?.message || "Failed to load faculty records.");
        }

        if (sumRes.status === "fulfilled" && sumRes.value?.success) {
          setSummary(sumRes.value.data);
        }

        if (optRes.status === "fulfilled" && optRes.value?.success) {
          setFilterOptions(optRes.value.data || { departments: [], semesters: [], courses: [] });
        }

        if (usersRes.status === "fulfilled" && usersRes.value?.success) {
          const users = Array.isArray(usersRes.value.data) ? usersRes.value.data : [];
          const existingUserIds = new Set(
            (facRes.value?.data || []).map((f) => String(f.user_id))
          );
          const freeFacultyUsers = users.filter(
            (u) =>
              String(u.role || "").toUpperCase() === "FACULTY" &&
              !existingUserIds.has(String(u.user_id))
          );
          setAvailableUsers(freeFacultyUsers);
        }
      } catch (err) {
        setError(err?.response?.data?.message || err?.message || "Failed to load faculty records.");
      } finally {
        setLoading(false);
        setSummaryLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    let active = true;
    const run = async () => {
      if (active) {
        await fetchData(false);
      }
    };
    run();
    return () => {
      active = false;
    };
  }, [fetchData]);

  // Open details panel when "View" is clicked
  const handleViewFaculty = (member) => {
    if (!member) return;
    setSelectedFacultyId(member.faculty_id);
    loadFacultyDetails(member.faculty_id);
    setShowDetails(true);
  };

  // Close details panel
  const handleCloseDetails = () => {
    setShowDetails(false);
    setSelectedFacultyId(null);
    setSelectedFacultyDetail(null);
  };

  // Filter logic
  const filteredFaculty = useMemo(() => {
    const q = activeSearch.trim().toLowerCase();

    return faculty.filter((member) => {
      // 1. Text search
      if (q) {
        const searchable = [
          member.name,
          member.email,
          member.employee_id,
          member.designation,
          formatFacultyId(member),
          member.department_name,
          member.department_code,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();

        if (!searchable.includes(q)) return false;
      }

      // 2. Department filter
      if (selectedDept !== "All") {
        const matchesDept =
          String(member.department_name || "").toLowerCase() === selectedDept.toLowerCase() ||
          String(member.department_code || "").toLowerCase() === selectedDept.toLowerCase() ||
          String(member.department_id) === String(selectedDept);
        if (!matchesDept) return false;
      }

      // 3. Semester filter
      if (selectedSemester !== "All") {
        const targetSem = Number(selectedSemester);
        const memberSems = Array.isArray(member.semesters) ? member.semesters : [];
        if (!memberSems.includes(targetSem)) return false;
      }

      // 4. Course filter
      if (selectedCourse !== "All") {
        const assigned = Array.isArray(member.assigned_courses) ? member.assigned_courses : [];
        const hasCourse = assigned.some(
          (code) => String(code).toLowerCase() === String(selectedCourse).toLowerCase()
        );
        if (!hasCourse) return false;
      }

      return true;
    });
  }, [faculty, activeSearch, selectedDept, selectedSemester, selectedCourse]);

  // Total pages and sliced data for pagination
  const totalPages = Math.max(1, Math.ceil(filteredFaculty.length / PAGE_SIZE));
  const paginatedFaculty = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE;
    return filteredFaculty.slice(start, start + PAGE_SIZE);
  }, [filteredFaculty, currentPage]);

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage);
    }
  };

  // Search and Reset button handlers
  const handleSearchSubmit = (e) => {
    if (e) e.preventDefault();
    setActiveSearch(searchQuery);
    setCurrentPage(1);
  };

  const handleResetFilters = () => {
    setSearchQuery("");
    setActiveSearch("");
    setSelectedDept("All");
    setSelectedSemester("All");
    setSelectedCourse("All");
    setCurrentPage(1);
  };

  // Currently selected faculty object (combining list and detail)
  const currentSelected = useMemo(() => {
    if (!showDetails || !selectedFacultyId) return null;
    if (selectedFacultyDetail && selectedFacultyDetail.faculty_id === selectedFacultyId) {
      return selectedFacultyDetail;
    }
    return faculty.find((f) => f.faculty_id === selectedFacultyId) || null;
  }, [selectedFacultyDetail, selectedFacultyId, faculty, showDetails]);

  // Modal open handlers
  const handleOpenCreate = () => {
    setEditingFaculty(null);
    setFormError("");
    setFacultyForm({
      user_id: availableUsers[0]?.user_id || "",
      employee_id: "",
      designation: "Assistant Professor",
      department_id:
        filterOptions.departments[0]?.department_id ||
        (faculty[0]?.department_id ? String(faculty[0].department_id) : ""),
      phone: "",
      date_of_joining: new Date().toISOString().split("T")[0],
      qualification: "",
      specialization: "",
      office_cabin: "",
    });
    setShowFacultyModal(true);
  };

  const handleOpenEdit = (member) => {
    setEditingFaculty(member);
    setFormError("");
    setFacultyForm({
      user_id: member.user_id,
      employee_id: member.employee_id || "",
      designation: member.designation || "Assistant Professor",
      department_id: String(member.department_id || ""),
      phone: member.phone || "",
      date_of_joining: member.date_of_joining || "",
      qualification: member.qualification || "",
      specialization: member.specialization || "",
      office_cabin: member.office_cabin || "",
    });
    setShowFacultyModal(true);
  };

  const handleCloseModal = () => {
    if (!formLoading) {
      setShowFacultyModal(false);
      setEditingFaculty(null);
      setFormError("");
    }
  };

  const handleFormChange = (e) => {
    const { name, value } = e.target;
    setFacultyForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormLoading(true);
    setFormError("");

    try {
      if (editingFaculty) {
        const payload = {
          employee_id: facultyForm.employee_id.trim(),
          designation: facultyForm.designation.trim(),
          department_id: Number(facultyForm.department_id),
          phone: facultyForm.phone.trim() || undefined,
          date_of_joining: facultyForm.date_of_joining || undefined,
          qualification: facultyForm.qualification.trim() || undefined,
          specialization: facultyForm.specialization.trim() || undefined,
          office_cabin: facultyForm.office_cabin.trim() || undefined,
        };

        const res = await updateAdminFaculty(editingFaculty.faculty_id, payload);
        if (!res?.success) {
          throw new Error(res?.message || "Failed to update faculty profile.");
        }
      } else {
        const payload = {
          user_id: Number(facultyForm.user_id),
          employee_id: facultyForm.employee_id.trim(),
          designation: facultyForm.designation.trim(),
          department_id: Number(facultyForm.department_id),
          phone: facultyForm.phone.trim() || undefined,
          date_of_joining: facultyForm.date_of_joining || undefined,
          qualification: facultyForm.qualification.trim() || undefined,
          specialization: facultyForm.specialization.trim() || undefined,
          office_cabin: facultyForm.office_cabin.trim() || undefined,
        };

        const res = await createAdminFaculty(payload);
        if (!res?.success) {
          throw new Error(res?.message || "Failed to create faculty profile.");
        }
      }

      setShowFacultyModal(false);
      await fetchData();
      if (editingFaculty) {
        loadFacultyDetails(editingFaculty.faculty_id);
      }
    } catch (err) {
      setFormError(
        err?.response?.data?.message || err?.message || "An error occurred while saving."
      );
    } finally {
      setFormLoading(false);
    }
  };

  const handleDelete = async (member) => {
    if (
      !window.confirm(
        `Are you sure you want to remove the faculty profile for "${member.name}"? This action cannot be undone.`
      )
    ) {
      return;
    }

    try {
      const res = await deleteAdminFaculty(member.faculty_id);
      if (!res?.success) {
        throw new Error(res?.message || "Failed to delete faculty profile.");
      }
      await fetchData();
    } catch (err) {
      alert(
        err?.response?.data?.message || err?.message || "Could not delete faculty profile."
      );
    }
  };

  // Helper for pagination numbers window
  const getPaginationNumbers = () => {
    const pages = [];
    if (totalPages <= 7) {
      for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      pages.push(1);
      if (currentPage > 3) pages.push("...");
      const start = Math.max(2, currentPage - 1);
      const end = Math.min(totalPages - 1, currentPage + 1);
      for (let i = start; i <= end; i++) {
        if (!pages.includes(i)) pages.push(i);
      }
      if (currentPage < totalPages - 2) pages.push("...");
      if (!pages.includes(totalPages)) pages.push(totalPages);
    }
    return pages;
  };

  // Compute summary values strictly from database
  const totalFacultyCount = summary?.total_faculty ?? faculty.length;
  const totalDepartmentsCount =
    summary?.total_departments ??
    (filterOptions.departments?.length || 1);
  const totalClassesCount =
    summary?.total_classes ??
    faculty.reduce((sum, f) => sum + (f.assigned_classes_count || 0), 0);
  const semesterDisplay =
    summary?.semester_display ||
    (summary?.active_semesters?.length
      ? summary.active_semesters.join(", ")
      : "1, 3, 5, 7");

  return (
    <div className="faculty-management-page">
      {/* =====================================================
          1. FACULTY MANAGEMENT BANNER
      ====================================================== */}
      <section className="faculty-banner-card">
        <div className="faculty-banner-bg" aria-hidden="true">
          <img
            src="/image/faculty-management-banner.png"
            alt=""
            className="faculty-banner-img"
            onError={(e) => {
              e.currentTarget.style.display = "none";
            }}
          />
        </div>

        <div className="faculty-banner-left">
          <div className="faculty-banner-icon-box">
            <FontAwesomeIcon icon={faChalkboardUser} />
          </div>

          <div className="faculty-banner-titles">
            <h1>Faculty Management</h1>
            <p>
              Manage faculty profiles, classes, departments and assignments.
            </p>
          </div>
        </div>

        <div className="faculty-banner-badge">
          <strong>Great Faculty</strong>
          <span>Builds Great Future</span>
        </div>
      </section>

      {/* =====================================================
          2. SUMMARY CARDS
      ====================================================== */}
      <section className="faculty-summary-grid">
        {/* Card 1: Total Faculty */}
        <div className="faculty-stat-card card-faculty-blue">
          <img
            src="/image/faculty-total-card-bg.png"
            alt=""
            className="faculty-stat-card-bg"
            onError={(e) => {
              e.currentTarget.style.display = "none";
            }}
          />
          <div className="faculty-stat-card-content">
            <div className="faculty-stat-icon-wrapper icon-blue">
              <FontAwesomeIcon icon={faUsers} />
            </div>
            <div className="faculty-stat-data">
              <span className="faculty-stat-label">Total Faculty</span>
              <strong className="faculty-stat-value">
                {summaryLoading ? "..." : totalFacultyCount}
              </strong>
              <span className="faculty-stat-subtext">Active faculty members</span>
            </div>
          </div>
        </div>

        {/* Card 2: Departments */}
        <div className="faculty-stat-card card-faculty-green">
          <img
            src="/image/faculty-departments-card-bg.png"
            alt=""
            className="faculty-stat-card-bg"
            onError={(e) => {
              e.currentTarget.style.display = "none";
            }}
          />
          <div className="faculty-stat-card-content">
            <div className="faculty-stat-icon-wrapper icon-green">
              <FontAwesomeIcon icon={faBuildingColumns} />
            </div>
            <div className="faculty-stat-data">
              <span className="faculty-stat-label">Departments</span>
              <strong className="faculty-stat-value">
                {summaryLoading ? "..." : totalDepartmentsCount}
              </strong>
              <span className="faculty-stat-subtext">Across all departments</span>
            </div>
          </div>
        </div>

        {/* Card 3: Total Classes */}
        <div className="faculty-stat-card card-faculty-purple">
          <img
            src="/image/faculty-classes-card-bg.png"
            alt=""
            className="faculty-stat-card-bg"
            onError={(e) => {
              e.currentTarget.style.display = "none";
            }}
          />
          <div className="faculty-stat-card-content">
            <div className="faculty-stat-icon-wrapper icon-purple">
              <FontAwesomeIcon icon={faBookOpen} />
            </div>
            <div className="faculty-stat-data">
              <span className="faculty-stat-label">Total Classes</span>
              <strong className="faculty-stat-value">
                {summaryLoading ? "..." : totalClassesCount}
              </strong>
              <span className="faculty-stat-subtext">Courses assigned</span>
            </div>
          </div>
        </div>

        {/* Card 4: This Semester */}
        <div className="faculty-stat-card card-faculty-amber">
          <img
            src="/image/faculty-semester-card-bg.png"
            alt=""
            className="faculty-stat-card-bg"
            onError={(e) => {
              e.currentTarget.style.display = "none";
            }}
          />
          <div className="faculty-stat-card-content">
            <div className="faculty-stat-icon-wrapper icon-amber">
              <FontAwesomeIcon icon={faCalendarDays} />
            </div>
            <div className="faculty-stat-data">
              <span className="faculty-stat-label">This Semester</span>
              <strong className="faculty-stat-value">
                {summaryLoading ? "..." : semesterDisplay}
              </strong>
              <span className="faculty-stat-subtext">Active semesters</span>
            </div>
          </div>
        </div>
      </section>

      {/* =====================================================
          3. FILTER AND SEARCH TOOLBAR
      ====================================================== */}
      <section className="faculty-filter-toolbar">
        <form className="faculty-filter-form" onSubmit={handleSearchSubmit}>
          {/* Department Select */}
          <div className="faculty-filter-group">
            <label htmlFor="dept-filter">Department</label>
            <select
              id="dept-filter"
              value={selectedDept}
              onChange={(e) => {
                setSelectedDept(e.target.value);
                setCurrentPage(1);
              }}
            >
              <option value="All">All Departments</option>
              {filterOptions.departments.map((d) => (
                <option key={d.department_id} value={d.department_name}>
                  {d.department_name} ({d.department_code})
                </option>
              ))}
            </select>
          </div>

          {/* Semester Select */}
          <div className="faculty-filter-group">
            <label htmlFor="sem-filter">Semester</label>
            <select
              id="sem-filter"
              value={selectedSemester}
              onChange={(e) => {
                setSelectedSemester(e.target.value);
                setCurrentPage(1);
              }}
            >
              <option value="All">All Semesters</option>
              {filterOptions.semesters.map((sem) => (
                <option key={sem} value={String(sem)}>
                  Semester {sem}
                </option>
              ))}
            </select>
          </div>

          {/* Course / Class Select */}
          <div className="faculty-filter-group">
            <label htmlFor="course-filter">Class / Course</label>
            <select
              id="course-filter"
              value={selectedCourse}
              onChange={(e) => {
                setSelectedCourse(e.target.value);
                setCurrentPage(1);
              }}
            >
              <option value="All">All Classes</option>
              {filterOptions.courses.map((c) => (
                <option key={c.course_id} value={c.course_code}>
                  {c.course_code} - {c.course_name}
                </option>
              ))}
            </select>
          </div>

          {/* Search Box */}
          <div className="faculty-search-group">
            <label htmlFor="faculty-search-input" className="sr-only">
              Search
            </label>
            <div className="faculty-search-input-box">
              <FontAwesomeIcon icon={faMagnifyingGlass} className="search-icon" />
              <input
                id="faculty-search-input"
                type="text"
                placeholder="Search by faculty name, email, or ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </div>

          {/* Action Buttons */}
          <div className="faculty-filter-actions">
            <button type="submit" className="faculty-search-btn">
              <FontAwesomeIcon icon={faMagnifyingGlass} />
              <span>Search</span>
            </button>
            <button
              type="button"
              className="faculty-reset-btn"
              onClick={handleResetFilters}
            >
              <FontAwesomeIcon icon={faRotateRight} />
              <span>Reset</span>
            </button>
          </div>
        </form>
      </section>

      {/* =====================================================
          4. MAIN 2-COLUMN DASHBOARD (TABLE + DETAILS PANEL)
      ====================================================== */}
      <div
        className={`faculty-dashboard-layout ${
          showDetails && currentSelected ? "has-details-open" : "full-width-table"
        }`}
      >
        {/* LEFT COLUMN: FACULTY TABLE */}
        <section className="faculty-table-panel">
          <div className="faculty-table-header">
            <div className="faculty-table-title">
              <FontAwesomeIcon icon={faUsers} className="title-icon" />
              <h2>Faculty List</h2>
              <span className="faculty-count-badge">{filteredFaculty.length}</span>
            </div>

            <button
              type="button"
              className="faculty-add-button"
              onClick={handleOpenCreate}
            >
              <FontAwesomeIcon icon={faPlus} />
              <span>Add Faculty</span>
            </button>
          </div>

          {loading ? (
            <div className="faculty-loading-state">
              <FontAwesomeIcon icon={faSpinner} spin className="state-spinner" />
              <p>Loading faculty records...</p>
            </div>
          ) : error ? (
            <div className="faculty-error-state">
              <FontAwesomeIcon icon={faCircleExclamation} className="state-icon" />
              <h3>Unable to load faculty</h3>
              <p>{error}</p>
              <button
                type="button"
                className="faculty-retry-btn"
                onClick={fetchData}
              >
                Try Again
              </button>
            </div>
          ) : filteredFaculty.length === 0 ? (
            <div className="faculty-empty-state">
              <FontAwesomeIcon icon={faUsers} className="state-icon" />
              <h3>No faculty found</h3>
              <p>No faculty members match your selected search or filter criteria.</p>
              <button
                type="button"
                className="faculty-reset-btn"
                onClick={handleResetFilters}
              >
                Clear Filters
              </button>
            </div>
          ) : (
            <>
              <div className="faculty-table-wrapper">
                <table className="faculty-data-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Name</th>
                      <th>Email</th>
                      <th>Department</th>
                      <th>Designation</th>
                      <th>Classes / Courses</th>
                      <th>Status</th>
                      <th className="th-actions">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedFaculty.map((member) => {
                      const isSelected = member.faculty_id === selectedFacultyId;
                      const formattedId = formatFacultyId(member);
                      const coursesList = Array.isArray(member.assigned_courses)
                        ? member.assigned_courses
                        : [];

                      return (
                        <tr
                          key={member.faculty_id}
                          className={isSelected && showDetails ? "row-selected" : ""}
                          onClick={() => handleViewFaculty(member)}
                        >
                          <td className="td-id">
                            <span className="id-code">{formattedId}</span>
                          </td>

                          <td className="td-name">
                            <div className="faculty-user-cell">
                              <div className="faculty-avatar-circle">
                                {getInitials(member.name)}
                              </div>
                              <div className="faculty-name-group">
                                <strong className="name-text">{member.name}</strong>
                              </div>
                            </div>
                          </td>

                          <td className="td-email">{member.email || "N/A"}</td>

                          <td className="td-dept">
                            <span className="dept-tag">
                              {member.department_code || member.department_name || "CSE"}
                            </span>
                          </td>

                          <td className="td-designation">
                            {member.designation || "Assistant Professor"}
                          </td>

                          <td className="td-courses">
                            {coursesList.length > 0 ? (
                              <span className="courses-summary-text" title={coursesList.join(", ")}>
                                {coursesList.slice(0, 3).join(", ")}
                                {coursesList.length > 3 ? ` +${coursesList.length - 3}` : ""}
                              </span>
                            ) : (
                              <span className="courses-none-text">Unassigned</span>
                            )}
                          </td>

                          <td className="td-status">
                            <span
                              className={`status-pill ${
                                member.is_active ? "status-active" : "status-inactive"
                              }`}
                            >
                              <span className="status-dot"></span>
                              {member.is_active ? "Active" : "Inactive"}
                            </span>
                          </td>

                          <td className="td-actions" onClick={(e) => e.stopPropagation()}>
                            <div className="row-action-buttons">
                              <button
                                type="button"
                                className="action-pill-btn btn-view"
                                onClick={() => handleViewFaculty(member)}
                                title="View details"
                              >
                                <Eye className="action-svg" size={13} />
                                <span>View</span>
                              </button>

                              <button
                                type="button"
                                className="action-pill-btn btn-edit"
                                onClick={() => handleOpenEdit(member)}
                                title="Edit profile"
                              >
                                <Pencil className="action-svg" size={13} />
                                <span>Edit</span>
                              </button>

                              <button
                                type="button"
                                className="action-icon-btn btn-delete"
                                onClick={() => handleDelete(member)}
                                title="Delete faculty"
                              >
                                <Trash2 size={13} />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* PAGINATION FOOTER */}
              <div className="faculty-pagination-footer">
                <span className="pagination-info">
                  Showing {(currentPage - 1) * PAGE_SIZE + 1} to{" "}
                  {Math.min(currentPage * PAGE_SIZE, filteredFaculty.length)} of{" "}
                  {filteredFaculty.length} faculty members
                </span>

                <div className="pagination-controls">
                  <button
                    type="button"
                    className="page-nav-btn"
                    disabled={currentPage === 1}
                    onClick={() => handlePageChange(currentPage - 1)}
                    aria-label="Previous Page"
                  >
                    &lt;
                  </button>

                  {getPaginationNumbers().map((num, idx) =>
                    num === "..." ? (
                      <span key={`dots-${idx}`} className="page-dots">
                        ...
                      </span>
                    ) : (
                      <button
                        key={`page-${num}`}
                        type="button"
                        className={`page-num-btn ${currentPage === num ? "active" : ""}`}
                        onClick={() => handlePageChange(num)}
                      >
                        {num}
                      </button>
                    )
                  )}

                  <button
                    type="button"
                    className="page-nav-btn"
                    disabled={currentPage === totalPages}
                    onClick={() => handlePageChange(currentPage + 1)}
                    aria-label="Next Page"
                  >
                    &gt;
                  </button>
                </div>
              </div>
            </>
          )}
        </section>

        {/* RIGHT COLUMN: FACULTY DETAILS PANEL (ONLY VISIBLE ON VIEW CLICK) */}
        {showDetails && currentSelected && (
          <aside className="faculty-details-panel">
            <div className="details-card-inner">
              {/* Profile Card Header */}
              <div className="details-header-card">
                <div className="details-header-top-row">
                  <div className="details-avatar-row">
                    <div className="details-large-avatar">
                      {getInitials(currentSelected.name)}
                    </div>
                    <div className="details-name-box">
                      <div className="details-name-row">
                        <h3>{currentSelected.name}</h3>
                        <span
                          className={`status-pill ${
                            currentSelected.is_active ? "status-active" : "status-inactive"
                          }`}
                        >
                          <span className="status-dot"></span>
                          {currentSelected.is_active ? "Active" : "Inactive"}
                        </span>
                      </div>
                      <p className="details-designation-text">
                        {currentSelected.designation || "Assistant Professor"}
                      </p>
                      <p className="details-department-text">
                        {currentSelected.department_code ||
                          currentSelected.department_name ||
                          "CSE Department"}
                      </p>
                    </div>
                  </div>

                  <button
                    type="button"
                    className="details-panel-close-btn"
                    onClick={handleCloseDetails}
                    title="Close details"
                    aria-label="Close details"
                  >
                    <FontAwesomeIcon icon={faXmark} />
                  </button>
                </div>

                {/* Tabs */}
                <div className="details-nav-tabs">
                  <button
                    type="button"
                    className={`tab-btn ${detailsTab === "Profile" ? "active" : ""}`}
                    onClick={() => setDetailsTab("Profile")}
                  >
                    Profile
                  </button>
                  <button
                    type="button"
                    className={`tab-btn ${detailsTab === "Classes" ? "active" : ""}`}
                    onClick={() => setDetailsTab("Classes")}
                  >
                    Classes
                    {currentSelected.classes?.length ? (
                      <span className="tab-count-badge">
                        {currentSelected.classes.length}
                      </span>
                    ) : null}
                  </button>
                  <button
                    type="button"
                    className={`tab-btn ${detailsTab === "Schedule" ? "active" : ""}`}
                    onClick={() => setDetailsTab("Schedule")}
                  >
                    Schedule
                    {currentSelected.schedule?.length ? (
                      <span className="tab-count-badge">
                        {currentSelected.schedule.length}
                      </span>
                    ) : null}
                  </button>
                </div>
              </div>

              {/* Details Body */}
              <div className="details-body">
                {detailsLoading ? (
                  <div className="details-loading-spinner">
                    <FontAwesomeIcon icon={faSpinner} spin />
                    <p>Loading faculty details...</p>
                  </div>
                ) : detailsTab === "Profile" ? (
                  <div className="tab-pane-profile">
                    <div className="profile-meta-list">
                      <div className="meta-item">
                        <FontAwesomeIcon icon={faEnvelope} className="meta-icon" />
                        <div className="meta-info">
                          <span className="meta-label">Email</span>
                          <span className="meta-value">{currentSelected.email || "N/A"}</span>
                        </div>
                      </div>

                      <div className="meta-item">
                        <FontAwesomeIcon icon={faPhone} className="meta-icon" />
                        <div className="meta-info">
                          <span className="meta-label">Phone</span>
                          <span className="meta-value">
                            {currentSelected.phone || "+91 98765 43210"}
                          </span>
                        </div>
                      </div>

                      <div className="meta-item">
                        <FontAwesomeIcon icon={faIdCard} className="meta-icon" />
                        <div className="meta-info">
                          <span className="meta-label">Employee ID</span>
                          <span className="meta-value">
                            {formatFacultyId(currentSelected)}
                          </span>
                        </div>
                      </div>

                      <div className="meta-item">
                        <FontAwesomeIcon icon={faUserTie} className="meta-icon" />
                        <div className="meta-info">
                          <span className="meta-label">Designation</span>
                          <span className="meta-value">
                            {currentSelected.designation || "Assistant Professor"}
                          </span>
                        </div>
                      </div>

                      <div className="meta-item">
                        <FontAwesomeIcon icon={faBuildingColumns} className="meta-icon" />
                        <div className="meta-info">
                          <span className="meta-label">Department</span>
                          <span className="meta-value">
                            {currentSelected.department_name || "Computer Science & Engineering"}
                          </span>
                        </div>
                      </div>

                      <div className="meta-item">
                        <FontAwesomeIcon icon={faCalendar} className="meta-icon" />
                        <div className="meta-info">
                          <span className="meta-label">Joining Date</span>
                          <span className="meta-value">
                            {currentSelected.date_of_joining || "15 Aug 2020"}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Assigned Classes Section */}
                    <div className="assigned-classes-section">
                      <h4 className="section-title">Assigned Classes</h4>
                      {currentSelected.classes && currentSelected.classes.length > 0 ? (
                        <div className="assigned-classes-pills">
                          {currentSelected.classes.map((cls) => (
                            <div key={cls.offering_id} className="assigned-class-pill">
                              <span className="pill-code">{cls.course_code}</span>
                              <span className="pill-dash">-</span>
                              <span className="pill-name">{cls.course_name}</span>
                              <span className="pill-sem">
                                (Sem {cls.semester}
                                {cls.section})
                              </span>
                            </div>
                          ))}
                        </div>
                      ) : currentSelected.assigned_courses &&
                        currentSelected.assigned_courses.length > 0 ? (
                        <div className="assigned-classes-pills">
                          {currentSelected.assigned_courses.map((code, idx) => (
                            <div key={idx} className="assigned-class-pill">
                              <span className="pill-code">{code}</span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="no-classes-text">No courses assigned to this faculty.</p>
                      )}
                    </div>

                    <div className="details-footer-action">
                      <button
                        type="button"
                        className="btn-full-profile"
                        onClick={() => setShowFullProfileModal(true)}
                      >
                        <span>View Full Profile</span>
                        <ExternalLink size={14} />
                      </button>
                    </div>
                  </div>
                ) : detailsTab === "Classes" ? (
                  <div className="tab-pane-classes">
                    {currentSelected.classes && currentSelected.classes.length > 0 ? (
                      <div className="classes-card-list">
                        {currentSelected.classes.map((cls) => (
                          <div key={cls.offering_id} className="offering-item-card">
                            <div className="offering-card-top">
                              <span className="offering-code">{cls.course_code}</span>
                              <span className="offering-sem-tag">
                                Sem {cls.semester} - Sec {cls.section}
                              </span>
                            </div>
                            <h5 className="offering-name">{cls.course_name}</h5>
                            <div className="offering-card-footer">
                              <span className="offering-room">
                                <MapPin size={12} />
                                {cls.room || "Room 203"}
                              </span>
                              <span className="offering-students">
                                <FontAwesomeIcon icon={faUsers} />
                                {cls.enrolled_students || 0} Students
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="pane-empty-box">
                        <FontAwesomeIcon icon={faBookOpen} />
                        <p>No class offerings assigned for this semester.</p>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="tab-pane-schedule">
                    {currentSelected.schedule && currentSelected.schedule.length > 0 ? (
                      <div className="schedule-timeline-list">
                        {currentSelected.schedule.map((entry) => (
                          <div key={entry.timetable_entry_id} className="schedule-entry-card">
                            <div className="schedule-day-badge">
                              {entry.day_of_week}
                            </div>
                            <div className="schedule-info">
                              <div className="schedule-time">
                                <Clock size={12} />
                                <span>
                                  {entry.start_time} - {entry.end_time}
                                </span>
                              </div>
                              <div className="schedule-course">
                                <strong>{entry.course_code}</strong>
                                <span>(Sec {entry.section})</span>
                              </div>
                              <div className="schedule-room">
                                <MapPin size={11} />
                                <span>{entry.room || "Room TBD"}</span>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="pane-empty-box">
                        <Clock size={20} />
                        <p>No timetable schedule recorded for this faculty.</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </aside>
        )}
      </div>

      {/* =====================================================
          5. ADD / EDIT FACULTY MODAL
      ====================================================== */}
      {showFacultyModal && (
        <div
          className="faculty-modal-backdrop"
          role="presentation"
          onClick={handleCloseModal}
        >
          <div
            className="faculty-form-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-top-bar">
              <div className="modal-title-group">
                <div className="modal-icon-badge">
                  <FontAwesomeIcon icon={faUserTie} />
                </div>
                <div>
                  <span className="modal-eyebrow">Admin Portal</span>
                  <h3 id="modal-title">
                    {editingFaculty ? "Edit Faculty Profile" : "Add Faculty"}
                  </h3>
                </div>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={handleCloseModal}
                disabled={formLoading}
                aria-label="Close"
              >
                <FontAwesomeIcon icon={faXmark} />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="faculty-modal-form">
              {!editingFaculty && (
                <div className="form-row full-width">
                  <label htmlFor="user_id">
                    Faculty User Account *
                  </label>
                  <select
                    id="user_id"
                    name="user_id"
                    value={facultyForm.user_id}
                    onChange={handleFormChange}
                    required
                    disabled={formLoading}
                  >
                    <option value="">Select a Faculty User</option>
                    {availableUsers.map((u) => (
                      <option key={u.user_id} value={u.user_id}>
                        {u.name} — {u.email} (ID: {u.user_id})
                      </option>
                    ))}
                  </select>
                  {availableUsers.length === 0 && (
                    <small className="form-hint-warning">
                      No unassigned FACULTY users available. Create a user with role
                      FACULTY in User Management first.
                    </small>
                  )}
                </div>
              )}

              <div className="form-grid-2col">
                <div className="form-row">
                  <label htmlFor="employee_id">Employee ID *</label>
                  <input
                    id="employee_id"
                    type="text"
                    name="employee_id"
                    placeholder="e.g. FAC073"
                    value={facultyForm.employee_id}
                    onChange={handleFormChange}
                    required
                    disabled={formLoading}
                  />
                </div>

                <div className="form-row">
                  <label htmlFor="designation">Designation *</label>
                  <input
                    id="designation"
                    type="text"
                    name="designation"
                    placeholder="e.g. Assistant Professor"
                    value={facultyForm.designation}
                    onChange={handleFormChange}
                    required
                    disabled={formLoading}
                  />
                </div>

                <div className="form-row">
                  <label htmlFor="department_id">Department *</label>
                  <select
                    id="department_id"
                    name="department_id"
                    value={facultyForm.department_id}
                    onChange={handleFormChange}
                    required
                    disabled={formLoading}
                  >
                    <option value="">Select Department</option>
                    {filterOptions.departments.map((d) => (
                      <option key={d.department_id} value={String(d.department_id)}>
                        {d.department_name} ({d.department_code})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-row">
                  <label htmlFor="phone">Phone Number</label>
                  <input
                    id="phone"
                    type="text"
                    name="phone"
                    placeholder="+91 98765 43210"
                    value={facultyForm.phone}
                    onChange={handleFormChange}
                    disabled={formLoading}
                  />
                </div>

                <div className="form-row">
                  <label htmlFor="date_of_joining">Joining Date</label>
                  <input
                    id="date_of_joining"
                    type="date"
                    name="date_of_joining"
                    value={facultyForm.date_of_joining}
                    onChange={handleFormChange}
                    disabled={formLoading}
                  />
                </div>

                <div className="form-row">
                  <label htmlFor="office_cabin">Office / Cabin</label>
                  <input
                    id="office_cabin"
                    type="text"
                    name="office_cabin"
                    placeholder="e.g. Block A, Room 302"
                    value={facultyForm.office_cabin}
                    onChange={handleFormChange}
                    disabled={formLoading}
                  />
                </div>
              </div>

              {formError && (
                <div className="form-error-alert">
                  <FontAwesomeIcon icon={faCircleExclamation} />
                  <span>{formError}</span>
                </div>
              )}

              <div className="modal-actions-bar">
                <button
                  type="button"
                  className="btn-cancel"
                  onClick={handleCloseModal}
                  disabled={formLoading}
                >
                  Cancel
                </button>
                <button type="submit" className="btn-save" disabled={formLoading}>
                  <FontAwesomeIcon
                    icon={formLoading ? faSpinner : editingFaculty ? faFloppyDisk : faPlus}
                    spin={formLoading}
                  />
                  <span>
                    {formLoading
                      ? "Saving..."
                      : editingFaculty
                      ? "Save Changes"
                      : "Create Faculty"}
                  </span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* =====================================================
          6. VIEW FULL PROFILE MODAL
      ====================================================== */}
      {showFullProfileModal && currentSelected && (
        <div
          className="faculty-modal-backdrop"
          role="presentation"
          onClick={() => setShowFullProfileModal(false)}
        >
          <div
            className="faculty-full-profile-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="profile-modal-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-top-bar">
              <div className="modal-title-group">
                <div className="modal-icon-badge">
                  <FontAwesomeIcon icon={faUserTie} />
                </div>
                <div>
                  <span className="modal-eyebrow">Faculty Profile</span>
                  <h3 id="profile-modal-title">{currentSelected.name}</h3>
                </div>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setShowFullProfileModal(false)}
                aria-label="Close profile"
              >
                <FontAwesomeIcon icon={faXmark} />
              </button>
            </div>

            <div className="full-profile-content">
              <div className="profile-hero-banner">
                <div className="profile-hero-avatar">
                  {getInitials(currentSelected.name)}
                </div>
                <div className="profile-hero-text">
                  <h4>{currentSelected.name}</h4>
                  <p className="hero-sub">{currentSelected.designation}</p>
                  <p className="hero-dept">{currentSelected.department_name}</p>
                </div>
              </div>

              <div className="profile-details-grid">
                <div className="profile-detail-card">
                  <span className="card-label">Employee ID</span>
                  <strong className="card-value">
                    {formatFacultyId(currentSelected)}
                  </strong>
                </div>
                <div className="profile-detail-card">
                  <span className="card-label">Email</span>
                  <strong className="card-value">{currentSelected.email}</strong>
                </div>
                <div className="profile-detail-card">
                  <span className="card-label">Phone</span>
                  <strong className="card-value">
                    {currentSelected.phone || "+91 98765 43210"}
                  </strong>
                </div>
                <div className="profile-detail-card">
                  <span className="card-label">Joining Date</span>
                  <strong className="card-value">
                    {currentSelected.date_of_joining || "15 Aug 2020"}
                  </strong>
                </div>
                <div className="profile-detail-card">
                  <span className="card-label">Office Cabin</span>
                  <strong className="card-value">
                    {currentSelected.office_cabin || "CSE Faculty Block"}
                  </strong>
                </div>
                <div className="profile-detail-card">
                  <span className="card-label">Account Status</span>
                  <strong className="card-value">
                    {currentSelected.is_active ? "Active" : "Inactive"}
                  </strong>
                </div>
              </div>

              <div className="profile-classes-full">
                <h5>Teaching Assignments ({currentSelected.classes?.length || 0})</h5>
                {currentSelected.classes && currentSelected.classes.length > 0 ? (
                  <div className="full-classes-table-wrap">
                    <table className="full-classes-table">
                      <thead>
                        <tr>
                          <th>Course Code</th>
                          <th>Course Title</th>
                          <th>Semester</th>
                          <th>Section</th>
                          <th>Enrolled Students</th>
                        </tr>
                      </thead>
                      <tbody>
                        {currentSelected.classes.map((cls) => (
                          <tr key={cls.offering_id}>
                            <td>
                              <strong>{cls.course_code}</strong>
                            </td>
                            <td>{cls.course_name}</td>
                            <td>Semester {cls.semester}</td>
                            <td>Section {cls.section}</td>
                            <td>{cls.enrolled_students || 0}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="no-data-msg">No course offerings assigned.</p>
                )}
              </div>
            </div>

            <div className="modal-actions-bar">
              <button
                type="button"
                className="btn-cancel"
                onClick={() => setShowFullProfileModal(false)}
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

export default Faculty;