from __future__ import annotations

from copy import deepcopy

from rest_framework import serializers

DEFAULT_LANDING: dict = {
    "nav": [
        {"id": "product", "label": "Product"},
        {"id": "how-it-works", "label": "How it works"},
        {"id": "pricing", "label": "Pricing"},
        {"id": "security", "label": "Security"},
        {"id": "faq", "label": "FAQ"},
    ],
    "hero_eyebrow": "{owner}",
    "hero_title": "Website intelligence, honest markets, and pipeline in one workspace.",
    "hero_body": "{product} crawls your sites, scores SEO, AEO, and GEO, checks keywords through a licensed first-page sample, and can apply allowlisted fixes. Then it reads your own commerce, cites market signals you ingest, records opportunities, finds matching leads, and converts them in a native CRM. Empty stays empty. No invented #1 ranks or city grades.",
    "hero_primary_cta": "Create workspace",
    "hero_secondary_cta": "See the platform",
    "hero_secondary_href": "#product",
    "stats": [
        {"value": "12", "label": "Product modules"},
        {"value": "SEO · AEO · GEO", "label": "Crawl scores"},
        {"value": "Licensed SERP", "label": "Keyword sample, not scrape"},
        {"value": "FACT tagged", "label": "AI is never stored as fact"},
    ],
    "pains_eyebrow": "Why teams switch",
    "pains_title": "Growth should not start in a spreadsheet.",
    "pains_body": "Website quality, your own commerce, market evidence, and pipeline belong in one system of record. {product} is built for that loop — not as a slide deck or a fake rank report.",
    "pains": [
        {
            "title": "Audits that never become action",
            "body": "SEO reports sit in slides. {product} scores the crawl, checks stored keywords in the background, and can apply allowlisted on-page fixes while keeping the first audit as the baseline.",
        },
        {
            "title": "Invented ranks and city grades",
            "body": "Most tools promise page one or Lahore = 92. Positions here come only from a licensed Custom Search or SerpAPI sample. Market scores stay empty until this workspace ingests signals.",
        },
        {
            "title": "Commerce, markets, and leads in three logins",
            "body": "Import CSV or sync Shopify, WooCommerce, Etsy, or eBay. Read a cited Market Brief. Record opportunities. Discover accounts in the same Leads product. Copy buyers are existing customers, not scraped prospects.",
        },
        {
            "title": "Tools that do not share a tenant",
            "body": "Crawler, licensed search, Claude or other package AI, enrichment, and CRM usually live apart. Usage, permissions, invoices, and the audit log should not.",
        },
    ],
    "product_eyebrow": "Product",
    "product_title": "Everything {product} ships in one workspace.",
    "product_body": "Modules are entitlements, not separate products. Operators assign what a tenant can run. Teams only see what they are licensed to use. Website intelligence and the growth loop share a login. They do not share scores.",
    "steps_eyebrow": "How it works",
    "steps_title": "From property to pipeline.",
    "steps_body": "Each step is a real background job. The UI shows live progress — not a timer. Navigation only lists modules on the package.",
    "steps": [
        {"step": "01", "title": "Connect websites", "body": "Add public properties. Crawl and audit run as jobs. SEO, AEO, GEO, and opportunity scores come from the pages, not a black-box grade."},
        {"step": "02", "title": "Check keywords", "body": "Stored SEO keywords (and homepage title if needed) are checked against a licensed first-page sample. Missing position means not in that sample — not a promised #1."},
        {"step": "03", "title": "Suggest and fix", "body": "Heuristic queries always appear. Scale and Enterprise add Claude or another enabled provider using package AI credits. Optional WordPress, FTP, SFTP, or cPanel access applies allowlisted fixes only."},
        {"step": "04", "title": "Analyze the business", "body": "Save the profile. Import CSV or sync a store. Revenue KPIs stay hidden until placed orders exist. Served cities are order geography, not demand grades."},
        {"step": "05", "title": "Markets and opportunities", "body": "Market Brief cites stored commerce and ingested signals. Generate opportunities only from that evidence. No synthetic city league table."},
        {"step": "06", "title": "Discover leads", "body": "Confirm an ICP. Discovery uses enabled platform sources. Enrichment does not invent email or phone. Copy buyers into Leads are existing customers."},
        {"step": "07", "title": "CRM and marketing", "body": "Promote into native companies and deals. Record a campaign against lists or imported cities you already have. Send stores a count. {product} does not dispatch email."},
    ],
    "workspace_eyebrow": "Tenant workspace",
    "workspace_title": "For the company running growth",
    "workspace_body": "Websites, audits, keyword ranks, allowlisted fixes, business and store sync, markets, opportunities, leads, CRM, marketing, Ask {product}, reports, and billing. Navigation only shows assigned modules.",
    "control_plane_eyebrow": "Control plane",
    "control_plane_title": "For {owner}",
    "control_plane_body": "Tenants, packages, module entitlements, licensed search and AI keys, payment gateways, invoicing, landing page, and product appearance — one operator console. Tenants never paste their own Claude key.",
    "pricing_eyebrow": "Pricing",
    "pricing_title": "Packages that match how the product is sold.",
    "pricing_body": "Each plan is an entitlement on the tenant: modules, page limits, audit volume, AI credits, and seats. Starter analyzes. Growth adds leads, CRM, and marketing. Scale adds the AI gateway and integrations. Enterprise adds AEO/GEO and commercial terms. Start on invoice. Card checkout waits until a gateway is enabled.",
    "security_eyebrow": "Trust",
    "security_title": "Enterprise controls without theatre.",
    "security_body": "Claims match the platform: isolation, roles, audit, session cookies, server-side secrets, and guarded outbound fetch. No invented certifications.",
    "security": [
        {"title": "Tenant isolation", "body": "Every workspace row carries a tenant. Managers, APIs, and background jobs enforce it."},
        {"title": "RBAC", "body": "System roles for operators, analysts, sellers, and marketers. Permissions are assigned, not implied."},
        {"title": "Immutable audit log", "body": "Platform and workspace actions are recorded with actor, resource, and request id."},
        {"title": "Session security", "body": "Browser sessions use HttpOnly JWT cookies. Refresh tokens never sit in JavaScript."},
        {"title": "Server-side secrets", "body": "Store tokens, site access, payment gateways, licensed search, and Claude keys stay on the server and are never returned to the browser."},
        {"title": "Safe crawling and search", "body": "Outbound fetch is SSRF-guarded. Keyword ranks use licensed Custom Search or SerpAPI. {product} does not scrape google.com."},
    ],
    "faq_eyebrow": "FAQ",
    "faq_title": "Straight answers.",
    "faqs": [
        {
            "q": "What is {product} for?",
            "a": "Growth teams that need website intelligence, licensed keyword checks, first-party commerce analysis, cited market briefs, lead discovery, and CRM in one tenant — instead of stitching five tools and inventing the missing numbers.",
        },
        {
            "q": "Is this a white-label report builder?",
            "a": "No. Audits produce explainable issues and scores. Keyword jobs show live progress. Leads are discovered against a confirmed ICP. CRM is native, with optional HubSpot or Odoo on Scale.",
        },
        {
            "q": "Do you scrape Google or promise a #1 rank?",
            "a": "No. Positions come from a licensed Google Custom Search or SerpAPI first-page sample enabled by {owner}. A missing position means the domain was not in that sample. Suggestions are recommendations or inference, never a forecast.",
        },
        {
            "q": "Do you invent city demand grades?",
            "a": "No. Served cities come from placed orders. Market scores stay empty until this workspace ingests or collects signals. Pakistan geography is a place catalog, not a league table.",
        },
        {
            "q": "Do you store AI answers as facts?",
            "a": "No. Claude, OpenAI, Grok, or Gemini run through the AI module on Scale and Enterprise, using package credits. Output is tagged inference or recommendation. Heuristic next actions still appear when AI is off.",
        },
        {
            "q": "Which stores can we connect?",
            "a": "Shopify, WooCommerce, Etsy, and eBay on the Business module (Starter and above). Secrets stay on the server. Amazon is not connected in this release. CSV templates remain available.",
        },
        {
            "q": "Who runs billing and packages?",
            "a": "{owner} operators run the control plane: packages, module entitlements, invoices, payment gateways, licensed sources, landing page, and appearance. Tenant admins use the workspace they are assigned.",
        },
        {
            "q": "Can we start on Starter and upgrade?",
            "a": "Yes. Packages are entitlements on the tenant. Growth adds lead intelligence, CRM, and marketing. Scale adds the AI gateway and integrations. Enterprise adds AEO/GEO and commercial terms.",
        },
        {
            "q": "Is there a trial?",
            "a": "Starter and Growth include 14 days. Scale includes 7 days. Enterprise is scoped commercially.",
        },
        {
            "q": "How do we pay?",
            "a": "Workspaces can start on invoice. Stripe and PayPal stay off until {owner} stores gateway credentials in the control plane.",
        },
    ],
    "cta_title": "Put evidence and pipeline on the same desk.",
    "cta_body": "Create a workspace, or sign in if {owner} already provisioned your tenant.",
    "cta_primary": "Create workspace",
    "cta_secondary": "Sign in",
}


