export type ApiErrorBody = {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
    request_id: string;
  };
};

export type TenantSummary = {
  id: string;
  name: string;
  slug: string;
  status: string;
  is_default: boolean;
  roles: string[];
};

export type TenantSubscription = {
  status: string;
  access: boolean;
  current_period_end: string | null;
  plan_id: string | null;
  plan_code: string | null;
  plan_name: string | null;
  max_users: number;
  seats_used: number;
};

export type CurrentUser = {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  email_verified_at: string | null;
  mfa_enabled: boolean;
  theme_preference: "light" | "dark" | "system";
  tenants: TenantSummary[];
  permissions: string[];
  is_platform_admin: boolean;
  modules: string[];
  subscription: TenantSubscription | null;
};

export type AppearanceAssetSlot =
  | "logo"
  | "logo_dark"
  | "logo_mark"
  | "logo_mark_dark"
  | "logo_nav"
  | "logo_nav_dark"
  | "logo_sidebar"
  | "logo_sidebar_dark"
  | "logo_footer"
  | "logo_footer_dark"
  | "favicon"
  | "app_icon";

export type PlatformBranding = {
  product_name: string;
  legal_name: string;
  tagline: string;
  description: string;
  support_email: string;
  support_url: string;
  login_footer: string;
  copyright_text: string;
  default_theme: "light" | "dark" | "system";
  primary_color: string;
  secondary_color: string;
  logo_url: string | null;
  logo_dark_url: string | null;
  logo_mark_url: string | null;
  logo_mark_dark_url: string | null;
  logo_nav_url: string | null;
  logo_nav_dark_url: string | null;
  logo_sidebar_url: string | null;
  logo_sidebar_dark_url: string | null;
  logo_footer_url: string | null;
  logo_footer_dark_url: string | null;
  favicon_url: string | null;
  app_icon_url: string | null;
  updated_at?: string;
};

export const defaultBranding: PlatformBranding = {
  product_name: "SIPulse",
  legal_name: "SI Global Solutions",
  tagline: "AI-Powered Business Growth Intelligence",
  description: "Website intelligence, licensed keyword ranks, first-party commerce, cited markets, lead discovery, and native CRM in one tenant. Empty stays empty.",
  support_email: "hello@siglobalsolutions.com",
  support_url: "",
  login_footer: "Need a workspace? Ask SI Global Solutions to provision your tenant.",
  copyright_text: "© 2026 SI Global Solutions. All rights reserved.",
  default_theme: "light",
  primary_color: "#0B4F6C",
  secondary_color: "#148A99",
  logo_url: null,
  logo_dark_url: null,
  logo_mark_url: null,
  logo_mark_dark_url: null,
  logo_nav_url: null,
  logo_nav_dark_url: null,
  logo_sidebar_url: null,
  logo_sidebar_dark_url: null,
  logo_footer_url: null,
  logo_footer_dark_url: null,
  favicon_url: null,
  app_icon_url: null,
};

export type LandingNavItem = { id: string; label: string };
export type LandingStat = { value: string; label: string };
export type LandingPair = { title: string; body: string };
export type LandingStep = { step: string; title: string; body: string };
export type LandingFaq = { q: string; a: string };

export type LandingContent = {
  nav: LandingNavItem[];
  hero_eyebrow: string;
  hero_title: string;
  hero_body: string;
  hero_primary_cta: string;
  hero_secondary_cta: string;
  hero_secondary_href: string;
  stats: LandingStat[];
  pains_eyebrow: string;
  pains_title: string;
  pains_body: string;
  pains: LandingPair[];
  product_eyebrow: string;
  product_title: string;
  product_body: string;
  steps_eyebrow: string;
  steps_title: string;
  steps_body: string;
  steps: LandingStep[];
  workspace_eyebrow: string;
  workspace_title: string;
  workspace_body: string;
  control_plane_eyebrow: string;
  control_plane_title: string;
  control_plane_body: string;
  pricing_eyebrow: string;
  pricing_title: string;
  pricing_body: string;
  security_eyebrow: string;
  security_title: string;
  security_body: string;
  security: LandingPair[];
  faq_eyebrow: string;
  faq_title: string;
  faqs: LandingFaq[];
  cta_title: string;
  cta_body: string;
  cta_primary: string;
  cta_secondary: string;
  updated_at?: string;
};

