"""
Admin routes for managing subjects, classes, and faculty assignments.
Only accessible by ADMIN role.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.models import User, Subject, Class, ClassSubject, FacultyAssignment, RoleEnum
from app.schemas import (
    SubjectCreate,
    SubjectResponse,
    ClassCreate,
    ClassResponse,
    ClassSubjectCreate,
    ClassSubjectResponse,
    FacultyAssignmentCreate,
    FacultyAssignmentResponse,
)
from app.dependencies import require_role


router = APIRouter()

print("require_role is:", require_role)
print("type:", type(require_role))


# Subject Management
@router.post(
    "/subjects", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED
)
def create_subject(
    subject_data: SubjectCreate,
    current_user: User = Depends(require_role([RoleEnum.ADMIN])),
    db: Session = Depends(get_db),
):
    """Create a new subject."""
    # Check if subject code already exists
    existing = db.query(Subject).filter(Subject.code == subject_data.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subject with this code already exists",
        )

    subject = Subject(**subject_data.dict())
    try:
        db.add(subject)
        db.commit()
        db.refresh(subject)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate or invalid operation",
        )
    return subject


@router.get("/subjects", response_model=List[SubjectResponse])
def list_subjects(
    current_user: User = Depends(require_role([RoleEnum.ADMIN])),
    db: Session = Depends(get_db),
):
    """List all subjects."""
    subjects = db.query(Subject).all()
    return subjects


# Class Management
@router.post(
    "/classes", response_model=ClassResponse, status_code=status.HTTP_201_CREATED
)
def create_class(
    class_data: ClassCreate,
    current_user: User = Depends(require_role([RoleEnum.ADMIN])),
    db: Session = Depends(get_db),
):
    """Create a new class."""
    existing = db.query(Class).filter(Class.code == class_data.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Class with this code already exists",
        )

    class_entity = Class(**class_data.dict())
    try:
        db.add(class_entity)
        db.commit()
        db.refresh(class_entity)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate or invalid operation",
        )
    return class_entity


@router.get("/classes", response_model=List[ClassResponse])
def list_classes(
    current_user: User = Depends(require_role([RoleEnum.ADMIN])),
    db: Session = Depends(get_db),
):
    """List all classes."""
    classes = db.query(Class).all()
    return classes


# Class-Subject Management
@router.post(
    "/class-subjects",
    response_model=ClassSubjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_class_subject(
    data: ClassSubjectCreate,
    current_user: User = Depends(require_role([RoleEnum.ADMIN])),
    db: Session = Depends(get_db),
):
    """Link a subject to a class (create class-subject relationship)."""
    # Verify class and subject exist
    class_entity = db.query(Class).filter(Class.id == data.class_id).first()
    if not class_entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Class not found"
        )

    subject = db.query(Subject).filter(Subject.id == data.subject_id).first()
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found"
        )

    # Check if link already exists
    existing = (
        db.query(ClassSubject)
        .filter(
            and_(
                ClassSubject.class_id == data.class_id,
                ClassSubject.subject_id == data.subject_id,
            )
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This subject is already linked to this class",
        )

    class_subject = ClassSubject(**data.dict())
    try:
        db.add(class_subject)
        db.commit()
        db.refresh(class_subject)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate or invalid operation",
        )
    return class_subject


@router.get("/class-subjects", response_model=List[ClassSubjectResponse])
def list_class_subjects(
    current_user: User = Depends(require_role([RoleEnum.ADMIN])),
    db: Session = Depends(get_db),
):
    """List all class-subject relationships."""
    class_subjects = db.query(ClassSubject).all()
    return class_subjects


# Faculty Assignment Management
@router.post(
    "/faculty-assignments",
    response_model=FacultyAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def assign_faculty(
    data: FacultyAssignmentCreate,
    current_user: User = Depends(require_role([RoleEnum.ADMIN])),
    db: Session = Depends(get_db),
):
    """Assign a faculty member to teach a subject in a class."""
    # Verify faculty user exists and has FACULTY role
    faculty = (
        db.query(User)
        .filter(and_(User.id == data.faculty_id, User.role == RoleEnum.FACULTY))
        .first()
    )
    if not faculty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Faculty user not found or user is not a faculty member",
        )

    # Verify class-subject exists
    class_subject = (
        db.query(ClassSubject).filter(ClassSubject.id == data.class_subject_id).first()
    )
    if not class_subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Class-subject not found"
        )

    # Check if assignment already exists
    existing = (
        db.query(FacultyAssignment)
        .filter(
            and_(
                FacultyAssignment.faculty_id == data.faculty_id,
                FacultyAssignment.class_subject_id == data.class_subject_id,
            )
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Faculty is already assigned to this class-subject",
        )

    assignment = FacultyAssignment(**data.dict())
    try:
        db.add(assignment)
        db.commit()
        db.refresh(assignment)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate or invalid operation",
        )
    return assignment


@router.get("/faculty-assignments", response_model=List[FacultyAssignmentResponse])
def list_faculty_assignments(
    current_user: User = Depends(require_role([RoleEnum.ADMIN])),
    db: Session = Depends(get_db),
):
    """List all faculty assignments."""
    assignments = db.query(FacultyAssignment).all()
    return assignments
