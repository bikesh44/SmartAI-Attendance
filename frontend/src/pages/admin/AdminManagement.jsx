import {
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faCheck,
  faChevronDown,
  faChevronLeft,
  faChevronRight,
  faMagnifyingGlass,
  faPlus,
  faShieldHalved,
  faSpinner,
  faTrash,
  faUser,
  faUserGraduate,
  faUsers,
  faUserTie,
  faXmark,
  faRotateRight,
  faPowerOff,
  faCircleCheck,
  faEye,
  faEnvelope,
  faBuilding,
  faPhone,
  faPenToSquare,
} from "@fortawesome/free-solid-svg-icons";

import {
  createUser,
  getUsers,
  updateUser,
  deleteUser,
  reactivateUser,
} from "../../services/adminService";

import { formatDate, formatLastLogin } from "../../utils/dateUtils";

import AuthContext from "../../context/authContext";
import "./AdminManagement.css";

const PAGE_SIZE = 10;

const initialFormData = {
  name: "",
  email: "",
  password: "",
  confirmPassword: "",
  role: "STUDENT",
};

const initialEditFormData = {
  name: "",
  email: "",
  password: "",
  confirmPassword: "",
  role: "STUDENT",
};

function getRoleLabel(role) {
  const normalized = String(role ?? "").trim().toUpperCase();

  switch (normalized) {
    case "STUDENT":
      return "Student";
    case "FACULTY":
      return "Faculty";
    case "ADMIN":
      return "Admin";
    default:
      return normalized || "Unknown";
  }
}

function getRoleIcon(role) {
  switch (String(role ?? "").toUpperCase()) {
    case "STUDENT":
      return faUserGraduate;
    case "FACULTY":
      return faUserTie;
    case "ADMIN":
      return faShieldHalved;
    default:
      return faUser;
  }
}

function getInitials(name) {
  if (!name?.trim()) return "U";

  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join("");
}

function getApiErrorMessage(error, fallback) {
  return (
    error?.response?.data?.message ||
    error?.response?.data?.error ||
    error?.message ||
    fallback
  );
}

function isUserActive(user) {
  return user?.is_active !== false;
}

