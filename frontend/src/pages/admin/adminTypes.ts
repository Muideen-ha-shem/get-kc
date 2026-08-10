export type WorkspaceAdmin = {
  id: string;
  slug: string;
  name: string;
  host: string | null;
  is_active: boolean;
  logo: string | null;
  primary_color: string | null;
  welcome_message: string | null;
  quick_actions: { label: string; prompt: string }[] | null;
  archived_at: string | null;
  deleted_at: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type WorkspaceSettings = {
  workspace_id: string;
  ai_enabled: boolean;
  confidence_threshold: number | null;
  live_search_enabled: boolean;
  human_escalation_enabled: boolean;
  ai_personality: string | null;
  welcome_prompt: string | null;
  chat_enabled: boolean;
  offline_mode: boolean;
  greeting_message: string | null;
  working_hours: Record<string, unknown> | null;
  escalation_timeout_minutes: number | null;
  auto_assignment_enabled: boolean;
  secondary_color: string | null;
  chat_avatar: string | null;
  company_name: string | null;
  footer_text: string | null;
};

export type WorkspaceProduct = { product_id: string; enabled: boolean };
export type FeatureFlag = { flag_key: string; enabled: boolean };

export type WorkspaceAnalytics = {
  conversation_count: number;
  escalation_count: number;
  escalation_status_breakdown: Record<string, number>;
  appointment_count: number;
  saved_recommendation_count: number;
  saved_comparison_count: number;
  feedback_helpful_count: number;
  feedback_not_helpful_count: number;
};

export type PlatformDashboard = {
  total_workspace_count: number;
  active_workspace_count: number;
  total_conversation_count: number;
  total_escalation_count: number;
  total_agent_count: number;
};

export type AuditLogEntry = {
  id: string;
  workspace_id: string | null;
  actor_auth_user_id: string;
  action: string;
  metadata: Record<string, unknown> | null;
  created_at: string | null;
};

export type AdminUser = {
  id: string;
  email: string | null;
  full_name: string | null;
};

export type SupportAgent = {
  id: string;
  workspace_id: string;
  name: string;
  email: string;
  department: string;
  status: 'available' | 'away' | 'offline';
  created_at: string | null;
};

export type AgentPerformance = {
  agent_id: string;
  active_chats: number;
  resolved_today: number;
  satisfaction_score: number | null;
};
