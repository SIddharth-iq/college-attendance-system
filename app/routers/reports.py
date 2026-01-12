"""
Phase 3.3 Reporting routes.
Provides read-only reporting endpoints for Attendance V3 data.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func, case, and_
from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, List
from app.database import get_db
from app.models import (
    User,
    AttendanceSessionV3,
    AttendanceRecordV3,
    AttendanceStatusEnum,
    Subject,
    Student,
    ClassEnrollment,
    ClassSubject,
    RoleEnum,
)
from app.routers.auth import require_role
from app.services.reports_service import (
    get_attendance_data_for_csv,
    generate_csv_content,
    get_session_attendance_summary,
    generate_session_summary_csv,
    get_global_attendance_report,
    get_student_attendance_report,
    get_faculty_student_attendance_report,
)
from app.schemas import (
    SessionAttendanceSummaryV3Response,
    AttendanceStatsV3,
    SessionStudentSummaryItemV3,
    GlobalAttendanceReportResponse,
    StudentAttendanceReportResponse,
    FacultyStudentAttendanceReportResponse,
)

router = APIRouter()


# Response schemas
class SessionReportResponse(BaseModel):
    """Response schema for session report endpoint."""

    session_id: int
    session_date: date
    subject_id: int
    subject_code: str
    subject_name: str
    is_locked: bool
    present_count: int
    absent_count: int
    late_count: int
    total_records: int

    class Config:
        from_attributes = True


class SubjectReportResponse(BaseModel):
    """Response schema for subject report endpoint."""

    subject_id: int
    subject_code: str
    subject_name: str
    total_sessions: int
    total_students: int
    total_records: int
    present_count: int
    absent_count: int
    late_count: int
    overall_attendance_percentage: float

    class Config:
        from_attributes = True


class StudentReportResponse(BaseModel):
    """Response schema for student report endpoint."""

    student_id: int
    student_code: str
    full_name: str
    total_sessions: int
    present_count: int
    absent_count: int
    late_count: int
    attendance_percentage: float

    class Config:
        from_attributes = True


class DefaulterReportResponse(BaseModel):
    """
    Response schema for defaulter report endpoint.

    Note: student_id is the internal database ID (primary key),
    while student_code is the external student identifier (e.g., "STU2024001").
    """

    student_id: int
    student_code: str
    full_name: str
    total_sessions: int
    present_count: int
    absent_count: int
    late_count: int
    attendance_percentage: float

    class Config:
        from_attributes = True


@router.get("/session/{session_id}", status_code=status.HTTP_200_OK)
def get_session_report(
    session_id: int,
    current_user: User = Depends(require_role([RoleEnum.ADMIN, RoleEnum.FACULTY])),
    db: Session = Depends(get_db),
):
    """
    Get present/absent/late counts for a single attendance session.
    Admin can access any session. Faculty can only access their own sessions.
    """
    # Get the session
    session = (
        db.query(AttendanceSessionV3)
        .filter(AttendanceSessionV3.id == session_id)
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance session not found",
        )

    # Enforce faculty access control: Faculty can only access their own sessions
    if current_user.role == RoleEnum.FACULTY:
        if session.faculty_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your own attendance sessions",
            )

    # Get subject details
    subject = db.query(Subject).filter(Subject.id == session.subject_id).first()
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject not found for this session",
        )

    # Count records by status
    status_counts = (
        db.query(
            AttendanceRecordV3.status,
            func.count(AttendanceRecordV3.id).label("count"),
        )
        .filter(AttendanceRecordV3.session_id == session_id)
        .group_by(AttendanceRecordV3.status)
        .all()
    )

    # Initialize counts
    present_count = 0
    absent_count = 0
    late_count = 0

    # Aggregate counts by status
    for status_enum, count in status_counts:
        if status_enum == AttendanceStatusEnum.PRESENT:
            present_count = count
        elif status_enum == AttendanceStatusEnum.ABSENT:
            absent_count = count
        elif status_enum == AttendanceStatusEnum.LATE:
            late_count = count

    # Calculate total records
    total_records = present_count + absent_count + late_count

    # Build response
    return SessionReportResponse(
        session_id=session.id,
        session_date=session.session_date,
        subject_id=subject.id,
        subject_code=subject.code,
        subject_name=subject.name,
        is_locked=session.is_locked,
        present_count=present_count,
        absent_count=absent_count,
        late_count=late_count,
        total_records=total_records,
    )


# -------------------------------------------------------------------
# SESSION SUMMARY (Phase 6.2)
# -------------------------------------------------------------------
@router.get(
    "/session/{session_id}/summary",
    response_model=SessionAttendanceSummaryV3Response,
    status_code=status.HTTP_200_OK,
)
def get_session_attendance_summary_v3(
    session_id: int,
    current_user: User = Depends(require_role([RoleEnum.FACULTY, RoleEnum.ADMIN])),
    db: Session = Depends(get_db),
):
    """
    Get comprehensive attendance summary for a single session (JSON format).

    Returns session metadata, aggregated statistics (present/absent/late/not_marked counts
    and percentages), and a detailed per-student attendance list. This endpoint is designed
    for analytics, reporting, and dashboards.

    FACULTY can only access their own sessions. ADMIN can access any session.
    STUDENT access is forbidden.

    Edge cases handled:
    - Empty subject enrollment: returns zero counts and empty student list
    - All students unmarked: returns not_marked_count == total_students
    - Division by zero: percentages return 0.0 when total_students == 0
    - Unlocked session: locked_at returns None

    For CSV export, use: GET /api/v3/reports/session/{session_id}/summary/export

    Existing endpoints remain unchanged:
    - /session/{session_id} - Basic counts without per-student details
    - /sessions/{session_id}/students - Raw student records for editing
    """
    return get_session_attendance_summary(session_id, current_user, db)


@router.get("/session/{session_id}/summary/export", status_code=status.HTTP_200_OK)
def export_session_attendance_summary_csv(
    session_id: int,
    current_user: User = Depends(require_role([RoleEnum.FACULTY, RoleEnum.ADMIN])),
    db: Session = Depends(get_db),
):
    """
    Export session attendance summary as CSV file.

    Returns the same summary data as the JSON endpoint (/session/{session_id}/summary)
    in CSV format, suitable for Excel and other spreadsheet applications.

    CSV structure:
    - Session metadata rows (ID, date, subject, faculty, lock status)
    - Aggregated statistics rows (total students, counts, percentages)
    - Blank separator row
    - Student table with header and data rows (code, name, status, marked_at)

    FACULTY can only access their own sessions. ADMIN can access any session.
    STUDENT access is forbidden.

    Edge cases handled:
    - Empty subject enrollment: CSV with metadata and zero counts, no student rows
    - All students unmarked: CSV with empty status fields for all students
    - Division by zero: percentages show 0.00 when total_students == 0
    - Unlocked session: locked_at field is empty

    Authorization matches the JSON summary endpoint exactly.
    Percentages match JSON endpoint exactly (same precision).
    """
    # Get summary data from service (handles auth and queries)
    summary_data = get_session_attendance_summary(session_id, current_user, db)

    # Generate CSV content
    csv_content = generate_session_summary_csv(summary_data)

    # Return CSV response with proper headers
    filename = (
        f"session_{session_id}_attendance_summary_{summary_data.session_date}.csv"
    )
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/subject/{subject_id}", status_code=status.HTTP_200_OK)
def get_subject_report(
    subject_id: int,
    start_date: Optional[date] = Query(
        None, description="Start date filter (YYYY-MM-DD)"
    ),
    end_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    current_user: User = Depends(require_role([RoleEnum.ADMIN, RoleEnum.FACULTY])),
    db: Session = Depends(get_db),
):
    """
    Get subject-level attendance summary.
    Admin can access any subject. Faculty can only access subjects where they have created sessions.
    """
    # Verify subject exists
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject not found",
        )

    # Build base query for sessions
    sessions_query = db.query(AttendanceSessionV3).filter(
        AttendanceSessionV3.subject_id == subject_id
    )

    # Apply date range filter if provided
    if start_date:
        sessions_query = sessions_query.filter(
            AttendanceSessionV3.session_date >= start_date
        )
    if end_date:
        sessions_query = sessions_query.filter(
            AttendanceSessionV3.session_date <= end_date
        )

    # Enforce faculty access control: Faculty can only access their own sessions
    if current_user.role == RoleEnum.FACULTY:
        sessions_query = sessions_query.filter(
            AttendanceSessionV3.faculty_id == current_user.id
        )

    # Get all session IDs for this subject (with filters applied)
    session_ids = [s.id for s in sessions_query.all()]

    # If no sessions found, check if faculty is trying to access unauthorized subject
    if not session_ids:
        if current_user.role == RoleEnum.FACULTY:
            # Check if subject exists but faculty has no sessions for it
            any_session = (
                db.query(AttendanceSessionV3)
                .filter(AttendanceSessionV3.subject_id == subject_id)
                .first()
            )
            if any_session:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only access subjects where you have created sessions",
                )
        # Return empty summary if no sessions (for admin or if no sessions exist at all)
        return SubjectReportResponse(
            subject_id=subject.id,
            subject_code=subject.code,
            subject_name=subject.name,
            total_sessions=0,
            total_students=0,
            total_records=0,
            present_count=0,
            absent_count=0,
            late_count=0,
            overall_attendance_percentage=0.0,
        )

    # Count total sessions
    total_sessions = len(session_ids)

    # Count total unique students
    total_students = (
        db.query(func.count(func.distinct(AttendanceRecordV3.student_id)))
        .filter(AttendanceRecordV3.session_id.in_(session_ids))
        .scalar()
        or 0
    )

    # Count records by status
    status_counts = (
        db.query(
            AttendanceRecordV3.status,
            func.count(AttendanceRecordV3.id).label("count"),
        )
        .filter(AttendanceRecordV3.session_id.in_(session_ids))
        .group_by(AttendanceRecordV3.status)
        .all()
    )

    # Initialize counts
    present_count = 0
    absent_count = 0
    late_count = 0

    # Aggregate counts by status
    for status_enum, count in status_counts:
        if status_enum == AttendanceStatusEnum.PRESENT:
            present_count = count
        elif status_enum == AttendanceStatusEnum.ABSENT:
            absent_count = count
        elif status_enum == AttendanceStatusEnum.LATE:
            late_count = count

    # Calculate total records
    total_records = present_count + absent_count + late_count

    # Calculate overall attendance percentage
    if total_records > 0:
        overall_attendance_percentage = round(
            ((present_count + late_count) / total_records) * 100, 2
        )
    else:
        overall_attendance_percentage = 0.0

    # Build response
    return SubjectReportResponse(
        subject_id=subject.id,
        subject_code=subject.code,
        subject_name=subject.name,
        total_sessions=total_sessions,
        total_students=total_students,
        total_records=total_records,
        present_count=present_count,
        absent_count=absent_count,
        late_count=late_count,
        overall_attendance_percentage=overall_attendance_percentage,
    )


@router.get("/defaulters/{subject_id}", status_code=status.HTTP_200_OK)
def get_defaulters_report(
    subject_id: int,
    min_percentage: float = Query(
        75.0, description="Minimum attendance percentage threshold"
    ),
    current_user: User = Depends(require_role([RoleEnum.ADMIN, RoleEnum.FACULTY])),
    db: Session = Depends(get_db),
):
    """
    Get list of students with attendance percentage below the minimum threshold for a subject.
    Admin can view defaulters for all faculty sessions.
    Faculty can only view defaulters for sessions they conducted.
    """
    # 1️⃣ Verify subject exists
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject not found",
        )

    # 2️⃣ Build base query for attendance records
    records_query = (
        db.query(AttendanceRecordV3)
        .join(
            AttendanceSessionV3,
            AttendanceRecordV3.session_id == AttendanceSessionV3.id,
        )
        .filter(AttendanceSessionV3.subject_id == subject_id)
    )

    # Enforce faculty access control: Faculty can only access their own sessions
    if current_user.role == RoleEnum.FACULTY:
        records_query = records_query.filter(
            AttendanceSessionV3.faculty_id == current_user.id
        )

    # 3️⃣ Fetch all matching records
    all_records = records_query.all()

    # 4️⃣ Handle empty records - check for unauthorized access
    if not all_records:
        if current_user.role == RoleEnum.FACULTY:
            # Check if subject has sessions by other faculty
            any_session = (
                db.query(AttendanceSessionV3)
                .filter(AttendanceSessionV3.subject_id == subject_id)
                .first()
            )
            if any_session:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only access subjects where you have created sessions",
                )
        # Return empty list if no records (valid response)
        return []

    # 5️⃣ Aggregate records by student using clean Python aggregation
    student_stats = {}
    for record in all_records:
        student_id = record.student_id
        if student_id not in student_stats:
            student_stats[student_id] = {
                "session_ids": set(),  # Use set for distinct session counting
                "present_count": 0,
                "absent_count": 0,
                "late_count": 0,
            }
        student_stats[student_id]["session_ids"].add(record.session_id)
        # Count statuses
        if record.status == AttendanceStatusEnum.PRESENT:
            student_stats[student_id]["present_count"] += 1
        elif record.status == AttendanceStatusEnum.ABSENT:
            student_stats[student_id]["absent_count"] += 1
        elif record.status == AttendanceStatusEnum.LATE:
            student_stats[student_id]["late_count"] += 1

    # 6️⃣ Calculate attendance percentages and filter defaulters
    defaulter_ids = []
    defaulter_data = {}

    for student_id, stats in student_stats.items():
        total_sessions = len(stats["session_ids"])
        present_count = stats["present_count"]
        absent_count = stats["absent_count"]
        late_count = stats["late_count"]

        # Calculate attendance percentage (handle division by zero)
        if total_sessions > 0:
            attendance_percentage = round(
                ((present_count + late_count) / total_sessions) * 100, 2
            )
        else:
            # If no sessions, skip (shouldn't happen, but handle gracefully)
            continue

        # Filter students below min_percentage
        if attendance_percentage < min_percentage:
            defaulter_ids.append(student_id)
            defaulter_data[student_id] = {
                "total_sessions": total_sessions,
                "present_count": present_count,
                "absent_count": absent_count,
                "late_count": late_count,
                "attendance_percentage": attendance_percentage,
            }

    # 7️⃣ Return empty list if no defaulters found
    if not defaulter_ids:
        return []

    # 8️⃣ Enrich with Student and User data in single query
    students = (
        db.query(Student)
        .join(User, Student.user_id == User.id)
        .filter(Student.id.in_(defaulter_ids))
        .all()
    )

    # Create mapping for student/user data
    student_info_map = {
        student.id: {
            "student_code": student.student_id,  # External identifier
            "full_name": student.user.full_name,
        }
        for student in students
    }

    # 9️⃣ Build response list
    result = []
    for student_id in defaulter_ids:
        if student_id in student_info_map:
            result.append(
                DefaulterReportResponse(
                    student_id=student_id,  # Internal database ID
                    student_code=student_info_map[student_id]["student_code"],
                    full_name=student_info_map[student_id]["full_name"],
                    total_sessions=defaulter_data[student_id]["total_sessions"],
                    present_count=defaulter_data[student_id]["present_count"],
                    absent_count=defaulter_data[student_id]["absent_count"],
                    late_count=defaulter_data[student_id]["late_count"],
                    attendance_percentage=defaulter_data[student_id][
                        "attendance_percentage"
                    ],
                )
            )

    return result


"""
Exports raw attendance records as CSV.
This endpoint provides row-level data for audits and manual analysis.
For aggregated reports and summaries, use:
- GET /api/v3/reports/session/{session_id}/summary
"""


@router.get("/export/csv", status_code=status.HTTP_200_OK)
def export_attendance_csv(
    subject_id: int = Query(..., description="Subject ID (required)"),
    student_id: Optional[int] = Query(None, description="Student ID (optional filter)"),
    start_date: Optional[date] = Query(
        None, description="Start date filter (YYYY-MM-DD)"
    ),
    end_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    current_user: User = Depends(require_role([RoleEnum.ADMIN, RoleEnum.FACULTY])),
    db: Session = Depends(get_db),
):
    """
    Export attendance report data in CSV format.
    
    Admin can export data for all faculty sessions.
    Faculty can only export data for sessions they conducted.
    
    Example curl command:
    curl -X GET "http://localhost:8000/api/v3/reports/export/csv?subject_id=1&student_id=1&start_date=2024-01-01&end_date=2024-12-31" \\
      -H "Authorization: Bearer <token>" \\
      -o attendance_report.csv
    """
    # 1️⃣ Validate subject exists BEFORE querying attendance
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject not found",
        )

    # 2️⃣ Get attendance data using service with faculty access control
    faculty_id = None
    if current_user.role == RoleEnum.FACULTY:
        faculty_id = current_user.id

    records = get_attendance_data_for_csv(
        db=db,
        subject_id=subject_id,
        student_id=student_id,
        start_date=start_date,
        end_date=end_date,
        faculty_id=faculty_id,
    )

    # 3️⃣ Generate CSV content
    csv_content = generate_csv_content(records)

    # 4️⃣ Return CSV response
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="attendance_report.csv"'},
    )


# -------------------------------------------------------------------
# ADMIN GLOBAL REPORT (Phase 6.4)
# -------------------------------------------------------------------
@router.get(
    "/admin/global",
    response_model=GlobalAttendanceReportResponse,
    status_code=status.HTTP_200_OK,
)
def get_global_attendance_report_v3(
    start_date: Optional[date] = Query(
        None, description="Start date filter (YYYY-MM-DD)"
    ),
    end_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    subject_id: Optional[int] = Query(None, description="Optional subject filter"),
    faculty_id: Optional[int] = Query(None, description="Optional faculty filter"),
    limit_subjects: int = Query(
        20, description="Limit for subject breakdown", ge=1, le=100
    ),
    limit_faculty: int = Query(
        20, description="Limit for faculty breakdown", ge=1, le=100
    ),
    current_user: User = Depends(require_role([RoleEnum.ADMIN])),
    db: Session = Depends(get_db),
):
    """
    Get global attendance report with aggregated statistics (ADMIN only).

    Returns high-level aggregated data across the system:
    - Summary: total sessions, unique students, subjects, faculty
    - Attendance overview: aggregated counts and marked_percentage
    - Subject breakdown: top subjects by record count (limited)
    - Faculty breakdown: top faculty by record count (limited)

    All aggregations are done in SQL using GROUP BY + CASE statements.
    No per-student data is returned.

    Filters:
    - start_date: Filter sessions from this date onwards
    - end_date: Filter sessions up to this date
    - subject_id: Filter to a specific subject
    - faculty_id: Filter to a specific faculty
    - limit_subjects: Maximum subjects in breakdown (default 20, max 100)
    - limit_faculty: Maximum faculty in breakdown (default 20, max 100)

    marked_percentage calculation:
    ((present_count + absent_count + late_count) / total_records) * 100

    Returns zeros and empty arrays when no data matches filters (no 404).
    """
    return get_global_attendance_report(
        db=db,
        start_date=start_date,
        end_date=end_date,
        subject_id=subject_id,
        faculty_id=faculty_id,
        limit_subjects=limit_subjects,
        limit_faculty=limit_faculty,
    )


# -------------------------------------------------------------------
# STUDENT-WISE ATTENDANCE REPORT (Phase 6.5)
# -------------------------------------------------------------------
@router.get(
    "/student/{student_id}",
    response_model=StudentAttendanceReportResponse,
    status_code=status.HTTP_200_OK,
)
def get_student_attendance_report_v3(
    student_id: int,
    start_date: Optional[date] = Query(
        None, description="Start date filter (YYYY-MM-DD)"
    ),
    end_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    subject_id: Optional[int] = Query(None, description="Optional subject filter"),
    limit_subjects: Optional[int] = Query(
        20, description="Limit for subject breakdown", ge=1, le=100
    ),
    current_user: User = Depends(require_role([RoleEnum.ADMIN, RoleEnum.STUDENT])),
    db: Session = Depends(get_db),
):
    """
    Get student-wise attendance report with aggregated statistics.

    Returns student information, overall attendance summary, and per-subject breakdown.
    All aggregations are done in SQL using GROUP BY + CASE statements.

    Authorization:
    - ADMIN: Can access any student's report
    - STUDENT: Can only access their own report (student_id must match current_user.student_profile.id)
    - FACULTY: Not allowed

    Filters:
    - start_date: Filter sessions from this date onwards
    - end_date: Filter sessions up to this date
    - subject_id: Filter to a specific subject
    - limit_subjects: Maximum subjects in breakdown (default 20, max 100)

    attendance_percentage calculation:
    ((present_count + absent_count + late_count) / total_sessions) * 100

    Late counts as attended for percentage calculation.

    Returns 404 if student not found.
    Returns 403 if STUDENT tries to access another student's report.
    Returns 400 if start_date > end_date.
    """
    # 1. STUDENT role authorization check
    if current_user.role == RoleEnum.STUDENT:
        # Check if student_profile exists
        if current_user.student_profile is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Student profile not found",
            )
        # Check if accessing own student_id
        if current_user.student_profile.id != student_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your own attendance report",
            )

    # 2. Date range validation
    if start_date and end_date:
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date must be less than or equal to end_date",
            )

    # 3. Call service function
    return get_student_attendance_report(
        db=db,
        student_id=student_id,
        start_date=start_date,
        end_date=end_date,
        subject_id=subject_id,
        limit_subjects=limit_subjects,
    )


# -------------------------------------------------------------------
# FACULTY-SCOPED STUDENT ATTENDANCE REPORT (Phase 6.6)
# -------------------------------------------------------------------
@router.get(
    "/faculty/student/{student_id}",
    response_model=FacultyStudentAttendanceReportResponse,
    status_code=status.HTTP_200_OK,
)
def get_faculty_student_attendance_report_v3(
    student_id: int,
    start_date: Optional[date] = Query(
        None, description="Start date filter (YYYY-MM-DD)"
    ),
    end_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    subject_id: Optional[int] = Query(None, description="Optional subject filter"),
    limit_subjects: int = Query(
        20, description="Limit for subject breakdown", ge=1, le=100
    ),
    current_user: User = Depends(require_role([RoleEnum.ADMIN, RoleEnum.FACULTY])),
    db: Session = Depends(get_db),
):
    """
    Get faculty-scoped student attendance report with aggregated statistics.

    Returns student information, overall attendance summary, and per-subject breakdown.
    All aggregations are done in SQL using GROUP BY + CASE statements.

    Authorization:
    - ADMIN: Global visibility across all faculty (unrestricted access to all faculty sessions)
    - FACULTY: Strictly scoped to their own sessions (AttendanceSessionV3.faculty_id == current_user.id)
    - STUDENT: Not allowed (403 Forbidden)

    Filters:
    - start_date: Filter sessions from this date onwards
    - end_date: Filter sessions up to this date
    - subject_id: Filter to a specific subject
    - limit_subjects: Maximum subjects in breakdown (default 20, max 100)

    attendance_percentage calculation:
    ((present_count + absent_count + late_count) / total_sessions) * 100

    attendance_percentage represents attendance coverage/participation completeness,
    not attendance quality. Late counts as attended for percentage calculation.

    Edge cases:
    - Non-existent student → 404 Not Found
    - Invalid date range (start_date > end_date) → 400 Bad Request
    - STUDENT role → 403 Forbidden (router-level authorization)
    - Faculty never taught student → 200 OK with zeros (intentional usability decision)
    - Empty results → 200 OK with empty arrays (not 404)
    """
    # 1. Date range validation
    if start_date and end_date:
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date must be less than or equal to end_date",
            )

    # 2. Determine faculty_id based on role
    # ADMIN: faculty_id=None means unrestricted access (all faculty sessions)
    # FACULTY: faculty_id=current_user.id means scoped to their own sessions
    faculty_id = None
    if current_user.role == RoleEnum.FACULTY:
        faculty_id = current_user.id

    # 3. Call service function
    return get_faculty_student_attendance_report(
        db=db,
        student_id=student_id,
        faculty_id=faculty_id,
        start_date=start_date,
        end_date=end_date,
        subject_id=subject_id,
        limit_subjects=limit_subjects,
    )
