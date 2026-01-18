import { useQuery } from "@tanstack/react-query";
import api from "../api/axios";
import { type StudentAttendanceReport } from "../types/studentReport";

export const useStudentReport = () => {
  return useQuery<StudentAttendanceReport>({
    queryKey: ["student-report"],
    queryFn: async () => {
      const res = await api.get("/reports/student/me");
      return res.data;
    },
  });
};
