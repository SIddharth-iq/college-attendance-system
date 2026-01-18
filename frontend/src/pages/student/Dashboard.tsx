import { useStudentReport } from "../../hooks/useStudentReport";

const Dashboard = () => {
  const { data, isLoading, error } = useStudentReport();

  if (isLoading) {
    return <p className="p-6 text-gray-600">Loading dashboard...</p>;
  }

  if (error || !data) {
    return (
      <p className="p-6 text-red-600">
        Failed to load student dashboard
      </p>
    );
  }

  const { student, summary, subject_breakdown } = data;

  return (
    <div className="p-6 space-y-6">
      {/* HEADER */}
      <div>
        <h1 className="text-2xl font-bold">Student Dashboard</h1>
        <p className="text-gray-600">
          {student.student_name} ({student.student_code})
        </p>
      </div>

      {/* SUMMARY CARDS */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border rounded p-4">
          <p className="text-sm text-gray-500">Total Sessions</p>
          <p className="text-xl font-semibold">
            {summary.total_sessions}
          </p>
        </div>

        <div className="bg-white border rounded p-4">
          <p className="text-sm text-gray-500">Present</p>
          <p className="text-xl font-semibold text-green-600">
            {summary.present_count}
          </p>
        </div>

        <div className="bg-white border rounded p-4">
          <p className="text-sm text-gray-500">Absent</p>
          <p className="text-xl font-semibold text-red-600">
            {summary.absent_count}
          </p>
        </div>

        <div className="bg-white border rounded p-4">
          <p className="text-sm text-gray-500">Attendance %</p>
          <p className="text-xl font-semibold">
            {summary.attendance_percentage}%
          </p>
        </div>
      </div>

      {/* SUBJECT TABLE */}
      <div className="bg-white border rounded">
        <table className="w-full border-collapse">
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
                <td className="p-3 border-b">
                  {subject.subject_name}
                </td>
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
  );
};

export default Dashboard;
