import type { AuthUser, LoginResponse } from "@/shared/api/auth";

const STORAGE_KEY = "restaurantbi.auth";

export type AuthState = {
  accessToken: string;
  refreshToken: string;
  expiresAt: number;
  user: AuthUser;
};

function isValidPayload(payload: unknown): payload is AuthState {
  if (!payload || typeof payload !== "object") return false;
  const candidate = payload as Partial<AuthState>;
  return (
    typeof candidate.accessToken === "string" &&
    typeof candidate.refreshToken === "string" &&
    typeof candidate.expiresAt === "number" &&
    candidate.user != null
  );
}

export function readAuth(): AuthState | null {
  if (typeof window === "undefined") return null;
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (!stored) return null;
    const parsed = JSON.parse(stored);
    if (!isValidPayload(parsed)) return null;
    
    // Verificar se o token não expirou
    if (parsed.expiresAt && parsed.expiresAt < Date.now()) {
      // Token expirado - limpar localStorage
      window.localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    
    return parsed;
  } catch {
    return null;
  }
}

export function persistAuth(response: LoginResponse): AuthState {
  const auth: AuthState = {
    accessToken: response.access_token,
    refreshToken: response.refresh_token,
    expiresAt: Date.now() + response.expires_in * 1000,
    user: response.user,
  };
  if (typeof window !== "undefined") {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(auth));
  }
  return auth;
}

export function writeAuthState(state: AuthState | null) {
  if (typeof window === "undefined") return;
  if (!state) {
    window.localStorage.removeItem(STORAGE_KEY);
  } else {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }
}

export function clearAuth() {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(STORAGE_KEY);
  }
}
