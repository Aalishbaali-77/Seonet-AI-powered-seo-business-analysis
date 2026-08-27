import { apiClient } from "@/services/apiClient";
import type { Audit, AuditIssue, AuditRecommendation, AuditReport, AuditPerformance, PerformancePageRow, PerformancePageDetail, PerformanceCompare, PerformanceTrends, AuditFixRun, FixPlanItem, KeywordRankRun, ICP, ImportBatch, Job, Lead, LeadSavedList, Website, WebsiteAccess, BusinessProfile, CommerceKpis, CommerceAnalysis, CommerceExpert, CatalogProduct, CommerceCustomer, CommerceOrder, CommerceReview, GeoPlace, MarketBrief, MarketScore, MarketSignal, GrowthOpportunity, AdvisorResult, Activity, Company, Contact, CrmAssignee, Deal, Pipeline, Stage, Campaign, WorkspaceReport } from "@/types/domain";

type Page<T> = { results: T[]; count?: number };

async function fetchAllPages<T>(load: (params: Record<string, string>) => Promise<Page<T>>, extra: Record<string, string> = {}): Promise<T[]> {
  const first = await load({ ...extra, page: "1", page_size: "100" });
  const items = [...(first.results ?? [])];
  const total = typeof first.count === "number" ? first.count : items.length;
  let page = 2;
  while (items.length < total && page <= 40) {
    const next = await load({ ...extra, page: String(page), page_size: "100" });
    if (!next.results?.length) break;
    items.push(...next.results);
    page += 1;
  }
  return items;
}

export const websiteApi = {
  list: (params?: Record<string, string>) => apiClient.get<Page<Website>>("/websites/", { params }).then((res) => res.data),
  listAll: (params?: Record<string, string>) => fetchAllPages((page) => websiteApi.list(page), params),
  get: (id: string) => apiClient.get<Website>(`/websites/${id}/`).then((res) => res.data),
  create: (payload: Partial<Website> & { url: string }) => apiClient.post<Website>("/websites/", payload).then((res) => res.data),
  update: (id: string, payload: Partial<Website>) => apiClient.patch<Website>(`/websites/${id}/`, payload).then((res) => res.data),
  delete: (id: string) => apiClient.delete(`/websites/${id}/`),
  startAudit: (id: string) => apiClient.post<Job>(`/websites/${id}/audit/`).then((res) => res.data),
  performanceTrends: (id: string) => apiClient.get<PerformanceTrends>(`/websites/${id}/performance/trends/`).then((res) => res.data),
  access: (id: string) => apiClient.get<{ connected: boolean; access: WebsiteAccess | null }>(`/websites/${id}/access/`).then((res) => res.data),
  saveAccess: (id: string, payload: Record<string, string>) =>
    apiClient.put<{ connected: boolean; access: WebsiteAccess; message: string }>(`/websites/${id}/access/`, payload).then((res) => res.data),
  removeAccess: (id: string) => apiClient.delete(`/websites/${id}/access/`),
  fixPlan: (id: string, auditId?: string) =>
    apiClient
      .get<{ audit_id: string; access_connected: boolean; applicable: FixPlanItem[]; skipped: FixPlanItem[]; why: string }>(`/websites/${id}/fix-plan/`, { params: auditId ? { audit: auditId } : undefined })
      .then((res) => res.data),
  applyFixes: (id: string, auditId: string) => apiClient.post<Job>(`/websites/${id}/apply-fixes/`, { audit_id: auditId }).then((res) => res.data),
  fixRuns: (id: string) => apiClient.get<{ results: AuditFixRun[] }>(`/websites/${id}/fix-runs/`).then((res) => res.data),
  fixRun: (id: string, runId: string) => apiClient.get<AuditFixRun>(`/websites/${id}/fix-runs/${runId}/`).then((res) => res.data),
  keywords: (id: string) => apiClient.get<{ run: KeywordRankRun | null }>(`/websites/${id}/keywords/`).then((res) => res.data),
  checkKeywords: (id: string) => apiClient.post<Job>(`/websites/${id}/keywords/`).then((res) => res.data),
};

