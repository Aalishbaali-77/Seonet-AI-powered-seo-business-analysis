import type { LandingContent, PlanPackage, PlatformBranding } from "@/types/api";

export function fillCopy(text: string, branding: PlatformBranding) {
  return text
    .replaceAll("{product}", branding.product_name)
    .replaceAll("{owner}", branding.legal_name)
    .replaceAll("{description}", branding.description)
    .replaceAll("{tagline}", branding.tagline);
}

export function interpolateLanding(landing: LandingContent, branding: PlatformBranding): LandingContent {
  const text = (value: string) => fillCopy(value, branding);
  return {
    ...landing,
    hero_eyebrow: text(landing.hero_eyebrow),
    hero_title: text(landing.hero_title),
    hero_body: text(landing.hero_body),
    pains_eyebrow: text(landing.pains_eyebrow),
    pains_title: text(landing.pains_title),
    pains_body: text(landing.pains_body),
    pains: landing.pains.map((item) => ({ title: text(item.title), body: text(item.body) })),
    product_eyebrow: text(landing.product_eyebrow),
    product_title: text(landing.product_title),
    product_body: text(landing.product_body),
    steps_eyebrow: text(landing.steps_eyebrow),
    steps_title: text(landing.steps_title),
    steps_body: text(landing.steps_body),
    steps: landing.steps.map((item) => ({ ...item, title: text(item.title), body: text(item.body) })),
    workspace_eyebrow: text(landing.workspace_eyebrow),
    workspace_title: text(landing.workspace_title),
    workspace_body: text(landing.workspace_body),
    control_plane_eyebrow: text(landing.control_plane_eyebrow),
    control_plane_title: text(landing.control_plane_title),
    control_plane_body: text(landing.control_plane_body),
    pricing_eyebrow: text(landing.pricing_eyebrow),
    pricing_title: text(landing.pricing_title),
    pricing_body: text(landing.pricing_body),
    security_eyebrow: text(landing.security_eyebrow),
    security_title: text(landing.security_title),
    security_body: text(landing.security_body),
    security: landing.security.map((item) => ({ title: text(item.title), body: text(item.body) })),
    faq_eyebrow: text(landing.faq_eyebrow),
    faq_title: text(landing.faq_title),
    faqs: landing.faqs.map((item) => ({ q: text(item.q), a: text(item.a) })),
    cta_title: text(landing.cta_title),
    cta_body: text(landing.cta_body),
  };
}

export function formatPlanPrice(plan: PlanPackage) {
  const amount = Number(plan.price_amount);
  if (!Number.isFinite(amount) || amount <= 0) {
    return "Custom";
  }
  const prefix = plan.currency === "USD" ? "$" : `${plan.currency} `;
  return `${prefix}${Number.isInteger(amount) ? amount.toFixed(0) : amount.toFixed(2)}`;
}

export function planCadence(plan: PlanPackage) {
  const amount = Number(plan.price_amount);
  if (!Number.isFinite(amount) || amount <= 0) {
    return "";
  }
  return plan.interval === "year" ? "/ year" : "/ month";
}

export function planCta(plan: PlanPackage, supportUrl?: string) {
  const custom = Number(plan.price_amount) <= 0;
  return {
    label: plan.cta_label || (custom ? "Talk to sales" : `Start ${plan.name}`),
    href: plan.cta_href || (custom && supportUrl ? supportUrl : "/register"),
    external: Boolean(plan.cta_href?.startsWith("http") || (custom && supportUrl && !plan.cta_href)),
  };
}

export function planFeatureList(plan: PlanPackage, previous?: PlanPackage) {
  const items: string[] = [];
  const included = plan.modules.filter((item) => item.is_included);
  const previousCodes = new Set((previous?.modules ?? []).filter((item) => item.is_included).map((item) => item.code));
  if (previous) {
    items.push(`Everything in ${previous.name}`);
  }
  included.forEach((item) => {
    if (!previousCodes.has(item.code)) {
      items.push(item.name);
    }
  });
  items.push(`${plan.max_pages.toLocaleString()} pages`);
  items.push(`${plan.max_audits_per_month.toLocaleString()} audits / month`);
  items.push(`${plan.ai_credits.toLocaleString()} AI credits`);
  items.push(`${plan.max_users.toLocaleString()} seats`);
  if (plan.trial_days) {
    items.push(`${plan.trial_days}-day trial`);
  }
  return items;
}
