import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import App from './App';
import { DashboardPage } from './pages/DashboardPage';
import { AgentDashboardPage } from './pages/AgentDashboardPage';
import { AdminDashboardPage } from './pages/admin/AdminDashboardPage';
import { AdminWorkspacesPage } from './pages/admin/AdminWorkspacesPage';
import { AdminWorkspaceDetailPage } from './pages/admin/AdminWorkspaceDetailPage';
import { AdminOnboardingWizardPage } from './pages/admin/AdminOnboardingWizardPage';
import { AdminUsersPage } from './pages/admin/AdminUsersPage';
import { AdminAgentsPage } from './pages/admin/AdminAgentsPage';
import { AdminAuditPage } from './pages/admin/AdminAuditPage';
import { AuthProvider } from './lib/authContext';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import './styles.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<App />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/agent"
            element={
              <ProtectedRoute>
                <AgentDashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <ProtectedRoute>
                <AdminDashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/workspaces"
            element={
              <ProtectedRoute>
                <AdminWorkspacesPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/workspaces/new"
            element={
              <ProtectedRoute>
                <AdminOnboardingWizardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/workspaces/:workspaceId"
            element={
              <ProtectedRoute>
                <AdminWorkspaceDetailPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/users"
            element={
              <ProtectedRoute>
                <AdminUsersPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/agents"
            element={
              <ProtectedRoute>
                <AdminAgentsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/audit"
            element={
              <ProtectedRoute>
                <AdminAuditPage />
              </ProtectedRoute>
            }
          />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>
);
