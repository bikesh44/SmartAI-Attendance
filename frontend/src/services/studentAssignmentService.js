import api from "./api";

/**
 * Fetch dynamic summary statistics for the student
 * (Total Assignments, Pending, Submitted, Notes Available)
 */
export async function getStudentAssignmentSummary() {
  const response = await api.get("/student/assignments/summary");
  return response.data;
}

/**
 * Fetch list of enrolled classes/subjects for filter dropdowns.
 */
export async function getStudentEnrolledClasses() {
  const response = await api.get("/student/assignments/enrolled-classes");
  return response.data;
}

/**
 * Fetch published assignments for the student with optional filters:
 * (offering_id, status, search)
 */
export async function getStudentAssignments(params = {}) {
  const response = await api.get("/student/assignments", { params });
  return response.data;
}

/**
 * Fetch single assignment details along with student's submission status.
 */
export async function getStudentAssignmentDetail(assignmentId) {
  const response = await api.get(`/student/assignments/${assignmentId}`);
  return response.data;
}

/**
 * Download faculty worksheet / assignment attachment.
 */
export async function downloadAssignmentAttachment(assignmentId) {
  const response = await api.get(`/student/assignments/${assignmentId}/download-attachment`, {
    responseType: "blob",
  });
  return response;
}

/**
 * Submit work for an assignment (accepts FormData for files or JSON for text).
 */
export async function submitAssignment(assignmentId, payload) {
  const response = await api.post(`/student/assignments/${assignmentId}/submit`, payload);
  return response.data;
}

/**
 * Fetch student's own submission history.
 */
export async function getStudentSubmissions() {
  const response = await api.get("/student/assignments/submissions");
  return response.data;
}

/**
 * Securely download student's own submitted file.
 */
export async function downloadStudentSubmissionFile(submissionId) {
  const response = await api.get(`/student/assignments/submissions/${submissionId}/download`, {
    responseType: "blob",
  });
  return response;
}

/**
 * Fetch published notes / study materials with optional filters:
 * (offering_id, category, search)
 */
export async function getStudentNotes(params = {}) {
  const response = await api.get("/student/assignments/notes", { params });
  return response.data;
}

/**
 * Securely download a published study material document.
 */
export async function downloadStudentNote(materialId) {
  const response = await api.get(`/student/assignments/notes/${materialId}/download`, {
    responseType: "blob",
  });
  return response;
}

/**
 * Fetch upcoming assignment deadlines in chronological order.
 */
export async function getStudentDeadlines() {
  const response = await api.get("/student/assignments/deadlines");
  return response.data;
}

/**
 * Fetch evaluated assignments with marks, percentages, and faculty comments.
 */
export async function getStudentResults() {
  const response = await api.get("/student/assignments/results");
  return response.data;
}
