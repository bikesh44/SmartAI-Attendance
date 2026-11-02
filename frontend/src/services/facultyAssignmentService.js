import api from "./api";

/**
 * Fetch summary statistics (Total Assignments, Total Notes, Total Submissions, Pending Review)
 */
export async function getAssignmentSummary() {
  const response = await api.get("/faculty/assignments/summary");
  return response.data;
}

/**
 * Fetch course offerings taught by the authenticated faculty member.
 */
export async function getFacultyClasses() {
  const response = await api.get("/faculty/assignments/classes");
  return response.data;
}

/**
 * Fetch assignments with optional filters (offering_id, status, search).
 */
export async function getAssignments(params = {}) {
  const response = await api.get("/faculty/assignments", { params });
  return response.data;
}

/**
 * Fetch single assignment detail.
 */
export async function getAssignmentDetail(assignmentId) {
  const response = await api.get(`/faculty/assignments/${assignmentId}`);
  return response.data;
}

/**
 * Create a new assignment (accepts FormData or plain object).
 */
export async function createAssignment(payload) {
  const response = await api.post("/faculty/assignments", payload);
  return response.data;
}

/**
 * Update an existing assignment.
 */
export async function updateAssignment(assignmentId, payload) {
  const response = await api.put(`/faculty/assignments/${assignmentId}`, payload);
  return response.data;
}

/**
 * Delete an assignment.
 */
export async function deleteAssignment(assignmentId) {
  const response = await api.delete(`/faculty/assignments/${assignmentId}`);
  return response.data;
}

/**
 * Toggle assignment status (PUBLISHED, CLOSED, DRAFT).
 */
export async function toggleAssignmentStatus(assignmentId, status) {
  const response = await api.patch(`/faculty/assignments/${assignmentId}/status`, { status });
  return response.data;
}

/**
 * Download assignment attachment.
 */
export async function downloadAssignmentAttachment(assignmentId) {
  const response = await api.get(`/faculty/assignments/${assignmentId}/download`, {
    responseType: "blob",
  });
  return response;
}

/**
 * Fetch enrolled students submission roster for an assignment.
 */
export async function getAssignmentSubmissions(assignmentId) {
  const response = await api.get(`/faculty/assignments/${assignmentId}/submissions`);
  return response.data;
}

/**
 * Evaluate and grade a student submission.
 */
export async function evaluateSubmission(submissionId, payload) {
  const response = await api.post(`/faculty/assignments/submissions/${submissionId}/evaluate`, payload);
  return response.data;
}

/**
 * Download student submission file.
 */
export async function downloadSubmissionFile(submissionId) {
  const response = await api.get(`/faculty/assignments/submissions/${submissionId}/download`, {
    responseType: "blob",
  });
  return response;
}

/**
 * Fetch study materials / notes with optional filters (offering_id, category, search).
 */
export async function getStudyMaterials(params = {}) {
  const response = await api.get("/faculty/assignments/notes", { params });
  return response.data;
}

/**
 * Upload a new study material document.
 */
export async function uploadStudyMaterial(formData) {
  const response = await api.post("/faculty/assignments/notes", formData);
  return response.data;
}

/**
 * Update study material metadata.
 */
export async function updateStudyMaterial(materialId, payload) {
  const response = await api.put(`/faculty/assignments/notes/${materialId}`, payload);
  return response.data;
}

/**
 * Delete study material.
 */
export async function deleteStudyMaterial(materialId) {
  const response = await api.delete(`/faculty/assignments/notes/${materialId}`);
  return response.data;
}

/**
 * Download study material document.
 */
export async function downloadStudyMaterial(materialId) {
  const response = await api.get(`/faculty/assignments/notes/${materialId}/download`, {
    responseType: "blob",
  });
  return response;
}

/**
 * Fetch class overview statistics.
 */
export async function getClassOverview() {
  const response = await api.get("/faculty/assignments/class-overview");
  return response.data;
}

/**
 * Fetch recent uploads for sidebar panel.
 */
export async function getRecentUploads() {
  const response = await api.get("/faculty/assignments/recent-uploads");
  return response.data;
}
