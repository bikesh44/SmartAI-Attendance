import api from "./api";

export async function getFacultyDashboard() {
  const response = await api.get("/faculty/dashboard");
  return response.data;
}

export async function getStudentDashboard() {
  const response = await api.get("/student/dashboard");
  return response.data;
}

export async function getStudentCourses() {
  const response = await api.get("/student/courses");
  return response.data;
}