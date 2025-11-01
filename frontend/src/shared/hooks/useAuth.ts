

import type { LoginResponse } from "@/shared/api/auth";
import type { AuthState } from "@/shared/lib/auth-storage";
import { useAuthContext } from "@/shared/providers/auth";

type UseAuth = {
  auth: AuthState | null;
  isAuthenticated: boolean;
  isReady: boolean;
  applyLogin: (payload: LoginResponse) => void;
  logout: () => void;
};

export function useAuth(): UseAuth {
  const { auth, isReady, applyLogin, logout } = useAuthContext();
  return {
    auth,
    isAuthenticated: Boolean(auth?.accessToken),
    isReady,
    applyLogin,
    logout,
  };
}
