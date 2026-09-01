import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { api, clearTokens, setTokens } from "@/services/api";
import type { TokenResponse, User } from "@/types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string, mfaCode?: string) => Promise<User>;
  register: (email: string, password: string, fullName: string) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const applyTokens = useCallback((tokens: TokenResponse) => {
    setTokens(tokens);
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function bootstrap() {
      try {
        const me = await api.me();
        if (!cancelled) setUser(me);
      } catch {
        clearTokens();
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(
    async (email: string, password: string, mfaCode?: string) => {
      const tokens = await api.login(email, password, mfaCode);
      applyTokens(tokens);
      const me = await api.me();
      setUser(me);
      return me;
    },
    [applyTokens],
  );

  const register = useCallback(
    async (email: string, password: string, fullName: string) => {
      const tokens = await api.register(email, password, fullName);
      applyTokens(tokens);
      const me = await api.me();
      setUser(me);
      return me;
    },
    [applyTokens],
  );

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      // Best-effort: clear locally even if server call fails
    }
    clearTokens();
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    const me = await api.me();
    setUser(me);
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, register, logout, refreshUser }),
    [user, loading, login, register, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
