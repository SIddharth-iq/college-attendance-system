"""
Database models for College Attendance Management System.
Defines all database tables with relationships.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Enum,
    Boolean,
    ForeignKey,
    Date,
    Float,
    DateTime,
    Text,
)
from sqlalchemy import Column, Integer, String, Boolean, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.sql.functions import current_user
from app.database import Base
import enum
from datetime import datetime
from sqlalchemy import UniqueConstraint


class BaseModel(Base):
    """
    Abstract base model with common fields.
    All models inherit id, created_at, updated_at from this.
    """

    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class RoleEnum(str, enum.Enum):
    """User roles in the system - defines access levels."""

    ADMIN = "admin"  # Full system access
    FACULTY = "faculty"  # Can manage attendance for assigned subjects/classes
    STUDENT = "student"  # Can view own attendance


class User(BaseModel):
    """
    User model - represents all users (Admin, Faculty, Students).
    Uses role-based access control (RBAC) via RoleEnum.
    """

    __tablename__ = "users"

    # Basic user info
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)  # Store hashed password
    full_name = Column(String(255), nullable=False)

    # Role-based access control
    role = Column(Enum(RoleEnum), nullable=False, index=True)

    # Additional fields
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    # Students: link to student_profile if role is STUDENT
    student_profile = relationship(
        "Student", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    # Faculty: link to faculty_assignments if role is FACULTY
    faculty_assignments = relationship(
        "FacultyAssignment", back_populates="faculty", cascade="all, delete-orphan"
    )

    # Attendance records for students


class Student(BaseModel):
    """
    Student model - extends User with student-specific information.
    One-to-one relationship with User (when user.role = STUDENT).
    """

    __tablename__ = "students"

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    student_id = Column(
        String(50), unique=True, index=True, nullable=False
    )  # e.g., "STU2024001"
    enrollment_date = Column(Date, nullable=False)

    # Relationship
    user = relationship("User", back_populates="student_profile")

    # Many-to-many: students enrolled in classes
    class_enrollments = relationship(
        "ClassEnrollment", back_populates="student", cascade="all, delete-orphan"
    )

    # Attendance records
    attendance_records = relationship(
        "AttendanceRecord", back_populates="student", cascade="all, delete-orphan"
    )


class Subject(BaseModel):
    """
    Subject model - represents academic subjects/courses.
    Examples: "Mathematics", "Computer Science 101", etc.
    """

    __tablename__ = "subjects"

    code = Column(String(50), unique=True, index=True, nullable=False)  # e.g., "CS101"
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Relationships
    # Many-to-many: subjects assigned to classes
    class_subjects = relationship(
        "ClassSubject", back_populates="subject", cascade="all, delete-orphan"
    )


class Class(BaseModel):
    """
    Class model - represents academic classes/batches.
    Examples: "CS-A-2024", "ME-B-2024" (Computer Science Section A, Mechanical Engineering Section B)
    """

    __tablename__ = "classes"

    code = Column(
        String(50), unique=True, index=True, nullable=False
    )  # e.g., "CS-A-2024"
    name = Column(String(255), nullable=False)  # e.g., "Computer Science Section A"
    academic_year = Column(String(20), nullable=False)  # e.g., "2024-2025"

    # Relationships
    # Many-to-many: classes have subjects
    class_subjects = relationship(
        "ClassSubject", back_populates="class_entity", cascade="all, delete-orphan"
    )

    # Students enrolled in this class
    enrollments = relationship(
        "ClassEnrollment", back_populates="class_entity", cascade="all, delete-orphan"
    )


class ClassSubject(BaseModel):
    """
    Junction table: Links Classes and Subjects (many-to-many).
    Also links Faculty to teach specific subject in specific class.
    Represents: "Faculty X teaches Subject Y in Class Z"
    """

    __tablename__ = "class_subjects"

    class_id = Column(
        Integer,
        ForeignKey("classes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_id = Column(
        Integer,
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationships
    class_entity = relationship("Class", back_populates="class_subjects")
    subject = relationship("Subject", back_populates="class_subjects")

    # Faculty assignments for this class-subject combination
    faculty_assignments = relationship(
        "FacultyAssignment",
        back_populates="class_subject",
        cascade="all, delete-orphan",
    )

    # Attendance sessions for this class-subject
    attendance_sessions = relationship(
        "AttendanceSession",
        back_populates="class_subject",
        cascade="all, delete-orphan",
    )

    # Unique constraint: same subject can't be added twice to same class
    __table_args__ = ({"mysql_engine": "InnoDB"},)


class FacultyAssignment(BaseModel):
    """
    Faculty assignment model - links Faculty (User) to ClassSubject.
    Represents: "Faculty with user_id teaches class_id + subject_id combination"
    """

    __tablename__ = "faculty_assignments"

    faculty_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    class_subject_id = Column(
        Integer,
        ForeignKey("class_subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationships
    faculty = relationship("User", back_populates="faculty_assignments")
    class_subject = relationship("ClassSubject", back_populates="faculty_assignments")

    # Unique constraint: same faculty can't be assigned twice to same class-subject
    __table_args__ = ({"mysql_engine": "InnoDB"},)


class ClassEnrollment(BaseModel):
    """
    Student enrollment model - links Students to Classes (many-to-many).
    Represents: "Student X is enrolled in Class Y"
    """

    __tablename__ = "class_enrollments"

    student_id = Column(
        Integer,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    class_id = Column(
        Integer,
        ForeignKey("classes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    enrollment_date = Column(Date, nullable=False, default=func.curdate())

    # Relationships
    student = relationship("Student", back_populates="class_enrollments")
    class_entity = relationship("Class", back_populates="enrollments")

    # Unique constraint: student can't be enrolled twice in same class
    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "class_id",
            name="uq_student_class_enrollment",
        ),
    )


class AttendanceSession(BaseModel):
    """
    Attendance session model - represents a single attendance-taking session.
    Once is_locked=True, no more records can be added/modified for this session.
    Faculty creates session, marks attendance, then locks it to prevent changes.
    """

    __tablename__ = "attendance_sessions"

    class_subject_id = Column(
        Integer,
        ForeignKey("class_subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    session_date = Column(Date, nullable=False, index=True)
    start_time = Column(DateTime, nullable=False)  # When session was created/started
    end_time = Column(DateTime, nullable=True)  # When session was locked

    # Lock mechanism - prevents further modifications once True
    locked_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Faculty who locked it

    # Additional info
    notes = Column(Text, nullable=True)  # Optional notes about the session

    # Relationships
    class_subject = relationship("ClassSubject", back_populates="attendance_sessions")

    # All attendance records for this session
    attendance_records = relationship(
        "AttendanceRecord", back_populates="session", cascade="all, delete-orphan"
    )

    # Unique constraint: one session per class-subject per date
    __table_args__ = (
        UniqueConstraint(
            "class_subject_id",
            "session_date",
            name="uq_session_per_class_subject_per_day",
        ),
    )


class AttendanceRecord(BaseModel):
    """
    Attendance record model - individual student attendance entry.
    Links: Student + AttendanceSession + status (present/absent).
    Can only be created/modified when session.is_locked = False.
    """

    __tablename__ = "attendance_records"

    session_id = Column(
        Integer,
        ForeignKey("attendance_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id = Column(
        Integer,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Attendance status
    is_present = Column(
        Boolean, nullable=False, default=False
    )  # True = present, False = absent

    # Marked by (faculty user_id)
    marked_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    session = relationship("AttendanceSession", back_populates="attendance_records")
    student = relationship("Student", back_populates="attendance_records")

    # Unique constraint: one record per student per session
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "student_id",
            name="uq_one_attendance_per_student_per_session",
        ),
    )


class AttendanceSessionV3(BaseModel):
    """
    Phase 3.1 Attendance Session model.
    Simplified attendance session with direct subject and faculty references.
    """

    __tablename__ = "attendance_sessions_v3"

    subject_id = Column(
        Integer,
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    faculty_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_date = Column(Date, nullable=False, index=True)
    is_locked = Column(Boolean, default=False, nullable=False)
    locked_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "subject_id",
            "faculty_id",
            "session_date",
            name="uq_subject_faculty_date_v3",
        ),
    )

    # Relationships
    attendance_records_v3 = relationship(
        "AttendanceRecordV3",
        back_populates="session",
        cascade="all, delete-orphan",
    )


class AttendanceStatusEnum(str, enum.Enum):
    """Attendance status options for Phase 3.2."""

    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"


class AttendanceRecordV3(BaseModel):
    """
    Phase 3.2 Attendance Record model.
    Individual student attendance entry for AttendanceSessionV3.
    """

    __tablename__ = "attendance_records_v3"

    session_id = Column(
        Integer,
        ForeignKey("attendance_sessions_v3.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id = Column(
        Integer,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(
        Enum(AttendanceStatusEnum),
        nullable=False,
    )
    marked_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    marked_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    session = relationship(
        "AttendanceSessionV3", back_populates="attendance_records_v3"
    )
    student = relationship("Student")

    # Unique constraint: one record per student per session
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "student_id",
            name="uq_one_attendance_per_student_per_session_v3",
        ),
    )
