export type WidgetMode = 'floating' | 'inline' | 'popup' | 'fullscreen';
export type Theme = 'light' | 'dark' | 'auto';
export type Position = 'bottom-right' | 'bottom-left';

export interface QuickAction {
  label: string;
  prompt: string;
}

/** What the host application knows about where HavisIQ is embedded —
 * shown as-is in the Intelligence Layer's Context panel, and the seed for
 * later phases where it's actually sent to the backend to ground
 * responses. Every field is optional and falls back to a neutral label
 * (see config.ts) rather than the panel inventing or omitting the
 * section — a host that passes nothing still gets a coherent, honest
 * Context panel, just a generic one. */
export interface HavisIQContext {
  /** The host platform's own name, e.g. "myAIRA" — falls back to the
   * workspace name from `GET /workspace/config` when omitted. */
  platform?: string;
  /** The signed-in user's display name, used only for the greeting
   * ("Good morning, {userName}"). Omit rather than guess — the greeting
   * degrades to a name-free one, never a placeholder like "there". */
  userName?: string;
  /** The end user's role in the host platform, e.g. "Candidate", "Admin". */
  role?: string;
  /** A human label for the page HavisIQ was opened from, e.g. "Dashboard". */
  currentPage?: string;
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
  context?: HavisIQContext;
  /** Pixels of the host's own nav/sidebar the panel must never cover —
   * e.g. a 264px-wide left sidebar passes 264. 0 (the default) means the
   * panel fills the full width; it's still never a total takeover since
   * a host with no fixed sidebar has nothing to protect. */
  reserveLeft?: number;
}

/** `HavisIQConfig` after defaults have been merged in and validated. */
export interface ResolvedConfig {
  apiKey: string;
  apiBaseUrl: string;
  mode: WidgetMode;
  theme: Theme;
  position: Position;
  container?: string | HTMLElement;
  context: HavisIQContext;
  reserveLeft: number;
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
