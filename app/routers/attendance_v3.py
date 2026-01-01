"""
Phase 3.2 Attendance management routes.
Handles attendance sessions using AttendanceSessionV3 model.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from datetime import date, datetime
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
)
from app.schemas import (
    AttendanceSessionV3Create,
    AttendanceSessionV3Response,
    AttendanceRecordV3Create,
    AttendanceRecordV3Response,
)
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


@router.post(
    "/sessions/{session_id}/records",
    response_model=AttendanceRecordV3Response,
    status_code=status.HTTP_201_CREATED,
)
def create_attendance_record_v3(
    session_id: int,
    record_data: AttendanceRecordV3Create,
    current_user: User = Depends(require_role([RoleEnum.FACULTY, RoleEnum.ADMIN])),
    db: Session = Depends(get_db),
):
    """
    Create or update attendance record for a student in a session (Phase 3.2).
    Only works if session is not locked.
    Faculty can only mark attendance for their own sessions.
    """
    # Get session and verify it exists
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

    # Check if session is locked
    if session.is_locked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify attendance records in a locked session",
        )

    # Verify faculty ownership (FACULTY can only mark their own sessions)
    if current_user.role == RoleEnum.FACULTY:
        if session.faculty_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only mark attendance for your own sessions",
            )

    # Verify student exists
    student = db.query(Student).filter(Student.id == record_data.student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Student not found"
        )

    # Validate student enrollment: student must be enrolled in a class that includes the subject
    enrollment_check = (
        db.query(ClassEnrollment)
        .join(ClassSubject, ClassSubject.class_id == ClassEnrollment.class_id)
        .filter(
            and_(
                ClassEnrollment.student_id == record_data.student_id,
                ClassSubject.subject_id == session.subject_id,
            )
        )
        .first()
    )

    if not enrollment_check:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student is not enrolled in any class that includes this subject",
        )

    # Validate status enum
    try:
        status_enum = AttendanceStatusEnum(record_data.status.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {[s.value for s in AttendanceStatusEnum]}",
        )

    # Check if record already exists
    existing = (
        db.query(AttendanceRecordV3)
        .filter(
            AttendanceRecordV3.session_id == session_id,
            AttendanceRecordV3.student_id == record_data.student_id,
        )
        .first()
    )

    # 🚨 Lock enforcement (MUST apply to update too)
    if session.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Attendance session is locked",
        )

    if existing:
        # Explicit update
        existing.status = status_enum
        existing.marked_by = current_user.id
        existing.marked_at = datetime.utcnow()

        # Update attendance record
        try:
            db.commit()
            db.refresh(existing)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update attendance record",
            )

        return existing

    # Create new record
    new_record = AttendanceRecordV3(
        session_id=session_id,
        student_id=record_data.student_id,
        status=status_enum,
        marked_by=current_user.id,
        marked_at=datetime.utcnow(),
    )

    db.add(new_record)
    try:
        db.commit()
        db.refresh(new_record)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Attendance record already exists",
        )

    return new_record
