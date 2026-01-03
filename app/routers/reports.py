"""
Phase 3.3 Reporting routes.
Provides read-only reporting endpoints for Attendance V3 data.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from datetime import date
from typing import Optional
from app.models import User, Student, AttendanceRecordV3, AttendanceSessionV3
from app.models import RoleEnum
from sqlalchemy import func, distinct
from sqlalchemy.sql.functions import user
from app.database import get_db
from app.models import (
    User,
    AttendanceSessionV3,
    AttendanceRecordV3,
    AttendanceStatusEnum,
    Subject,
    Student,
    RoleEnum,
)
from app.routers.auth import require_role
from app.services.reports_service import (
    get_attendance_data_for_csv,
    generate_csv_content,
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


@router.get("/student/{student_id}", status_code=status.HTTP_200_OK)
def get_student_report(
    student_id: int,
    subject_id: Optional[int] = Query(None, description="Optional subject filter"),
    current_user: User = Depends(require_role([RoleEnum.ADMIN, RoleEnum.FACULTY])),
    db: Session = Depends(get_db),
):
    """
    Get simple attendance summary for a student.
    Admin can access any student.
    Faculty can only access students from their own sessions.
    """

    # 1️⃣ Fetch Student + linked User
    student = (
        db.query(Student)
        .join(User, Student.user_id == User.id)
        .filter(Student.id == student_id)
        .first()
    )

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    user = student.user  # relationship-backed, clean, explicit

    # 2️⃣ Build base attendance query
    records_query = (
        db.query(AttendanceRecordV3)
        .join(
            AttendanceSessionV3,
            AttendanceRecordV3.session_id == AttendanceSessionV3.id,
        )
        .filter(AttendanceRecordV3.student_id == student.id)
    )

    # 3️⃣ Optional subject filter
    if subject_id:
        records_query = records_query.filter(
            AttendanceSessionV3.subject_id == subject_id
        )

    # 4️⃣ Faculty access restriction
    if current_user.role == RoleEnum.FACULTY:
        records_query = records_query.filter(
            AttendanceSessionV3.faculty_id == current_user.id
        )

    all_records = records_query.all()

    # 5️⃣ Handle empty records safely
    if not all_records:
        if current_user.role == RoleEnum.FACULTY:
            any_record = (
                db.query(AttendanceRecordV3)
                .filter(AttendanceRecordV3.student_id == student.id)
                .first()
            )
            if any_record:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only access students from your own sessions",
                )

        return StudentReportResponse(
            student_id=student.id,
            student_code=student.student_id,
            full_name=user.full_name,
            total_sessions=0,
            present_count=0,
            absent_count=0,
            late_count=0,
            attendance_percentage=0.0,
        )

    # 6️⃣ Aggregate stats
    session_ids = {r.session_id for r in all_records}
    total_sessions = len(session_ids)

    present_count = sum(r.status == AttendanceStatusEnum.PRESENT for r in all_records)
    absent_count = sum(r.status == AttendanceStatusEnum.ABSENT for r in all_records)
    late_count = sum(r.status == AttendanceStatusEnum.LATE for r in all_records)

    attendance_percentage = round(
        ((present_count + late_count) / total_sessions) * 100, 2
    )

    # 7️⃣ Final response
    return StudentReportResponse(
        student_id=student.id,
        student_code=student.student_id,
        full_name=user.full_name,
        total_sessions=total_sessions,
        present_count=present_count,
        absent_count=absent_count,
        late_count=late_count,
        attendance_percentage=attendance_percentage,
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
