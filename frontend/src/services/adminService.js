import api from "./api";

// ==================== ADMIN DASHBOARD ====================

export async function getAdminDashboard() {
  const response = await api.get("/admin/dashboard");
  return response.data;
}

// ==================== USERS ====================

export async function getUsers() {
  const response = await api.get("/admin/users");
  return response.data;
}

export async function getUser(userId) {
  const response = await api.get(`/admin/users/${userId}`);
  return response.data;
}

export async function createUser(userData) {
  const response = await api.post("/admin/users", userData);
  return response.data;
}

export async function updateUser(userId, userData) {
  const response = await api.patch(
    `/admin/users/${userId}`,
    userData,
  );
  return response.data;
}

export async function deleteUser(userId) {
  const response = await api.delete(
    `/admin/users/${userId}`,
  );
  return response.data;
}

// ==================== STUDENTS ====================

export async function getAdminStudents(params = {}) {
  const response = await api.get("/admin/students", { params });
  return response.data;
}

export async function getAdminStudentsSummary() {
  const response = await api.get("/admin/students/summary");
  return response.data;
}

export async function getAdminStudentsFilterOptions() {
  const response = await api.get("/admin/students/filter-options");
  return response.data;
}

export async function getAdminStudent(studentId) {
  const response = await api.get(
    `/admin/students/${studentId}`,
  );
  return response.data;
}

export async function createAdminStudent(studentData) {
  const response = await api.post(
    "/admin/students",
    studentData,
  );
  return response.data;
}

export async function updateAdminStudent(
  studentId,
  studentData,
) {
  const response = await api.patch(
    `/admin/students/${studentId}`,
    studentData,
  );
  return response.data;
}

export async function deleteAdminStudent(studentId) {
  const response = await api.delete(
    `/admin/students/${studentId}`,
  );
  return response.data;
}

export async function deleteAdminStudentFaceRegistration(studentId, options = {}) {
  const { reason, permanent = false, face_id } = options;
  const payload = {};
  if (reason) payload.reason = reason;
  if (permanent) payload.permanent = true;
  if (face_id) payload.face_id = face_id;

  const response = await api.delete(
    `/admin/students/${studentId}/face`,
    { data: payload }
  );
  return response.data;
}

// ==================== FACULTY ====================

export async function getAdminFaculty() {
  const response = await api.get("/admin/faculty");
  return response.data;
}

export async function getAdminFacultySummary() {
  const response = await api.get("/admin/faculty/summary");
  return response.data;
}

export async function getAdminFacultyFilterOptions() {
  const response = await api.get("/admin/faculty/filter-options");
  return response.data;
}

export async function getAdminFacultyById(facultyId) {
  const response = await api.get(
    `/admin/faculty/${facultyId}`,
  );
  return response.data;
}

export async function createAdminFaculty(facultyData) {
  const response = await api.post(
    "/admin/faculty",
    facultyData,
  );
  return response.data;
}

export async function updateAdminFaculty(
  facultyId,
  facultyData,
) {
  const response = await api.patch(
    `/admin/faculty/${facultyId}`,
    facultyData,
  );
  return response.data;
}

export async function deleteAdminFaculty(facultyId) {
  const response = await api.delete(
    `/admin/faculty/${facultyId}`,
  );
  return response.data;
}

// ==================== ADMIN PROFILE ====================

export async function getAdminProfile() {
  const response = await api.get("/admin/profile");
  return response.data;
}

export async function updateAdminProfile(profileData) {
  const response = await api.patch(
    "/admin/profile",
    profileData,
  );
  return response.data;
}

export async function changeAdminPassword(passwordData) {
  const response = await api.post(
    "/admin/change-password",
    passwordData,
  );
  return response.data;
}


// ==================== FACE PROFILES ====================

export async function getAdminFaceProfiles() {
  const response = await api.get("/admin/face-profiles");
  return response.data;
}

// ==================== ADMIN ATTENDANCE REPORTS ====================

export async function getAdminAttendanceSessions(params = {}) {
  const response = await api.get(
    "/admin/attendance/sessions",
    {
      params,
    },
  );

  return response.data;
}

