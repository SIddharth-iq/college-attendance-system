# Create app/services/classes_service.py

"""
Classes service module for faculty class management.
Contains business logic for fetching faculty-assigned classes.
"""

from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import (
    FacultyAssignment,
    ClassSubject,
    Class,
    Subject,
    ClassEnrollment,
)
from app.schemas import FacultyClassResponse


def get_faculty_classes(db: Session, faculty_id: int):
    query = (
        db.query(
            Class.id.label("class_id"),
            Class.code.label("class_code"),
            Class.name.label("class_name"),
            Class.academic_year.label("academic_year"),
            Subject.id.label("subject_id"),
            Subject.code.label("subject_code"),
            Subject.name.label("subject_name"),
        )
        .select_from(FacultyAssignment)
        .join(
            ClassSubject,
            FacultyAssignment.class_subject_id == ClassSubject.id,
        )
        .join(
            Class,
            ClassSubject.class_id == Class.id,
        )
        .join(
            Subject,
            ClassSubject.subject_id == Subject.id,
        )
        .filter(FacultyAssignment.faculty_id == faculty_id)
    )

    return query.all()

    # Transform to Pydantic models
    classes = []
    for row in results:
        classes.append(
            FacultyClassResponse(
                class_id=row.class_id,
                class_code=row.class_code,
                class_name=row.class_name,
                academic_year=row.academic_year,
                subject_id=row.subject_id,
                subject_code=row.subject_code,
                subject_name=row.subject_name,
                student_count=row.student_count if row.student_count else 0,
            )
        )

    return classes
