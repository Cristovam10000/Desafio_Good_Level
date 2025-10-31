
"use client";

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { LoginResponse } from "@/shared/api/auth";
import { http } from "@/shared/api/http";
import { AuthState, clearAuth, persistAuth, readAuth, writeAuthState } from "@/shared/lib/auth-storage";

type AuthContextValue = {
  auth: AuthState | null;
  setAuthState: (state: AuthState | null) => void;
  applyLogin: (response: LoginResponse) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<AuthState | null>(() => readAuth());

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
      setAuthState: setAuth,
      applyLogin: (response: LoginResponse) => setAuth(persistAuth(response)),
      logout: () => setAuth(null),
    }),
    [auth]
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
