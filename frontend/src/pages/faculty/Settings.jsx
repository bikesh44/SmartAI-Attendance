
import { useState } from "react";
import "./Settings.css";
import useAppearance from "../../hooks/useAppearance";

const SETTINGS_STORAGE_KEY = "sams-faculty-settings";

const DEFAULT_FACULTY_SETTINGS = {
  attendanceView: "list",
  confirmBeforeStart: true,
  sessionNotifications: true,
  attendanceAlerts: true,
  reportAvailability: true,
  systemAnnouncements: true,
};

const loadFacultySettings = () => {
  try {
    const storedSettings = localStorage.getItem(SETTINGS_STORAGE_KEY);

    if (!storedSettings) {
      return { ...DEFAULT_FACULTY_SETTINGS };
    }

    const parsedSettings = JSON.parse(storedSettings);

    if (
      !parsedSettings ||
      typeof parsedSettings !== "object" ||
      Array.isArray(parsedSettings)
    ) {
      return { ...DEFAULT_FACULTY_SETTINGS };
    }

    const validSettings = {};

    Object.entries(DEFAULT_FACULTY_SETTINGS).forEach(
      ([key, defaultValue]) => {
        const value = parsedSettings[key];

        validSettings[key] =
          typeof value === typeof defaultValue
            ? value
            : defaultValue;
      },
    );

    return validSettings;
  } catch {
    return { ...DEFAULT_FACULTY_SETTINGS };
  }
};

const saveFacultySettings = (settings) => {
  try {
    localStorage.setItem(
      SETTINGS_STORAGE_KEY,
      JSON.stringify(settings),
    );
    return true;
  } catch {
    return false;
  }
};

