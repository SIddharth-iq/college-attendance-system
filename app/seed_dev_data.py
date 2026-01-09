from datetime import date
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    User,
    RoleEnum,
    Subject,
    AttendanceSessionV3,
    AttendanceRecordV3,
    AttendanceStatusEnum,
    Student,
    Class,
    ClassSubject,
    ClassEnrollment,
    FacultyAssignment,
)
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def get_or_create(db: Session, model, defaults=None, **filters):
    instance = db.query(model).filter_by(**filters).first()
    if instance:
        return instance
    instance = model(**filters, **(defaults or {}))
    db.add(instance)
    db.commit()
    db.refresh(instance)
    return instance


def seed():
    db = SessionLocal()

    # --------------------
    # USERS
    # --------------------
    admin = get_or_create(
        db,
        User,
        email="admin@college.com",
        defaults={
            "full_name": "System Admin",
            "password_hash": hash_password("admin123"),
            "role": RoleEnum.ADMIN,
            "is_active": True,
        },
    )

    faculty1 = get_or_create(
        db,
        User,
        email="faculty1@college.com",
        defaults={
            "full_name": "Faculty One",
            "password_hash": hash_password("faculty123"),
            "role": RoleEnum.FACULTY,
            "is_active": True,
        },
    )

    faculty2 = get_or_create(
        db,
        User,
        email="faculty2@college.com",
        defaults={
            "full_name": "Faculty Two",
            "password_hash": hash_password("faculty123"),
            "role": RoleEnum.FACULTY,
            "is_active": True,
        },
    )
    faculty3 = get_or_create(
        db,
        User,
        email="faculty3@college.com",
        defaults={
            "full_name": "Faculty Three",
            "password_hash": hash_password("faculty123"),
            "role": RoleEnum.FACULTY,
            "is_active": True,
        },
    )

    student1 = get_or_create(
        db,
        User,
        email="student1@college.com",
        defaults={
            "full_name": "Student One",
            "password_hash": hash_password("student123"),
            "role": RoleEnum.STUDENT,
            "is_active": True,
        },
    )

    student2 = get_or_create(
        db,
        User,
        email="student2@college.com",
        defaults={
            "full_name": "Student Two",
            "password_hash": hash_password("student123"),
            "role": RoleEnum.STUDENT,
            "is_active": True,
        },
    )
    student3 = get_or_create(
        db,
        User,
        email="student3@college.com",
        defaults={
            "full_name": "Student Three",
            "password_hash": hash_password("student123"),
            "role": RoleEnum.STUDENT,
            "is_active": True,
        },
    )
    # --------------------
    # STUDENTS (DOMAIN TABLE)
    # --------------------
    student1_profile = get_or_create(
        db,
        Student,
        user_id=student1.id,
        student_id="STU001",
        defaults={
            "enrollment_date": date(2024, 6, 1),
        },
    )

    student2_profile = get_or_create(
        db,
        Student,
        user_id=student2.id,
        student_id="STU002",
        defaults={
            "enrollment_date": date(2024, 6, 1),
        },
    )
    student3_profile = get_or_create(
        db,
        Student,
        user_id=student3.id,
        student_id="STU003",
        defaults={
            "enrollment_date": date(2024, 6, 1),
        },
    )

    # --------------------
    # SUBJECTS
    # --------------------
    subject1 = get_or_create(
        db,
        Subject,
        code="CS101",
        defaults={"name": "Computer Science"},
    )

    subject2 = get_or_create(
        db,
        Subject,
        code="CS102",
        defaults={"name": "Data Structures"},
    )
    # --------------------
    # CLASSES
    # --------------------
    class_2a = get_or_create(
        db,
        Class,
        code="CSE2A",
        defaults={
            "name": "CSE 2nd Year - Section A",
            "academic_year": "2025-2026",
        },
    )

    # --------------------
    # CLASS-SUBJECT MAPPING
    # --------------------
    class_subject_cs101 = get_or_create(
        db,
        ClassSubject,
        class_id=class_2a.id,
        subject_id=subject1.id,
    )

    # --------------------
    # FACULTY ASSIGNMENTS
    # --------------------
    get_or_create(
        db,
        FacultyAssignment,
        faculty_id=faculty1.id,
        class_subject_id=class_subject_cs101.id,
    )
    # --------------------
    # CLASS-SUBJECT MAPPING for CS102 (Data Structures)
    # --------------------
    class_subject_cs102 = get_or_create(
        db,
        ClassSubject,
        class_id=class_2a.id,
        subject_id=subject2.id,
    )
    # --------------------
    get_or_create(
        db,
        FacultyAssignment,
        faculty_id=faculty2.id,
        class_subject_id=class_subject_cs102.id,
    )

    # --------------------
    # CLASS ENROLLMENTS
    # --------------------
    get_or_create(
        db,
        ClassEnrollment,
        student_id=student1_profile.id,
        class_id=class_2a.id,
    )

    get_or_create(
        db,
        ClassEnrollment,
        student_id=student2_profile.id,
        class_id=class_2a.id,
    )

    # --------------------
    # ATTENDANCE SESSION
    # --------------------
    session1 = get_or_create(
        db,
        AttendanceSessionV3,
        subject_id=subject1.id,
        faculty_id=faculty1.id,
        session_date=date(2026, 1, 1),
        defaults={"is_locked": True},
    )

    session2 = get_or_create(
        db,
        AttendanceSessionV3,
        subject_id=subject1.id,  # SAME subject
        faculty_id=faculty1.id,  # SAME faculty
        session_date=date(2026, 1, 2),  # DIFFERENT date
        defaults={"is_locked": True},
    )

    # --------------------
    # ATTENDANCE RECORDS FOR SESSION1 & SESSION2
    # --------------------
    get_or_create(
        db,
        AttendanceRecordV3,
        session_id=session1.id,
        student_id=student1_profile.id,
        defaults={"status": AttendanceStatusEnum.PRESENT},
    )

    get_or_create(
        db,
        AttendanceRecordV3,
        session_id=session1.id,
        student_id=student2_profile.id,
        defaults={"status": AttendanceStatusEnum.ABSENT},
    )

    get_or_create(
        db,
        AttendanceRecordV3,
        session_id=session2.id,
        student_id=student1_profile.id,
        defaults={"status": AttendanceStatusEnum.PRESENT},
    )

    get_or_create(
        db,
        AttendanceRecordV3,
        session_id=session2.id,
        student_id=student2_profile.id,
        defaults={"status": AttendanceStatusEnum.ABSENT},
    )
    # --------------------
    # ATTENDANCE SESSION FOR DATA STRUCTURES (SUBJECT2)
    # --------------------
    session3 = get_or_create(
        db,
        AttendanceSessionV3,
        subject_id=subject2.id,
        faculty_id=faculty3.id,  # assigned faculty who previously had no sessions
        session_date=date(2026, 1, 3),
        defaults={"is_locked": True},
    )

    # --------------------
    # ATTENDANCE RECORDS FOR SESSION3
    # --------------------
    get_or_create(
        db,
        AttendanceRecordV3,
        session_id=session3.id,
        student_id=student1_profile.id,
        defaults={"status": AttendanceStatusEnum.PRESENT},
    )

    get_or_create(
        db,
        AttendanceRecordV3,
        session_id=session3.id,
        student_id=student2_profile.id,
        defaults={"status": AttendanceStatusEnum.ABSENT},
    )

    db.close()
    print("✅ Dev database seeded successfully")


if __name__ == "__main__":
    seed()
