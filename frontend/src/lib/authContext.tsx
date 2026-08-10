import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from 'react';
import { apiFetch, apiJson, getStoredToken, setStoredToken } from './apiClient';

export type AuthUser = {
  id: string;
  email: string | null;
  full_name: string | null;
};

export type AuthSessionResponse = {
  access_token: string;
  refresh_token: string;
  user: AuthUser;
};

type AuthContextValue = {
  user: AuthUser | null;
  isLoading: boolean;
  signUp: (email: string, password: string, fullName?: string) => Promise<void>;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  requestPasswordReset: (email: string) => Promise<void>;
  applySession: (session: AuthSessionResponse) => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = getStoredToken();
    if (!token) {
      setIsLoading(false);
      return;
    }
    apiJson<AuthUser>('/auth/me')
      .then(setUser)
      .catch(() => setStoredToken(null))
      .finally(() => setIsLoading(false));
  }, []);

  const signUp = useCallback(async (email: string, password: string, fullName?: string) => {
    const session = await apiJson<AuthSessionResponse>('/auth/sign-up', {
      method: 'POST',
      body: JSON.stringify({ email, password, full_name: fullName || null }),
    });
    setStoredToken(session.access_token);
    setUser(session.user);
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const session = await apiJson<AuthSessionResponse>('/auth/sign-in', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    setStoredToken(session.access_token);
    setUser(session.user);
  }, []);

  const signOut = useCallback(async () => {
    try {
      await apiFetch('/auth/sign-out', { method: 'POST' });
    } finally {
      setStoredToken(null);
      setUser(null);
    }
  }, []);

  const requestPasswordReset = useCallback(async (email: string) => {
    await apiJson('/auth/password-reset', { method: 'POST', body: JSON.stringify({ email }) });
  }, []);

  /** Stores a session obtained from a route other than /auth/sign-up or
   * /auth/sign-in (Phase 28: org signup, invite acceptance) — same
   * setStoredToken + setUser tail those two already share. */
  const applySession = useCallback((session: AuthSessionResponse) => {
    setStoredToken(session.access_token);
    setUser(session.user);
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, isLoading, signUp, signIn, signOut, requestPasswordReset, applySession }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
