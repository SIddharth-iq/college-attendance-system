import { DashboardLayout } from "../../layouts/DashboardLayout";
import { useStudentReport } from "../../hooks/useStudentReport";

const Attendance = () => {
  const { data, isLoading, error } = useStudentReport();

  if (isLoading) {
    return (
      <DashboardLayout>
        <p className="text-gray-600">Loading attendance...</p>
      </DashboardLayout>
    );
  }

  if (error || !data) {
    return (
      <DashboardLayout>
        <p className="text-red-600">Failed to load attendance data</p>
      </DashboardLayout>
    );
  }

  const { subject_breakdown } = data;

  if (!subject_breakdown || subject_breakdown.length === 0) {
    return (
      <DashboardLayout>
        <div className="space-y-6">
          <h1 className="text-2xl font-bold">Attendance</h1>
          <p className="text-gray-600">No attendance data available</p>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Attendance</h1>

        <div className="bg-white border rounded overflow-x-auto">
          <table className="min-w-full border-collapse">
            <thead className="bg-gray-100">
              <tr>
                <th className="text-left p-3 border-b">Subject</th>
                <th className="text-center p-3 border-b">Sessions</th>
                <th className="text-center p-3 border-b">Present</th>
                <th className="text-center p-3 border-b">Absent</th>
                <th className="text-center p-3 border-b">Attendance %</th>
              </tr>
            </thead>
            <tbody>
              {subject_breakdown.map((subject) => (
                <tr key={subject.subject_id} className="hover:bg-gray-50">
                  <td className="p-3 border-b">{subject.subject_name}</td>
                  <td className="text-center p-3 border-b">
                    {subject.total_sessions}
                  </td>
                  <td className="text-center p-3 border-b text-green-600">
                    {subject.present_count}
                  </td>
                  <td className="text-center p-3 border-b text-red-600">
                    {subject.absent_count}
                  </td>
                  <td className="text-center p-3 border-b">
                    {subject.attendance_percentage}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default Attendance;