export const auditApi = {
  list: (params?: Record<string, string>) => apiClient.get<Page<Audit>>("/audits/", { params }).then((res) => res.data),
  listAll: (params?: Record<string, string>) => fetchAllPages((page) => auditApi.list(page), params),
  get: (id: string) => apiClient.get<Audit>(`/audits/${id}/`).then((res) => res.data),
  issues: (id: string, params?: Record<string, string>) =>
    fetchAllPages((page) => apiClient.get<Page<AuditIssue>>(`/audits/${id}/issues/`, { params: { ...params, ...page } }).then((res) => res.data)),
  updateIssue: (auditId: string, issueId: string, payload: { status: string }) =>
    apiClient.patch<AuditIssue>(`/audits/${auditId}/issues/${issueId}/`, payload).then((res) => res.data),
  recommendations: (id: string) =>
    fetchAllPages((page) => apiClient.get<Page<AuditRecommendation>>(`/audits/${id}/recommendations/`, { params: page }).then((res) => res.data)),
  report: (id: string) => apiClient.get<AuditReport>(`/audits/${id}/report/`).then((res) => res.data),
  performance: (id: string) => apiClient.get<AuditPerformance>(`/audits/${id}/performance/`).then((res) => res.data),
  pages: (id: string, params?: Record<string, string>) =>
    apiClient.get<{ results: PerformancePageRow[]; count?: number }>(`/audits/${id}/pages/`, { params }).then((res) => res.data),
  page: (id: string, pageId: string) => apiClient.get<PerformancePageDetail>(`/audits/${id}/pages/${pageId}/`).then((res) => res.data),
  compare: (id: string, other?: string) =>
    apiClient.get<PerformanceCompare>(`/audits/${id}/compare/`, { params: other ? { other } : undefined }).then((res) => res.data),
};

async function downloadCsv(path: string, fallback: string, params?: Record<string, string>) {
  const res = await apiClient.get(path, { params, responseType: "blob" });
  const blob = res.data as Blob;
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  const disposition = String(res.headers["content-disposition"] ?? "");
  const match = disposition.match(/filename="?([^"]+)"?/);
  link.download = match?.[1] ?? fallback;
  link.click();
  URL.revokeObjectURL(url);
}

export const jobApi = {
  list: (params?: Record<string, string>) => apiClient.get<Page<Job>>("/jobs/", { params }).then((res) => res.data),
  get: (id: string) => apiClient.get<Job>(`/jobs/${id}/`).then((res) => res.data),
  cancel: (id: string) => apiClient.post<Job>(`/jobs/${id}/cancel/`).then((res) => res.data),
};

export const leadApi = {
  list: (params?: Record<string, string>) => apiClient.get<{ results: Lead[]; count?: number }>("/leads/", { params }).then((res) => res.data),
  get: (id: string) => apiClient.get<Lead>(`/leads/${id}/`).then((res) => res.data),
  update: (id: string, payload: Partial<Lead>) => apiClient.patch<Lead>(`/leads/${id}/`, payload).then((res) => res.data),
  delete: (id: string) => apiClient.delete(`/leads/${id}/`),
  createIcp: (payload: Partial<ICP> & { raw_input: string }) => apiClient.post<ICP>("/leads/icps/", payload).then((res) => res.data),
  confirmIcp: (id: string) => apiClient.post<ICP>(`/leads/icps/${id}/confirm/`).then((res) => res.data),
  startSearch: (icp: string, extra?: { geo_place?: string }) =>
    apiClient.post<{ search: { id: string; job: string }; job: Job }>("/leads/searches/start/", { icp, ...(extra?.geo_place ? { geo_place: extra.geo_place } : {}) }).then((res) => res.data),
  lists: () => apiClient.get<{ results: LeadSavedList[] }>("/leads/lists/").then((res) => res.data),
  createList: (payload: { name: string; description?: string }) => apiClient.post<LeadSavedList>("/leads/lists/", payload).then((res) => res.data),
  getList: (id: string) => apiClient.get<LeadSavedList>(`/leads/lists/${id}/`).then((res) => res.data),
  addToList: (id: string, leadIds: string[]) => apiClient.post(`/leads/lists/${id}/members/`, { lead_ids: leadIds }).then((res) => res.data),
  removeFromList: (id: string, leadIds: string[]) => apiClient.delete(`/leads/lists/${id}/members/`, { data: { lead_ids: leadIds } }).then((res) => res.data),
  score: (leadIds?: string[]) => apiClient.post<{ scored: number }>("/leads/score/", leadIds?.length ? { lead_ids: leadIds } : {}).then((res) => res.data),
  enrich: (id: string) =>
    apiClient
      .post<{ lead: Lead; filled: Array<{ field: string; source: string }>; missing_fields: string[]; sources: string[]; errors: string[]; why: string }>(
        `/leads/${id}/enrich/`,
      )
      .then((res) => res.data),
  enrichMany: (leadIds?: string[]) =>
    apiClient.post<{ job: Job }>("/leads/enrich/", leadIds?.length ? { lead_ids: leadIds } : {}).then((res) => res.data),
  exportCsv: (params?: Record<string, string>) => downloadCsv("/leads/export/", "sipulse-leads.csv", params),
};

