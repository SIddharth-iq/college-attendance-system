"""
Reports service module for CSV export functionality.
Contains business logic for generating CSV reports.
"""

import csv
import io
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, case, and_
from fastapi import HTTPException, status
from app.models import (
    AttendanceRecordV3,
    AttendanceSessionV3,
    AttendanceStatusEnum,
    Subject,
    Student,
    ClassEnrollment,
    ClassSubject,
    User,
    RoleEnum,
)
from app.schemas import (
    SessionAttendanceSummaryV3Response,
    AttendanceStatsV3,
    SessionStudentSummaryItemV3,
    GlobalAttendanceReportResponse,
    GlobalSummarySchema,
    DateRangeSchema,
    AttendanceOverviewSchema,
    SubjectBreakdownItemSchema,
    FacultyBreakdownItemSchema,
    StudentAttendanceReportResponse,
    StudentInfoSchema,
    StudentSummarySchema,
    StudentSubjectBreakdownSchema,
    FacultyStudentAttendanceReportResponse,
    FacultyStudentInfoSchema,
    FacultyStudentSummarySchema,
    FacultyStudentSubjectBreakdownSchema,
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
        .join(
            AttendanceSessionV3, AttendanceRecordV3.session_id == AttendanceSessionV3.id
        )
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
        records.append(
            {
                "student_id": student.id,
                "student_code": student.student_id,
                "student_name": user.full_name,
                "subject_id": subject.id,
                "subject_name": subject.name,
                "session_id": session.id,
                "session_date": session.session_date,
                "attendance_status": record_v3.status.value.upper(),  # PRESENT, ABSENT, LATE
            }
        )

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


def get_session_attendance_summary(
    session_id: int,
    current_user: User,
    db: Session,
) -> SessionAttendanceSummaryV3Response:
    """
    Get comprehensive attendance summary for a single session.

    Handles session lookup, authorization, aggregation queries, and student list query.
    This function is the single source of truth for session summary data.

    Args:
        session_id: ID of the attendance session
        current_user: Current authenticated user
        db: Database session

    Returns:
        SessionAttendanceSummaryV3Response with session metadata, stats, and student list

    Raises:
        HTTPException(404): Session, subject, or faculty not found
        HTTPException(403): FACULTY accessing another faculty's session
    """
    # 1. Fetch session
    session = (
        db.query(AttendanceSessionV3)
        .filter(AttendanceSessionV3.id == session_id)
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance session not found",
        )

    # 2. Authorization check
    if current_user.role == RoleEnum.FACULTY:
        if session.faculty_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your own attendance sessions",
            )

    # 3. Get subject details
    subject = db.query(Subject).filter(Subject.id == session.subject_id).first()
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject not found for this session",
        )

    # 4. Get faculty details
    faculty = db.query(User).filter(User.id == session.faculty_id).first()
    if not faculty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Faculty not found for this session",
        )

    # 5. Aggregation query - Calculate total students and counts by status
    aggregation_result = (
        db.query(
            func.count(func.distinct(Student.id)).label("total_students"),
            func.count(
                func.distinct(
                    case(
                        (
                            AttendanceRecordV3.status == AttendanceStatusEnum.PRESENT,
                            AttendanceRecordV3.id,
                        ),
                        else_=None,
                    )
                )
            ).label("present_count"),
            func.count(
                func.distinct(
                    case(
                        (
                            AttendanceRecordV3.status == AttendanceStatusEnum.ABSENT,
                            AttendanceRecordV3.id,
                        ),
                        else_=None,
                    )
                )
            ).label("absent_count"),
            func.count(
                func.distinct(
                    case(
                        (
                            AttendanceRecordV3.status == AttendanceStatusEnum.LATE,
                            AttendanceRecordV3.id,
                        ),
                        else_=None,
                    )
                )
            ).label("late_count"),
        )
        .join(ClassEnrollment, ClassEnrollment.student_id == Student.id)
        .join(ClassSubject, ClassSubject.class_id == ClassEnrollment.class_id)
        .outerjoin(
            AttendanceRecordV3,
            and_(
                AttendanceRecordV3.student_id == Student.id,
                AttendanceRecordV3.session_id == session_id,
            ),
        )
        .filter(ClassSubject.subject_id == session.subject_id)
        .first()
    )

    total_students = aggregation_result.total_students or 0
    present_count = aggregation_result.present_count or 0
    absent_count = aggregation_result.absent_count or 0
    late_count = aggregation_result.late_count or 0
    not_marked_count = total_students - (present_count + absent_count + late_count)

    # Calculate percentages with division by zero protection
    if total_students > 0:
        present_percentage = round((present_count / total_students) * 100, 2)
        marked_percentage = round(
            ((present_count + absent_count + late_count) / total_students) * 100, 2
        )
    else:
        present_percentage = 0.0
        marked_percentage = 0.0

    # 6. Per-student list query
    students_query = (
        db.query(
            Student.id.label("student_id"),
            Student.student_id.label("student_code"),
            User.full_name.label("student_name"),
            AttendanceRecordV3.status.label("attendance_status"),
            AttendanceRecordV3.marked_at.label("marked_at"),
        )
        .join(ClassEnrollment, ClassEnrollment.student_id == Student.id)
        .join(ClassSubject, ClassSubject.class_id == ClassEnrollment.class_id)
        .join(User, User.id == Student.user_id)
        .outerjoin(
            AttendanceRecordV3,
            and_(
                AttendanceRecordV3.student_id == Student.id,
                AttendanceRecordV3.session_id == session_id,
            ),
        )
        .filter(ClassSubject.subject_id == session.subject_id)
        .distinct()
        .order_by(User.full_name.asc())
    )

    students_results = students_query.all()

    # 7. Map results to response schemas
    attendance_stats = AttendanceStatsV3(
        present_count=present_count,
        absent_count=absent_count,
        late_count=late_count,
        not_marked_count=not_marked_count,
        present_percentage=present_percentage,
        marked_percentage=marked_percentage,
    )

    students_list = []
    for row in students_results:
        students_list.append(
            SessionStudentSummaryItemV3(
                student_id=row.student_id,
                student_code=row.student_code,
                student_name=row.student_name,
                attendance_status=row.attendance_status,  # Already Optional[AttendanceStatusEnum]
                marked_at=row.marked_at,
            )
        )

    # 8. Construct and return response
    return SessionAttendanceSummaryV3Response(
        session_id=session.id,
        session_date=session.session_date,
        is_locked=session.is_locked,
        locked_at=session.locked_at,  # Can be None if session is not locked
        subject_id=subject.id,
        subject_code=subject.code,
        subject_name=subject.name,
        faculty_id=session.faculty_id,
        faculty_name=faculty.full_name,
        total_students=total_students,
        attendance_stats=attendance_stats,
        students=students_list,
    )


