import { useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  GraduationCap,
  Home,
  Calendar,
  SquareCheck,
  Users,
  BarChart3,
  User,
  FileSpreadsheet,
  FileText,
  ChevronDown,
  LogOut,
  Menu,
  X,
  Settings,
} from "lucide-react";
import useAuth from "../hooks/useAuth";
import "./FacultyLayout.css";

const navigationItems = [
  {
    label: "Dashboard",
    path: "/faculty",
    icon: <Home size={19} strokeWidth={2.2} />,
  },
  {
    label: "My Classes",
    path: "/faculty/classes",
    icon: <Calendar size={19} strokeWidth={2.2} />,
  },
  {
    label: "Attendance",
    path: "/faculty/attendance",
    icon: <SquareCheck size={19} strokeWidth={2.2} />,
  },
  {
    label: "Students",
    path: "/faculty/students",
    icon: <Users size={19} strokeWidth={2.2} />,
  },
  {
    label: "Assignment & Notes",
    path: "/faculty/assignments",
    icon: <FileText size={19} strokeWidth={2.2} />,
  },
  {
    label: "Reports",
    path: "/faculty/reports",
    icon: <BarChart3 size={19} strokeWidth={2.2} />,
  },
  {
    label: "Result Upload",
    path: "/faculty/results",
    icon: <FileSpreadsheet size={19} strokeWidth={2.2} />,
  },
  {
    label: "My Profile",
    path: "/faculty/profile",
    icon: <User size={19} strokeWidth={2.2} />,
  },
  {
    label: "Settings",
    path: "/faculty/settings",
    icon: <Settings size={19} strokeWidth={2.2} />,
  },
];

function getDisplayName(user) {
  if (!user || typeof user !== "object") return "Faculty Member";

  const fullName =
    user.full_name ||
    user.fullName ||
    user.name ||
    [user.first_name, user.last_name].filter(Boolean).join(" ") ||
    [user.firstName, user.lastName].filter(Boolean).join(" ");

  return typeof fullName === "string" && fullName.trim()
    ? fullName.trim()
    : "Faculty Member";
}

function getInitials(name) {
  if (!name || name === "Faculty Member") return "FM";
  return (
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part.charAt(0).toUpperCase())
      .join("") || "FM"
  );
}

function FacultyLayout() {
  const auth = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileNavigationOpen, setMobileNavigationOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);

  const user = auth?.user;
  const displayName = getDisplayName(user);
  const initials = getInitials(displayName);

  async function handleLogout() {
    if (loggingOut) return;

    setLoggingOut(true);

    try {
      if (auth?.logout) {
        await auth.logout();
      }
      navigate("/auth", { replace: true });
    } catch (error) {
      console.error("Faculty logout failed:", error);
      setLoggingOut(false);
    }
  }

  function closeMobileNavigation() {
    setMobileNavigationOpen(false);
  }

  const isItemActive = (itemPath) => {
    if (itemPath === "/faculty") {
      return (
        location.pathname === "/faculty" ||
        location.pathname === "/faculty/" ||
        location.pathname === "/faculty/dashboard"
      );
    }
    return (
      location.pathname === itemPath ||
      location.pathname.startsWith(`${itemPath}/`)
    );
  };

  return (
    <div className="faculty-layout">
      {mobileNavigationOpen && (
        <button
          type="button"
          className="faculty-mobile-backdrop"
          aria-label="Close navigation"
          onClick={closeMobileNavigation}
        />
      )}

      {/* Left Sidebar */}
      <aside
        className={`faculty-sidebar${mobileNavigationOpen ? " faculty-sidebar-open" : ""}`}
        aria-label="Faculty sidebar"
      >
        <NavLink
          to="/faculty"
          className="faculty-brand"
          aria-label="SAMS-FR Faculty Dashboard"
          onClick={closeMobileNavigation}
        >
          <div className="faculty-brand-icon-wrap" aria-hidden="true">
            <GraduationCap size={26} strokeWidth={2.4} color="#ffffff" />
          </div>

          <div className="faculty-brand-copy">
            <strong>SAMS-FR</strong>
            <span>Face Recognition Attendance System</span>
          </div>
        </NavLink>

        <nav className="faculty-navigation" aria-label="Faculty navigation">
          <div className="faculty-navigation-list">
            {navigationItems.map((item) => {
              const active = isItemActive(item.path);
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  onClick={closeMobileNavigation}
                  className={`faculty-nav-link${active ? " active" : ""}`}
                >
                  <span className="faculty-nav-icon">{item.icon}</span>
                  <span className="faculty-nav-text">{item.label}</span>
                </NavLink>
              );
            })}
          </div>
        </nav>

        {/* Bottom Sidebar Logout Button */}
        <div className="faculty-sidebar-bottom">
          <button
            type="button"
            className="faculty-sidebar-logout-btn"
            onClick={handleLogout}
            disabled={loggingOut}
            aria-label="Logout"
            title="Logout"
          >
            <LogOut size={17} strokeWidth={2.2} className="faculty-sidebar-logout-icon" />
            <span>{loggingOut ? "Logging out..." : "Logout"}</span>
          </button>

          <div className="faculty-sidebar-version">v1.0.0</div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="faculty-main">
        {/* Top Header Bar */}
        <header className="faculty-topbar">
          <div className="faculty-topbar-left">
            <button
              type="button"
              className="faculty-mobile-menu-button"
              aria-label={mobileNavigationOpen ? "Close menu" : "Open menu"}
              aria-expanded={mobileNavigationOpen}
              onClick={() => setMobileNavigationOpen((open) => !open)}
            >
              {mobileNavigationOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>

          <div className="faculty-topbar-right">
            {/* User Profile Pill */}
            <div className="faculty-user-profile-menu">
              <NavLink
                to="/faculty/profile"
                className="faculty-user"
                aria-label={`View profile for ${displayName}`}
              >
                <div className="faculty-user-avatar" aria-hidden="true">
                  {initials}
                </div>

                <div className="faculty-user-info">
                  <strong>{displayName}</strong>
                  <span>Faculty</span>
                </div>

                <ChevronDown size={16} className="faculty-user-chevron" aria-hidden="true" />
              </NavLink>
            </div>
          </div>
        </header>

        {/* Main Workspace Body */}
        <main className="faculty-content" id="faculty-main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default FacultyLayout;
