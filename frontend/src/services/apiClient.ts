import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

import { env } from "@/config/env";
import type { ApiErrorBody } from "@/types/api";

export class ApiError extends Error {
  code: string;
  details: Record<string, unknown>;
  requestId: string;
  status: number;

  constructor(payload: ApiErrorBody["error"], status: number) {
    super(payload.message);
    this.name = "ApiError";
    this.code = payload.code;
    this.details = payload.details ?? {};
    this.requestId = payload.request_id;
    this.status = status;
  }
}

export const apiClient = axios.create({
  baseURL: `${env.apiUrl}/api/v1`,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.request.use((config) => {
  if (typeof FormData !== "undefined" && config.data instanceof FormData) {
    config.headers.delete("Content-Type");
  }
  const url = config.url ?? "";
  if (/\/auth\/(login|register|refresh|password)/.test(url) || url.includes("/platform/")) {
    return config;
  }
  const tenantId = typeof window !== "undefined" ? window.localStorage.getItem("seonet.tenant") : null;
  if (tenantId) {
    config.headers.set("X-Tenant-ID", tenantId);
  }
  return config;
});

let refreshing: Promise<void> | null = null;

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiErrorBody>) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined;
    const status = error.response?.status;
    if (status === 401 && original && !original._retry && !original.url?.includes("/auth/")) {
      original._retry = true;
      refreshing ??= apiClient.post("/auth/refresh/").then(() => undefined);
      try {
        await refreshing;
        refreshing = null;
        return apiClient(original);
      } catch {
        refreshing = null;
      }
    }
    const data = error.response?.data;
    if (data?.error) {
      throw new ApiError(data.error, status ?? 500);
    }
    throw error;
  },
);
