"""
Phase 3.2 Attendance management routes.
Handles attendance sessions using AttendanceSessionV3 model.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from typing import List
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
    SessionStudentAttendanceV3Response,
)
from app.routers.auth import require_role, RoleEnum

router = APIRouter()


# -------------------------------------------------------------------
# CREATE ATTENDANCE SESSION
# -------------------------------------------------------------------
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
    Create a new attendance session.
    Only FACULTY or ADMIN can create sessions.
    """

    # Verify subject exists
    subject = db.query(Subject).filter(Subject.id == session_data.subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    # Prevent duplicate session for same subject + faculty + date
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
            status_code=400,
            detail="Attendance session already exists for this subject and date",
        )

    session = AttendanceSessionV3(
        subject_id=session_data.subject_id,
        faculty_id=current_user.id,
        session_date=session_data.session_date,
        is_locked=False,
    )

    try:
        db.add(session)
        db.commit()
        db.refresh(session)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Failed to create attendance session",
        )

    return session


# -------------------------------------------------------------------
# CREATE / UPDATE ATTENDANCE RECORD
# -------------------------------------------------------------------
@router.post(
    "/sessions/{session_id}/records",
    response_model=AttendanceRecordV3Response,
    status_code=status.HTTP_201_CREATED,
)
def create_attendance_record_v3(
    session_id: int,
    record_data: AttendanceRecordV3Create,
    current_user: User = Depends(require_role([RoleEnum.FACULTY])),
    db: Session = Depends(get_db),
):
    """
    Mark or update attendance for a student.
    Rules:
    - ONLY FACULTY can mark attendance
    - Faculty can mark ONLY their own sessions
    - Locked sessions cannot be modified
    """

    # ---- Fetch session ----
    session = (
        db.query(AttendanceSessionV3)
        .filter(AttendanceSessionV3.id == session_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Attendance session not found")

    # ---- Ownership enforcement ----
    if session.faculty_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to mark attendance for this session",
        )

    # ---- Lock enforcement ----
    if session.is_locked:
        raise HTTPException(
            status_code=409,
            detail="Attendance session is locked and cannot be modified",
        )

    # ---- Verify student exists ----
    student = db.query(Student).filter(Student.id == record_data.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # ---- Verify student enrollment ----
    enrollment = (
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
    if not enrollment:
        raise HTTPException(
            status_code=400,
            detail="Student is not enrolled for this subject",
        )

    # ---- Validate attendance status ----
    try:
        status_enum = AttendanceStatusEnum(record_data.status.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Allowed: {[s.value for s in AttendanceStatusEnum]}",
        )

    # ---- Check existing record ----
    existing = (
        db.query(AttendanceRecordV3)
        .filter(
            AttendanceRecordV3.session_id == session_id,
            AttendanceRecordV3.student_id == record_data.student_id,
        )
        .first()
    )

    try:
        if existing:
            # Update existing record
            existing.status = status_enum
            existing.marked_by = current_user.id
            existing.marked_at = datetime.utcnow()
        else:
            # Create new record
            new_record = AttendanceRecordV3(
                session_id=session_id,
                student_id=record_data.student_id,
                status=status_enum,
                marked_by=current_user.id,
                marked_at=datetime.utcnow(),
            )
            db.add(new_record)

        db.commit()

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Attendance record operation failed",
        )

    return existing if existing else new_record


@router.post(
    "/sessions/{session_id}/lock",
    response_model=AttendanceSessionV3Response,
    operation_id="lock_attendance_session_v3",
)
def lock_attendance_session_v3(
    session_id: int,
    current_user: User = Depends(require_role([RoleEnum.FACULTY, RoleEnum.ADMIN])),
    db: Session = Depends(get_db),
):
    session = (
        db.query(AttendanceSessionV3)
        .filter(AttendanceSessionV3.id == session_id)
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="Attendance session not found")

    if session.is_locked:
        raise HTTPException(status_code=409, detail="Session already locked")

    if current_user.role == RoleEnum.FACULTY and session.faculty_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    session.is_locked = True
    session.locked_at = datetime.utcnow()

    db.commit()
    db.refresh(session)
    return session


# -------------------------------------------------------------------
# LIST ATTENDANCE SESSIONS
# -------------------------------------------------------------------
@router.get(
    "/sessions",
    response_model=List[AttendanceSessionV3Response],
    status_code=status.HTTP_200_OK,
)
def list_attendance_sessions_v3(
    current_user: User = Depends(require_role([RoleEnum.FACULTY, RoleEnum.ADMIN])),
    db: Session = Depends(get_db),
):
    """
    List attendance sessions.
    FACULTY can only see their own sessions.
    ADMIN can see all sessions.
    """
    query = db.query(AttendanceSessionV3)

    # Filter by faculty_id if user is FACULTY
    if current_user.role == RoleEnum.FACULTY:
        query = query.filter(AttendanceSessionV3.faculty_id == current_user.id)

    # Order by session_date DESC, then created_at DESC
    sessions = query.order_by(
        AttendanceSessionV3.session_date.desc(),
        AttendanceSessionV3.created_at.desc(),
    ).all()

    return sessions


# -------------------------------------------------------------------
# GET SESSION STUDENTS WITH ATTENDANCE
# -------------------------------------------------------------------
@router.get(
    "/sessions/{session_id}/students",
    response_model=List[SessionStudentAttendanceV3Response],
    status_code=status.HTTP_200_OK,
)
def get_session_students_v3(
    session_id: int,
    current_user: User = Depends(require_role([RoleEnum.FACULTY, RoleEnum.ADMIN])),
    db: Session = Depends(get_db),
):
    """
    Get all students enrolled in the session's subject with their attendance status.
    FACULTY can only access their own sessions.
    ADMIN can access any session.
    """
    # Fetch session
    session = (
        db.query(AttendanceSessionV3)
        .filter(AttendanceSessionV3.id == session_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Attendance session not found")

    # Authorization check
    if current_user.role == RoleEnum.FACULTY and session.faculty_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to access this session",
        )

    # Query students enrolled in the session's subject
    # Join: Student -> ClassEnrollment -> ClassSubject -> User
    # Left join: AttendanceRecordV3
    query = (
        db.query(
            Student.id.label("student_id"),
            Student.student_id.label("student_code"),
            User.full_name.label("student_name"),
            AttendanceRecordV3.status.label("attendance_status"),
            AttendanceRecordV3.marked_at.label("marked_at"),
        )
        .join(ClassEnrollment, ClassEnrollment.student_id == Student.id)
        .join(ClassSubject, ClassSubject.class_id == ClassEnrollment.class_id)
        .join(User, User.id == Student.user_id)
        .outerjoin(
            AttendanceRecordV3,
            and_(
                AttendanceRecordV3.student_id == Student.id,
                AttendanceRecordV3.session_id == session_id,
            ),
        )
        .filter(ClassSubject.subject_id == session.subject_id)
        .distinct()
        .order_by(User.full_name.asc())
    )

    results = query.all()

    # Map results to response schema
    students = []
    for row in results:
        students.append(
            SessionStudentAttendanceV3Response(
                student_id=row.student_id,
                student_code=row.student_code,
                student_name=row.student_name,
                attendance_status=row.attendance_status,
                marked_at=row.marked_at,
            )
        )

    return students
