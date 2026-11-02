# SAMS-FR API Documentation

## Computer Vision Module

### 1. Purpose

The Computer Vision (CV) module is responsible for:

- Face detection
- Face validation
- Face alignment and preprocessing
- Face feature extraction
- Face comparison
- Student recognition
- Face registration

The CV module must not directly access or modify the attendance database.

The integration boundary is:

Camera/Image
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

---

## 2. CV Technology Stack

| Component | Technology |
|---|---|
| Programming Language | Python 3.11 |
| Computer Vision | OpenCV 5.0.0 |
| Face Detection | YuNet |
| Face Recognition | SFace |
| Model Format | ONNX |
| Initial Execution | CPU |
| Input | Camera frame / image |

### Models

- YuNet: `face_detection_yunet_2023mar.onnx`
- SFace: `face_recognition_sface_2021dec.onnx`

The model files are stored locally and excluded from Git.

---

## 3. CV Processing Pipeline

Camera/Image
    |
    v
Face Detection
    |
    v
Face Validation
    |
    v
Face Alignment / Preprocessing
    |
    v
SFace Feature Extraction
    |
    v
Feature Comparison
    |
    v
Student Identification
    |
    v
Recognition Result

---

## 4. CV Service Interface

### `detect_faces()`

Detect faces in an image or camera frame.

**Input:**
- Image/frame

**Output:**
- Face bounding boxes
- Facial landmarks
- Detection confidence

**Technology:**
- YuNet

---

### `extract_face()`

Extract and align a detected face for recognition.

**Input:**
- Image/frame
- Detected face information

**Output:**
- Aligned face

---

### `generate_encoding()`

Generate a feature representation for an aligned face.

**Input:**
- Aligned face

**Output:**
- Face feature vector

**Technology:**
- SFace

---

### `compare_encoding()`

Compare a probe face feature with a registered face feature.

**Input:**
- Probe face feature
- Registered face feature

**Output:**
- Similarity score
- Match decision

The final matching threshold will be determined through validation and testing.

---

### `recognize_student()`

Identify a student from a face in an image or camera frame.

**Input:**
- Image/frame
- Registered student face features

**Processing:**

Image
    |
    v
Face Detection
    |
    v
Face Alignment
    |
    v
Feature Extraction
    |
    v
Feature Comparison
    |
    v
Best Candidate
    |
    v
Recognition Result

**Conceptual output:**

```json
{
  "student_id": "STU001",
  "matched": true,
  "similarity_score": 0.0,
  "status": "recognized"
}
```

The exact response schema will be finalized when the CV service and backend service contracts are implemented.

---

## 5. Face Registration Workflow

Student
    |
    v
Capture Image
    |
    v
Detect Face
    |
    v
Validate Face
    |
    v
Align / Preprocess
    |
    v
Generate Encoding
    |
    v
Store Face Data

### Validation Cases

The registration workflow must handle:

- No face detected
- Multiple faces detected
- Poor-quality image
- Invalid face crop
- Duplicate or incorrect registration
- Feature-generation failure

Registration should not proceed when the captured image fails the required validation checks.

---

## 6. Attendance Recognition Workflow

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

The CV module only produces the recognition result.

The Attendance Service is responsible for attendance rules and database operations.

---

## 7. Application Architecture Boundary

The expected application flow is:

Route
    |
    v
Service
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

The CV service must remain independent of database operations.

This separation allows the recognition pipeline to be tested independently from attendance management.

---

## 8. Recognition Result

The CV service should return a structured recognition result containing information such as:

- Student identifier
- Match status
- Similarity score
- Recognition status
- Optional error or rejection reason

Example:

```json
{
  "student_id": "STU001",
  "matched": true,
  "similarity_score": 0.0,
  "status": "recognized"
}
```

The exact response schema will be finalized when the CV service and backend service contracts are implemented.

---

## 9. Current Environment Verification

The selected environment has been verified with:

- Python 3.11.9
- OpenCV 5.0.0
- YuNet model loading successfully
- SFace model loading successfully
- Initial execution target: CPU

The recognition threshold and production performance characteristics remain subject to testing.

---

## 10. Current Status

### Completed

- CV technology stack selected
- OpenCV environment verified
- YuNet selected for face detection
- SFace selected for face recognition
- ONNX models obtained locally
- Model loading verified
- CV service interface defined
- Face registration workflow defined
- Attendance recognition workflow defined
- CV/database separation defined

### Pending

- Implement CV service
- Test face detection
- Test face alignment
- Test feature extraction
- Test face matching
- Determine matching threshold experimentally
- Test recognition accuracy
- Integrate recognition result with backend Attendance Service