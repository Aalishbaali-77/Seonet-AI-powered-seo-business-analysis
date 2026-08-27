import { apiClient } from "@/services/apiClient";
import type {
  Paginated,
  PaymentGateway,
  LeadSource,
  PlanPackage,
  PlatformAdmin,
  PlatformInvoice,
  PlatformOverview,
  PlatformSubscription,
  PlatformTenant,
  ProductModule,
  PlatformBranding,
  AppearanceAssetSlot,
  LandingContent,
  PlatformPromptLog,
  PlatformAskLog,
  PlatformPageLog,
  PlatformActivityLog,
} from "@/types/api";

export const platformAdminApi = {
  overview: () => apiClient.get<PlatformOverview>("/platform/overview/").then((res) => res.data),
  platformAdmins: () => apiClient.get<Paginated<PlatformAdmin>>("/platform/admins/").then((res) => res.data),
  invitePlatformAdmin: (payload: { email: string; first_name?: string; last_name?: string }) =>
    apiClient.post<PlatformAdmin>("/platform/admins/", payload).then((res) => res.data),
  setPlatformAdminActive: (id: string, is_active: boolean) =>
    apiClient.patch<PlatformAdmin>(`/platform/admins/${id}/`, { is_active }).then((res) => res.data),
  removePlatformAdmin: (id: string) => apiClient.delete(`/platform/admins/${id}/`),
  resetPlatformAdminPassword: (id: string) => apiClient.post<{ ok: boolean }>(`/platform/admins/${id}/reset-password/`).then((res) => res.data),
  tenants: () => apiClient.get<Paginated<PlatformTenant>>("/platform/tenants/").then((res) => res.data),
  tenant: (id: string) => apiClient.get<PlatformTenant>(`/platform/tenants/${id}/`).then((res) => res.data),
  createTenant: (payload: {
    name: string;
    owner_email: string;
    owner_first_name?: string;
    owner_last_name?: string;
    owner_password?: string;
    plan_id?: string;
  }) => apiClient.post<PlatformTenant>("/platform/tenants/", payload).then((res) => res.data),
  updateTenant: (id: string, payload: Partial<Pick<PlatformTenant, "status" | "name" | "feature_flags">>) =>
    apiClient.patch<PlatformTenant>(`/platform/tenants/${id}/`, payload).then((res) => res.data),
  deleteTenant: (id: string) => apiClient.delete(`/platform/tenants/${id}/`),
  assignPlan: (id: string, payload: { plan_id: string; status?: string }) =>
    apiClient.post(`/platform/tenants/${id}/plan/`, payload).then((res) => res.data),
  assignModule: (id: string, payload: { module_code: string; is_enabled: boolean }) =>
    apiClient.post<PlatformTenant>(`/platform/tenants/${id}/modules/`, payload).then((res) => res.data),
  modules: () => apiClient.get<Paginated<ProductModule>>("/platform/modules/").then((res) => res.data),
  createModule: (payload: Partial<ProductModule> & { code: string; name: string }) =>
    apiClient.post<ProductModule>("/platform/modules/", payload).then((res) => res.data),
  updateModule: (id: string, payload: Partial<ProductModule>) =>
    apiClient.patch<ProductModule>(`/platform/modules/${id}/`, payload).then((res) => res.data),
  deleteModule: (id: string) => apiClient.delete(`/platform/modules/${id}/`),
  createFeature: (moduleId: string, payload: { code: string; name: string; description?: string; is_active?: boolean }) =>
    apiClient.post<ProductModule>(`/platform/modules/${moduleId}/features/`, payload).then((res) => res.data),
  updateFeature: (id: string, payload: { name?: string; description?: string; is_active?: boolean }) =>
    apiClient.patch(`/platform/features/${id}/`, payload).then((res) => res.data),
  deleteFeature: (id: string) => apiClient.delete(`/platform/features/${id}/`),
  packages: () => apiClient.get<Paginated<PlanPackage>>("/platform/packages/").then((res) => res.data),
  createPackage: (payload: Partial<PlanPackage> & { code: string; name: string; module_codes?: string[] }) =>
    apiClient.post<PlanPackage>("/platform/packages/", payload).then((res) => res.data),
  updatePackage: (id: string, payload: Partial<PlanPackage> & { module_codes?: string[] }) =>
    apiClient.patch<PlanPackage>(`/platform/packages/${id}/`, payload).then((res) => res.data),
  deletePackage: (id: string) => apiClient.delete(`/platform/packages/${id}/`),
  gateways: () => apiClient.get<Paginated<PaymentGateway>>("/platform/gateways/").then((res) => res.data),
  createGateway: (payload: Partial<PaymentGateway> & { code: string; provider: string; display_name: string }) =>
    apiClient.post<PaymentGateway>("/platform/gateways/", payload).then((res) => res.data),
  updateGateway: (id: string, payload: Record<string, unknown>) =>
    apiClient.patch<PaymentGateway>(`/platform/gateways/${id}/`, payload).then((res) => res.data),
  deleteGateway: (id: string) => apiClient.delete(`/platform/gateways/${id}/`),
  leadSources: () => apiClient.get<Paginated<LeadSource>>("/platform/lead-sources/").then((res) => res.data),
  updateLeadSource: (
    id: string,
    payload: {
      api_key?: string;
      is_enabled?: boolean;
      display_name?: string;
      purpose?: string;
      setup_hint?: string;
      model?: string;
      search_url?: string;
      homepage_url?: string;
    },
  ) => apiClient.patch<LeadSource>(`/platform/lead-sources/${id}/`, payload).then((res) => res.data),
  testLeadSource: (id: string) =>
    apiClient.post<{ ok: boolean; sample_count: number; provider: string; message?: string }>(`/platform/lead-sources/${id}/test/`).then((res) => res.data),
  invoices: () => apiClient.get<Paginated<PlatformInvoice>>("/platform/invoices/").then((res) => res.data),
  createInvoice: (payload: { tenant_id: string; description: string; amount: string; notes?: string }) =>
    apiClient.post<PlatformInvoice>("/platform/invoices/", payload).then((res) => res.data),
  updateInvoice: (id: string, payload: { description?: string; amount?: string; notes?: string }) =>
    apiClient.patch<PlatformInvoice>(`/platform/invoices/${id}/`, payload).then((res) => res.data),
  deleteInvoice: (id: string) => apiClient.delete(`/platform/invoices/${id}/`),
  issueInvoice: (id: string) => apiClient.post<PlatformInvoice>(`/platform/invoices/${id}/issue/`).then((res) => res.data),
  markInvoicePaid: (id: string) => apiClient.post<PlatformInvoice>(`/platform/invoices/${id}/mark-paid/`).then((res) => res.data),
  voidInvoice: (id: string) => apiClient.post<PlatformInvoice>(`/platform/invoices/${id}/void/`).then((res) => res.data),
  subscriptions: () => apiClient.get<Paginated<PlatformSubscription>>("/platform/subscriptions/").then((res) => res.data),
  createSubscription: (payload: { tenant_id: string; plan_id: string; status?: string; seats?: number }) =>
    apiClient.post<PlatformSubscription>("/platform/subscriptions/", payload).then((res) => res.data),
  updateSubscription: (id: string, payload: { plan_id?: string; status?: string; seats?: number }) =>
    apiClient.patch<PlatformSubscription>(`/platform/subscriptions/${id}/`, payload).then((res) => res.data),
  cancelSubscription: (id: string) => apiClient.delete(`/platform/subscriptions/${id}/`),
  appearance: () => apiClient.get<PlatformBranding>("/platform/appearance/").then((res) => res.data),
  updateAppearance: (payload: Partial<PlatformBranding>) =>
    apiClient.patch<PlatformBranding>("/platform/appearance/", payload).then((res) => res.data),
  uploadAppearanceAsset: (slot: AppearanceAssetSlot, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiClient.post<PlatformBranding>(`/platform/appearance/assets/${slot}/`, form).then((res) => res.data);
  },
  clearAppearanceAsset: (slot: AppearanceAssetSlot) =>
    apiClient.delete<PlatformBranding>(`/platform/appearance/assets/${slot}/`).then((res) => res.data),
  landing: () => apiClient.get<LandingContent>("/platform/landing/").then((res) => res.data),
  updateLanding: (payload: Partial<LandingContent>) =>
    apiClient.patch<LandingContent>("/platform/landing/", payload).then((res) => res.data),
  prompts: (params?: Record<string, string>) =>
    apiClient.get<Paginated<PlatformPromptLog>>("/platform/telemetry/prompts/", { params }).then((res) => res.data),
  asks: (params?: Record<string, string>) =>
    apiClient.get<Paginated<PlatformAskLog>>("/platform/telemetry/asks/", { params }).then((res) => res.data),
  pages: (params?: Record<string, string>) =>
    apiClient.get<Paginated<PlatformPageLog>>("/platform/telemetry/pages/", { params }).then((res) => res.data),
  workspaceActivity: (params?: Record<string, string>) =>
    apiClient.get<{ count: number; results: PlatformActivityLog[] }>("/platform/telemetry/activity/", { params }).then((res) => res.data),
};
