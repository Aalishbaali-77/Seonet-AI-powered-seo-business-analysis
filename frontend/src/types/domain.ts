export type Job = {
  id: string;
  job_type: string;
  status: "PENDING" | "QUEUED" | "RUNNING" | "COMPLETED" | "FAILED" | "CANCELLED";
  progress: number;
  payload: Record<string, unknown>;
  result: Record<string, unknown>;
  error: string;
  started_at: string | null;
  completed_at: string | null;
  created_at?: string;
};

export type Website = {
  id: string;
  url: string;
  domain: string;
  name: string;
  status: string;
  business_name: string;
  industry: string;
  description: string;
  target_markets: string[];
  keywords: string[];
  competitors: string[];
  audit_config?: Record<string, unknown>;
    access_connected?: boolean;
  last_audit: {
    id: string;
    overall_score: number | null;
    scores: Record<string, number>;
    summary?: Record<string, unknown>;
    completed_at: string | null;
    issue_count: number;
    status: string;
    pages_crawled?: number;
  } | null;
  created_at: string;
  updated_at: string;
};

export type WebsiteAccess = {
  kind: string;
  status: string;
  host: string;
  port: string | number;
  root_path: string;
  wp_url: string;
  username: string;
  has_secret: boolean;
  last_tested_at: string | null;
  last_error: string;
};

export type FixPlanItem = {
  issue_id?: string;
  title: string;
  code?: string;
  via?: string;
  category?: string;
  reason?: string;
  status?: string;
};

export type IntelligenceCompare = {
  available: boolean;
  origin: string;
  why: string;
  baseline_audit_id: string;
  followup_audit_id: string;
  before_issues: number;
  after_issues: number;
  resolved_titles: string[];
  new_titles: string[];
  still_open_titles: string[];
  rows: Array<{ metric: string; before: number | null; after: number | null; delta: number | null }>;
};

export type AuditFixRun = {
  id: string;
  status: string;
  baseline_audit_id: string;
  followup_audit_id: string | null;
  plan: { applicable?: FixPlanItem[]; skipped?: FixPlanItem[]; why?: string };
  result: { applied?: FixPlanItem[]; skipped?: FixPlanItem[]; errors?: string[] };
  comparison: IntelligenceCompare | Record<string, unknown>;
  error: string;
  created_at: string | null;
};

export type KeywordRankRow = {
  keyword: string;
  position: number | null;
  in_first_page?: boolean;
  matched_url?: string;
  matched_title?: string;
  origin?: string;
  source?: string;
  error?: string;
};

export type KeywordSuggestion = {
  keyword: string;
  intent: string;
  origin: string;
  why: string;
};

export type KeywordAiMeta = {
  used?: boolean;
  provider?: string;
  model?: string;
  origin?: string;
  reason?: string;
};

export type KeywordRankRun = {
  id: string;
  status: string;
  source: string;
  keywords: string[];
  results: KeywordRankRow[];
  suggestions: KeywordSuggestion[];
  ai?: KeywordAiMeta;
  error: string;
  created_at: string | null;
  why: string;
};

export type AuditIssue = {
  id: string;
  severity: string;
  category: string;
  title: string;
  why_it_matters: string;
  affected_urls: string[];
  evidence: string;
  recommendation: string;
  estimated_effort: string;
  status: string;
  origin: string;
  confidence: number | null;
  priority: number;
  code?: string;
};

export type AuditRecommendation = {
  id: string;
  issue_id?: string | null;
  title: string;
  verified_finding: string;
  ai_interpretation: string;
  recommendation: string;
  origin: string;
  confidence: number | null;
  effort?: string;
  priority?: number;
  category?: string;
  severity?: string;
};

export type Audit = {
  id: string;
  website: string;
  website_id?: string;
  website_domain?: string;
  website_name?: string;
  job: string | null;
  status: string;
  overall_score: number | null;
  scores: Record<string, number>;
  summary?: Record<string, unknown>;
  pages_crawled: number;
  issue_count: number;
  completed_at: string | null;
  created_at: string;
  issues?: AuditIssue[];
  recommendations?: AuditRecommendation[];
};