export const defaultLanding: LandingContent = {
  nav: [
    { id: "product", label: "Product" },
    { id: "how-it-works", label: "How it works" },
    { id: "pricing", label: "Pricing" },
    { id: "security", label: "Security" },
    { id: "faq", label: "FAQ" },
  ],
  hero_eyebrow: "{owner}",
  hero_title: "Website intelligence, honest markets, and pipeline in one workspace.",
  hero_body:
    "{product} crawls your sites, scores SEO, AEO, and GEO, checks keywords through a licensed first-page sample, and can apply allowlisted fixes. Then it reads your own commerce, cites market signals you ingest, records opportunities, finds matching leads, and converts them in a native CRM. Empty stays empty. No invented #1 ranks or city grades.",
  hero_primary_cta: "Create workspace",
  hero_secondary_cta: "See the platform",
  hero_secondary_href: "#product",
  stats: [
    { value: "12", label: "Product modules" },
    { value: "SEO · AEO · GEO", label: "Crawl scores" },
    { value: "Licensed SERP", label: "Keyword sample, not scrape" },
    { value: "FACT tagged", label: "AI is never stored as fact" },
  ],
  pains_eyebrow: "Why teams switch",
  pains_title: "Growth should not start in a spreadsheet.",
  pains_body: "Website quality, your own commerce, market evidence, and pipeline belong in one system of record. {product} is built for that loop — not as a slide deck or a fake rank report.",
  pains: [
    { title: "Audits that never become action", body: "SEO reports sit in slides. {product} scores the crawl, checks stored keywords in the background, and can apply allowlisted on-page fixes while keeping the first audit as the baseline." },
    { title: "Invented ranks and city grades", body: "Most tools promise page one or Lahore = 92. Positions here come only from a licensed Custom Search or SerpAPI sample. Market scores stay empty until this workspace ingests signals." },
    { title: "Commerce, markets, and leads in three logins", body: "Import CSV or sync Shopify, WooCommerce, Etsy, or eBay. Read a cited Market Brief. Record opportunities. Discover accounts in the same Leads product. Copy buyers are existing customers, not scraped prospects." },
    { title: "Tools that do not share a tenant", body: "Crawler, licensed search, Claude or other package AI, enrichment, and CRM usually live apart. Usage, permissions, invoices, and the audit log should not." },
  ],
  product_eyebrow: "Product",
  product_title: "Everything {product} ships in one workspace.",
  product_body: "Modules are entitlements, not separate products. Operators assign what a tenant can run. Teams only see what they are licensed to use. Website intelligence and the growth loop share a login. They do not share scores.",
  steps_eyebrow: "How it works",
  steps_title: "From property to pipeline.",
  steps_body: "Each step is a real background job. The UI shows live progress — not a timer. Navigation only lists modules on the package.",
  steps: [
    { step: "01", title: "Connect websites", body: "Add public properties. Crawl and audit run as jobs. SEO, AEO, GEO, and opportunity scores come from the pages, not a black-box grade." },
    { step: "02", title: "Check keywords", body: "Stored SEO keywords (and homepage title if needed) are checked against a licensed first-page sample. Missing position means not in that sample — not a promised #1." },
    { step: "03", title: "Suggest and fix", body: "Heuristic queries always appear. Scale and Enterprise add Claude or another enabled provider using package AI credits. Optional WordPress, FTP, SFTP, or cPanel access applies allowlisted fixes only." },
    { step: "04", title: "Analyze the business", body: "Save the profile. Import CSV or sync a store. Revenue KPIs stay hidden until placed orders exist. Served cities are order geography, not demand grades." },
    { step: "05", title: "Markets and opportunities", body: "Market Brief cites stored commerce and ingested signals. Generate opportunities only from that evidence. No synthetic city league table." },
    { step: "06", title: "Discover leads", body: "Confirm an ICP. Discovery uses enabled platform sources. Enrichment does not invent email or phone. Copy buyers into Leads are existing customers." },
    { step: "07", title: "CRM and marketing", body: "Promote into native companies and deals. Record a campaign against lists or imported cities you already have. Send stores a count. {product} does not dispatch email." },
  ],
  workspace_eyebrow: "Tenant workspace",
  workspace_title: "For the company running growth",
  workspace_body: "Websites, audits, keyword ranks, allowlisted fixes, business and store sync, markets, opportunities, leads, CRM, marketing, Ask {product}, reports, and billing. Navigation only shows assigned modules.",
  control_plane_eyebrow: "Control plane",
  control_plane_title: "For {owner}",
  control_plane_body: "Tenants, packages, module entitlements, licensed search and AI keys, payment gateways, invoicing, landing page, and product appearance — one operator console. Tenants never paste their own Claude key.",
  pricing_eyebrow: "Pricing",
  pricing_title: "Packages that match how the product is sold.",
  pricing_body: "Each plan is an entitlement on the tenant: modules, page limits, audit volume, AI credits, and seats. Starter analyzes. Growth adds leads, CRM, and marketing. Scale adds the AI gateway and integrations. Enterprise adds AEO/GEO and commercial terms. Start on invoice. Card checkout waits until a gateway is enabled.",
  security_eyebrow: "Trust",
  security_title: "Enterprise controls without theatre.",
  security_body: "Claims match the platform: isolation, roles, audit, session cookies, server-side secrets, and guarded outbound fetch. No invented certifications.",
  security: [
    { title: "Tenant isolation", body: "Every workspace row carries a tenant. Managers, APIs, and background jobs enforce it." },
    { title: "RBAC", body: "System roles for operators, analysts, sellers, and marketers. Permissions are assigned, not implied." },
    { title: "Immutable audit log", body: "Platform and workspace actions are recorded with actor, resource, and request id." },
    { title: "Session security", body: "Browser sessions use HttpOnly JWT cookies. Refresh tokens never sit in JavaScript." },
    { title: "Server-side secrets", body: "Store tokens, site access, payment gateways, licensed search, and Claude keys stay on the server and are never returned to the browser." },
    { title: "Safe crawling and search", body: "Outbound fetch is SSRF-guarded. Keyword ranks use licensed Custom Search or SerpAPI. {product} does not scrape google.com." },
  ],
  faq_eyebrow: "FAQ",
  faq_title: "Straight answers.",
  faqs: [
    { q: "What is {product} for?", a: "Growth teams that need website intelligence, licensed keyword checks, first-party commerce analysis, cited market briefs, lead discovery, and CRM in one tenant — instead of stitching five tools and inventing the missing numbers." },
    { q: "Is this a white-label report builder?", a: "No. Audits produce explainable issues and scores. Keyword jobs show live progress. Leads are discovered against a confirmed ICP. CRM is native, with optional HubSpot or Odoo on Scale." },
    { q: "Do you scrape Google or promise a #1 rank?", a: "No. Positions come from a licensed Google Custom Search or SerpAPI first-page sample enabled by {owner}. A missing position means the domain was not in that sample. Suggestions are recommendations or inference, never a forecast." },
    { q: "Do you invent city demand grades?", a: "No. Served cities come from placed orders. Market scores stay empty until this workspace ingests or collects signals. Pakistan geography is a place catalog, not a league table." },
    { q: "Do you store AI answers as facts?", a: "No. Claude, OpenAI, Grok, or Gemini run through the AI module on Scale and Enterprise, using package credits. Output is tagged inference or recommendation. Heuristic next actions still appear when AI is off." },
    { q: "Which stores can we connect?", a: "Shopify, WooCommerce, Etsy, and eBay on the Business module (Starter and above). Secrets stay on the server. Amazon is not connected in this release. CSV templates remain available." },
    { q: "Who runs billing and packages?", a: "{owner} operators run the control plane: packages, module entitlements, invoices, payment gateways, licensed sources, landing page, and appearance. Tenant admins use the workspace they are assigned." },
    { q: "Can we start on Starter and upgrade?", a: "Yes. Packages are entitlements on the tenant. Growth adds lead intelligence, CRM, and marketing. Scale adds the AI gateway and integrations. Enterprise adds AEO/GEO and commercial terms." },
    { q: "Is there a trial?", a: "Starter and Growth include 14 days. Scale includes 7 days. Enterprise is scoped commercially." },
    { q: "How do we pay?", a: "Workspaces can start on invoice. Stripe and PayPal stay off until {owner} stores gateway credentials in the control plane." },
  ],
  cta_title: "Put evidence and pipeline on the same desk.",
  cta_body: "Create a workspace, or sign in if {owner} already provisioned your tenant.",
  cta_primary: "Create workspace",
  cta_secondary: "Sign in",
};

