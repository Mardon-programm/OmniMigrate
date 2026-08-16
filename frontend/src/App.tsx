import { BrowserRouter, Route, Routes } from "react-router-dom";

import { Navbar } from "@/components/Navbar";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { ToastProvider } from "@/context/ToastContext";
import { I18nProvider } from "@/i18n";
import { CodeUpload } from "@/pages/CodeUpload";
import { Dashboard } from "@/pages/Dashboard";
import { JobDetails } from "@/pages/JobDetails";
import { Jobs } from "@/pages/Jobs";
import { Login } from "@/pages/Login";
import { NotFound } from "@/pages/NotFound";
import { ProjectDetails } from "@/pages/ProjectDetails";
import { Projects } from "@/pages/Projects";
import { Register } from "@/pages/Register";

function Shell() {
  const { user } = useAuth();
  return (
    <div className="relative min-h-screen bg-ambient">
      <div className="pointer-events-none fixed inset-0 bg-grid" aria-hidden="true" />
      <div className="pointer-events-none fixed inset-x-0 top-0 h-24 bg-gradient-to-b from-primary/10 to-transparent" aria-hidden="true" />
      <div className="relative">
        {user && <Navbar />}
        <main>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

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
