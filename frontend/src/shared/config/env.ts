export const env = {
  apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000",
  appName: process.env.NEXT_PUBLIC_APP_NAME || "RestaurantBI",
} as const;
