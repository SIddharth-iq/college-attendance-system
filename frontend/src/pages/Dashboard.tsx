import { useAuth } from "../contexts/AuthContext";
import StudentDashboard from "./student/Dashboard";
import FacultyDashboard from "./faculty/Dashboard";
import AdminDashboard from "./admin/Dashboard";

const Dashboard = () => {
  const { role, isLoading } = useAuth();

  if (isLoading) {
    return <p className="text-gray-600">Loading...</p>;
  }

  switch (role) {
    case "STUDENT":
      return <StudentDashboard />;
    case "FACULTY":
      return <FacultyDashboard />;
    case "ADMIN":
      return <AdminDashboard />;
    default:
      return <p className="text-red-600">Invalid role</p>;
  }
};

export default Dashboard;

