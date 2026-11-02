import { useCallback, useEffect, useMemo, useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faAlignLeft,
  faBookOpen,
  faBuilding,
  faBuildingColumns,
  faCheck,
  faChevronLeft,
  faChevronRight,
  faCircleCheck,
  faEllipsis,
  faEye,
  faGraduationCap,
  faMagnifyingGlass,
  faPenToSquare,
  faPlus,
  faPowerOff,
  faRotateRight,
  faTableCellsLarge,
  faTrash,
  faUser,
  faUsers,
  faXmark,
} from "@fortawesome/free-solid-svg-icons";

import {
  createAdminDepartment,
  deleteAdminDepartment,
  getAdminCourses,
  getAdminDepartments,
  getAdminFaculty,
  updateAdminDepartment,
} from "../../services/adminService";

import "./Departments.css";

const PAGE_SIZE = 10;

const EMPTY_FORM = {
  departmentId: "",
  departmentName: "",
  departmentCode: "",
  headFacultyId: "",
  isActive: "true",
};

function getInitials(name = "") {
  if (!name?.trim()) return "DE";

  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function getErrorMessage(error) {
  return (
    error?.response?.data?.message ||
    error?.message ||
    "Something went wrong. Please try again."
  );
}

function normalizeDepartment(item) {
  return {
    departmentId: String(item.department_id),
    name: item.department_name ?? "",
    code: item.department_code ?? "",
    headFacultyId:
      item.head_faculty_id == null ? "" : String(item.head_faculty_id),
    headName: item.head_name ?? null,
    headEmail: item.head_email ?? null,
    headEmployeeId: item.head_employee_id ?? null,
    facultyCount: Number.isFinite(Number(item.faculty_count))
      ? Number(item.faculty_count)
      : 0,
    studentCount: Number.isFinite(Number(item.student_count))
      ? Number(item.student_count)
      : 0,
    courseCount: Number.isFinite(Number(item.course_count))
      ? Number(item.course_count)
      : 0,
    isActive: item.is_active === true || item.is_active === 1,
    description: item.description ?? "",
  };
}

const DEPT_BADGE_COLORS = [
  "#2563eb", // Royal blue
  "#8b5cf6", // Purple
  "#ea580c", // Orange
  "#0d9488", // Teal
  "#db2777", // Pink
  "#d97706", // Amber
  "#059669", // Emerald
  "#6366f1", // Indigo
];

function getDeptAvatarColor(code = "", index = 0) {
  const normalized = String(code).toUpperCase().trim();
  if (normalized === "CSE") return "#2563eb";
  if (normalized === "ECE") return "#8b5cf6";
  if (normalized === "ME") return "#ea580c";
  if (normalized === "CE") return "#0d9488";
  return DEPT_BADGE_COLORS[index % DEPT_BADGE_COLORS.length];
}

function Departments() {
  const [searchTerm, setSearchTerm] = useState("");
  const [searchFilter, setSearchFilter] = useState("");
  const [selectedHead, setSelectedHead] = useState("All");
  const [selectedStatus, setSelectedStatus] = useState("All");

  const [currentPage, setCurrentPage] = useState(1);
  const [selectedDepartment, setSelectedDepartment] = useState(null);
  const [activeMenuDeptId, setActiveMenuDeptId] = useState(null);

  const [showAddModal, setShowAddModal] = useState(false);
  const [editingDepartment, setEditingDepartment] = useState(null);
  const [formData, setFormData] = useState(EMPTY_FORM);
  const [savingDepartment, setSavingDepartment] = useState(false);
  const [formError, setFormError] = useState("");
  const [pageMessage, setPageMessage] = useState("");

  const [departments, setDepartments] = useState([]);
  const [faculty, setFaculty] = useState([]);
  const [coursesCount, setCoursesCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [facultyError, setFacultyError] = useState("");

  const fetchDepartments = useCallback(async () => {
    try {
      const response = await getAdminDepartments();

      if (!response?.success || !Array.isArray(response.data)) {
        throw new Error("Unexpected department API response.");
      }

      const normalized = response.data.map(normalizeDepartment);
      setDepartments(normalized);
      setError("");
      return true;
    } catch (err) {
      setError(getErrorMessage(err));
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchFaculty = useCallback(async () => {
    try {
      const response = await getAdminFaculty();

      if (!response?.success || !Array.isArray(response.data)) {
        throw new Error("Unexpected faculty API response.");
      }

      setFaculty(response.data);
      setFacultyError("");
      return true;
    } catch (err) {
      setFacultyError(getErrorMessage(err));
      return false;
    }
  }, []);

  const fetchCourses = useCallback(async () => {
    try {
      const response = await getAdminCourses();
      if (response?.success && Array.isArray(response.data)) {
        setCoursesCount(response.data.length);
      }
    } catch {
      // Non-critical: course total will fallback to sum of department course counts
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    const loadData = async () => {
      setLoading(true);
      const [departmentsResult, facultyResult, coursesResult] =
        await Promise.allSettled([
          getAdminDepartments(),
          getAdminFaculty(),
          getAdminCourses(),
        ]);

      if (cancelled) return;

      if (departmentsResult.status === "fulfilled") {
        const response = departmentsResult.value;
        if (response?.success && Array.isArray(response.data)) {
          setDepartments(response.data.map(normalizeDepartment));
          setError("");
        } else {
          setError("Unexpected department API response.");
        }
      } else {
        setError(getErrorMessage(departmentsResult.reason));
      }

      if (facultyResult.status === "fulfilled") {
        const response = facultyResult.value;
        if (response?.success && Array.isArray(response.data)) {
          setFaculty(response.data);
          setFacultyError("");
        } else {
          setFacultyError("Unexpected faculty API response.");
        }
      } else {
        setFacultyError(getErrorMessage(facultyResult.reason));
      }

      if (coursesResult.status === "fulfilled") {
        const response = coursesResult.value;
        if (response?.success && Array.isArray(response.data)) {
          setCoursesCount(response.data.length);
        }
      }

      setLoading(false);
    };

    loadData();

    return () => {
      cancelled = true;
    };
  }, []);

  // Close more actions menu on external click
  useEffect(() => {
    const handleOutsideClick = (e) => {
      if (!e.target.closest(".dept-action-menu-wrapper")) {
        setActiveMenuDeptId(null);
      }
    };
    document.addEventListener("click", handleOutsideClick);
    return () => document.removeEventListener("click", handleOutsideClick);
  }, []);

  // Close details panel on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape") {
        if (showAddModal) {
          setShowAddModal(false);
        } else if (selectedDepartment) {
          setSelectedDepartment(null);
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [showAddModal, selectedDepartment]);

  // Derived filter options
  const headOptions = useMemo(() => {
    const heads = [];
    const seen = new Set();

    departments.forEach((dept) => {
      if (dept.headName && !seen.has(dept.headName)) {
        seen.add(dept.headName);
        heads.push(dept.headName);
      }
    });

    return heads.sort((a, b) => a.localeCompare(b));
  }, [departments]);

  // Filtered department records
  const filteredDepartments = useMemo(() => {
    const query = searchFilter.trim().toLowerCase();

    return departments.filter((dept) => {
      // Search query filter
      if (query) {
        const matchesQuery = [
          dept.name,
          dept.code,
          dept.departmentId,
          dept.headName ?? "",
          dept.headEmail ?? "",
        ].some((val) => String(val).toLowerCase().includes(query));

        if (!matchesQuery) return false;
      }

      // Head filter
      if (selectedHead !== "All") {
        if (dept.headName !== selectedHead) return false;
      }

      // Status filter
      if (selectedStatus === "Active" && !dept.isActive) return false;
      if (selectedStatus === "Inactive" && dept.isActive) return false;

      return true;
    });
  }, [departments, searchFilter, selectedHead, selectedStatus]);

  // Pagination calculation
  const totalItems = filteredDepartments.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / PAGE_SIZE));
  const safeCurrentPage = Math.min(currentPage, totalPages);

  const paginatedDepartments = useMemo(() => {
    const start = (safeCurrentPage - 1) * PAGE_SIZE;
    return filteredDepartments.slice(start, start + PAGE_SIZE);
  }, [filteredDepartments, safeCurrentPage]);

  // Statistics counts
  const totalDepartmentsCount = departments.length;
  const activeDepartmentsCount = useMemo(
    () => departments.filter((dept) => dept.isActive).length,
    [departments],
  );

  const totalFacultyCount = useMemo(() => {
    if (faculty.length > 0) return faculty.length;
    return departments.reduce((acc, dept) => acc + (dept.facultyCount || 0), 0);
  }, [faculty, departments]);

  const totalCoursesFinalCount = useMemo(() => {
    if (coursesCount > 0) return coursesCount;
    return departments.reduce((acc, dept) => acc + (dept.courseCount || 0), 0);
  }, [coursesCount, departments]);

  // Search & Filter handlers
  const handleSearchSubmit = (e) => {
    if (e) e.preventDefault();
    setSearchFilter(searchTerm);
    setCurrentPage(1);
  };

  const handleResetFilters = () => {
    setSearchTerm("");
    setSearchFilter("");
    setSelectedHead("All");
    setSelectedStatus("All");
    setCurrentPage(1);
  };

  // View department details (Opens Side Panel)
  const handleViewDepartment = (dept) => {
    setSelectedDepartment(dept);
    setActiveMenuDeptId(null);
  };

  const handleCloseDetails = () => {
    setSelectedDepartment(null);
  };

  // Edit modal handlers
  const openCreateModal = () => {
    setEditingDepartment(null);
    setFormData(EMPTY_FORM);
    setFormError("");
    setShowAddModal(true);
    setActiveMenuDeptId(null);
  };

  const openEditModal = (department) => {
    setEditingDepartment(department);
    setFormData({
      departmentId: department.departmentId,
      departmentName: department.name,
      departmentCode: department.code,
      headFacultyId: department.headFacultyId,
      isActive: String(department.isActive),
    });
    setFormError("");
    setShowAddModal(true);
    setActiveMenuDeptId(null);
  };

  const closeModal = () => {
    if (savingDepartment) return;
    setShowAddModal(false);
    setEditingDepartment(null);
    setFormData(EMPTY_FORM);
    setFormError("");
  };

  const handleFormChange = (event) => {
    const { name, value } = event.target;
    setFormData((current) => ({
      ...current,
      [name]: value,
    }));
    if (formError) setFormError("");
  };

  const handleSaveDepartment = async (event) => {
    event.preventDefault();

    const name = formData.departmentName.trim();
    const code = formData.departmentCode.trim().toUpperCase();

    if (!name || !code) {
      setFormError("Department name and code are required.");
      return;
    }

    if (name.length > 100 || code.length > 20) {
      setFormError(
        "Department name must be at most 100 characters and code at most 20.",
      );
      return;
    }

    setSavingDepartment(true);
    setFormError("");

    try {
      const payload = {
        department_name: name,
        department_code: code,
      };

      let response;

      if (editingDepartment) {
        payload.head_faculty_id = formData.headFacultyId
          ? Number(formData.headFacultyId)
          : null;
        payload.is_active = formData.isActive === "true";

        response = await updateAdminDepartment(
          editingDepartment.departmentId,
          payload,
        );
      } else {
        response = await createAdminDepartment(payload);
      }

      if (!response?.success) {
        throw new Error(response?.message || "Unable to save department.");
      }

      const wasEditing = Boolean(editingDepartment);

      setShowAddModal(false);
      setEditingDepartment(null);
      setFormData(EMPTY_FORM);

      await fetchDepartments();
      await fetchCourses();

      setPageMessage(
        wasEditing
          ? "Department updated successfully."
          : "Department created successfully.",
      );

      // If updating currently viewed department, update its details
      if (wasEditing && selectedDepartment?.departmentId === editingDepartment.departmentId) {
        setSelectedDepartment((prev) =>
          prev
            ? {
                ...prev,
                name,
                code,
                isActive: payload.is_active,
                headFacultyId: payload.head_faculty_id ? String(payload.head_faculty_id) : "",
              }
            : null,
        );
      }
    } catch (err) {
      setFormError(getErrorMessage(err));
    } finally {
      setSavingDepartment(false);
    }
  };

  // Toggle active/inactive status from menu
  const handleToggleStatus = async (department) => {
    setActiveMenuDeptId(null);
    try {
      const updatedStatus = !department.isActive;
      const response = await updateAdminDepartment(department.departmentId, {
        is_active: updatedStatus,
      });

      if (!response?.success) {
        throw new Error(response?.message || "Unable to update status.");
      }

      setPageMessage(
        `Department "${department.name}" marked as ${
          updatedStatus ? "Active" : "Inactive"
        }.`,
      );

      await fetchDepartments();

      if (selectedDepartment?.departmentId === department.departmentId) {
        setSelectedDepartment((prev) =>
          prev ? { ...prev, isActive: updatedStatus } : null,
        );
      }
    } catch (err) {
      setPageMessage(`Error: ${getErrorMessage(err)}`);
    }
  };

  // Delete department
  const handleDeleteDepartment = async (department) => {
    setActiveMenuDeptId(null);
    const confirmed = window.confirm(
      `Are you sure you want to delete "${department.name}" (${department.code})?\n\nNote: If this department has linked students, faculty, or courses, the database will preserve them and reject deletion.`,
    );

    if (!confirmed) return;

    try {
      const response = await deleteAdminDepartment(department.departmentId);

      if (!response?.success) {
        throw new Error(response?.message || "Unable to delete department.");
      }

      setPageMessage(`Department "${department.name}" deleted successfully.`);

      if (selectedDepartment?.departmentId === department.departmentId) {
        setSelectedDepartment(null);
      }

      await fetchDepartments();
      await fetchCourses();
    } catch (err) {
      setPageMessage(`Cannot delete: ${getErrorMessage(err)}`);
    }
  };

  const handleRetry = async () => {
    setLoading(true);
    setError("");
    await Promise.all([fetchDepartments(), fetchFaculty(), fetchCourses()]);
  };

  const departmentFacultyForModal = useMemo(() => {
    if (!editingDepartment) return [];
    return faculty.filter(
      (member) =>
        String(member.department_id) === editingDepartment.departmentId,
    );
  }, [faculty, editingDepartment]);

  return (
    <section className="department-management-page">
      {/* =====================================================
          1. DEPARTMENT MANAGEMENT BANNER
      ====================================================== */}
      <section className="department-banner-card">
        <div className="department-banner-left">
          <div className="department-banner-icon-box">
            <FontAwesomeIcon icon={faBuildingColumns} />
          </div>

          <div className="department-banner-titles">
            <h1>Department Management</h1>
            <p>Manage departments, faculty, courses and academic details.</p>
          </div>
        </div>

        <div className="department-banner-right">
          <div className="department-banner-badge">
            <div className="department-banner-badge-icon">
              <FontAwesomeIcon icon={faGraduationCap} />
            </div>
            <div className="department-banner-badge-content">
              <strong>Building better education</strong>
              <span>
                Efficient department management for a stronger future.
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* =====================================================
          2. STATISTICS SUMMARY CARDS
      ====================================================== */}
      <section className="department-summary-grid">
        {/* Card 1: Total Departments */}
        <article className="department-summary-card card-total-dept">
          <div className="department-summary-card-inner">
            <div className="department-summary-icon icon-blue">
              <FontAwesomeIcon icon={faBuilding} />
            </div>
            <div className="department-summary-content">
              <div className="department-summary-header">
                <span className="department-summary-label">
                  Total Departments
                </span>
                <FontAwesomeIcon
                  icon={faChevronRight}
                  className="department-summary-chevron"
                />
              </div>
              <strong className="department-summary-value">
                {loading ? "..." : totalDepartmentsCount}
              </strong>
              <span className="department-summary-sub">
                All departments in the system
              </span>
            </div>
          </div>
        </article>

        {/* Card 2: Active Departments */}
        <article className="department-summary-card card-active-dept">
          <div className="department-summary-card-inner">
            <div className="department-summary-icon icon-green">
              <FontAwesomeIcon icon={faCircleCheck} />
            </div>
            <div className="department-summary-content">
              <div className="department-summary-header">
                <span className="department-summary-label">
                  Active Departments
                </span>
                <FontAwesomeIcon
                  icon={faChevronRight}
                  className="department-summary-chevron"
                />
              </div>
              <strong className="department-summary-value">
                {loading ? "..." : activeDepartmentsCount}
              </strong>
              <span className="department-summary-sub">Currently active</span>
            </div>
          </div>
        </article>

        {/* Card 3: Total Faculty */}
        <article className="department-summary-card card-total-faculty">
          <div className="department-summary-card-inner">
            <div className="department-summary-icon icon-purple">
              <FontAwesomeIcon icon={faUsers} />
            </div>
            <div className="department-summary-content">
              <div className="department-summary-header">
                <span className="department-summary-label">Total Faculty</span>
                <FontAwesomeIcon
                  icon={faChevronRight}
                  className="department-summary-chevron"
                />
              </div>
              <strong className="department-summary-value">
                {loading ? "..." : totalFacultyCount}
              </strong>
              <span className="department-summary-sub">
                Across all departments
              </span>
            </div>
          </div>
        </article>

        {/* Card 4: Total Courses */}
        <article className="department-summary-card card-total-courses">
          <div className="department-summary-card-inner">
            <div className="department-summary-icon icon-amber">
              <FontAwesomeIcon icon={faBookOpen} />
            </div>
            <div className="department-summary-content">
              <div className="department-summary-header">
                <span className="department-summary-label">Total Courses</span>
                <FontAwesomeIcon
                  icon={faChevronRight}
                  className="department-summary-chevron"
                />
              </div>
              <strong className="department-summary-value">
                {loading ? "..." : totalCoursesFinalCount}
              </strong>
              <span className="department-summary-sub">
                Across all departments
              </span>
            </div>
          </div>
        </article>
      </section>

      {/* =====================================================
          3. SEARCH AND FILTERS BAR
      ====================================================== */}
      <section className="department-filters-card">
        <form
          className="department-filters-form"
          onSubmit={handleSearchSubmit}
        >
          {/* Search Box */}
          <div className="department-filter-group filter-search-group">
            <div className="department-search-input-box">
              <FontAwesomeIcon
                icon={faMagnifyingGlass}
                className="department-search-icon"
              />
              <input
                id="department-search-input"
                type="search"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search by department name, code, or head..."
                aria-label="Search departments"
              />
            </div>
          </div>

          {/* Head of Department Select */}
          <div className="department-filter-group">
            <label
              htmlFor="department-head-select"
              className="department-filter-label"
            >
              Head of Department
            </label>
            <select
              id="department-head-select"
              value={selectedHead}
              onChange={(e) => {
                setSelectedHead(e.target.value);
                setCurrentPage(1);
              }}
              className="department-filter-select"
            >
              <option value="All">All Heads</option>
              {headOptions.map((head) => (
                <option key={head} value={head}>
                  {head}
                </option>
              ))}
            </select>
          </div>

          {/* Status Select */}
          <div className="department-filter-group">
            <label
              htmlFor="department-status-select"
              className="department-filter-label"
            >
              Status
            </label>
            <select
              id="department-status-select"
              value={selectedStatus}
              onChange={(e) => {
                setSelectedStatus(e.target.value);
                setCurrentPage(1);
              }}
              className="department-filter-select"
            >
              <option value="All">All Status</option>
              <option value="Active">Active</option>
              <option value="Inactive">Inactive</option>
            </select>
          </div>

          {/* Action Buttons: Search & Reset */}
          <div className="department-filter-actions">
            <button
              type="submit"
              className="department-filter-search-btn"
              title="Search"
            >
              <FontAwesomeIcon icon={faMagnifyingGlass} />
              <span>Search</span>
            </button>

            <button
              type="button"
              className="department-filter-reset-btn"
              onClick={handleResetFilters}
              title="Reset all filters"
            >
              <FontAwesomeIcon icon={faRotateRight} />
              <span>Reset</span>
            </button>
          </div>
        </form>
      </section>

      {/* Notifications / Flash Messages */}
      {pageMessage && (
        <div className="department-alert-banner" role="status">
          <div className="department-alert-content">
            <FontAwesomeIcon icon={faCheck} />
            <span>{pageMessage}</span>
          </div>
          <button
            type="button"
            className="department-alert-close"
            onClick={() => setPageMessage("")}
            aria-label="Dismiss message"
          >
            <FontAwesomeIcon icon={faXmark} />
          </button>
        </div>
      )}

      {/* =====================================================
          4. WORKSPACE: DEPARTMENT TABLE + SIDE PANEL
      ====================================================== */}
      <div
        className={`department-workspace-layout ${
          selectedDepartment ? "with-details-panel" : "full-width-table"
        }`}
      >
        {/* Table Container */}
        <section className="department-table-card">
          <div className="department-table-header">
            <div className="department-table-title">
              <div className="department-table-icon">
                <FontAwesomeIcon icon={faBuilding} />
              </div>
              <h2>
                Department List ({filteredDepartments.length})
              </h2>
            </div>

            <button
              type="button"
              className="department-add-button"
              onClick={openCreateModal}
            >
              <FontAwesomeIcon icon={faPlus} />
              <span>Add Department</span>
            </button>
          </div>

          <div className="department-table-responsive">
            <table className="department-data-table">
              <thead>
                <tr>
                  <th className="th-sn">S.N.</th>
                  <th className="th-dept">Department</th>
                  <th className="th-code">Department Code</th>
                  <th className="th-hod">Head of Department</th>
                  <th className="th-count">Faculty</th>
                  <th className="th-count">Courses</th>
                  <th className="th-status">Status</th>
                  <th className="th-actions">Actions</th>
                </tr>
              </thead>

              <tbody>
                {!loading &&
                  !error &&
                  paginatedDepartments.map((dept, index) => {
                    const rowSn = (safeCurrentPage - 1) * PAGE_SIZE + index + 1;
                    const avatarColor = getDeptAvatarColor(dept.code, index);
                    const isSelected =
                      selectedDepartment?.departmentId === dept.departmentId;

                    return (
                      <tr
                        key={dept.departmentId}
                        className={isSelected ? "row-selected" : ""}
                      >
                        <td className="td-sn">{rowSn}</td>

                        <td className="td-dept">
                          <div className="dept-identity-box">
                            <div
                              className="dept-avatar-badge"
                              style={{ backgroundColor: avatarColor }}
                              aria-hidden="true"
                            >
                              {dept.code || getInitials(dept.name)}
                            </div>
                            <span className="dept-name-text" title={dept.name}>
                              {dept.name}
                            </span>
                          </div>
                        </td>

                        <td className="td-code">
                          <span className="dept-code-tag">{dept.code}</span>
                        </td>

                        <td className="td-hod">
                          {dept.headName ? (
                            <div className="dept-hod-info">
                              <span className="dept-hod-name">
                                {dept.headName}
                              </span>
                              {dept.headEmail ? (
                                <span className="dept-hod-email">
                                  {dept.headEmail}
                                </span>
                              ) : null}
                            </div>
                          ) : (
                            <span className="dept-hod-empty">Not assigned</span>
                          )}
                        </td>

                        <td className="td-count">{dept.facultyCount}</td>

                        <td className="td-count">{dept.courseCount}</td>

                        <td className="td-status">
                          <span
                            className={`department-status-badge ${
                              dept.isActive ? "status-active" : "status-inactive"
                            }`}
                          >
                            <span className="status-dot" aria-hidden="true" />
                            {dept.isActive ? "Active" : "Inactive"}
                          </span>
                        </td>

                        <td className="td-actions">
                          <div className="dept-actions-group">
                            {/* View (eye) button -> opens details panel */}
                            <button
                              type="button"
                              className={`dept-action-btn view-btn ${
                                isSelected ? "active-view-btn" : ""
                              }`}
                              onClick={() => handleViewDepartment(dept)}
                              title="View Department Details"
                              aria-label={`View details for ${dept.name}`}
                            >
                              <FontAwesomeIcon icon={faEye} />
                            </button>

                            {/* Edit (pencil) button -> opens edit modal */}
                            <button
                              type="button"
                              className="dept-action-btn edit-btn"
                              onClick={() => openEditModal(dept)}
                              title="Edit Department"
                              aria-label={`Edit ${dept.name}`}
                            >
                              <FontAwesomeIcon icon={faPenToSquare} />
                            </button>

                            {/* More actions button -> dropdown */}
                            <div className="dept-action-menu-wrapper">
                              <button
                                type="button"
                                className="dept-action-btn more-btn"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setActiveMenuDeptId(
                                    activeMenuDeptId === dept.departmentId
                                      ? null
                                      : dept.departmentId,
                                  );
                                }}
                                title="More Actions"
                                aria-label="More actions"
                                aria-expanded={
                                  activeMenuDeptId === dept.departmentId
                                }
                              >
                                <FontAwesomeIcon icon={faEllipsis} />
                              </button>

                              {activeMenuDeptId === dept.departmentId && (
                                <div className="dept-dropdown-menu" role="menu">
                                  <button
                                    type="button"
                                    className="dept-dropdown-item"
                                    onClick={() => handleToggleStatus(dept)}
                                  >
                                    <FontAwesomeIcon icon={faPowerOff} />
                                    <span>
                                      {dept.isActive
                                        ? "Deactivate Department"
                                        : "Activate Department"}
                                    </span>
                                  </button>

                                  <button
                                    type="button"
                                    className="dept-dropdown-item item-danger"
                                    onClick={() => handleDeleteDepartment(dept)}
                                  >
                                    <FontAwesomeIcon icon={faTrash} />
                                    <span>Delete Department</span>
                                  </button>
                                </div>
                              )}
                            </div>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>

            {/* Empty, Loading, and Error States */}
            {loading ? (
              <div className="department-table-state-box" role="status">
                <h3>Loading departments...</h3>
                <p>Please wait while department records are retrieved.</p>
              </div>
            ) : error ? (
              <div className="department-table-state-box error-box" role="alert">
                <h3>Unable to load departments</h3>
                <p>{error}</p>
                <button
                  type="button"
                  className="department-retry-btn"
                  onClick={handleRetry}
                >
                  <FontAwesomeIcon icon={faRotateRight} />
                  <span>Retry</span>
                </button>
              </div>
            ) : departments.length === 0 ? (
              <div className="department-table-state-box">
                <h3>No departments created yet</h3>
                <p>Click "Add Department" to register your first academic department.</p>
              </div>
            ) : filteredDepartments.length === 0 ? (
              <div className="department-table-state-box">
                <h3>No matching departments found</h3>
                <p>Try adjusting your search query or status filter.</p>
                <button
                  type="button"
                  className="department-retry-btn"
                  onClick={handleResetFilters}
                >
                  <FontAwesomeIcon icon={faRotateRight} />
                  <span>Reset Filters</span>
                </button>
              </div>
            ) : null}
          </div>

          {/* Table Footer: Pagination */}
          {!loading && !error && filteredDepartments.length > 0 && (
            <div className="department-table-footer">
              <span className="department-pagination-info">
                Showing{" "}
                <strong>
                  {Math.min(
                    (safeCurrentPage - 1) * PAGE_SIZE + 1,
                    totalItems,
                  )}{" "}
                  – {Math.min(safeCurrentPage * PAGE_SIZE, totalItems)}
                </strong>{" "}
                of <strong>{totalItems}</strong> departments
              </span>

              <div className="department-pagination-controls">
                <button
                  type="button"
                  className="department-page-nav-btn"
                  disabled={safeCurrentPage <= 1}
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  aria-label="Previous page"
                >
                  <FontAwesomeIcon icon={faChevronLeft} />
                </button>

                {Array.from({ length: totalPages }, (_, i) => i + 1).map(
                  (pageNum) => (
                    <button
                      key={pageNum}
                      type="button"
                      className={`department-page-num-btn ${
                        pageNum === safeCurrentPage ? "active" : ""
                      }`}
                      onClick={() => setCurrentPage(pageNum)}
                    >
                      {pageNum}
                    </button>
                  ),
                )}

                <button
                  type="button"
                  className="department-page-nav-btn"
                  disabled={safeCurrentPage >= totalPages}
                  onClick={() =>
                    setCurrentPage((p) => Math.min(totalPages, p + 1))
                  }
                  aria-label="Next page"
                >
                  <FontAwesomeIcon icon={faChevronRight} />
                </button>
              </div>
            </div>
          )}
        </section>

        {/* =====================================================
            5. DEPARTMENT DETAILS SIDE PANEL (CLICK-TRIGGERED)
        ====================================================== */}
        {selectedDepartment && (
          <aside
            className="department-details-panel"
            aria-label="Department Details"
          >
            {/* Top Blue Header Card */}
            <div className="dept-details-header-card">
              <div className="dept-details-header-badge">
                {getInitials(selectedDepartment.name)}
              </div>

              <div className="dept-details-header-text">
                <h3>{selectedDepartment.name}</h3>
                <span className="dept-details-code-sub">
                  {selectedDepartment.code}
                </span>
              </div>

              <div className="dept-details-header-right">
                <span
                  className={`dept-details-status-pill ${
                    selectedDepartment.isActive ? "active" : "inactive"
                  }`}
                >
                  {selectedDepartment.isActive ? "Active" : "Inactive"}
                </span>

                <button
                  type="button"
                  className="dept-details-close-btn"
                  onClick={handleCloseDetails}
                  aria-label="Close details panel"
                  title="Close (Esc)"
                >
                  <FontAwesomeIcon icon={faXmark} />
                </button>
              </div>
            </div>

            {/* Details Attributes List Card */}
            <div className="dept-details-body-card">
              <div className="dept-details-attributes-list">
                <div className="dept-attr-row">
                  <div className="dept-attr-icon">
                    <FontAwesomeIcon icon={faBuilding} />
                  </div>
                  <span className="dept-attr-label">Department Name</span>
                  <strong className="dept-attr-value">
                    {selectedDepartment.name}
                  </strong>
                </div>

                <div className="dept-attr-row">
                  <div className="dept-attr-icon">
                    <FontAwesomeIcon icon={faTableCellsLarge} />
                  </div>
                  <span className="dept-attr-label">Department Code</span>
                  <strong className="dept-attr-value">
                    {selectedDepartment.code}
                  </strong>
                </div>

                <div className="dept-attr-row">
                  <div className="dept-attr-icon">
                    <FontAwesomeIcon icon={faUser} />
                  </div>
                  <span className="dept-attr-label">Head of Department</span>
                  <div className="dept-attr-value-group">
                    <strong className="dept-attr-value">
                      {selectedDepartment.headName || "Not assigned"}
                    </strong>
                    {selectedDepartment.headEmail && (
                      <span className="dept-attr-sub">
                        {selectedDepartment.headEmail}
                      </span>
                    )}
                  </div>
                </div>

                <div className="dept-attr-row">
                  <div className="dept-attr-icon">
                    <FontAwesomeIcon icon={faUsers} />
                  </div>
                  <span className="dept-attr-label">Total Faculty</span>
                  <strong className="dept-attr-value">
                    {selectedDepartment.facultyCount}
                  </strong>
                </div>

                <div className="dept-attr-row">
                  <div className="dept-attr-icon">
                    <FontAwesomeIcon icon={faBookOpen} />
                  </div>
                  <span className="dept-attr-label">Total Courses</span>
                  <strong className="dept-attr-value">
                    {selectedDepartment.courseCount}
                  </strong>
                </div>

                <div className="dept-attr-row dept-attr-description-row">
                  <div className="dept-attr-icon">
                    <FontAwesomeIcon icon={faAlignLeft} />
                  </div>
                  <span className="dept-attr-label">Description</span>
                  <p className="dept-attr-desc-text">
                    {selectedDepartment.description ||
                      "Focuses on academic excellence, modern curriculum, and comprehensive student learning."}
                  </p>
                </div>
              </div>

              {/* Action in Details Card */}
              <div className="dept-details-footer-action">
                <button
                  type="button"
                  className="dept-details-action-btn"
                  onClick={() => openEditModal(selectedDepartment)}
                >
                  <FontAwesomeIcon icon={faPenToSquare} />
                  <span>Edit Department</span>
                </button>
              </div>
            </div>
          </aside>
        )}
      </div>

      {/* =====================================================
          6. ADD / EDIT DEPARTMENT MODAL
      ====================================================== */}
      {showAddModal && (
        <div
          className="department-modal-overlay"
          role="presentation"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) closeModal();
          }}
        >
          <div
            className="department-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="dept-modal-title"
          >
            <div className="department-modal-header">
              <div className="department-modal-header-text">
                <span className="dept-modal-eyebrow">Department Management</span>
                <h2 id="dept-modal-title">
                  {editingDepartment ? "Edit Department" : "Add Department"}
                </h2>
                <p>
                  {editingDepartment
                    ? "Update department information, HOD assignment, and status."
                    : "Create a new academic department in the institution."}
                </p>
              </div>

              <button
                type="button"
                className="department-modal-close-btn"
                onClick={closeModal}
                disabled={savingDepartment}
                aria-label="Close dialog"
              >
                <FontAwesomeIcon icon={faXmark} />
              </button>
            </div>

            <form onSubmit={handleSaveDepartment}>
              <div className="department-modal-body">
                {formError && (
                  <div className="dept-modal-error-box" role="alert">
                    <span>{formError}</span>
                  </div>
                )}

                <div className="dept-modal-grid">
                  {editingDepartment && (
                    <div className="dept-modal-field">
                      <label htmlFor="modal-dept-id">Department ID</label>
                      <input
                        id="modal-dept-id"
                        type="text"
                        value={formData.departmentId}
                        disabled
                        className="input-disabled"
                      />
                    </div>
                  )}

                  <div className="dept-modal-field">
                    <label htmlFor="modal-dept-name">Department Name *</label>
                    <input
                      id="modal-dept-name"
                      name="departmentName"
                      type="text"
                      value={formData.departmentName}
                      onChange={handleFormChange}
                      placeholder="e.g. Computer Science & Engineering"
                      maxLength={100}
                      required
                      disabled={savingDepartment}
                    />
                  </div>

                  <div className="dept-modal-field">
                    <label htmlFor="modal-dept-code">Department Code *</label>
                    <input
                      id="modal-dept-code"
                      name="departmentCode"
                      type="text"
                      value={formData.departmentCode}
                      onChange={handleFormChange}
                      placeholder="e.g. CSE"
                      maxLength={20}
                      required
                      disabled={savingDepartment}
                    />
                  </div>

                  {editingDepartment && (
                    <>
                      <div className="dept-modal-field dept-modal-field-full">
                        <label htmlFor="modal-dept-hod">
                          Head of Department (HOD)
                        </label>
                        <select
                          id="modal-dept-hod"
                          name="headFacultyId"
                          value={formData.headFacultyId}
                          onChange={handleFormChange}
                          disabled={savingDepartment || Boolean(facultyError)}
                        >
                          <option value="">No HOD assigned</option>
                          {departmentFacultyForModal
                            .filter((m) => m.is_active === true)
                            .map((member) => (
                              <option
                                key={member.faculty_id}
                                value={String(member.faculty_id)}
                              >
                                {member.name} ({member.employee_id})
                              </option>
                            ))}
                        </select>
                        {facultyError ? (
                          <small className="field-hint error-hint">
                            Could not load faculty: {facultyError}
                          </small>
                        ) : departmentFacultyForModal.length === 0 ? (
                          <small className="field-hint">
                            No faculty registered in this department yet.
                          </small>
                        ) : (
                          <small className="field-hint">
                            Only active faculty belonging to this department can be
                            assigned as HOD.
                          </small>
                        )}
                      </div>

                      <div className="dept-modal-field dept-modal-field-full">
                        <label htmlFor="modal-dept-status">
                          Department Status
                        </label>
                        <select
                          id="modal-dept-status"
                          name="isActive"
                          value={formData.isActive}
                          onChange={handleFormChange}
                          disabled={savingDepartment}
                        >
                          <option value="true">Active</option>
                          <option value="false">Inactive</option>
                        </select>
                      </div>
                    </>
                  )}
                </div>
              </div>

              <div className="department-modal-footer">
                <button
                  type="button"
                  className="dept-modal-cancel-btn"
                  onClick={closeModal}
                  disabled={savingDepartment}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="dept-modal-submit-btn"
                  disabled={savingDepartment}
                >
                  {savingDepartment
                    ? "Saving..."
                    : editingDepartment
                      ? "Save Changes"
                      : "Add Department"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  );
}

export default Departments;
