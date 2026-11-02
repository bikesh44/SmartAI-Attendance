import api from "./api";

export async function getStudentFaceProfile() {
  const response = await api.get("/student/face-profile");
  return response.data;
}

export async function deleteStudentFaceProfile() {
  const response = await api.delete("/student/face-profile");
  return response.data;
}