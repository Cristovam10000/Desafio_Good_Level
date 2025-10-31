import { http } from "./http";
import { LoginInput } from "@/entities/auth/schemas";

export type AuthUser = {
  id: string;
  email: string;
  name: string;
  roles: string[];
  stores: number[];
};

export type LoginResponse = {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
  user: AuthUser;
};

export async function login(data: LoginInput): Promise<LoginResponse> {
  const response = await http.post<LoginResponse>("/auth/login", data);
  return response.data;
}

export async function fetchCurrentUser(): Promise<AuthUser> {
  const response = await http.get<AuthUser>("/auth/me");
  return response.data;
}
