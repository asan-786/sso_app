import React, { createContext, useState, useContext, useEffect } from "react";

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const savedUser = sessionStorage.getItem("user");
    if (savedUser) setUser(JSON.parse(savedUser));
    setLoading(false);
  }, []);

  const login = (email, password) => {
    if (email === "admin@example.com" && password === "admin123") {
      const newUser = { id: 1, name: "Admin User", email, role: "admin" };
      setUser(newUser);
      sessionStorage.setItem("user", JSON.stringify(newUser));
      return { success: true };
    }
    if (email === "student@example.com" && password === "student123") {
      const newUser = { id: 2, name: "Student User", email, role: "student" };
      setUser(newUser);
      sessionStorage.setItem("user", JSON.stringify(newUser));
      return { success: true };
    }
    return { success: false, message: "Invalid credentials" };
  };

  const logout = () => {
    setUser(null);
    sessionStorage.removeItem("user");
  };

  const register = (userData) => {
    const newUser = { ...userData, role: "student" };
    setUser(newUser);
    sessionStorage.setItem("user", JSON.stringify(newUser));
    return { success: true };
  };

  const updateProfile = (updatedData) => {
    const updatedUser = { ...user, ...updatedData };
    setUser(updatedUser);
    sessionStorage.setItem("user", JSON.stringify(updatedUser));
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, register, updateProfile }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