export type AuditReport = {
  audit: Audit;
  website: {
    id: string;
    name: string;
    domain: string;
    url: string;
    industry: string;
    keywords: string[];
    target_markets: string[];
    competitors: string[];
  };
  issues_by_category: Record<string, AuditIssue[]>;
  recommendations: AuditRecommendation[];
  export: string;
};

export type PerformanceKpis = {
  median_ttfb_ms?: number;
  avg_ttfb_ms?: number;
  p75_ttfb_ms?: number;
  p90_ttfb_ms?: number;
  p95_ttfb_ms?: number;
  avg_html_bytes?: number;
  median_html_bytes?: number;
  transfer_bytes?: number;
  compression_rate?: number;
  redirect_pages?: number;
  slow_pages?: number;
  error_pages?: number;
  pages?: number;
};

export type PerformanceSnapshot = {
  overall_score?: number;
  technical_score?: number;
  ux_score?: number | null;
  ux_source?: string | null;
  ux_available?: boolean;
  band?: string;
  technical_band?: string;
  ux_band?: string;
  explain?: { overall?: string; main_problems?: string[]; data_sources?: Record<string, string> };
  kpis?: PerformanceKpis;
  distributions?: {
    compression?: Record<string, number>;
    protocol?: Record<string, number>;
    status?: Record<string, number>;
    resources?: Record<string, number>;
  };
  slowest?: Array<{ url: string; ttfb_ms: number; html_bytes: number; score: number; status: number | null }>;
  issues?: Array<{ code: string; title: string; severity: string; evidence: string; recommendation: string; affected_urls: string[] }>;
  regression?: { detected?: boolean; changes?: Array<{ metric: string; previous: number; current: number; regression: boolean; label: string }>; message?: string };
  ux_metrics?: Record<string, unknown>;
  breakdown?: Record<string, number>;
};

export type AuditPerformance = {
  audit_id: string;
  website_id: string;
  website_domain: string;
  completed_at: string | null;
  scores: { overall: number | null; technical: number | null; ux: number | null };
  snapshot: PerformanceSnapshot;
  issue_counts: Record<string, number>;
  recommendations: Array<{ title: string; recommendation: string; code: string; severity: string; evidence: string; ai_interpretation?: string }>;
};

export type PerformancePageRow = {
  id: string;
  url: string;
  status_code: number | null;
  title: string;
  ttfb_ms: number;
  html_size_bytes: number;
  transfer_bytes: number;
  redirect_count: number;
  compression: string;
  http_protocol: string;
  page_score: number | null;
  https: boolean;
  cdn: string;
  timing_source: string;
  lcp_ms?: number | null;
  inp_ms?: number | null;
  cls?: number | null;
  cwv_source?: string;
  updated_at: string;
  resource_summary?: Record<string, unknown>;
  redirect_hops?: Array<Record<string, unknown>>;
};

export type PerformancePageDetail = PerformancePageRow & {
  timing: Record<string, unknown>;
  response: Record<string, unknown>;
  resources: Array<Record<string, unknown>>;
  issues?: AuditIssue[];
  recommendations?: Array<{ title: string; recommendation: string; severity: string; evidence: string }>;
};

export type PerformanceCompare = {
  current_audit_id: string;
  previous_audit_id: string | null;
  comparison: {
    available: boolean;
    rows: Array<{ metric: string; previous: number | null; current: number | null; change: number | null; change_pct: number | null; unit: string }>;
    improvements: string[];
    regressions: string[];
    new_issue_codes: string[];
    resolved_issue_codes: string[];
  };
  regression: { detected: boolean; changes: Array<Record<string, unknown>> };
};

export type PerformanceTrends = {
  website_id: string;
  domain: string;
  points: Array<{
    audit_id: string;
    completed_at: string;
    overall: number | null;
    technical: number | null;
    ux: number | null;
    median_ttfb_ms: number | null;
    p75_ttfb_ms?: number | null;
    p95_ttfb_ms?: number | null;
  }>;
  latest: Record<string, unknown> | null;
};

