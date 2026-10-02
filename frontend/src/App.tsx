import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { Navbar } from "@/components/Navbar";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { ToastProvider } from "@/context/ToastContext";
import { I18nProvider } from "@/i18n";
import { Admin } from "@/pages/Admin";
import { AutonomousPipeline } from "@/pages/AutonomousPipeline";
import { CodeUpload } from "@/pages/CodeUpload";
import { Dashboard } from "@/pages/Dashboard";
import { Demo } from "@/pages/Demo";
import { ForgotPassword } from "@/pages/ForgotPassword";
import { JobDetails } from "@/pages/JobDetails";
import { Jobs } from "@/pages/Jobs";
import { Landing } from "@/pages/Landing";
import { Login } from "@/pages/Login";
import { NotFound } from "@/pages/NotFound";
import { Organizations } from "@/pages/Organizations";
import { ProjectDetails } from "@/pages/ProjectDetails";
import { Projects } from "@/pages/Projects";
import { Register } from "@/pages/Register";
import { ResetPassword } from "@/pages/ResetPassword";
import { Settings } from "@/pages/Settings";

function Shell() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-bg-primary">
        <div className="text-text-tertiary">Loading...</div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen bg-bg-primary">
      <div className="relative">
        {user && <Navbar />}
        <main id="main-content">
          <Routes>
            {/* Public routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />

            {/* Demo page - public */}
            <Route path="/demo" element={<Demo />} />

            {/* Landing page for unauthenticated users */}
            <Route
              path="/"
              element={user ? <Navigate to="/dashboard" replace /> : <Landing />}
            />

            {/* Protected routes */}
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/projects"
              element={
                <ProtectedRoute>
                  <Projects />
                </ProtectedRoute>
              }
            />
            <Route
              path="/projects/:id"
              element={
                <ProtectedRoute>
                  <ProjectDetails />
                </ProtectedRoute>
              }
            />
            <Route
              path="/upload"
              element={
                <ProtectedRoute>
                  <CodeUpload />
                </ProtectedRoute>
              }
            />
            <Route
              path="/jobs"
              element={
                <ProtectedRoute>
                  <Jobs />
                </ProtectedRoute>
              }
            />
            <Route
              path="/jobs/:id"
              element={
                <ProtectedRoute>
                  <JobDetails />
                </ProtectedRoute>
              }
            />
            <Route
              path="/autonomous"
              element={
                <ProtectedRoute>
                  <AutonomousPipeline />
                </ProtectedRoute>
              }
            />
            <Route
              path="/organizations"
              element={
                <ProtectedRoute>
                  <Organizations />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin"
              element={
                <ProtectedRoute>
                  <Admin />
                </ProtectedRoute>
              }
            />
            <Route
              path="/settings"
              element={
                <ProtectedRoute>
                  <Settings />
                </ProtectedRoute>
              }
            />

            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <I18nProvider>
        <ToastProvider>
          <AuthProvider>
            <Shell />
          </AuthProvider>
        </ToastProvider>
      </I18nProvider>
    </BrowserRouter>
  );
}
