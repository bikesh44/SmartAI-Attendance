import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faUser,
  faEnvelope,
  faGraduationCap,
  faLocationDot,
  faLock,
  faSignature,
  faCircleCheck,
  faXmark,
  faPhone,
  faUsers,
  faDroplet,
  faCalendarDays,
  faCamera,
  faPenToSquare,
  faKey,
  faRotateRight,
  faShieldHalved,
  faTriangleExclamation,
  faSpinner,
  faFloppyDisk,
  faEye,
  faEyeSlash,
  faBookOpen,
  faBuilding,
  faIdCard,
  faFileImage,
  faArrowUpFromBracket,
  faHouse,
  faCity,
  faMapPin,
  faEarthAmericas,
  faVenusMars,
  faCheck,
} from "@fortawesome/free-solid-svg-icons";

import {
  getStudentProfile,
  updateStudentProfile,
  uploadStudentPhoto,
  uploadStudentSignature,
  changeStudentPassword,
} from "../../services/studentService";
import "./Profile.css";

const MAX_FILE_SIZE_BYTES = 50 * 1024; // Strictly 50 KB

function getInitials(name) {
  if (!name || typeof name !== "string") return "ST";
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return (
    parts
      .slice(0, 2)
      .map((part) => part.charAt(0).toUpperCase())
      .join("") || "ST"
  );
}

function getPasswordStrength(password) {
  if (!password) {
    return { label: "Enter a password", level: 0 };
  }
  let score = 0;
  if (password.length >= 8) score += 1;
  if (/[A-Z]/.test(password)) score += 1;
  if (/[0-9]/.test(password)) score += 1;
  if (/[^A-Za-z0-9]/.test(password)) score += 1;

  if (score <= 1) return { label: "Weak", level: 1 };
  if (score <= 2) return { label: "Moderate", level: 2 };
  if (score <= 3) return { label: "Strong", level: 3 };
  return { label: "Very strong", level: 4 };
}

