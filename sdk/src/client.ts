import type { ChatApiResponse, ResolvedConfig, WorkspaceConfigResponse } from './types';

// Distinct from the React frontend's 'havisiq_session_id' (frontend/src/lib/sessionId.ts)
// so an embed never collides sessions with a same-page React app instance.
const SESSION_ID_KEY = 'havisiq_sdk_session_id';

/** A per-browser-tab-session id sent with every /chat request, mirroring
 * frontend/src/lib/sessionId.ts's approach (sessionStorage, not
 * localStorage — a fresh tab starts a fresh conversation). */
export function getOrCreateSessionId(): string {
  let id = sessionStorage.getItem(SESSION_ID_KEY);
  if (!id) {
    id = crypto.randomUUID();
    sessionStorage.setItem(SESSION_ID_KEY, id);
  }
  return id;
}

class HavisIQApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'HavisIQApiError';
  }
}

export async function fetchWorkspaceConfig(config: ResolvedConfig): Promise<WorkspaceConfigResponse> {
  const response = await fetch(`${config.apiBaseUrl}/workspace/config`, {
    method: 'GET',
    headers: { 'X-Api-Key': config.apiKey },
  });
  if (!response.ok) {
    throw new HavisIQApiError(response.status, `Failed to load workspace config (${response.status})`);
  }
  return (await response.json()) as WorkspaceConfigResponse;
}

export async function sendChatMessage(
  config: ResolvedConfig,
  message: string,
  sessionId: string,
): Promise<ChatApiResponse> {
  const response = await fetch(`${config.apiBaseUrl}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Api-Key': config.apiKey,
    },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  if (!response.ok) {
    throw new HavisIQApiError(response.status, `Chat request failed (${response.status})`);
  }
  const data = await response.json();
  return {
    answer: data.answer as string,
    sources: (data.sources as string[]) ?? [],
    sessionId: (data.session_id as string | null) ?? null,
  };
}

export { HavisIQApiError };