def generate_session_summary_csv(
    summary_data: SessionAttendanceSummaryV3Response,
) -> str:
    """
    Generate CSV string from session attendance summary data.

    Creates a multi-section CSV with:
    - Session metadata rows
    - Aggregated statistics rows
    - Blank separator row
    - Student table with header and data rows

    Args:
        summary_data: SessionAttendanceSummaryV3Response object

    Returns:
        CSV string content ready for download

    CSV Format:
    Row 1: Session ID, Session Date, Subject Code, Subject Name
    Row 2: Faculty Name, Is Locked
    Row 3: Total Students, Present Count, Absent Count, Late Count, Not Marked Count
    Row 4: Present Percentage, Marked Percentage
    Row 5: (blank row)
    Row 6: Student Code, Student Name, Attendance Status, Marked At (header)
    Row 7+: Student data rows
    """
    # Create StringIO buffer for CSV output
    output = io.StringIO()
    writer = csv.writer(output)

    # Row 1: Session metadata (ID, date, subject code, subject name)
    writer.writerow(
        [
            "Session ID",
            str(summary_data.session_id),
            "Session Date",
            str(summary_data.session_date),
            "Subject Code",
            summary_data.subject_code,
            "Subject Name",
            summary_data.subject_name,
        ]
    )

    # Row 2: Faculty name, is_locked
    writer.writerow(
        [
            "Faculty Name",
            summary_data.faculty_name,
            "Is Locked",
            "true" if summary_data.is_locked else "false",
        ]
    )

    # Row 3: Total students + counts
    writer.writerow(
        [
            "Total Students",
            str(summary_data.total_students),
            "Present Count",
            str(summary_data.attendance_stats.present_count),
            "Absent Count",
            str(summary_data.attendance_stats.absent_count),
            "Late Count",
            str(summary_data.attendance_stats.late_count),
            "Not Marked Count",
            str(summary_data.attendance_stats.not_marked_count),
        ]
    )

    # Row 4: Percentages
    writer.writerow(
        [
            "Present Percentage",
            f"{summary_data.attendance_stats.present_percentage:.2f}",
            "Marked Percentage",
            f"{summary_data.attendance_stats.marked_percentage:.2f}",
        ]
    )

    # Row 5: Blank row
    writer.writerow([])

    # Row 6: Student table header
    writer.writerow(
        [
            "Student Code",
            "Student Name",
            "Attendance Status",
            "Marked At",
        ]
    )

    # Row 7+: Student data rows
    for student in summary_data.students:
        # Format marked_at as string if present
        marked_at_str = ""
        if student.marked_at:
            marked_at_str = student.marked_at.strftime("%Y-%m-%d %H:%M:%S")

        # Format attendance_status (enum value or empty string)
        attendance_status_str = ""
        if student.attendance_status:
            # Handle both enum type and string (if already serialized)
            if isinstance(student.attendance_status, AttendanceStatusEnum):
                attendance_status_str = student.attendance_status.value
            else:
                attendance_status_str = str(student.attendance_status)

        writer.writerow(
            [
                student.student_code,
                student.student_name,
                attendance_status_str,
                marked_at_str,
            ]
        )

    # Get CSV string
    csv_content = output.getvalue()
    output.close()

    return csv_content


