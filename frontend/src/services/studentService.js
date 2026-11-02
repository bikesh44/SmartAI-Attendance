import api from "./api";

// ==================== STUDENT PROFILE ====================

export async function getStudentProfile() {
  const response = await api.get("/student/profile");
  return response.data;
}

export async function updateStudentProfile(profileData) {
  const response = await api.patch("/student/profile", profileData);
  return response.data;
}

export async function uploadStudentPhoto(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post("/student/upload-photo", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
}

export async function uploadStudentSignature(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post("/student/upload-signature", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
}

export async function changeStudentPassword(passwordData) {
  const response = await api.post("/student/change-password", passwordData);
  return response.data;
}

// ==================== COURSES & ACADEMICS ====================

export async function getStudentCourses(params = {}) {
  const response = await api.get("/student/courses", { params });
  return response.data;
}

export async function getStudentCourseDetails(offeringId) {
  const response = await api.get(`/student/courses/${offeringId}`);
  return response.data;
}

export async function getStudentDashboard(weeks = 4) {
  const response = await api.get(`/student/dashboard?weeks=${weeks}`);
  return response.data;
}
