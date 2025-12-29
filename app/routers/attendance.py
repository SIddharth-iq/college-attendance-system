"""
Attendance management routes.
Handles attendance sessions and records.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import Integer, and_, func, extract
from typing import List, Optional
from datetime import date, datetime
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.models import (
    User,
    AttendanceSession,
    AttendanceRecord,
    Student,
    ClassSubject,
    FacultyAssignment,
    ClassEnrollment,
    Class,
    Subject,
)
from app.schemas import (
    AttendanceSessionCreate,
    AttendanceSessionResponse,
    AttendanceRecordCreate,
    AttendanceRecordResponse,
    MonthlyAttendanceReport,
)
from app.routers.auth import get_current_user, require_role, RoleEnum

router = APIRouter()


@router.post(
    "/sessions",
    response_model=AttendanceSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_attendance_session(
    session_data: AttendanceSessionCreate,
    current_user: User = Depends(require_role([RoleEnum.FACULTY, RoleEnum.ADMIN])),
    db: Session = Depends(get_db),
):
    """
    Create a new attendance session.
    Only faculty assigned to the class-subject can create sessions.
    """
    # Verify faculty is assigned to this class-subject
    if current_user.role == RoleEnum.FACULTY:
        assignment = (
            db.query(FacultyAssignment)
            .filter(
                and_(
                    FacultyAssignment.faculty_id == current_user.id,
                    FacultyAssignment.class_subject_id == session_data.class_subject_id,
                )
            )
            .first()
        )
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not assigned to teach this class-subject combination",
            )

    # Check if session already exists for this class-subject on this date
    existing = (
        db.query(AttendanceSession)
        .filter(
            and_(
                AttendanceSession.class_subject_id == session_data.class_subject_id,
                AttendanceSession.session_date == session_data.session_date,
            )
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Attendance session already exists for this class-subject on this date",
        )

    # Create session
    db_session = AttendanceSession(
        class_subject_id=session_data.class_subject_id,
        session_date=session_data.session_date,
        start_time=datetime.now(),
        notes=session_data.notes,
        is_locked=False,
    )
    try:
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate or invalid operation",
        )
    return db_session


@router.post(
    "/sessions/{session_id}/records",
    response_model=AttendanceRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_attendance_record(
    session_id: int,
    record_data: AttendanceRecordCreate,
    current_user: User = Depends(require_role([RoleEnum.FACULTY, RoleEnum.ADMIN])),
    db: Session = Depends(get_db),
):
    """
    Create or update attendance record for a student in a session.
    Only works if session is not locked.
    """
    # Get session and verify it exists and is not locked
    session = (
        db.query(AttendanceSession).filter(AttendanceSession.id == session_id).first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Attendance session not found"
        )

    if session.is_locked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify attendance records in a locked session",
        )

    # Verify faculty is assigned (if faculty)
    if current_user.role == RoleEnum.FACULTY:
        assignment = (
            db.query(FacultyAssignment)
            .filter(
                and_(
                    FacultyAssignment.faculty_id == current_user.id,
                    FacultyAssignment.class_subject_id == session.class_subject_id,
                )
            )
            .first()
        )
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )

    # Check if record already exists
    existing = (
        db.query(AttendanceRecord)
        .filter(
            and_(
                AttendanceRecord.session_id == session_id,
                AttendanceRecord.student_id == record_data.student_id,
            )
        )
        .first()
    )

    if existing:
        # Update existing record
        existing.is_present = record_data.is_present
        existing.marked_by = current_user.id
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Create new record
        record = AttendanceRecord(
            session_id=session_id,
            student_id=record_data.student_id,
            is_present=record_data.is_present,
            marked_by=current_user.id,
        )
        try:
            db.add(record)
            db.commit()
            db.refresh(record)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Duplicate or invalid operation",
            )
    return record


@router.post("/sessions/{session_id}/lock", response_model=AttendanceSessionResponse)
def lock_attendance_session(
    session_id: int,
    current_user: User = Depends(require_role([RoleEnum.FACULTY, RoleEnum.ADMIN])),
    db: Session = Depends(get_db),
):
    """
    Lock an attendance session to prevent further modifications.
    Once locked, no records can be added or modified.
    """
    session = (
        db.query(AttendanceSession).filter(AttendanceSession.id == session_id).first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    if session.is_locked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Session is already locked"
        )

    # Verify faculty is assigned (if faculty)
    if current_user.role == RoleEnum.FACULTY:
        assignment = (
            db.query(FacultyAssignment)
            .filter(
                and_(
                    FacultyAssignment.faculty_id == current_user.id,
                    FacultyAssignment.class_subject_id == session.class_subject_id,
                )
            )
            .first()
        )
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )

    # Lock the session
    session.is_locked = True
    session.end_time = datetime.now()
    session.locked_by = current_user.id
    try:
        db.commit()
        db.refresh(session)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate or invalid operation",
        )
    return session


@router.get(
    "/sessions/{session_id}/records", response_model=List[AttendanceRecordResponse]
)
def get_session_records(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all attendance records for a session.
    Students can only view if they're enrolled in the class.
    """
    session = (
        db.query(AttendanceSession).filter(AttendanceSession.id == session_id).first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    # Students can only view their own records
    if current_user.role == RoleEnum.STUDENT:
        student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student profile not found",
            )

        records = (
            db.query(AttendanceRecord)
            .filter(
                and_(
                    AttendanceRecord.session_id == session_id,
                    AttendanceRecord.student_id == student.id,
                )
            )
            .all()
        )
        return records

    # Faculty and Admin can view all records
    records = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.session_id == session_id)
        .all()
    )
    return records


