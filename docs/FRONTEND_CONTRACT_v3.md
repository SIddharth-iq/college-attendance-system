# Frontend API Contract – v3 (Frozen)

⚠️ This contract is frozen.
Frontend must use ONLY `/api/v3/*`.
Breaking changes require a new API version.

🔐 Role-Based API Access
ADMIN
Allowed Endpoints

- GET /api/v3/reports/admin/global
- GET /api/v3/reports/subject/{subject_id}
- GET /api/v3/reports/defaulters/{subject_id}
- GET /api/v3/reports/session/{session_id}
- GET /api/v3/reports/session/{session_id}/summary
- GET /api/v3/reports/student/{student_id}
- GET /api/v3/reports/faculty/student/{student_id}

Visibility Rules

- Full system visibility
- Can view data across all faculty, students, subjects, and sessions
- No scoping restrictions

Notes

- Student reports are unrestricted for ADMIN
- Global aggregates include cross-faculty data

FACULTY
Allowed Endpoints

- GET /api/v3/reports/session/{session_id}
- GET /api/v3/reports/session/{session_id}/summary
- GET /api/v3/reports/faculty/student/{student_id}

Visibility Rules

- Session endpoints:

  - Access allowed ONLY if session.faculty_id == current_user.id
  - Otherwise → 403 Forbidden

- Faculty-student report:
  - Data strictly scoped to sessions taught by the faculty
  - If no matching sessions exist → 200 OK with zero counts

Explicit Restrictions

- Cannot access /reports/admin/global
- Cannot view other faculty’s sessions
- Cannot view global aggregates

STUDENT
Allowed Endpoints

- GET /api/v3/reports/student/{student_id}

Visibility Rules

- Can access ONLY their own student_id
- Accessing another student_id → 403 Forbidden

Explicit Restrictions

- No access to faculty endpoints
- No access to admin/global endpoints
- No access to defaulters or aggregates

📊 Attendance Percentage Semantics (IMPORTANT)
attendance_percentage represents attendance coverage/completeness,
not attendance quality.

Formula:
((present + absent + late) / total_sessions) \* 100

Late counts as attended.

This avoids future arguments with frontend or stakeholders.

❌ Non-Goals (Guaranteed Not Supported)

- No CSV export guarantees
- No pagination guarantees
- No backward compatibility outside /api/v3
- No undocumented fields should be consumed by frontend
