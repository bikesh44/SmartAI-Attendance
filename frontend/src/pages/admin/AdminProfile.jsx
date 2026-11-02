import { useCallback, useEffect, useMemo, useState } from "react";

import {
  getAdminProfile,
  updateAdminProfile,
  changeAdminPassword,
} from "../../services/adminService";

import "./AdminProfile.css";

function getInitials(name) {
  if (!name) {
    return "AD";
  }

  const parts = name
    .trim()
    .split(/\s+/)
    .filter(Boolean);

  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }

  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

function formatDate(value) {
  if (!value) {
    return "N/A";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

function getPasswordStrength(password) {
  if (!password) {
    return {
      label: "Enter a password",
      level: 0,
    };
  }

  let score = 0;

  if (password.length >= 8) {
    score += 1;
  }

  if (/[A-Z]/.test(password)) {
    score += 1;
  }

  if (/[a-z]/.test(password)) {
    score += 1;
  }

  if (/[0-9]/.test(password)) {
    score += 1;
  }

  if (/[^A-Za-z0-9]/.test(password)) {
    score += 1;
  }

  if (score <= 2) {
    return {
      label: "Weak",
      level: 1,
    };
  }

  if (score <= 3) {
    return {
      label: "Moderate",
      level: 2,
    };
  }

  if (score === 4) {
    return {
      label: "Strong",
      level: 3,
    };
  }

  return {
    label: "Very strong",
    level: 4,
  };
}

function AdminProfile() {
  const [profile, setProfile] = useState(null);

  // Profile Edit Form state
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [designation, setDesignation] = useState("");
  const [department, setDepartment] = useState("");

  // Password Change Form state
  const [currentPassword, setCurrentPassword] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [passwordError, setPasswordError] = useState("");

  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const loadProfile = useCallback(async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError("");

      const response = await getAdminProfile();

      if (!response?.success) {
        throw new Error(
          response?.message || "Failed to load admin profile."
        );
      }

      const data = response.data;

      setProfile(data);
      setName(data?.name || "");
      setEmail(data?.email || "");
      setPhone(data?.phone || "");
      setDesignation(data?.designation || "");
      setDepartment(data?.department || "");

      if (isRefresh) {
        setSuccess("Profile details synchronized from backend.");
      }
    } catch (requestError) {
      setError(
        requestError?.response?.data?.message ||
          requestError?.message ||
          "Failed to load admin profile."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    let mounted = true;

    const initialLoad = async () => {
      try {
        setLoading(true);
        setError("");

        const response = await getAdminProfile();

        if (!mounted) return;

        if (!response?.success) {
          throw new Error(
            response?.message || "Failed to load admin profile."
          );
        }

        const data = response.data;
        setProfile(data);
        setName(data?.name || "");
        setEmail(data?.email || "");
        setPhone(data?.phone || "");
        setDesignation(data?.designation || "");
        setDepartment(data?.department || "");
      } catch (requestError) {
        if (!mounted) return;
        setProfile(null);
        setError(
          requestError?.response?.data?.message ||
            requestError?.message ||
            "Failed to load admin profile."
        );
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    initialLoad();

    return () => {
      mounted = false;
    };
  }, []);

  const initials = useMemo(
    () => getInitials(profile?.name),
    [profile?.name]
  );

  const passwordStrength = useMemo(
    () => getPasswordStrength(password),
    [password]
  );

  const profileChanged = useMemo(() => {
    if (!profile) return false;
    return (
      name.trim() !== (profile.name || "") ||
      email.trim() !== (profile.email || "") ||
      phone.trim() !== (profile.phone || "") ||
      designation.trim() !== (profile.designation || "") ||
      department.trim() !== (profile.department || "")
    );
  }, [profile, name, email, phone, designation, department]);

  const passwordChanged =
    currentPassword.length > 0 ||
    password.length > 0 ||
    confirmPassword.length > 0;

  const clearMessages = () => {
    setError("");
    setSuccess("");
    setPasswordError("");
  };

  const handleProfileSubmit = async (event) => {
    event.preventDefault();
    clearMessages();

    const trimmedName = name.trim();
    const trimmedEmail = email.trim();
    const trimmedPhone = phone.trim();
    const trimmedDesignation = designation.trim();
    const trimmedDepartment = department.trim();

    if (!trimmedName) {
      setError("Full name cannot be empty.");
      return;
    }

    if (!trimmedEmail) {
      setError("Email address cannot be empty.");
      return;
    }

    try {
      setSavingProfile(true);

      const response = await updateAdminProfile({
        name: trimmedName,
        email: trimmedEmail,
        phone: trimmedPhone,
        designation: trimmedDesignation,
        department: trimmedDepartment,
      });

      if (!response?.success) {
        throw new Error(
          response?.message || "Failed to update profile."
        );
      }

      const updatedProfile = response.data;

      setProfile(updatedProfile);
      setName(updatedProfile?.name || "");
      setEmail(updatedProfile?.email || "");
      setPhone(updatedProfile?.phone || "");
      setDesignation(updatedProfile?.designation || "");
      setDepartment(updatedProfile?.department || "");

      setSuccess("Administrator profile updated successfully.");
    } catch (requestError) {
      setError(
        requestError?.response?.data?.message ||
          requestError?.message ||
          "Failed to update profile."
      );
    } finally {
      setSavingProfile(false);
    }
  };

  const handlePasswordSubmit = async (event) => {
    event.preventDefault();
    clearMessages();

    if (!currentPassword) {
      setPasswordError("Please enter your current password.");
      return;
    }

    if (password.length < 8) {
      setPasswordError(
        "New password must contain at least 8 characters."
      );
      return;
    }

    if (password !== confirmPassword) {
      setPasswordError("New passwords do not match.");
      return;
    }

    try {
      setSavingPassword(true);

      const response = await changeAdminPassword({
        current_password: currentPassword,
        new_password: password,
        confirm_password: confirmPassword,
      });

      if (!response?.success) {
        throw new Error(
          response?.message || "Failed to update password."
        );
      }

      setCurrentPassword("");
      setPassword("");
      setConfirmPassword("");

      setShowCurrentPassword(false);
      setShowPassword(false);
      setShowConfirmPassword(false);

      setSuccess("Account password changed successfully.");
    } catch (requestError) {
      setPasswordError(
        requestError?.response?.data?.message ||
          requestError?.message ||
          "Failed to change password."
      );
    } finally {
      setSavingPassword(false);
    }
  };

  const handleResetProfile = () => {
    if (!profile) return;

    setName(profile.name || "");
    setEmail(profile.email || "");
    setPhone(profile.phone || "");
    setDesignation(profile.designation || "");
    setDepartment(profile.department || "");

    clearMessages();
  };

  const handleResetPassword = () => {
    setCurrentPassword("");
    setPassword("");
    setConfirmPassword("");

    setShowCurrentPassword(false);
    setShowPassword(false);
    setShowConfirmPassword(false);

    setPasswordError("");
  };

  if (loading) {
    return (
      <section className="admin-profile-page">
        <div className="admin-profile-state">
          <div className="admin-profile-state-icon">
            <i
              className="fa-solid fa-spinner fa-spin"
              aria-hidden="true"
            />
          </div>

          <h2>Loading Administrator Profile</h2>

          <p>
            Fetching verified administrator account records and live system
            metrics from the database.
          </p>
        </div>
      </section>
    );
  }

  if (!profile) {
    return (
      <section className="admin-profile-page">
        <div className="admin-profile-state admin-profile-state-error">
          <div className="admin-profile-state-icon">
            <i
              className="fa-solid fa-triangle-exclamation"
              aria-hidden="true"
            />
          </div>

          <h2>Unable to Load Profile</h2>

          <p>
            {error ||
              "Administrator profile information is currently unavailable."}
          </p>

          <button
            type="button"
            className="admin-profile-primary-button"
            onClick={() => loadProfile(false)}
          >
            <i
              className="fa-solid fa-rotate-right"
              aria-hidden="true"
            />
            Try Again
          </button>
        </div>
      </section>
    );
  }

  const stats = profile.stats || {};

  return (
    <section className="admin-profile-page">
      {/* Header */}
      <header className="admin-profile-header">
        <div className="admin-profile-header-content">
          <span className="admin-profile-eyebrow">
            Central Administration
          </span>

          <h1>Admin Profile &amp; Account</h1>

          <p>
            View institutional administrator details, maintain verified contact
            credentials, and monitor system-wide scope.
          </p>
        </div>

        <div className="admin-profile-account-status">
          <span>Account Privilege</span>

          <strong>
            <span
              className="admin-profile-status-dot"
              aria-hidden="true"
            />
            {profile.role || "ADMIN"} • Active
          </strong>
        </div>
      </header>

      {/* Alert Banner */}
      {(error || success) && (
        <div
          className={`admin-profile-alert ${
            error
              ? "admin-profile-alert-error"
              : "admin-profile-alert-success"
          }`}
          role={error ? "alert" : "status"}
        >
          <div className="admin-profile-alert-icon">
            <i
              className={`fa-solid ${
                error
                  ? "fa-circle-exclamation"
                  : "fa-circle-check"
              }`}
              aria-hidden="true"
            />
          </div>

          <div>
            <strong>
              {error ? "Action Required" : "Success"}
            </strong>

            <span>{error || success}</span>
          </div>

          <button
            type="button"
            className="admin-profile-alert-close"
            onClick={clearMessages}
            aria-label="Dismiss message"
          >
            <i
              className="fa-solid fa-xmark"
              aria-hidden="true"
            />
          </button>
        </div>
      )}

      {/* Hero Overview */}
      <section className="admin-profile-overview">
        <div className="admin-profile-avatar">
          {initials}
        </div>

        <div className="admin-profile-overview-content">
          <span className="admin-profile-overview-label">
            {profile.designation || "System Administrator"} •{" "}
            {profile.department || "Administration"}
          </span>

          <h2>{profile.name || "Administrator"}</h2>

          <div className="admin-profile-overview-meta">
            <span>
              <i
                className="fa-solid fa-envelope"
                aria-hidden="true"
              />
              {profile.email || "N/A"}
            </span>

            {profile.phone ? (
              <span>
                <i
                  className="fa-solid fa-phone"
                  aria-hidden="true"
                />
                {profile.phone}
              </span>
            ) : null}

            <span>
              <i
                className="fa-solid fa-id-card"
                aria-hidden="true"
              />
              Admin ID: #{profile.user_id}
            </span>

            <span>
              <i
                className="fa-solid fa-shield-halved"
                aria-hidden="true"
              />
              Role: {profile.role || "ADMIN"}
            </span>
          </div>
        </div>

        <div className="admin-profile-overview-actions">
          <span className="admin-profile-overview-status">
            <i
              className="fa-solid fa-circle-check"
              aria-hidden="true"
            />
            Verified
          </span>

          <button
            type="button"
            className="admin-profile-secondary-button admin-profile-refresh-btn"
            onClick={() => loadProfile(true)}
            disabled={refreshing}
            title="Refresh database records"
          >
            <i
              className={`fa-solid fa-rotate-right ${
                refreshing ? "fa-spin" : ""
              }`}
              aria-hidden="true"
            />
            {refreshing ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </section>

      {/* Live System Impact Stats Bar (100% Real Database Queries) */}
      <section className="admin-profile-stats-card">
        <div className="admin-profile-stats-header">
          <div>
            <span className="admin-profile-stats-eyebrow">
              Database Metrics
            </span>
            <h3>Administrative System Oversight</h3>
          </div>
          <span className="admin-profile-stats-badge">
            <i className="fa-solid fa-server" aria-hidden="true" />
            Live Backend Data
          </span>
        </div>

        <div className="admin-profile-stats-grid">
          <div className="admin-profile-stat-box">
            <div className="admin-profile-stat-icon stat-icon-users">
              <i className="fa-solid fa-users" aria-hidden="true" />
            </div>
            <div className="admin-profile-stat-info">
              <span className="stat-label">Total Users</span>
              <strong className="stat-value">
                {stats.total_users ?? 0}
              </strong>
            </div>
          </div>

          <div className="admin-profile-stat-box">
            <div className="admin-profile-stat-icon stat-icon-students">
              <i
                className="fa-solid fa-graduation-cap"
                aria-hidden="true"
              />
            </div>
            <div className="admin-profile-stat-info">
              <span className="stat-label">Students</span>
              <strong className="stat-value">
                {stats.total_students ?? 0}
              </strong>
            </div>
          </div>

          <div className="admin-profile-stat-box">
            <div className="admin-profile-stat-icon stat-icon-faculty">
              <i
                className="fa-solid fa-chalkboard-user"
                aria-hidden="true"
              />
            </div>
            <div className="admin-profile-stat-info">
              <span className="stat-label">Faculty Members</span>
              <strong className="stat-value">
                {stats.total_faculty ?? 0}
              </strong>
            </div>
          </div>

          <div className="admin-profile-stat-box">
            <div className="admin-profile-stat-icon stat-icon-courses">
              <i className="fa-solid fa-book-open" aria-hidden="true" />
            </div>
            <div className="admin-profile-stat-info">
              <span className="stat-label">Active Courses</span>
              <strong className="stat-value">
                {stats.total_courses ?? 0}
              </strong>
            </div>
          </div>

          <div className="admin-profile-stat-box">
            <div className="admin-profile-stat-icon stat-icon-sessions">
              <i
                className="fa-solid fa-clipboard-check"
                aria-hidden="true"
              />
            </div>
            <div className="admin-profile-stat-info">
              <span className="stat-label">Attendance Sessions</span>
              <strong className="stat-value">
                {stats.total_sessions ?? 0}
              </strong>
            </div>
          </div>
        </div>
      </section>

      {/* Main Grid Layout */}
      <div className="admin-profile-layout">
        {/* Card 1: Read-Only Institutional Record */}
        <section className="admin-profile-card admin-profile-card-wide">
          <div className="admin-profile-card-header">
            <div className="admin-profile-card-title">
              <div className="admin-profile-card-icon">
                <i
                  className="fa-solid fa-address-card"
                  aria-hidden="true"
                />
              </div>

              <div>
                <span>Database Identity</span>
                <h2>Institutional Account Details</h2>
              </div>
            </div>

            <span className="admin-profile-readonly-badge">
              Verified Record
            </span>
          </div>

          <div className="admin-profile-info-grid">
            <div className="admin-profile-info-item">
              <span>Full Name</span>
              <strong>{profile.name || "N/A"}</strong>
            </div>

            <div className="admin-profile-info-item">
              <span>Official Email</span>
              <strong>{profile.email || "N/A"}</strong>
            </div>

            <div className="admin-profile-info-item">
              <span>Contact Phone</span>
              <strong>{profile.phone || "Not configured"}</strong>
            </div>

            <div className="admin-profile-info-item">
              <span>Designation</span>
              <strong>
                {profile.designation || "System Administrator"}
              </strong>
            </div>

            <div className="admin-profile-info-item">
              <span>Department</span>
              <strong>
                {profile.department || "Administration"}
              </strong>
            </div>

            <div className="admin-profile-info-item">
              <span>System Role</span>
              <strong className="admin-profile-role-tag">
                {profile.role || "ADMIN"}
              </strong>
            </div>

            <div className="admin-profile-info-item">
              <span>Account ID</span>
              <strong>User #{profile.user_id}</strong>
            </div>

            <div className="admin-profile-info-item">
              <span>Created At</span>
              <strong>{formatDate(profile.created_at)}</strong>
            </div>

            <div className="admin-profile-info-item">
              <span>Last Modified</span>
              <strong>{formatDate(profile.updated_at)}</strong>
            </div>
          </div>
        </section>

        {/* Card 2: Edit Profile Form */}
        <section className="admin-profile-card">
          <div className="admin-profile-card-header">
            <div className="admin-profile-card-title">
              <div className="admin-profile-card-icon">
                <i
                  className="fa-solid fa-pen-to-square"
                  aria-hidden="true"
                />
              </div>

              <div>
                <span>Profile Management</span>
                <h2>Edit Administrator Information</h2>
              </div>
            </div>
          </div>

          <form
            className="admin-profile-form"
            onSubmit={handleProfileSubmit}
          >
            <div className="admin-profile-form-field">
              <label htmlFor="admin-profile-name">
                Full Name *
              </label>

              <div className="admin-profile-input-wrapper">
                <i
                  className="fa-solid fa-user"
                  aria-hidden="true"
                />

                <input
                  id="admin-profile-name"
                  type="text"
                  value={name}
                  onChange={(event) =>
                    setName(event.target.value)
                  }
                  placeholder="e.g. Dr. John Doe"
                  autoComplete="name"
                  required
                />
              </div>
            </div>

            <div className="admin-profile-form-field">
              <label htmlFor="admin-profile-email">
                Official Email Address *
              </label>

              <div className="admin-profile-input-wrapper">
                <i
                  className="fa-solid fa-envelope"
                  aria-hidden="true"
                />

                <input
                  id="admin-profile-email"
                  type="email"
                  value={email}
                  onChange={(event) =>
                    setEmail(event.target.value)
                  }
                  placeholder="admin@university.edu"
                  autoComplete="email"
                  required
                />
              </div>
            </div>

            <div className="admin-profile-form-field">
              <label htmlFor="admin-profile-phone">
                Contact Phone Number
              </label>

              <div className="admin-profile-input-wrapper">
                <i
                  className="fa-solid fa-phone"
                  aria-hidden="true"
                />

                <input
                  id="admin-profile-phone"
                  type="tel"
                  value={phone}
                  onChange={(event) =>
                    setPhone(event.target.value)
                  }
                  placeholder="+91 98765 43210"
                  autoComplete="tel"
                />
              </div>
            </div>

            <div className="admin-profile-form-row">
              <div className="admin-profile-form-field">
                <label htmlFor="admin-profile-designation">
                  Designation
                </label>

                <div className="admin-profile-input-wrapper">
                  <i
                    className="fa-solid fa-briefcase"
                    aria-hidden="true"
                  />

                  <input
                    id="admin-profile-designation"
                    type="text"
                    value={designation}
                    onChange={(event) =>
                      setDesignation(event.target.value)
                    }
                    placeholder="System Administrator"
                  />
                </div>
              </div>

              <div className="admin-profile-form-field">
                <label htmlFor="admin-profile-department">
                  Department
                </label>

                <div className="admin-profile-input-wrapper">
                  <i
                    className="fa-solid fa-building"
                    aria-hidden="true"
                  />

                  <input
                    id="admin-profile-department"
                    type="text"
                    value={department}
                    onChange={(event) =>
                      setDepartment(event.target.value)
                    }
                    placeholder="Administration"
                  />
                </div>
              </div>
            </div>

            <div className="admin-profile-form-actions">
              <button
                type="button"
                className="admin-profile-secondary-button"
                onClick={handleResetProfile}
                disabled={
                  savingProfile || !profileChanged
                }
              >
                <i
                  className="fa-solid fa-rotate-left"
                  aria-hidden="true"
                />
                Reset
              </button>

              <button
                type="submit"
                className="admin-profile-primary-button"
                disabled={
                  savingProfile || !profileChanged
                }
              >
                {savingProfile ? (
                  <>
                    <i
                      className="fa-solid fa-spinner fa-spin"
                      aria-hidden="true"
                    />
                    Saving Changes...
                  </>
                ) : (
                  <>
                    <i
                      className="fa-solid fa-floppy-disk"
                      aria-hidden="true"
                    />
                    Save Changes
                  </>
                )}
              </button>
            </div>
          </form>
        </section>

        {/* Card 3: Change Password Form */}
        <section className="admin-profile-card">
          <div className="admin-profile-card-header">
            <div className="admin-profile-card-title">
              <div className="admin-profile-card-icon admin-profile-security-icon">
                <i
                  className="fa-solid fa-shield-halved"
                  aria-hidden="true"
                />
              </div>

              <div>
                <span>Account Security</span>
                <h2>Change Password</h2>
              </div>
            </div>
          </div>

          <form
            className="admin-profile-form"
            onSubmit={handlePasswordSubmit}
          >
            {/* Current Password */}
            <div className="admin-profile-form-field">
              <label htmlFor="admin-profile-current-password">
                Current Password *
              </label>

              <div className="admin-profile-input-wrapper">
                <i
                  className="fa-solid fa-lock"
                  aria-hidden="true"
                />

                <input
                  id="admin-profile-current-password"
                  type={
                    showCurrentPassword ? "text" : "password"
                  }
                  value={currentPassword}
                  onChange={(e) => {
                    setCurrentPassword(e.target.value);
                    if (passwordError) setPasswordError("");
                  }}
                  placeholder="Enter your current password"
                  autoComplete="current-password"
                  required
                />

                <button
                  type="button"
                  className="admin-profile-input-action"
                  onClick={() =>
                    setShowCurrentPassword(
                      (current) => !current
                    )
                  }
                  aria-label={
                    showCurrentPassword
                      ? "Hide current password"
                      : "Show current password"
                  }
                >
                  <i
                    className={`fa-solid ${
                      showCurrentPassword
                        ? "fa-eye-slash"
                        : "fa-eye"
                    }`}
                    aria-hidden="true"
                  />
                </button>
              </div>
            </div>

            {/* New Password */}
            <div className="admin-profile-form-field">
              <label htmlFor="admin-profile-password">
                New Password *
              </label>

              <div className="admin-profile-input-wrapper">
                <i
                  className="fa-solid fa-key"
                  aria-hidden="true"
                />

                <input
                  id="admin-profile-password"
                  type={
                    showPassword ? "text" : "password"
                  }
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (passwordError) setPasswordError("");
                  }}
                  placeholder="At least 8 characters"
                  autoComplete="new-password"
                  required
                />

                <button
                  type="button"
                  className="admin-profile-input-action"
                  onClick={() =>
                    setShowPassword(
                      (current) => !current
                    )
                  }
                  aria-label={
                    showPassword
                      ? "Hide password"
                      : "Show password"
                  }
                >
                  <i
                    className={`fa-solid ${
                      showPassword
                        ? "fa-eye-slash"
                        : "fa-eye"
                    }`}
                    aria-hidden="true"
                  />
                </button>
              </div>

              {password && (
                <div className="admin-profile-password-strength">
                  <div className="admin-profile-strength-header">
                    <span>Password strength</span>

                    <strong
                      className={`strength-${passwordStrength.level}`}
                    >
                      {passwordStrength.label}
                    </strong>
                  </div>

                  <div className="admin-profile-strength-bars">
                    {[1, 2, 3, 4].map((bar) => (
                      <span
                        key={bar}
                        className={
                          bar <= passwordStrength.level
                            ? `strength-active strength-${passwordStrength.level}`
                            : ""
                        }
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Confirm Password */}
            <div className="admin-profile-form-field">
              <label htmlFor="admin-profile-confirm-password">
                Confirm New Password *
              </label>

              <div className="admin-profile-input-wrapper">
                <i
                  className="fa-solid fa-lock"
                  aria-hidden="true"
                />

                <input
                  id="admin-profile-confirm-password"
                  type={
                    showConfirmPassword
                      ? "text"
                      : "password"
                  }
                  value={confirmPassword}
                  onChange={(e) => {
                    setConfirmPassword(e.target.value);
                    if (passwordError) setPasswordError("");
                  }}
                  placeholder="Re-enter your new password"
                  autoComplete="new-password"
                  required
                />

                <button
                  type="button"
                  className="admin-profile-input-action"
                  onClick={() =>
                    setShowConfirmPassword(
                      (current) => !current
                    )
                  }
                  aria-label={
                    showConfirmPassword
                      ? "Hide password confirmation"
                      : "Show password confirmation"
                  }
                >
                  <i
                    className={`fa-solid ${
                      showConfirmPassword
                        ? "fa-eye-slash"
                        : "fa-eye"
                    }`}
                    aria-hidden="true"
                  />
                </button>
              </div>

              {confirmPassword && (
                <div
                  className={`admin-profile-password-match ${
                    password === confirmPassword
                      ? "password-match"
                      : "password-mismatch"
                  }`}
                >
                  <i
                    className={`fa-solid ${
                      password === confirmPassword
                        ? "fa-circle-check"
                        : "fa-circle-exclamation"
                    }`}
                    aria-hidden="true"
                  />

                  <span>
                    {password === confirmPassword
                      ? "Passwords match"
                      : "Passwords do not match"}
                  </span>
                </div>
              )}
            </div>

            {/* Password Validation Error */}
            {passwordError && (
              <div
                className="admin-profile-message admin-profile-message-error"
                role="alert"
              >
                <i
                  className="fa-solid fa-circle-exclamation"
                  aria-hidden="true"
                />

                <span>{passwordError}</span>
              </div>
            )}

            <div className="admin-profile-form-actions">
              <button
                type="button"
                className="admin-profile-secondary-button"
                onClick={handleResetPassword}
                disabled={
                  savingPassword || !passwordChanged
                }
              >
                <i
                  className="fa-solid fa-rotate-left"
                  aria-hidden="true"
                />
                Clear
              </button>

              <button
                type="submit"
                className="admin-profile-primary-button"
                disabled={
                  savingPassword ||
                  !currentPassword ||
                  !password ||
                  !confirmPassword
                }
              >
                {savingPassword ? (
                  <>
                    <i
                      className="fa-solid fa-spinner fa-spin"
                      aria-hidden="true"
                    />
                    Updating Password...
                  </>
                ) : (
                  <>
                    <i
                      className="fa-solid fa-key"
                      aria-hidden="true"
                    />
                    Update Password
                  </>
                )}
              </button>
            </div>
          </form>
        </section>
      </div>

      {/* Security Architecture & API Info Banner */}
      <div className="admin-profile-integration-note">
        <div className="admin-profile-note-icon">
          <i
            className="fa-solid fa-shield-halved"
            aria-hidden="true"
          />
        </div>

        <div>
          <strong>Administrator Authentication &amp; Security Protocol</strong>

          <p>
            Connected to <code>/api/admin/profile</code> and{" "}
            <code>/api/admin/change-password</code>. Credentials protected via
            Bcrypt salt hashing; sessions managed via HTTP-only JWT cookies with
            CSRF mitigation. All database records and impact metrics reflect
            live institutional data.
          </p>
        </div>

        <span className="admin-profile-integration-status">
          Live Backend
        </span>
      </div>
    </section>
  );
}

export default AdminProfile;