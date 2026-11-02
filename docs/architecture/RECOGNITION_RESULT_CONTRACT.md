# Recognition Result Contract

## Purpose

This document defines the structured result returned by the Computer Vision recognition service.

The Flask backend uses this result to determine whether a student was successfully recognized and what action should be taken next.

The recognition service does not directly record attendance or access the database.

## Standard Recognition Result

The `FaceService.recognize_student()` method returns a dictionary with the following fields:

```python
{
      "student_id": "STU001",
      "matched": True,
      "similarity_score": 0.6955,
      "status": "recognized",
}
```
