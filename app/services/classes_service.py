"""
Classes service module for faculty class management.
Contains business logic for fetching faculty-assigned classes.
"""

from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from app.models import (
    FacultyAssignment,
    ClassSubject,
    Class,
    Subject,
    ClassEnrollment,
    Student,
    User,
)
from app.schemas import (
    FacultyClassResponse,
    ClassSubjectStudentsResponse,
    ClassSubjectDetailsResponse,
    ClassStudentResponse,
)


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


def get_class_subject_students(
    db: Session, class_subject_id: int, faculty_id: int
) -> ClassSubjectStudentsResponse:
    """
    Get class-subject details and enrolled students for a faculty member.

    Args:
        db: Database session
        class_subject_id: ID of the class-subject combination
        faculty_id: ID of the faculty user

    Returns:
        ClassSubjectStudentsResponse containing class-subject details and student list

    Raises:
        HTTPException 403: If faculty is not assigned to this class-subject
        HTTPException 404: If class-subject does not exist
    """
    # 1. Authorization check: Verify faculty is assigned to this class-subject
    assignment = (
        db.query(FacultyAssignment)
        .filter(FacultyAssignment.faculty_id == faculty_id)
        .filter(FacultyAssignment.class_subject_id == class_subject_id)
        .first()
    )

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Faculty not assigned to this class-subject",
        )

    # 2. Fetch class-subject details with class and subject information
    class_subject_row = (
        db.query(ClassSubject, Class, Subject)
        .join(Class, ClassSubject.class_id == Class.id)
        .join(Subject, ClassSubject.subject_id == Subject.id)
        .filter(ClassSubject.id == class_subject_id)
        .first()
    )

    if not class_subject_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class-subject not found",
        )

    class_subject, class_entity, subject_entity = class_subject_row

    # 3. Fetch enrolled students for this class
    students_rows = (
        db.query(Student, User, ClassEnrollment)
        .join(User, Student.user_id == User.id)
        .join(ClassEnrollment, ClassEnrollment.student_id == Student.id)
        .filter(ClassEnrollment.class_id == class_entity.id)
        .order_by(Student.student_id)
        .all()
    )

    # 4. Transform to Pydantic models
    class_subject_details = ClassSubjectDetailsResponse(
        class_subject_id=class_subject.id,
        class_id=class_entity.id,
        class_code=class_entity.code,
        class_name=class_entity.name,
        academic_year=class_entity.academic_year,
        subject_id=subject_entity.id,
        subject_code=subject_entity.code,
        subject_name=subject_entity.name,
    )

    students = []
    for student, user, enrollment in students_rows:
        students.append(
            ClassStudentResponse(
                student_id=student.id,
                student_code=student.student_id,
                full_name=user.full_name,
                email=user.email,
                enrollment_date=enrollment.enrollment_date,
            )
        )

    return ClassSubjectStudentsResponse(
        class_subject=class_subject_details, students=students
    )
