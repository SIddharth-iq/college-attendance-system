"""
Pydantic schemas for request/response validation.
Defines data structures for API endpoints.
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date, datetime
from app.models import RoleEnum
from sqlalchemy.exc import IntegrityError


# User Schemas
class UserBase(BaseModel):
    """Base user schema with common fields."""

    email: EmailStr
    full_name: str


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str
    role: RoleEnum


class UserResponse(UserBase):
    """Schema for user response (excludes password)."""

    id: int
    role: RoleEnum
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Student Schemas
class StudentBase(BaseModel):
    """Base student schema."""

    student_id: str
    enrollment_date: date


class StudentCreate(BaseModel):
    """Schema for creating a student (requires user_id)."""

    user_id: int
    student_id: str
    enrollment_date: date


class StudentResponse(StudentBase):
    """Schema for student response."""

    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Subject Schemas
class SubjectBase(BaseModel):
    """Base subject schema."""

    code: str
    name: str
    description: Optional[str] = None


class SubjectCreate(SubjectBase):
    """Schema for creating a subject."""

    pass


class SubjectResponse(SubjectBase):
    """Schema for subject response."""

    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Class Schemas
class ClassBase(BaseModel):
    """Base class schema."""

    code: str
    name: str
    academic_year: str


class ClassCreate(ClassBase):
    """Schema for creating a class."""

    pass


class ClassResponse(ClassBase):
    """Schema for class response."""

    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ClassSubject Schemas
class ClassSubjectCreate(BaseModel):
    """Schema for creating class-subject link."""

    class_id: int
    subject_id: int


class ClassSubjectResponse(BaseModel):
    """Schema for class-subject response."""

    id: int
    class_id: int
    subject_id: int
    class_entity: ClassResponse
    subject: SubjectResponse
    created_at: datetime

    class Config:
        from_attributes = True


# Faculty Assignment Schemas
class FacultyAssignmentCreate(BaseModel):
    """Schema for assigning faculty to class-subject."""

    faculty_id: int
    class_subject_id: int


class FacultyAssignmentResponse(BaseModel):
    """Schema for faculty assignment response."""

    id: int
    faculty_id: int
    class_subject_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Attendance Session Schemas
class AttendanceSessionCreate(BaseModel):
    """Schema for creating attendance session."""

    class_subject_id: int
    session_date: date
    notes: Optional[str] = None


class AttendanceSessionResponse(BaseModel):
    """Schema for attendance session response."""

    id: int
    class_subject_id: int
    session_date: date
    start_time: datetime
    end_time: Optional[datetime]
    is_locked: bool
    locked_by: Optional[int]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Attendance Record Schemas
class AttendanceRecordCreate(BaseModel):
    """Schema for creating attendance record."""

    session_id: int
    student_id: int
    is_present: bool


class AttendanceRecordResponse(BaseModel):
    """Schema for attendance record response."""

    id: int
    session_id: int
    student_id: int
    is_present: bool
    marked_by: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# Monthly Report Schemas
class MonthlyAttendanceReport(BaseModel):
    """Schema for monthly attendance percentage report per student."""

    student_id: int
    student_name: str
    student_code: str
    class_code: str
    subject_code: str
    subject_name: str
    month: int
    year: int
    total_sessions: int
    present_count: int
    absent_count: int
    attendance_percentage: float

    class Config:
        from_attributes = True


# Phase 3.2 - Attendance Session V3 Schemas
class AttendanceSessionV3Create(BaseModel):
    """Schema for creating Phase 3.2 attendance session."""

    subject_id: int
    session_date: date


class AttendanceSessionV3Response(BaseModel):
    """Schema for Phase 3.2 attendance session response."""

    id: int
    subject_id: int
    faculty_id: int
    session_date: date
    is_locked: bool
    locked_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# Phase 3.2 - Attendance Record V3 Schemas
class AttendanceRecordV3Create(BaseModel):
    """Schema for creating Phase 3.2 attendance record."""

    student_id: int
    status: str  # "present", "absent", or "late"


class AttendanceRecordV3Response(BaseModel):
    """Schema for Phase 3.2 attendance record response."""

    id: int
    session_id: int
    student_id: int
    status: str
    marked_by: Optional[int]
    marked_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True
