import React, { useState, useEffect } from "react";
import { useAuth } from "./components/AuthContext";
import LoginPage from "./components/LoginPage";
import RegisterPage from "./components/RegisterPage";
import StudentDashboard from "./components/StudentDashboard";
import AdminDashboard from "./components/AdminDashboard";

const App = () => {
  const { user, loading } = useAuth();
  const [currentPage, setCurrentPage] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get("view") === "register" ? "register" : "login";
  });

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (currentPage === "register") {
      params.set("view", "register");
    } else {
      params.delete("view");
    }
    const query = params.toString();
    const newUrl = `${window.location.pathname}${query ? `?${query}` : ""}`;
    window.history.replaceState({}, "", newUrl);
  }, [currentPage]);

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