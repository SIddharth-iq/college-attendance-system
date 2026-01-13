# Frontend Data Map – API v3

This document defines which backend endpoints feed each frontend screen.
Backend is frozen at `/api/v3/*`.

---

## ROLE: ADMIN

### 1. Admin Dashboard (Overview Screen)

**Endpoint**
GET /api/v3/reports/admin/global

**Purpose**
System-wide attendance overview.

**Fields Used**

- summary.total_sessions
- summary.unique_students_count
- summary.total_subjects
- summary.total_faculty
- summary.date_range.start_date
- summary.date_range.end_date

- attendance_overview.present_count
- attendance_overview.absent_count
- attendance_overview.late_count
- attendance_overview.marked_percentage

**Charts / Tables**

- subject_breakdown[]

  - subject_name
  - total_sessions
  - present_count
  - absent_count

- faculty_breakdown[]
  - faculty_name
  - total_sessions
  - present_count
  - absent_count

---

### 2. Subject Detail (Admin)

**Endpoint**
GET /api/v3/reports/subject/{subject_id}

**Purpose**
Deep dive into a subject across all faculty.

**Fields Used**

- subject metadata
- total_sessions
- attendance counts
- faculty-wise breakdown

---

### 3. Session Summary (Admin)

**Endpoint**
GET /api/v3/reports/session/{session_id}/summary

**Purpose**
Audit individual attendance session.

**Fields Used**

- session info
- student list
- attendance status per student

---

## ROLE: FACULTY

### 1. Faculty Dashboard

**Endpoint**
GET /api/v3/reports/faculty/student/{student_id}

**Purpose**
View attendance of a specific student scoped to logged-in faculty.

**Guaranteed Rules**

- Only sessions taught by current faculty are included
- If no relation exists → returns 200 with empty data

**Fields Used**

- student.student_code
- summary.total_sessions
- summary.present_count
- summary.absent_count
- summary.attendance_percentage

- subject_breakdown[]
  - subject_name
  - total_sessions
  - present_count
  - absent_count

---

### 2. Session Summary (Faculty)

**Endpoint**
GET /api/v3/reports/session/{session_id}/summary

**Purpose**
Review own session attendance.

**Rules**

- Faculty can only access their own sessions
- Others return 403

---

## ROLE: STUDENT

### 1. Student Dashboard

**Endpoint**
GET /api/v3/reports/student/{student_id}

**Purpose**
Student views their own attendance across all subjects.

**Rules**

- Student can ONLY access their own student_id
- Cross-student access returns 403

**Fields Used**

- summary.total_sessions
- summary.present_count
- summary.absent_count
- summary.attendance_percentage

- subject_breakdown[]
  - subject_name
  - total_sessions
  - present_count
  - absent_count

---

## Global Rules

- All frontend calls use `/api/v3/*`
- Empty datasets return 200 with empty arrays
- Unauthorized access returns 403
- Invalid IDs return 404
- No frontend assumptions beyond documented fields
