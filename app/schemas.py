"""
Pydantic schemas for request/response validation.
Defines data structures for API endpoints.
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date, datetime
from app.models import RoleEnum, AttendanceStatusEnum
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


# Phase 3.2 - Session Student Attendance Response
class SessionStudentAttendanceV3Response(BaseModel):
    """Schema for session student attendance response."""

    student_id: int
    student_code: str
    student_name: str
    attendance_status: Optional[AttendanceStatusEnum]
    marked_at: Optional[datetime]

    class Config:
        from_attributes = True


# Phase 3.2 - Subject Attendance Summary Response
class SubjectAttendanceSummaryV3Response(BaseModel):
    """Schema for subject attendance summary response."""

    student_id: int
    student_code: str
    student_name: str
    total_sessions: int
    present_count: int
    absent_count: int
    late_count: int
    attendance_percentage: float

    class Config:
        from_attributes = True


# Phase 3.2 - Student Own Attendance Record Response
class StudentAttendanceRecordV3Response(BaseModel):
    """Schema for student's own attendance record response."""

    id: int
    session_id: int
    session_date: date
    subject_id: int
    status: str
    marked_at: datetime

    class Config:
        from_attributes = True


# Phase 6.2 - Session Attendance Summary Response Schemas
class AttendanceStatsV3(BaseModel):
    """Aggregated attendance statistics for a session."""

    present_count: int
    absent_count: int
    late_count: int
    not_marked_count: int  # Students with no attendance record
    present_percentage: (
        float  # (present_count / total_students) * 100, or 0.0 if total_students == 0
    )
    marked_percentage: float  # ((present + absent + late) / total_students) * 100, or 0.0 if total_students == 0

    class Config:
        from_attributes = True


class SessionStudentSummaryItemV3(BaseModel):
    """Individual student attendance item within session summary."""

    student_id: int
    student_code: str
    student_name: str
    attendance_status: Optional[AttendanceStatusEnum]  # None if not marked
    marked_at: Optional[datetime]  # None if not marked

    class Config:
        from_attributes = True


class SessionAttendanceSummaryV3Response(BaseModel):
    """Session-wise attendance summary with aggregated statistics."""

    # Session metadata
    session_id: int
    session_date: date
    is_locked: bool
    locked_at: Optional[datetime]  # Can be None if session is not locked

    # Subject information
    subject_id: int
    subject_code: str
    subject_name: str

    # Faculty information
    faculty_id: int
    faculty_name: str

    # Aggregated statistics
    total_students: int  # Total enrolled students for this subject
    attendance_stats: AttendanceStatsV3

    # Per-student list
    students: List[SessionStudentSummaryItemV3]

    class Config:
        from_attributes = True


# Phase 6.4 - Admin Global Attendance Report Schemas
class DateRangeSchema(BaseModel):
    """Date range schema for global report."""

    start_date: Optional[date]
    end_date: Optional[date]

    class Config:
        from_attributes = True


class GlobalSummarySchema(BaseModel):
    """Summary schema for global attendance report."""

    total_sessions: int
    unique_students_count: int
    total_subjects: int
    total_faculty: int
    date_range: DateRangeSchema

    class Config:
        from_attributes = True


class AttendanceOverviewSchema(BaseModel):
    """Attendance overview schema for global report."""

    total_records: int
    present_count: int
    absent_count: int
    late_count: int
    marked_percentage: float  # ((present + absent + late) / total_records) * 100

    class Config:
        from_attributes = True


class SubjectBreakdownItemSchema(BaseModel):
    """Subject breakdown item schema for global report."""

    subject_id: int
    subject_code: str
    subject_name: str
    total_sessions: int
    total_records: int
    present_count: int
    absent_count: int
    late_count: int
    marked_percentage: float  # ((present + absent + late) / total_records) * 100

    class Config:
        from_attributes = True


class FacultyBreakdownItemSchema(BaseModel):
    """Faculty breakdown item schema for global report."""

    faculty_id: int
    faculty_name: str
    total_sessions: int
    total_records: int
    present_count: int
    absent_count: int
    late_count: int
    marked_percentage: float  # ((present + absent + late) / total_records) * 100

    class Config:
        from_attributes = True


class GlobalAttendanceReportResponse(BaseModel):
    """Global attendance report response schema (ADMIN only)."""

    summary: GlobalSummarySchema
    attendance_overview: AttendanceOverviewSchema
    subject_breakdown: List[SubjectBreakdownItemSchema]
    faculty_breakdown: List[FacultyBreakdownItemSchema]

    class Config:
        from_attributes = True


# Phase 6.5 - Student-wise Attendance Report Schemas
class StudentInfoSchema(BaseModel):
    """Student information schema for student attendance report."""

    student_id: int
    student_code: str
    student_name: str

    class Config:
        from_attributes = True


class StudentSummarySchema(BaseModel):
    """Summary schema for student attendance report."""

    total_sessions: int
    present_count: int
    absent_count: int
    late_count: int
    attendance_percentage: float  # ((present + absent + late) / total_sessions) * 100

    class Config:
        from_attributes = True


class StudentSubjectBreakdownSchema(BaseModel):
    """Subject breakdown item schema for student attendance report."""

    subject_id: int
    subject_code: str
    subject_name: str
    total_sessions: int
    present_count: int
    absent_count: int
    late_count: int
    attendance_percentage: float  # ((present + absent + late) / total_sessions) * 100

    class Config:
        from_attributes = True


class StudentAttendanceReportResponse(BaseModel):
    """Student attendance report response schema."""

    student: StudentInfoSchema
    summary: StudentSummarySchema
    subject_breakdown: List[StudentSubjectBreakdownSchema]

    class Config:
        from_attributes = True


# Phase 6.6 - Faculty-Scoped Student Attendance Report Schemas
class FacultyStudentInfoSchema(BaseModel):
    """Student information schema for faculty-scoped student attendance report."""

    student_id: int
    student_code: str
    student_name: str

    class Config:
        from_attributes = True


class FacultyStudentSummarySchema(BaseModel):
    """Summary schema for faculty-scoped student attendance report.
    
    attendance_percentage represents attendance coverage/participation completeness,
    not attendance quality. Late counts as attended.
    Formula: ((present + absent + late) / total_sessions) * 100
    """

    total_sessions: int
    present_count: int
    absent_count: int
    late_count: int
    attendance_percentage: float  # ((present + absent + late) / total_sessions) * 100

    class Config:
        from_attributes = True


class FacultyStudentSubjectBreakdownSchema(BaseModel):
    """Subject breakdown item schema for faculty-scoped student attendance report.
    
    attendance_percentage represents attendance coverage/participation completeness,
    not attendance quality. Late counts as attended.
    Formula: ((present + absent + late) / total_sessions) * 100
    """

    subject_id: int
    subject_code: str
    subject_name: str
    total_sessions: int
    present_count: int
    absent_count: int
    late_count: int
    attendance_percentage: float  # ((present + absent + late) / total_sessions) * 100

    class Config:
        from_attributes = True


class FacultyStudentAttendanceReportResponse(BaseModel):
    """Faculty-scoped student attendance report response schema."""

    student: FacultyStudentInfoSchema
    summary: FacultyStudentSummarySchema
    subject_breakdown: List[FacultyStudentSubjectBreakdownSchema]

    class Config:
        from_attributes = True