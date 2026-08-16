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
  login: (email: string, password: string) => Promise<User>;
  register: (email: string, password: string, fullName: string) => Promise<User>;
  logout: () => void;
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
    async (email: string, password: string) => {
      const tokens = await api.login(email, password);
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

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, register, logout }),
    [user, loading, login, register, logout],
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