export const crmApi = {
  pipelines: () => apiClient.get<Pipeline[]>("/crm/pipelines/").then((res) => res.data),
  createPipeline: (payload: { name: string; is_default?: boolean }) => apiClient.post<Pipeline>("/crm/pipelines/", payload).then((res) => res.data),
  updatePipeline: (id: string, payload: Partial<Pipeline>) => apiClient.patch<Pipeline>(`/crm/pipelines/${id}/`, payload).then((res) => res.data),
  deletePipeline: (id: string) => apiClient.delete(`/crm/pipelines/${id}/`),
  createStage: (pipelineId: string, payload: Partial<Stage> & { name: string }) =>
    apiClient.post<Stage>(`/crm/pipelines/${pipelineId}/stages/`, payload).then((res) => res.data),
  updateStage: (pipelineId: string, id: string, payload: Partial<Stage>) =>
    apiClient.patch<Stage>(`/crm/pipelines/${pipelineId}/stages/${id}/`, payload).then((res) => res.data),
  deleteStage: (pipelineId: string, id: string) => apiClient.delete(`/crm/pipelines/${pipelineId}/stages/${id}/`),
  exportCsv: (kind: "companies" | "contacts" | "deals" | "activities") => downloadCsv("/crm/export/", `sipulse-crm-${kind}.csv`, { kind }),
  assignees: () => apiClient.get<CrmAssignee[]>("/crm/assignees/").then((res) => res.data),
  funnel: (params?: Record<string, string>) =>
    apiClient
      .get<{
        pipeline: string;
        pipeline_id?: string;
        origin: string;
        why: string;
        stages: Array<{ id: string; name: string; code: string; is_won: boolean; is_lost: boolean; deals: number; amount: string }>;
      }>("/crm/funnel/", { params })
      .then((res) => res.data),
  companies: (params?: Record<string, string>) =>
    apiClient.get<Page<Company>>("/crm/companies/", { params }).then((res) => res.data),
  companiesAll: (params?: Record<string, string>) => fetchAllPages((page) => crmApi.companies(page), params),
  getCompany: (id: string) => apiClient.get<Company>(`/crm/companies/${id}/`).then((res) => res.data),
  updateCompany: (id: string, payload: Partial<Company>) => apiClient.patch<Company>(`/crm/companies/${id}/`, payload).then((res) => res.data),
  createCompany: (payload: Partial<Company> & { name: string }) => apiClient.post<Company>("/crm/companies/", payload).then((res) => res.data),
  deleteCompany: (id: string) => apiClient.delete(`/crm/companies/${id}/`),
  contacts: (params?: Record<string, string>) =>
    apiClient.get<Page<Contact>>("/crm/contacts/", { params }).then((res) => res.data),
  contactsAll: (params?: Record<string, string>) => fetchAllPages((page) => crmApi.contacts(page), params),
  getContact: (id: string) => apiClient.get<Contact>(`/crm/contacts/${id}/`).then((res) => res.data),
  updateContact: (id: string, payload: Partial<Contact>) => apiClient.patch<Contact>(`/crm/contacts/${id}/`, payload).then((res) => res.data),
  createContact: (payload: Partial<Contact> & { company: string; first_name: string }) =>
    apiClient.post<Contact>("/crm/contacts/", payload).then((res) => res.data),
  deleteContact: (id: string) => apiClient.delete(`/crm/contacts/${id}/`),
  deals: (params?: Record<string, string>) => apiClient.get<Page<Deal>>("/crm/deals/", { params }).then((res) => res.data),
  dealsAll: (params?: Record<string, string>) => fetchAllPages((page) => crmApi.deals(page), params),
  getDeal: (id: string) => apiClient.get<Deal>(`/crm/deals/${id}/`).then((res) => res.data),
  createDeal: (payload: Partial<Deal> & { pipeline: string; stage: string; company: string; name: string }) =>
    apiClient.post<Deal>("/crm/deals/", payload).then((res) => res.data),
  updateDeal: (id: string, payload: Partial<Deal>) => apiClient.patch<Deal>(`/crm/deals/${id}/`, payload).then((res) => res.data),
  deleteDeal: (id: string) => apiClient.delete(`/crm/deals/${id}/`),
  activities: (params?: Record<string, string>) =>
    apiClient.get<Page<Activity>>("/crm/activities/", { params }).then((res) => res.data),
  activitiesAll: (params?: Record<string, string>) => fetchAllPages((page) => crmApi.activities(page), params),
  createActivity: (payload: Partial<Activity> & { title: string }) => apiClient.post<Activity>("/crm/activities/", payload).then((res) => res.data),
  updateActivity: (id: string, payload: Partial<Activity>) => apiClient.patch<Activity>(`/crm/activities/${id}/`, payload).then((res) => res.data),
  deleteActivity: (id: string) => apiClient.delete(`/crm/activities/${id}/`),
};

