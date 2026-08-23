import { BrowserRouter, Route, Routes } from "react-router-dom";

import { Navbar } from "@/components/Navbar";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { ToastProvider } from "@/context/ToastContext";
import { I18nProvider } from "@/i18n";
import { Admin } from "@/pages/Admin";
import { AutonomousPipeline } from "@/pages/AutonomousPipeline";
import { CodeUpload } from "@/pages/CodeUpload";
import { Dashboard } from "@/pages/Dashboard";
import { ForgotPassword } from "@/pages/ForgotPassword";
import { JobDetails } from "@/pages/JobDetails";
import { Jobs } from "@/pages/Jobs";
import { Login } from "@/pages/Login";
import { NotFound } from "@/pages/NotFound";
import { Organizations } from "@/pages/Organizations";
import { ProjectDetails } from "@/pages/ProjectDetails";
import { Projects } from "@/pages/Projects";
import { Register } from "@/pages/Register";
import { ResetPassword } from "@/pages/ResetPassword";
import { Settings } from "@/pages/Settings";

function Shell() {
  const { user } = useAuth();
  return (
    <div className="relative min-h-screen bg-ambient">
      <div className="pointer-events-none fixed inset-0 bg-grid" aria-hidden="true" />
      <div
        className="pointer-events-none fixed inset-0 opacity-90"
        style={{
          backgroundImage:
            "radial-gradient(900px 480px at 12% -8%, rgba(16,185,129,0.10), transparent 62%), radial-gradient(820px 420px at 92% -12%, rgba(6,182,212,0.08), transparent 60%)",
        }}
        aria-hidden="true"
      />
      <div className="pointer-events-none fixed inset-x-0 top-0 h-24 bg-gradient-to-b from-primary/10 to-transparent" aria-hidden="true" />
      <div className="noise" aria-hidden="true" />
      <div className="relative">
        {user && <Navbar />}
        <main>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />

            <Route
              path="/"
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
