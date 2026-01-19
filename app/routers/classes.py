# Create app/routers/classes.py

"""
Classes router for faculty class management endpoints.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import User, RoleEnum
from app.routers.auth import require_role
from app.services.classes_service import get_faculty_classes
from app.schemas import FacultyClassResponse

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