def get_global_attendance_report(
    db: Session,
    start_date: Optional[date],
    end_date: Optional[date],
    subject_id: Optional[int],
    faculty_id: Optional[int],
    limit_subjects: int,
    limit_faculty: int,
) -> GlobalAttendanceReportResponse:
    """
    Get global attendance report with aggregated statistics (ADMIN only).

    All aggregations are done in SQL using GROUP BY + CASE statements.
    No Python-side counting, no N+1 queries.

    Args:
        db: Database session
        start_date: Optional start date filter (applied to session_date)
        end_date: Optional end date filter (applied to session_date)
        subject_id: Optional subject filter
        faculty_id: Optional faculty filter
        limit_subjects: Limit for subject_breakdown (default 20)
        limit_faculty: Limit for faculty_breakdown (default 20)

    Returns:
        GlobalAttendanceReportResponse with summary, overview, and breakdowns

    Note:
        - Summary uses LEFT JOIN to include sessions with zero records
        - Overview and breakdowns use INNER JOIN (only sessions with records)
        - marked_percentage = ((present + absent + late) / total_records) * 100
    """
    # 1. Summary Aggregation (LEFT JOIN to include sessions with zero records)
    summary_result = (
        db.query(
            func.count(func.distinct(AttendanceSessionV3.id)).label("total_sessions"),
            func.count(func.distinct(AttendanceRecordV3.student_id)).label(
                "unique_students_count"
            ),
            func.count(func.distinct(AttendanceSessionV3.subject_id)).label(
                "total_subjects"
            ),
            func.count(func.distinct(AttendanceSessionV3.faculty_id)).label(
                "total_faculty"
            ),
        )
        .select_from(AttendanceSessionV3)
        .outerjoin(
            AttendanceRecordV3,
            AttendanceRecordV3.session_id == AttendanceSessionV3.id,
        )
    )

    # Apply filters to summary query
    if start_date:
        summary_result = summary_result.filter(
            AttendanceSessionV3.session_date >= start_date
        )
    if end_date:
        summary_result = summary_result.filter(
            AttendanceSessionV3.session_date <= end_date
        )
    if subject_id:
        summary_result = summary_result.filter(
            AttendanceSessionV3.subject_id == subject_id
        )
    if faculty_id:
        summary_result = summary_result.filter(
            AttendanceSessionV3.faculty_id == faculty_id
        )

    summary_row = summary_result.first()
    total_sessions = summary_row.total_sessions or 0
    unique_students_count = summary_row.unique_students_count or 0
    total_subjects = summary_row.total_subjects or 0
    total_faculty = summary_row.total_faculty or 0

    # 2. Attendance Overview Aggregation (INNER JOIN - only sessions with records)
    overview_result = (
        db.query(
            func.count(AttendanceRecordV3.id).label("total_records"),
            func.sum(
                case(
                    (AttendanceRecordV3.status == AttendanceStatusEnum.PRESENT, 1),
                    else_=0,
                )
            ).label("present_count"),
            func.sum(
                case(
                    (AttendanceRecordV3.status == AttendanceStatusEnum.ABSENT, 1),
                    else_=0,
                )
            ).label("absent_count"),
            func.sum(
                case(
                    (AttendanceRecordV3.status == AttendanceStatusEnum.LATE, 1),
                    else_=0,
                )
            ).label("late_count"),
        )
        .select_from(AttendanceSessionV3)
        .join(
            AttendanceRecordV3,
            AttendanceRecordV3.session_id == AttendanceSessionV3.id,
        )
    )

    # Apply filters to overview query
    if start_date:
        overview_result = overview_result.filter(
            AttendanceSessionV3.session_date >= start_date
        )
    if end_date:
        overview_result = overview_result.filter(
            AttendanceSessionV3.session_date <= end_date
        )
    if subject_id:
        overview_result = overview_result.filter(
            AttendanceSessionV3.subject_id == subject_id
        )
    if faculty_id:
        overview_result = overview_result.filter(
            AttendanceSessionV3.faculty_id == faculty_id
        )

    overview_row = overview_result.first()
    total_records = overview_row.total_records or 0
    present_count = overview_row.present_count or 0
    absent_count = overview_row.absent_count or 0
    late_count = overview_row.late_count or 0

    # Calculate marked_percentage: ((present + absent + late) / total_records) * 100
    if total_records > 0:
        marked_percentage = round(
            ((present_count + absent_count + late_count) / total_records) * 100, 2
        )
    else:
        marked_percentage = 0.0

    # 3. Subject Breakdown (INNER JOIN - only sessions with records, GROUP BY)
    subject_breakdown_query = (
        db.query(
            AttendanceSessionV3.subject_id,
            Subject.code.label("subject_code"),
            Subject.name.label("subject_name"),
            func.count(func.distinct(AttendanceSessionV3.id)).label("total_sessions"),
            func.count(AttendanceRecordV3.id).label("total_records"),
            func.sum(
                case(
                    (AttendanceRecordV3.status == AttendanceStatusEnum.PRESENT, 1),
                    else_=0,
                )
            ).label("present_count"),
            func.sum(
                case(
                    (AttendanceRecordV3.status == AttendanceStatusEnum.ABSENT, 1),
                    else_=0,
                )
            ).label("absent_count"),
            func.sum(
                case(
                    (AttendanceRecordV3.status == AttendanceStatusEnum.LATE, 1),
                    else_=0,
                )
            ).label("late_count"),
        )
        .select_from(AttendanceSessionV3)
        .join(
            AttendanceRecordV3,
            AttendanceRecordV3.session_id == AttendanceSessionV3.id,
        )
        .join(Subject, Subject.id == AttendanceSessionV3.subject_id)
    )

    # -------------------------------------------------
    # APPLY FILTERS FIRST (CRITICAL FIX)
    # -------------------------------------------------
    if start_date:
        subject_breakdown_query = subject_breakdown_query.filter(
            AttendanceSessionV3.session_date >= start_date
        )
    if end_date:
        subject_breakdown_query = subject_breakdown_query.filter(
            AttendanceSessionV3.session_date <= end_date
        )
    if subject_id:
        subject_breakdown_query = subject_breakdown_query.filter(
            AttendanceSessionV3.subject_id == subject_id
        )

    if faculty_id:
        subject_breakdown_query = subject_breakdown_query.filter(
            AttendanceSessionV3.faculty_id == faculty_id
        )

    # -------------------------------------------------
    # GROUP, ORDER, LIMIT — LAST
    # -------------------------------------------------
    subject_breakdown_query = (
        subject_breakdown_query.group_by(
            AttendanceSessionV3.subject_id,
            Subject.code,
            Subject.name,
        )
        .order_by(func.count(AttendanceRecordV3.id).desc())
        .limit(limit_subjects)
    )
    # -------------------------------------------------
    # EXECUTION & MAPPING (UNCHANGED)
    # -------------------------------------------------
    subject_breakdown_rows = subject_breakdown_query.all()

    subject_breakdown = []
    for row in subject_breakdown_rows:
        subj_total_records = row.total_records or 0
        subj_present = row.present_count or 0
        subj_absent = row.absent_count or 0
        subj_late = row.late_count or 0

        if subj_total_records > 0:
            subj_marked_percentage = round(
                ((subj_present + subj_absent + subj_late) / subj_total_records) * 100,
                2,
            )
        else:
            subj_marked_percentage = 0.0

        subject_breakdown.append(
            SubjectBreakdownItemSchema(
                subject_id=row.subject_id,
                subject_code=row.subject_code,
                subject_name=row.subject_name,
                total_sessions=row.total_sessions or 0,
                total_records=subj_total_records,
                present_count=subj_present,
                absent_count=subj_absent,
                late_count=subj_late,
                marked_percentage=subj_marked_percentage,
            )
        )

    # 4. Faculty Breakdown (INNER JOIN - only sessions with records, GROUP BY)
    # ---------------------------
    # FACULTY BREAKDOWN QUERY
    # ---------------------------

    faculty_breakdown_query = (
        db.query(
            AttendanceSessionV3.faculty_id,
            User.full_name.label("faculty_name"),
            func.count(func.distinct(AttendanceSessionV3.id)).label("total_sessions"),
            func.count(AttendanceRecordV3.id).label("total_records"),
            func.sum(
                case(
                    (AttendanceRecordV3.status == AttendanceStatusEnum.PRESENT, 1),
                    else_=0,
                )
            ).label("present_count"),
            func.sum(
                case(
                    (AttendanceRecordV3.status == AttendanceStatusEnum.ABSENT, 1),
                    else_=0,
                )
            ).label("absent_count"),
            func.sum(
                case(
                    (AttendanceRecordV3.status == AttendanceStatusEnum.LATE, 1),
                    else_=0,
                )
            ).label("late_count"),
        )
        .select_from(AttendanceSessionV3)
        .join(
            AttendanceRecordV3,
            AttendanceRecordV3.session_id == AttendanceSessionV3.id,
        )
        .join(User, User.id == AttendanceSessionV3.faculty_id)
    )

    # ---------------------------
    # APPLY FILTERS (ALWAYS FIRST)
    # ---------------------------

    if start_date:
        faculty_breakdown_query = faculty_breakdown_query.filter(
            AttendanceSessionV3.session_date >= start_date
        )

    if end_date:
        faculty_breakdown_query = faculty_breakdown_query.filter(
            AttendanceSessionV3.session_date <= end_date
        )

    if subject_id:
        faculty_breakdown_query = faculty_breakdown_query.filter(
            AttendanceSessionV3.subject_id == subject_id
        )

    if faculty_id:
        faculty_breakdown_query = faculty_breakdown_query.filter(
            AttendanceSessionV3.faculty_id == faculty_id
        )

    # ---------------------------
    # GROUP, ORDER, LIMIT
    # ---------------------------

    faculty_breakdown_query = (
        faculty_breakdown_query.group_by(AttendanceSessionV3.faculty_id, User.full_name)
        .order_by(func.count(AttendanceRecordV3.id).desc())
        .limit(limit_faculty)
    )
    # ---------------------------
    # EXECUTE & MAP RESPONSE
    # ---------------------------

    faculty_breakdown_rows = faculty_breakdown_query.all()

    faculty_breakdown = []
    for row in faculty_breakdown_rows:
        fac_total_records = row.total_records or 0
        fac_present = row.present_count or 0
        fac_absent = row.absent_count or 0
        fac_late = row.late_count or 0

        if fac_total_records > 0:
            fac_marked_percentage = round(
                ((fac_present + fac_absent + fac_late) / fac_total_records) * 100, 2
            )
        else:
            fac_marked_percentage = 0.0
    fac_late = row.late_count or 0

    if fac_total_records > 0:
        fac_marked_percentage = round(
            ((fac_present + fac_absent + fac_late) / fac_total_records) * 100, 2
        )
    else:
        fac_marked_percentage = 0.0

    faculty_breakdown.append(
        FacultyBreakdownItemSchema(
            faculty_id=row.faculty_id,
            faculty_name=row.faculty_name,
            total_sessions=row.total_sessions or 0,
            total_records=fac_total_records,
            present_count=fac_present,
            absent_count=fac_absent,
            late_count=fac_late,
            marked_percentage=fac_marked_percentage,
        )
    )

    # 5. Construct and return response
    return GlobalAttendanceReportResponse(
        summary=GlobalSummarySchema(
            total_sessions=total_sessions,
            unique_students_count=unique_students_count,
            total_subjects=total_subjects,
            total_faculty=total_faculty,
            date_range=DateRangeSchema(start_date=start_date, end_date=end_date),
        ),
        attendance_overview=AttendanceOverviewSchema(
            total_records=total_records,
            present_count=present_count,
            absent_count=absent_count,
            late_count=late_count,
            marked_percentage=marked_percentage,
        ),
        subject_breakdown=subject_breakdown,
        faculty_breakdown=faculty_breakdown,
    )


