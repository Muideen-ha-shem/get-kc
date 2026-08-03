export type WidgetMode = 'floating' | 'inline' | 'popup' | 'fullscreen';
export type Theme = 'light' | 'dark' | 'auto';
export type Position = 'bottom-right' | 'bottom-left';

export interface QuickAction {
  label: string;
  prompt: string;
}

/** Configuration passed to `HavisIQ.init({...})`. Only `apiKey` is required
 * — everything else has a sensible default (see config.ts). */
export interface HavisIQConfig {
  apiKey: string;
  apiBaseUrl?: string;
  mode?: WidgetMode;
  theme?: Theme;
  position?: Position;
  /** Required only for mode:'inline' (extension point, not implemented this phase). */
  container?: string | HTMLElement;
}

/** `HavisIQConfig` after defaults have been merged in and validated. */
export interface ResolvedConfig {
  apiKey: string;
  apiBaseUrl: string;
  mode: WidgetMode;
  theme: Theme;
  position: Position;
  container?: string | HTMLElement;
}

/** Mirrors `WorkspaceConfigSchema` in src/api/schemas.py — camelCase JSON
 * from `GET /workspace/config`. */
export interface WorkspaceConfigResponse {
  id: string;
  slug: string;
  name: string;
  logo: string | null;
  primaryColor: string | null;
  welcomeMessage: string | null;
  quickActions: QuickAction[] | null;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  text: string;
}

/** Mirrors `ChatResponse` in src/api/schemas.py (the subset the SDK uses). */
export interface ChatApiResponse {
  answer: string;
  sources: string[];
  sessionId: string | null;
}
