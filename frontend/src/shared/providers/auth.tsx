
"use client";

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { LoginResponse } from "@/shared/api/auth";
import { http } from "@/shared/api/http";
import { AuthState, clearAuth, persistAuth, readAuth, writeAuthState } from "@/shared/lib/auth-storage";

type AuthContextValue = {
  auth: AuthState | null;
  isReady: boolean;
  setAuthState: (state: AuthState | null) => void;
  applyLogin: (response: LoginResponse) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  // Inicializar o estado com validação de expiração
  const [auth, setAuth] = useState<AuthState | null>(() => {
    if (typeof window === "undefined") return null;
    const stored = readAuth();
    if (!stored) return null;
    
    // Verificar se o token não expirou
    if (stored.expiresAt && stored.expiresAt <= Date.now()) {
      clearAuth();
      return null;
    }
    
    return stored;
  });
  const isReady = true; // Sempre pronto já que o estado inicial é calculado de forma síncrona

  useEffect(() => {
    if (auth) {
      http.defaults.headers.common.Authorization = `Bearer ${auth.accessToken}`;
      writeAuthState(auth);
    } else {
      delete http.defaults.headers.common.Authorization;
      clearAuth();
    }
  }, [auth]);

  const value = useMemo<AuthContextValue>(
    () => ({
      auth,
      isReady,
      setAuthState: setAuth,
      applyLogin: (response: LoginResponse) => setAuth(persistAuth(response)),
      logout: () => setAuth(null),
    }),
    [auth, isReady]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuthContext() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuthContext deve ser usado dentro de AuthProvider");
  }
  return ctx;
}