export const billingApi = {
  get: () => apiClient.get("/billing/").then((res) => res.data),
  usage: () => apiClient.get("/usage/summary/").then((res) => res.data),
  aiUsage: () => apiClient.get("/ai/usage/").then((res) => res.data),
  subscribe: (planId: string) => apiClient.post("/billing/subscribe/", { plan_id: planId }).then((res) => res.data),
  payInvoice: (id: string) =>
    apiClient
      .post<{
        method: string;
        paid: boolean;
        invoice_id: string;
        status: string;
        instructions: string;
        gateway_name: string;
        card_available?: boolean;
        checkout_url?: string;
      }>(`/billing/invoices/${id}/pay/`)
      .then((res) => res.data),
};

export const telemetryApi = {
  page: (payload: { path: string; title?: string; referrer?: string }) =>
    apiClient.post("/telemetry/page/", payload).then((res) => res.data).catch(() => null),
};

export const integrationApi = {
  list: () => apiClient.get<{ items: IntegrationItem[]; webhook_events: string[] }>("/integrations/").then((res) => res.data),
  save: (provider: string, payload: Record<string, unknown>) =>
    apiClient.put<IntegrationItem>(`/integrations/${provider}/`, payload).then((res) => res.data),
  test: (provider: string) => apiClient.post<IntegrationItem>(`/integrations/${provider}/test/`).then((res) => res.data),
  sync: (provider: string) => apiClient.post<Job>(`/integrations/${provider}/sync/`).then((res) => res.data),
  disconnect: (provider: string) => apiClient.delete<IntegrationItem>(`/integrations/${provider}/`).then((res) => res.data),
  rotateWebhook: () => apiClient.post<IntegrationItem>("/integrations/webhook/rotate/").then((res) => res.data),
};

export type IntegrationField = {
  key: string;
  label: string;
  secret: boolean;
  required: boolean;
  input: string;
  help?: string;
};