@router.get("/reports/monthly", response_model=List[MonthlyAttendanceReport])
def get_monthly_attendance_report(
    month: int,
    year: int,
    class_subject_id: Optional[int] = None,
    student_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get monthly attendance percentage report per student.
    Calculates attendance percentage for given month/year.
    """
    # Build base query for attendance records in the month
    query = (
        db.query(
            Student.id.label("student_id"),
            User.full_name.label("student_name"),
            Student.student_id.label("student_code"),
            Class.code.label("class_code"),
            Subject.code.label("subject_code"),
            Subject.name.label("subject_name"),
            extract("month", AttendanceSession.session_date).label("month"),
            extract("year", AttendanceSession.session_date).label("year"),
            func.count(AttendanceRecord.id).label("total_sessions"),
            func.sum(func.cast(AttendanceRecord.is_present, Integer)).label(
                "present_count"
            ),
            func.count(AttendanceRecord.id)
            - func.sum(func.cast(AttendanceRecord.is_present, Integer)).label(
                "absent_count"
            ),
        )
        .join(AttendanceRecord, AttendanceRecord.student_id == Student.id)
        .join(AttendanceSession, AttendanceSession.id == AttendanceRecord.session_id)
        .join(ClassSubject, ClassSubject.id == AttendanceSession.class_subject_id)
        .join(Class, Class.id == ClassSubject.class_id)
        .join(Subject, Subject.id == ClassSubject.subject_id)
        .join(User, User.id == Student.user_id)
        .filter(
            and_(
                extract("month", AttendanceSession.session_date) == month,
                extract("year", AttendanceSession.session_date) == year,
                AttendanceSession.is_locked == True,  # Only count locked sessions
            )
        )
    )

    # Apply filters
    if class_subject_id:
        query = query.filter(ClassSubject.id == class_subject_id)
    if student_id:
        query = query.filter(Student.id == student_id)

    # Students can only view their own reports
    if current_user.role == RoleEnum.STUDENT:
        student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if student:
            query = query.filter(Student.id == student.id)
        else:
            return []

    # Group by student and class-subject
    results = query.group_by(Student.id, Class.code, Subject.id).all()

    # Format results
    reports = []
    for row in results:
        total = row.total_sessions or 0
        present = row.present_count or 0
        percentage = (present / total * 100) if total > 0 else 0.0

        reports.append(
            MonthlyAttendanceReport(
                student_id=row.student_id,
                student_name=row.student_name,
                student_code=row.student_code,
                class_code=row.class_code,
                subject_code=row.subject_code,
                subject_name=row.subject_name,
                month=month,
                year=year,
                total_sessions=total,
                present_count=int(present),
                absent_count=row.absent_count or 0,
                attendance_percentage=round(percentage, 2),
            )
        )

    return reports