def get_student_attendance_report(
    db: Session,
    student_id: int,
    start_date: Optional[date],
    end_date: Optional[date],
    subject_id: Optional[int],
    limit_subjects: Optional[int] = 20,
) -> StudentAttendanceReportResponse:
    """
    Get student-wise attendance report with aggregated statistics.

    All aggregations are done in SQL using GROUP BY + CASE statements.
    No Python-side counting, no N+1 queries.

    Args:
        db: Database session
        student_id: Student ID to generate report for
        start_date: Optional start date filter (applied to session_date)
        end_date: Optional end date filter (applied to session_date)
        subject_id: Optional subject filter
        limit_subjects: Limit for subject_breakdown (default 20)

    Returns:
        StudentAttendanceReportResponse with student info, summary, and subject breakdown

    Raises:
        HTTPException(404): Student not found

    Note:
        - Summary uses INNER JOIN (only sessions with records for this student)
        - attendance_percentage = ((present + absent + late) / total_sessions) * 100
        - Late counts as attended for percentage calculation
    """
    # 1. Validate student exists and fetch student info
    student = (
        db.query(Student)
        .join(User, Student.user_id == User.id)
        .filter(Student.id == student_id)
        .first()
    )

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )

    student_info = StudentInfoSchema(
        student_id=student.id,
        student_code=student.student_id,  # student_id column contains the code
        student_name=student.user.full_name,
    )

    # 2. Summary Aggregation Query (INNER JOIN - only sessions with records for this student)
    summary_query = (
        db.query(
            func.count(func.distinct(AttendanceSessionV3.id)).label("total_sessions"),
            func.sum(
                case(
                    (AttendanceRecordV3.status == AttendanceStatusEnum.PRESENT, 1),
                    else_=0,
                )
            ).label("present_count"),
            func.sum(
                case(
                    (AttendanceRecordV3.status == AttendanceStatusEnum.ABSENT, 1),
                    else_=0,
                )
            ).label("absent_count"),
            func.sum(
                case(
                    (AttendanceRecordV3.status == AttendanceStatusEnum.LATE, 1),
                    else_=0,
                )
            ).label("late_count"),
        )
        .select_from(AttendanceSessionV3)
        .join(
            AttendanceRecordV3,
            and_(
                AttendanceRecordV3.session_id == AttendanceSessionV3.id,
                AttendanceRecordV3.student_id == student_id,
            ),
        )
    )

    # Apply filters to summary query
    if start_date:
        summary_query = summary_query.filter(
            AttendanceSessionV3.session_date >= start_date
        )
    if end_date:
        summary_query = summary_query.filter(
            AttendanceSessionV3.session_date <= end_date
        )
    if subject_id:
        summary_query = summary_query.filter(
            AttendanceSessionV3.subject_id == subject_id
        )

    summary_row = summary_query.first()
    total_sessions = summary_row.total_sessions or 0
    present_count = summary_row.present_count or 0
    absent_count = summary_row.absent_count or 0
    late_count = summary_row.late_count or 0

    # Calculate attendance_percentage: ((present + absent + late) / total_sessions) * 100
    if total_sessions > 0:
        attendance_percentage = round(
            ((present_count + absent_count + late_count) / total_sessions) * 100, 2
        )
    else:
        attendance_percentage = 0.0

    summary = StudentSummarySchema(
        total_sessions=total_sessions,
        present_count=present_count,
        absent_count=absent_count,
        late_count=late_count,
        attendance_percentage=attendance_percentage,
    )

    # 3. Subject Breakdown Query (INNER JOIN - only sessions with records, GROUP BY)
    subject_breakdown_query = (
        db.query(
            AttendanceSessionV3.subject_id,
            Subject.code.label("subject_code"),
            Subject.name.label("subject_name"),
            func.count(func.distinct(AttendanceSessionV3.id)).label("total_sessions"),
            func.sum(
                case(
                    (AttendanceRecordV3.status == AttendanceStatusEnum.PRESENT, 1),
                    else_=0,
                )
            ).label("present_count"),
            func.sum(
                case(
                    (AttendanceRecordV3.status == AttendanceStatusEnum.ABSENT, 1),
                    else_=0,
                )
            ).label("absent_count"),
            func.sum(
                case(
                    (AttendanceRecordV3.status == AttendanceStatusEnum.LATE, 1),
                    else_=0,
                )
            ).label("late_count"),
        )
        .select_from(AttendanceSessionV3)
        .join(
            AttendanceRecordV3,
            and_(
                AttendanceRecordV3.session_id == AttendanceSessionV3.id,
                AttendanceRecordV3.student_id == student_id,
            ),
        )
        .join(Subject, Subject.id == AttendanceSessionV3.subject_id)
    )

    # Apply filters to subject breakdown query
    if start_date:
        subject_breakdown_query = subject_breakdown_query.filter(
            AttendanceSessionV3.session_date >= start_date
        )
    if end_date:
        subject_breakdown_query = subject_breakdown_query.filter(
            AttendanceSessionV3.session_date <= end_date
        )
    if subject_id:
        subject_breakdown_query = subject_breakdown_query.filter(
            AttendanceSessionV3.subject_id == subject_id
        )

    # Group, order, and limit
    subject_breakdown_query = (
        subject_breakdown_query.group_by(
            AttendanceSessionV3.subject_id,
            Subject.code,
            Subject.name,
        )
        .order_by(func.count(func.distinct(AttendanceSessionV3.id)).desc())
        .limit(limit_subjects or 20)
    )

    subject_breakdown_rows = subject_breakdown_query.all()

    subject_breakdown = []
    for row in subject_breakdown_rows:
        subj_total_sessions = row.total_sessions or 0
        subj_present = row.present_count or 0
        subj_absent = row.absent_count or 0
        subj_late = row.late_count or 0

        if subj_total_sessions > 0:
            subj_attendance_percentage = round(
                ((subj_present + subj_absent + subj_late) / subj_total_sessions) * 100,
                2,
            )
        else:
            subj_attendance_percentage = 0.0

        subject_breakdown.append(
            StudentSubjectBreakdownSchema(
                subject_id=row.subject_id,
                subject_code=row.subject_code,
                subject_name=row.subject_name,
                total_sessions=subj_total_sessions,
                present_count=subj_present,
                absent_count=subj_absent,
                late_count=subj_late,
                attendance_percentage=subj_attendance_percentage,
            )
        )

    # 4. Construct and return response
    return StudentAttendanceReportResponse(
        student=student_info,
        summary=summary,
        subject_breakdown=subject_breakdown,
    )


