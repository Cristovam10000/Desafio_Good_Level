
import axios, { AxiosHeaders } from "axios";
import { env } from "@/shared/config/env";

const AUTH_STORAGE_KEY = "restaurantbi.auth";

export const http = axios.create({
  baseURL: env.apiBaseUrl,
  timeout: 60000, // 60 segundos para queries pesadas (período completo)
});

http.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    try {
      const stored = window.localStorage.getItem(AUTH_STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as { accessToken?: string };
        const token = parsed?.accessToken;
        if (token) {
          let headers = config.headers;
          if (!headers) {
            headers = config.headers = new AxiosHeaders();
          }

          if (headers instanceof AxiosHeaders) {
            headers.set("Authorization", `Bearer ${token}`);
          } else {
            (headers as Record<string, unknown>)["Authorization"] = `Bearer ${token}`;
          }
        }
      }
    } catch {
      // ignore corrupted auth data
    }
  }
  return config;
});

http.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(error)
);
