import api from "./api";

/**
 * Fetch dynamic filter options (Academic years, semesters, departments, courses, faculty, statuses).
 */
export async function getAdminResultsFilters() {
  const response = await api.get("/admin/academic-results/filters");
  return response.data;
}

/**
 * Fetch 4 KPI summary cards (Pending reviews, Submitted, Published, Returned) and pass rate stats.
 */
export async function getAdminResultsOverview() {
  const response = await api.get("/admin/academic-results/overview");
  return response.data;
}

/**
 * Fetch paginated list of result submissions with filters.
 * @param {Object} params - { academic_year, semester, department_id, course_id, faculty_id, status, page, limit }
 */
export async function getAdminSubmissions(params = {}) {
  const response = await api.get("/admin/academic-results/submissions", { params });
  return response.data;
}

/**
 * Fetch complete submission details, student score list, and missing marks warnings.
 * @param {number} submissionId
 */
export async function getAdminSubmissionDetails(submissionId) {
  const response = await api.get(`/admin/academic-results/submissions/${submissionId}`);
  return response.data;
}

/**
 * Approve a submitted result set.
 * @param {number} submissionId
 * @param {Object} data - { remarks?: string }
 */
export async function approveSubmission(submissionId, data = {}) {
  const response = await api.post(`/admin/academic-results/submissions/${submissionId}/approve`, data);
  return response.data;
}

/**
 * Return an incomplete or invalid submission for faculty correction with mandatory reason.
 * @param {number} submissionId
 * @param {Object} data - { reason: string }
 */
export async function returnSubmission(submissionId, data = {}) {
  const response = await api.post(`/admin/academic-results/submissions/${submissionId}/return`, data);
  return response.data;
}

/**
 * Publish approved results to the Student Portal.
 * @param {number} submissionId
 */
export async function publishSubmission(submissionId) {
  const response = await api.post(`/admin/academic-results/submissions/${submissionId}/publish`, {});
  return response.data;
}

/**
 * Record an authorized correction to a student result with audit logging.
 * @param {Object} data - { result_id: number, new_marks: number, reason: string }
 */
export async function recordResultCorrection(data) {
  const response = await api.post("/admin/academic-results/corrections", data);
  return response.data;
}

/**
 * Fetch timeline of submission, review, approval, return, publication, and correction events.
 * @param {Object} params - { limit?: number }
 */
export async function getAdminAuditHistory(params = {}) {
  const response = await api.get("/admin/academic-results/audit-history", { params });
  return response.data;
}

/**
 * Create a new assessment definition for a course offering.
 * @param {Object} data - { offering_id, assessment_name, assessment_type, max_marks, weightage, assessment_date }
 */
export async function createAssessment(data) {
  const response = await api.post("/admin/academic-results/assessments", data);
  return response.data;
}
