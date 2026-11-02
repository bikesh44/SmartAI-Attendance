import { useState, useEffect } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faHouse,
  faCalendarCheck,
  faChartSimple,
  faClock,
  faChartColumn,
  faCalendarDays,
  faGraduationCap,
  faBookOpen,
  faFileLines,
  faUser,
  faGear,
  faRightFromBracket,
  faBars,
  faChevronDown,
  faChevronUp,
  faBuildingColumns,
} from "@fortawesome/free-solid-svg-icons";
import useAuth from "../hooks/useAuth";
import { getStudentProfile } from "../services/studentService";
import "./StudentLayout.css";

const navigationItems = [
  {
    label: "Dashboard",
    path: "/student",
    icon: faHouse,
    end: true,
  },
  {
    label: "My Classes",
    path: "/student/courses",
    icon: faBookOpen,
  },
  {
    label: "Timetable",
    path: "/student/timetable",
    icon: faCalendarDays,
  },
  {
    label: "Assignments & Notes",
    path: "/student/assignments",
    icon: faFileLines,
  },
  {
    label: "Attendance",
    path: "/student/attendance",
    icon: faCalendarCheck,
    isGroup: true,
    children: [
      {
        label: "Daily Punch",
        path: "/student/attendance",
        icon: faChartSimple,
        end: true,
      },
      {
        label: "Attendance History",
        path: "/student/attendance-history",
        icon: faClock,
      },
      {
        label: "Subject-wise Report",
        path: "/student/reports",
        icon: faChartColumn,
      },
    ],
  },
  {
    label: "Academic Records",
    path: "/student/academic-records",
    icon: faGraduationCap,
    isGroup: true,
    children: [
      {
        label: "Academic Report",
        path: "/student/academic-records",
        icon: faFileLines,
      },
    ],
  },
];

const systemItems = [
  {
    label: "Profile",
    path: "/student/profile",
    icon: faUser,
  },
  {
    label: "Settings",
    path: "/student/settings",
    icon: faGear,
  },
];

function StudentLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const auth = useAuth();
  const loggedInUser = auth?.user;
  const authLoading = auth?.loading;

  const [mobileOpen, setMobileOpen] = useState(false);
  const [profileState, setProfileState] = useState({
    userId: null,
    data: null,
    loading: true,
  });

  const profile =
    loggedInUser?.user_id && loggedInUser.user_id === profileState.userId
      ? profileState.data
      : null;

  const profileLoading =
    Boolean(loggedInUser?.user_id) &&
    loggedInUser.user_id !== profileState.userId
      ? true
      : profileState.loading;

  // Load authenticated student profile
  useEffect(() => {
    let active = true;

    if (!loggedInUser?.user_id) {
      return () => {
        active = false;
      };
    }

    getStudentProfile()
      .then((res) => {
        if (active && res?.success && res.data) {
          setProfileState({
            userId: loggedInUser.user_id,
            data: res.data,
            loading: false,
          });
        } else if (active) {
          setProfileState({
            userId: loggedInUser.user_id,
            data: null,
            loading: false,
          });
        }
      })
      .catch((err) => {
        console.error("Failed to load student profile:", err);
        if (active) {
          setProfileState({
            userId: loggedInUser.user_id,
            data: null,
            loading: false,
          });
        }
      });

    return () => {
      active = false;
    };
  }, [loggedInUser?.user_id]);

  // Keep profile synchronized if navigating back from profile page
  useEffect(() => {
    let active = true;
    if (loggedInUser?.user_id && location.pathname !== "/student/profile") {
      getStudentProfile()
        .then((res) => {
          if (active && res?.success && res.data) {
            setProfileState({
              userId: loggedInUser.user_id,
              data: res.data,
              loading: false,
            });
          }
        })
        .catch(() => {});
    }
    return () => {
      active = false;
    };
  }, [location.pathname, loggedInUser?.user_id]);

  const rawName = profile?.name || loggedInUser?.name || "";
  const studentName = typeof rawName === "string" ? rawName.trim() : "";
  const isLoadingName = authLoading || (profileLoading && !studentName);

  // Determine if current path belongs to groups
  const isAttendanceRoute =
    location.pathname === "/student/attendance" ||
    location.pathname.startsWith("/student/attendance/") ||
    location.pathname.startsWith("/student/daily-punch") ||
    location.pathname.startsWith("/student/attendance-history") ||
    location.pathname.startsWith("/student/reports") ||
    location.pathname.startsWith("/student/subject-wise-report");

  const isAcademicRoute =
    location.pathname === "/student/academic-records" ||
    location.pathname.startsWith("/student/academic-records/") ||
    location.pathname.startsWith("/student/academic-report");

  const [manualOpenGroups, setManualOpenGroups] = useState({});

  const isGroupOpen = (label) => {
    if (manualOpenGroups[label] !== undefined) {
      return manualOpenGroups[label];
    }
    if (label === "Attendance") return isAttendanceRoute;
    if (label === "Academic Records") return isAcademicRoute;
    return false;
  };

  const toggleGroup = (label) => {
    setManualOpenGroups((prev) => ({
      ...prev,
      [label]: !isGroupOpen(label),
    }));
  };

  const handleLogout = async () => {
    try {
      if (auth?.logout) {
        await auth.logout();
      }
    } catch (err) {
      console.error("Logout error:", err);
    } finally {
      navigate("/auth", { replace: true });
    }
  };

  const closeMobileSidebar = () => {
    setMobileOpen(false);
  };

  return (
    <div className="student-layout">
      {/* Mobile Backdrop */}
      {mobileOpen && (
        <button
          type="button"
          className="student-sidebar-overlay"
          onClick={closeMobileSidebar}
          aria-label="Close navigation"
        />
      )}

      {/* Main Sidebar */}
      <aside
        className={`student-sidebar ${
          mobileOpen ? "student-sidebar-open" : ""
        }`}
        aria-label="Student navigation sidebar"
      >
        {/* Branding Section */}
        <div className="student-brand">
          <div className="student-brand-icon">
            <FontAwesomeIcon icon={faBuildingColumns} />
          </div>

          <div className="student-brand-text">
            <span className="student-brand-name">SAMS-FR</span>
            <span className="student-brand-role">Student Portal</span>
          </div>
        </div>

        {/* Navigation Sections */}
        <nav className="student-navigation">
          <div className="student-navigation-section">
            <div className="student-navigation-list">
              {navigationItems.map((item) => {
                if (item.isGroup) {
                  const isOpen = isGroupOpen(item.label);
                  const isCurrentGroupActive =
                    item.label === "Attendance"
                      ? isAttendanceRoute
                      : item.label === "Academic Records"
                      ? isAcademicRoute
                      : false;

                  return (
                    <div key={item.label} className="student-nav-group">
                      <button
                        type="button"
                        className={`student-nav-link student-nav-group-btn ${
                          isCurrentGroupActive ? "student-nav-group-active" : ""
                        }`}
                        onClick={() => toggleGroup(item.label)}
                        aria-expanded={isOpen}
                      >
                        <FontAwesomeIcon icon={item.icon} className="student-nav-icon" />
                        <span className="student-nav-label">{item.label}</span>
                        <FontAwesomeIcon
                          icon={isOpen ? faChevronUp : faChevronDown}
                          className="student-nav-chevron"
                        />
                      </button>

                      {isOpen && (
                        <div className="student-nav-tree-wrap">
                          {/* Vertical Connector Tree Line */}
                          <div className="student-tree-line" />

                          <div className="student-nav-sublist">
                            {item.children.map((subItem) => {
                              // Check if sub-item is active
                              const isSubActive =
                                subItem.path === "/student/attendance"
                                  ? location.pathname === "/student/attendance" ||
                                    location.pathname === "/student/daily-punch"
                                  : subItem.path === "/student/reports"
                                  ? location.pathname === "/student/reports" ||
                                    location.pathname === "/student/subject-wise-report" ||
                                    location.pathname === "/student/attendance/subject-wise"
                                  : subItem.path === "/student/academic-records"
                                  ? location.pathname === "/student/academic-records" ||
                                    location.pathname === "/student/academic-report"
                                  : location.pathname.startsWith(subItem.path);

                              return (
                                <NavLink
                                  key={subItem.path}
                                  to={subItem.path}
                                  end={subItem.end}
                                  onClick={closeMobileSidebar}
                                  className={`student-subnav-link ${
                                    isSubActive ? "student-subnav-link-active" : ""
                                  }`}
                                >
                                  {/* Connector Node Dot */}
                                  <span
                                    className={`student-tree-dot ${
                                      isSubActive ? "tree-dot-active" : ""
                                    }`}
                                  />

                                  <FontAwesomeIcon
                                    icon={subItem.icon}
                                    className="student-subnav-icon"
                                  />
                                  <span className="student-subnav-label">{subItem.label}</span>
                                </NavLink>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                }

                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    end={item.end}
                    onClick={closeMobileSidebar}
                    className={({ isActive }) =>
                      `student-nav-link ${
                        isActive ? "student-nav-link-active" : ""
                      }`
                    }
                  >
                    <FontAwesomeIcon icon={item.icon} className="student-nav-icon" />
                    <span className="student-nav-label">{item.label}</span>
                    {item.hasChevron && (
                      <FontAwesomeIcon
                        icon={faChevronDown}
                        className="student-nav-chevron-muted"
                      />
                    )}
                  </NavLink>
                );
              })}

              {/* System Section Items */}
              {systemItems.map((item) => (
                <NavLink
                  key={item.path}
                  to={item.path}
                  onClick={closeMobileSidebar}
                  className={({ isActive }) =>
                    `student-nav-link ${
                      isActive ? "student-nav-link-active" : ""
                    }`
                  }
                >
                  <FontAwesomeIcon icon={item.icon} className="student-nav-icon" />
                  <span className="student-nav-label">{item.label}</span>
                </NavLink>
              ))}
            </div>
          </div>
        </nav>

        {/* Bottom Logout Button */}
        <div className="student-sidebar-footer">
          <button
            type="button"
            className="student-logout-button"
            onClick={handleLogout}
            aria-label="Log out of student portal"
          >
            <FontAwesomeIcon icon={faRightFromBracket} />
            <span>Logout</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="student-main">
        {/* Top Header */}
        <header className="student-topbar">
          <div className="student-topbar-left">
            <button
              type="button"
              className="student-mobile-menu"
              onClick={() => setMobileOpen(true)}
              aria-label="Open navigation menu"
            >
              <FontAwesomeIcon icon={faBars} />
            </button>

          </div>

          <div className="student-topbar-right">
            {/* Student Profile Pill */}
            <button
              type="button"
              className="student-profile-summary"
              onClick={() => navigate("/student/profile")}
              aria-label={studentName ? `View profile for ${studentName}` : "View student profile"}
            >
              <span className="student-avatar-generic">
                <FontAwesomeIcon icon={faUser} />
              </span>

              <span className="student-profile-text">
                {isLoadingName ? (
                  <>
                    <strong>Loading...</strong>
                    <small>Student</small>
                  </>
                ) : studentName ? (
                  <>
                    <strong title={studentName}>{studentName}</strong>
                    <small>Student</small>
                  </>
                ) : (
                  <strong>Student</strong>
                )}
              </span>

              <FontAwesomeIcon icon={faChevronDown} className="student-profile-chevron" />
            </button>
          </div>
        </header>

        {/* Page Content Rendered via Outlet */}
        <main className="student-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default StudentLayout;