export type Lead = {
  id: string;
  company_name: string;
  industry: string;
  location: string;
  website: string;
  phone: string;
  email: string;
  linkedin_url?: string;
  description?: string;
  employee_count?: string;
  enriched_at?: string | null;
  enrichment?: Array<{ at?: string; filled?: Array<{ field: string; source: string }>; errors?: string[] }>;
  source: string;
  status: string;
  lead_score: number | null;
  opportunity_score: number | null;
  quality_score: number | null;
  icp_fit?: number | null;
  location_fit?: number | null;
  industry_fit?: number | null;
  crm_synced: boolean;
  notes?: string;
  ai_summary?: string;
  origin: string;
  list_ids?: string[];
  updated_at: string;
};

export type LeadSavedList = {
  id: string;
  name: string;
  description: string;
  lead_count: number;
  leads?: Lead[];
};

export type ICP = {
  id: string;
  name: string;
  raw_input: string;
  industry: string;
  employee_count: string;
  locations: string[];
  keywords: string[];
  origin: string;
  status: string;
};

export type CrmAssignee = {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  name: string;
};

export type Deal = {
  id: string;
  pipeline: string;
  stage: string;
  stage_name?: string;
  stage_code?: string;
  company: string;
  company_name?: string;
  contact?: string | null;
  contact_name?: string;
  name: string;
  amount: string;
  currency?: string;
  expected_close_at?: string | null;
  priority?: string;
  next_step?: string;
  won_reason?: string;
  lost_reason?: string;
  closed_at?: string | null;
  last_activity_at?: string | null;
  lead?: string | null;
  owner?: string | null;
  owner_name?: string;
};

export type Stage = { id: string; name: string; code: string; order: number; is_won?: boolean; is_lost?: boolean };
export type Pipeline = { id: string; name: string; is_default: boolean; stages: Stage[] };
export type Company = {
  id: string;
  name: string;
  domain: string;
  industry: string;
  location: string;
  phone?: string;
  email?: string;
  notes?: string;
  tags?: string[];
  last_activity_at?: string | null;
  owner?: string | null;
  owner_name?: string;
};
export type Contact = {
  id: string;
  company: string;
  company_name?: string;
  first_name: string;
  last_name: string;
  title?: string;
  email: string;
  phone: string;
  owner?: string | null;
  owner_name?: string;
};
export type Activity = {
  id: string;
  company: string | null;
  company_name?: string;
  deal: string | null;
  deal_name?: string;
  contact?: string | null;
  contact_name?: string;
  kind: string;
  title: string;
  body: string;
  due_at: string | null;
  completed_at?: string | null;
  owner?: string | null;
  owner_name?: string;
};

export type AdvisorResult = {
  domain: string;
  facts: string[];
  inference: string;
  recommendation: string;
  origin: string;
};

export type MarketSignal = {
  id: string;
  place: string;
  place_name?: string;
  place_code?: string;
  kind: string;
  value: number;
  source: string;
  source_url?: string;
  verification_status: string;
};

export type MarketCitation = {
  id: string;
  kind: string;
  title: string;
  text: string;
  href: string;
  origin: string;
};

export type MarketCityScore = {
  id: string;
  name: string;
  code: string;
  score: number;
  origin: string;
  why: string;
  coverage: number;
};

export type BusinessProfile = {
  id: string;
  business_type: string;
  industry: string;
  category: string;
  current_market: string;
  goal: string;
  notes: string;
  updated_at?: string;
};

export type MarketAnalysis = {
  question: string;
  inference: string;
  recommendation: string;
  origin: string;
  citations?: MarketCitation[];
  findings: string[];
};

export type MarketBrief = {
  available: boolean;
  why: string;
  profile: BusinessProfile;
  subject: string;
  findings: string[];
  served: Array<{ city: string; orders?: number; why?: string }>;
  expansion: Array<{ city: string; why?: string }>;
  scored: MarketCityScore[];
  unscored_cities: number;
  overlap: MarketCityScore[];
  signal_without_orders: MarketCityScore[];
  signal_count: number;
  citations: MarketCitation[];
  commerce_available: boolean;
  last_analysis: MarketAnalysis | null;
};

export type MarketAsk = MarketAnalysis & { brief: MarketBrief; citations: MarketCitation[] };