def get_faculty_student_attendance_report(
    db: Session,
    student_id: int,
    faculty_id: Optional[int],  # None = ADMIN (unrestricted), int = FACULTY (scoped)
    start_date: Optional[date],
    end_date: Optional[date],
    subject_id: Optional[int],
    limit_subjects: int = 20,
) -> FacultyStudentAttendanceReportResponse:
    """
    Get faculty-scoped student attendance report with aggregated statistics.

    All aggregations are done in SQL using GROUP BY + CASE statements.
    No Python-side counting, no N+1 queries.

    Args:
        db: Database session
        student_id: Student ID to generate report for
        faculty_id: Faculty ID to scope sessions (None for ADMIN = unrestricted,
                   int for FACULTY = scoped to sessions where faculty_id matches)
        start_date: Optional start date filter (applied to session_date)
        end_date: Optional end date filter (applied to session_date)
        subject_id: Optional subject filter
        limit_subjects: Limit for subject_breakdown (default 20)

    Returns:
        FacultyStudentAttendanceReportResponse with student info, summary, and subject breakdown

    Raises:
        HTTPException(404): Student not found

    Note:
        - Summary uses INNER JOIN (only sessions with records for this student)
        - Faculty scoping: If faculty_id is not None, only sessions where
          AttendanceSessionV3.faculty_id == faculty_id are included
        - ADMIN: faculty_id=None means unrestricted access (all faculty sessions)
        - FACULTY: faculty_id=int means strictly scoped to their own sessions
        - attendance_percentage = ((present + absent + late) / total_sessions) * 100
        - Late counts as attended for percentage calculation
        - Returns 200 OK with zeros if faculty never taught student (intentional usability decision)
    """
    # 1. Validate student exists and fetch student info
    student = (
        db.query(Student)
        .join(User, Student.user_id == User.id)
        .filter(Student.id == student_id)
        .first()
    )

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )

    student_info = FacultyStudentInfoSchema(
        student_id=student.id,
        student_code=student.student_id,  # student_id column contains the code
        student_name=student.user.full_name,
    )

    # 2. Summary Aggregation Query (INNER JOIN - only sessions with records for this student)
    # CRITICAL: Apply faculty_id filter FIRST (before other filters)
    summary_query = (
        db.query(
            func.count(func.distinct(AttendanceSessionV3.id)).label("total_sessions"),
            func.sum(
                case(
                    (AttendanceRecordV3.status == AttendanceStatusEnum.PRESENT, 1),
                    else_=0,
                )
            ).label("present_count"),
            func.sum(
                case(
                    (AttendanceRecordV3.status == AttendanceStatusEnum.ABSENT, 1),
                    else_=0,
                )
            ).label("absent_count"),
            func.sum(
                case(
                    (AttendanceRecordV3.status == AttendanceStatusEnum.LATE, 1),
                    else_=0,
                )
            ).label("late_count"),
        )
        .select_from(AttendanceSessionV3)
        .join(
            AttendanceRecordV3,
            and_(
                AttendanceRecordV3.session_id == AttendanceSessionV3.id,
                AttendanceRecordV3.student_id == student_id,
            ),
        )
    )

    # Apply faculty scope filter FIRST (CRITICAL: before other filters)
    if faculty_id is not None:
        summary_query = summary_query.filter(
            AttendanceSessionV3.faculty_id == faculty_id
        )

    # Apply date and subject filters
    if start_date:
        summary_query = summary_query.filter(
            AttendanceSessionV3.session_date >= start_date
        )
    if end_date:
        summary_query = summary_query.filter(
            AttendanceSessionV3.session_date <= end_date
        )
    if subject_id:
        summary_query = summary_query.filter(
            AttendanceSessionV3.subject_id == subject_id
        )

    summary_row = summary_query.first()
    total_sessions = summary_row.total_sessions or 0
    present_count = summary_row.present_count or 0
    absent_count = summary_row.absent_count or 0
    late_count = summary_row.late_count or 0

    # Calculate attendance_percentage: ((present + absent + late) / total_sessions) * 100
    if total_sessions > 0:
        attendance_percentage = round(
            ((present_count + absent_count + late_count) / total_sessions) * 100, 2
        )
    else:
        attendance_percentage = 0.0

    summary = FacultyStudentSummarySchema(
        total_sessions=total_sessions,
        present_count=present_count,
        absent_count=absent_count,
        late_count=late_count,
        attendance_percentage=attendance_percentage,
    )

    # 3. Subject Breakdown Query (INNER JOIN - only sessions with records, GROUP BY)
    subject_breakdown_query = (
        db.query(
            AttendanceSessionV3.subject_id,
            Subject.code.label("subject_code"),
            Subject.name.label("subject_name"),
            func.count(func.distinct(AttendanceSessionV3.id)).label("total_sessions"),
            func.sum(
                case(
                    (AttendanceRecordV3.status == AttendanceStatusEnum.PRESENT, 1),
                    else_=0,
                )
            ).label("present_count"),
            func.sum(
                case(
                    (AttendanceRecordV3.status == AttendanceStatusEnum.ABSENT, 1),
                    else_=0,
                )
            ).label("absent_count"),
            func.sum(
                case(
                    (AttendanceRecordV3.status == AttendanceStatusEnum.LATE, 1),
                    else_=0,
                )
            ).label("late_count"),
        )
        .select_from(AttendanceSessionV3)
        .join(
            AttendanceRecordV3,
            and_(
                AttendanceRecordV3.session_id == AttendanceSessionV3.id,
                AttendanceRecordV3.student_id == student_id,
            ),
        )
        .join(Subject, Subject.id == AttendanceSessionV3.subject_id)
    )

    # Apply faculty scope filter FIRST (CRITICAL: before GROUP BY)
    if faculty_id is not None:
        subject_breakdown_query = subject_breakdown_query.filter(
            AttendanceSessionV3.faculty_id == faculty_id
        )

    # Apply date and subject filters
    if start_date:
        subject_breakdown_query = subject_breakdown_query.filter(
            AttendanceSessionV3.session_date >= start_date
        )
    if end_date:
        subject_breakdown_query = subject_breakdown_query.filter(
            AttendanceSessionV3.session_date <= end_date
        )
    if subject_id:
        subject_breakdown_query = subject_breakdown_query.filter(
            AttendanceSessionV3.subject_id == subject_id
        )

    # Group, order, and limit
    subject_breakdown_query = (
        subject_breakdown_query.group_by(
            AttendanceSessionV3.subject_id,
            Subject.code,
            Subject.name,
        )
        .order_by(func.count(func.distinct(AttendanceSessionV3.id)).desc())
        .limit(limit_subjects)
    )

    subject_breakdown_rows = subject_breakdown_query.all()

    subject_breakdown = []
    for row in subject_breakdown_rows:
        subj_total_sessions = row.total_sessions or 0
        subj_present = row.present_count or 0
        subj_absent = row.absent_count or 0
        subj_late = row.late_count or 0

        if subj_total_sessions > 0:
            subj_attendance_percentage = round(
                ((subj_present + subj_absent + subj_late) / subj_total_sessions) * 100,
                2,
            )
        else:
            subj_attendance_percentage = 0.0

        subject_breakdown.append(
            FacultyStudentSubjectBreakdownSchema(
                subject_id=row.subject_id,
                subject_code=row.subject_code,
                subject_name=row.subject_name,
                total_sessions=subj_total_sessions,
                present_count=subj_present,
                absent_count=subj_absent,
                late_count=subj_late,
                attendance_percentage=subj_attendance_percentage,
            )
        )

    # 4. Construct and return response
    return FacultyStudentAttendanceReportResponse(
        student=student_info,
        summary=summary,
        subject_breakdown=subject_breakdown,
    )