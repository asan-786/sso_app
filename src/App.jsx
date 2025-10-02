import React, { useState } from "react";
import { useAuth } from "./components/AuthContext";
import LoginPage from "./components/LoginPage";
import RegisterPage from "./components/RegisterPage";
import StudentDashboard from "./components/StudentDashboard";
import AdminDashboard from "./components/AdminDashboard";

const App = () => {
  const { user, loading } = useAuth();
  const [currentPage, setCurrentPage] = useState("login");

  if (loading) return <div>Loading...</div>;

  if (user) {
    return user.role === "admin" ? <AdminDashboard /> : <StudentDashboard />;
  }

  return currentPage === "register" ? (
    <RegisterPage onNavigate={setCurrentPage} />
  ) : (
    <LoginPage onNavigate={setCurrentPage} />
  );
};

export default App;