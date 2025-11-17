import React, { useState, useEffect } from "react";
import { useAuth } from "./AuthContext";
import { User, LogOut, ExternalLink } from "lucide-react";
import DeveloperKeys from "./DeveloperKeys";

const API_URL = "http://127.0.0.1:8000/api";

const StudentDashboard = () => {
  const { user, logout, token, updateProfile } = useAuth();
  const [profile, setProfile] = useState({ name: user.name, email: user.email });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [appMessage, setAppMessage] = useState("");
  const [appError, setAppError] = useState("");
  const [apps, setApps] = useState([]);
  const [loading, setLoading] = useState(false);
  const [removingAppId, setRemovingAppId] = useState(null);

  // Fetch user's authorized apps
  useEffect(() => {
    fetchMyApps();
  }, []);

  const fetchMyApps = async () => {
    try {
      const response = await fetch(`${API_URL}/user/email/${user.email}/apps`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setApps(data);
      }
    } catch (err) {
      console.error("Error fetching apps:", err);
    }
  };

  const handleChange = (e) => setProfile({ ...profile, [e.target.name]: e.target.value });

  const handleUpdate = async () => {
    setLoading(true);
    setError("");
    setMessage("");

    const result = await updateProfile(profile);
    
    if (result.success) {
      setMessage("Profile updated successfully!");
      setTimeout(() => setMessage(""), 3000);
    } else {
      setError(result.message || "Update failed");
    }
    
    setLoading(false);
  };

  const handleRemoveApp = async (appId) => {
    setAppMessage("");
    setAppError("");
    setRemovingAppId(appId);
    try {
      const response = await fetch(`${API_URL}/user/apps/${appId}/remove`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`
        }
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to remove application");
      }

      const data = await response.json();
      setAppMessage(data.message || "Application removed successfully");
      fetchMyApps();
      setTimeout(() => setAppMessage(""), 4000);
    } catch (err) {
      console.error("Remove app error:", err);
      setAppError(err.message || "Unable to remove application");
      setTimeout(() => setAppError(""), 4000);
    } finally {
      setRemovingAppId(null);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-teal-100">
      {/* Header */}
      <header className="bg-white shadow-sm mb-8">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-teal-600 w-10 h-10 rounded-full flex items-center justify-center">
              <User className="text-white" size={20} />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-800">Student Dashboard</h1>
              <p className="text-sm text-gray-500">Welcome, {user.name}</p>
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

      <div className="max-w-6xl mx-auto px-4 pb-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Profile Card */}
          <div className="bg-white rounded-2xl shadow-xl p-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="bg-teal-600 w-12 h-12 rounded-full flex items-center justify-center">
                <User className="text-white" size={24} />
              </div>
              <h2 className="text-2xl font-bold text-gray-800">My Profile</h2>
            </div>

            {message && (
              <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg mb-4">
                {message}
              </div>
            )}

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
                {error}
              </div>
            )}

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
                <input
                  name="name"
                  value={profile.name}
                  onChange={handleChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input
                  name="email"
                  value={profile.email}
                  onChange={handleChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Roll Number</label>
                <input
                  value={user.rollNo || "N/A"}
                  disabled
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-100 text-gray-600"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Branch</label>
                  <input
                    value={user.branch || "N/A"}
                    disabled
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-100 text-gray-600"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Semester</label>
                  <input
                    value={user.semester || "N/A"}
                    disabled
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-100 text-gray-600"
                  />
                </div>
              </div>

              <button
                type="button"
                onClick={handleUpdate}
                disabled={loading}
                className="w-full bg-teal-600 text-white py-3 rounded-lg font-semibold hover:bg-teal-700 transition disabled:bg-gray-400"
              >
                {loading ? "Updating..." : "Update Profile"}
              </button>
            </div>
          </div>

          {/* My Applications Card - FIXED */}
          <div className="bg-white rounded-2xl shadow-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-bold text-gray-800">My Applications</h2>
              <span className="text-sm text-gray-500">{apps.length} active</span>
            </div>

            {appMessage && (
              <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-2 rounded-lg mb-4">
                {appMessage}
              </div>
            )}
            {appError && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded-lg mb-4">
                {appError}
              </div>
            )}
            
            {apps.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-gray-500 mb-2">No applications assigned yet</p>
                <p className="text-sm text-gray-400">Contact your administrator for access</p>
              </div>
            ) : (
              <div className="space-y-3">
                {apps.map((app) => (
                  <div
                    key={app.id}
                    className="p-4 border border-gray-200 rounded-lg hover:shadow-md transition bg-white"
                  >
                    <div className="flex flex-col gap-2">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-semibold text-gray-800">{app.name}</p>
                          <p className="text-sm text-gray-500 break-all">{app.url}</p>
                        </div>
                        <a
                          href={app.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-teal-600 hover:text-teal-800 text-sm"
                        >
                          Open
                          <ExternalLink size={16} />
                        </a>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <button
                          onClick={() => handleRemoveApp(app.id)}
                          disabled={removingAppId === app.id}
                          className="px-3 py-1.5 text-sm rounded-lg border border-red-200 text-red-600 hover:bg-red-50 disabled:opacity-60"
                        >
                          {removingAppId === app.id ? "Removing..." : "Remove Access"}
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Quick Info Card */}
        <div className="bg-white rounded-2xl shadow-xl p-6 mt-6">
          <h2 className="text-xl font-bold text-gray-800 mb-4">Account Information</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">Account Type</p>
              <p className="text-lg font-semibold text-gray-800 capitalize">{user.role}</p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">Authorized Apps</p>
              <p className="text-lg font-semibold text-gray-800">{apps.length}</p>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};

export default StudentDashboard;