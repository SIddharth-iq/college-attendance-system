"""
Phase 3.2 Attendance management routes.
Handles attendance sessions using AttendanceSessionV3 model.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from datetime import date
from app.database import get_db
from app.models import User, AttendanceSessionV3, Subject
from app.schemas import AttendanceSessionV3Create, AttendanceSessionV3Response
from app.routers.auth import require_role, RoleEnum

router = APIRouter()


@router.post(
    "/sessions",
    response_model=AttendanceSessionV3Response,
    status_code=status.HTTP_201_CREATED,
)
def create_attendance_session_v3(
    session_data: AttendanceSessionV3Create,
    current_user: User = Depends(require_role([RoleEnum.FACULTY, RoleEnum.ADMIN])),
    db: Session = Depends(get_db),
):
    """
    Create a new attendance session (Phase 3.2).
    Only FACULTY and ADMIN can create sessions.
    faculty_id is automatically set from current_user.
    """
    # Verify subject exists
    subject = db.query(Subject).filter(Subject.id == session_data.subject_id).first()
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found"
        )

    # Check if session already exists for this subject + faculty + date
    existing = (
        db.query(AttendanceSessionV3)
        .filter(
            and_(
                AttendanceSessionV3.subject_id == session_data.subject_id,
                AttendanceSessionV3.faculty_id == current_user.id,
                AttendanceSessionV3.session_date == session_data.session_date,
            )
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Attendance session already exists for this subject, faculty, and date",
        )

    # Create session
    db_session = AttendanceSessionV3(
        subject_id=session_data.subject_id,
        faculty_id=current_user.id,
        session_date=session_data.session_date,
        is_locked=False,
    )
    try:
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create attendance session. Duplicate entry or constraint violation.",
        )

    return db_session

