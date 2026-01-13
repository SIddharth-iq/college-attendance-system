Frontend API Contract – v3 (FROZEN)

⚠️ THIS CONTRACT IS FROZEN

Frontend must use ONLY /api/v3/\*

No breaking changes without introducing /api/v4

Backend guarantees the structure and semantics documented here

Frontend must not assume undocumented fields

Base Rules

All API calls use /api/v3/\*

Empty datasets return 200 OK with empty arrays and zero counts

Unauthorized access returns 403 Forbidden

Invalid resource IDs return 404 Not Found

Date validation errors return 400 Bad Request

No pagination guarantees

No CSV/export guarantees

No backward compatibility outside /api/v3

🔐 Role-Based API Access
ROLE: ADMIN
Allowed Endpoints

GET /api/v3/reports/admin/global

GET /api/v3/reports/subject/{subject_id}

GET /api/v3/reports/defaulters/{subject_id}

GET /api/v3/reports/session/{session_id}

GET /api/v3/reports/session/{session_id}/summary

GET /api/v3/reports/student/{student_id}

GET /api/v3/reports/faculty/student/{student_id}

Visibility Rules

Full system visibility

Can view data across all faculty, students, subjects, and sessions

No scoping restrictions

Can access any student’s report

Global reports include cross-faculty aggregates

Guarantees

Admin dashboard is powered exclusively by /reports/admin/global

Subject/session/defaulter reports are unrestricted

Admin access is never scoped

ROLE: FACULTY
Allowed Endpoints

GET /api/v3/reports/session/{session_id}

GET /api/v3/reports/session/{session_id}/summary

GET /api/v3/reports/faculty/student/{student_id}

Visibility Rules
Session Endpoints

Access allowed ONLY if:

AttendanceSessionV3.faculty_id == current_user.id

Otherwise → 403 Forbidden

Faculty–Student Report

Data strictly scoped to sessions taught by the logged-in faculty

Query-level enforcement via faculty_id filter

If faculty never taught the student:

Returns 200 OK

Zero counts

Empty subject breakdown

NOT 403 or 404 (intentional UX decision)

Explicit Restrictions

❌ Cannot access /reports/admin/global

❌ Cannot view other faculty’s sessions

❌ Cannot view cross-faculty aggregates

❌ Cannot access /reports/student/{student_id} unless ADMIN

ROLE: STUDENT
Allowed Endpoints

GET /api/v3/reports/student/{student_id}

Visibility Rules

Student can access ONLY their own student_id

Accessing any other student → 403 Forbidden

Explicit Restrictions

❌ No access to faculty-scoped endpoints

❌ No access to admin/global endpoints

❌ No access to defaulters

❌ No access to session or subject reports

📊 Attendance Percentage Semantics (CRITICAL)

attendance_percentage represents attendance coverage / participation completeness,
NOT attendance quality.

Formula
((present + absent + late) / total_sessions) \* 100

Rules

Late counts as attended

Percentage reflects how much attendance was recorded, not performance

This definition is consistent across:

Student reports

Faculty-student reports

Admin aggregates

Frontend must not reinterpret this field.

🧊 Freeze Declaration

The following are guaranteed for frontend:

Endpoint paths

Role access rules

Response field names

Attendance percentage semantics

Error behaviors (403 / 404 / 400)

The following are explicitly not guaranteed:

CSV export availability

Pagination

Field ordering

Additional computed fields

Performance characteristics