export type IntegrationItem = {
  code: string;
  name: string;
  category: string;
  description: string;
  connectable: boolean;
  fields: IntegrationField[];
  setup_steps?: string[];
  required_module?: string;
  locked: boolean;
  lock_reason: string;
  status: string;
  credentials_configured: boolean;
  enabled: boolean;
  config: Record<string, unknown>;
  last_checked_at: string | null;
  last_error: string;
  last_sync_at: string | null;
  records_synced: number;
  revealed?: Record<string, string>;
};

export const tenantApi = {
  list: () => apiClient.get<{ results: Array<{ id: string; name: string; slug: string; status: string }> }>("/tenants/").then((res) => res.data),
  get: (id: string) => apiClient.get<WorkspaceProfile>(`/tenants/${id}/`).then((res) => res.data),
  update: (id: string, payload: Partial<WorkspaceProfile>) => apiClient.patch<WorkspaceProfile>(`/tenants/${id}/`, payload).then((res) => res.data),
  members: (id: string) =>
    apiClient.get<WorkspaceMember[] | { results: WorkspaceMember[] }>(`/tenants/${id}/members/`).then((res) => (Array.isArray(res.data) ? res.data : res.data.results ?? [])),
  addMember: (id: string, payload: { email: string; first_name?: string; last_name?: string; role_code?: string; password?: string }) =>
    apiClient.post<WorkspaceMember>(`/tenants/${id}/members/`, payload).then((res) => res.data),
  updateMember: (id: string, memberId: string, payload: { role_code?: string; status?: string }) =>
    apiClient.patch<WorkspaceMember>(`/tenants/${id}/members/${memberId}/`, payload).then((res) => res.data),
  removeMember: (id: string, memberId: string) => apiClient.delete(`/tenants/${id}/members/${memberId}/`),
  apiTokens: (id: string) => apiClient.get<WorkspaceApiToken[]>(`/tenants/${id}/api-tokens/`).then((res) => res.data),
  createApiToken: (id: string, name: string) => apiClient.post<WorkspaceApiToken>(`/tenants/${id}/api-tokens/`, { name }).then((res) => res.data),
  revokeApiToken: (id: string, tokenId: string) => apiClient.delete(`/tenants/${id}/api-tokens/${tokenId}/`),
};

export type WorkspaceProfile = {
  id: string;
  name: string;
  slug: string;
  status: string;
  timezone: string;
  locale: string;
  currency: string;
  company_legal_name: string;
  company_website: string;
  industry: string;
  support_email: string;
  reply_to_email: string;
  notification_digest: string;
  primary_crm: string;
};

export type WorkspaceApiToken = {
  id: string;
  name: string;
  prefix: string;
  last_used_at: string | null;
  created_at: string;
  revoked_at: string | null;
  token?: string;
};

export type WorkspaceMember = {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  status: string;
  roles: string[];
};

export type WorkspaceRole = {
  id: string;
  code: string;
  name: string;
  is_system: boolean;
  permissions: string[];
};

export type AccessPermission = {
  id: string;
  code: string;
  name: string;
  module: string;
};

export const accessApi = {
  roles: () => apiClient.get<WorkspaceRole[]>("/roles/").then((res) => res.data),
  createRole: (payload: { name: string; permission_codes: string[] }) => apiClient.post<WorkspaceRole>("/roles/", payload).then((res) => res.data),
  updateRole: (id: string, payload: { name?: string; permission_codes?: string[] }) => apiClient.patch<WorkspaceRole>(`/roles/${id}/`, payload).then((res) => res.data),
  deleteRole: (id: string) => apiClient.delete(`/roles/${id}/`),
  permissions: () => apiClient.get<AccessPermission[]>("/permissions/").then((res) => res.data),
};

