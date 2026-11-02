# SAMS-FR System Integration Review

## Purpose

This document records the current integration boundaries and
implementation gaps identified during system integration review.

The review is based on the existing frontend services, backend
structure, API documentation, database documentation, and CV
service documentation.

## 1. Frontend -> Backend

### Current Frontend Boundary

The login page calls:

POST /auth/login

The request is sent through the frontend Axios API client.

The backend base URL is configured through:

VITE_API_BASE_URL

### Current Status

Frontend authentication communication is defined in the frontend.

The corresponding Flask authentication route was not found in the
current backend implementation reviewed during this integration check.

### Required Follow-up

Backend authentication implementation must provide the endpoint
expected by the frontend authentication service.

The request and response schema should be finalized between the
frontend and backend owners.

---

## 2. Backend -> Computer Vision

### Expected Boundary

The backend/service layer communicates with the CV service.

The CV service is responsible for:

- Face detection
- Face validation
- Face alignment and preprocessing
- Feature extraction
- Face comparison
- Student recognition
- Face registration

The CV service must not directly access or modify the attendance
database.

### Current Status

The CV service file exists in:

backend/app/services/face_service.py

The API documentation defines the conceptual CV service interface.

The backend-to-CV integration route/service contract is not yet
implemented in the current backend structure reviewed.

### Required Follow-up

The backend service owner and CV owner should finalize the service
interface and structured recognition result contract.

---

## 3. Computer Vision -> Attendance

### Expected Flow

Camera/Image
    |
    v
Face Detection
    |
    v
Face Validation
    |
    v
Face Alignment
    |
    v
Face Encoding
    |
    v
Face Matching
    |
    v
Student ID
    |
    v
Attendance Validation
    |
    v
Attendance Record

### Responsibility Boundary

The CV module produces the recognition result.

The Attendance Service is responsible for attendance rules and
database operations.

### Current Status

The recognition workflow is documented.

Integration of the recognition result with the backend Attendance
Service remains pending.

---

## 4. Database Boundary

The approved architecture requires database operations to remain
within the backend/service layer.

The CV module must not directly access the attendance database.

The approved ER model provides the entity and relationship structure
that backend models and database tables must follow.

### Current Status

Database entities and relationships have been reviewed and documented.

Backend database models and database operations are part of the
backend implementation work.

---

## 5. Current Integration Gaps

| Integration Area | Current Status | Required Action |
|---|---|---|
| Frontend -> Authentication | Frontend call exists | Backend authentication endpoint required |
| Frontend -> Other APIs | Service layer exists | Verify each endpoint against backend implementation |
| Backend -> CV | CV service exists | Finalize backend/CV service contract |
| CV -> Attendance | Workflow documented | Connect recognition result to attendance processing |
| Services -> Database | Architecture defined | Implement and verify backend database operations |
| Recognition Response | Conceptual schema documented | Finalize exact response contract |
| Attendance Validation | Workflow documented | Implement backend attendance rules |

---

## 6. Integration Principles

- Frontend communicates with the backend through defined API endpoints.
- Backend services own business logic.
- CV processing remains independent from database operations.
- Attendance rules and attendance database operations belong to the
  backend Attendance Service.
- Recognition results must be structured before being passed to
  attendance processing.
- Approved ER entities and relationships must be preserved.
- Integration contracts should be agreed upon before dependent
  components are connected.

---

## 7. Review Result

The project has documented integration boundaries and workflows,
but several implementation-level connections remain pending.

The identified gaps should be resolved by the corresponding module
owners before end-to-end integration is considered complete.
