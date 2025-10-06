import React, { createContext, useState, useContext, useEffect } from "react";

const AuthContext = createContext();
const API_URL = "http://127.0.0.1:8000/api";

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(null);

  // Load user from localStorage on mount
  useEffect(() => {
    const savedToken = localStorage.getItem("access_token");
    const savedUser = localStorage.getItem("user");
    
    if (savedToken && savedUser) {
      setToken(savedToken);
      setUser(JSON.parse(savedUser));
    }
    setLoading(false);
  }, []);

  // Refresh access token using refresh token
  const refreshAccessToken = async () => {
    const refreshToken = localStorage.getItem("refresh_token");
    if (!refreshToken) return false;

    try {
      const response = await fetch(`${API_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!response.ok) {
        // Refresh token expired, logout
        logout();
        return false;
      }

      const data = await response.json();
      localStorage.setItem("access_token", data.access_token);
      setToken(data.access_token);
      return true;
    } catch (error) {
      console.error("Token refresh error:", error);
      logout();
      return false;
    }
  };

  // Login function
  const login = async (email, password) => {
    try {
      const response = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const error = await response.json();
        return { success: false, message: error.detail || "Login failed" };
      }

      const data = await response.json();
      
      // Save BOTH access token and refresh token
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      localStorage.setItem("user", JSON.stringify(data.user));
      
      setToken(data.access_token);
      setUser(data.user);
      
      return { success: true };
    } catch (error) {
      console.error("Login error:", error);
      return { success: false, message: "Network error. Please try again." };
    }
  };

  // Register function
  const register = async (userData) => {
    try {
      const response = await fetch(`${API_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(userData),
      });

      if (!response.ok) {
        const error = await response.json();
        return { success: false, message: error.detail || "Registration failed" };
      }

      const data = await response.json();
      
      // Save BOTH access token and refresh token
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      localStorage.setItem("user", JSON.stringify(data.user));
      
      setToken(data.access_token);
      setUser(data.user);
      
      return { success: true };
    } catch (error) {
      console.error("Register error:", error);
      return { success: false, message: "Network error. Please try again." };
    }
  };

  // Logout function
  const logout = async () => {
    try {
      if (token) {
        await fetch(`${API_URL}/auth/logout`, {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${token}`,
          },
        });
      }
    } catch (error) {
      console.error("Logout error:", error);
    } finally {
      // Clear ALL stored data including refresh token
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("user");
      setToken(null);
      setUser(null);
    }
  };

  // Update profile function
  const updateProfile = async (updatedData) => {
    try {
      const response = await fetch(`${API_URL}/profile`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify(updatedData),
      });

      if (!response.ok) {
        const error = await response.json();
        return { success: false, message: error.detail || "Update failed" };
      }

      // Update local user data
      const updatedUser = { ...user, ...updatedData };
      setUser(updatedUser);
      localStorage.setItem("user", JSON.stringify(updatedUser));
      
      return { success: true };
    } catch (error) {
      console.error("Update profile error:", error);
      return { success: false, message: "Network error. Please try again." };
    }
  };

  // Helper function to make authenticated requests with automatic token refresh
  const fetchWithAuth = async (endpoint, options = {}) => {
    if (!token) {
      throw new Error("No authentication token");
    }

    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers: {
        ...options.headers,
        "Authorization": `Bearer ${token}`,
      },
    });

    // If token expired, try to refresh
    if (response.status === 401) {
      const refreshed = await refreshAccessToken();
      
      if (refreshed) {
        // Retry the request with new token
        const newToken = localStorage.getItem("access_token");
        return await fetch(`${API_URL}${endpoint}`, {
          ...options,
          headers: {
            ...options.headers,
            "Authorization": `Bearer ${newToken}`,
          },
        });
      } else {
        // Refresh failed, logout
        logout();
        throw new Error("Session expired. Please login again.");
      }
    }

    return response;
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        login,
        logout,
        register,
        updateProfile,
        fetchWithAuth,
        refreshAccessToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
};