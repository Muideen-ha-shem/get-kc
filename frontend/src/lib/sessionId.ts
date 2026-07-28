const SESSION_ID_KEY = 'havisiq_session_id';

/** A per-browser-tab-session id sent with every /chat request so the
 * backend's SessionContext can resolve pronouns ("it", "this") and stay
 * aware of what's already been discussed (Phase 20, Workstream 3).
 * Session storage (not local storage) so a fresh tab starts a fresh
 * conversation context, matching the backend's TTL-based session model. */
export function getSessionId(): string {
  let id = sessionStorage.getItem(SESSION_ID_KEY);
  if (!id) {
    id = crypto.randomUUID();
    sessionStorage.setItem(SESSION_ID_KEY, id);
  }
  return id;
}

export function setSessionId(id: string): void {
  sessionStorage.setItem(SESSION_ID_KEY, id);
}
