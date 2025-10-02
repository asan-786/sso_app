import React, { useState, useEffect } from "react";
import { useAuth } from "./AuthContext";
import { Shield, LogOut, Users, Settings, Home } from "lucide-react";

const API_URL = "http://127.0.0.1:8000/applications"; // backend FastAPI

const AdminDashboard = ({ onNavigate }) => {
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState("users");
  const [users, setUsers] = useState([
    { id: 1, name: "Aryan Swarnkar", email: "aryan@university.edu", rollNo: "23UCSE4007", role: "student", status: "Active" },
    { id: 2, name: "Asan Ali", email: "asan@university.edu", rollNo: "23UCSE4008", role: "student", status: "Active" },
    { id: 3, name: "Sankalp Sharma", email: "sankalp@university.edu", rollNo: "23UCSE4044", role: "student", status: "Active" },
    { id: 4, name: "Devansh Silan", email: "devansh@university.edu", rollNo: "23UCSE4012", role: "student", status: "Inactive" },
  ]);

  // --- New State for Applications (Backend CRUD) ---
  const [apps, setApps] = useState([]);
  const [newApp, setNewApp] = useState({ id: "", name: "", url: "" });

  // Load apps from backend
  useEffect(() => {
    fetch(API_URL)
      .then((res) => res.json())
      .then((data) => setApps(data))
      .catch((err) => console.error("Error fetching apps:", err));
  }, []);

  // Add new application
  const handleAddApp = async (e) => {
    e.preventDefault();
    if (!newApp.id || !newApp.name || !newApp.url) {
      alert("Please fill all fields");
      return;
    }
    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newApp),
      });
      const data = await res.json();
      setApps([...apps, data.app]);
      setNewApp({ id: "", name: "", url: "" });
      alert("App added successfully!");
    } catch (err) {
      console.error("Error adding app:", err);
    }
  };

  // Delete application
  const handleDeleteApp = async (id) => {
    try {
      await fetch(`${API_URL}/${id}`, { method: "DELETE" });
      setApps(apps.filter((app) => app.id !== id));
    } catch (err) {
      console.error("Error deleting app:", err);
    }
  };

  // Update role of a user
  const handleRoleChange = (userId, newRole) => {
    setUsers(users.map((u) => (u.id === userId ? { ...u, role: newRole } : u)));
    alert(`Role updated to ${newRole}`);
  };

  const stats = [
    { label: "Total Users", value: "245", icon: Users, color: "bg-blue-500" },
    { label: "Active Sessions", value: "89", icon: Shield, color: "bg-green-500" },
    { label: "Applications", value: apps.length.toString(), icon: Home, color: "bg-purple-500" },
    { label: "Admin Users", value: "5", icon: Settings, color: "bg-orange-500" },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-purple-600 w-10 h-10 rounded-full flex items-center justify-center">
              <Shield className="text-white" size={20} />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-800">Admin Dashboard</h1>
              <p className="text-sm text-gray-500">SSO Management Portal</p>
            </div>
          </div>
          <button
            onClick={() => {
              logout();
              onNavigate("login");
            }}
            className="flex items-center gap-2 px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition"
          >
            <LogOut size={18} />
            Logout
          </button>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {stats.map((stat, idx) => (
            <div key={idx} className="bg-white rounded-xl shadow-md p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-500 text-sm">{stat.label}</p>
                  <p className="text-3xl font-bold text-gray-800 mt-1">{stat.value}</p>
                </div>
                <div className={`${stat.color} w-12 h-12 rounded-lg flex items-center justify-center`}>
                  <stat.icon className="text-white" size={24} />
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-xl shadow-md">
          <div className="border-b border-gray-200">
            <div className="flex gap-4 px-6">
              <button
                onClick={() => setActiveTab("users")}
                className={`py-4 px-2 border-b-2 font-medium transition ${
                  activeTab === "users" ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                User Management
              </button>
              <button
                onClick={() => setActiveTab("roles")}
                className={`py-4 px-2 border-b-2 font-medium transition ${
                  activeTab === "roles" ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                Role Assignment
              </button>
              <button
                onClick={() => setActiveTab("apps")}
                className={`py-4 px-2 border-b-2 font-medium transition ${
                  activeTab === "apps" ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                Manage Applications
              </button>
            </div>
          </div>

          <div className="p-6">
            {activeTab === "users" && (
              <div>
                <h2 className="text-lg font-bold text-gray-800 mb-4">Registered Users</h2>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Roll No</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Role</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {users.map((u) => (
                        <tr key={u.id} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm font-medium text-gray-800">{u.name}</td>
                          <td className="px-4 py-3 text-sm text-gray-600">{u.email}</td>
                          <td className="px-4 py-3 text-sm text-gray-600">{u.rollNo}</td>
                          <td className="px-4 py-3 text-sm">
                            <span
                              className={`px-2 py-1 rounded-full text-xs font-medium ${
                                u.role === "admin" ? "bg-purple-100 text-purple-700" : "bg-blue-100 text-blue-700"
                              }`}
                            >
                              {u.role}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-sm">
                            <span
                              className={`px-2 py-1 rounded-full text-xs font-medium ${
                                u.status === "Active" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
                              }`}
                            >
                              {u.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {activeTab === "roles" && (
              <div>
                <h2 className="text-lg font-bold text-gray-800 mb-4">Role Management</h2>
                <div className="space-y-4">
                  {users.map((u) => (
                    <div
                      key={u.id}
                      className="flex items-center justify-between p-4 border border-gray-200 rounded-lg"
                    >
                      <div>
                        <p className="font-semibold text-gray-800">{u.name}</p>
                        <p className="text-sm text-gray-500">{u.email}</p>
                      </div>
                      <select
                        value={u.role}
                        onChange={(e) => handleRoleChange(u.id, e.target.value)}
                        className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                      >
                        <option value="student">Student</option>
                        <option value="admin">Admin</option>
                      </select>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === "apps" && (
              <div>
                <h2 className="text-lg font-bold text-gray-800 mb-4">Manage Applications</h2>

                {/* Add App Form */}
                <form onSubmit={handleAddApp} className="flex gap-2 mb-4">
                  <input
                    type="number"
                    placeholder="ID"
                    value={newApp.id}
                    onChange={(e) => setNewApp({ ...newApp, id: parseInt(e.target.value) })}
                    className="px-4 py-2 border rounded-lg"
                  />
                  <input
                    type="text"
                    placeholder="App Name"
                    value={newApp.name}
                    onChange={(e) => setNewApp({ ...newApp, name: e.target.value })}
                    className="px-4 py-2 border rounded-lg"
                  />
                  <input
                    type="text"
                    placeholder="App URL"
                    value={newApp.url}
                    onChange={(e) => setNewApp({ ...newApp, url: e.target.value })}
                    className="px-4 py-2 border rounded-lg"
                  />
                  <button type="submit" className="bg-indigo-600 text-white px-4 py-2 rounded-lg">
                    Add
                  </button>
                </form>

                {/* Applications List */}
                <div className="space-y-3">
                  {apps.map((app) => (
                    <div
                      key={app.id}
                      className="flex items-center justify-between p-4 border border-gray-200 rounded-lg"
                    >
                      <div>
                        <p className="font-semibold text-gray-800">{app.name}</p>
                        <p className="text-sm text-gray-500">{app.url}</p>
                      </div>
                      <button
                        onClick={() => handleDeleteApp(app.id)}
                        className="text-red-600 hover:underline"
                      >
                        Delete
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
