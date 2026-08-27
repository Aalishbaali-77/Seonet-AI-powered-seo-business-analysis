import { apiClient } from "@/services/apiClient";
import type { DashboardOverview, NotificationItem, PublicConfig } from "@/types/api";

export const configApi = {
  get: () => apiClient.get<PublicConfig>("/config/").then((res) => res.data),
};

export const dashboardApi = {
  overview: () => apiClient.get<DashboardOverview>("/dashboard/overview/").then((res) => res.data),
};

export const notificationApi = {
  list: () =>
    apiClient.get<{ results: NotificationItem[] }>("/notifications/", { params: { page_size: "25" } }).then((res) => res.data.results ?? []),
  markRead: (id: string) => apiClient.post<NotificationItem>(`/notifications/${id}/read/`).then((res) => res.data),
  markAllRead: () => apiClient.post<{ updated: number }>("/notifications/read-all/").then((res) => res.data),
};