export type NotificationItem = {
  id: string;
  title: string;
  body: string;
  kind: string;
  link: string;
  read_at: string | null;
  created_at: string;
};

export type DashboardOverview = {
  overview: {
    websites: number;
    audits: number;
    total_leads: number;
    qualified_leads: number;
    opportunities: number;
    crm_deals?: number;
    growth_opportunities?: number;
    campaigns?: number;
    crm_synced: number;
    commerce_orders?: number;
    commerce_revenue?: string | null;
    served_cities?: number;
    expansion_cities?: number;
  };
  intelligence: {
    website_health: number | null;
    seo_score: number | null;
    aeo_score: number | null;
    geo_score: number | null;
    opportunity_score: number | null;
    performance_score: number | null;
  };
  lead_intelligence: {
    by_industry: Array<{ industry: string; count: number }>;
    by_location: Array<{ location: string; count: number }>;
    score_distribution: Array<{ label: string; count: number }>;
    opportunity_distribution: Array<{ label: string; count: number }>;
    data_quality: {
      leads: number;
      with_website: number;
      with_email: number;
      with_phone: number;
      with_location: number;
      with_industry: number;
      avg_quality_score: number | null;
    } | null;
    new_leads_over_time: Array<{ day: string; count: number }>;
  };
  activity: Array<{ id: string; title: string; action?: string; actor?: string; created_at: string }>;
  ai_usage: {
    credits: number;
    credits_used?: number;
    credits_limit?: number;
    credits_remaining?: number;
    tokens: number;
    cost: number;
    trend: unknown[];
  };
  modules?: Record<string, boolean>;
};

