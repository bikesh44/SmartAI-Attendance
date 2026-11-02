
import api from "./api";

/**
 * Retrieve existing enrollment records for the admin table.
 */
export async function getAdminEnrollments() {
  const response = await api.get("/admin/enrollments");
  return response.data;
}

/**
 * Delete an existing enrollment record.
 */
export async function deleteAdminEnrollment(enrollmentId) {
  const response = await api.delete(
    `/admin/enrollments/${enrollmentId}`
  );

  return response.data;
}

/**
 * Preview enrollment for a department, cohort, semester, and section.
 *
 * Pass offeringIds to preview selected offerings.
 * Pass an empty array to preview no offerings.
 * Omit offeringIds to preview all matching offerings.
 */
export async function previewGroupEnrollment(
  groupData,
  offeringIds
) {
  const payload = {
    department_id: Number(groupData.department_id),
    academic_year: groupData.academic_year,
    semester: Number(groupData.semester),
    section: groupData.section,
  };

  if (Array.isArray(offeringIds)) {
    payload.offering_ids = offeringIds.map(Number);
  } else if (Array.isArray(groupData.offering_ids)) {
    payload.offering_ids = groupData.offering_ids.map(Number);
  }

  const response = await api.post(
    "/admin/enrollments/group-preview",
    payload
  );

  return response.data;
}

/**
 * Retrieve enrollment summary metrics and student groups.
 */
export async function getAdminEnrollmentsSummary() {
  const response = await api.get("/admin/enrollments/summary");
  return response.data;
}

/**
 * Enroll eligible students in the selected offerings.
 *
 * Do not call until the preview has been checked and confirmed.
 */
export async function bulkEnrollGroup(groupData) {
  const payload = {
    department_id: Number(groupData.department_id),
    academic_year: groupData.academic_year,
    semester: Number(groupData.semester),
    section: groupData.section,
  };

  if (Array.isArray(groupData.course_ids)) {
    payload.course_ids = groupData.course_ids.map(Number);
  }

  if (Array.isArray(groupData.offering_ids)) {
    payload.offering_ids = groupData.offering_ids.map(Number);
  }

  if (Array.isArray(groupData.student_ids)) {
    payload.student_ids = groupData.student_ids.map(Number);
  }

  const response = await api.post(
    "/admin/enrollments/group-bulk",
    payload
  );

  return response.data;
}