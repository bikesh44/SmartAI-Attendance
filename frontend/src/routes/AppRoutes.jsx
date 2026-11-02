
import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import ProtectedRoute from "./ProtectedRoute";

// Shared Layouts (eagerly imported to keep navigation stable)
import AdminLayout from "../layouts/AdminLayout";
import FacultyLayout from "../layouts/FacultyLayout";
import StudentLayout from "../layouts/StudentLayout";

// Auth & Public Pages (lazy loaded)
const Unauthorized = lazy(() => import("../pages/Unauthorized"));
const Login = lazy(() => import("../pages/auth/Login"));
const ForgotPassword = lazy(() => import("../pages/auth/ForgotPassword"));
const VerifyOtp = lazy(() => import("../pages/auth/VerifyOtp"));

// Admin Portal Pages (lazy loaded)
const AdminDashboard = lazy(() => import("../pages/admin/AdminDashboard"));
const Students = lazy(() => import("../pages/admin/Students"));
const FaceRegistration = lazy(() => import("../pages/admin/FaceRegistration"));
const Faculty = lazy(() => import("../pages/admin/Faculty"));
const Departments = lazy(() => import("../pages/admin/Departments"));
const AcademicManagement = lazy(() => import("../pages/admin/AcademicManagement"));
const CourseEnrollments = lazy(() => import("../pages/admin/CourseEnrollments"));
const AcademicResults = lazy(() => import("../pages/admin/AcademicResults"));
const AttendanceReports = lazy(() => import("../pages/admin/AttendanceReports"));
const AdminManagement = lazy(() => import("../pages/admin/AdminManagement"));
const BatchManagement = lazy(() => import("../pages/admin/BatchManagement"));
const TimetableManagement = lazy(() => import("../pages/admin/TimetableManagement"));
const AdminProfile = lazy(() => import("../pages/admin/AdminProfile"));
const AdminSettings = lazy(() => import("../pages/admin/AdminSettings"));
const ActivityLogs = lazy(() => import("../pages/admin/ActivityLogs"));

// Faculty Portal Pages (lazy loaded)
const FacultyDashboard = lazy(() => import("../pages/faculty/FacultyDashboard"));
const Classes = lazy(() => import("../pages/faculty/Classes"));
const FacultyStudents = lazy(() => import("../pages/faculty/Students"));
const AssignmentsNotes = lazy(() => import("../pages/faculty/AssignmentsNotes"));
const Attendance = lazy(() => import("../pages/faculty/Attendance"));
const Reports = lazy(() => import("../pages/faculty/Reports"));
const ResultUpload = lazy(() => import("../pages/faculty/ResultUpload"));
const FacultyProfile = lazy(() => import("../pages/faculty/Profile"));
const FacultySettings = lazy(() => import("../pages/faculty/Settings"));

// Student Portal Pages (lazy loaded)
const StudentDashboard = lazy(() => import("../pages/student/StudentDashboard"));
const Profile = lazy(() => import("../pages/student/Profile"));
const StudentAttendance = lazy(() => import("../pages/student/Attendance"));
const AttendanceHistory = lazy(() => import("../pages/student/AttendanceHistory"));
const Courses = lazy(() => import("../pages/student/Courses"));
const AcademicReport = lazy(() => import("../pages/student/AcademicReport"));
const Schedule = lazy(() => import("../pages/student/Schedule"));
const StudentReports = lazy(() => import("../pages/student/Reports"));
const StudentSettings = lazy(() => import("../pages/student/Settings"));
const StudentAssignmentsNotes = lazy(() => import("../pages/student/StudentAssignmentsNotes"));

