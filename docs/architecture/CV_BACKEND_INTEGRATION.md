# CV and Backend Integration Contract

## Purpose

This document defines the integration boundary between the Flask backend and the Computer Vision face recognition service.

The Computer Vision module is responsible only for face detection, face preprocessing, feature extraction, face comparison, and student recognition.

The Flask backend is responsible for receiving API requests, preparing registered student data, handling attendance logic, and communicating with the database.

The Computer Vision service does not directly access the database or record attendance.

## Integration Flow

The intended integration flow is:

```text
React Frontend
      |
      v
Flask API Route
      |
      v
Backend Service
      |
      v
FaceService.recognize_student()
      |
      v
Recognition Result
      |
      v
Attendance Service
      |
      v
Database
```

The Computer Vision service remains independent from the attendance and database layers.

## CV Service Entry Point

The backend should use the following service method for student recognition:

```python
FaceService.recognize_student(
    image,
    registered_students,
    similarity_threshold,
)
```

The backend should call this method through the service layer rather than placing Computer Vision logic directly inside a Flask route.

## Input Contract

The `recognize_student()` method expects three inputs.

### 1. Image

The `image` parameter is an OpenCV BGR image or camera frame.

Example:

```python
image = cv2.imread("student.jpg")
```

The image must be valid and non-empty.

If the image is invalid or empty, the CV service raises:

```text
ValueError: Invalid or empty image.
```

### 2. Registered Students

The `registered_students` parameter contains the face features of registered students that can be considered for recognition.

Each student entry should provide:

```python
{
    "student_id": "STU001",
    "encoding": registered_feature
}
```

The backend is responsible for obtaining the registered student data from the appropriate service or database layer and providing it to the CV service.

The CV service does not retrieve this data from the database itself.

### 3. Similarity Threshold

The `similarity_threshold` parameter defines the minimum cosine similarity required for a recognition match.

The current experimental threshold is:

```python
similarity_threshold = 0.54
```

This value is currently experimental and is subject to future validation.

## Recognition Processing

The CV service performs the following processing:

```text
Input Image
    |
    v
Face Detection
    |
    v
Face Validation
    |
    +---- No face ------> no_face
    |
    +---- Multiple faces -> multiple_faces
    |
    v
Face Alignment
    |
    v
Feature Extraction
    |
    v
Comparison with Registered Features
    |
    v
Best Candidate
    |
    v
Similarity Threshold
    |
    v
Recognition Result
```

## Output Contract

The CV service returns a structured recognition result.

Example for a recognized student:

```python
{
    "student_id": "STU001",
    "matched": True,
    "similarity_score": 0.6955,
    "status": "recognized"
}
```

For an unrecognized student:

```python
{
    "student_id": None,
    "matched": False,
    "similarity_score": 0.4711,
    "status": "not_recognized"
}
```

The complete recognition result definitions are documented separately in:

`RECOGNITION_RESULT_CONTRACT.md`

## Recognition Statuses

The CV service can return the following recognition statuses:

| Status | Meaning |
|---|---|
| `recognized` | A registered student matched the input face above the configured threshold. |
| `not_recognized` | A face was detected, but no registered student met the similarity threshold. |
| `no_face` | No face was detected in the input image. |
| `multiple_faces` | More than one face was detected, so the frame is rejected as ambiguous. |
| `no_registered_students` | No registered student data was provided for comparison. |
| `no_valid_registered_encoding` | No valid registered face encoding was available for comparison. |

## Backend Responsibility After Recognition

The backend must interpret the recognition result and decide what action should occur.

For example:

```text
Recognition Result
      |
      v
matched == True
      |
      v
Validate Attendance Rules
      |
      v
Attendance Service
      |
      v
Database
```

The CV service must not:

- Create attendance records.
- Update attendance tables.
- Query the database.
- Decide whether attendance should be marked.
- Handle authentication or authorization.
- Communicate directly with the React frontend.

## Separation of Responsibilities

### Computer Vision Service

Responsible for:

- Face detection.
- Face alignment and preprocessing.
- Face feature extraction.
- Face feature comparison.
- Student recognition.
- Returning the recognition result.

### Backend Service

Responsible for:

- Receiving recognition requests.
- Preparing registered student face data.
- Calling the CV service.
- Interpreting the recognition result.
- Applying attendance rules.
- Communicating with the database.

### Attendance Service

Responsible for:

- Attendance validation.
- Duplicate attendance prevention.
- Attendance record creation.
- Attendance-related business rules.

### Database Layer

Responsible for:

- Persisting student data.
- Persisting registered face data as defined by the approved database design.
- Persisting attendance records.
- Providing stored data to backend services.

## Integration Boundary

The required boundary is:

```text
Flask Route
      |
      v
Backend Service
      |
      v
CV Service
      |
      v
Recognition Result
      |
      v
Attendance Service
      |
      v
Database
```

The CV service stops at the recognition result.

This separation allows the Computer Vision module to be tested independently and prevents Computer Vision code from becoming tightly coupled to Flask routes or database operations.
