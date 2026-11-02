# SAMS-FR: Smart Attendance Management System Using Face Recognition

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask Version](https://img.shields.io/badge/Flask-3.1-black.svg)](https://flask.palletsprojects.com/)
[![React Version](https://img.shields.io/badge/React-19.2-61DAFB.svg)](https://react.dev/)
[![Vite Version](https://img.shields.io/badge/Vite-8.2-646CFF.svg)](https://vitejs.dev/)
[![OpenCV DNN](https://img.shields.io/badge/OpenCV-YuNet%20%2B%20SFace-5C3EE8.svg)](https://opencv.org/)
[![Database](https://img.shields.io/badge/MySQL-8.0-4479A1.svg)](https://www.mysql.com/)
[![Automated Tests](https://img.shields.io/badge/Pytest-486%20Passed-brightgreen.svg)](backend/tests/)
[![License: Proprietary](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)

An academic capstone project and engineering prototype for a contactless, AI-powered web attendance platform that automates attendance tracking and academic lifecycle management by decoupling facial recognition from proprietary hardware kiosks. SAMS-FR captures camera frames directly through standard web browsers, processes deep neural embeddings using OpenCV DNN (YuNet + SFace), validates liveness via multi-cue anti-spoofing, and commits verified attendance to a centralized relational database.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Project Objectives](#project-objectives)
- [Feature Matrix](#feature-matrix)
- [Key Features](#key-features)
  - [Administrator Portal](#1-administrator-portal)
  - [Faculty Portal](#2-faculty-portal)
  - [Student Portal](#3-student-portal)
  - [Face Registration and Biometric Verification](#4-face-registration-and-biometric-verification)
  - [Presentation Attack Detection (Anti-Spoofing)](#5-presentation-attack-detection-anti-spoofing)
  - [Attendance Tracking and Duplicate Prevention](#6-attendance-tracking-and-duplicate-prevention)
  - [Academic Records, Coursework and Notes](#7-academic-records-coursework-and-notes)
- [Technology Stack](#technology-stack)
- [System Architecture](#system-architecture)
- [Computer Vision Pipeline](#computer-vision-pipeline)
- [Repository Structure](#repository-structure)
- [Prerequisites](#prerequisites)
- [Installation and Setup](#installation-and-setup)
  - [1. Clone Repository](#1-clone-repository)
  - [2. Database Setup](#2-database-setup)
  - [3. Backend Setup](#3-backend-setup)
  - [4. Frontend Setup](#4-frontend-setup)
- [Running the Application](#running-the-application)
- [Running Tests and Verification](#running-tests-and-verification)
- [Application Screenshots](#application-screenshots)
- [Project Documentation](#project-documentation)
- [Security and Privacy Considerations](#security-and-privacy-considerations)
- [Known Limitations](#known-limitations)
- [License](#license)

---

## Project Overview

Traditional attendance management in educational institutions commonly relies on manual paper roll calls or dedicated fingerprint/facial biometric terminals installed at classroom entrances. Both paradigms present operational hurdles:
- **Manual Calling**: Consumes 10–15 minutes of lecture time, introduces human transcription errors, and is susceptible to proxy attendance.
- **Dedicated Hardware Biometric Stations**: Require expensive physical hardware procurement, ongoing maintenance, power/network cabling, and generate bottlenecks during class changeovers.

**SAMS-FR** resolves these systemic challenges through a modern, three-tier web application architecture. By utilizing the HTML5 MediaDevices API in standard desktop and laptop browsers, authorized faculty members conduct attendance sessions using their existing devices. Deep learning computer vision pipelines execute asynchronously on the Flask backend, matching probe faces against enrolled embeddings using lightweight ONNX neural networks.

> **Development State**: SAMS-FR is an **academic capstone project and engineering prototype**. Developed as a functional reference implementation with 486 passing automated tests across 47 verified test files and end-to-end multi-role portals, biometric thresholds are calibrated on controlled development datasets and require multi-cohort validation prior to production deployment.

---

## Project Objectives

Derived from the original institutional project synopsis ([synopsis.pdf](project_report/synopsis.pdf)), SAMS-FR achieves eight primary objectives:

1. **Web-Based Attendance**: Enable authorized instructors to mark attendance using any camera-equipped computing device through standard web browsers.
2. **Automated Facial Recognition**: Accurately detect, align, and identify registered students in real time without physical contact.
3. **Proxy Mitigation**: Mitigate proxy attendance and fraudulent records through AI-driven facial recognition, liveness verification heuristics, and role-based JWT authentication.
4. **Three Dedicated Portals**: Deliver isolated, role-specific interfaces for Administrators, Faculty Members, and Students.
5. **Centralized Database**: Maintain a relational schema in MySQL 8.0 mapping students, faculty, course offerings, timetables, and attendance logs.
6. **Analytics and Institutional Reporting**: Provide multi-format export engines (CSV, XLSX, PDF) and real-time visual analytics on student attendance compliance.
7. **Responsive Multi-Device Operation**: Ensure accessibility across desktops, laptops, and tablets without native client installation.
8. **Extensible System Architecture**: Integrate advanced academic workflows including master timetable scheduling, temporary faculty substitution, anti-spoofing challenge protocols, and coursework distribution.

---

## Feature Matrix

| Feature / Domain | Module Scope | Status | Verification Evidence |
|---|---|---|---|
| **Multi-Role Authentication** | Admin, Faculty, Student login with JWT | **Implemented** | [`backend/app/routes/auth.py`](backend/app/routes/auth.py) |
| **Face Detection & Alignment** | YuNet ONNX edge face detector | **Implemented** | [`.cv-models/face_detection_yunet_2023mar.onnx`](.cv-models/face_detection_yunet_2023mar.onnx) |
| **Face Embedding Extraction** | SFace 128D deep feature vectors | **Implemented** | [`.cv-models/face_recognition_sface_2021dec.onnx`](.cv-models/face_recognition_sface_2021dec.onnx) |
| **Biometric Distance Matching** | Cosine similarity with 0.5400 threshold | **Implemented** | [`docs/architecture/RECOGNITION_THRESHOLD.md`](docs/architecture/RECOGNITION_THRESHOLD.md) |
| **Passive Liveness (PAD)** | Fourier 2D, chrominance, texture analysis | **Implemented** | [`backend/app/services/cv/liveness_service.py`](backend/app/services/cv/liveness_service.py) |
| **Active Liveness Challenge** | Randomized head turn, nod, and blink | **Implemented** | [`backend/evaluate_liveness.py`](backend/evaluate_liveness.py) |
| **Live Attendance Session** | Real-time camera attendance for faculty | **Implemented** | [`frontend/src/pages/faculty/Attendance.jsx`](frontend/src/pages/faculty/Attendance.jsx) |
| **Daily Punch Face Punch-in** | Student self-service biometric punch | **Implemented** | [`frontend/src/pages/student/Attendance.jsx`](frontend/src/pages/student/Attendance.jsx) |
| **Multi-Format Export Engine** | Attendance registers to CSV, XLSX, and PDF | **Implemented** | [`backend/app/utils/export_engine/`](backend/app/utils/export_engine/) |
| **Master Timetable Matrix** | Room scheduling, period grids, substitution | **Implemented** | [`backend/app/routes/timetable.py`](backend/app/routes/timetable.py) |
| **Assignments & Notes Hub** | Coursework creation, uploads, submissions | **Implemented** | [`frontend/src/pages/faculty/AssignmentsNotes.jsx`](frontend/src/pages/faculty/AssignmentsNotes.jsx) |
| **Academic Results Moderation**| Internal assessment gradebook & report cards | **Implemented** | [`backend/app/routes/admin_academic_results.py`](backend/app/routes/admin_academic_results.py) |
| **Native Mobile Applications** | Dedicated iOS / Android standalone apps | *Future Scope* | Documented in Project Synopsis & Final Report |
| **Multi-Tenant Cloud Clusters**| Distributed Kubernetes / ERP connectors | *Future Scope* | Documented in Project Synopsis & Final Report |

---

## Key Features

### 1. Administrator Portal
- **Institutional Analytics**: Real-time metrics tracking enrolled students, faculty members, active course offerings, and daily attendance trends.
- **Student Lifecycle Management**: Searchable directory with cohort, semester, and section filters, student registration modals, and status badges.
- **Biometric Enrollment**: Multi-angle camera capture (Frontal, Left, Right, Up, Down) extracting 128D SFace embeddings into relational storage.
- **Curriculum & Faculty Allocation**: Academic department structure, course configurations, batch graduation, and faculty course assignments.
- **Master Timetable Scheduling**: Visual weekly period grid mapping rooms, class times, instructors, and temporary substitute allocations.
- **Institutional Reports & Auditing**: Comprehensive attendance analytics exportable to Excel/PDF and searchable security audit logs.

### 2. Faculty Portal
- **Daily Teaching Schedule**: Dashboard highlighting current-day class periods, assigned course offerings, and room allocations.
- **Real-Time Attendance Control**: Web-based camera session allowing automated face detection and identification of students in the class roster.
- **Manual Fallback Marking**: Fast toggle controls to manually override or mark student attendance with immediate audit logging.
- **Multi-Format Export Engine**: Download official course attendance registers in CSV, Microsoft Excel (`.xlsx`), or formatted PDF.
- **Assignments & Study Material**: Upload lecture notes, syllabus guidelines, and coursework assignments with deadlines and submission limits.
- **Internal Assessment Gradebook**: Entry and evaluation interface for mid-term marks and academic assessments.

### 3. Student Portal
- **Personal Attendance Metric**: Transparent aggregate percentage tracking compliance against the institutional 75% attendance threshold.
- **Contactless Daily Punch**: Self-service facial verification interface confirming daily on-campus attendance.
- **Chronological History Log**: Searchable and date-filtered attendance records detailing session timestamps, subjects, and verification methods.
- **Weekly Class Timetable**: Visual schedule matrix detailing daily class hours, subjects, room assignments, and instructors.
- **Coursework & Study Material**: Dedicated hub to view active assignments, submit completed work, and download faculty-uploaded lecture notes.
- **Official Academic Transcripts**: Download formatted semester attendance report cards and academic result summaries in PDF.

### 4. Face Registration and Biometric Verification
- **Multi-Angle Enrollment**: Gathers 5 distinct facial orientations to generate a robust biometric profile under varying poses.
- **Pose Quality Gating**: YuNet landmark tracking ensures frontal alignment and adequate facial sharpness prior to embedding generation.
- **SFace Deep Metric Embeddings**: Faces are transformed into compact 128-dimensional float32 feature vectors (512 bytes) via OpenCV DNN, stored as binary BLOBs in MySQL without application-level encryption at rest.
- **Cosine Distance Matching**: Verification compares probe vectors against enrolled templates using cosine similarity:
  $$\text{Cosine Similarity} = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\|_2 \|\mathbf{v}\|_2}$$
  Matches are confirmed when $\text{Cosine Similarity} \ge 0.5400$ (calibrated in [`docs/architecture/RECOGNITION_THRESHOLD.md`](docs/architecture/RECOGNITION_THRESHOLD.md)).

### 5. Presentation Attack Detection (Anti-Spoofing)
- **Passive Multi-Cue Analysis**:
  - *2D Fourier Frequency Spectrum*: Identifies high-frequency periodic lattice artifacts characteristic of screen moiré and printer halftone dots.
  - *Chrominance & Glare Analysis*: Analyzes skin pigment dispersion across YCrCb and HSV color spaces to detect digital screen backlights and paper reflections.
  - *Laplacian Gradient Variance*: Evaluates texture sharpness and optical blur.
  - *Temporal Difference*: Analyzes frame-to-frame variations across consecutive frames to detect static photo presentation.
- **Active Liveness Challenge**:
  - Issues randomized, cryptographically fresh challenges (`TURN_HEAD_LEFT`, `TURN_HEAD_RIGHT`, `NOD_HEAD_DOWN`, `TILT_HEAD_UP`, `BLINK`).
  - Tracks 3D head-pose angular ratios and eye aspect ratios (EAR) across timestamped frame sequences.
  - Enforces single-use verification tokens with short expiry to mitigate token replay.
- **Heuristic Characterization**: Passive PAD metrics and active motion challenge checks are computer-vision and signal-processing heuristics designed to mitigate presentation attacks from physical print photographs and digital screen replays. They do not constitute cryptographic proofs or mathematically absolute anti-spoofing guarantees.

### 6. Attendance Tracking and Duplicate Prevention
- **Dual-Layer Concurrency Control**:
  - *Application Guard*: Attendance routes query active session records prior to processing, returning HTTP 400/409 if a student is already marked.
  - *Database Engine Guard*: Enforced at the relational storage level via composite database constraint:
    ```sql
    UNIQUE KEY uq_session_student_attendance (session_id, student_id)
    ```

### 7. Academic Records, Coursework and Notes
- **Full-Stack Coursework Lifecycle**: Faculty upload assignment specifications and lecture materials; students upload submissions with deadline verification; faculty grade submissions in the internal assessment gradebook.
- **Academic Results Moderation**: Admin and faculty moderation workflows supporting marks entry, moderation, and PDF report card publishing.
- **Analytical Time Savings Estimate**: Projected operational time savings (e.g., reducing attendance overhead from 10–15 minutes of manual calling to ~1–2 minutes per session) represent analytical workflow modeling estimates, not an empirical multi-classroom stopwatch study.

---

## Technology Stack

```
+-----------------------------------------------------------------------------------+
|                                  PRESENTATION LAYER                               |
|   React 19.2  *  Vite 8.2  *  React Router 7.18  *  Tailwind CSS  *  Axios 1.19    |
+-----------------------------------------------------------------------------------+
                                         |
                            HTTP/REST + JWT Cookies
                                         v
+-----------------------------------------------------------------------------------+
|                                  APPLICATION LAYER                                |
|   Python 3.10  *  Flask 3.1  *  Flask-JWT-Extended 4.7  *  SQLAlchemy 2.0 ORM     |
|   Flask-Migrate 4.1 (Alembic)  *  Flask-Bcrypt  *  Flask-CORS  *  PyMySQL 1.2    |
+-----------------------------------------------------------------------------------+
                     |                                       |
                     v                                       v
+------------------------------------+  +-------------------------------------------+
|       COMPUTER VISION ENGINE       |  |                 DATA LAYER                |
|  OpenCV 4.10 DNN (YuNet + SFace)   |  |  MySQL 8.0 Relational Database (24 Tables)|
|  NumPy 2.4  *  DeepFace (Auxiliary)|  |  OpenPyXL 3.1 (XLSX) * ReportLab 4.4 (PDF) |
+------------------------------------+  +-------------------------------------------+
```

---

## System Architecture

SAMS-FR follows a three-tier architecture ensuring complete separation of presentation, business logic, and relational persistence:

![System Architecture](project_report/assets/diagrams/figure1_system_architecture.png)

1. **Presentation Layer (Frontend)**: Single-Page Application (SPA) built with React 19 and Vite. Coordinates camera streams using the HTML5 MediaDevices API, executes client-side form validations, and enforces role-based navigation guards.
2. **Application Layer (Backend API)**: RESTful Flask service structuring business logic into modular blueprints (`auth`, `admin`, `faculty`, `student`, `attendance`, `recognition`, `timetable`, `reports`). Manages JWT lifecycle and executes computer vision inference.
3. **Data Layer (Storage & Persistence)**: Centralized MySQL 8.0 relational database containing 24 relational tables mapped from 24 SQLAlchemy ORM models with foreign keys and cascade rules. Biometric templates are stored as 128D vector arrays linked to student records.

---

## Computer Vision Pipeline

```mermaid
flowchart TD
    A["Camera Capture (Browser)"] --> B["Base64 Frame Transmission"]
    B --> C["OpenCV Image Decoding"]
    C --> D["YuNet Face Detection & 5-Landmark Localization"]
    D --> E{"Passive PAD Check<br/>(Fourier / Glare / Texture)"}
    E -- Failed --> F["Reject: Presentation Attack Detected"]
    E -- Passed --> G{"Active Challenge Required?"}
    G -- Yes --> H["Pose Ratio & Blink Verification"]
    H -- Failed --> F
    G -- No --> I["SFace 128D Feature Extraction"]
    H -- Passed --> I
    I --> J["Cosine Similarity Matching (Threshold >= 0.5400)"]
    J --> K{"Matched Student Enrolled?"}
    K -- No --> L["Status: Not Recognized / Unknown"]
    K -- Yes --> M["Check Duplicate Record (uq_session_student_attendance)"]
    M -- Duplicate --> N["Reject: Already Marked"]
    M -- Unique --> O["Commit AttendanceRecord to MySQL"]
```

---

## Repository Structure

```text
SAMS-FR/
├── .cv-models/                             # Deep learning ONNX computer vision models
│   ├── face_detection_yunet_2023mar.onnx   # YuNet edge face detector (232 KB)
│   └── face_recognition_sface_2021dec.onnx # SFace 128D feature recognizer (38.7 MB)
├── backend/                                # Flask application root
│   ├── app/
│   │   ├── models/                         # 24 SQLAlchemy ORM models (24 mapped tables)
│   │   ├── routes/                         # Modular Flask blueprint controllers
│   │   ├── services/                       # Business logic, export engine, auth service
│   │   │   └── cv/                         # FaceService and LivenessService (PAD)
│   │   ├── utils/                          # JWT decorators, token blocklist, formatters
│   │   ├── config.py                       # Database URI, JWT, and CORS configuration
│   │   └── __init__.py                     # Application factory (create_app)
│   ├── cv/                                 # Computer vision test scripts and recognizers
│   ├── migrations/                         # Alembic database schema migrations
│   ├── tests/                              # Pytest automated test suite (47 verified test files)
│   ├── .env.example                        # Template environment variables
│   ├── evaluate_liveness.py                # Standalone PAD & active liveness benchmark
│   ├── requirements.txt                    # Python dependency manifest
│   └── run.py                              # Flask development server entrypoint
├── docs/                                   # Architectural documentation and diagrams
│   ├── api/                                # REST API endpoint specifications
│   ├── architecture/                       # System contracts and threshold calibrations
│   └── database/                           # ER diagram mappings and checklist
├── frontend/                               # React Single-Page Application root
│   ├── src/
│   │   ├── components/                     # Reusable UI components (LiveFaceCapture, Tables)
│   │   ├── context/                        # AuthContext and role state providers
│   │   ├── pages/                          # Role-isolated portal views
│   │   │   ├── admin/                      # 10 Administrator management views
│   │   │   ├── faculty/                    # 7 Faculty teaching & attendance views
│   │   │   └── student/                    # 8 Student self-service & records views
│   │   └── services/                       # Axios API communication services
│   ├── package.json                        # Node.js dependencies and scripts
│   └── vite.config.js                      # Vite server proxy configuration
├── project_report/                         # Comprehensive Academic Project Documentation
│   ├── assets/
│   │   ├── diagrams/                       # 5 High-resolution system UML diagrams
│   │   └── screenshots/                    # 42 Desktop application screenshots
│   ├── SAMS-FR_Project_Report_Final.pdf    # Final 85-page compiled Word PDF report
│   ├── SAMS-FR_Project_Report_Final.docx   # Final editable Word report deliverable
│   ├── FINAL_ACADEMIC_AUDIT.md             # 15-area technical audit against synopsis
│   ├── FINAL_VALIDATION_REPORT.md          # Word COM field and pagination audit
│   ├── FEATURE_TRACEABILITY.md             # Feature-to-code traceability register
│   ├── SCREENSHOT_REGISTER.md              # 42-image metadata and route register
│   └── synopsis.pdf                        # Original 19-page institutional synopsis
└── README.md                               # Project documentation
```

---

## Prerequisites

Ensure the following runtimes and tools are installed:

- **Operating System**: Windows 10/11, macOS, or Linux (PowerShell commands documented below).
- **Python**: Version `3.10` or higher (`python --version`).
- **Node.js**: Version `20.19.0` or higher (or `22.12.0+`; required by Vite 8) with `npm` (`node -v`, `npm -v`).
- **MySQL Database Server**: Version `8.0` or higher running locally or accessible via network.
- **Hardware**: Standard computing workstation equipped with a functional web camera (720p or 1080p recommended).

---

## Installation and Setup

### 1. Clone Repository
Open Windows PowerShell and navigate to your workspace directory:
```powershell
git clone https://github.com/Upendra78/SAMS-FR.git
cd SAMS-FR
```

Verify that the pre-trained ONNX models exist in `.cv-models/`:
```powershell
Get-ChildItem .cv-models\*.onnx
```
*(Both `face_detection_yunet_2023mar.onnx` and `face_recognition_sface_2021dec.onnx` must be present).*

---

### 2. Database Setup
Start your MySQL Server and launch the MySQL CLI:
```powershell
mysql -u root -p
```
Create the database:
```sql
CREATE DATABASE sams_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;
```

---

### 3. Backend Setup
Navigate into `backend/`, initialize a Python virtual environment, and install dependencies:
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create your backend environment configuration file:
```powershell
Copy-Item .env.example .env
```

#### Environment Variables Reference (`backend/.env`)

Configure `backend/.env` matching your local environment:

| Variable | Description | Default / Example Value |
|---|---|---|
| `SECRET_KEY` | Flask application session secret | `dev-secret-key-sams-fr-change-in-production` |
| `JWT_SECRET_KEY` | Secret key for signing JWT tokens | `jwt-secret-key-sams-fr-change-in-production` |
| `LOCAL_DB_USER` | MySQL database username | `root` |
| `LOCAL_DB_PASSWORD` | MySQL database password | `your_mysql_password` |
| `LOCAL_DB_HOST` | MySQL database host address | `localhost` |
| `LOCAL_DB_NAME` | MySQL database schema name | `sams_db` |
| `CORS_ORIGINS` | Allowed frontend origin for CORS | `http://localhost:5173` |
| `INSTITUTION_TIMEZONE` | Timezone for schedule checking | `Asia/Kolkata` |
| `DATABASE_URL` | Optional reference URI (shown in `.env.example`) | `mysql+pymysql://root:password@localhost:3306/sams_db` |

Apply database migrations to instantiate all 24 relational tables:
```powershell
flask db upgrade
```

---

### 4. Frontend Setup
Open a separate PowerShell terminal, navigate to `frontend/`, and install Node dependencies:
```powershell
cd frontend
npm install
```

---

## Running the Application

### 1. Start the Flask Backend API
From the activated backend virtual environment (`backend/`):
```powershell
python run.py
```
*The backend API server launches at: **`http://127.0.0.1:5000`***

### 2. Start the Vite Frontend Client
From the frontend directory (`frontend/`):
```powershell
npm run dev
```
*The React client launches at: **`http://localhost:5173`***

Open your browser and navigate to `http://localhost:5173` to access the central Multi-Role Authentication Gateway.

---

## Running Tests and Verification

### Backend Automated Test Suite (Pytest)
From `backend/` with the virtual environment active:
```powershell
pytest -q
```
*Executes all 486 unit, integration, and security tests across 47 test files in `backend/tests/`.*

### Presentation Attack Detection Benchmark
Run the standalone passive and active liveness verification suite:
```powershell
python evaluate_liveness.py
```
*Evaluates passive multi-cue PAD on 80 test cases and active challenges across 40 test cases.*

### Frontend Code Quality and Static Analysis
From `frontend/`:
```powershell
# Run ESLint static analysis
npm run lint

# Compile production bundle
npm run build
```
*Compiles 2,100+ modules into optimized production chunks (`vendor-react`, CSS assets).*

---

## Application Screenshots

### Authentication Gateway
The central login portal features dynamic role selection across Administrator, Faculty, and Student portals:

![Central Authentication Gateway](project_report/assets/screenshots/login/login_page.png)

---

### Administrator Portal
Holistic academic governance, student management, timetable scheduling, and biometric face registration:

| Administrator Dashboard | Multi-Angle Face Registration |
|---|---|
| ![Admin Dashboard](project_report/assets/screenshots/admin/admin_dashboard.png) | ![Face Registration](project_report/assets/screenshots/admin/admin_face_registration.png) |

| Student Lifecycle Management | Master Timetable Scheduling |
|---|---|
| ![Student Management](project_report/assets/screenshots/admin/admin_student_management.png) | ![Timetable Management](project_report/assets/screenshots/admin/admin_timetable_management.png) |

---

### Faculty Portal
Pedagogical session management, real-time computer vision attendance, and coursework distribution:

| Faculty Dashboard & Schedule | Real-Time Attendance Session |
|---|---|
| ![Faculty Dashboard](project_report/assets/screenshots/faculty/faculty_dashboard.png) | ![Live Attendance](project_report/assets/screenshots/faculty/faculty_attendance.png) |

| Assignments & Study Notes Hub | Multi-Format Attendance Reports |
|---|---|
| ![Assignments and Notes](project_report/assets/screenshots/faculty/faculty_assignments_notes.png) | ![Faculty Reports](project_report/assets/screenshots/faculty/faculty_reports.png) |

---

### Student Portal
Self-service attendance tracking, contactless daily punch-in, timetables, and academic transcripts:

| Student Dashboard & Attendance Metric | Contactless Daily Punch Verification |
|---|---|
| ![Student Dashboard](project_report/assets/screenshots/student/student_dashboard.png) | ![Daily Punch](project_report/assets/screenshots/student/student_daily_punch.png) |

| Chronological Attendance History | Coursework & Study Material Downloads |
|---|---|
| ![Attendance History](project_report/assets/screenshots/student/student_attendance_history.png) | ![Student Assignments and Notes](project_report/assets/screenshots/student/student_assignments_notes.png) |

---

## Project Documentation

Comprehensive academic documentation, technical specifications, and validation audits are available in the repository:

- 📄 **[Final Academic Project Report (PDF)](project_report/SAMS-FR_Project_Report_Final.pdf)**: Complete 85-page university project report formatted in Times New Roman with native Word dynamic Table of Contents, List of Figures, List of Tables, and sequential pagination.
- 📝 **[Final Academic Project Report (DOCX)](project_report/SAMS-FR_Project_Report_Final.docx)**: Fully editable Microsoft Word master document.
- 🔍 **[Final Academic Content Audit](project_report/FINAL_ACADEMIC_AUDIT.md)**: 15-area technical audit evaluating report claims against actual source code, database models, and the project synopsis.
- 📋 **[Final Word Field Validation Report](project_report/FINAL_VALIDATION_REPORT.md)**: Field-by-field verification of dynamic Word sequences and page numbering.
- 🗺️ **[Feature Traceability Matrix](project_report/FEATURE_TRACEABILITY.md)**: Traceability register linking all 31 application features to backend blueprints, frontend components, and database models.
- 📸 **[Screenshot Register](project_report/SCREENSHOT_REGISTER.md)**: Detailed metadata inventory of all 42 desktop screenshots and 5 UML diagrams.
- 🎯 **[Original Project Synopsis](project_report/synopsis.pdf)**: 19-page institutional project proposal defining the baseline objectives.
- 📐 **[Biometric Recognition Threshold](docs/architecture/RECOGNITION_THRESHOLD.md)**: Calibration empirical data establishing the 0.5400 cosine similarity threshold.
- 📡 **[REST API Documentation](docs/api/api-documentation.md)**: Specification of Flask endpoints, schemas, and HTTP status codes.

---

## Security and Privacy Considerations

1. **Biometric Template & Image Handling**:
   - **Camera Frames & Biometric Pipeline**: Camera frames captured during face enrollment, facial recognition, attendance verification, and active liveness verification are decoded and processed transiently in volatile system memory (`cv2.imdecode`); no raw camera frames are persisted by these audited pipelines to disk or the relational database.
   - **Student Profile Photos**: Student profile photos uploaded through `/api/student/upload-photo` are saved as image files to disk under `uploads/students/photos/` and referenced by `students.photo_url`. When a student uploads a replacement photo, the previous file on disk is deleted if it exists within `uploads/students/photos/` and differs from the newly written file.
   - **Biometric Embeddings**: SFace generates 128-dimensional float32 embeddings (512 bytes) stored in the `face_profiles.embedding` column as a MySQL binary BLOB. Application-level encryption at rest is not implemented; embeddings are stored as unencrypted binary payloads. Transport-layer security between web clients and the Flask application requires HTTPS in production, while encryption for database client-server connections (MySQL TLS) depends on separate database server and connection string configuration and is not enabled by default in development. Consequently, host infrastructure security, database user privilege controls, and network-level isolation are the primary operational controls.
2. **Credential Protection**: User passwords are cryptographically hashed using bcrypt with individual per-user salts (12 rounds) before database persistence, rather than reversibly encrypted.
3. **Session Authentication & Cookie Security**: JWT access tokens are stored in `HttpOnly`, `SameSite=Lax` cookies with configurable expiration policies (7 days for general users, 3 hours for administrators). The `HttpOnly` flag prevents direct client-side JavaScript access to `document.cookie`, but it does not prevent or eliminate underlying Cross-Site Scripting (XSS) vulnerabilities, nor does it stop malicious scripts executing in the browser from initiating authenticated requests (e.g., via `fetch` or `XMLHttpRequest`). In development, `JWT_COOKIE_SECURE` is `False` to permit local testing over unencrypted HTTP; production deployments must set `JWT_COOKIE_SECURE=True` over HTTPS. Note that explicit double-submit CSRF cookie protection is not currently configured.
4. **Anti-Replay & Liveness Challenge State**: Active liveness challenges use cryptographically random identifiers generated via the Python `secrets` module and issue single-use verification tokens bound to specific sessions and student/faculty identities. However, active challenge state, issued verification tokens, and the JWT token revocation blocklist are held in backend process memory. This in-memory state is lost upon process restart and is not shared across multi-worker WSGI processes or multi-server deployments without an external distributed store such as Redis.
5. **Presentation Attack Detection (PAD) Limitations**: Passive PAD checks (Fourier 2D frequency spectrum, chrominance dispersion, Laplacian texture variance) and active motion challenge checks are computer-vision and signal-processing heuristics rather than cryptographic proofs or absolute anti-spoofing guarantees. While designed to detect artifacts typical of physical print photographs and digital screen replays, they are heuristic in nature and do not provide mathematically unforgeable proofs of physical presence.
6. **Role-Based Access Control**: Sensitive administrative and faculty endpoints are protected by backend decorators (`@admin_required`, `@faculty_required`) that verify role claims directly on each request.

---

## Known Limitations

- **Environmental Lighting Sensitivity**: Recognition accuracy decreases under severe backlighting, high-contrast shadows, underexposure, or insufficient ambient illumination.
- **Extreme Facial Occlusion**: Heavy occlusions (opaque sunglasses, medical masks covering the nose and mouth) prevent landmark localization, requiring manual fallback marking by instructors.
- **Controlled Threshold Calibration**: The current cosine similarity threshold ($0.5400$) was calibrated on a controlled development test dataset. Multi-cohort tuning across diverse demographic populations is recommended before large-scale campus rollouts.
- **Network Dependency**: Client workstations and mobile browsers require reliable local area network (LAN) or internet connectivity to communicate with the Flask API backend.

---

## License

This software and its documentation are proprietary and confidential. Copyright &copy; 2026 Bikesh Kumar Pandit and Upendra Kumar Maurya. All rights reserved. Unauthorized copying, modification, distribution, or commercial exploitation is strictly prohibited without prior written permission from the copyright holders. See the [LICENSE](LICENSE) file for complete details.
