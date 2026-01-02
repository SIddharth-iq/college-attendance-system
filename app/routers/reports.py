"""
Phase 3.3 Reporting routes.
Provides read-only reporting endpoints for Attendance V3 data.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from datetime import date
from app.database import get_db
from app.models import (
    User,
    AttendanceSessionV3,
    AttendanceRecordV3,
    AttendanceStatusEnum,
    Subject,
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