function Profile() {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [activeTab, setActiveTab] = useState("all"); // 'all', 'personal', 'academic', 'address', 'documents'

  // Photo & Signature State + Fallback handling
  const photoInputRef = useRef(null);
  const signatureInputRef = useRef(null);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);
  const [uploadingSignature, setUploadingSignature] = useState(false);
  const [photoError, setPhotoError] = useState("");
  const [signatureError, setSignatureError] = useState("");
  const [photoLoadFailed, setPhotoLoadFailed] = useState(false);
  const [sigLoadFailed, setSigLoadFailed] = useState(false);

  // Edit Profile Modal State
  const [showEditModal, setShowEditModal] = useState(false);
  const [editLoading, setEditLoading] = useState(false);
  const [editError, setEditError] = useState("");
  const [editForm, setEditForm] = useState({
    name: "",
    phone: "",
    father_name: "",
    mother_name: "",
    guardian_phone: "",
    blood_group: "",
    gender: "",
    date_of_birth: "",
    address: "",
    city: "",
    state: "",
    pin_code: "",
    country: "India",
    emergency_contact_name: "",
    emergency_contact_phone: "",
  });

  // Password Modal State
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [passwordError, setPasswordError] = useState("");
  const [passwordForm, setPasswordForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const loadProfileData = useCallback(async (isRefresh = false) => {
    try {
      if (isRefresh) setRefreshing(true);
      else setLoading(true);
      setErrorMessage("");

      const response = await getStudentProfile();

      if (!response?.success || !response?.data) {
        throw new Error(response?.message || "Failed to load student profile.");
      }

      setProfile(response.data);
      setPhotoLoadFailed(false);
      setSigLoadFailed(false);

      if (isRefresh) {
        setSuccessMessage("Student records synchronized from database.");
        setTimeout(() => setSuccessMessage(""), 4000);
      }
    } catch (err) {
      setErrorMessage(
        err?.response?.data?.message ||
          err?.message ||
          "Unable to load student profile records."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    let mounted = true;

    async function initialFetch() {
      try {
        setLoading(true);
        setErrorMessage("");
        const response = await getStudentProfile();
        if (!mounted) return;

        if (!response?.success || !response?.data) {
          throw new Error(
            response?.message || "Failed to load student profile."
          );
        }
        setProfile(response.data);
      } catch (err) {
        if (!mounted) return;
        setErrorMessage(
          err?.response?.data?.message ||
            err?.message ||
            "Unable to load student profile records."
        );
      } finally {
        if (mounted) setLoading(false);
      }
    }

    initialFetch();

    return () => {
      mounted = false;
    };
  }, []);

  // Open Edit Profile
  const handleOpenEdit = () => {
    if (!profile) return;
    setEditForm({
      name: profile.name || "",
      phone: profile.phone || "",
      father_name: profile.father_name || "",
      mother_name: profile.mother_name || "",
      guardian_phone: profile.guardian_phone || "",
      blood_group: profile.blood_group || "",
      gender: profile.gender || "",
      date_of_birth: profile.date_of_birth || "",
      address: profile.address || "",
      city: profile.city || "",
      state: profile.state || "",
      pin_code: profile.pin_code || "",
      country: profile.country || "India",
      emergency_contact_name: profile.emergency_contact_name || "",
      emergency_contact_phone: profile.emergency_contact_phone || "",
    });
    setEditError("");
    setShowEditModal(true);
  };

  // Submit Profile Edits
  const handleEditSubmit = async (e) => {
    e.preventDefault();
    setEditError("");

    const name = editForm.name.trim();
    if (!name) {
      setEditError("Full name is required.");
      return;
    }

    setEditLoading(true);

    try {
      const response = await updateStudentProfile(editForm);

      if (!response?.success || !response?.data) {
        throw new Error(response?.message || "Failed to update profile.");
      }

      setProfile(response.data);
      setShowEditModal(false);
      setSuccessMessage("Student details updated successfully in database.");
      setTimeout(() => setSuccessMessage(""), 4500);
    } catch (err) {
      setEditError(
        err?.response?.data?.message ||
          err?.message ||
          "Failed to update profile details."
      );
    } finally {
      setEditLoading(false);
    }
  };

  // Handle Photo File Selection & Upload (< 50 KB Strict)
  const handlePhotoSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setPhotoError("");

    // Strict Size Check (< 50 KB)
    if (file.size > MAX_FILE_SIZE_BYTES) {
      const sizeKb = (file.size / 1024).toFixed(1);
      setPhotoError(
        `Passport photo must be strictly less than 50 KB. (Selected file: ${sizeKb} KB). Please resize or compress your image.`
      );
      if (photoInputRef.current) photoInputRef.current.value = "";
      return;
    }

    // Strict Extension Check
    const ext = file.name.split(".").pop().toLowerCase();
    if (!["jpg", "jpeg", "png", "webp"].includes(ext)) {
      setPhotoError("Please select a valid image file (JPG, PNG, or WebP).");
      if (photoInputRef.current) photoInputRef.current.value = "";
      return;
    }

    setUploadingPhoto(true);

    try {
      const response = await uploadStudentPhoto(file);

      if (!response?.success) {
        throw new Error(response?.message || "Failed to upload photo.");
      }

      setProfile((prev) => ({
        ...prev,
        photo_url: response.photo_url,
      }));
      setPhotoLoadFailed(false);

      setSuccessMessage("Passport-size photo (< 50 KB) uploaded and saved!");
      setTimeout(() => setSuccessMessage(""), 4500);
    } catch (err) {
      setPhotoError(
        err?.response?.data?.message ||
          err?.message ||
          "Failed to upload passport photo."
      );
    } finally {
      setUploadingPhoto(false);
      if (photoInputRef.current) photoInputRef.current.value = "";
    }
  };

  // Handle Signature File Selection & Upload (< 50 KB Strict)
  const handleSignatureSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setSignatureError("");

    // Strict Size Check (< 50 KB)
    if (file.size > MAX_FILE_SIZE_BYTES) {
      const sizeKb = (file.size / 1024).toFixed(1);
      setSignatureError(
        `Signature file must be strictly less than 50 KB. (Selected file: ${sizeKb} KB). Please resize or crop your signature.`
      );
      if (signatureInputRef.current) signatureInputRef.current.value = "";
      return;
    }

    // Strict Extension Check
    const ext = file.name.split(".").pop().toLowerCase();
    if (!["jpg", "jpeg", "png", "webp"].includes(ext)) {
      setSignatureError("Please select a valid image file (PNG or JPG).");
      if (signatureInputRef.current) signatureInputRef.current.value = "";
      return;
    }

    setUploadingSignature(true);

    try {
      const response = await uploadStudentSignature(file);

      if (!response?.success) {
        throw new Error(response?.message || "Failed to upload signature.");
      }

      setProfile((prev) => ({
        ...prev,
        signature_url: response.signature_url,
      }));
      setSigLoadFailed(false);

      setSuccessMessage("Signature (< 50 KB) uploaded and saved!");
      setTimeout(() => setSuccessMessage(""), 4500);
    } catch (err) {
      setSignatureError(
        err?.response?.data?.message ||
          err?.message ||
          "Failed to upload signature."
      );
    } finally {
      setUploadingSignature(false);
      if (signatureInputRef.current) signatureInputRef.current.value = "";
    }
  };

  // Handle Password Submit
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
      const response = await changeStudentPassword({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });

      if (!response?.success) {
        throw new Error(response?.message || "Failed to change password.");
      }

      setShowPasswordModal(false);
      setPasswordForm({
        current_password: "",
        new_password: "",
        confirm_password: "",
      });
      setSuccessMessage("Account password updated successfully!");
      setTimeout(() => setSuccessMessage(""), 4500);
    } catch (err) {
      setPasswordError(
        err?.response?.data?.message ||
          err?.message ||
          "Failed to change password. Please verify your current password."
      );
    } finally {
      setPasswordLoading(false);
    }
  };

  const passwordStrength = useMemo(
    () => getPasswordStrength(passwordForm.new_password),
    [passwordForm.new_password]
  );

  const initials = useMemo(
    () => getInitials(profile?.name),
    [profile?.name]
  );

  if (loading) {
    return (
      <section className="student-profile">
        <div className="student-profile-state">
          <div className="student-profile-state-icon">
            <FontAwesomeIcon icon={faSpinner} spin />
          </div>
          <h2>Loading Student Profile</h2>
          <p>
            Fetching verified academic records, personal information, and uploaded
            media credentials from the university database.
          </p>
        </div>
      </section>
    );
  }

  if (errorMessage && !profile) {
    return (
      <section className="student-profile">
        <div className="student-profile-state student-profile-state-error">
          <div className="student-profile-state-icon">
            <FontAwesomeIcon icon={faTriangleExclamation} />
          </div>
          <h2>Unable to Load Profile</h2>
          <p>{errorMessage}</p>
          <button
            type="button"
            className="student-profile-primary-button"
            onClick={() => loadProfileData(false)}
          >
            <FontAwesomeIcon icon={faRotateRight} /> Try Again
          </button>
        </div>
      </section>
    );
  }

  const deptName = profile.department?.department_name || "Computer Science Engineering";
  const deptCode = profile.department?.department_code || "CSE";
  const batchName = profile.batch_year || profile.batch?.batch_name || "—";
  const stats = profile.stats || {};

  const hasPhoto = Boolean(profile.photo_url && !photoLoadFailed);
  const hasSignature = Boolean(profile.signature_url && !sigLoadFailed);

  return (
    <section className="student-profile">
      {/* Hidden file inputs for photo & signature */}
      <input
        type="file"
        ref={photoInputRef}
        onChange={handlePhotoSelect}
        accept="image/png, image/jpeg, image/jpg, image/webp"
        style={{ display: "none" }}
      />
      <input
        type="file"
        ref={signatureInputRef}
        onChange={handleSignatureSelect}
        accept="image/png, image/jpeg, image/jpg, image/webp"
        style={{ display: "none" }}
      />

      {/* Page Header */}
      <div className="student-profile-header">
        <div>
          <span className="student-profile-eyebrow">
            Student Identification &amp; Records
          </span>
          <h1>Student Profile</h1>
          <p>
            Official institutional record of academic enrollment, family credentials,
            contact coordinates, and digital verified media.
          </p>
        </div>

        <div className="student-profile-account-status">
          <span>Student Portal</span>
          <strong>
            <span className="student-profile-status-dot" />
            {profile.account_status || "Active"} • Verified
          </strong>
        </div>
      </div>

      {/* Global Alerts / Toasts */}
      {successMessage && (
        <div className="student-profile-alert student-profile-alert-success" role="status">
          <div className="student-profile-alert-icon">
            <FontAwesomeIcon icon={faCircleCheck} />
          </div>
          <div>
            <strong>Success</strong>
            <span>{successMessage}</span>
          </div>
          <button
            type="button"
            className="student-profile-alert-close"
            onClick={() => setSuccessMessage("")}
            aria-label="Dismiss"
          >
            <FontAwesomeIcon icon={faXmark} />
          </button>
        </div>
      )}

      {errorMessage && (
        <div className="student-profile-alert student-profile-alert-error" role="alert">
          <div className="student-profile-alert-icon">
            <FontAwesomeIcon icon={faTriangleExclamation} />
          </div>
          <div>
            <strong>Attention</strong>
            <span>{errorMessage}</span>
          </div>
          <button
            type="button"
            className="student-profile-alert-close"
            onClick={() => setErrorMessage("")}
            aria-label="Dismiss"
          >
            <FontAwesomeIcon icon={faXmark} />
          </button>
        </div>
      )}

      {photoError && (
        <div className="student-profile-alert student-profile-alert-error" role="alert">
          <div className="student-profile-alert-icon">
            <FontAwesomeIcon icon={faTriangleExclamation} />
          </div>
          <div>
            <strong>Passport Photo Error</strong>
            <span>{photoError}</span>
          </div>
          <button
            type="button"
            className="student-profile-alert-close"
            onClick={() => setPhotoError("")}
            aria-label="Dismiss"
          >
            <FontAwesomeIcon icon={faXmark} />
          </button>
        </div>
      )}

      {signatureError && (
        <div className="student-profile-alert student-profile-alert-error" role="alert">
          <div className="student-profile-alert-icon">
            <FontAwesomeIcon icon={faTriangleExclamation} />
          </div>
          <div>
            <strong>Signature Error</strong>
            <span>{signatureError}</span>
          </div>
          <button
            type="button"
            className="student-profile-alert-close"
            onClick={() => setSignatureError("")}
            aria-label="Dismiss"
          >
            <FontAwesomeIcon icon={faXmark} />
          </button>
        </div>
      )}

      {/* Hero Overview Card */}
      <section className="student-profile-overview">
        {/* Passport Photo Frame in Hero */}
        <div className="student-hero-photo-wrap">
          {hasPhoto ? (
            <img
              src={profile.photo_url}
              alt="Student Passport"
              className="student-hero-photo-img"
              onError={() => setPhotoLoadFailed(true)}
            />
          ) : (
            <div className="student-hero-avatar-fallback">
              <span className="fallback-initials">{initials}</span>
              <span className="fallback-label">Photo</span>
            </div>
          )}

          <button
            type="button"
            className="student-hero-photo-btn"
            onClick={() => photoInputRef.current?.click()}
            title="Upload Passport Photo (< 50 KB)"
            disabled={uploadingPhoto}
          >
            {uploadingPhoto ? (
              <FontAwesomeIcon icon={faSpinner} spin />
            ) : (
              <>
                <FontAwesomeIcon icon={faCamera} />
                <span>Upload</span>
              </>
            )}
          </button>
        </div>

        <div className="student-profile-overview-content">
          <div className="student-hero-badges-row">
            <span className="student-enrollment-tag">
              ID: {profile.enrollment_no}
            </span>
            <span className="student-hero-dept-chip">
              {deptCode} • {deptName}
            </span>
          </div>

          <h2>{profile.name || "Student"}</h2>

          <div className="student-profile-overview-meta">
            <span className="meta-pill">
              <FontAwesomeIcon icon={faEnvelope} />
              {profile.email || "N/A"}
            </span>

            {profile.phone ? (
              <span className="meta-pill">
                <FontAwesomeIcon icon={faPhone} />
                {profile.phone}
              </span>
            ) : null}

            {profile.blood_group ? (
              <span className="meta-pill blood-pill">
                <FontAwesomeIcon icon={faDroplet} />
                Blood: {profile.blood_group}
              </span>
            ) : null}

            <span className="meta-pill">
              <FontAwesomeIcon icon={faGraduationCap} />
              Semester {profile.semester} • Section {profile.section}
            </span>
          </div>
        </div>

        {/* Hero Actions */}
        <div className="student-hero-actions">
          <button
            type="button"
            className="student-profile-primary-button"
            onClick={handleOpenEdit}
          >
            <FontAwesomeIcon icon={faPenToSquare} /> Edit Details
          </button>

          <button
            type="button"
            className="student-profile-secondary-button"
            onClick={() => {
              setPasswordError("");
              setShowPasswordModal(true);
            }}
          >
            <FontAwesomeIcon icon={faKey} /> Password
          </button>

          <button
            type="button"
            className="student-profile-secondary-button student-btn-icon"
            onClick={() => loadProfileData(true)}
            disabled={refreshing}
            title="Refresh from Database"
          >
            <FontAwesomeIcon icon={faRotateRight} spin={refreshing} />
          </button>
        </div>
      </section>

      {/* Live Academic & Attendance Snapshot Cards */}
      <section className="student-profile-stats-card">
        <div className="student-profile-stats-header">
          <div>
            <span className="student-profile-stats-eyebrow">Academic Snapshot</span>
            <h3>Enrollment &amp; Attendance Standing</h3>
          </div>
          <span className="student-profile-stats-badge">
            <FontAwesomeIcon icon={faCircleCheck} /> SAMS-FR Synchronized
          </span>
        </div>

        <div className="student-profile-stats-grid">
          <div className="student-stat-box">
            <div className="student-stat-icon stat-icon-courses">
              <FontAwesomeIcon icon={faBookOpen} />
            </div>
            <div className="student-stat-info">
              <span className="stat-label">Active Courses</span>
              <strong className="stat-value">
                {stats.total_enrolled_courses ?? 0}
              </strong>
            </div>
          </div>

          <div className="student-stat-box">
            <div className="student-stat-icon stat-icon-attendance">
              <FontAwesomeIcon icon={faCircleCheck} />
            </div>
            <div className="student-stat-info">
              <span className="stat-label">Attendance Rate</span>
              <strong className="stat-value text-emerald">
                {stats.attendance_percentage ?? 100}%
              </strong>
            </div>
          </div>

          <div className="student-stat-box">
            <div className="student-stat-icon stat-icon-sessions">
              <FontAwesomeIcon icon={faCalendarDays} />
            </div>
            <div className="student-stat-info">
              <span className="stat-label">Total Attendance Logs</span>
              <strong className="stat-value">
                {stats.total_attendance_records ?? 0}
              </strong>
            </div>
          </div>

          <div className="student-stat-box">
            <div className="student-stat-icon stat-icon-department">
              <FontAwesomeIcon icon={faBuilding} />
            </div>
            <div className="student-stat-info">
              <span className="stat-label">Batch &amp; Department</span>
              <strong className="stat-value stat-small">
                {deptCode} ({batchName})
              </strong>
            </div>
          </div>
        </div>
      </section>

      {/* Tabs Filter Bar */}
      <div className="student-tabs-bar">
        <button
          type="button"
          className={`student-tab-pill ${activeTab === "all" ? "active" : ""}`}
          onClick={() => setActiveTab("all")}
        >
          All Details
        </button>
        <button
          type="button"
          className={`student-tab-pill ${activeTab === "personal" ? "active" : ""}`}
          onClick={() => setActiveTab("personal")}
        >
          Personal &amp; Family
        </button>
        <button
          type="button"
          className={`student-tab-pill ${activeTab === "documents" ? "active" : ""}`}
          onClick={() => setActiveTab("documents")}
        >
          Photo &amp; Signature (&lt; 50 KB)
        </button>
        <button
          type="button"
          className={`student-tab-pill ${activeTab === "address" ? "active" : ""}`}
          onClick={() => setActiveTab("address")}
        >
          Address &amp; Location
        </button>
        <button
          type="button"
          className={`student-tab-pill ${activeTab === "academic" ? "active" : ""}`}
          onClick={() => setActiveTab("academic")}
        >
          Academic Details
        </button>
      </div>

      {/* Main Details Sections */}
      <div className="student-profile-layout">
        {/* Section: Passport Photo & Signature Upload Section */}
        {(activeTab === "all" || activeTab === "documents") && (
          <section className="student-profile-panel student-profile-panel-wide">
            <div className="student-profile-panel-header">
              <div>
                <span>Digital Identity Media</span>
                <h2>Passport-Size Photo &amp; Official Signature</h2>
              </div>
              <div className="student-profile-panel-icon bg-blue">
                <FontAwesomeIcon icon={faFileImage} />
              </div>
            </div>

            <div className="student-media-grid">
              {/* Card 1: Passport Size Photo */}
              <div className="student-media-card">
                <div className="student-media-card-top">
                  <div>
                    <span className="media-eyebrow">Required Document</span>
                    <h4>Passport-Size Photo</h4>
                    <p className="media-hint">
                      Recent formal photograph with light background. Must be strictly <strong>&lt; 50 KB</strong>.
                    </p>
                  </div>
                  <span className="media-size-badge">Max 50 KB</span>
                </div>

                <div className="student-pp-preview-box">
                  {hasPhoto ? (
                    <img
                      src={profile.photo_url}
                      alt="Student passport"
                      className="student-pp-img"
                      onError={() => setPhotoLoadFailed(true)}
                    />
                  ) : (
                    <div className="student-media-placeholder">
                      <div className="placeholder-icon-circle">
                        <FontAwesomeIcon icon={faUser} />
                      </div>
                      <span className="placeholder-title">No Photo Uploaded</span>
                      <small className="placeholder-desc">Must be strictly &lt; 50 KB (JPG, PNG, WebP)</small>
                    </div>
                  )}
                </div>

                <div className="student-media-footer">
                  <div className="media-actions-row">
                    <button
                      type="button"
                      className="student-profile-primary-button media-upload-btn"
                      onClick={() => photoInputRef.current?.click()}
                      disabled={uploadingPhoto}
                    >
                      {uploadingPhoto ? (
                        <>
                          <FontAwesomeIcon icon={faSpinner} spin /> Uploading...
                        </>
                      ) : (
                        <>
                          <FontAwesomeIcon icon={faArrowUpFromBracket} /> Upload Photo (&lt; 50 KB)
                        </>
                      )}
                    </button>

                    {hasPhoto && (
                      <span className="media-status-verified">
                        <FontAwesomeIcon icon={faCheck} /> Verified &amp; Saved
                      </span>
                    )}
                  </div>
                  <p className="media-format-note">
                    Supported: JPG, JPEG, PNG, WEBP • Max Size: 50 KB
                  </p>
                </div>
              </div>

              {/* Card 2: Student Signature */}
              <div className="student-media-card">
                <div className="student-media-card-top">
                  <div>
                    <span className="media-eyebrow">Required Document</span>
                    <h4>Official Signature</h4>
                    <p className="media-hint">
                      Clear signature on plain white background. Must be strictly <strong>&lt; 50 KB</strong>.
                    </p>
                  </div>
                  <span className="media-size-badge">Max 50 KB</span>
                </div>

                <div className="student-sig-preview-box">
                  {hasSignature ? (
                    <img
                      src={profile.signature_url}
                      alt="Student signature"
                      className="student-sig-img"
                      onError={() => setSigLoadFailed(true)}
                    />
                  ) : (
                    <div className="student-media-placeholder">
                      <div className="placeholder-icon-circle">
                        <FontAwesomeIcon icon={faSignature} />
                      </div>
                      <span className="placeholder-title">No Signature Uploaded</span>
                      <small className="placeholder-desc">Sign on white paper, crop &amp; upload (&lt; 50 KB)</small>
                    </div>
                  )}
                </div>

                <div className="student-media-footer">
                  <div className="media-actions-row">
                    <button
                      type="button"
                      className="student-profile-primary-button media-upload-btn"
                      onClick={() => signatureInputRef.current?.click()}
                      disabled={uploadingSignature}
                    >
                      {uploadingSignature ? (
                        <>
                          <FontAwesomeIcon icon={faSpinner} spin /> Uploading...
                        </>
                      ) : (
                        <>
                          <FontAwesomeIcon icon={faArrowUpFromBracket} /> Upload Signature (&lt; 50 KB)
                        </>
                      )}
                    </button>

                    {hasSignature && (
                      <span className="media-status-verified">
                        <FontAwesomeIcon icon={faCheck} /> Verified &amp; Saved
                      </span>
                    )}
                  </div>
                  <p className="media-format-note">
                    Supported: PNG, JPG, JPEG • Max Size: 50 KB
                  </p>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* Section: Personal & Family Information */}
        {(activeTab === "all" || activeTab === "personal") && (
          <section className="student-profile-panel">
            <div className="student-profile-panel-header">
              <div>
                <span>Identity &amp; Lineage</span>
                <h2>Personal &amp; Family Information</h2>
              </div>
              <div className="student-profile-panel-icon bg-purple">
                <FontAwesomeIcon icon={faUsers} />
              </div>
            </div>

            <div className="student-profile-info-grid">
              <div className="student-info-item">
                <span className="info-label">
                  <FontAwesomeIcon icon={faUser} /> Full Name
                </span>
                <strong className="info-value">{profile.name || "N/A"}</strong>
              </div>

              <div className="student-info-item">
                <span className="info-label">
                  <FontAwesomeIcon icon={faPhone} /> Student Mobile Number
                </span>
                <strong className="info-value">{profile.phone || "Not configured"}</strong>
              </div>

              <div className="student-info-item">
                <span className="info-label">
                  <FontAwesomeIcon icon={faUser} /> Father&apos;s Name
                </span>
                <strong className="info-value">{profile.father_name || "Not provided"}</strong>
              </div>

              <div className="student-info-item">
                <span className="info-label">
                  <FontAwesomeIcon icon={faUser} /> Mother&apos;s Name
                </span>
                <strong className="info-value">{profile.mother_name || "Not provided"}</strong>
              </div>

              <div className="student-info-item">
                <span className="info-label">
                  <FontAwesomeIcon icon={faPhone} /> Guardian / Parent Phone
                </span>
                <strong className="info-value">{profile.guardian_phone || "Not provided"}</strong>
              </div>

              <div className="student-info-item">
                <span className="info-label">
                  <FontAwesomeIcon icon={faDroplet} /> Blood Group
                </span>
                {profile.blood_group ? (
                  <span className="blood-highlight">
                    <FontAwesomeIcon icon={faDroplet} /> {profile.blood_group}
                  </span>
                ) : (
                  <strong className="info-value">Not provided</strong>
                )}
              </div>

              <div className="student-info-item">
                <span className="info-label">
                  <FontAwesomeIcon icon={faVenusMars} /> Gender
                </span>
                <strong className="info-value">{profile.gender || "Not specified"}</strong>
              </div>

              <div className="student-info-item">
                <span className="info-label">
                  <FontAwesomeIcon icon={faCalendarDays} /> Date of Birth
                </span>
                <strong className="info-value">{profile.date_of_birth || "Not provided"}</strong>
              </div>
            </div>
          </section>
        )}

        {/* Section: Residential & Address Details */}
        {(activeTab === "all" || activeTab === "address") && (
          <section className="student-profile-panel">
            <div className="student-profile-panel-header">
              <div>
                <span>Location &amp; Emergency</span>
                <h2>Residential Address &amp; Contact Coordinates</h2>
              </div>
              <div className="student-profile-panel-icon bg-emerald">
                <FontAwesomeIcon icon={faLocationDot} />
              </div>
            </div>

            <div className="student-profile-info-grid">
              <div className="student-info-item span-full">
                <span className="info-label">
                  <FontAwesomeIcon icon={faHouse} /> Permanent Residential Address
                </span>
                <strong className="info-value">{profile.address || "Not provided"}</strong>
              </div>

              <div className="student-info-item">
                <span className="info-label">
                  <FontAwesomeIcon icon={faCity} /> City
                </span>
                <strong className="info-value">{profile.city || "Not provided"}</strong>
              </div>

              <div className="student-info-item">
                <span className="info-label">
                  <FontAwesomeIcon icon={faMapPin} /> State / Province
                </span>
                <strong className="info-value">{profile.state || "Not provided"}</strong>
              </div>

              <div className="student-info-item">
                <span className="info-label">
                  <FontAwesomeIcon icon={faMapPin} /> PIN / Postal Code
                </span>
                <strong className="info-value">{profile.pin_code || "Not provided"}</strong>
              </div>

              <div className="student-info-item">
                <span className="info-label">
                  <FontAwesomeIcon icon={faEarthAmericas} /> Country
                </span>
                <strong className="info-value">{profile.country || "India"}</strong>
              </div>

              <div className="student-info-item">
                <span className="info-label">
                  <FontAwesomeIcon icon={faUser} /> Emergency Contact Person
                </span>
                <strong className="info-value">{profile.emergency_contact_name || "Not provided"}</strong>
              </div>

              <div className="student-info-item">
                <span className="info-label">
                  <FontAwesomeIcon icon={faPhone} /> Emergency Contact Phone
                </span>
                <strong className="info-value">{profile.emergency_contact_phone || "Not provided"}</strong>
              </div>
            </div>
          </section>
        )}

        {/* Section: Academic Information */}
        {(activeTab === "all" || activeTab === "academic") && (
          <section className="student-profile-panel">
            <div className="student-profile-panel-header">
              <div>
                <span>Academic Record</span>
                <h2>University Academic Enrollment</h2>
              </div>
              <div className="student-profile-panel-icon bg-amber">
                <FontAwesomeIcon icon={faGraduationCap} />
              </div>
            </div>

            <div className="student-profile-info-grid">
              <div className="student-info-item">
                <span className="info-label">Enrollment / Roll No.</span>
                <span className="code-badge">{profile.enrollment_no}</span>
              </div>

              <div className="student-info-item">
                <span className="info-label">Department</span>
                <strong className="info-value">{deptName}</strong>
              </div>

              <div className="student-info-item">
                <span className="info-label">Department Code</span>
                <strong className="info-value">{deptCode}</strong>
              </div>

              <div className="student-info-item">
                <span className="info-label">Batch Year</span>
                <strong className="info-value">{batchName}</strong>
              </div>

              <div className="student-info-item">
                <span className="info-label">Semester</span>
                <strong className="info-value">Semester {profile.semester ?? "—"}</strong>
              </div>

              <div className="student-info-item">
                <span className="info-label">Section</span>
                <strong className="info-value">Section {profile.section || "—"}</strong>
              </div>

              <div className="student-info-item">
                <span className="info-label">Academic Year</span>
                <strong className="info-value">{profile.academic_year || "—"}</strong>
              </div>

              <div className="student-info-item">
                <span className="info-label">System Student ID</span>
                <span className="code-badge">ID #{profile.student_id}</span>
              </div>
            </div>
          </section>
        )}

        {/* Section: Security & System Architecture */}
        <section className="student-profile-panel">
          <div className="student-profile-panel-header">
            <div>
              <span>Account Security</span>
              <h2>Security &amp; Biometric Integration</h2>
            </div>
            <div className="student-profile-panel-icon bg-blue">
              <FontAwesomeIcon icon={faShieldHalved} />
            </div>
          </div>

          <div className="student-security-box">
            <div className="security-item-row">
              <div className="security-icon-circle">
                <FontAwesomeIcon icon={faLock} />
              </div>
              <div className="security-item-info">
                <strong>Account Password</strong>
                <p>
                  Password protected with salted Bcrypt hashing. You can update your password at any time.
                </p>
              </div>
              <button
                type="button"
                className="student-profile-secondary-button"
                onClick={() => {
                  setPasswordError("");
                  setShowPasswordModal(true);
                }}
              >
                <FontAwesomeIcon icon={faKey} /> Change Password
              </button>
            </div>

            <div className="security-item-row">
              <div className="security-icon-circle bg-emerald-light text-emerald">
                <FontAwesomeIcon icon={faIdCard} />
              </div>
              <div className="security-item-info">
                <strong>Facial Recognition Biometrics (SAMS-FR)</strong>
                <p>
                  Facial embeddings are synchronized with the classroom edge network for automated attendance check-in.
                </p>
              </div>
              <span className="security-badge-active">ACTIVE</span>
            </div>
          </div>
        </section>
      </div>

      {/* Edit Profile Modal Dialog */}
      {showEditModal && (
        <div
          className="student-modal-backdrop"
          onClick={(e) => {
            if (e.target === e.currentTarget && !editLoading) {
              setShowEditModal(false);
            }
          }}
        >
          <div className="student-modal-dialog" role="dialog" aria-modal="true">
            <div className="student-modal-header">
              <div>
                <span className="modal-eyebrow">Personal Information Management</span>
                <h3>Edit Student Profile Details</h3>
              </div>
              <button
                type="button"
                className="student-modal-close"
                onClick={() => setShowEditModal(false)}
                disabled={editLoading}
                aria-label="Close dialog"
              >
                <FontAwesomeIcon icon={faXmark} />
              </button>
            </div>

            {editError && (
              <div className="student-modal-error" role="alert">
                <FontAwesomeIcon icon={faTriangleExclamation} />
                <span>{editError}</span>
              </div>
            )}

            <form onSubmit={handleEditSubmit} className="student-modal-form">
              <div className="modal-form-section-title">Personal &amp; Identity</div>
              <div className="modal-form-grid">
                <div className="modal-field">
                  <label htmlFor="edit-name">Full Name *</label>
                  <input
                    id="edit-name"
                    type="text"
                    value={editForm.name}
                    onChange={(e) =>
                      setEditForm((prev) => ({ ...prev, name: e.target.value }))
                    }
                    required
                  />
                </div>

                <div className="modal-field">
                  <label htmlFor="edit-phone">Mobile / Phone Number</label>
                  <input
                    id="edit-phone"
                    type="tel"
                    placeholder="e.g. 9876543210"
                    value={editForm.phone}
                    onChange={(e) =>
                      setEditForm((prev) => ({ ...prev, phone: e.target.value }))
                    }
                  />
                </div>

                <div className="modal-field">
                  <label htmlFor="edit-gender">Gender</label>
                  <select
                    id="edit-gender"
                    value={editForm.gender}
                    onChange={(e) =>
                      setEditForm((prev) => ({ ...prev, gender: e.target.value }))
                    }
                  >
                    <option value="">Select Gender</option>
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Other">Other</option>
                  </select>
                </div>

                <div className="modal-field">
                  <label htmlFor="edit-dob">Date of Birth</label>
                  <input
                    id="edit-dob"
                    type="date"
                    value={editForm.date_of_birth}
                    onChange={(e) =>
                      setEditForm((prev) => ({
                        ...prev,
                        date_of_birth: e.target.value,
                      }))
                    }
                  />
                </div>

                <div className="modal-field">
                  <label htmlFor="edit-blood">Blood Group</label>
                  <select
                    id="edit-blood"
                    value={editForm.blood_group}
                    onChange={(e) =>
                      setEditForm((prev) => ({
                        ...prev,
                        blood_group: e.target.value,
                      }))
                    }
                  >
                    <option value="">Select Blood Group</option>
                    <option value="A+">A+</option>
                    <option value="A-">A-</option>
                    <option value="B+">B+</option>
                    <option value="B-">B-</option>
                    <option value="O+">O+</option>
                    <option value="O-">O-</option>
                    <option value="AB+">AB+</option>
                    <option value="AB-">AB-</option>
                  </select>
                </div>
              </div>

              <div className="modal-form-section-title">Family &amp; Guardian Details</div>
              <div className="modal-form-grid">
                <div className="modal-field">
                  <label htmlFor="edit-father">Father&apos;s Name</label>
                  <input
                    id="edit-father"
                    type="text"
                    placeholder="Father's full name"
                    value={editForm.father_name}
                    onChange={(e) =>
                      setEditForm((prev) => ({
                        ...prev,
                        father_name: e.target.value,
                      }))
                    }
                  />
                </div>

                <div className="modal-field">
                  <label htmlFor="edit-mother">Mother&apos;s Name</label>
                  <input
                    id="edit-mother"
                    type="text"
                    placeholder="Mother's full name"
                    value={editForm.mother_name}
                    onChange={(e) =>
                      setEditForm((prev) => ({
                        ...prev,
                        mother_name: e.target.value,
                      }))
                    }
                  />
                </div>

                <div className="modal-field">
                  <label htmlFor="edit-guardian-phone">Parent / Guardian Phone</label>
                  <input
                    id="edit-guardian-phone"
                    type="tel"
                    placeholder="e.g. 9876500000"
                    value={editForm.guardian_phone}
                    onChange={(e) =>
                      setEditForm((prev) => ({
                        ...prev,
                        guardian_phone: e.target.value,
                      }))
                    }
                  />
                </div>
              </div>

              <div className="modal-form-section-title">Address &amp; Emergency Location</div>
              <div className="modal-form-grid">
                <div className="modal-field span-2">
                  <label htmlFor="edit-address">Residential Address</label>
                  <input
                    id="edit-address"
                    type="text"
                    placeholder="House/Street/Apartment"
                    value={editForm.address}
                    onChange={(e) =>
                      setEditForm((prev) => ({
                        ...prev,
                        address: e.target.value,
                      }))
                    }
                  />
                </div>

                <div className="modal-field">
                  <label htmlFor="edit-city">City</label>
                  <input
                    id="edit-city"
                    type="text"
                    placeholder="City name"
                    value={editForm.city}
                    onChange={(e) =>
                      setEditForm((prev) => ({ ...prev, city: e.target.value }))
                    }
                  />
                </div>

                <div className="modal-field">
                  <label htmlFor="edit-state">State / Province</label>
                  <input
                    id="edit-state"
                    type="text"
                    placeholder="State name"
                    value={editForm.state}
                    onChange={(e) =>
                      setEditForm((prev) => ({ ...prev, state: e.target.value }))
                    }
                  />
                </div>

                <div className="modal-field">
                  <label htmlFor="edit-pincode">PIN / Postal Code</label>
                  <input
                    id="edit-pincode"
                    type="text"
                    placeholder="e.g. 834001"
                    value={editForm.pin_code}
                    onChange={(e) =>
                      setEditForm((prev) => ({
                        ...prev,
                        pin_code: e.target.value,
                      }))
                    }
                  />
                </div>

                <div className="modal-field">
                  <label htmlFor="edit-country">Country</label>
                  <input
                    id="edit-country"
                    type="text"
                    value={editForm.country}
                    onChange={(e) =>
                      setEditForm((prev) => ({
                        ...prev,
                        country: e.target.value,
                      }))
                    }
                  />
                </div>

                <div className="modal-field">
                  <label htmlFor="edit-emerg-name">Emergency Contact Name</label>
                  <input
                    id="edit-emerg-name"
                    type="text"
                    placeholder="Contact person"
                    value={editForm.emergency_contact_name}
                    onChange={(e) =>
                      setEditForm((prev) => ({
                        ...prev,
                        emergency_contact_name: e.target.value,
                      }))
                    }
                  />
                </div>

                <div className="modal-field">
                  <label htmlFor="edit-emerg-phone">Emergency Contact Phone</label>
                  <input
                    id="edit-emerg-phone"
                    type="tel"
                    placeholder="Emergency phone number"
                    value={editForm.emergency_contact_phone}
                    onChange={(e) =>
                      setEditForm((prev) => ({
                        ...prev,
                        emergency_contact_phone: e.target.value,
                      }))
                    }
                  />
                </div>
              </div>

              <div className="student-modal-actions">
                <button
                  type="button"
                  className="student-profile-secondary-button"
                  onClick={() => setShowEditModal(false)}
                  disabled={editLoading}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="student-profile-primary-button"
                  disabled={editLoading}
                >
                  {editLoading ? (
                    <>
                      <FontAwesomeIcon icon={faSpinner} spin /> Saving...
                    </>
                  ) : (
                    <>
                      <FontAwesomeIcon icon={faFloppyDisk} /> Save Details
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Change Password Modal */}
      {showPasswordModal && (
        <div
          className="student-modal-backdrop"
          onClick={(e) => {
            if (e.target === e.currentTarget && !passwordLoading) {
              setShowPasswordModal(false);
            }
          }}
        >
          <div className="student-modal-dialog student-modal-small" role="dialog" aria-modal="true">
            <div className="student-modal-header">
              <div>
                <span className="modal-eyebrow">Account Security</span>
                <h3>Change Account Password</h3>
              </div>
              <button
                type="button"
                className="student-modal-close"
                onClick={() => setShowPasswordModal(false)}
                disabled={passwordLoading}
                aria-label="Close dialog"
              >
                <FontAwesomeIcon icon={faXmark} />
              </button>
            </div>

            {passwordError && (
              <div className="student-modal-error" role="alert">
                <FontAwesomeIcon icon={faTriangleExclamation} />
                <span>{passwordError}</span>
              </div>
            )}

            <form onSubmit={handlePasswordSubmit} className="student-modal-form">
              {/* Current Password */}
              <div className="modal-field">
                <label htmlFor="student-curr-pass">Current Password *</label>
                <div className="modal-input-wrapper">
                  <input
                    id="student-curr-pass"
                    type={showCurrentPassword ? "text" : "password"}
                    value={passwordForm.current_password}
                    onChange={(e) =>
                      setPasswordForm((prev) => ({
                        ...prev,
                        current_password: e.target.value,
                      }))
                    }
                    placeholder="Enter current password"
                    required
                  />
                  <button
                    type="button"
                    className="modal-input-eye-btn"
                    onClick={() => setShowCurrentPassword((prev) => !prev)}
                    aria-label="Toggle password visibility"
                  >
                    <FontAwesomeIcon icon={showCurrentPassword ? faEyeSlash : faEye} />
                  </button>
                </div>
              </div>

              {/* New Password */}
              <div className="modal-field">
                <label htmlFor="student-new-pass">New Password *</label>
                <div className="modal-input-wrapper">
                  <input
                    id="student-new-pass"
                    type={showNewPassword ? "text" : "password"}
                    value={passwordForm.new_password}
                    onChange={(e) =>
                      setPasswordForm((prev) => ({
                        ...prev,
                        new_password: e.target.value,
                      }))
                    }
                    placeholder="Minimum 6 characters"
                    required
                  />
                  <button
                    type="button"
                    className="modal-input-eye-btn"
                    onClick={() => setShowNewPassword((prev) => !prev)}
                    aria-label="Toggle password visibility"
                  >
                    <FontAwesomeIcon icon={showNewPassword ? faEyeSlash : faEye} />
                  </button>
                </div>

                {passwordForm.new_password && (
                  <div className="modal-password-strength">
                    <div className="strength-header">
                      <span>Password strength</span>
                      <strong className={`strength-${passwordStrength.level}`}>
                        {passwordStrength.label}
                      </strong>
                    </div>
                    <div className="strength-bars">
                      {[1, 2, 3, 4].map((bar) => (
                        <span
                          key={bar}
                          className={bar <= passwordStrength.level ? `active strength-${passwordStrength.level}` : ""}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Confirm Password */}
              <div className="modal-field">
                <label htmlFor="student-conf-pass">Confirm New Password *</label>
                <div className="modal-input-wrapper">
                  <input
                    id="student-conf-pass"
                    type={showConfirmPassword ? "text" : "password"}
                    value={passwordForm.confirm_password}
                    onChange={(e) =>
                      setPasswordForm((prev) => ({
                        ...prev,
                        confirm_password: e.target.value,
                      }))
                    }
                    placeholder="Re-enter new password"
                    required
                  />
                  <button
                    type="button"
                    className="modal-input-eye-btn"
                    onClick={() => setShowConfirmPassword((prev) => !prev)}
                    aria-label="Toggle password visibility"
                  >
                    <FontAwesomeIcon icon={showConfirmPassword ? faEyeSlash : faEye} />
                  </button>
                </div>

                {passwordForm.confirm_password && (
                  <div
                    className={`password-match-badge ${
                      passwordForm.new_password === passwordForm.confirm_password
                        ? "match"
                        : "mismatch"
                    }`}
                  >
                    <FontAwesomeIcon
                      icon={
                        passwordForm.new_password === passwordForm.confirm_password
                          ? faCircleCheck
                          : faTriangleExclamation
                      }
                    />
                    <span>
                      {passwordForm.new_password === passwordForm.confirm_password
                        ? "Passwords match"
                        : "Passwords do not match"}
                    </span>
                  </div>
                )}
              </div>

              <div className="student-modal-actions">
                <button
                  type="button"
                  className="student-profile-secondary-button"
                  onClick={() => setShowPasswordModal(false)}
                  disabled={passwordLoading}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="student-profile-primary-button"
                  disabled={
                    passwordLoading ||
                    !passwordForm.current_password ||
                    !passwordForm.new_password ||
                    !passwordForm.confirm_password
                  }
                >
                  {passwordLoading ? (
                    <>
                      <FontAwesomeIcon icon={faSpinner} spin /> Updating...
                    </>
                  ) : (
                    <>
                      <FontAwesomeIcon icon={faKey} /> Update Password
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

export default Profile;