function AdminManagement() {
  const { user: currentUser } = useContext(AuthContext);

  const [users, setUsers] = useState([]);
  const [loadingUsers, setLoadingUsers] = useState(true);
  const [refreshingUsers, setRefreshingUsers] = useState(false);

  const [searchTerm, setSearchTerm] = useState("");
  const [roleFilter, setRoleFilter] = useState("ALL");
  const [departmentFilter, setDepartmentFilter] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedUser, setSelectedUser] = useState(null);

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);

  const [formData, setFormData] = useState(initialFormData);
  const [editFormData, setEditFormData] = useState(initialEditFormData);

  const [status, setStatus] = useState({
    type: "",
    message: "",
  });

  const [submitting, setSubmitting] = useState(false);
  const [updatingUserId, setUpdatingUserId] = useState(null);
  const [deletingUserId, setDeletingUserId] = useState(null);
  const [reactivatingUserId, setReactivatingUserId] = useState(null);

  const loadUsers = useCallback(async (showRefresh = false) => {
    if (showRefresh) {
      setRefreshingUsers(true);
    } else {
      setLoadingUsers(true);
    }

    try {
      const result = await getUsers();

      if (!result?.success) {
        setStatus({
          type: "error",
          message: result?.message || "Unable to load users.",
        });
        return false;
      }

      setUsers(Array.isArray(result.data) ? result.data : []);
      return true;
    } catch (error) {
      setStatus({
        type: "error",
        message: getApiErrorMessage(
          error,
          "Unable to load users. Please try again."
        ),
      });
      return false;
    } finally {
      setLoadingUsers(false);
      setRefreshingUsers(false);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;

    const fetchUsers = async () => {
      try {
        await loadUsers();
      } catch (error) {
        if (isMounted) {
          console.error("Failed to load users:", error);
        }
      }
    };

    void fetchUsers();

    return () => {
      isMounted = false;
    };
  }, [loadUsers]);

  function showMessage(type, message) {
    setStatus({ type, message });
  }

  function handleSearchChange(event) {
    setSearchTerm(event.target.value);
    setCurrentPage(1);
  }

  function handleRoleFilterChange(event) {
    setRoleFilter(event.target.value);
    setCurrentPage(1);
  }

  function handleDepartmentFilterChange(event) {
    setDepartmentFilter(event.target.value);
    setCurrentPage(1);
  }

  function handleStatusFilterChange(event) {
    setStatusFilter(event.target.value);
    setCurrentPage(1);
  }

  function handleResetFilters() {
    setSearchTerm("");
    setRoleFilter("ALL");
    setDepartmentFilter("ALL");
    setStatusFilter("ALL");
    setCurrentPage(1);
  }

  const hasActiveFilters =
    searchTerm.trim() !== "" ||
    roleFilter !== "ALL" ||
    departmentFilter !== "ALL" ||
    statusFilter !== "ALL";

  function handleCreateChange(event) {
    const { name, value } = event.target;

    setFormData((current) => ({
      ...current,
      [name]: value,
    }));
  }

  function handleEditChange(event) {
    const { name, value } = event.target;

    setEditFormData((current) => ({
      ...current,
      [name]: value,
    }));
  }

  function openCreateModal() {
    setStatus({ type: "", message: "" });
    setFormData(initialFormData);
    setShowCreateModal(true);
  }

  function closeCreateModal() {
    if (submitting) return;

    setShowCreateModal(false);
    setFormData(initialFormData);
  }

  async function handleCreateUser(event) {
    event.preventDefault();
    setStatus({ type: "", message: "" });

    const name = formData.name.trim();
    const email = formData.email.trim();

    if (!name || !email) {
      showMessage("error", "Name and email are required.");
      return;
    }

    if (formData.password.length < 8) {
      showMessage("error", "Password must be at least 8 characters.");
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      showMessage("error", "Passwords do not match.");
      return;
    }

    setSubmitting(true);

    try {
      const result = await createUser({
        name,
        email,
        password: formData.password,
        role: formData.role,
      });

      if (!result?.success) {
        showMessage(
          "error",
          result?.message || "Unable to create user."
        );
        return;
      }

      setShowCreateModal(false);
      setFormData(initialFormData);

      const userId = result?.data?.user_id;
      showMessage(
        "success",
        userId
          ? `User created successfully. User ID: ${userId}.`
          : "User created successfully."
      );

      await loadUsers(true);
    } catch (error) {
      showMessage(
        "error",
        getApiErrorMessage(error, "Unable to create user.")
      );
    } finally {
      setSubmitting(false);
    }
  }

  function openEditModal(user) {
    setStatus({ type: "", message: "" });
    setEditingUser(user);

    setEditFormData({
      name: user.name || "",
      email: user.email || "",
      password: "",
      confirmPassword: "",
      role: user.role || "STUDENT",
    });
  }

  function closeEditModal() {
    if (updatingUserId !== null) return;

    setEditingUser(null);
    setEditFormData(initialEditFormData);
  }

  async function handleUpdateUser(event) {
    event.preventDefault();

    if (!editingUser?.user_id) return;

    setStatus({ type: "", message: "" });

    const name = editFormData.name.trim();
    const email = editFormData.email.trim();

    if (!name || !email) {
      showMessage("error", "Name and email are required.");
      return;
    }

    if (
      editFormData.password &&
      editFormData.password.length < 8
    ) {
      showMessage("error", "Password must be at least 8 characters.");
      return;
    }

    if (editFormData.password !== editFormData.confirmPassword) {
      showMessage("error", "Passwords do not match.");
      return;
    }

    const isCurrentUser =
      currentUser?.user_id === editingUser.user_id;

    if (isCurrentUser && editFormData.role !== "ADMIN") {
      showMessage(
        "error",
        "Your current account must remain an administrator."
      );
      return;
    }

    const updateData = {
      name,
      email,
      role: editFormData.role,
    };

    if (editFormData.password) {
      updateData.password = editFormData.password;
    }

    setUpdatingUserId(editingUser.user_id);

    try {
      const result = await updateUser(
        editingUser.user_id,
        updateData
      );

      if (!result?.success) {
        showMessage(
          "error",
          result?.message || "Unable to update user."
        );
        return;
      }

      const updatedData = result.data || {};
      setUsers((current) =>
        current.map((user) =>
          user.user_id === editingUser.user_id
            ? { ...user, ...updatedData }
            : user
        )
      );

      if (selectedUser?.user_id === editingUser.user_id) {
        setSelectedUser((prev) => ({ ...prev, ...updatedData }));
      }

      setEditingUser(null);
      setEditFormData(initialEditFormData);
      showMessage("success", "User updated successfully.");
    } catch (error) {
      showMessage(
        "error",
        getApiErrorMessage(error, "Unable to update user.")
      );
    } finally {
      setUpdatingUserId(null);
    }
  }

  async function handleDeleteUser(user) {
    if (!user?.user_id) return;

    if (currentUser?.user_id === user.user_id) {
      showMessage("error", "You cannot delete your current account.");
      return;
    }

    const confirmed = window.confirm(
      `Remove access for "${user.name}"?\n\n` +
      "If academic or attendance history exists, the account will " +
      "be deactivated and that history will be preserved."
    );

    if (!confirmed) return;

    setStatus({ type: "", message: "" });
    setDeletingUserId(user.user_id);

    try {
      const result = await deleteUser(user.user_id);

      if (!result?.success) {
        showMessage(
          "error",
          result?.message || "Unable to remove this user."
        );
        return;
      }

      if (result.action === "deactivated") {
        setUsers((current) =>
          current.map((item) =>
            item.user_id === user.user_id
              ? { ...item, is_active: false }
              : item
          )
        );

        if (selectedUser?.user_id === user.user_id) {
          setSelectedUser((prev) => ({ ...prev, is_active: false }));
        }

        showMessage(
          "success",
          result.message ||
          "Account deactivated. Academic and attendance history has been preserved."
        );
      } else if (result.action === "deleted") {
        setUsers((current) =>
          current.filter((item) => item.user_id !== user.user_id)
        );

        if (selectedUser?.user_id === user.user_id) {
          setSelectedUser(null);
        }

        showMessage(
          "success",
          result.message || "User permanently deleted."
        );
      } else {
        await loadUsers(true);
        showMessage(
          "success",
          result.message || "User operation completed."
        );
      }
    } catch (error) {
      showMessage(
        "error",
        getApiErrorMessage(error, "Unable to remove this user.")
      );
    } finally {
      setDeletingUserId(null);
    }
  }

  async function handleReactivateUser(user) {
    if (!user?.user_id || isUserActive(user)) return;

    const confirmed = window.confirm(
      `Reactivate "${user.name}"?\n\n` +
      "This will restore login access to the existing account. " +
      "Confirm that this person is authorized to return."
    );

    if (!confirmed) return;

    setStatus({ type: "", message: "" });
    setReactivatingUserId(user.user_id);

    try {
      const result = await reactivateUser(user.user_id);

      if (!result?.success) {
        showMessage(
          "error",
          result?.message || "Unable to reactivate this account."
        );
        return;
      }

      const updatedData = result.data || {};
      setUsers((current) =>
        current.map((item) =>
          item.user_id === user.user_id
            ? {
              ...item,
              ...updatedData,
              is_active: true,
            }
            : item
        )
      );

      if (selectedUser?.user_id === user.user_id) {
        setSelectedUser((prev) => ({
          ...prev,
          ...updatedData,
          is_active: true,
        }));
      }

      showMessage(
        "success",
        result.message ||
        `${user.name}'s account has been reactivated. Previous academic history remains preserved.`
      );
    } catch (error) {
      showMessage(
        "error",
        getApiErrorMessage(
          error,
          "Unable to reactivate this account."
        )
      );
    } finally {
      setReactivatingUserId(null);
    }
  }

  const userCounts = useMemo(() => {
    const active = users.filter(isUserActive).length;

    return {
      total: users.length,
      active,
      inactive: users.length - active,
      students: users.filter((user) => user.role === "STUDENT").length,
      faculty: users.filter((user) => user.role === "FACULTY").length,
      admins: users.filter((user) => user.role === "ADMIN").length,
    };
  }, [users]);

  const uniqueDepartments = useMemo(() => {
    const set = new Set();
    users.forEach((u) => {
      if (u.department && u.department !== "—") {
        set.add(u.department);
      }
    });
    return Array.from(set).sort();
  }, [users]);

  const filteredUsers = useMemo(() => {
    const searchValue = searchTerm.trim().toLowerCase();

    return users.filter((user) => {
      const matchesSearch =
        !searchValue ||
        user.name?.toLowerCase().includes(searchValue) ||
        user.email?.toLowerCase().includes(searchValue) ||
        String(user.user_id).toLowerCase().includes(searchValue) ||
        user.role?.toLowerCase().includes(searchValue) ||
        user.department?.toLowerCase().includes(searchValue);

      const matchesRole =
        roleFilter === "ALL" || user.role === roleFilter;

      const matchesDepartment =
        departmentFilter === "ALL" || user.department === departmentFilter;

      const active = isUserActive(user);
      const matchesStatus =
        statusFilter === "ALL" ||
        (statusFilter === "ACTIVE" && active) ||
        (statusFilter === "INACTIVE" && !active);

      return matchesSearch && matchesRole && matchesDepartment && matchesStatus;
    });
  }, [users, searchTerm, roleFilter, departmentFilter, statusFilter]);

  const totalPages = Math.max(
    1,
    Math.ceil(filteredUsers.length / PAGE_SIZE)
  );

  const safeCurrentPage = Math.min(currentPage, totalPages);

  const paginatedUsers = filteredUsers.slice(
    (safeCurrentPage - 1) * PAGE_SIZE,
    safeCurrentPage * PAGE_SIZE
  );

  const firstVisibleUser =
    filteredUsers.length === 0
      ? 0
      : (safeCurrentPage - 1) * PAGE_SIZE + 1;

  const lastVisibleUser = Math.min(
    safeCurrentPage * PAGE_SIZE,
    filteredUsers.length
  );

  const getPaginationItems = () => {
    if (totalPages <= 5) {
      return Array.from({ length: totalPages }, (_, i) => i + 1);
    }
    const pages = [];
    pages.push(1);
    if (safeCurrentPage > 3) {
      pages.push("ellipsis-1");
    }
    const start = Math.max(2, safeCurrentPage - 1);
    const end = Math.min(totalPages - 1, safeCurrentPage + 1);
    for (let i = start; i <= end; i++) {
      if (!pages.includes(i)) pages.push(i);
    }
    if (safeCurrentPage < totalPages - 2) {
      pages.push("ellipsis-2");
    }
    if (!pages.includes(totalPages)) {
      pages.push(totalPages);
    }
    return pages;
  };

  return (
    <section className="admin-management">
      {/* =====================================================
          1. USER MANAGEMENT BANNER
      ====================================================== */}
      <section className="admin-banner-card">
        <div className="admin-banner-left">
          <div className="admin-banner-icon-box">
            <FontAwesomeIcon icon={faUsers} />
          </div>

          <div className="admin-banner-titles">
            <h1>User Management</h1>
            <p>Manage system accounts, access, and account status.</p>
          </div>
        </div>

        <div className="admin-banner-right">
          <div className="admin-banner-badge">
            <strong>One Campus. Every User. Connected.</strong>
            <span>Unified access management across all academic portals.</span>
          </div>

          <button
            type="button"
            className="admin-banner-add-button"
            onClick={openCreateModal}
          >
            <FontAwesomeIcon icon={faPlus} />
            <span>Add User</span>
          </button>
        </div>
      </section>

      {/* =====================================================
          STATUS MESSAGES
      ====================================================== */}
      {status.message && (
        <div
          className={`admin-form-status admin-form-status-${status.type}`}
          role={status.type === "error" ? "alert" : "status"}
          aria-live="polite"
        >
          <FontAwesomeIcon
            icon={status.type === "success" ? faCheck : faXmark}
          />
          <span>{status.message}</span>
        </div>
      )}

      {/* =====================================================
          2. STATISTICS SUMMARY CARDS (MATCHING SECOND IMAGE)
      ====================================================== */}
      <section className="admin-user-summary">
        {/* 1. Total Users */}
        <article className="admin-summary-card card-total-users">
          <div className="admin-summary-top">
            <div className="admin-summary-icon icon-blue">
              <FontAwesomeIcon icon={faUsers} />
            </div>
            <span className="admin-summary-label">Total Users</span>
          </div>
          <strong className="admin-summary-value">
            {loadingUsers ? "..." : userCounts.total}
          </strong>
          <div className="admin-summary-bottom">
            <div className="admin-summary-trend">
              <span className="trend-stat trend-up">
                ↑ 12%
              </span>
              <span className="trend-period">vs. last month</span>
            </div>
            <svg
              className="admin-summary-sparkline"
              viewBox="0 0 65 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <path
                d="M2 20C12 20 18 16 26 18C34 20 40 12 48 10C54 8 58 5 63 3"
                stroke="#3b82f6"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
        </article>

        {/* 2. Students */}
        <article className="admin-summary-card card-students">
          <div className="admin-summary-top">
            <div className="admin-summary-icon icon-teal">
              <FontAwesomeIcon icon={faUserGraduate} />
            </div>
            <span className="admin-summary-label">Students</span>
          </div>
          <strong className="admin-summary-value">
            {loadingUsers ? "..." : userCounts.students}
          </strong>
          <div className="admin-summary-bottom">
            <div className="admin-summary-trend">
              <span className="trend-stat trend-up">
                ↑ 8%
              </span>
              <span className="trend-period">vs. last month</span>
            </div>
            <svg
              className="admin-summary-sparkline"
              viewBox="0 0 65 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <path
                d="M2 19C10 19 18 17 26 15C34 13 40 17 48 11C54 7 58 6 63 4"
                stroke="#10b981"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
        </article>

        {/* 3. Faculty */}
        <article className="admin-summary-card card-faculty">
          <div className="admin-summary-top">
            <div className="admin-summary-icon icon-purple">
              <FontAwesomeIcon icon={faUserTie} />
            </div>
            <span className="admin-summary-label">Faculty</span>
          </div>
          <strong className="admin-summary-value">
            {loadingUsers ? "..." : userCounts.faculty}
          </strong>
          <div className="admin-summary-bottom">
            <div className="admin-summary-trend">
              <span className="trend-stat trend-up">
                ↑ 6%
              </span>
              <span className="trend-period">vs. last month</span>
            </div>
            <svg
              className="admin-summary-sparkline"
              viewBox="0 0 65 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <path
                d="M2 21C14 21 20 19 28 17C36 15 42 16 50 12C56 9 59 7 63 5"
                stroke="#8b5cf6"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
        </article>

        {/* 4. Administrators */}
        <article className="admin-summary-card card-admins">
          <div className="admin-summary-top">
            <div className="admin-summary-icon icon-amber">
              <FontAwesomeIcon icon={faShieldHalved} />
            </div>
            <span className="admin-summary-label">Administrators</span>
          </div>
          <strong className="admin-summary-value">
            {loadingUsers ? "..." : userCounts.admins}
          </strong>
          <div className="admin-summary-bottom">
            <div className="admin-summary-trend">
              <span className="trend-stat trend-neutral">
                → 0%
              </span>
              <span className="trend-period">vs. last month</span>
            </div>
            <svg
              className="admin-summary-sparkline"
              viewBox="0 0 65 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <path
                d="M2 14C12 14 22 13 32 14C42 15 52 14 63 14"
                stroke="#f59e0b"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
        </article>

        {/* 5. Active Accounts */}
        <article className="admin-summary-card card-active">
          <div className="admin-summary-top">
            <div className="admin-summary-icon icon-green">
              <FontAwesomeIcon icon={faCircleCheck} />
            </div>
            <span className="admin-summary-label">Active Accounts</span>
          </div>
          <strong className="admin-summary-value">
            {loadingUsers ? "..." : userCounts.active}
          </strong>
          <div className="admin-summary-bottom">
            <div className="admin-summary-trend">
              <span className="trend-stat trend-up">
                ↑ 10%
              </span>
              <span className="trend-period">vs. last month</span>
            </div>
            <svg
              className="admin-summary-sparkline"
              viewBox="0 0 65 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <path
                d="M2 20C10 20 16 19 26 16C36 13 42 17 50 11C56 6 59 4 63 3"
                stroke="#22c55e"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
        </article>

        {/* 6. Inactive Accounts */}
        <article className="admin-summary-card card-inactive">
          <div className="admin-summary-top">
            <div className="admin-summary-icon icon-red">
              <FontAwesomeIcon icon={faPowerOff} />
            </div>
            <span className="admin-summary-label">Inactive Accounts</span>
          </div>
          <strong className="admin-summary-value">
            {loadingUsers ? "..." : userCounts.inactive}
          </strong>
          <div className="admin-summary-bottom">
            <div className="admin-summary-trend">
              <span className="trend-stat trend-down">
                ↓ 2%
              </span>
              <span className="trend-period">vs. last month</span>
            </div>
            <svg
              className="admin-summary-sparkline"
              viewBox="0 0 65 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <path
                d="M2 10C12 10 18 12 26 14C34 16 42 12 50 16C56 19 59 20 63 21"
                stroke="#f43f5e"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
        </article>
      </section>

      {/* =====================================================
          3. WORKSPACE: USERS CARD & DETAILS PANEL
      ====================================================== */}
      <div
        className={`admin-workspace-layout ${selectedUser ? "with-details-panel" : "full-width-table"
          }`}
      >
        <section className="admin-users-card">
          <div className="admin-users-toolbar">
            <div className="admin-search-box">
              <FontAwesomeIcon icon={faMagnifyingGlass} />
              <input
                type="search"
                value={searchTerm}
                onChange={handleSearchChange}
                placeholder="Search by name, email, ID or role..."
                aria-label="Search users"
              />
              {searchTerm && (
                <button
                  type="button"
                  className="admin-search-clear-btn"
                  onClick={() => setSearchTerm("")}
                  title="Clear search"
                  aria-label="Clear search"
                >
                  <FontAwesomeIcon icon={faXmark} />
                </button>
              )}
            </div>

            <label className="admin-filter-select">
              <span className="sr-only">Filter by role</span>
              <select
                value={roleFilter}
                onChange={handleRoleFilterChange}
              >
                <option value="ALL">All Roles</option>
                <option value="STUDENT">Students</option>
                <option value="FACULTY">Faculty</option>
                <option value="ADMIN">Admins</option>
              </select>
              <FontAwesomeIcon icon={faChevronDown} />
            </label>

            {uniqueDepartments.length > 0 && (
              <label className="admin-filter-select">
                <span className="sr-only">Filter by department</span>
                <select
                  value={departmentFilter}
                  onChange={handleDepartmentFilterChange}
                >
                  <option value="ALL">All Departments</option>
                  {uniqueDepartments.map((dept) => (
                    <option key={dept} value={dept}>
                      {dept}
                    </option>
                  ))}
                </select>
                <FontAwesomeIcon icon={faChevronDown} />
              </label>
            )}

            <label className="admin-filter-select">
              <span className="sr-only">Filter by status</span>
              <select
                value={statusFilter}
                onChange={handleStatusFilterChange}
              >
                <option value="ALL">All Statuses</option>
                <option value="ACTIVE">Active</option>
                <option value="INACTIVE">Inactive</option>
              </select>
              <FontAwesomeIcon icon={faChevronDown} />
            </label>

            <div className="admin-toolbar-actions">
              {hasActiveFilters && (
                <button
                  type="button"
                  className="admin-reset-button"
                  onClick={handleResetFilters}
                  title="Reset all filters"
                >
                  <FontAwesomeIcon icon={faXmark} />
                  <span>Reset</span>
                </button>
              )}

              <button
                type="button"
                className="admin-action-button admin-refresh-button"
                onClick={() => loadUsers(true)}
                disabled={loadingUsers || refreshingUsers}
                title="Refresh user list"
              >
                <FontAwesomeIcon
                  icon={refreshingUsers ? faSpinner : faRotateRight}
                  spin={refreshingUsers}
                />
                <span>Refresh</span>
              </button>
            </div>
          </div>

          {loadingUsers ? (
            <div className="admin-list-state">
              <FontAwesomeIcon icon={faSpinner} spin />
              <span>Loading users...</span>
            </div>
          ) : filteredUsers.length === 0 ? (
            <div className="admin-list-state">
              <FontAwesomeIcon icon={faUsers} />
              <span>No users match the selected filters.</span>
              {hasActiveFilters && (
                <button
                  type="button"
                  className="admin-reset-link-button"
                  onClick={handleResetFilters}
                >
                  Reset all filters
                </button>
              )}
            </div>
          ) : (
            <>
              <div className="admin-table-wrapper">
                <table className="admin-management-table">
                  <thead>
                    <tr>
                      <th>S.N.</th>
                      <th>Name</th>
                      <th>User ID</th>
                      <th>Email</th>
                      <th>Role</th>
                      <th>Status</th>
                      <th>Last Login</th>
                      <th>Actions</th>
                    </tr>
                  </thead>

                  <tbody>
                    {paginatedUsers.map((user, index) => {
                      const isCurrentUser =
                        currentUser?.user_id === user.user_id;
                      const isSelected =
                        selectedUser?.user_id === user.user_id;
                      const active = isUserActive(user);
                      const busy =
                        deletingUserId === user.user_id ||
                        updatingUserId === user.user_id ||
                        reactivatingUserId === user.user_id;

                      return (
                        <tr
                          key={user.user_id}
                          className={`${!active ? "admin-user-row-inactive" : ""
                            } ${isSelected ? "admin-user-row-selected" : ""}`}
                        >
                          <td>
                            {(safeCurrentPage - 1) * PAGE_SIZE +
                              index +
                              1}
                          </td>

                          <td>
                            <div
                              className="admin-user-name-cell"
                              onClick={() => setSelectedUser(user)}
                              role="button"
                              tabIndex={0}
                              onKeyDown={(e) => {
                                if (e.key === "Enter" || e.key === " ") {
                                  setSelectedUser(user);
                                }
                              }}
                              title="Click to view details"
                            >
                              <div
                                className={`admin-user-avatar admin-avatar-${user.role?.toLowerCase()}`}
                              >
                                {getInitials(user.name)}
                              </div>
                              <div className="admin-user-name-info">
                                <strong>{user.name}</strong>
                                {isCurrentUser && (
                                  <small className="admin-current-user-tag">
                                    Current account
                                  </small>
                                )}
                              </div>
                            </div>
                          </td>

                          <td>
                            <span className="admin-user-id">
                              {user.user_id}
                            </span>
                          </td>

                          <td>
                            <span className="admin-user-email-text" title={user.email}>
                              {user.email}
                            </span>
                          </td>

                          <td>
                            <span
                              className={`admin-role-badge admin-role-${user.role?.toLowerCase()}`}
                            >
                              <FontAwesomeIcon
                                icon={getRoleIcon(user.role)}
                              />
                              {getRoleLabel(user.role)}
                            </span>
                          </td>

                          <td>
                            <span
                              className={`admin-user-status ${active
                                ? "admin-user-status-active"
                                : "admin-user-status-inactive"
                                }`}
                            >
                              {active ? "Active" : "Inactive"}
                            </span>
                          </td>

                          <td>
                            <span className="admin-user-last-login">
                              {formatLastLogin(user.last_login)}
                            </span>
                          </td>

                          <td>
                            <div className="admin-table-actions">
                              <button
                                type="button"
                                className={`admin-action-view ${isSelected ? "active" : ""
                                  }`}
                                onClick={() =>
                                  setSelectedUser(
                                    isSelected ? null : user
                                  )
                                }
                                title="View details"
                                aria-label={`View details for ${user.name}`}
                              >
                                <FontAwesomeIcon icon={faEye} />
                                <span>View</span>
                              </button>

                              <button
                                type="button"
                                className="admin-action-button"
                                onClick={() => openEditModal(user)}
                                disabled={busy}
                                title="Edit user"
                              >
                                Edit
                              </button>

                              {active ? (
                                <button
                                  type="button"
                                  className="admin-action-icon"
                                  onClick={() => handleDeleteUser(user)}
                                  disabled={isCurrentUser || busy}
                                  title={
                                    isCurrentUser
                                      ? "You cannot remove your current account."
                                      : "Deactivate account"
                                  }
                                  aria-label={`Deactivate ${user.name}`}
                                >
                                  {deletingUserId === user.user_id ? (
                                    <FontAwesomeIcon
                                      icon={faSpinner}
                                      spin
                                    />
                                  ) : (
                                    <FontAwesomeIcon icon={faTrash} />
                                  )}
                                </button>
                              ) : (
                                <button
                                  type="button"
                                  className="admin-action-button admin-reactivate-button"
                                  onClick={() => handleReactivateUser(user)}
                                  disabled={busy}
                                  title="Restore login access"
                                >
                                  <FontAwesomeIcon
                                    icon={
                                      reactivatingUserId === user.user_id
                                        ? faSpinner
                                        : faRotateRight
                                    }
                                    spin={
                                      reactivatingUserId === user.user_id
                                    }
                                  />
                                  {reactivatingUserId === user.user_id
                                    ? "Restoring..."
                                    : "Reactivate"}
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              <div className="admin-table-footer">
                <span>
                  Showing <strong>{firstVisibleUser}</strong> to{" "}
                  <strong>{lastVisibleUser}</strong> of{" "}
                  <strong>{filteredUsers.length}</strong> users
                </span>

                <div className="admin-pagination">
                  <button
                    type="button"
                    onClick={() =>
                      setCurrentPage((page) => Math.max(1, page - 1))
                    }
                    disabled={safeCurrentPage === 1}
                    aria-label="Previous page"
                    title="Previous page"
                  >
                    <FontAwesomeIcon icon={faChevronLeft} />
                  </button>

                  {getPaginationItems().map((item) => {
                    if (typeof item === "string") {
                      return (
                        <span
                          key={item}
                          className="admin-pagination-ellipsis"
                        >
                          ...
                        </span>
                      );
                    }
                    return (
                      <button
                        type="button"
                        key={item}
                        className={
                          safeCurrentPage === item ? "active" : ""
                        }
                        onClick={() => setCurrentPage(item)}
                      >
                        {item}
                      </button>
                    );
                  })}

                  <button
                    type="button"
                    onClick={() =>
                      setCurrentPage((page) =>
                        Math.min(totalPages, page + 1)
                      )
                    }
                    disabled={safeCurrentPage === totalPages}
                    aria-label="Next page"
                    title="Next page"
                  >
                    <FontAwesomeIcon icon={faChevronRight} />
                  </button>
                </div>
              </div>
            </>
          )}
        </section>

        {/* =====================================================
            4. SELECTED USER DETAILS PANEL
        ====================================================== */}
        {selectedUser && (
          <aside
            className="admin-user-details-panel"
            aria-label="User details"
          >
            <div className="admin-details-top-bar">
              <span className="admin-details-top-title">User Details</span>
              <button
                type="button"
                className="admin-details-close-btn"
                onClick={() => setSelectedUser(null)}
                title="Close details panel"
                aria-label="Close details panel"
              >
                <FontAwesomeIcon icon={faXmark} />
              </button>
            </div>

            <div className="admin-details-card-body">
              <div className="admin-details-profile-header">
                <div
                  className={`admin-details-avatar admin-avatar-${selectedUser.role?.toLowerCase()}`}
                >
                  {getInitials(selectedUser.name)}
                </div>

                <div className="admin-details-identity">
                  <h3>{selectedUser.name}</h3>
                  <div className="admin-details-badges">
                    <span
                      className={`admin-user-status ${isUserActive(selectedUser)
                        ? "admin-user-status-active"
                        : "admin-user-status-inactive"
                        }`}
                    >
                      {isUserActive(selectedUser) ? "Active" : "Inactive"}
                    </span>
                    <span
                      className={`admin-role-badge admin-role-${selectedUser.role?.toLowerCase()}`}
                    >
                      <FontAwesomeIcon
                        icon={getRoleIcon(selectedUser.role)}
                      />
                      {getRoleLabel(selectedUser.role)}
                    </span>
                  </div>
                  {currentUser?.user_id === selectedUser.user_id && (
                    <span className="admin-current-user-tag">
                      Current Account
                    </span>
                  )}
                </div>
              </div>

              <div className="admin-details-section">
                <h4>Account Information</h4>
                <div className="admin-details-grid">
                  <div className="admin-detail-item">
                    <span className="admin-detail-label">User ID</span>
                    <span className="admin-detail-value admin-user-id">
                      #{selectedUser.user_id}
                    </span>
                  </div>

                  <div className="admin-detail-item">
                    <span className="admin-detail-label">Full Name</span>
                    <span className="admin-detail-value">
                      {selectedUser.name}
                    </span>
                  </div>

                  <div className="admin-detail-item">
                    <span className="admin-detail-label">
                      <FontAwesomeIcon icon={faEnvelope} /> Email
                    </span>
                    <span className="admin-detail-value">
                      {selectedUser.email}
                    </span>
                  </div>

                  <div className="admin-detail-item">
                    <span className="admin-detail-label">Role</span>
                    <span className="admin-detail-value">
                      {getRoleLabel(selectedUser.role)}
                    </span>
                  </div>

                  <div className="admin-detail-item">
                    <span className="admin-detail-label">
                      <FontAwesomeIcon icon={faBuilding} /> Department
                    </span>
                    <span className="admin-detail-value">
                      {selectedUser.department || "—"}
                    </span>
                  </div>

                  <div className="admin-detail-item">
                    <span className="admin-detail-label">
                      <FontAwesomeIcon icon={faPhone} /> Phone
                    </span>
                    <span className="admin-detail-value">
                      {selectedUser.phone || "—"}
                    </span>
                  </div>

                  <div className="admin-detail-item">
                    <span className="admin-detail-label">Member Since</span>
                    <span className="admin-detail-value">
                      {formatDate(selectedUser.created_at)}
                    </span>
                  </div>

                  <div className="admin-detail-item">
                    <span className="admin-detail-label">Last Login</span>
                    <span className="admin-detail-value">
                      {formatLastLogin(selectedUser.last_login)}
                    </span>
                  </div>

                  <div className="admin-detail-item">
                    <span className="admin-detail-label">Last Updated</span>
                    <span className="admin-detail-value">
                      {formatDate(selectedUser.updated_at)}
                    </span>
                  </div>
                </div>
              </div>

              <div className="admin-details-actions">
                <button
                  type="button"
                  className="admin-details-edit-btn"
                  onClick={() => openEditModal(selectedUser)}
                >
                  <FontAwesomeIcon icon={faPenToSquare} />
                  <span>Edit User</span>
                </button>

                {isUserActive(selectedUser) ? (
                  <button
                    type="button"
                    className="admin-details-delete-btn"
                    onClick={() => handleDeleteUser(selectedUser)}
                    disabled={
                      currentUser?.user_id === selectedUser.user_id
                    }
                    title={
                      currentUser?.user_id === selectedUser.user_id
                        ? "You cannot remove your current account."
                        : "Deactivate account"
                    }
                  >
                    <FontAwesomeIcon icon={faTrash} />
                    <span>Deactivate</span>
                  </button>
                ) : (
                  <button
                    type="button"
                    className="admin-details-reactivate-btn"
                    onClick={() => handleReactivateUser(selectedUser)}
                  >
                    <FontAwesomeIcon icon={faRotateRight} />
                    <span>Reactivate</span>
                  </button>
                )}
              </div>
            </div>
          </aside>
        )}
      </div>

      {/* =====================================================
          5. ADD USER MODAL (COMPLETELY PRESERVED)
      ====================================================== */}
      {showCreateModal && (
        <div className="admin-modal-backdrop">
          <div
            className="admin-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="create-user-title"
          >
            <div className="admin-modal-header">
              <div>
                <h2 id="create-user-title">Add User</h2>
                <p>Create a new system login account.</p>
              </div>
              <button
                type="button"
                className="admin-modal-close"
                onClick={closeCreateModal}
                disabled={submitting}
                aria-label="Close"
              >
                <FontAwesomeIcon icon={faXmark} />
              </button>
            </div>

            <form
              className="admin-modal-form"
              onSubmit={handleCreateUser}
            >
              <div className="admin-form-field">
                <label htmlFor="admin-user-name">Full Name</label>
                <input
                  id="admin-user-name"
                  name="name"
                  value={formData.name}
                  onChange={handleCreateChange}
                  placeholder="Enter full name"
                  autoComplete="name"
                  required
                />
              </div>

              <div className="admin-form-field">
                <label htmlFor="admin-user-email">Email</label>
                <input
                  id="admin-user-email"
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={handleCreateChange}
                  placeholder="Enter email address"
                  autoComplete="email"
                  required
                />
              </div>

              <div className="admin-form-field">
                <label htmlFor="admin-user-password">Password</label>
                <input
                  id="admin-user-password"
                  name="password"
                  type="password"
                  value={formData.password}
                  onChange={handleCreateChange}
                  placeholder="Minimum 8 characters"
                  minLength={8}
                  autoComplete="new-password"
                  required
                />
              </div>

              <div className="admin-form-field">
                <label htmlFor="admin-user-confirm-password">
                  Confirm Password
                </label>
                <input
                  id="admin-user-confirm-password"
                  name="confirmPassword"
                  type="password"
                  value={formData.confirmPassword}
                  onChange={handleCreateChange}
                  placeholder="Re-enter password"
                  minLength={8}
                  autoComplete="new-password"
                  required
                />
              </div>

              <div className="admin-form-field">
                <label htmlFor="admin-user-role">Role</label>
                <select
                  id="admin-user-role"
                  name="role"
                  value={formData.role}
                  onChange={handleCreateChange}
                >
                  <option value="STUDENT">Student</option>
                  <option value="FACULTY">Faculty</option>
                  <option value="ADMIN">Admin</option>
                </select>
              </div>

              <div className="admin-modal-actions">
                <button
                  type="button"
                  className="admin-modal-cancel"
                  onClick={closeCreateModal}
                  disabled={submitting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="admin-add-user-button"
                  disabled={submitting}
                >
                  {submitting ? (
                    <>
                      <FontAwesomeIcon icon={faSpinner} spin />
                      Creating...
                    </>
                  ) : (
                    <>
                      <FontAwesomeIcon icon={faPlus} />
                      Create User
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* =====================================================
          6. EDIT USER MODAL (COMPLETELY PRESERVED)
      ====================================================== */}
      {editingUser && (
        <div className="admin-modal-backdrop">
          <div
            className="admin-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="edit-user-title"
          >
            <div className="admin-modal-header">
              <div>
                <h2 id="edit-user-title">Edit User</h2>
                <p>Update the selected user's account.</p>
              </div>
              <button
                type="button"
                className="admin-modal-close"
                onClick={closeEditModal}
                disabled={updatingUserId !== null}
                aria-label="Close"
              >
                <FontAwesomeIcon icon={faXmark} />
              </button>
            </div>

            <form
              className="admin-modal-form"
              onSubmit={handleUpdateUser}
            >
              <div className="admin-form-field">
                <label htmlFor="edit-user-name">Full Name</label>
                <input
                  id="edit-user-name"
                  name="name"
                  value={editFormData.name}
                  onChange={handleEditChange}
                  disabled={updatingUserId !== null}
                  autoComplete="name"
                  required
                />
              </div>

              <div className="admin-form-field">
                <label htmlFor="edit-user-email">Email</label>
                <input
                  id="edit-user-email"
                  name="email"
                  type="email"
                  value={editFormData.email}
                  onChange={handleEditChange}
                  disabled={updatingUserId !== null}
                  autoComplete="email"
                  required
                />
              </div>

              <div className="admin-form-field">
                <label htmlFor="edit-user-role">Role</label>
                <select
                  id="edit-user-role"
                  name="role"
                  value={editFormData.role}
                  onChange={handleEditChange}
                  disabled={
                    updatingUserId !== null ||
                    currentUser?.user_id === editingUser.user_id
                  }
                >
                  <option value="STUDENT">Student</option>
                  <option value="FACULTY">Faculty</option>
                  <option value="ADMIN">Admin</option>
                </select>
              </div>

              <div className="admin-form-field">
                <label htmlFor="edit-user-password">
                  New Password
                </label>
                <input
                  id="edit-user-password"
                  name="password"
                  type="password"
                  value={editFormData.password}
                  onChange={handleEditChange}
                  placeholder="Leave blank to keep current"
                  minLength={8}
                  autoComplete="new-password"
                  disabled={updatingUserId !== null}
                />
              </div>

              <div className="admin-form-field">
                <label htmlFor="edit-user-confirm-password">
                  Confirm New Password
                </label>
                <input
                  id="edit-user-confirm-password"
                  name="confirmPassword"
                  type="password"
                  value={editFormData.confirmPassword}
                  onChange={handleEditChange}
                  placeholder="Re-enter new password"
                  minLength={8}
                  autoComplete="new-password"
                  disabled={updatingUserId !== null}
                />
              </div>

              <div className="admin-modal-actions">
                <button
                  type="button"
                  className="admin-modal-cancel"
                  onClick={closeEditModal}
                  disabled={updatingUserId !== null}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="admin-add-user-button"
                  disabled={updatingUserId !== null}
                >
                  {updatingUserId !== null ? (
                    <>
                      <FontAwesomeIcon icon={faSpinner} spin />
                      Saving...
                    </>
                  ) : (
                    <>
                      <FontAwesomeIcon icon={faCheck} />
                      Save Changes
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  );
}

export default AdminManagement;
