# Face Recognition Test Report

## 1. Overview

This document describes the automated tests implemented for the SAMS-FR face recognition service.
The tests verify the recognition service's behavior for known students, face detection edge cases, invalid registration data, and similarity threshold boundaries.

## 2. Test Framework

- Framework: Python unittest
- Mocking: unittest.mock.MagicMock
- Image processing: OpenCV
- Test module: tests/cv/test_recognition.py

## 3. Test Environment

- Python version: 3.11.9
- Operating system: Windows
- Virtual environment: .venv-1
- Backend import configuration: PYTHONPATH=backend

## 4. Test Cases

|Test ID| Test Case                               | Expected Result   |
|-------|-----------------------------------------|------------------------------|
| TC-01 | Recognize Student A                     | Student STU001 is recognized |
| TC-02 | Recognize Student B                     | Student STU002 is recognized |
| TC-03 | Unknown student                         | Recognition fails with not_recognized status |
| TC-04 | Image contains no face                  | Recognition fails with no_face status |
| TC-05 | Image contains multiple faces           | Recognition fails with multiple_faces status |
| TC-06 | No registered students                  | Recognition fails with no_registered_students status |
| TC-07 | Invalid registered encoding             | Recognition fails with no_valid_registered_encoding status |
| TC-08 | Missing student ID                      | Invalid registration record is skipped |
| TC-09 | Mixed valid and invalid student records | Valid Student A is recognized |
| TC-10 | Similarity equals threshold (0.54)      | Student is recognized |
| TC-11 | Similarity below threshold (0.5399)     | Student is not recognized |

## 5. Result Contract
The tests verify that recognition results contain the following keys:
- student_id
- matched
- similarity_score
- status

## 6. Test Execution
Command:
    $env:PYTHONPATH="$PWD\backend"
    python -m unittest test.cv.test_recognition -v

## 7. Test Results
Execution date: 2026-09-21
Total tests executed: 11
passed: 11
Failed: 0
Errors: 0
Overall result: PASS

## 8. Notes
- Image-based tests use the test images stored in tests/cv/images/.
- Threshold tests use mocked components to control similarity values.
- The threshold boundary tests verify acceptance at 0.54 and rejection at 0.5399.
- These results reflect execution in the local development environment.
- The test report does not establish production readiness or validate the complete SAMS-FR application.