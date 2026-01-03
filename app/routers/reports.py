"""
Phase 3.3 Reporting routes.
Provides read-only reporting endpoints for Attendance V3 data.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from datetime import date
from typing import Optional
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
    Admin can access any student. Faculty can only access students from their own sessions.
    """
    # Verify student exists
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )

    # Get student's user details for full_name
    user = db.query(User).filter(User.id == student.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found for this student",
        )

    # Build base query for records
    records_query = (
        db.query(AttendanceRecordV3)
        .join(
            AttendanceSessionV3, AttendanceRecordV3.session_id == AttendanceSessionV3.id
        )
        .filter(AttendanceRecordV3.student_id == student_id)
    )

    # Apply subject filter if provided
    if subject_id:
        records_query = records_query.filter(
            AttendanceSessionV3.subject_id == subject_id
        )

    # Enforce faculty access control: Faculty can only access their own sessions
    if current_user.role == RoleEnum.FACULTY:
        records_query = records_query.filter(
            AttendanceSessionV3.faculty_id == current_user.id
        )

    # Get all records for this student (with filters applied)
    all_records = records_query.all()

    # If no records found, check if faculty is trying to access unauthorized student
    if not all_records:
        if current_user.role == RoleEnum.FACULTY:
            # Check if student has records but not from this faculty's sessions
            any_record = (
                db.query(AttendanceRecordV3)
                .filter(AttendanceRecordV3.student_id == student_id)
                .first()
            )
            if any_record:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only access students from your own sessions",
                )
        # Return empty summary if no records
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

    # Count total distinct sessions
    session_ids = list(set([r.session_id for r in all_records]))
    total_sessions = len(session_ids)

    # Count records by status
    present_count = sum(
        1 for r in all_records if r.status == AttendanceStatusEnum.PRESENT
    )
    absent_count = sum(
        1 for r in all_records if r.status == AttendanceStatusEnum.ABSENT
    )
    late_count = sum(1 for r in all_records if r.status == AttendanceStatusEnum.LATE)

    # Calculate attendance percentage: (present_count + late_count) / total_sessions * 100
    if total_sessions > 0:
        attendance_percentage = round(
            ((present_count + late_count) / total_sessions) * 100, 2
        )
    else:
        attendance_percentage = 0.0

    # Build response
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
