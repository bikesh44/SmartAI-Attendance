import api from "./api";

export async function getStudentAttendance(params = {}) {
  const response = await api.get("/student/attendance/", {
    params,
  });

  return response.data;
}

export async function getStudentAttendanceSummary(params = {}) {
  const response = await api.get("/student/attendance/summary", {
    params,
  });
  return response.data;
}

export async function getStudentAttendanceDetail(attendanceId) {
  const response = await api.get(`/student/attendance/${attendanceId}`);
  return response.data;
}

export async function getStudentCourses(params = {}) {
  const response = await api.get("/student/courses", { params });
  return response.data;
}

export async function getStudentDailyPunch(params = {}) {
  const response = await api.get("/student/attendance/daily-punch", { params });
  return response.data;
}

/**
 * Export official subject-wise attendance report in PDF, Excel, or CSV format.
 * Defaults to genuine server-generated PDF.
 * @param {Object} params - { academic_year?: string, semester?: number|string, format?: string, ... }
 */
export async function exportStudentAttendanceReport(params = {}) {
  const queryParams = {
    format: "pdf",
    ...params,
  };
  const response = await api.get("/student/attendance/export", {
    params: queryParams,
    responseType: "blob",
  });
  return response;
}
