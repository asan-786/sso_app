import React, { useState, useEffect } from "react";
import { Shield, LogOut, Users, Settings, Home, Edit2, Trash2, Search, ChevronDown, X, Key as KeyIcon, Copy, Lock, Unlock, Ban } from "lucide-react";

const API_URL = "http://127.0.0.1:8000/api";

// Auth hook that works with your FastAPI backend
const useAuth = () => {
  const [authData, setAuthData] = useState(null);
  
  useEffect(() => {
    // Check for token in localStorage
    const token = localStorage.getItem("access_token");
    const userStr = localStorage.getItem("user");
    
    if (token && userStr) {
      setAuthData({
        token,
        user: JSON.parse(userStr)
      });
    } else {
      // Check URL for token (from SSO redirect)
      const urlParams = new URLSearchParams(window.location.search);
      const urlToken = urlParams.get('token');
      
      if (urlToken) {
        // Verify token with backend
        fetch(`${API_URL}/auth/verify`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: urlToken })
        })
        .then(res => res.json())
        .then(data => {
          if (data.valid) {
            // Fetch user details
            fetch(`${API_URL}/auth/me`, {
              headers: { 'Authorization': `Bearer ${urlToken}` }
            })
            .then(res => res.json())
            .then(userData => {
              localStorage.setItem("access_token", urlToken);
              localStorage.setItem("user", JSON.stringify(userData));
              setAuthData({ token: urlToken, user: userData });
              // Clean URL
              window.history.replaceState({}, document.title, window.location.pathname);
            });
          }
        });
      }
    }
  }, []);
  
  const logout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user");
    setAuthData(null);
    window.location.reload();
  };
  
  return {
    user: authData?.user || null,
    token: authData?.token || null,
    logout
  };
};

const AdminDashboard = () => {
  const { user, logout, token } = useAuth();
  const [activeTab, setActiveTab] = useState("users");
  const [users, setUsers] = useState([]);
  const [apps, setApps] = useState([]);
  const [removalLogs, setRemovalLogs] = useState([]);
  const [loadingRemovals, setLoadingRemovals] = useState(false);
  
  // App form state
  const [newApp, setNewApp] = useState({ 
    name: "", 
    url: "",
    client_id: "",
    client_secret: "",
    redirect_url: ""
  });
  const [editingApp, setEditingApp] = useState(null);
  const [appKeyModal, setAppKeyModal] = useState({ visible: false, value: "", appName: "" });
  const [searchQueries, setSearchQueries] = useState({});
  const [sortOrders, setSortOrders] = useState({});
  const parseRedirectField = (value = "") =>
    value
      .split(/[\n,]+/)
      .map((entry) => entry.trim())
      .filter(Boolean);
  
  // Load users from backend
  useEffect(() => {
    if (!token) return;
    loadUsers();
  }, [token]);

  // Load apps from backend
  useEffect(() => {
    if (!token) return;
    loadApps();
    loadRemovalLogs();
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

  const loadRemovalLogs = async () => {
    try {
      setLoadingRemovals(true);
      const res = await fetch(`${API_URL}/admin/removals`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setRemovalLogs(data || []);
    } catch (err) {
      console.error("Error loading removal logs:", err);
      setRemovalLogs([]);
    } finally {
      setLoadingRemovals(false);
    }
  };

  // Add new application
  const handleAddApp = async () => {
    if (!newApp.name || !newApp.url || !newApp.redirect_url) {
      alert("Please fill required fields (Name, URL, Redirect URL)");
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
      await loadRemovalLogs();
      setNewApp({ name: "", url: "", client_id: "", client_secret: "", redirect_url: "" });
      alert("App added successfully!");
    } catch (err) {
      console.error("Error adding app:", err);
      alert("Failed to add application");
    }
  };

  // Update application
  const handleUpdateApp = async () => {
    if (!editingApp.name || !editingApp.url || !editingApp.redirect_url) {
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
          client_secret: editingApp.client_secret,
          redirect_url: editingApp.redirect_url
        }),
      });
      
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      
      await loadApps();
      await loadRemovalLogs();
      setEditingApp(null);
      alert("App updated successfully!");
    } catch (err) {
      console.error("Error updating app:", err);
      alert("Failed to update application.");
    }
  };

  const handleToggleAppBlock = async (appId, nextState) => {
    try {
      const res = await fetch(`${API_URL}/applications/${appId}/block`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ blocked: nextState })
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await loadApps();
      alert(`Application ${nextState ? "blocked" : "unblocked"}`);
    } catch (err) {
      console.error("Error toggling app block:", err);
      alert("Failed to update application block status");
    }
  };

  const handleToggleUserBlock = async (appId, email, nextState) => {
    try {
      const res = await fetch(`${API_URL}/applications/${appId}/users/block`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ email, blocked: nextState })
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await loadApps();
      alert(`User ${email} ${nextState ? "blocked" : "unblocked"} for this app`);
    } catch (err) {
      console.error("Error toggling user block:", err);
      alert("Failed to update user block status");
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

  const getFilteredUsers = (appId, usersList) => {
    if (!usersList || usersList.length === 0) return [];
    const query = (searchQueries[appId] || "").toLowerCase();
    const order = sortOrders[appId] || "asc";
    let filtered = usersList.filter((user) =>
      user.email.toLowerCase().includes(query)
    );
    filtered.sort((a, b) =>
      order === "asc"
        ? a.email.localeCompare(b.email)
        : b.email.localeCompare(a.email)
    );
    return filtered;
  };

  const handleSearchChange = (appId, value) => {
    setSearchQueries((prev) => ({ ...prev, [appId]: value }));
  };

  const clearSearch = (appId) => {
    setSearchQueries((prev) => ({ ...prev, [appId]: "" }));
  };

  const toggleSortOrder = (appId) => {
    setSortOrders((prev) => ({
      ...prev,
      [appId]: prev[appId] === "asc" ? "desc" : "asc",
    }));
  };

  const copyText = (text) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    alert("Copied to clipboard!");
  };

  const handleGenerateAppKey = async (app) => {
    try {
      const res = await fetch(`${API_URL}/applications/${app.id}/api-keys`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ name: `${app.name} API Key` })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to create API key");

      setAppKeyModal({
        visible: true,
        value: data.key_value,
        appName: app.name
      });
    } catch (err) {
      console.error("Error generating application key:", err);
      alert(err.message || "Failed to generate API key");
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
                <div className="space-y-3 mb-6 p-4 bg-gray-50 rounded-lg">
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
                    />
                    <div className="md:col-span-2">
                      <textarea
                        rows={3}
                        placeholder="Redirect URLs * (one per line, e.g., https://app.example.com/callback)"
                        value={editingApp ? editingApp.redirect_url : newApp.redirect_url}
                        onChange={(e) => editingApp
                          ? setEditingApp({ ...editingApp, redirect_url: e.target.value })
                          : setNewApp({ ...newApp, redirect_url: e.target.value })
                        }
                        className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        Supports multiple redirect URIs — add each one on a new line (similar to Google OAuth).
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button 
                      onClick={editingApp ? handleUpdateApp : handleAddApp}
                      className="bg-indigo-600 text-white px-6 py-2 rounded-lg hover:bg-indigo-700"
                    >
                      {editingApp ? "Update Application" : "Add Application"}
                    </button>
                    {editingApp && (
                      <button 
                        onClick={() => setEditingApp(null)}
                        className="bg-gray-300 text-gray-700 px-6 py-2 rounded-lg hover:bg-gray-400"
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </div>

                {/* Applications List */}
                <div className="space-y-4">
                  {apps.map((app) => {
                    const authorizedUsers = app.authorized_users || (app.authorized_emails || []).map(email => ({ email, blocked: false }));
                    const hasUsers = authorizedUsers.length > 0;
                    const filteredUsers = getFilteredUsers(app.id, authorizedUsers);
                    
                    return (
                      <div key={app.id} className="border border-gray-200 rounded-lg p-4">
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex-1">
                            <h3 className="font-semibold text-gray-800 text-lg">{app.name}</h3>
                            <p className="text-sm text-gray-500">{app.url}</p>
                          {app.redirect_url && (
                            <div className="text-xs text-gray-500 mt-2 space-y-1">
                              <p className="font-semibold text-gray-600">Redirect URLs</p>
                              <ul className="list-disc list-inside space-y-0.5">
                                {parseRedirectField(app.redirect_url).map((uri) => (
                                  <li key={`${app.id}-${uri}`} className="font-mono break-all">
                                    {uri}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                            {app.client_id && (
                              <p className="text-xs text-gray-400 mt-1">Client ID: {app.client_id}</p>
                            )}
                          {app.blocked && (
                            <p className="text-xs font-semibold text-red-600 mt-1">Application is blocked</p>
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
                              onClick={() => handleToggleAppBlock(app.id, !app.blocked)}
                              className="p-2 text-amber-600 hover:bg-amber-50 rounded-lg"
                              title={app.blocked ? "Unblock application" : "Block application"}
                            >
                              {app.blocked ? <Unlock size={18} /> : <Lock size={18} />}
                            </button>
                          <button
                            onClick={() => handleGenerateAppKey(app)}
                            className="p-2 text-indigo-600 hover:bg-indigo-50 rounded-lg"
                            title="Generate API Key"
                          >
                            <KeyIcon size={18} />
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
                        
                        {/* Authorized Users with Search and Sort */}
                        {hasUsers && (
                          <div className="mt-3 pt-3 border-t border-gray-200">
                            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between mb-3">
                              <p className="text-sm font-medium text-gray-700">
                                Authorized Users ({filteredUsers.length}/{authorizedUsers.length})
                              </p>
                              <div className="flex items-center gap-2">
                                <div className="relative">
                                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={16} />
                                  <input
                                    type="text"
                                    placeholder="Search email"
                                    value={searchQueries[app.id] || ""}
                                    onChange={(e) => handleSearchChange(app.id, e.target.value)}
                                    className="pl-9 pr-8 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                                  />
                                  {searchQueries[app.id] && (
                                    <button
                                      onClick={() => clearSearch(app.id)}
                                      className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                                    >
                                      <X size={16} />
                                    </button>
                                  )}
                                </div>
                                <button
                                  onClick={() => toggleSortOrder(app.id)}
                                  className="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
                                >
                                  Sort
                                  <ChevronDown
                                    size={16}
                                    className={`transform transition-transform ${sortOrders[app.id] === "desc" ? "rotate-180" : ""}`}
                                  />
                                </button>
                              </div>
                            </div>
                            {filteredUsers.length > 0 ? (
                              <div className="flex flex-wrap gap-2">
                                {filteredUsers.map((user) => (
                                  <span
                                    key={user.email}
                                    className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm ${
                                      user.blocked ? "bg-red-100 text-red-700" : "bg-green-100 text-green-700"
                                    }`}
                                  >
                                    {user.email}
                                    <button
                                      onClick={() => handleToggleUserBlock(app.id, user.email, !user.blocked)}
                                      className="hover:text-gray-800"
                                      title={user.blocked ? "Unblock user" : "Block user"}
                                    >
                                      {user.blocked ? <Unlock size={14} /> : <Lock size={14} />}
                                    </button>
                                  </span>
                                ))}
                              </div>
                            ) : (
                              <p className="text-sm text-gray-500 italic">No users match your search.</p>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* Removal Activity */}
                <div className="mt-8">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-lg font-bold text-gray-800">Recent Removals</h3>
                    <button
                      onClick={loadRemovalLogs}
                      className="text-sm text-indigo-600 hover:text-indigo-800"
                    >
                      Refresh
                    </button>
                  </div>
                  {loadingRemovals ? (
                    <p className="text-sm text-gray-500">Loading...</p>
                  ) : removalLogs.length === 0 ? (
                    <p className="text-sm text-gray-500">No removal activity recorded yet.</p>
                  ) : (
                    <div className="space-y-3">
                      {removalLogs.map((log) => (
                        <div key={log.id} className="p-4 border border-gray-200 rounded-lg bg-gray-50">
                          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
                            <div>
                              <p className="text-sm font-semibold text-gray-800">{log.app_name}</p>
                              <p className="text-xs text-gray-500">{log.app_id}</p>
                            </div>
                            <div className="text-sm text-gray-700">
                              <p>Removed by: {log.user_name || log.user_email}</p>
                              <p className="text-xs text-gray-500">{log.user_email}</p>
                            </div>
                            <div className="text-xs text-gray-500">
                              {new Date(log.removed_at).toLocaleString(undefined, {
                                dateStyle: "medium",
                                timeStyle: "short"
                              })}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
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