import React, { useState } from "react";
import { useAuth } from "./AuthContext";
import { User } from "lucide-react";

const StudentDashboard = () => {
  const { user, logout, updateProfile } = useAuth();
  const [profile, setProfile] = useState({ name: user.name, email: user.email });
  const [message, setMessage] = useState("");

  const handleChange = (e) => setProfile({ ...profile, [e.target.name]: e.target.value });

  const handleUpdate = () => {
    updateProfile(profile);
    setMessage("Profile updated successfully!");
    setTimeout(() => setMessage(""), 3000);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-teal-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md">
        <div className="text-center mb-6">
          <div className="bg-teal-600 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
            <User className="text-white" size={32} />
          </div>
          <h1 className="text-3xl font-bold text-gray-800">Student Dashboard</h1>
          <p className="text-gray-600 mt-1">Welcome, {user.name}</p>
        </div>

        <form className="space-y-4">
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

          {message && <p className="text-green-500 text-sm">{message}</p>}

          <button
            type="button"
            onClick={handleUpdate}
            className="w-full bg-teal-600 text-white py-3 rounded-lg font-semibold hover:bg-teal-700 transition"
          >
            Update Profile
          </button>
          <button
            type="button"
            onClick={logout}
            className="w-full bg-gray-200 text-gray-700 py-3 rounded-lg font-semibold hover:bg-gray-300 transition"
          >
            Logout
          </button>
        </form>
      </div>
    </div>
  );
};

export default StudentDashboard;