export const businessApi = {
  overview: () =>
    apiClient.get<{ profile: BusinessProfile; kpis: CommerceKpis; analysis: CommerceAnalysis; expert: CommerceExpert }>("/business/overview/").then((res) => res.data),
  profile: () => apiClient.get<BusinessProfile>("/business/profile/").then((res) => res.data),
  saveProfile: (payload: Partial<BusinessProfile>) => apiClient.patch<BusinessProfile>("/business/profile/", payload).then((res) => res.data),
  products: () => apiClient.get<{ results: CatalogProduct[] }>("/business/products/").then((res) => res.data),
  customers: () => apiClient.get<{ results: CommerceCustomer[] }>("/business/customers/").then((res) => res.data),
  orders: () => apiClient.get<{ results: CommerceOrder[] }>("/business/orders/").then((res) => res.data),
  orderDetail: (id: string) => apiClient.get<CommerceOrder>(`/business/orders/${id}/`).then((res) => res.data),
  updateOrder: (id: string, payload: Partial<Pick<CommerceOrder, "ordered_at" | "city" | "channel" | "status" | "currency">>) =>
    apiClient.patch<CommerceOrder>(`/business/orders/${id}/`, payload).then((res) => res.data),
  reviews: () => apiClient.get<{ results: CommerceReview[] }>("/business/reviews/").then((res) => res.data),
  stores: () => apiClient.get<{ items: IntegrationItem[] }>("/business/stores/").then((res) => res.data),
  saveStore: (provider: string, payload: Record<string, unknown>) =>
    apiClient.put<IntegrationItem>(`/business/stores/${provider}/`, payload).then((res) => res.data),
  testStore: (provider: string) => apiClient.post<IntegrationItem>(`/business/stores/${provider}/test/`).then((res) => res.data),
  syncStore: (provider: string) => apiClient.post<Job>(`/business/stores/${provider}/sync/`).then((res) => res.data),
  disconnectStore: (provider: string) => apiClient.delete<IntegrationItem>(`/business/stores/${provider}/`).then((res) => res.data),
  promoteCustomers: () => apiClient.post<{ created: number; skipped: number }>("/business/customers/promote/").then((res) => res.data),
  analyze: () => apiClient.post<Job>("/business/analyze/").then((res) => res.data),
  downloadCsvTemplate: async (kind: "products" | "orders") => {
    const res = await apiClient.get("/business/import/", { params: { kind }, responseType: "blob" });
    const blob = res.data as Blob;
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    const disposition = String(res.headers["content-disposition"] ?? "");
    const match = disposition.match(/filename="?([^"]+)"?/);
    link.download = match?.[1] ?? `sipulse-${kind}-template.csv`;
    link.click();
    URL.revokeObjectURL(url);
  },
  importCsv: (kind: "products" | "orders", file: File) => {
    const body = new FormData();
    body.append("kind", kind);
    body.append("file", file);
    return apiClient.post<Job>("/business/import/", body).then((res) => res.data);
  },
  imports: () => apiClient.get<{ results: ImportBatch[] }>("/business/imports/").then((res) => res.data),
  deleteImportBatch: (id: string, mode: "log_only" | "log_and_rows") =>
    apiClient.delete<{ deleted: boolean; mode: string; rows_removed: number }>(`/business/imports/${id}/`, { params: { mode } }).then((res) => res.data),
};

export const marketApi = {
  overview: () =>
    apiClient
      .get<{ country: string; cities: Array<{ place: GeoPlace; score: MarketScore }>; weights: Record<string, number>; scored_cities: number; note: string }>(
        "/markets/overview/",
      )
      .then((res) => res.data),
  places: (params?: Record<string, string>) => apiClient.get<GeoPlace[]>("/markets/places/", { params }).then((res) => res.data),
  place: (id: string) =>
    apiClient
      .get<{ place: GeoPlace; parent: GeoPlace | null; children: GeoPlace[]; signals: unknown[]; score: MarketScore }>(`/markets/places/${id}/`)
      .then((res) => res.data),
  scoring: () => apiClient.get<{ id: string | null; weights: Record<string, number>; defaults: Record<string, number> }>("/markets/scoring/").then((res) => res.data),
  saveScoring: (weights: Record<string, number>) =>
    apiClient.put<{ id: string; weights: Record<string, number>; defaults: Record<string, number> }>("/markets/scoring/", { weights }).then((res) => res.data),
  signals: (params?: Record<string, string>) =>
    apiClient.get<MarketSignal[] | { results: MarketSignal[] }>("/markets/signals/", { params }).then((res) => {
      const data = res.data;
      return { results: Array.isArray(data) ? data : data.results ?? [] };
    }),
  createSignal: (payload: { place: string; kind: string; value: number; source: string; verification_status?: string }) =>
    apiClient.post<MarketSignal>("/markets/signals/", payload).then((res) => res.data),
  brief: () => apiClient.get<MarketBrief>("/markets/brief/").then((res) => res.data),
  ask: (payload: { question?: string; profile?: Partial<BusinessProfile> } | string) => {
    const body = typeof payload === "string" ? { question: payload } : payload;
    return apiClient.post<Job>("/markets/brief/", body).then((res) => res.data);
  },
  downloadSignalTemplate: async () => {
    const res = await apiClient.get("/markets/import/", { responseType: "blob" });
    const blob = res.data as Blob;
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    const disposition = String(res.headers["content-disposition"] ?? "");
    const match = disposition.match(/filename="?([^"]+)"?/);
    link.download = match?.[1] ?? "sipulse-market-signals-template.csv";
    link.click();
    URL.revokeObjectURL(url);
  },
  importSignals: (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return apiClient.post<Job>("/markets/import/", body).then((res) => res.data);
  },
  collect: () => apiClient.post<Job>("/markets/collect/").then((res) => res.data),
};

