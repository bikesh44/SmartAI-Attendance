import api from "./api";

/**
 * Fetch courses/offerings assigned to the authenticated faculty member.
 */
export async function getFacultyCourses() {
  const response = await api.get("/faculty/results/courses");
  return response.data;
}

/**
 * Fetch assessments for a course offering.
 */
export async function getFacultyAssessments(offeringId) {
  const response = await api.get("/faculty/results/assessments", {
    params: { offering_id: offeringId },
  });
  return response.data;
}

/**
 * Create a new assessment for a course offering.
 */
export async function createFacultyAssessment(payload) {
  const response = await api.post("/faculty/results/assessments", payload);
  return response.data;
}

/**
 * Fetch real summary card metrics (total students, draft, submitted, published).
 */
export async function getFacultyResultsSummary(offeringId, assessmentId) {
  const params = {};
  if (offeringId) params.offering_id = offeringId;
  if (assessmentId) params.assessment_id = assessmentId;
  const response = await api.get("/faculty/results/summary", { params });
  return response.data;
}

/**
 * Fetch enrolled students roster and current marks for entry.
 */
export async function getFacultyStudentsForEntry(offeringId, assessmentId) {
  const params = { offering_id: offeringId };
  if (assessmentId) params.assessment_id = assessmentId;
  const response = await api.get("/faculty/results/students", { params });
  return response.data;
}

/**
 * Save marks as DRAFT without submitting for administrative review.
 */
export async function saveFacultyDraftMarks(payload) {
  const response = await api.post("/faculty/results/save-draft", payload);
  return response.data;
}

/**
 * Submit marks for administrative review and publication workflow.
 */
export async function submitFacultyMarks(payload) {
  const response = await api.post("/faculty/results/submit", payload);
  return response.data;
}

/**
 * Validate imported CSV records against active enrollment roster and max marks.
 */
export async function importFacultyMarks(payload) {
  const response = await api.post("/faculty/results/import", payload);
  return response.data;
}
