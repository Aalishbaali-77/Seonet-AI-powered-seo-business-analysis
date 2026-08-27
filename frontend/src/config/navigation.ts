export type FeatureFlagKey =
  | "AI_AEO_ENABLED"
  | "LEAD_DISCOVERY_ENABLED"
  | "HUBSPOT_ENABLED"
  | "ODOO_ENABLED"
  | "WHITE_LABEL_ENABLED";

export type NavItem = {
  id: string;
  label: string;
  href: string;
  flag?: FeatureFlagKey;
  module?: string;
  bypassLock?: boolean;
  children?: NavItem[];
};

export const navigation: NavItem[] = [
  { id: "dashboard", label: "Dashboard", href: "/app/dashboard" },
  { id: "ask", label: "Ask Seonet", href: "/app/ask" },
  {
    id: "business",
    label: "Business Analysis",
    href: "/app/business",
    module: "business",
    children: [
      { id: "business-overview", label: "Overview", href: "/app/business", module: "business" },
      { id: "business-sales", label: "Sales", href: "/app/business/sales", module: "business" },
      { id: "business-products", label: "Products", href: "/app/business/products", module: "business" },
      { id: "business-customers", label: "Customers", href: "/app/business/customers", module: "business" },
      { id: "business-ecommerce", label: "E-Commerce", href: "/app/business/ecommerce", module: "business" },
      { id: "business-geography", label: "Geography", href: "/app/business/geography", module: "business" },
      { id: "business-advisor", label: "AI Advisor", href: "/app/business/advisor", module: "business" },
    ],
  },
  {
    id: "markets",
    label: "Market Intelligence",
    href: "/app/markets",
    module: "markets",
    children: [
      { id: "market-overview", label: "Market Brief", href: "/app/markets", module: "markets" },
      { id: "market-demand", label: "Demand", href: "/app/markets/demand", module: "markets" },
      { id: "market-places", label: "Markets", href: "/app/markets/places", module: "markets" },
      { id: "market-competition", label: "Competition", href: "/app/markets/competition", module: "markets" },
      { id: "market-segments", label: "Customer Segments", href: "/app/markets/segments", module: "markets" },
      { id: "market-scoring", label: "Scoring", href: "/app/markets/scoring", module: "markets" },
      { id: "market-advisor", label: "AI Advisor", href: "/app/markets/advisor", module: "markets" },
    ],
  },
  {
    id: "opportunities",
    label: "Opportunities",
    href: "/app/opportunities",
    module: "opportunities",
    children: [
      { id: "opportunity-list", label: "Pipeline", href: "/app/opportunities", module: "opportunities" },
      { id: "opportunity-advisor", label: "AI Advisor", href: "/app/opportunities/advisor", module: "opportunities" },
    ],
  },
  {
    id: "intelligence",
    label: "Website Intelligence",
    href: "/app/websites",
    module: "websites",
    children: [
      { id: "websites", label: "Websites", href: "/app/websites", module: "websites" },
      { id: "audits", label: "Audits", href: "/app/audits", module: "audits" },
      { id: "seo", label: "SEO", href: "/app/seo", module: "audits" },
      { id: "aeo", label: "AEO/GEO", href: "/app/aeo", module: "audits" },
      { id: "performance", label: "Performance", href: "/app/performance", module: "audits" },
    ],
  },
  {
    id: "leads",
    label: "Leads",
    href: "/app/leads",
    module: "leads",
    children: [
      { id: "all-leads", label: "All leads", href: "/app/leads", module: "leads" },
      { id: "discover", label: "Lead Discovery", href: "/app/leads/discover", module: "leads" },
      { id: "lists", label: "Lead Lists", href: "/app/leads/lists", module: "leads" },
      { id: "enrichment", label: "Enrichment", href: "/app/leads/enrichment", module: "leads" },
      { id: "scoring", label: "Scoring", href: "/app/leads/scoring", module: "leads" },
      { id: "lead-advisor", label: "AI Advisor", href: "/app/leads/advisor", module: "leads" },
    ],
  },
  {
    id: "crm",
    label: "CRM",
    href: "/app/crm",
    module: "crm",
    children: [
      { id: "crm-pipelines", label: "Pipelines", href: "/app/crm/pipelines", module: "crm" },
      { id: "crm-leads", label: "Leads", href: "/app/crm/leads", module: "crm" },
      { id: "companies", label: "Companies", href: "/app/crm/companies", module: "crm" },
      { id: "contacts", label: "Contacts", href: "/app/crm/contacts", module: "crm" },
      { id: "deals", label: "Deals", href: "/app/crm/deals", module: "crm" },
      { id: "activities", label: "Activities", href: "/app/crm/activities", module: "crm" },
    ],
  },
  { id: "marketing", label: "Marketing", href: "/app/marketing", module: "marketing" },
  { id: "reports", label: "Reports", href: "/app/reports", module: "reports" },
  { id: "integrations", label: "Integrations", href: "/app/integrations" },
  { id: "billing", label: "Subscription", href: "/app/billing", bypassLock: true },
  { id: "usage", label: "Usage", href: "/app/usage" },
  {
    id: "settings",
    label: "Settings",
    href: "/app/settings",
    bypassLock: true,
    children: [
      { id: "settings-workspace", label: "Workspace", href: "/app/settings", bypassLock: true },
      { id: "settings-team", label: "Team", href: "/app/settings/team", bypassLock: true },
      { id: "settings-roles", label: "Roles & permissions", href: "/app/settings/roles", bypassLock: true },
      { id: "settings-api", label: "API keys", href: "/app/settings/api", bypassLock: true },
      { id: "settings-jobs", label: "Jobs", href: "/app/jobs" },
    ],
  },
];

export const platformNavigation: NavItem[] = [
  { id: "platform-home", label: "Control plane", href: "/platform" },
  { id: "platform-tenants", label: "Tenants", href: "/platform/tenants" },
  { id: "platform-packages", label: "Packages", href: "/platform/packages" },
  { id: "platform-modules", label: "Modules & features", href: "/platform/modules" },
  { id: "platform-landing", label: "Landing page", href: "/platform/landing" },
  { id: "platform-subscriptions", label: "Subscriptions", href: "/platform/subscriptions" },
  { id: "platform-invoices", label: "Invoicing", href: "/platform/invoices" },
  { id: "platform-gateways", label: "Payment gateways", href: "/platform/gateways" },
  { id: "platform-lead-sources", label: "API sources", href: "/platform/lead-sources" },
  { id: "platform-telemetry", label: "Tenant activity", href: "/platform/activity" },
  { id: "platform-settings", label: "Settings", href: "/platform/settings" },
];
