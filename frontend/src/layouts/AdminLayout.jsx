
import { useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faBookOpen,
  faBuilding,
  faCalendarDays,
  faCamera,
  faChartColumn,
  faChartLine,
  faChevronDown,
  faChevronRight,
  faChalkboardUser,
  faClipboardCheck,
  faGear,
  faGraduationCap,
  faRightFromBracket,
  faSchool,
  faUser,
  faUsers,
} from "@fortawesome/free-solid-svg-icons";
import {
  NavLink,
  Outlet,
  useLocation,
  useNavigate,
} from "react-router-dom";

import useAuth from "../hooks/useAuth";

import "./AdminLayout.css";

const studentManagementItems = [
  {
    label: "Students",
    path: "/admin/students",
    icon: faGraduationCap,
    end: true,
  },
  {
    label: "Face Registration",
    path: "/admin/face-registration",
    icon: faCamera,
  },
];



const academicItems = [
  {
    label: "Courses",
    path: "/admin/academic-management/courses",
    icon: faBookOpen,
  },
  {
    label: "Course Offerings",
    path: "/admin/academic-management/course-offerings",
    icon: faBookOpen,
  },
  {
    label: "Course Enrollments",
    path: "/admin/academic-management/course-enrollments",
    icon: faGraduationCap,
  },
  {
    label: "Batches",
    path: "/admin/batches",
    icon: faSchool,
  },
  {
    label: "Assignments",
    path: "/admin/academic-management/assignments",
    icon: faBookOpen,
  },
  {
    label: "Academic Results",
    path: "/admin/academic-management/results",
    icon: faClipboardCheck,
  },
];

const timetableItems = [
  {
    label: "Timetable",
    path: "/admin/timetable",
    icon: faCalendarDays,
    end: true,
  },
  {
    label: "Faculty Adjustment",
    path: "/admin/timetable/faculty-adjustment",
    icon: faUsers,
  },
];

const systemItems = [
  {
    label: "Profile",
    path: "/admin/profile",
    icon: faUser,
  },
  {
    label: "Settings",
    path: "/admin/settings",
    icon: faGear,
  },
];

