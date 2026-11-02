import api from "./api";

export async function getFacultyProfile() {
  const response = await api.get("/faculty/profile");

  return response.data;
}

export async function updateFacultyProfile(profileData) {
  const response = await api.patch(
    "/faculty/profile",
    profileData
  );

  return response.data;
}

export async function changeFacultyPassword(passwordData) {
  const response = await api.post(
    "/faculty/change-password",
    passwordData
  );

  return response.data;
}

export async function getFacultyClassesSummary(params = {}) {
  const response = await api.get("/faculty/classes/summary", { params });

  return response.data;
}

export async function getFacultyCourses(params = {}) {
  const response = await api.get("/faculty/courses", { params });

  return response.data;
}

export async function getFacultyCourseDetails(courseId) {
  const response = await api.get(
    `/faculty/courses/${courseId}`
  );

  return response.data;
}

export async function getFacultyStudents(params = {}) {
  const response = await api.get("/faculty/students", { params });

  return response.data;
}

export async function getFacultyAttendanceSessions(params = {}) {
  const response = await api.get(
    "/faculty/attendance/sessions",
    { params }
  );

  return response.data;
}

export async function getActiveFacultyAttendanceSession(params = {}) {
  const response = await api.get(
    "/faculty/attendance/sessions/active",
    { params }
  );

  return response.data;
}

export async function startFacultyAttendanceSession(
  offeringIdOrPayload,
  timetableEntryId = null
) {
  const payload =
    typeof offeringIdOrPayload === "object" && offeringIdOrPayload !== null
      ? { ...offeringIdOrPayload }
      : {
          offering_id: offeringIdOrPayload,
          ...(timetableEntryId ? { timetable_entry_id: timetableEntryId } : {}),
        };

  const response = await api.post(
    "/faculty/attendance/sessions",
    payload
  );

  return response.data;
}


export async function closeFacultyAttendanceSession(
  sessionId
) {
  const response = await api.post(
    `/faculty/attendance/sessions/${sessionId}/close`
  );

  return response.data;
}

export async function getFacultyAttendanceRecords(
  sessionId
) {
  const response = await api.get(
    `/faculty/attendance/sessions/${sessionId}/records`
  );

  return response.data;
}

export async function requestLivenessChallenge(sessionId) {
  const response = await api.post("/faculty/recognition/liveness/challenge", {
    session_id: Number(sessionId),
  });

  return response.data;
}

export async function verifyLiveness(payload) {
  // Supports both FormData and regular JSON payload
  if (payload instanceof FormData) {
    const response = await api.post("/faculty/recognition/liveness/verify", payload);
    return response.data;
  }

  const response = await api.post("/faculty/recognition/liveness/verify", payload);
  return response.data;
}

export async function recordVerifiedAttendance(
  sessionId,
  verificationToken,
  studentId = null
) {
  const payload = {
    session_id: Number(sessionId),
    verification_token: verificationToken,
    ...(studentId ? { student_id: Number(studentId) } : {}),
  };

  const response = await api.post("/faculty/recognition/attendance", payload);
  return response.data;
}

export async function recognizeFacultyAttendance(
  sessionId,
  imageBlob,
  verificationToken = null,
  studentId = null
) {
  if (
    typeof imageBlob === "object" &&
    !(imageBlob instanceof Blob) &&
    !(imageBlob instanceof File)
  ) {
    const response = await api.post("/faculty/recognition/attendance", {
      session_id: Number(sessionId),
      ...imageBlob,
    });
    return response.data;
  }

  const formData = new FormData();

  formData.append(
    "session_id",
    String(sessionId)
  );

  if (imageBlob) {
    formData.append(
      "image",
      imageBlob,
      "attendance-frame.jpg"
    );
  }

  if (verificationToken) {
    formData.append("verification_token", verificationToken);
  }

  if (studentId) {
    formData.append("student_id", String(studentId));
  }

  const response = await api.post(
    "/faculty/recognition/attendance",
    formData
  );

  return response.data;
}

export async function getFacultyTimetable(params = {}) {
  const response = await api.get("/timetable/faculty", { params });

  return response.data;
}

export async function getFacultyAttendanceOverview(params = {}) {
  const response = await api.get("/faculty/attendance/overview", { params });

  return response.data;
}

export async function getSystemHealth() {
  const response = await api.get("/db-health");

  return response.data;
}

export async function exportClassRoster(offeringId, params = {}) {
  const response = await api.get(`/faculty/classes/${offeringId}/roster/export`, {
    params,
    responseType: "blob",
  });

  return response;
}

export async function getOfferingRoster(offeringId) {
  const response = await api.get(`/faculty/classes/${offeringId}/roster`);

  return response.data;
}
