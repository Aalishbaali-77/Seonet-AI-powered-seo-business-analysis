import { apiClient } from "@/services/apiClient";
import type { CurrentUser } from "@/types/api";

export const authApi = {
  login: (payload: { email: string; password: string }) =>
    apiClient.post<CurrentUser>("/auth/login/", payload).then((res) => res.data),
  register: (payload: { email: string; password: string; name?: string; first_name?: string; last_name?: string; company_name?: string }) =>
    apiClient.post<CurrentUser>("/auth/register/", payload).then((res) => res.data),
  logout: () => apiClient.post("/auth/logout/"),
  me: () => apiClient.get<CurrentUser>("/auth/me/").then((res) => res.data),
  updateProfile: (payload: { first_name?: string; last_name?: string; theme_preference?: "light" | "dark" | "system" }) =>
    apiClient.patch<CurrentUser>("/auth/me/", payload).then((res) => res.data),
  requestPasswordReset: (email: string) => apiClient.post("/auth/password/reset/", { email }),
  confirmPasswordReset: (payload: { uid: string; token: string; password: string }) =>
    apiClient.post("/auth/password/reset/confirm/", payload),
};
