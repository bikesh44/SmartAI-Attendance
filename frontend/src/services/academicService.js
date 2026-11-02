import api from "./api";

/**
 * Fetch high-level academic summary (GPA, CGPA, Credits, Current Semester, Batch).
 */
export async function getAcademicOverview() {
  const response = await api.get("/student/academic-records/overview");
  return response.data;
}

/**
 * Fetch subject-wise results, marks, grades, grade points, credits, and SGPA.
 * @param {Object} params - { semester: number, academic_year?: string }
 */
export async function getSemesterResults(params = {}) {
  const response = await api.get("/student/academic-records/results", { params });
  return response.data;
}

/**
 * Fetch semester-by-semester GPA and CGPA progression for line charting.
 */
export async function getAcademicPerformanceHistory() {
  const response = await api.get("/student/academic-records/performance-history");
  return response.data;
}

/**
 * Fetch examination records and schedules.
 */
export async function getExaminationRecords() {
  const response = await api.get("/student/academic-records/examinations");
  return response.data;
}

/**
 * Fetch verifiable academic documents (grade cards, transcripts).
 */
export async function getAcademicDocuments() {
  const response = await api.get("/student/academic-records/documents");
  return response.data;
}

/**
 * Export official academic report in PDF, Excel, or CSV format.
 * Defaults to genuine PDF Grade Card.
 * @param {Object} params - { semester?: number, format?: string }
 */
export async function exportAcademicReport(params = {}) {
  const queryParams = {
    format: "pdf",
    ...params,
  };
  const response = await api.get("/student/academic-records/export", {
    params: queryParams,
    responseType: "blob",
  });
  return response;
}
