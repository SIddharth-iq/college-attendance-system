import { DashboardLayout } from "../../layouts/DashboardLayout";
import { useFacultyClasses } from "../../hooks/useFacultyClasses";

const Classes = () => {
  const { data, isLoading, error } = useFacultyClasses();

  if (isLoading) {
    return (
      <DashboardLayout>
        <p className="text-gray-600">Loading classes...</p>
      </DashboardLayout>
    );
  }

  if (error || !data) {
    return (
      <DashboardLayout>
        <p className="text-red-600">Failed to load classes</p>
      </DashboardLayout>
    );
  }

  if (data.length === 0) {
    return (
      <DashboardLayout>
        <div className="space-y-6">
          <h1 className="text-2xl font-bold">Classes</h1>
          <p className="text-gray-600">No classes assigned</p>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Classes</h1>

        <div className="bg-white border rounded overflow-x-auto">
          <table className="min-w-full border-collapse">
            <thead className="bg-gray-100">
              <tr>
                <th className="text-left p-3 border-b">Class Name</th>
                <th className="text-left p-3 border-b">Class Code</th>
                <th className="text-center p-3 border-b">Students</th>
              </tr>
            </thead>
            <tbody>
              {data.map((classItem) => (
                <tr key={classItem.class_id} className="hover:bg-gray-50">
                  <td className="p-3 border-b">
                    {classItem.class_name || classItem.subject_name}
                  </td>
                  <td className="p-3 border-b">
                    {classItem.class_code || classItem.subject_id || "-"}
                  </td>
                  <td className="text-center p-3 border-b">
                    {classItem.student_count ?? "-"}
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

export default Classes;

