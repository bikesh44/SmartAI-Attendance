import { useCallback, useEffect, useState } from "react";
import {
  User,
  Mail,
  GraduationCap,
  Building,
  MapPin,
  Shield,
  Lock,
  KeyRound,
  CheckCircle2,
  AlertCircle,
  Edit3,
  X,
  RefreshCw,
  Sparkles,
  Award,
  Hash,
  BadgeCheck,
  FileText,
  Eye,
  EyeOff,
  Phone,
} from "lucide-react";

import {
  getFacultyProfile,
  updateFacultyProfile,
  changeFacultyPassword,
} from "../../services/facultyService";
import "./Profile.css";

function getInitials(name) {
  if (!name || typeof name !== "string") return "FM";
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return (
    parts
      .slice(0, 2)
      .map((part) => part.charAt(0).toUpperCase())
      .join("") || "FM"
  );
}

function Profile() {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState("");
  const [activeTab, setActiveTab] = useState("overview"); // overview, personal, security

  // Edit Profile Modal
  const [showEditModal, setShowEditModal] = useState(false);
  const [editForm, setEditForm] = useState({
    name: "",
    email: "",
    designation: "",
    phone: "",
    gender: "",
    date_of_birth: "",
    date_of_joining: "",
    employment_status: "Permanent",
    qualification: "",
    specialization: "",
    office_cabin: "",
    address: "",
    city: "",
    state: "",
    pin_code: "",
    country: "India",
  });
  const [editLoading, setEditLoading] = useState(false);
  const [editError, setEditError] = useState("");
  const [successToast, setSuccessToast] = useState("");

  // Change Password Modal
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [passwordForm, setPasswordForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [passwordError, setPasswordError] = useState("");

  const loadProfile = useCallback(async () => {
    setLoading(true);
    setApiError("");

    try {
      const result = await getFacultyProfile();

      if (result?.success && result?.data) {
        setProfile(result.data);
      } else {
        setProfile(null);
        setApiError(result?.message || "Failed to load faculty profile.");
      }
    } catch (err) {
      setProfile(null);
      setApiError(
        err?.response?.data?.message ||
        err?.message ||
        "Unable to load faculty profile. Please try again."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function fetchProfile() {
      try {
        const result = await getFacultyProfile();

        if (cancelled) return;

        if (result?.success && result?.data) {
          setProfile(result.data);
          setApiError("");
        } else {
          setProfile(null);
          setApiError(result?.message || "Failed to load faculty profile.");
        }
      } catch (err) {
        if (cancelled) return;
        setProfile(null);
        setApiError(
          err?.response?.data?.message ||
          err?.message ||
          "Unable to load faculty profile. Please try again."
        );
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchProfile();

    return () => {
      cancelled = true;
    };
  }, []);

  // Open Edit Profile
  const handleOpenEdit = () => {
    if (!profile) return;
    setEditForm({
      name: profile.name || "",
      email: profile.email || "",
      designation: profile.designation || "",
      phone: profile.phone || "",
      gender: profile.gender || "",
      date_of_birth: profile.date_of_birth || "",
      date_of_joining: profile.date_of_joining || "",
      employment_status: profile.employment_status || "Permanent",
      qualification: profile.qualification || "",
      specialization: profile.specialization || "",
      office_cabin: profile.office_cabin || "",
      address: profile.address || "",
      city: profile.city || "",
      state: profile.state || "",
      pin_code: profile.pin_code || "",
      country: profile.country || "India",
    });
    setEditError("");
    setShowEditModal(true);
  };

  // Submit Profile Changes
  const handleEditSubmit = async (e) => {
    e.preventDefault();
    const name = editForm.name.trim();
    const email = editForm.email.trim();
    const designation = editForm.designation.trim();

    if (!name || !email || !designation) {
      setEditError("Full name, email, and designation are required.");
      return;
    }

    setEditLoading(true);
    setEditError("");

    try {
      const result = await updateFacultyProfile({
        name,
        email,
        designation,
        phone: editForm.phone.trim(),
        gender: editForm.gender.trim(),
        date_of_birth: editForm.date_of_birth.trim(),
        date_of_joining: editForm.date_of_joining.trim(),
        employment_status: editForm.employment_status.trim(),
        qualification: editForm.qualification.trim(),
        specialization: editForm.specialization.trim(),
        office_cabin: editForm.office_cabin.trim(),
        address: editForm.address.trim(),
        city: editForm.city.trim(),
        state: editForm.state.trim(),
        pin_code: editForm.pin_code.trim(),
        country: editForm.country.trim(),
      });

      if (result?.success && result?.data) {
        setProfile(result.data);
        setShowEditModal(false);
        setSuccessToast("Faculty profile updated successfully!");
        setTimeout(() => setSuccessToast(""), 4000);
      } else {
        throw new Error(result?.message || "Failed to update profile.");
      }
    } catch (err) {
      setEditError(
        err?.response?.data?.message ||
        err?.message ||
        "Unable to update profile. Please verify your details."
      );
    } finally {
      setEditLoading(false);
    }
  };

  // Submit Password Change
  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    setPasswordError("");

    const currentPassword = passwordForm.current_password.trim();
    const newPassword = passwordForm.new_password.trim();
    const confirmPassword = passwordForm.confirm_password.trim();

    if (!currentPassword || !newPassword) {
      setPasswordError("Both current password and new password are required.");
      return;
    }

    if (newPassword.length < 6) {
      setPasswordError("New password must be at least 6 characters.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setPasswordError("New password and confirm password do not match.");
      return;
    }

    setPasswordLoading(true);

    try {
      const result = await changeFacultyPassword({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });

      if (result?.success) {
        setShowPasswordModal(false);
        setPasswordForm({
          current_password: "",
          new_password: "",
          confirm_password: "",
        });
        setSuccessToast("Password changed successfully!");
        setTimeout(() => setSuccessToast(""), 4000);
      } else {
        throw new Error(result?.message || "Failed to change password.");
      }
    } catch (err) {
      setPasswordError(
        err?.response?.data?.message ||
        err?.message ||
        "Failed to change password. Please check your current password."
      );
    } finally {
      setPasswordLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="faculty-profile-container">
        <div className="faculty-profile-loading-box">
          <RefreshCw size={28} className="spin text-blue" />
          <p>Retrieving faculty profile records from backend...</p>
        </div>
      </div>
    );
  }

  if (apiError && !profile) {
    return (
      <div className="faculty-profile-container">
        <div className="faculty-profile-error-box">
          <AlertCircle size={32} className="text-amber" />
          <h2>Unable to Load Faculty Profile</h2>
          <p>{apiError}</p>
          <button
            type="button"
            className="faculty-btn-primary"
            onClick={loadProfile}
          >
            <RefreshCw size={15} /> Retry
          </button>
        </div>
      </div>
    );
  }

  const fullName = profile?.name || "Faculty Member";
  const email = profile?.email || "Not provided";
  const designation = profile?.designation || "Not specified";
  const employeeId = profile?.employee_id || "Not assigned";
  const facultyId = profile?.faculty_id ? String(profile.faculty_id) : "Not assigned";
  const userId = profile?.user_id ? String(profile.user_id) : "Not assigned";
  const departmentName =
    typeof profile?.department === "object"
      ? profile?.department?.department_name || "Department"
      : profile?.department || "Department";
  const departmentCode =
    typeof profile?.department === "object"
      ? profile?.department?.department_code || "N/A"
      : "N/A";

  const phone = profile?.phone || "Not provided";
  const gender = profile?.gender || "Not specified";
  const dateOfBirth = profile?.date_of_birth || "Not provided";
  const dateOfJoining = profile?.date_of_joining || "Not provided";
  const employmentStatus = profile?.employment_status || "Permanent";
  const qualification = profile?.qualification || "Not provided";
  const specialization = profile?.specialization || "Not provided";
  const officeCabin = profile?.office_cabin || "Not assigned";
  const address = profile?.address || "Not provided";
  const city = profile?.city || "Not provided";
  const state = profile?.state || "Not provided";
  const pinCode = profile?.pin_code || "Not provided";
  const country = profile?.country || "India";
  const accountStatus = profile?.account_status || "Active";

  const initials = getInitials(fullName);

  return (
    <div className="faculty-profile-container">
      {/* Success Notification Toast */}
      {successToast && (
        <div className="faculty-profile-toast" role="status">
          <CheckCircle2 size={18} className="toast-icon" />
          <span>{successToast}</span>
          <button
            type="button"
            className="toast-close"
            onClick={() => setSuccessToast("")}
          >
            <X size={15} />
          </button>
        </div>
      )}

      {/* Top Hero Banner */}
      <section className="faculty-profile-hero">
        <div className="faculty-hero-cover" />

        <div className="faculty-hero-body">
          <div className="faculty-hero-avatar-wrap">
            <div className="faculty-hero-avatar">{initials}</div>
            <span className="faculty-avatar-online" title="Account Active" />
          </div>

          <div className="faculty-hero-info">
            <div className="faculty-hero-title-row">
              <h1 className="faculty-hero-name">{fullName}</h1>
              <span className="faculty-verified-badge" title="Verified Faculty">
                <BadgeCheck size={16} /> Verified Faculty
              </span>
            </div>

            <p className="faculty-hero-sub">
              <span className="hero-designation">{designation}</span>
              <span className="hero-separator">•</span>
              <span className="hero-department">{departmentName}</span>
            </p>

            <div className="faculty-hero-meta-row">
              <span className="faculty-meta-chip">
                <Hash size={13} /> Employee ID: {employeeId}
              </span>
              <span className="faculty-meta-chip">
                <Mail size={13} /> {email}
              </span>
              {phone !== "Not provided" && (
                <span className="faculty-meta-chip">
                  <Phone size={13} /> {phone}
                </span>
              )}
              <span className="faculty-meta-chip">
                <Building size={13} /> Code: {departmentCode}
              </span>
            </div>
          </div>

          <div className="faculty-hero-actions">
            <button
              type="button"
              className="faculty-btn-primary"
              onClick={handleOpenEdit}
            >
              <Edit3 size={15} /> Edit Profile
            </button>

            <button
              type="button"
              className="faculty-btn-secondary"
              onClick={() => {
                setPasswordError("");
                setShowPasswordModal(true);
              }}
            >
              <KeyRound size={15} /> Password
            </button>

            <button
              type="button"
              className="faculty-btn-icon"
              onClick={loadProfile}
              title="Refresh Profile"
              disabled={loading}
            >
              <RefreshCw size={15} className={loading ? "spin" : ""} />
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="faculty-profile-tabs">
          <button
            type="button"
            className={`faculty-tab-btn ${activeTab === "overview" ? "active" : ""}`}
            onClick={() => setActiveTab("overview")}
          >
            <GraduationCap size={16} /> Academic &amp; Overview
          </button>

          <button
            type="button"
            className={`faculty-tab-btn ${activeTab === "personal" ? "active" : ""}`}
            onClick={() => setActiveTab("personal")}
          >
            <User size={16} /> Personal &amp; Contact
          </button>

          <button
            type="button"
            className={`faculty-tab-btn ${activeTab === "security" ? "active" : ""}`}
            onClick={() => setActiveTab("security")}
          >
            <Shield size={16} /> Security &amp; System
          </button>
        </div>
      </section>

      {/* Main Grid Content */}
      <div className="faculty-profile-grid">
        {/* Left Column: Quick Cards */}
        <div className="faculty-profile-sidebar-col">
          {/* Card: Academic Snapshot */}
          <div className="faculty-card">
            <div className="faculty-card-header">
              <div className="faculty-card-icon-box bg-blue">
                <Award size={18} />
              </div>
              <h3 className="faculty-card-title">Academic Snapshot</h3>
            </div>

            <div className="faculty-card-body faculty-snapshot-list">
              <div className="faculty-snapshot-item">
                <span className="snapshot-label">Designation</span>
                <strong className="snapshot-value">{designation}</strong>
              </div>

              <div className="faculty-snapshot-item">
                <span className="snapshot-label">Department</span>
                <strong className="snapshot-value">{departmentName}</strong>
              </div>

              <div className="faculty-snapshot-item">
                <span className="snapshot-label">Department Code</span>
                <strong className="snapshot-value badge-pill">{departmentCode}</strong>
              </div>

              <div className="faculty-snapshot-item">
                <span className="snapshot-label">Employee ID</span>
                <strong className="snapshot-value">{employeeId}</strong>
              </div>

              <div className="faculty-snapshot-item">
                <span className="snapshot-label">Employment Status</span>
                <strong className="snapshot-value text-emerald">{employmentStatus}</strong>
              </div>

              <div className="faculty-snapshot-item">
                <span className="snapshot-label">Date of Joining</span>
                <strong className="snapshot-value">{dateOfJoining}</strong>
              </div>
            </div>
          </div>

          {/* Card: Biometrics & Face Recognition */}
          <div className="faculty-card">
            <div className="faculty-card-header">
              <div className="faculty-card-icon-box bg-emerald">
                <Sparkles size={18} />
              </div>
              <h3 className="faculty-card-title">Biometrics &amp; SAMS-FR</h3>
            </div>

            <div className="faculty-card-body">
              <div className="faculty-bio-status-box">
                <div className="faculty-bio-indicator">
                  <span className="pulse-green-dot" />
                  <strong>Face Recognition Active</strong>
                </div>
                <p className="faculty-bio-text">
                  Facial embeddings are active for automated classroom recognition and attendance session validation.
                </p>
              </div>

              <div className="faculty-bio-details">
                <div className="bio-detail-row">
                  <span>Recognition Status</span>
                  <span className="bio-badge-active">Active</span>
                </div>
                <div className="bio-detail-row">
                  <span>Portal Role</span>
                  <strong>FACULTY</strong>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Dynamic Tabs Content */}
        <div className="faculty-profile-main-col">
          {activeTab === "overview" && (
            <div className="faculty-tab-content-pane">
              {/* Card 1: Professional Qualifications */}
              <div className="faculty-card">
                <div className="faculty-card-header">
                  <div className="faculty-card-icon-box bg-purple">
                    <GraduationCap size={18} />
                  </div>
                  <div>
                    <h3 className="faculty-card-title">Professional Qualifications &amp; Expertise</h3>
                    <p className="faculty-card-sub">Teaching credentials, academic background, and specialization.</p>
                  </div>
                </div>

                <div className="faculty-details-grid">
                  <div className="faculty-field-item">
                    <span className="field-label">Primary Department</span>
                    <strong className="field-value">{departmentName}</strong>
                  </div>

                  <div className="faculty-field-item">
                    <span className="field-label">Designation</span>
                    <strong className="field-value">{designation}</strong>
                  </div>

                  <div className="faculty-field-item span-2">
                    <span className="field-label">Academic Qualification</span>
                    <strong className="field-value">{qualification}</strong>
                  </div>

                  <div className="faculty-field-item span-2">
                    <span className="field-label">Specialization &amp; Research</span>
                    <strong className="field-value">{specialization}</strong>
                  </div>

                  <div className="faculty-field-item">
                    <span className="field-label">Office / Cabin</span>
                    <strong className="field-value">{officeCabin}</strong>
                  </div>

                  <div className="faculty-field-item">
                    <span className="field-label">Employment Status</span>
                    <strong className="field-value text-emerald">{employmentStatus}</strong>
                  </div>
                </div>
              </div>

              {/* Card 2: System Identifiers */}
              <div className="faculty-card">
                <div className="faculty-card-header">
                  <div className="faculty-card-icon-box bg-blue">
                    <FileText size={18} />
                  </div>
                  <div>
                    <h3 className="faculty-card-title">Institutional Identifiers</h3>
                    <p className="faculty-card-sub">Employee and system identification records from the database.</p>
                  </div>
                </div>

                <div className="faculty-details-grid">
                  <div className="faculty-field-item">
                    <span className="field-label">Employee ID</span>
                    <strong className="field-value code-font">{employeeId}</strong>
                  </div>

                  <div className="faculty-field-item">
                    <span className="field-label">Faculty Record ID</span>
                    <strong className="field-value code-font">{facultyId}</strong>
                  </div>

                  <div className="faculty-field-item">
                    <span className="field-label">System User ID</span>
                    <strong className="field-value code-font">{userId}</strong>
                  </div>

                  <div className="faculty-field-item">
                    <span className="field-label">Account Status</span>
                    <strong className="field-value text-emerald">{accountStatus}</strong>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "personal" && (
            <div className="faculty-tab-content-pane">
              {/* Card 1: Personal Details */}
              <div className="faculty-card">
                <div className="faculty-card-header">
                  <div className="faculty-card-icon-box bg-blue">
                    <User size={18} />
                  </div>
                  <div>
                    <h3 className="faculty-card-title">Personal Details</h3>
                    <p className="faculty-card-sub">Basic personal identity records on file.</p>
                  </div>
                </div>

                <div className="faculty-details-grid">
                  <div className="faculty-field-item">
                    <span className="field-label">Full Name</span>
                    <strong className="field-value">{fullName}</strong>
                  </div>

                  <div className="faculty-field-item">
                    <span className="field-label">Official Email</span>
                    <strong className="field-value">{email}</strong>
                  </div>

                  <div className="faculty-field-item">
                    <span className="field-label">Phone Number</span>
                    <strong className="field-value">{phone}</strong>
                  </div>

                  <div className="faculty-field-item">
                    <span className="field-label">Gender</span>
                    <strong className="field-value">{gender}</strong>
                  </div>

                  <div className="faculty-field-item">
                    <span className="field-label">Date of Birth</span>
                    <strong className="field-value">{dateOfBirth}</strong>
                  </div>

                  <div className="faculty-field-item">
                    <span className="field-label">Date of Joining</span>
                    <strong className="field-value">{dateOfJoining}</strong>
                  </div>
                </div>
              </div>

              {/* Card 2: Campus & Location Details */}
              <div className="faculty-card">
                <div className="faculty-card-header">
                  <div className="faculty-card-icon-box bg-purple">
                    <MapPin size={18} />
                  </div>
                  <div>
                    <h3 className="faculty-card-title">Campus &amp; Address</h3>
                    <p className="faculty-card-sub">Campus location and contact coordinates.</p>
                  </div>
                </div>

                <div className="faculty-details-grid">
                  <div className="faculty-field-item span-2">
                    <span className="field-label">Campus Address</span>
                    <strong className="field-value">{address}</strong>
                  </div>

                  <div className="faculty-field-item">
                    <span className="field-label">City</span>
                    <strong className="field-value">{city}</strong>
                  </div>

                  <div className="faculty-field-item">
                    <span className="field-label">State / Region</span>
                    <strong className="field-value">{state}</strong>
                  </div>

                  <div className="faculty-field-item">
                    <span className="field-label">PIN Code</span>
                    <strong className="field-value">{pinCode}</strong>
                  </div>

                  <div className="faculty-field-item">
                    <span className="field-label">Country</span>
                    <strong className="field-value">{country}</strong>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "security" && (
            <div className="faculty-tab-content-pane">
              {/* Card: Account Security */}
              <div className="faculty-card">
                <div className="faculty-card-header">
                  <div className="faculty-card-icon-box bg-emerald">
                    <Shield size={18} />
                  </div>
                  <div>
                    <h3 className="faculty-card-title">Account Security &amp; Credentials</h3>
                    <p className="faculty-card-sub">Manage password and security verification settings.</p>
                  </div>
                </div>

                <div className="faculty-security-content">
                  <div className="faculty-security-row">
                    <div className="faculty-security-info">
                      <div className="security-title-row">
                        <Lock size={16} className="text-blue" />
                        <strong>Account Password</strong>
                      </div>
                      <p>
                        Password is encrypted and stored via secure bcrypt hash. You can update your password at any time.
                      </p>
                    </div>

                    <button
                      type="button"
                      className="faculty-btn-secondary"
                      onClick={() => {
                        setPasswordError("");
                        setShowPasswordModal(true);
                      }}
                    >
                      <KeyRound size={14} /> Change Password
                    </button>
                  </div>

                  <div className="faculty-security-row">
                    <div className="faculty-security-info">
                      <div className="security-title-row">
                        <CheckCircle2 size={16} className="text-emerald" />
                        <strong>Authentication Method</strong>
                      </div>
                      <p>
                        Email/Password authentication with JWT cookie + Face Recognition verification during active attendance.
                      </p>
                    </div>

                    <span className="security-badge-active">Enabled</span>
                  </div>

                  <div className="faculty-security-notice">
                    <CheckCircle2 size={15} className="text-emerald" />
                    <span>
                      All profile details, academic records, and account credentials are fully synchronized with the university backend database.
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Edit Profile Modal Dialog */}
      {showEditModal && (
        <div
          className="faculty-modal-backdrop"
          onClick={(e) => {
            if (e.target === e.currentTarget && !editLoading) {
              setShowEditModal(false);
            }
          }}
        >
          <div className="faculty-edit-modal-card" role="dialog" aria-modal="true">
            <div className="faculty-edit-modal-header">
              <div>
                <span className="modal-eyebrow">Profile Management</span>
                <h3 className="modal-title">Edit Faculty Profile</h3>
                <p className="modal-sub">Update your official information in the backend database.</p>
              </div>

              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setShowEditModal(false)}
                disabled={editLoading}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleEditSubmit}>
              <div className="modal-fields-grid">
                {/* Full Name */}
                <div className="modal-field-group">
                  <label htmlFor="edit-name-input">Full Name *</label>
                  <input
                    id="edit-name-input"
                    type="text"
                    value={editForm.name}
                    onChange={(e) =>
                      setEditForm((prev) => ({ ...prev, name: e.target.value }))
                    }
                    placeholder="Enter full name"
                    disabled={editLoading}
                    required
                  />
                </div>

                {/* Email */}
                <div className="modal-field-group">
                  <label htmlFor="edit-email-input">Official Email *</label>
                  <input
                    id="edit-email-input"
                    type="email"
                    value={editForm.email}
                    onChange={(e) =>
                      setEditForm((prev) => ({ ...prev, email: e.target.value }))
                    }
                    placeholder="Official email address"
                    disabled={editLoading}
                    required
                  />
                </div>

                {/* Designation */}
                <div className="modal-field-group">
                  <label htmlFor="edit-designation-input">Academic Designation *</label>
                  <input
                    id="edit-designation-input"
                    type="text"
                    value={editForm.designation}
                    onChange={(e) =>
                      setEditForm((prev) => ({ ...prev, designation: e.target.value }))
                    }
                    placeholder="e.g. Professor, Associate Professor"
                    disabled={editLoading}
                    required
                  />
                </div>

                {/* Phone */}
                <div className="modal-field-group">
                  <label htmlFor="edit-phone-input">Phone Number</label>
                  <input
                    id="edit-phone-input"
                    type="tel"
                    value={editForm.phone}
                    onChange={(e) =>
                      setEditForm((prev) => ({ ...prev, phone: e.target.value }))
                    }
                    placeholder="e.g. +91 98765 43210"
                    disabled={editLoading}
                  />
                </div>

                {/* Gender */}
                <div className="modal-field-group">
                  <label htmlFor="edit-gender-input">Gender</label>
                  <select
                    id="edit-gender-input"
                    value={editForm.gender}
                    onChange={(e) =>
                      setEditForm((prev) => ({ ...prev, gender: e.target.value }))
                    }
                    disabled={editLoading}
                  >
                    <option value="">Select Gender</option>
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Other">Other</option>
                  </select>
                </div>

                {/* Date of Birth */}
                <div className="modal-field-group">
                  <label htmlFor="edit-dob-input">Date of Birth</label>
                  <input
                    id="edit-dob-input"
                    type="date"
                    value={editForm.date_of_birth}
                    onChange={(e) =>
                      setEditForm((prev) => ({ ...prev, date_of_birth: e.target.value }))
                    }
                    disabled={editLoading}
                  />
                </div>

                {/* Date of Joining */}
                <div className="modal-field-group">
                  <label htmlFor="edit-doj-input">Date of Joining</label>
                  <input
                    id="edit-doj-input"
                    type="date"
                    value={editForm.date_of_joining}
                    onChange={(e) =>
                      setEditForm((prev) => ({ ...prev, date_of_joining: e.target.value }))
                    }
                    disabled={editLoading}
                  />
                </div>

                {/* Employment Status */}
                <div className="modal-field-group">
                  <label htmlFor="edit-status-input">Employment Status</label>
                  <select
                    id="edit-status-input"
                    value={editForm.employment_status}
                    onChange={(e) =>
                      setEditForm((prev) => ({ ...prev, employment_status: e.target.value }))
                    }
                    disabled={editLoading}
                  >
                    <option value="Permanent">Permanent</option>
                    <option value="Contract">Contract</option>
                    <option value="Visiting">Visiting</option>
                    <option value="Probation">Probation</option>
                  </select>
                </div>

                {/* Qualification */}
                <div className="modal-field-group modal-field-span-2">
                  <label htmlFor="edit-qualification-input">Academic Qualification</label>
                  <input
                    id="edit-qualification-input"
                    type="text"
                    value={editForm.qualification}
                    onChange={(e) =>
                      setEditForm((prev) => ({ ...prev, qualification: e.target.value }))
                    }
                    placeholder="e.g. Ph.D. in Computer Science, M.Tech, B.Tech"
                    disabled={editLoading}
                  />
                </div>

                {/* Specialization */}
                <div className="modal-field-group modal-field-span-2">
                  <label htmlFor="edit-specialization-input">Specialization &amp; Research</label>
                  <input
                    id="edit-specialization-input"
                    type="text"
                    value={editForm.specialization}
                    onChange={(e) =>
                      setEditForm((prev) => ({ ...prev, specialization: e.target.value }))
                    }
                    placeholder="e.g. Machine Learning, Computer Vision, Data Science"
                    disabled={editLoading}
                  />
                </div>

                {/* Office Cabin */}
                <div className="modal-field-group">
                  <label htmlFor="edit-cabin-input">Office / Cabin</label>
                  <input
                    id="edit-cabin-input"
                    type="text"
                    value={editForm.office_cabin}
                    onChange={(e) =>
                      setEditForm((prev) => ({ ...prev, office_cabin: e.target.value }))
                    }
                    placeholder="e.g. Block B, Room 304"
                    disabled={editLoading}
                  />
                </div>

                {/* City */}
                <div className="modal-field-group">
                  <label htmlFor="edit-city-input">City</label>
                  <input
                    id="edit-city-input"
                    type="text"
                    value={editForm.city}
                    onChange={(e) =>
                      setEditForm((prev) => ({ ...prev, city: e.target.value }))
                    }
                    placeholder="City"
                    disabled={editLoading}
                  />
                </div>

                {/* Campus Address */}
                <div className="modal-field-group modal-field-span-2">
                  <label htmlFor="edit-address-input">Campus Address</label>
                  <input
                    id="edit-address-input"
                    type="text"
                    value={editForm.address}
                    onChange={(e) =>
                      setEditForm((prev) => ({ ...prev, address: e.target.value }))
                    }
                    placeholder="Address / Faculty Quarters"
                    disabled={editLoading}
                  />
                </div>

                {/* State */}
                <div className="modal-field-group">
                  <label htmlFor="edit-state-input">State / Region</label>
                  <input
                    id="edit-state-input"
                    type="text"
                    value={editForm.state}
                    onChange={(e) =>
                      setEditForm((prev) => ({ ...prev, state: e.target.value }))
                    }
                    placeholder="State"
                    disabled={editLoading}
                  />
                </div>

                {/* PIN Code */}
                <div className="modal-field-group">
                  <label htmlFor="edit-pincode-input">PIN Code</label>
                  <input
                    id="edit-pincode-input"
                    type="text"
                    value={editForm.pin_code}
                    onChange={(e) =>
                      setEditForm((prev) => ({ ...prev, pin_code: e.target.value }))
                    }
                    placeholder="e.g. 110001"
                    disabled={editLoading}
                  />
                </div>
              </div>

              {editError && (
                <div className="modal-error-box">
                  <AlertCircle size={15} />
                  <span>{editError}</span>
                </div>
              )}

              <p className="modal-note-text">
                Submitting updates your faculty record in the backend via <code>PATCH /api/faculty/profile</code>.
              </p>

              <div className="modal-actions-row">
                <button
                  type="button"
                  className="faculty-btn-secondary"
                  onClick={() => setShowEditModal(false)}
                  disabled={editLoading}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="faculty-btn-primary"
                  disabled={editLoading}
                >
                  {editLoading ? "Saving Changes..." : "Save Changes"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Change Password Modal Dialog */}
      {showPasswordModal && (
        <div
          className="faculty-modal-backdrop"
          onClick={(e) => {
            if (e.target === e.currentTarget && !passwordLoading) {
              setShowPasswordModal(false);
            }
          }}
        >
          <div className="faculty-edit-modal-card" style={{ maxWidth: "480px" }} role="dialog" aria-modal="true">
            <div className="faculty-edit-modal-header">
              <div>
                <span className="modal-eyebrow">Account Security</span>
                <h3 className="modal-title">Change Password</h3>
                <p className="modal-sub">Update your account login password securely.</p>
              </div>

              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setShowPasswordModal(false)}
                disabled={passwordLoading}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handlePasswordSubmit}>
              <div className="modal-fields-stack">
                <div className="modal-field-group">
                  <label htmlFor="current-password-input">Current Password *</label>
                  <div className="modal-input-password-wrap">
                    <input
                      id="current-password-input"
                      type={showCurrentPassword ? "text" : "password"}
                      value={passwordForm.current_password}
                      onChange={(e) =>
                        setPasswordForm((prev) => ({
                          ...prev,
                          current_password: e.target.value,
                        }))
                      }
                      placeholder="Enter current password"
                      disabled={passwordLoading}
                      required
                    />
                    <button
                      type="button"
                      className="modal-password-toggle"
                      onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                      tabIndex="-1"
                    >
                      {showCurrentPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>

                <div className="modal-field-group">
                  <label htmlFor="new-password-input">New Password *</label>
                  <div className="modal-input-password-wrap">
                    <input
                      id="new-password-input"
                      type={showNewPassword ? "text" : "password"}
                      value={passwordForm.new_password}
                      onChange={(e) =>
                        setPasswordForm((prev) => ({
                          ...prev,
                          new_password: e.target.value,
                        }))
                      }
                      placeholder="Minimum 6 characters"
                      disabled={passwordLoading}
                      required
                    />
                    <button
                      type="button"
                      className="modal-password-toggle"
                      onClick={() => setShowNewPassword(!showNewPassword)}
                      tabIndex="-1"
                    >
                      {showNewPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>

                <div className="modal-field-group">
                  <label htmlFor="confirm-password-input">Confirm New Password *</label>
                  <div className="modal-input-password-wrap">
                    <input
                      id="confirm-password-input"
                      type={showConfirmPassword ? "text" : "password"}
                      value={passwordForm.confirm_password}
                      onChange={(e) =>
                        setPasswordForm((prev) => ({
                          ...prev,
                          confirm_password: e.target.value,
                        }))
                      }
                      placeholder="Re-enter new password"
                      disabled={passwordLoading}
                      required
                    />
                    <button
                      type="button"
                      className="modal-password-toggle"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      tabIndex="-1"
                    >
                      {showConfirmPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>
              </div>

              {passwordError && (
                <div className="modal-error-box">
                  <AlertCircle size={15} />
                  <span>{passwordError}</span>
                </div>
              )}

              <p className="modal-note-text">
                Password will be securely encrypted with bcrypt via <code>POST /api/faculty/change-password</code>.
              </p>

              <div className="modal-actions-row">
                <button
                  type="button"
                  className="faculty-btn-secondary"
                  onClick={() => setShowPasswordModal(false)}
                  disabled={passwordLoading}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="faculty-btn-primary"
                  disabled={passwordLoading}
                >
                  {passwordLoading ? "Updating..." : "Update Password"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Profile;