function Settings() {
  const {
    theme,
    setTheme,
    sidebarMode,
    setSidebarMode,
  } = useAppearance();

  const [settings, setSettings] = useState(loadFacultySettings);
  const [saveMessage, setSaveMessage] = useState("");
  const [saveStatus, setSaveStatus] = useState("idle");

  const persistSettings = (nextSettings) => {
    const saved = saveFacultySettings(nextSettings);

    setSaveStatus(saved ? "saved" : "error");
    setSaveMessage(
      saved
        ? "Faculty preferences saved locally."
        : "Preferences could not be saved in this browser.",
    );
  };

  const updateSetting = (key, value) => {
    const nextSettings = {
      ...settings,
      [key]: value,
    };

    setSettings(nextSettings);
    persistSettings(nextSettings);
  };

  const updateAppearance = (key, value) => {
    if (key === "theme") {
      setTheme(value);
    }

    if (key === "sidebar") {
      setSidebarMode(value);
    }

    setSaveStatus("pending");
    setSaveMessage("Appearance preference updated.");
  };

  const handleReset = () => {
    const defaultSettings = { ...DEFAULT_FACULTY_SETTINGS };

    setSettings(defaultSettings);
    persistSettings(defaultSettings);
    setTheme("light");
    setSidebarMode("expanded");
  };

  const renderRadioOption = (
    name,
    value,
    label,
    currentValue,
    onChange,
  ) => (
    <label
      className="faculty-settings-radio-option"
      key={`${name}-${value}`}
    >
      <input
        type="radio"
        name={name}
        value={value}
        checked={currentValue === value}
        onChange={() => onChange(value)}
      />
      <span>{label}</span>
    </label>
  );

  return (
    <div className="faculty-settings-page">
      <section className="faculty-settings-header">
        <div>
          <span className="faculty-settings-eyebrow">
            FACULTY PORTAL
          </span>
          <h1>Settings</h1>
          <p>
            Manage your faculty portal preferences and attendance
            settings.
          </p>
        </div>

        <span className="faculty-settings-system-status">
          <span className="faculty-settings-status-dot" />
          System Operational
        </span>
      </section>

      {saveMessage && (
        <div
          className="faculty-settings-save-message"
          role="status"
          aria-live="polite"
          data-status={saveStatus}
        >
          <span aria-hidden="true">
            {saveStatus === "error"
              ? "!"
              : saveStatus === "pending"
                ? "…"
                : "✓"}
          </span>
          {saveMessage}
        </div>
      )}

      <section className="faculty-settings-section">
        <div className="faculty-settings-section-heading">
          <h2>Appearance</h2>
          <p>
            Customize how the faculty portal looks and behaves.
          </p>
        </div>

        <div className="faculty-settings-card">
          <div className="faculty-settings-row">
            <div className="faculty-settings-row-content">
              <h3>Theme</h3>
              <p>
                Choose the appearance used throughout the SAMS-FR
                application.
              </p>
            </div>

            <div className="faculty-settings-radio-group">
              {renderRadioOption(
                "theme",
                "light",
                "Light",
                theme,
                (value) => updateAppearance("theme", value),
              )}
              {renderRadioOption(
                "theme",
                "dark",
                "Dark",
                theme,
                (value) => updateAppearance("theme", value),
              )}
              {renderRadioOption(
                "theme",
                "system",
                "System",
                theme,
                (value) => updateAppearance("theme", value),
              )}
            </div>
          </div>

          <div className="faculty-settings-divider" />

          <div className="faculty-settings-row">
            <div className="faculty-settings-row-content">
              <h3>Sidebar</h3>
              <p>
                Choose whether the faculty sidebar starts expanded
                or compact.
              </p>
            </div>

            <div className="faculty-settings-radio-group">
              {renderRadioOption(
                "sidebar",
                "expanded",
                "Expanded",
                sidebarMode,
                (value) => updateAppearance("sidebar", value),
              )}
              {renderRadioOption(
                "sidebar",
                "compact",
                "Compact",
                sidebarMode,
                (value) => updateAppearance("sidebar", value),
              )}
            </div>
          </div>
        </div>
      </section>

      <section className="faculty-settings-section">
        <div className="faculty-settings-section-heading">
          <h2>Attendance Preferences</h2>
          <p>
            Configure your preferred attendance workflow.
          </p>
        </div>

        <div className="faculty-settings-card">
          <div className="faculty-settings-row">
            <div className="faculty-settings-row-content">
              <h3>Default Attendance View</h3>
              <p>
                Select the preferred view when working with attendance
                records.
              </p>
            </div>

            <div className="faculty-settings-radio-group">
              {renderRadioOption(
                "attendance-view",
                "list",
                "List View",
                settings.attendanceView,
                (value) => updateSetting("attendanceView", value),
              )}
              {renderRadioOption(
                "attendance-view",
                "session",
                "Session View",
                settings.attendanceView,
                (value) => updateSetting("attendanceView", value),
              )}
            </div>
          </div>

          <div className="faculty-settings-divider" />

          <div className="faculty-settings-toggle-row">
            <div className="faculty-settings-row-content">
              <h3>Confirmation Before Starting Attendance</h3>
              <p>
                Ask for confirmation before starting an attendance
                session.
              </p>
            </div>

            <button
              type="button"
              className={`faculty-settings-toggle ${
                settings.confirmBeforeStart ? "active" : ""
              }`}
              onClick={() =>
                updateSetting(
                  "confirmBeforeStart",
                  !settings.confirmBeforeStart,
                )
              }
              aria-pressed={settings.confirmBeforeStart}
              aria-label="Toggle confirmation before starting attendance"
            >
              <span />
            </button>
          </div>

          <div className="faculty-settings-divider" />

          <div className="faculty-settings-toggle-row">
            <div className="faculty-settings-row-content">
              <h3>Session Notifications</h3>
              <p>
                Set your preference for notifications related to
                attendance sessions.
              </p>
            </div>

            <button
              type="button"
              className={`faculty-settings-toggle ${
                settings.sessionNotifications ? "active" : ""
              }`}
              onClick={() =>
                updateSetting(
                  "sessionNotifications",
                  !settings.sessionNotifications,
                )
              }
              aria-pressed={settings.sessionNotifications}
              aria-label="Toggle session notifications"
            >
              <span />
            </button>
          </div>
        </div>
      </section>

      <section className="faculty-settings-section">
        <div className="faculty-settings-section-heading">
          <h2>Notifications</h2>
          <p>Manage your notification preferences.</p>
        </div>

        <div className="faculty-settings-card">
          {[
            {
              key: "attendanceAlerts",
              title: "Attendance Session Alerts",
              description:
                "Set your preference for attendance session alerts.",
            },
            {
              key: "reportAvailability",
              title: "Report Availability",
              description:
                "Set your preference for report availability notifications.",
            },
            {
              key: "systemAnnouncements",
              title: "System Announcements",
              description:
                "Set your preference for system announcement notifications.",
            },
          ].map((item, index) => (
            <div key={item.key}>
              {index > 0 && (
                <div className="faculty-settings-divider" />
              )}

              <div className="faculty-settings-toggle-row">
                <div className="faculty-settings-row-content">
                  <h3>{item.title}</h3>
                  <p>{item.description}</p>
                </div>

                <button
                  type="button"
                  className={`faculty-settings-toggle ${
                    settings[item.key] ? "active" : ""
                  }`}
                  onClick={() =>
                    updateSetting(item.key, !settings[item.key])
                  }
                  aria-pressed={settings[item.key]}
                  aria-label={`Toggle ${item.title}`}
                >
                  <span />
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="faculty-settings-section">
        <div className="faculty-settings-section-heading">
          <h2>System Information</h2>
          <p>
            Technical information about the SAMS-FR application.
          </p>
        </div>

        <div className="faculty-settings-system-card">
          <div>
            <span>Application</span>
            <strong>SAMS-FR</strong>
          </div>
          <div>
            <span>Version</span>
            <strong>1.0.0</strong>
          </div>
          <div>
            <span>Frontend</span>
            <strong>React + Vite</strong>
          </div>
          <div>
            <span>Backend</span>
            <strong>Flask</strong>
          </div>
          <div>
            <span>Database</span>
            <strong>MySQL</strong>
          </div>
          <div>
            <span>Recognition</span>
            <strong>Face Recognition</strong>
          </div>
          <div>
            <span>Environment</span>
            <strong>Development</strong>
          </div>
          <div>
            <span>Portal</span>
            <strong>Faculty</strong>
          </div>
        </div>
      </section>

      <section className="faculty-settings-actions">
        <div>
          <strong>Restore default preferences</strong>
          <p>
            Reset faculty preferences and appearance to their defaults.
          </p>
        </div>

        <button
          type="button"
          className="faculty-settings-reset-button"
          onClick={handleReset}
        >
          Restore Defaults
        </button>
      </section>
    </div>
  );
}

export default Settings;
