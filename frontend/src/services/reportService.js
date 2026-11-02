import api from "./api";

export async function getFacultyAttendanceAnalytics(params = {}) {
  const response = await api.get(
    "/faculty/attendance/analytics",
    {
      params,
    }
  );

  return response.data;
}

export async function getFacultyAttendanceReports(params = {}) {
  const response = await api.get(
    "/faculty/attendance/reports",
    {
      params,
    }
  );

  return response.data;
}

export async function exportFacultyAttendanceReport(params = {}) {
  const response = await api.get(
    "/faculty/attendance/reports/export",
    {
      params,
      responseType: "blob",
      headers: {
        "Cache-Control": "no-cache",
      },
    }
  );

  return response;
}
