export interface FacultyClass {
  class_id: number;
  class_name: string;
  class_code?: string;
  subject_id?: number;
  subject_name?: string;
  student_count?: number;
}

export interface FacultyClassesResponse {
  classes: FacultyClass[];
}