export type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type ProductModule = {
  id: string;
  code: string;
  name: string;
  description: string;
  category: string;
  is_active: boolean;
  sort_order: number;
  features: Array<{ id: string; code: string; name: string; description: string; is_active: boolean }>;
};

export type PlanPackage = {
  id: string;
  code: string;
  name: string;
  description: string;
  price_amount: string;
  currency: string;
  interval: string;
  trial_days: number;
  max_pages: number;
  max_audits_per_month: number;
  ai_credits: number;
  max_users: number;
  is_active: boolean;
  is_public: boolean;
  is_featured: boolean;
  cta_label: string;
  cta_href: string;
  sort_order: number;
  modules: Array<{ id: string; code: string; name: string; is_included: boolean }>;
};

export type PublicConfig = {
  product: string;
  owner: string;
  version: string;
  feature_flags: Record<string, boolean>;
  branding: PlatformBranding;
  landing: LandingContent;
  packages: PlanPackage[];
  modules: ProductModule[];
};

export type PaymentGateway = {
  id: string;
  code: string;
  provider: string;
  display_name: string;
  is_enabled: boolean;
  is_default: boolean;
  test_mode: boolean;
  public_config: Record<string, unknown>;
  credentials_configured: boolean;
  updated_at: string;
};

export type LeadSource = {
  id: string;
  code: string;
  provider: string;
  category: "discovery" | "enrichment" | "ai" | "diagnostics";
  display_name: string;
  purpose: string;
  is_enabled: boolean;
  setup_hint: string;
  sort_order: number;
  credentials_configured: boolean;
  requires_key?: boolean;
  homepage_url?: string;
  search_url?: string;
  model: string;
  updated_at: string;
};

