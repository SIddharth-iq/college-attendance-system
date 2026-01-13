# Backend Freeze – API v3

## Scope

- All frontend must use ONLY `/api/v3/*`
- No legacy or v2 endpoints are allowed
- Any backend change after this requires explicit version bump

## Roles & Access Contracts

### ADMIN

- Full system visibility
- Can access:
  - /reports/admin/global
  - /reports/subject/{id}
  - /reports/defaulters/{id}
  - /reports/session/{id}
  - /reports/session/{id}/summary
  - /reports/student/{student_id}
- No scoping restrictions

### FACULTY

- Scoped strictly to own sessions
- Can access:
  - /reports/session/{id} (only own)
  - /reports/session/{id}/summary (only own)
  - /reports/faculty/student/{student_id} (own sessions only)
- Must NEVER see:
  - Other faculty sessions
  - Global stats

### STUDENT

- Self-only visibility
- Can access:
  - /reports/student/{student_id} (only self)
- Must NEVER see:
  - Other students
  - Faculty-scoped endpoints
  - Global or defaulter reports

## Response Stability

- Field names and nesting are locked
- Empty datasets return 200 with empty arrays (not 403)
- Invalid access returns 403
- Invalid IDs return 404

## Seed Data Guarantee

- Multiple faculty
- Multiple subjects
- Same student across multiple faculty
- Mixed attendance states
