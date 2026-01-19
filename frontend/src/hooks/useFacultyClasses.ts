import { useQuery } from "@tanstack/react-query";
import api from "../api/axios";
import type { FacultyClass } from "../types/facultyClasses";

export const useFacultyClasses = () => {
  return useQuery<FacultyClass[]>({
    queryKey: ["faculty-classes"],
    queryFn: async () => {
      const res = await api.get("/classes/me");
      return res.data;
    },
  });
};