export type PlatformInvoice = {
  id: string;
  number: string;
  status: string;
  currency: string;
  subtotal: string;
  tax: string;
  total: string;
  due_at: string | null;
  issued_at: string | null;
  paid_at: string | null;
  notes: string;
  tenant_id: string;
  tenant_name: string;
  gateway_name: string | null;
  plan_id?: string | null;
  plan_name?: string | null;
  lines: Array<{ id: string; description: string; quantity: number; unit_amount: string; amount: string }>;
  created_at: string;
};

export type PlatformSubscription = {
  id: string;
  status: string;
  plan: PlanPackage;
  tenant_id: string;
  tenant_name: string;
  seats: number;
  current_period_end: string | null;
  gateway_name: string | null;
  created_at: string;
};

export type TenantModuleAssignment = {
  id: string;
  code: string;
  name: string;
  category: string;
  is_enabled: boolean;
  source: string;
  limits: Record<string, unknown>;
};

export type PlatformTenant = {
  id: string;
  name: string;
  slug: string;
  status: string;
  feature_flags: Record<string, unknown>;
  member_count: number;
  subscription: PlatformSubscription | null;
  modules: TenantModuleAssignment[];
  ai_usage?: {
    credits_used: number;
    credits_limit: number;
    credits_remaining: number;
    tokens: number;
    requests: number;
  };
  created_at: string;
  updated_at: string;
};

export type PlatformAdmin = {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  is_superuser: boolean;
  last_login: string | null;
  date_joined: string;
};

export type PlatformOverview = {
  tenants: { total: number; active: number; suspended: number; pending: number };
  users: number;
  subscriptions: { trialing: number; active: number; past_due: number; canceled: number };
  invoices: { issued: number; paid: number; overdue: number; outstanding: string; collected: string };
  packages: number;
  gateways: number;
  lead_sources: number;
  modules: number;
  ai?: { requests: number; tokens: number };
  telemetry?: { prompts: number; asks: number; page_views: number };
  recent_tenants: Array<{ id: string; name: string; status: string; created_at: string }>;
  activity?: Array<{ id: string; title: string; action?: string; actor?: string; created_at: string }>;
};

export type PlatformPromptLog = {
  id: string;
  tenant: string;
  tenant_name: string;
  user_email: string;
  provider: string;
  model: string;
  task: string;
  status: string;
  prompt: string;
  untrusted_input: string;
  response_text: string;
  prompt_tokens: number;
  completion_tokens: number;
  duration_ms: number;
  error: string;
  created_at: string;
};

export type PlatformAskLog = {
  id: string;
  tenant: string;
  tenant_name: string;
  user_email: string;
  question: string;
  intent: string;
  origin: string;
  facts: string[];
  why: string;
  created_at: string;
};

export type PlatformPageLog = {
  id: string;
  tenant: string;
  tenant_name: string;
  user_email: string;
  path: string;
  title: string;
  referrer: string;
  ip_address: string | null;
  user_agent: string;
  created_at: string;
};

export type PlatformActivityLog = {
  id: string;
  title: string;
  action: string;
  actor: string;
  created_at: string;
  resource_type?: string;
  scope?: string;
  tenant_id?: string;
  tenant_name?: string;
  metadata?: Record<string, unknown>;
};
