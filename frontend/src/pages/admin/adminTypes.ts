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
  target_resolution_rate: number | null;
  target_response_minutes: number | null;
  target_resolution_minutes: number | null;
  target_csat: number | null;
  aux_categories: Record<string, string> | null;
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

export type WorkspaceAgentBreakdown = {
  id: string;
  name: string;
  department: string;
  status: string;
  current_workload: number;
  clock_in_at: string | null;
  current_aux: string | null;
  current_aux_started_at: string | null;
  avg_first_response_minutes: number | null;
};

export type WorkspacePerformanceTargets = {
  resolution_rate: number | null;
  response_minutes: number | null;
  resolution_minutes: number | null;
  csat: number | null;
};

export type WorkspaceAdherenceEntry = {
  agent_id: string;
  scheduled_start: string;
  actual_clock_in_at: string;
  difference_minutes: number;
};

export type WorkspaceReport = WorkspaceAnalytics & {
  resolution_rate: number | null;
  average_resolution_minutes: number | null;
  avg_first_response_minutes: number | null;
  department_activity: Record<string, number>;
  frustrated_conversation_count: number;
  agents: WorkspaceAgentBreakdown[];
  requested_products: Record<string, number>;
  ai_resolved_rate_estimate: number | null;
  ai_resolved_rate_caveat: string;
  knowledge_gaps: string[] | null;
  frequently_searched_topics: string[] | null;
  insufficient_evidence_questions: string[] | null;
  source_failures: string[] | null;
  knowledge_tracking_note: string;
  clocked_in_count: number;
  available_count: number;
  aux_breakdown: Record<string, number>;
  aux_time_by_category: Record<string, number>;
  performance_targets: WorkspacePerformanceTargets;
  adherence: WorkspaceAdherenceEntry[] | null;
  adherence_note: string | null;
  csat_note: string;
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