export const advisorApi = {
  ask: (domain: "business" | "market" | "opportunity" | "lead" | "marketing") =>
    apiClient.post<AdvisorResult>("/ai/advisor/", { domain }).then((res) => res.data),
  query: (question: string) =>
    apiClient
      .post<{
        question: string;
        intent: string | null;
        facts: string[];
        origin: string;
        why: string;
        inference?: string;
        recommendation?: string;
        href?: string;
        job_id?: string;
      }>("/ai/query/", { question })
      .then((res) => res.data),
};

export const opportunityApi = {
  list: (params?: Record<string, string>) => apiClient.get<{ results: GrowthOpportunity[] }>("/opportunities/", { params }).then((res) => res.data),
  get: (id: string) => apiClient.get<GrowthOpportunity>(`/opportunities/${id}/`).then((res) => res.data),
  create: (payload: Partial<GrowthOpportunity> & { title: string; type: string; evidence: string; recommended_action: string; related_lead_ids?: string[] }) =>
    apiClient.post<GrowthOpportunity>("/opportunities/", payload).then((res) => res.data),
  update: (id: string, payload: Partial<GrowthOpportunity> & { related_lead_ids?: string[] }) => apiClient.patch<GrowthOpportunity>(`/opportunities/${id}/`, payload).then((res) => res.data),
  generate: () => apiClient.post<{ created: number; results: GrowthOpportunity[]; note: string }>("/opportunities/generate/").then((res) => res.data),
};

export const marketingApi = {
  campaigns: (params?: Record<string, string>) => apiClient.get<{ results: Campaign[] }>("/marketing/campaigns/", { params }).then((res) => res.data),
  get: (id: string) => apiClient.get<Campaign>(`/marketing/campaigns/${id}/`).then((res) => res.data),
  create: (payload: Partial<Campaign> & { name: string }) => apiClient.post<Campaign>("/marketing/campaigns/", payload).then((res) => res.data),
  update: (id: string, payload: Partial<Campaign>) => apiClient.patch<Campaign>(`/marketing/campaigns/${id}/`, payload).then((res) => res.data),
  send: (id: string) => apiClient.post<Campaign>(`/marketing/campaigns/${id}/send/`).then((res) => res.data),
  preview: (params: Record<string, string>) =>
    apiClient.get<{ count: number; label: string; origin: string; why: string }>("/marketing/audiences/preview/", { params }).then((res) => res.data),
  exportAudience: (params: Record<string, string>) => downloadCsv("/marketing/audiences/export/", "sipulse-campaign-audience.csv", params),
};

export const reportsApi = {
  catalog: () => apiClient.get<{ results: WorkspaceReport[] }>("/reports/").then((res) => res.data),
  exportJson: () => apiClient.get<{ results: WorkspaceReport[]; origin: string; why: string }>("/reports/export/").then((res) => res.data),
};