def default_nav():
    return deepcopy(DEFAULT_LANDING["nav"])


def default_stats():
    return deepcopy(DEFAULT_LANDING["stats"])


def default_pains():
    return deepcopy(DEFAULT_LANDING["pains"])


def default_steps():
    return deepcopy(DEFAULT_LANDING["steps"])


def default_security():
    return deepcopy(DEFAULT_LANDING["security"])


def default_faqs():
    return deepcopy(DEFAULT_LANDING["faqs"])


ITEM_SPECS = {
    "nav": ("id", "label"),
    "stats": ("value", "label"),
    "pains": ("title", "body"),
    "steps": ("step", "title", "body"),
    "security": ("title", "body"),
    "faqs": ("q", "a"),
}


def validate_item_list(value, *, keys: tuple[str, ...], label: str, max_items: int = 16) -> list[dict]:
    if not isinstance(value, list):
        raise serializers.ValidationError(f"{label} must be a list.")
    if len(value) > max_items:
        raise serializers.ValidationError(f"{label} cannot have more than {max_items} items.")
    cleaned: list[dict] = []
    for index, raw in enumerate(value):
        if not isinstance(raw, dict):
            raise serializers.ValidationError(f"{label} item {index + 1} is invalid.")
        item = {}
        for key in keys:
            text = str(raw.get(key, "")).strip()
            if not text:
                raise serializers.ValidationError(f"{label} item {index + 1} needs {key}.")
            if len(text) > 2000:
                raise serializers.ValidationError(f"{label} item {index + 1} {key} is too long.")
            item[key] = text
        cleaned.append(item)
    return cleaned
