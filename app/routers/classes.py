"""
Classes router for faculty class management endpoints.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import User, RoleEnum
from app.routers.auth import require_role
from app.services.classes_service import (
    get_faculty_classes,
    get_class_subject_students,
)
from app.schemas import FacultyClassResponse, ClassSubjectStudentsResponse

router = APIRouter()


@router.get(
    "/me",
    response_model=List[FacultyClassResponse],
    status_code=status.HTTP_200_OK,
)
def get_my_classes(
    current_user: User = Depends(require_role([RoleEnum.FACULTY])),
    db: Session = Depends(get_db),
):
    """
    Get all classes assigned to the authenticated faculty user.

    Returns a list of classes (with subjects) that the faculty member is assigned to teach.
    Each entry includes class information, subject information, and student count.

    Authorization:
    - FACULTY: Can access their own classes
    - STUDENT: 403 Forbidden
    - ADMIN: 403 Forbidden
    - Unauthenticated: 401 Unauthorized

    Returns empty list if faculty has no class assignments.
    """
    return get_faculty_classes(db=db, faculty_id=current_user.id)


@router.get(
    "/{class_subject_id}/students",
    response_model=ClassSubjectStudentsResponse,
    status_code=status.HTTP_200_OK,
)
def get_class_subject_students_endpoint(
    class_subject_id: int,
    current_user: User = Depends(require_role([RoleEnum.FACULTY])),
    db: Session = Depends(get_db),
):
    """
    Get class-subject details and enrolled students for the authenticated faculty user.

    Returns class information, subject information, and a list of all students
    enrolled in the class associated with the class-subject combination.

    Authorization:
    - FACULTY: Can access class-subjects they are assigned to
    - STUDENT: 403 Forbidden
    - ADMIN: 403 Forbidden
    - Unauthenticated: 401 Unauthorized

    Returns 403 if faculty is not assigned to the requested class-subject.
    Returns 404 if class-subject does not exist.
    Returns empty students list if class has no enrolled students.
    """
    return get_class_subject_students(
        db=db, class_subject_id=class_subject_id, faculty_id=current_user.id
    )
