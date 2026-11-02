# Face Enrollment Result Contract
## 1. Purpose
This document defines the result returned by the CV service when enrolling a student's face.

The CV service generates and validates a face encoding. It does not save student information or write to the database.

## 2. Input
The enrollment method is:
    FaceService.enroll_student(image)

The input is a BGR image represented as a NumPy array.

## 3. Successful Enrollment

When exactly one face is detected and a valid encoding is generated, the method returns:
    {
        "status": "enrolled",
        "encoding": encoding
    }

The encoding is a NumPy array with:

- Shape: (1, 128)
- Data type: float32
- Values: finite numerical values

The backend is responsible for associating the encoding with the student and saving it to the database.

## 4. Failure Results

| Status        | Meaning
|---------------|---------------
| invalid_image | The input image is missing or empyt. |
| no_face       | No face was detected in the image. |
| multiple_faces| More than one face was detected. |
| encoding_failed| An expected encoding operation failed. |
| invalid_encoding| The generated encoding failed validation. |

Failure results contain:
    {
        "status": "<failure_status>",
        "encoding": None
    }

## 5. Responsibilities

### CV Service

- Validate the input image.
- Detect faces.
- Require exactly one detected face.
- Align and crop the face.
- Generate the face encoding.
- Validate the encoding.
- Return the enrollment result.

### Backend

- Authenticate and authorize the requesting user.
- Obtain the student's record.
- Call the CV enrollment mehtod.
- Associate the returned encoding with the correct student.
- Persist the encoding securely.
- Handle API responses and database operations.

## 6. Important Notes

The encoding is a Numpy array, not a JSON-serialization value.

The backend is a NumPy array, not a JSON-serializable value.

The backend must convert or serialize it appropriately before storing or transmitting it.

The CV service does not independently confirm a studnet's identity. Enrollment must be associated with a student trhough the backend's authentication and authorization workflow.