export type CommerceAnalysis = {
  available: boolean;
  reason: string;
  origin?: string;
  business?: {
    orders?: number;
    revenue?: string | null;
    average_order_value?: string | null;
    products?: number;
    customers?: number;
    cancelled_or_returned?: number;
    top_city?: string;
    top_city_share?: string | null;
    channels?: Array<{ channel: string; orders: number }>;
    industry?: string;
    current_market?: string;
    goal?: string;
  };
  products?: {
    top: Array<{ name: string; sku: string; units: string; revenue: string; why: string }>;
    unsold: Array<{ name: string; sku: string; why: string }>;
    weak_reviews: Array<{ name: string; sku: string; negative: number; why: string }>;
    gaps: Array<{ name: string; sku: string; city: string; why: string }>;
  };
  demand?: {
    served: Array<{ city: string; orders: number; units?: string; revenue?: string; why: string }>;
    thin: Array<{ city: string; orders: number; why: string }>;
    expansion: Array<{ city: string; kind: string; why: string; score?: number }>;
  };
  next_actions?: Array<{ action: string; origin: string }>;
};

export type CommerceExpert = {
  origin?: string;
  inference?: string;
  recommendation?: string;
  ran_at?: string;
  facts?: string[];
};

export type CommerceKpis = {
  available: boolean;
  reason: string;
  products: number;
  customers: number;
  orders: number;
  revenue?: string | null;
  average_order_value?: string | null;
  units?: string;
  by_city?: Array<{ city: string; orders: number }>;
  by_channel?: Array<{ channel: string; orders: number }>;
  by_source?: Array<{ source: string; orders: number }>;
  customer_cities?: string[];
  reviews?: {
    count: number;
    average_rating: number | null;
    positive: number;
    neutral: number;
    negative: number;
    reason: string;
    origin?: string;
  };
  potential_areas?: Array<{ city: string; orders: number; why: string }>;
  origin?: string;
};

export type CatalogProduct = {
  id: string;
  sku: string;
  name: string;
  category: string;
  unit_price: string | null;
  cost_price: string | null;
  source: string;
  verification_status: string;
};

export type CommerceCustomer = { id: string; name: string; city: string; email: string; source: string };
export type CommerceOrderItem = {
  id: string;
  sku: string;
  name: string;
  quantity: string;
  unit_price: string;
  discount: string;
  cost: string | null;
};
export type CommerceOrder = {
  id: string;
  external_id: string;
  ordered_at: string | null;
  customer_name: string;
  city: string;
  channel: string;
  status: string;
  currency: string;
  source: string;
  items: CommerceOrderItem[];
  created_at: string;
};
export type ImportBatch = {
  id: string;
  file_name: string;
  kind: "orders" | "products";
  status: "success" | "partial" | "failed";
  rows_total: number;
  rows_imported: number;
  created_at: string;
};
export type CommerceReview = {
  id: string;
  product_name: string;
  rating: number | null;
  title: string;
  body: string;
  reviewer: string;
  source: string;
  sentiment: string;
  origin: string;
};

export type MarketScore = {
  score: number | null;
  parts: Record<string, number | null>;
  coverage: number;
  missing: string[];
  origin: string;
  why: string;
};

export type GeoPlace = {
  id: string;
  code: string;
  name: string;
  kind: string;
  country_code: string;
  parent: string | null;
  parent_name?: string;
  score?: MarketScore;
};

export type GrowthOpportunity = {
  id: string;
  title: string;
  type: string;
  score: number | null;
  evidence: string;
  recommended_action: string;
  potential_impact: string;
  confidence: number | null;
  origin: string;
  status: string;
  geo_place: string | null;
  geo_place_name: string;
  related_leads?: Array<{
    id: string;
    company_name: string;
    location: string;
    lead_score: number | null;
    status: string;
  }>;
  created_at: string;
};

export type Campaign = {
  id: string;
  name: string;
  status: string;
  channel: string;
  audience_type: string;
  lead_list: string | null;
  lead_list_name: string;
  city: string;
  opportunity: string | null;
  opportunity_title: string;
  offer_title: string;
  offer_body: string;
  audience_count: number | null;
  live_audience_count: number;
  sent_at: string | null;
  send_note: string;
};

export type WorkspaceReport = {
  code: string;
  title: string;
  count: number;
  available: boolean;
  href: string;
  why: string;
  stages?: Array<{ name: string; deals: number; amount: string }>;
};

