import React, { useState, useEffect } from "react";
import { useAuth } from "./AuthContext";
import { Shield, LogOut, Users, Settings, Home, Edit2, Trash2, UserPlus, Link2 } from "lucide-react";

const API_URL = "http://127.0.0.1:8000/api";

const AdminDashboard = () => {
  const { user, logout, token } = useAuth();
  const [activeTab, setActiveTab] = useState("users");
  const [users, setUsers] = useState([]);
  const [apps, setApps] = useState([]);
  
  // App form state
  const [newApp, setNewApp] = useState({ 
    name: "", 
    url: "", 
    client_id: "", 
    client_secret: "" 
  });
  const [editingApp, setEditingApp] = useState(null);
  
  // Mapping state
  const [showMapModal, setShowMapModal] = useState(false);
  const [selectedApp, setSelectedApp] = useState(null);
  const [mappingEmail, setMappingEmail] = useState("");

  // Load users from backend
  useEffect(() => {
    if (!token) return;
    loadUsers();
  }, [token]);

  // Load apps from backend
  useEffect(() => {
    if (!token) return;
    loadApps();
  }, [token]);

  const loadUsers = async () => {
    try {
      const res = await fetch(`${API_URL}/users`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setUsers(data);
    } catch (err) {
      console.error("Error fetching users:", err);
    }
  };

  const loadApps = async () => {
    try {
      const res = await fetch(`${API_URL}/applications`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setApps(data || []);
    } catch (err) {
      console.error("Error fetching apps:", err);
      setApps([]);
    }
  };

  // Add new application
  const handleAddApp = async (e) => {
    e.preventDefault();
    if (!newApp.name || !newApp.url) {
      alert("Please fill required fields (Name and URL)");
      return;
    }
    try {
      const res = await fetch(`${API_URL}/applications`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(newApp),
      });
      
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      
      await loadApps();
      setNewApp({ name: "", url: "", client_id: "", client_secret: "" });
      alert("App added successfully!");
    } catch (err) {
      console.error("Error adding app:", err);
      alert("Failed to add application");
    }
  };

  // Update application
  const handleUpdateApp = async (e) => {
    e.preventDefault();
    if (!editingApp.name || !editingApp.url) {
      alert("Please fill required fields");
      return;
    }
    try {
      const res = await fetch(`${API_URL}/applications/${editingApp.id}`, {
        method: "PUT",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          name: editingApp.name,
          url: editingApp.url,
          client_id: editingApp.client_id,
          client_secret: editingApp.client_secret
        }),
      });
      
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      
      await loadApps();
      setEditingApp(null);
      alert("App updated successfully!");
    } catch (err) {
      console.error("Error updating app:", err);
      alert("Failed to update application.");
    }
  };

  // Delete application
  const handleDeleteApp = async (id) => {
    if (!confirm("Are you sure you want to delete this application?")) return;
    
    try {
      const res = await fetch(`${API_URL}/applications/${id}`, { 
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
      });
      
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      
      await loadApps();
      alert("App deleted successfully!");
    } catch (err) {
      console.error("Error deleting app:", err);
      alert("Failed to delete application!");
    }
  };

  // Map user to application
  const handleMapUser = async () => {
    if (!mappingEmail || !selectedApp) {
      alert("Please enter an email");
      return;
    }
    
    try {
      const res = await fetch(`${API_URL}/map`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          email: mappingEmail,
          app_id: selectedApp.id
        }),
      });
      
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      
      await loadApps();
      setShowMapModal(false);
      setMappingEmail("");
      alert("User mapped successfully!");
    } catch (err) {
      console.error("Error mapping user:", err);
      alert("Failed to map user");
    }
  };

  // Unmap user from application
  const handleUnmapUser = async (email, appId) => {
    if (!confirm(`Remove access for ${email}?`)) return;
    
    try {
      const res = await fetch(`${API_URL}/unmap`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          email: email,
          app_id: appId
        }),
      });
      
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      
      await loadApps();
      alert("User access removed!");
    } catch (err) {
      console.error("Error unmapping user:", err);
      alert("Failed to remove access");
    }
  };

  // Update user role
  const handleRoleChange = async (userId, newRole) => {
    try {
      const res = await fetch(`${API_URL}/users/${userId}/role?role=${newRole}`, {
        method: "PUT",
        headers: { "Authorization": `Bearer ${token}` }
      });
      
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      
      await loadUsers();
      alert(`Role updated to ${newRole}`);
    } catch (err) {
      console.error("Error updating role:", err);
      alert("Failed to update role");
    }
  };

  const stats = [
    { label: "Total Users", value: users.length.toString(), icon: Users, color: "bg-blue-500" },
    { label: "Active Sessions", value: users.filter(u => u.status === "active").length.toString(), icon: Shield, color: "bg-green-500" },
    { label: "Applications", value: apps.length.toString(), icon: Home, color: "bg-purple-500" },
    { label: "Admin Users", value: users.filter(u => u.role === "admin").length.toString(), icon: Settings, color: "bg-orange-500" },
  ];

  return (
    <div className="min-h-screen bg-gray-100">
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
            onClick={logout}
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
            {/* USERS TAB */}
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
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Branch</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Role</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {users.map((u) => (
                        <tr key={u.id} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm font-medium text-gray-800">{u.name}</td>
                          <td className="px-4 py-3 text-sm text-gray-600">{u.email}</td>
                          <td className="px-4 py-3 text-sm text-gray-600">{u.rollNo || "N/A"}</td>
                          <td className="px-4 py-3 text-sm text-gray-600">{u.branch || "N/A"}</td>
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
                                u.status === "active" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
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

            {/* ROLES TAB */}
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

            {/* APPLICATIONS TAB */}
            {activeTab === "apps" && (
              <div>
                <h2 className="text-lg font-bold text-gray-800 mb-4">Manage Applications</h2>

                {/* Add/Edit App Form */}
                <form onSubmit={editingApp ? handleUpdateApp : handleAddApp} className="space-y-3 mb-6 p-4 bg-gray-50 rounded-lg">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <input
                      type="text"
                      placeholder="Application Name *"
                      value={editingApp ? editingApp.name : newApp.name}
                      onChange={(e) => editingApp 
                        ? setEditingApp({...editingApp, name: e.target.value})
                        : setNewApp({...newApp, name: e.target.value})
                      }
                      className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
                      required
                    />
                    <input
                      type="url"
                      placeholder="Application URL *"
                      value={editingApp ? editingApp.url : newApp.url}
                      onChange={(e) => editingApp 
                        ? setEditingApp({...editingApp, url: e.target.value})
                        : setNewApp({...newApp, url: e.target.value})
                      }
                      className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
                      required
                    />
                    <input
                      type="text"
                      placeholder="Client ID (optional)"
                      value={editingApp ? editingApp.client_id : newApp.client_id}
                      onChange={(e) => editingApp 
                        ? setEditingApp({...editingApp, client_id: e.target.value})
                        : setNewApp({...newApp, client_id: e.target.value})
                      }
                      className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
                    />
                    <input
                      type="password"
                      placeholder="Client Secret (optional)"
                      value={editingApp ? editingApp.client_secret : newApp.client_secret}
                      onChange={(e) => editingApp 
                        ? setEditingApp({...editingApp, client_secret: e.target.value})
                        : setNewApp({...newApp, client_secret: e.target.value})
                      }
                      className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                  <div className="flex gap-2">
                    <button type="submit" className="bg-indigo-600 text-white px-6 py-2 rounded-lg hover:bg-indigo-700">
                      {editingApp ? "Update Application" : "Add Application"}
                    </button>
                    {editingApp && (
                      <button 
                        type="button" 
                        onClick={() => setEditingApp(null)}
                        className="bg-gray-300 text-gray-700 px-6 py-2 rounded-lg hover:bg-gray-400"
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </form>

                {/* Applications List */}
                <div className="space-y-4">
                  {apps.map((app) => (
                    <div key={app.id} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex-1">
                          <h3 className="font-semibold text-gray-800 text-lg">{app.name}</h3>
                          <p className="text-sm text-gray-500">{app.url}</p>
                          {app.client_id && (
                            <p className="text-xs text-gray-400 mt-1">Client ID: {app.client_id}</p>
                          )}
                        </div>
                        <div className="flex gap-2">
                          <button
                            onClick={() => setEditingApp(app)}
                            className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg"
                            title="Edit"
                          >
                            <Edit2 size={18} />
                          </button>
                          <button
                            onClick={() => {
                              setSelectedApp(app);
                              setShowMapModal(true);
                            }}
                            className="p-2 text-green-600 hover:bg-green-50 rounded-lg"
                            title="Map User"
                          >
                            <UserPlus size={18} />
                          </button>
                          <button
                            onClick={() => handleDeleteApp(app.id)}
                            className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                            title="Delete"
                          >
                            <Trash2 size={18} />
                          </button>
                        </div>
                      </div>
                      
                      {/* Authorized Users */}
                      {app.authorized_emails && app.authorized_emails.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-gray-200">
                          <p className="text-sm font-medium text-gray-700 mb-2">Authorized Users:</p>
                          <div className="flex flex-wrap gap-2">
                            {app.authorized_emails.map((email) => (
                              <span
                                key={email}
                                className="inline-flex items-center gap-2 px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs"
                              >
                                {email}
                                <button
                                  onClick={() => handleUnmapUser(email, app.id)}
                                  className="hover:text-red-600"
                                  title="Remove access"
                                >
                                  ×
                                </button>
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Map User Modal */}
      {showMapModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-bold text-gray-800 mb-4">
              Map User to {selectedApp?.name}
            </h3>
            <input
              type="email"
              placeholder="Enter user email"
              value={mappingEmail}
              onChange={(e) => setMappingEmail(e.target.value)}
              className="w-full px-4 py-2 border rounded-lg mb-4 focus:ring-2 focus:ring-indigo-500"
            />
            <div className="flex gap-2">
              <button
                onClick={handleMapUser}
                className="flex-1 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700"
              >
                Map User
              </button>
              <button
                onClick={() => {
                  setShowMapModal(false);
                  setMappingEmail("");
                }}
                className="flex-1 bg-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-400"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminDashboard;