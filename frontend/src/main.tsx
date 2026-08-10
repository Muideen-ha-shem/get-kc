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
import { KnowledgeManagementPage } from './pages/knowledge/KnowledgeManagementPage';
import { WorkspaceTeamPage } from './pages/team/WorkspaceTeamPage';
import { ResetPasswordPage } from './pages/auth/ResetPasswordPage';
import { OrgSignupPage } from './pages/signup/OrgSignupPage';
import { AcceptInvitePage } from './pages/signup/AcceptInvitePage';
import { AuthProvider } from './lib/authContext';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import './styles.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<App />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route path="/signup" element={<OrgSignupPage />} />
          <Route path="/accept-invite" element={<AcceptInvitePage />} />
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
            path="/admin/workspaces/:workspaceId/knowledge"
            element={
              <ProtectedRoute>
                <KnowledgeManagementPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/workspaces/:workspaceId/team"
            element={
              <ProtectedRoute>
                <WorkspaceTeamPage />
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
