export interface StudentInfo {
    student_id: number;
    student_code: string;
    student_name: string;
  }
  
  export interface StudentSummary {
    total_sessions: number;
    present_count: number;
    absent_count: number;
    late_count: number;
    attendance_percentage: number;
  }
  
  export interface SubjectBreakdown {
    subject_id: number;
    subject_code: string;
    subject_name: string;
    total_sessions: number;
    present_count: number;
    absent_count: number;
    late_count: number;
    attendance_percentage: number;
  }
  
  export interface StudentAttendanceReport {
    student: StudentInfo;
    summary: StudentSummary;
    subject_breakdown: SubjectBreakdown[];
  }
  