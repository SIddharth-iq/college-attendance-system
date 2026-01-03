"""
Reports service module for CSV export functionality.
Contains business logic for generating CSV reports.
"""

import csv
import io
from datetime import date
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models import (
    AttendanceRecordV3,
    AttendanceSessionV3,
    Student,
    User,
    Subject,
    AttendanceStatusEnum,
)


def get_attendance_data_for_csv(
    db: Session,
    subject_id: int,
    student_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    faculty_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Query attendance records with filters for CSV export.
    
    Args:
        db: Database session
        subject_id: Subject ID (required)
        student_id: Optional student ID filter
        start_date: Optional start date filter
        end_date: Optional end date filter
        faculty_id: Optional faculty ID filter (for access control)
    
    Returns a list of dictionaries with attendance data including:
    - student_id, student_code, student_name
    - subject_id, subject_name
    - session_id, session_date
    - attendance_status
    """
    # Build query with joins
    query = (
        db.query(
            AttendanceRecordV3,
            Student,
            User,
            Subject,
            AttendanceSessionV3,
        )
        .join(AttendanceSessionV3, AttendanceRecordV3.session_id == AttendanceSessionV3.id)
        .join(Student, AttendanceRecordV3.student_id == Student.id)
        .join(User, Student.user_id == User.id)
        .join(Subject, AttendanceSessionV3.subject_id == Subject.id)
        .filter(AttendanceSessionV3.subject_id == subject_id)
    )

    # Apply optional filters
    if student_id is not None:
        query = query.filter(AttendanceRecordV3.student_id == student_id)

    if start_date is not None:
        query = query.filter(AttendanceSessionV3.session_date >= start_date)

    if end_date is not None:
        query = query.filter(AttendanceSessionV3.session_date <= end_date)

    # Apply faculty access control filter
    if faculty_id is not None:
        query = query.filter(AttendanceSessionV3.faculty_id == faculty_id)

    # Order by session_date and student_id for consistent output
    query = query.order_by(
        AttendanceSessionV3.session_date,
        Student.id,
    )

    # Execute query
    results = query.all()

    # Transform results into list of dictionaries
    records = []
    for record_v3, student, user, subject, session in results:
        records.append({
            "student_id": student.id,
            "student_code": student.student_id,
            "student_name": user.full_name,
            "subject_id": subject.id,
            "subject_name": subject.name,
            "session_id": session.id,
            "session_date": session.session_date,
            "attendance_status": record_v3.status.value.upper(),  # PRESENT, ABSENT, LATE
        })

    return records


def generate_csv_content(records: List[Dict[str, Any]]) -> str:
    """
    Generate CSV string from attendance records.
    
    Always includes header row, even if records list is empty.
    
    CSV columns (in order):
    - student_id
    - student_code
    - student_name
    - subject_id
    - subject_name
    - session_id
    - session_date
    - attendance_status
    """
    # Define CSV columns in the required order
    fieldnames = [
        "student_id",
        "student_code",
        "student_name",
        "subject_id",
        "subject_name",
        "session_id",
        "session_date",
        "attendance_status",
    ]

    # Create StringIO buffer for CSV output
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")

    # Write header row
    writer.writeheader()

    # Write data rows
    for record in records:
        # Format session_date as string (YYYY-MM-DD)
        row = record.copy()
        if "session_date" in row and row["session_date"] is not None:
            if isinstance(row["session_date"], date):
                row["session_date"] = row["session_date"].strftime("%Y-%m-%d")
        writer.writerow(row)

    # Get CSV string
    csv_content = output.getvalue()
    output.close()

    return csv_content