function getInitials(name) {
  if (!name) return "AD";
  const cleanName = name
    .replace(/^(dr\.|dr|prof\.|prof|mr\.|mr|mrs\.|mrs|ms\.|ms)\s+/i, "")
    .trim();
  const parts = cleanName.split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "AD";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function AdminLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const displayName =
    user?.name ||
    user?.full_name ||
    user?.fullName ||
    user?.username ||
    (user?.email ? user.email.split("@")[0] : "Admin");
  const initials = getInitials(displayName);
  const userRole = user?.role
    ? user.role.charAt(0).toUpperCase() + user.role.slice(1)
    : "Administrator";

  const pathname = location.pathname;

  // Determine which navigation groups match the current route.
  const isAddUserRoute =
    pathname === "/admin/management" ||
    pathname.startsWith("/admin/management") ||
    pathname === "/admin/add-user" ||
    pathname.startsWith("/admin/add-user");

  const isStudentManagementRoute =
    pathname === "/admin/students" ||
    pathname.startsWith("/admin/students") ||
    pathname === "/admin/face-registration" ||
    pathname.startsWith("/admin/face-registration");

  const isFacultyManagementRoute =
    pathname === "/admin/faculty" ||
    pathname.startsWith("/admin/faculty");

  const isUserManagementRoute =
    isAddUserRoute || isStudentManagementRoute || isFacultyManagementRoute;

  const isAcademicRoute =
    pathname.startsWith("/admin/academic-management") ||
    pathname === "/admin/batches" ||
    pathname === "/admin/assignments";

  const isAttendanceRoute =
    pathname.startsWith("/admin/attendance-reports") ||
    pathname.startsWith("/admin/attendance");

  const isTimetableRoute =
    pathname.startsWith("/admin/timetable");

  // null means follow the current route automatically.
  // true/false means the user has manually toggled the group.
  const [userManagementManualOpen, setUserManagementManualOpen] =
    useState(null);

  const [studentManagementManualOpen, setStudentManagementManualOpen] =
    useState(null);

  const [academicManualOpen, setAcademicManualOpen] =
    useState(null);

  const [attendanceManualOpen, setAttendanceManualOpen] =
    useState(null);

  const [timetableManualOpen, setTimetableManualOpen] =
    useState(null);

  const userManagementOpen =
    userManagementManualOpen ?? isUserManagementRoute;

  const studentManagementOpen =
    studentManagementManualOpen ?? isStudentManagementRoute;

  const academicOpen =
    academicManualOpen ?? isAcademicRoute;

  const attendanceOpen =
    attendanceManualOpen ?? isAttendanceRoute;

  const timetableOpen =
    timetableManualOpen ?? isTimetableRoute;


  async function handleLogout() {
    try {
      await logout();
    } finally {
      navigate("/auth", { replace: true });
    }
  }

  function handleUserManagementToggle() {
    setUserManagementManualOpen((current) =>
      !(current ?? isUserManagementRoute)
    );
  }

  function handleStudentManagementToggle(e) {
    if (e && e.stopPropagation) {
      e.stopPropagation();
    }
    setStudentManagementManualOpen((current) =>
      !(current ?? isStudentManagementRoute)
    );
  }

  function handleAcademicToggle() {
    setAcademicManualOpen((current) =>
      !(current ?? isAcademicRoute)
    );
  }

  function handleAttendanceToggle() {
    setAttendanceManualOpen((current) =>
      !(current ?? isAttendanceRoute)
    );
  }

  function handleTimetableToggle() {
    setTimetableManualOpen((current) =>
      !(current ?? isTimetableRoute)
    );
  }

  function getGroupClass(isActive) {
    return [
      "admin-nav-link",
      "admin-nav-group-button",
      isActive ? "parent-active" : "",
    ]
      .filter(Boolean)
      .join(" ");
  }

  function getNavClass({ isActive }) {
    return `admin-nav-link ${isActive ? "active" : ""}`;
  }

  function getSubNavClass({ isActive }) {
    return `admin-subnav-link ${isActive ? "active" : ""}`;
  }

  function getAddUserNavClass({ isActive }) {
    return `admin-subnav-link ${isActive || isAddUserRoute ? "active" : ""}`;
  }

  return (
    <div className="admin-layout">
      {/* Sidebar */}
      <aside className="admin-sidebar">
        <div className="admin-sidebar-top">
          <div className="admin-brand">
            <div className="admin-brand-mark">
              <FontAwesomeIcon icon={faSchool} />
            </div>

            <div className="admin-brand-content">
              <strong>SAMS-FR</strong>
              <span>Admin Portal</span>
            </div>
          </div>
        </div>

        <nav
          className="admin-navigation"
          aria-label="Admin navigation"
        >
          <div className="admin-nav-list">
            {/* Dashboard */}
            <NavLink
              to="/admin/dashboard"
              end
              className={getNavClass}
            >
              <span className="admin-nav-icon">
                <FontAwesomeIcon icon={faChartLine} />
              </span>

              <span className="admin-nav-label">
                Dashboard
              </span>
            </NavLink>

            {/* User Management (Top-level Parent Menu) */}
            <div className="admin-nav-group">
              <button
                type="button"
                className={getGroupClass(isUserManagementRoute)}
                onClick={handleUserManagementToggle}
                aria-expanded={userManagementOpen}
              >
                <span className="admin-nav-icon">
                  <FontAwesomeIcon icon={faUsers} />
                </span>

                <span className="admin-nav-label">
                  User Management
                </span>

                <span className="admin-nav-chevron">
                  <FontAwesomeIcon
                    icon={
                      userManagementOpen
                        ? faChevronDown
                        : faChevronRight
                    }
                  />
                </span>
              </button>

              {userManagementOpen && (
                <div className="admin-subnav">
                  {/* User Management navigation item */}
                  <NavLink
                    to="/admin/management"
                    className={getAddUserNavClass}
                  >
                    <span className="admin-subnav-icon">
                      <FontAwesomeIcon icon={faUsers} />
                    </span>

                    <span>User</span>
                  </NavLink>

                  {/* Student Management (Subgroup) */}
                  <div className="admin-nav-nested-group">
                    <button
                      type="button"
                      className={`admin-subnav-group-button ${
                        isStudentManagementRoute ? "parent-active" : ""
                      }`}
                      onClick={handleStudentManagementToggle}
                      aria-expanded={studentManagementOpen}
                    >
                      <span className="admin-subnav-group-left">
                        <span className="admin-subnav-icon">
                          <FontAwesomeIcon icon={faGraduationCap} />
                        </span>
                        <span>Student Management</span>
                      </span>

                      <span className="admin-subnav-chevron">
                        <FontAwesomeIcon
                          icon={
                            studentManagementOpen
                              ? faChevronDown
                              : faChevronRight
                          }
                        />
                      </span>
                    </button>

                    {studentManagementOpen && (
                      <div className="admin-nested-subnav">
                        {studentManagementItems.map((item) => (
                          <NavLink
                            key={item.label}
                            to={item.path}
                            end={item.end}
                            className={getSubNavClass}
                          >
                            <span className="admin-subnav-icon">
                              <FontAwesomeIcon icon={item.icon} />
                            </span>

                            <span>{item.label}</span>
                          </NavLink>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Faculty Management (Sibling under User Management) */}
                  <NavLink
                    to="/admin/faculty"
                    className={getSubNavClass}
                  >
                    <span className="admin-subnav-icon">
                      <FontAwesomeIcon icon={faChalkboardUser} />
                    </span>

                    <span>Faculty Management</span>
                  </NavLink>
                </div>
              )}
            </div>

            {/* Departments */}
            <NavLink
              to="/admin/departments"
              className={getNavClass}
            >
              <span className="admin-nav-icon">
                <FontAwesomeIcon icon={faBuilding} />
              </span>

              <span className="admin-nav-label">
                Departments
              </span>
            </NavLink>

            {/* Academic Management */}
            <div className="admin-nav-group">
              <button
                type="button"
                className={getGroupClass(isAcademicRoute)}
                onClick={handleAcademicToggle}
                aria-expanded={academicOpen}
              >
                <span className="admin-nav-icon">
                  <FontAwesomeIcon icon={faBookOpen} />
                </span>

                <span className="admin-nav-label">
                  Academic Management
                </span>

                <span className="admin-nav-chevron">
                  <FontAwesomeIcon
                    icon={
                      academicOpen
                        ? faChevronDown
                        : faChevronRight
                    }
                  />
                </span>
              </button>

              {academicOpen && (
                <div className="admin-subnav">
                  {academicItems.map((item) => (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      end
                      className={getSubNavClass}
                    >
                      <span className="admin-subnav-icon">
                        <FontAwesomeIcon icon={item.icon} />
                      </span>

                      <span>{item.label}</span>
                    </NavLink>
                  ))}
                </div>
              )}
            </div>

            {/* Timetable Management */}
            <div className="admin-nav-group">
              <button
                type="button"
                className={getGroupClass(isTimetableRoute)}
                onClick={handleTimetableToggle}
                aria-expanded={timetableOpen}
              >
                <span className="admin-nav-icon">
                  <FontAwesomeIcon icon={faCalendarDays} />
                </span>

                <span className="admin-nav-label">
                  Timetable Management
                </span>

                <span className="admin-nav-chevron">
                  <FontAwesomeIcon
                    icon={
                      timetableOpen
                        ? faChevronDown
                        : faChevronRight
                    }
                  />
                </span>
              </button>

              {timetableOpen && (
                <div className="admin-subnav">
                  {timetableItems.map((item) => (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      end={item.end}
                      className={getSubNavClass}
                    >
                      <span className="admin-subnav-icon">
                        <FontAwesomeIcon icon={item.icon} />
                      </span>

                      <span>{item.label}</span>
                    </NavLink>
                  ))}
                </div>
              )}
            </div>

            {/* Reports & Analytics */}
            <div className="admin-nav-group">
              <button
                type="button"
                className={getGroupClass(isAttendanceRoute)}
                onClick={handleAttendanceToggle}
                aria-expanded={attendanceOpen}
              >
                <span className="admin-nav-icon">
                  <FontAwesomeIcon icon={faChartColumn} />
                </span>

                <span className="admin-nav-label">
                  Reports & Analytics
                </span>

                <span className="admin-nav-chevron">
                  <FontAwesomeIcon
                    icon={
                      attendanceOpen
                        ? faChevronDown
                        : faChevronRight
                    }
                  />
                </span>
              </button>

              {attendanceOpen && (
                <div className="admin-subnav">
                  <NavLink
                    to="/admin/attendance-reports"
                    className={getSubNavClass}
                  >
                    <span>Attendance Reports</span>
                  </NavLink>

                  <span className="admin-subnav-link admin-subnav-disabled" title="Academic Reports">
                    <span>Academic Reports</span>
                  </span>

                  <span className="admin-subnav-link admin-subnav-disabled" title="System Reports">
                    <span>System Reports</span>
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* System */}
          <p className="admin-nav-title admin-nav-title-system">
            SYSTEM
          </p>

          <div className="admin-nav-list">
            {systemItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                end
                className={getNavClass}
              >
                <span className="admin-nav-icon">
                  <FontAwesomeIcon icon={item.icon} />
                </span>

                <span className="admin-nav-label">
                  {item.label}
                </span>
              </NavLink>
            ))}

            <button
              type="button"
              className="admin-nav-link admin-logout-button"
              onClick={handleLogout}
            >
              <span className="admin-nav-icon admin-logout-icon">
                <FontAwesomeIcon icon={faRightFromBracket} />
              </span>

              <span className="admin-nav-label">
                Logout
              </span>
            </button>
          </div>
        </nav>
      </aside>

      {/* Main content */}
      <div className="admin-content">
        <header className="admin-header">
          <div className="admin-header-actions">
            <div className="admin-user-pill">
              <div className="admin-user-avatar">
                <span>{initials}</span>
              </div>

              <div className="admin-user-info">
                <strong>{displayName}</strong>
                <span>{userRole}</span>
              </div>
            </div>
          </div>
        </header>

        <main className="admin-main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default AdminLayout;
