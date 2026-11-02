import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faBell,
  faBookOpen,
  faCircleInfo,
  faEye,
  faGear,
  faLock,
  faPalette,
  faShieldHalved,
  faSliders,
  faSun,
  faUser,
} from "@fortawesome/free-solid-svg-icons";
import useAppearance from "../../hooks/useAppearance";
import { getCurrentUser } from "../../services/authService";
import { getStudentFaceProfile } from "../../services/faceProfileService";
import "./Settings.css";

const DEFAULT_SETTINGS = {
  attendanceView: "course",
  attendanceAlerts: true,
  lowAttendanceWarning: true,
  reportAvailability: true,
  courseScheduleUpdates: true,
  systemAnnouncements: true,
};

function Settings() {
  const {
    theme,
    setTheme,
    sidebarMode,
    setSidebarMode,
  } = useAppearance();

  const [settings, setSettings] = useState(() => {
    const storedSettings = localStorage.getItem("studentPortalSettings");

    if (!storedSettings) {
      return DEFAULT_SETTINGS;
    }

    try {
      return {
        ...DEFAULT_SETTINGS,
        ...JSON.parse(storedSettings),
      };
    } catch {
      localStorage.removeItem("studentPortalSettings");
      return DEFAULT_SETTINGS;
    }
  });

  const [currentUser, setCurrentUser] = useState(null);
  const [userLoading, setUserLoading] = useState(true);
  const [userError, setUserError] = useState("");
  const [faceProfileStatus, setFaceProfileStatus] = useState("Checking...");

  const [savedMessage, setSavedMessage] = useState("");

  useEffect(() => {
    let isMounted = true;

    async function loadCurrentUser() {
      try {
        setUserLoading(true);
        setUserError("");

        const result = await getCurrentUser();

        if (!result?.success || !result?.data) {
          throw new Error(
            result?.message || "Unable to load account information.",
          );
        }

        if (result.data.role !== "STUDENT") {
          throw new Error("This account is not a student account.");
        }

        if (isMounted) {
          setCurrentUser(result.data);
        }
      } catch (error) {
        if (isMounted) {
          setCurrentUser(null);
          setUserError(
            error?.response?.data?.message ||
              error?.message ||
              "Unable to load account information.",
          );
        }
      } finally {
        if (isMounted) {
          setUserLoading(false);
        }
      }
    }

    loadCurrentUser();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    let isMounted = true;

    async function loadFaceProfile() {
      try {
        const result = await getStudentFaceProfile();

        if (!result?.success || !result?.data) {
          throw new Error(
            result?.message || "Face profile not found.",
          );
        }

        if (isMounted) {
          setFaceProfileStatus(
            result.data.is_active ? "Registered" : "Inactive",
          );
        }
      } catch (error) {
        if (isMounted) {
          if (error?.response?.status === 404) {
            setFaceProfileStatus("Not Registered");
          } else {
            setFaceProfileStatus("Unavailable");
          }
        }
      }
    }

    loadFaceProfile();

    return () => {
      isMounted = false;
    };
  }, []);

  const showSavedMessage = (message) => {
    setSavedMessage(message);

    window.setTimeout(() => {
      setSavedMessage("");
    }, 1800);
  };

  const updateSetting = (key, value) => {
    const updatedSettings = {
      ...settings,
      [key]: value,
    };

    setSettings(updatedSettings);

    localStorage.setItem(
      "studentPortalSettings",
      JSON.stringify(updatedSettings),
    );

    showSavedMessage("Settings saved");
  };

  const resetSettings = () => {
    setSettings(DEFAULT_SETTINGS);

    setTheme("light");
    setSidebarMode("expanded");

    localStorage.setItem(
      "studentPortalSettings",
      JSON.stringify(DEFAULT_SETTINGS),
    );

    showSavedMessage("Settings restored to defaults");
  };

  const handleThemeChange = (event) => {
    setTheme(event.target.value);
    showSavedMessage("Theme saved");
  };

  const handleSidebarChange = (event) => {
    setSidebarMode(event.target.value);
    showSavedMessage("Sidebar preference saved");
  };

  const roleLabel =
    currentUser?.role === "STUDENT"
      ? "Student"
      : currentUser?.role || "N/A";

  return (
    <section className="student-settings">
      <div className="student-settings-header">
        <div>
          <span className="student-settings-eyebrow">
            PORTAL PREFERENCES
          </span>

          <h1>Settings</h1>

          <p>
            Manage your student portal preferences, notifications and display
            settings.
          </p>
        </div>

        <div className="student-settings-status">
          <span className="student-settings-status-dot" />
          System Operational
        </div>
      </div>

      {savedMessage && (
        <div className="student-settings-save-message" role="status">
          {savedMessage}
        </div>
      )}

      {/* Appearance */}
      <section className="student-settings-card">
        <div className="student-settings-card-header">
          <div className="student-settings-section-icon">
            <FontAwesomeIcon icon={faPalette} />
          </div>

          <div>
            <h2>Appearance</h2>
            <p>Customize how the student portal looks and behaves.</p>
          </div>
        </div>

        <div className="student-settings-options">
          <div className="student-settings-option">
            <div className="student-settings-option-info">
              <FontAwesomeIcon icon={faSun} />

              <div>
                <strong>Theme</strong>
                <span>Choose the appearance of your portal.</span>
              </div>
            </div>

            <select
              value={theme}
              onChange={handleThemeChange}
              aria-label="Theme"
            >
              <option value="light">Light</option>
              <option value="dark">Dark</option>
              <option value="system">System</option>
            </select>
          </div>

          <div className="student-settings-option">
            <div className="student-settings-option-info">
              <FontAwesomeIcon icon={faSliders} />

              <div>
                <strong>Sidebar</strong>
                <span>Choose your preferred sidebar layout.</span>
              </div>
            </div>

            <select
              value={sidebarMode}
              onChange={handleSidebarChange}
              aria-label="Sidebar layout"
            >
              <option value="expanded">Expanded</option>
              <option value="compact">Compact</option>
            </select>
          </div>
        </div>
      </section>

      {/* Attendance Preferences */}
      <section className="student-settings-card">
        <div className="student-settings-card-header">
          <div className="student-settings-section-icon">
            <FontAwesomeIcon icon={faBookOpen} />
          </div>

          <div>
            <h2>Attendance Preferences</h2>
            <p>
              Control how attendance information is displayed in your portal.
            </p>
          </div>
        </div>

        <div className="student-settings-options">
          <div className="student-settings-option">
            <div className="student-settings-option-info">
              <FontAwesomeIcon icon={faEye} />

              <div>
                <strong>Default Attendance View</strong>
                <span>
                  Choose the view shown when opening attendance.
                </span>
              </div>
            </div>

            <select
              value={settings.attendanceView}
              onChange={(event) =>
                updateSetting("attendanceView", event.target.value)
              }
              aria-label="Default attendance view"
            >
              <option value="overview">Overview</option>
              <option value="course">Course-wise</option>
              <option value="history">Attendance History</option>
            </select>
          </div>

          <SettingToggle
            label="Attendance Alerts"
            description="Highlight important attendance-related notifications."
            checked={settings.attendanceAlerts}
            onChange={(value) => updateSetting("attendanceAlerts", value)}
            icon={faBell}
          />

          <SettingToggle
            label="Low Attendance Warning"
            description="Show warnings when your attendance requires attention."
            checked={settings.lowAttendanceWarning}
            onChange={(value) =>
              updateSetting("lowAttendanceWarning", value)
            }
            icon={faShieldHalved}
          />

          <div className="student-settings-info-row">
            <div>
              <strong>Warning Threshold</strong>

              <span>
                Attendance thresholds are configured by the institution.
              </span>
            </div>

            <span className="student-settings-readonly">
              Institution configured
            </span>
          </div>
        </div>
      </section>

      {/* Notifications */}
      <section className="student-settings-card">
        <div className="student-settings-card-header">
          <div className="student-settings-section-icon">
            <FontAwesomeIcon icon={faBell} />
          </div>

          <div>
            <h2>Notifications</h2>
            <p>
              Choose which student portal notifications you want to see.
            </p>
          </div>
        </div>

        <div className="student-settings-options">
          <SettingToggle
            label="Attendance Alerts"
            description="Receive notifications related to attendance records."
            checked={settings.attendanceAlerts}
            onChange={(value) => updateSetting("attendanceAlerts", value)}
            icon={faBell}
          />

          <SettingToggle
            label="Report Availability"
            description="Notify when attendance reports become available."
            checked={settings.reportAvailability}
            onChange={(value) =>
              updateSetting("reportAvailability", value)
            }
            icon={faBookOpen}
          />

          <SettingToggle
            label="Course & Schedule Updates"
            description="Show updates related to courses and schedules."
            checked={settings.courseScheduleUpdates}
            onChange={(value) =>
              updateSetting("courseScheduleUpdates", value)
            }
            icon={faGear}
          />

          <SettingToggle
            label="System Announcements"
            description="Show important announcements from the institution."
            checked={settings.systemAnnouncements}
            onChange={(value) =>
              updateSetting("systemAnnouncements", value)
            }
            icon={faCircleInfo}
          />
        </div>
      </section>

      {/* Privacy & Recognition */}
      <section className="student-settings-card">
        <div className="student-settings-card-header">
          <div className="student-settings-section-icon">
            <FontAwesomeIcon icon={faShieldHalved} />
          </div>

          <div>
            <h2>Privacy &amp; Recognition</h2>
            <p>
              Information about facial recognition and attendance identity.
            </p>
          </div>
        </div>

        <div className="student-settings-info-grid">
          <InfoItem
            label="Face Recognition"
            value={faceProfileStatus}
          />

          <InfoItem
            label="Attendance Identification"
            value="Authorized attendance sessions"
          />

          <InfoItem
            label="Face Data Management"
            value="Managed by institution"
          />

          <InfoItem
            label="Privacy"
            value="Subject to institutional policy"
          />
        </div>

        <div className="student-settings-privacy-note">
          <FontAwesomeIcon icon={faLock} />

          <span>
            Facial recognition information is managed by the institution and
            is not exposed as raw biometric data through the student portal.
          </span>
        </div>
      </section>

      {/* Account & Security */}
      <section className="student-settings-card">
        <div className="student-settings-card-header">
          <div className="student-settings-section-icon">
            <FontAwesomeIcon icon={faLock} />
          </div>

          <div>
            <h2>Account &amp; Security</h2>
            <p>
              View your account status and security information.
            </p>
          </div>
        </div>

        {userLoading ? (
          <div className="student-settings-info-grid">
            <InfoItem
              label="Account Status"
              value="Loading..."
            />

            <InfoItem
              label="Role"
              value="Loading..."
            />
          </div>
        ) : userError ? (
          <div
            className="student-settings-privacy-note"
            role="alert"
          >
            <FontAwesomeIcon icon={faCircleInfo} />

            <span>{userError}</span>
          </div>
        ) : (
          <div className="student-settings-account-grid">
            <InfoItem
              label="Account Status"
              value="Authenticated"
            />

            <InfoItem
              label="Role"
              value={roleLabel}
            />
          </div>
        )}

        <Link
          className="student-settings-profile-link"
          to="/student/profile"
        >
          <FontAwesomeIcon icon={faUser} />
          Go to Profile
        </Link>
      </section>

      {/* System Information */}
      <section className="student-settings-card">
        <div className="student-settings-card-header">
          <div className="student-settings-section-icon">
            <FontAwesomeIcon icon={faCircleInfo} />
          </div>

          <div>
            <h2>System Information</h2>
            <p>
              Read-only information about the SAMS-FR platform.
            </p>
          </div>
        </div>

        <div className="student-settings-system-grid">
          <InfoItem label="Application" value="SAMS-FR" />
          <InfoItem label="Version" value="v1.0.0" />
          <InfoItem label="Frontend" value="React + Vite" />
          <InfoItem label="Backend" value="Flask" />
          <InfoItem label="Database" value="MySQL" />
          <InfoItem label="Recognition" value="Face Recognition" />
          <InfoItem label="Environment" value="Development" />
          <InfoItem label="Portal" value="Student" />
        </div>
      </section>

      {/* Restore Defaults */}
      <div className="student-settings-footer">
        <div>
          <strong>Restore default preferences</strong>

          <span>
            Reset your local student portal preferences to their defaults.
          </span>
        </div>

        <button
          type="button"
          onClick={resetSettings}
        >
          Restore Defaults
        </button>
      </div>
    </section>
  );
}

function SettingToggle({
  label,
  description,
  checked,
  onChange,
  icon,
}) {
  return (
    <div className="student-settings-option">
      <div className="student-settings-option-info">
        <FontAwesomeIcon icon={icon} />

        <div>
          <strong>{label}</strong>
          <span>{description}</span>
        </div>
      </div>

      <button
        type="button"
        className={`student-settings-toggle ${
          checked ? "is-enabled" : ""
        }`}
        onClick={() => onChange(!checked)}
        aria-pressed={checked}
        aria-label={`${label}: ${checked ? "On" : "Off"}`}
      >
        <span />
      </button>
    </div>
  );
}

function InfoItem({ label, value }) {
  return (
    <div className="student-settings-info-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export default Settings;