function PageFallback() {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "40vh",
        width: "100%",
        opacity: 0.8,
      }}
    >
      <div
        style={{
          width: "28px",
          height: "28px",
          border: "3px solid rgba(148, 163, 184, 0.2)",
          borderTopColor: "#38bdf8",
          borderRadius: "50%",
          animation: "pageSpin 0.7s linear infinite",
        }}
      />
      <style>{`@keyframes pageSpin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function AppRoutes() {
  return (
    <Suspense fallback={<PageFallback />}>
      <Routes>
        {/* Default */}
        <Route
          path="/"
          element={<Navigate to="/auth" replace />}
        />

        {/* Authentication */}
        <Route path="/auth" element={<Login />} />

        <Route
          path="/auth/forgot-password"
          element={<ForgotPassword />}
        />

        <Route
          path="/auth/verify-otp"
          element={<VerifyOtp />}
        />

        <Route
          path="/unauthorized"
          element={<Unauthorized />}
        />

        {/* Admin portal */}
        <Route
          path="/admin"
          element={
            <ProtectedRoute allowedRole="ADMIN">
              <AdminLayout />
            </ProtectedRoute>
          }
        >
          <Route
            index
            element={<Navigate to="/admin/dashboard" replace />}
          />

          <Route
            path="dashboard"
            element={<AdminDashboard />}
          />

          {/* User management */}
          <Route
            path="management"
            element={<AdminManagement />}
          />
          <Route
            path="add-user"
            element={<AdminManagement />}
          />

          <Route
            path="students"
            element={<Students />}
          />

          <Route
            path="face-registration"
            element={<FaceRegistration />}
          />

          <Route
            path="faculty"
            element={<Faculty />}
          />

          {/* Departments */}
          <Route
            path="departments"
            element={<Departments />}
          />
          <Route
            path="department"
            element={<Departments />}
          />

          {/* Academic management */}
          <Route
            path="academic-management"
            element={
              <Navigate
                to="/admin/academic-management/courses"
                replace
              />
            }
          />

          <Route
            path="academic-management/courses"
            element={<AcademicManagement />}

          />

          <Route
            path="academic-management/course-offerings"
            element={<AcademicManagement />}

          />

          <Route
            path="academic-management/course-enrollments"
            element={<CourseEnrollments />}
          />

          <Route
            path="academic-management/assignments"
            element={<AcademicManagement />}

          />

          <Route
            path="academic-management/results"
            element={<AcademicResults />}
          />

          <Route
            path="academic-results"
            element={
              <Navigate
                to="/admin/academic-management/results"
                replace
              />
            }

          />

          {/* Keep the original batch URL working */}
          <Route
            path="academic-management/batches"
            element={
              <Navigate to="/admin/batches" replace />
            }
          />

          {/* Batches: matches the sidebar URL */}
          <Route
            path="batches"
            element={<BatchManagement />}
          />

          {/* Timetable management */}
          <Route
            path="timetable"
            element={<TimetableManagement />}
          />
          <Route
            path="timetable/faculty-adjustment"
            element={<TimetableManagement />}
          />

          {/* Attendance reports */}
          <Route
            path="attendance-reports"
            element={<AttendanceReports />}
          />
          <Route
            path="attendance"
            element={<AttendanceReports />}
          />

          {/* Admin account */}
          <Route
            path="profile"
            element={<AdminProfile />}
          />

          <Route
            path="settings"
            element={<AdminSettings />}
          />

          {/* Activity Logs */}
          <Route
            path="activity"
            element={<ActivityLogs />}
          />
          <Route
            path="activity-logs"
            element={<ActivityLogs />}
          />
        </Route>

        {/* Faculty portal */}
        <Route
          path="/faculty"
          element={
            <ProtectedRoute allowedRole="FACULTY">
              <FacultyLayout />
            </ProtectedRoute>
          }
        >
          <Route
            index
            element={<Navigate to="/faculty/dashboard" replace />}
          />

          <Route
            path="dashboard"
            element={<FacultyDashboard />}
          />

          <Route
            path="classes"
            element={<Classes />}
          />

          <Route
            path="students"
            element={<FacultyStudents />}
          />

          <Route
            path="assignments"
            element={<AssignmentsNotes />}
          />
          <Route
            path="assignments-notes"
            element={<Navigate to="/faculty/assignments" replace />}
          />

          <Route
            path="attendance"
            element={<Attendance />}
          />

          <Route
            path="reports"
            element={<Reports />}
          />

          <Route
            path="results"
            element={<ResultUpload />}
          />
          <Route
            path="result-upload"
            element={<Navigate to="/faculty/results" replace />}
          />

          <Route
            path="profile"
            element={<FacultyProfile />}
          />

          <Route
            path="settings"
            element={<FacultySettings />}
          />
        </Route>

        {/* Student portal */}
        <Route
          path="/student"
          element={
            <ProtectedRoute allowedRole="STUDENT">
              <StudentLayout />
            </ProtectedRoute>
          }
        >
          <Route
            index
            element={<Navigate to="/student/dashboard" replace />}
          />

          <Route
            path="dashboard"
            element={<StudentDashboard />}
          />

          <Route
            path="attendance"
            element={<StudentAttendance />}
          />

          <Route
            path="daily-punch"
            element={<StudentAttendance />}
          />

          <Route
            path="attendance-history"
            element={<AttendanceHistory />}
          />

          <Route
            path="courses"
            element={<Courses />}
          />

          <Route
            path="assignments"
            element={<StudentAssignmentsNotes />}
          />
          <Route
            path="assignments-notes"
            element={<Navigate to="/student/assignments" replace />}
          />

          <Route
            path="academic-records"
            element={<AcademicReport />}
          />

          <Route
            path="academic-report"
            element={<AcademicReport />}
          />

          <Route
            path="profile"
            element={<Profile />}
          />

          <Route
            path="timetable"
            element={<Schedule />}
          />

          <Route
            path="schedule"
            element={<Schedule />}
          />

          <Route
            path="reports"
            element={<StudentReports />}
          />

          <Route
            path="attendance/subject-wise"
            element={<StudentReports />}
          />

          <Route
            path="subject-wise-report"
            element={<StudentReports />}
          />

          <Route
            path="settings"
            element={<StudentSettings />}
          />
        </Route>

        {/* Unknown routes */}
        <Route
          path="*"
          element={<Navigate to="/auth" replace />}
        />
      </Routes>
    </Suspense>
  );
}

export default AppRoutes;