export async function getAdminAttendanceSession(sessionId) {
  const response = await api.get(
    `/admin/attendance/sessions/${sessionId}`,
  );

  return response.data;
}

export async function getAdminAttendanceRecords(sessionId) {
  const response = await api.get(
    `/admin/attendance/sessions/${sessionId}/records`,
  );

  return response.data;
}

export async function getAdminAttendanceFilterOptions(params = {}) {
  const response = await api.get("/admin/attendance/filter-options", {
    params,
  });
  return response.data;
}

export async function getAdminAttendanceDashboard(params = {}) {
  const response = await api.get("/admin/attendance/dashboard", {
    params,
  });
  return response.data;
}

export async function getAdminAttendanceAnalytics(params = {}) {
  const response = await api.get("/admin/attendance/analytics", {
    params,
  });
  return response.data;
}

export async function getAdminAttendanceRecordsList(params = {}) {
  const response = await api.get("/admin/attendance/records", {
    params,
  });
  return response.data;
}

export async function getAdminAttendanceRecordDetail(attendanceId) {
  const response = await api.get(`/admin/attendance/records/${attendanceId}`);
  return response.data;
}

export async function exportAdminAttendanceCsv(params = {}) {
  const response = await api.get("/admin/attendance/export", {
    params,
    responseType: "blob",
  });
  return response.data;
}


export async function getAdminDepartments() {
  const response = await api.get("/admin/departments");
  return response.data;
}

export async function createAdminDepartment(departmentData) {
  const response = await api.post(
    "/admin/departments",
    departmentData,
  );
  return response.data;
}

export async function updateAdminDepartment(
  departmentId,
  departmentData,
) {
  const response = await api.patch(
    `/admin/departments/${departmentId}`,
    departmentData,
  );
  return response.data;
}

export async function deleteAdminDepartment(departmentId) {
  const response = await api.delete(
    `/admin/departments/${departmentId}`,
  );
  return response.data;
}

 // ==================== COURSE OFFERINGS ====================

export async function getAdminAcademicSummary(options = {}) {
  const response = await api.get("/admin/academic/summary", options);
  return response.data;
}

export async function getAdminCourses() {
  const response = await api.get("/admin/courses");
  return response.data;
}

export async function createAdminCourse(courseData) {
  const response = await api.post("/admin/courses", courseData);
  return response.data;
}

export async function updateAdminCourse(courseId, courseData) {
  const response = await api.patch(
    `/admin/courses/${courseId}`,
    courseData
  );

  return response.data;
}

export async function deleteAdminCourse(courseId) {
  const response = await api.delete(`/admin/courses/${courseId}`);
  return response.data;
}

export async function getAdminCourseOfferings() {
  const response = await api.get("/admin/course-offerings");
  return response.data;
}

export async function createAdminCourseOffering(offeringData) {
  const response = await api.post(
    "/admin/course-offerings",
    offeringData,
  );
  return response.data;
}

export async function updateAdminCourseOffering(
  offeringId,
  offeringData,
) {
  const response = await api.patch(
    `/admin/course-offerings/${offeringId}`,
    offeringData,
  );
  return response.data;
}

export async function deleteAdminCourseOffering(offeringId) {
  const response = await api.delete(
    `/admin/course-offerings/${offeringId}`,
  );
  return response.data;
}


export async function reactivateUser(userId) {
  const response = await api.patch(
    `/admin/users/${userId}/reactivate`
  );

  return response.data;
}


export async function getAdminBatches() {
  const response = await api.get("/admin/batches");
  return response.data;
}

export async function createAdminBatch(batchData) {
  const response = await api.post("/admin/batches", batchData);
  return response.data;
}

export async function getAdminAcademicSession() {
  const response = await api.get("/admin/academic-session");
  return response.data;
}

export async function updateAdminAcademicSession(sessionData) {
  const response = await api.post("/admin/academic-session", sessionData);
  return response.data;
}

// ==================== RECENT ACTIVITY & AUDIT LOGS ====================

export async function getRecentActivity(limit = 10) {
  const response = await api.get("/admin/activity/recent", {
    params: { limit },
  });
  return response.data;
}

export async function getActivityLogs(params = {}) {
  const response = await api.get("/admin/activity", { params });
  return response.data;
}
