import { useState } from "react";
import useAppearance from "../../hooks/useAppearance";
import "./AdminSettings.css";

function AdminSettings() {
  const {
    theme,
    setTheme,
    sidebarCollapsed,
    setSidebarCollapsed,
  } = useAppearance();

  const [saveMessage, setSaveMessage] = useState("");

  const handleThemeChange = (value) => {
    setTheme(value);
    setSaveMessage("Appearance preference updated.");
  };

  const handleSidebarChange = (collapsed) => {
    setSidebarCollapsed(collapsed);
    setSaveMessage("Sidebar preference updated.");
  };

  return (
    <section className="admin-settings-page">
      <header className="admin-page-header">
        <div>
          <span className="admin-page-eyebrow">Administration</span>
          <h1>System Settings</h1>
          <p>
            Manage application preferences and system configuration.
          </p>
        </div>
      </header>

      {saveMessage && (
        <div className="admin-settings-feedback" role="status">
          <i className="fa-solid fa-circle-check" aria-hidden="true" />
          <span>{saveMessage}</span>
        </div>
      )}

      <div className="admin-settings-grid">
        {/* Appearance */}
        <section className="admin-settings-card admin-settings-notifications-card">
          <div className="admin-settings-section-heading">
            <div className="admin-settings-icon">
              <i className="fa-solid fa-palette" aria-hidden="true" />
            </div>

            <div>
              <h2>Appearance</h2>
              <p>
                Customize your administration portal experience.
              </p>
            </div>
          </div>

          <div className="admin-settings-options">
            <div className="admin-setting-row">
              <div className="admin-setting-content">
                <strong>Theme</strong>
                <span>
                  Choose how the SAMS-FR administration interface
                  should appear.
                </span>
              </div>

              <div
                className="admin-segmented-control"
                role="group"
                aria-label="Theme"
              >
                <button
                  type="button"
                  className={theme === "light" ? "active" : ""}
                  onClick={() => handleThemeChange("light")}
                >
                  <i className="fa-solid fa-sun" aria-hidden="true" />
                  Light
                </button>

                <button
                  type="button"
                  className={theme === "dark" ? "active" : ""}
                  onClick={() => handleThemeChange("dark")}
                >
                  <i className="fa-solid fa-moon" aria-hidden="true" />
                  Dark
                </button>

                <button
                  type="button"
                  className={theme === "system" ? "active" : ""}
                  onClick={() => handleThemeChange("system")}
                >
                  <i
                    className="fa-solid fa-desktop"
                    aria-hidden="true"
                  />
                  System
                </button>
              </div>
            </div>

            <div className="admin-setting-row">
              <div className="admin-setting-content">
                <strong>Sidebar</strong>
                <span>
                  Choose the default navigation layout for the
                  administration portal.
                </span>
              </div>

              <div
                className="admin-segmented-control"
                role="group"
                aria-label="Sidebar layout"
              >
                <button
                  type="button"
                  className={!sidebarCollapsed ? "active" : ""}
                  onClick={() => handleSidebarChange(false)}
                >
                  <i className="fa-solid fa-bars" aria-hidden="true" />
                  Expanded
                </button>

                <button
                  type="button"
                  className={sidebarCollapsed ? "active" : ""}
                  onClick={() => handleSidebarChange(true)}
                >
                  <i
                    className="fa-solid fa-align-justify"
                    aria-hidden="true"
                  />
                  Compact
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* Attendance */}
        <section className="admin-settings-card">
          <div className="admin-settings-section-heading">
            <div className="admin-settings-icon">
              <i className="fa-solid fa-calendar-check" aria-hidden="true" />
            </div>

            <div>
              <h2>Attendance</h2>
              <p>
                Configure attendance-related system behavior.
              </p>
            </div>
          </div>

          <div className="admin-settings-service-list">
            <BackendSetting
              icon="fa-clock"
              title="Attendance Timing"
              description="Session duration and attendance timing rules."
              status="Integration Pending"
            />

            <BackendSetting
              icon="fa-face-smile"
              title="Face Recognition"
              description="Recognition service status and verification configuration."
              status="Integration Pending"
            />

            <BackendSetting
              icon="fa-list-check"
              title="Attendance Rules"
              description="Rules applied when attendance is recorded."
              status="Integration Pending"
            />
          </div>
        </section>

        {/* Notifications */}
        <section className="admin-settings-card">
          <div className="admin-settings-section-heading">
            <div className="admin-settings-icon admin-settings-icon-green">
              <i
                className="fa-solid fa-bell"
                aria-hidden="true"
              />
            </div>

            <div>
              <h2>Notifications</h2>
              <p>
                Manage system and attendance notification preferences.
              </p>
            </div>
          </div>

          <div className="admin-settings-service-list">
            <BackendSetting
              icon="fa-envelope"
              title="Email Notifications"
              description="Configure system-generated email notifications."
              status="Coming Soon"
            />

            <BackendSetting
              icon="fa-triangle-exclamation"
              title="Attendance Alerts"
              description="Configure notifications related to attendance."
              status="Coming Soon"
            />

            <BackendSetting
              icon="fa-circle-info"
              title="System Notifications"
              description="Receive important system notifications."
              status="Coming Soon"
            />
          </div>
        </section>

        {/* System Information */}
        <section className="admin-settings-card admin-settings-system-card">
          <div className="admin-settings-section-heading">
            <div className="admin-settings-icon admin-settings-icon-purple">
              <i className="fa-solid fa-circle-info" aria-hidden="true" />
            </div>

            <div>
              <h2>System Information</h2>
              <p>Read-only information about the SAMS-FR application.</p>
            </div>
          </div>

          <div className="admin-system-information">
            <InfoItem label="Application" value="SAMS-FR" />
            <InfoItem label="Version" value="1.0.0" />
            <InfoItem label="Frontend" value="React + Vite" />
            <InfoItem label="Backend" value="Flask" />
            <InfoItem label="Database" value="MySQL" />
            <InfoItem label="Recognition" value="Face Recognition" />
            <InfoItem label="Environment" value="Development" />
          </div>
        </section>
      </div>
    </section>
  );
}

function BackendSetting({ icon, title, description, status }) {
  return (
    <div className="admin-setting-service-row">
      <div className="admin-setting-service-icon">
        <i className={`fa-solid ${icon}`} aria-hidden="true" />
      </div>

      <div className="admin-setting-service-content">
        <strong>{title}</strong>
        <span>{description}</span>
      </div>

      <span className="admin-setting-status">
        {status}
      </span>
    </div>
  );
}

function InfoItem({ label, value }) {
  return (
    <div className="admin-system-info-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export default AdminSettings;