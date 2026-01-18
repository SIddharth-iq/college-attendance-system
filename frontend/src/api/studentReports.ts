import api from "./axios";

export const getStudentReport = async (studentId: number) => {
  const res = await api.get(`/reports/student/${studentId}`);
  return res.data;
};
