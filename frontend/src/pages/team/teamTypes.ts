export type InvitationRole = 'workspace_admin' | 'agent';
export type InvitationStatus = 'pending' | 'accepted' | 'revoked';
export type Department = 'Support' | 'Sales' | 'Solution Architect' | 'Customer Success' | 'General';

export type WorkspaceInvitation = {
  id: string;
  workspace_id: string;
  email: string;
  role: InvitationRole;
  department: Department | null;
  invited_by: string;
  status: InvitationStatus;
  created_at: string | null;
  accepted_at: string | null;
};
