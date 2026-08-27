from __future__ import annotations

PUSH_TOGGLES: list[dict] = [
    {
        "key": "push_leads",
        "label": "Send leads here",
        "secret": False,
        "required": False,
        "input": "toggle",
        "help": "New and updated leads are posted automatically after you connect.",
    },
    {
        "key": "push_results",
        "label": "Send audit results here",
        "secret": False,
        "required": False,
        "input": "toggle",
        "help": "Completed website audits are posted automatically after you connect.",
    },
]


def _fields(*fields: dict, push: bool = True) -> list[dict]:
    items = list(fields)
    if push:
        items.extend(PUSH_TOGGLES)
    return items


PROVIDERS: list[dict] = [
    {
        "code": "native",
        "name": "SIPulse CRM",
        "category": "crm",
        "connectable": False,
        "required_module": "crm",
        "description": "Companies, contacts, pipelines, and deals that already live in this workspace. No API key required.",
        "setup_steps": [],
        "fields": [],
    },
    {
        "code": "hubspot",
        "name": "HubSpot",
        "category": "crm",
        "connectable": True,
        "required_module": "integrations",
        "description": "Push qualified companies, contacts, and audit notes into HubSpot with a private app token. Secrets stay on the server.",
        "setup_steps": [
            "Sign in to HubSpot in your browser.",
            "Click the settings gear in the top right.",
            "Open Integrations, then Private Apps.",
            "Click Create a private app and name it SIPulse.",
            "Open the Scopes tab. Turn on read and write for companies, contacts, and notes (crm.objects.companies, crm.objects.contacts, crm.objects.notes).",
            "Click Create app, then Show token. Copy the token and paste it below. Treat it like a password.",
            "Save, then click Test connection. New leads and finished audits will be sent to HubSpot automatically.",
        ],
        "fields": _fields(
            {"key": "access_token", "label": "Private app token", "secret": True, "required": True, "input": "password"},
        ),
    },
    {
        "code": "odoo",
        "name": "Odoo",
        "category": "erp",
        "connectable": True,
        "required_module": "integrations",
        "description": "Push companies and audit notes into Odoo over JSON-RPC. Use a public HTTPS URL on port 443.",
        "setup_steps": [
            "Open your Odoo in the browser. The address must start with https://.",
            "Copy the address from the bar, stopping at the domain (for example https://odoo.yourcompany.com).",
            "Ask your Odoo administrator for the database name.",
            "Use the email you already use to sign in to Odoo.",
            "In Odoo go to Settings → Users → your user → Account Security → New API Key. Copy that key (or use your password if your server still uses one).",
            "Paste the URL, database, username, and key below. Save, then Test connection.",
        ],
        "fields": _fields(
            {"key": "base_url", "label": "Odoo URL", "secret": False, "required": True, "input": "url"},
            {"key": "database", "label": "Database", "secret": False, "required": True, "input": "text"},
            {"key": "username", "label": "Username", "secret": False, "required": True, "input": "text"},
            {"key": "api_key", "label": "API key or password", "secret": True, "required": True, "input": "password"},
        ),
    },
    {
        "code": "custom_api",
        "name": "Custom REST / ERP",
        "category": "erp",
        "connectable": True,
        "required_module": "integrations",
        "description": "Any HTTPS REST API. SIPulse POSTs leads and audit results with your API key. Secrets stay on the server.",
        "setup_steps": [
            "Ask your developer or ERP vendor for an HTTPS address (for example https://erp.yourcompany.com).",
            "Ask for an API key that is allowed to create records.",
            "SIPulse will POST new leads as JSON to /leads and finished audits to /results on that address. You can change those paths below if your API uses different ones.",
            "Paste the base URL and API key. If the API expects X-API-Key instead of a Bearer token, choose that header.",
            "Save, then Test connection.",
        ],
        "fields": _fields(
            {"key": "base_url", "label": "Base URL", "secret": False, "required": True, "input": "url"},
            {"key": "health_path", "label": "Health path", "secret": False, "required": False, "input": "text", "help": "Optional path used only to test the connection."},
            {"key": "leads_path", "label": "Leads path", "secret": False, "required": False, "input": "text", "help": "Default /leads. SIPulse POSTs JSON here."},
            {"key": "results_path", "label": "Results path", "secret": False, "required": False, "input": "text", "help": "Default /results. SIPulse POSTs JSON here."},
            {"key": "auth_header", "label": "Auth header name", "secret": False, "required": False, "input": "text"},
            {"key": "api_key", "label": "API key", "secret": True, "required": True, "input": "password"},
        ),
    },
    {
        "code": "google_sheets",
        "name": "Google Sheets",
        "category": "sheets",
        "connectable": True,
        "required_module": "integrations",
        "description": "Append leads and audit results as new rows in your spreadsheet. Uses a Google Cloud service account so SIPulse can write without anyone staying signed in.",
        "setup_steps": [
            "In Google Drive, click New → Google Sheets. Name it something like SIPulse leads.",
            "Look at the browser address. Copy the long ID between /d/ and /edit. You can also paste the whole address below.",
            "Open https://console.cloud.google.com and sign in with the same Google account that owns the Sheet.",
            "Click the project picker at the top → New project. Name it SIPulse and click Create. Select that project if it is not already selected.",
            "Open the menu (three lines) → APIs & Services → Library. Search for Google Sheets API and click Enable.",
            "Open APIs & Services → Credentials → Create credentials → Service account. Name it sipulse-sheets and click Done (you can skip optional steps).",
            "Click the service account you just created. Open the Keys tab → Add key → Create new key → JSON. A file downloads to your computer. Keep it private.",
            "Open that JSON file in Notepad (Windows) or TextEdit (Mac). Select all, copy it, and paste it into the JSON box below.",
            "In the JSON, find client_email (it looks like sipulse-sheets@….iam.gserviceaccount.com). Open your Google Sheet → Share, paste that email, choose Editor, uncheck Notify people, then Share.",
            "Paste the spreadsheet ID or URL below, save, then click Test connection. New leads go to the Leads tab and finished audits go to the Audit results tab.",
        ],
        "fields": _fields(
            {
                "key": "spreadsheet_id",
                "label": "Spreadsheet ID or URL",
                "secret": False,
                "required": True,
                "input": "text",
                "help": "Paste the full Google Sheets address or the ID between /d/ and /edit.",
            },
            {
                "key": "leads_tab",
                "label": "Leads tab name",
                "secret": False,
                "required": False,
                "input": "text",
                "help": "Created automatically if it does not exist. Default: Leads.",
            },
            {
                "key": "results_tab",
                "label": "Results tab name",
                "secret": False,
                "required": False,
                "input": "text",
                "help": "Created automatically if it does not exist. Default: Audit results.",
            },
            {
                "key": "service_account_json",
                "label": "Service account JSON",
                "secret": True,
                "required": True,
                "input": "textarea",
                "help": "Paste the entire downloaded JSON file. It is stored on the server and never shown again.",
            },
        ),
    },
    {
        "code": "webhook",
        "name": "Outbound webhook",
        "category": "webhook",
        "connectable": True,
        "required_module": "integrations",
        "description": "Receive signed HTTPS callbacks when leads are created or updated and when audits finish. The signing secret is shown once.",
        "setup_steps": [
            "Ask your developer for an HTTPS address that can receive JSON posts.",
            "Paste that address below and tick the events you want (lead.created, lead.updated, and audit.completed cover leads and results).",
            "Save. Copy the signing secret immediately — it is shown only once. Your developer checks the X-SIPulse-Signature header.",
            "Click Test connection. We send a small ping so they can confirm the URL works.",
        ],
        "fields": _fields(
            {"key": "url", "label": "Endpoint URL", "secret": False, "required": True, "input": "url"},
            {"key": "events", "label": "Events", "secret": False, "required": False, "input": "events"},
            push=False,
        ),
    },
    {
        "code": "shopify",
        "name": "Shopify",
        "category": "commerce",
        "connectable": True,
        "required_module": "business",
        "description": "Pull products, orders, and customers from a Shopify Admin API custom app. KPIs stay empty until a sync stores rows.",
        "setup_steps": [
            "In Shopify admin open Settings → Apps and sales channels → Develop apps.",
            "Create an app named SIPulse. Open API credentials and install the app on the shop.",
            "Grant read_products, read_orders, and read_customers. Copy the Admin API access token.",
            "Paste the shop domain (your-store.myshopify.com) and the token. Save, Test connection, then Sync store.",
        ],
        "fields": [
            {"key": "shop_domain", "label": "Shop domain", "secret": False, "required": True, "input": "text", "help": "Example: your-store.myshopify.com"},
            {"key": "access_token", "label": "Admin API access token", "secret": True, "required": True, "input": "password"},
        ],
    },
    {
        "code": "woocommerce",
        "name": "WooCommerce",
        "category": "commerce",
        "connectable": True,
        "required_module": "business",
        "description": "Pull products, orders, customers, and product reviews from WooCommerce REST API. Sentiment is counted from stored star ratings.",
        "setup_steps": [
            "In WordPress open WooCommerce → Settings → Advanced → REST API.",
            "Add a key with Read permission. Copy the consumer key and consumer secret.",
            "Paste the public store HTTPS URL plus both keys. Save, Test connection, then Sync store.",
        ],
        "fields": [
            {"key": "base_url", "label": "Store URL", "secret": False, "required": True, "input": "url"},
            {"key": "consumer_key", "label": "Consumer key", "secret": True, "required": True, "input": "password"},
            {"key": "consumer_secret", "label": "Consumer secret", "secret": True, "required": True, "input": "password"},
        ],
    },
    {
        "code": "etsy",
        "name": "Etsy",
        "category": "commerce",
        "connectable": True,
        "required_module": "business",
        "description": "Pull shop receipts and reviews from the Etsy Open API. Requires a shop ID and an OAuth access token from your Etsy app.",
        "setup_steps": [
            "Create an app at https://www.etsy.com/developers. Note the API keystring.",
            "Complete OAuth 2 for your shop and copy the access token.",
            "Find the numeric shop ID in Etsy shop manager. Paste shop ID, API key, and token. Save, Test, Sync.",
        ],
        "fields": [
            {"key": "shop_id", "label": "Shop ID", "secret": False, "required": True, "input": "text"},
            {"key": "api_key", "label": "API keystring", "secret": True, "required": True, "input": "password"},
            {"key": "access_token", "label": "OAuth access token", "secret": True, "required": True, "input": "password"},
        ],
    },
    {
        "code": "ebay",
        "name": "eBay",
        "category": "commerce",
        "connectable": True,
        "required_module": "business",
        "description": "Pull seller orders from the eBay Fulfillment API. Reviews are not imported from eBay in this release.",
        "setup_steps": [
            "Create a keyset at https://developer.ebay.com. Generate a user access token with sell.fulfillment scope.",
            "Paste that token. Save, Test connection, then Sync store.",
        ],
        "fields": [
            {"key": "access_token", "label": "User access token", "secret": True, "required": True, "input": "password"},
        ],
    },
]

WEBHOOK_EVENTS = [
    "lead.created",
    "lead.updated",
    "audit.completed",
    "company.created",
    "deal.created",
    "deal.updated",
    "invoice.paid",
]

SECRET_KEYS = {"access_token", "api_key", "password", "signing_secret", "private_key", "service_account_json", "client_secret", "refresh_token", "consumer_key", "consumer_secret"}
URL_KEYS = {"base_url", "url", "company_website"}
PUSH_PROVIDERS = {"hubspot", "odoo", "custom_api", "google_sheets", "webhook"}

PROVIDER_CODES = {item["code"] for item in PROVIDERS}
PROVIDER_BY_CODE = {item["code"]: item for item in PROVIDERS}
