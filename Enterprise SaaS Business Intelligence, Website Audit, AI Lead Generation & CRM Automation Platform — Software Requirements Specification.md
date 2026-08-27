# SOFTWARE REQUIREMENTS SPECIFICATION (SRS)

## Enterprise SaaS Business Intelligence, Website Intelligence, AI Lead Generation, Data Enrichment & CRM Automation Platform

**Document Version:** 1.0  
**Status:** Enterprise Product Baseline  
**Prepared For:** Product Development / Engineering / Investment / Implementation  
**Target Architecture:** Multi-Tenant Cloud SaaS  
**Frontend:** Next.js + React + MUI + Redux Toolkit + Redux-Saga  
**Backend:** Django + Django REST Framework  
**Primary Database:** PostgreSQL  
**Caching / Queueing:** Redis  
**Background Processing:** Celery  
**Search:** OpenSearch / Elasticsearch-compatible engine  
**Object Storage:** S3-compatible storage  
**AI Layer:** Provider-Agnostic AI Gateway  
**Primary AI Providers:** OpenAI, Anthropic Claude, xAI/Grok and additional providers  
**Maps / Local Business Data:** Google Places API (New) + additional lawful/open data providers  
**CRM:** Native CRM + HubSpot + Odoo + extensible third-party adapters  
**Deployment:** Docker/Kubernetes-ready cloud architecture  
**Product Model:** Subscription SaaS + usage-based metering

---

# 1. EXECUTIVE SUMMARY

## 1.1 Product Vision

The proposed platform is an enterprise-grade, multi-tenant SaaS platform that allows businesses, agencies, marketers and sales teams to:

- Audit any authorized website by URL.
- Analyze technical SEO.
- Analyze on-page SEO.
- Analyze content quality.
- Analyze local SEO.
- Analyze AEO/GEO/AI-search readiness.
- Analyze performance and Core Web Vitals.
- Analyze accessibility.
- Analyze security-related website configuration.
- Analyze structured data/schema.
- Analyze social/open-graph metadata.
- Analyze internal linking.
- Analyze crawlability and indexability.
- Identify competitors and market opportunities.
- Generate prioritized recommendations.
- Continuously monitor website health.
- Define a target business profile.
- Define target industries.
- Define target locations/zones.
- Discover businesses and prospects.
- Enrich discovered businesses using permitted data sources.
- Validate and normalize business information.
- Score and qualify prospects.
- Remove duplicates.
- Detect low-quality/spam records.
- Identify potential decision-maker/contact information where legally and technically permitted.
- Use multiple AI providers to classify, enrich and prioritize leads.
- Push qualified leads into the platform's native CRM.
- Synchronize leads with external CRMs such as HubSpot and Odoo.
- Track lead status and sales progression.
- Generate AI-assisted outreach intelligence.
- Measure campaign and prospecting performance.

The platform should combine capabilities commonly found across SEO audit, business intelligence, local search, lead intelligence, enrichment and CRM products into one unified system.

For positioning purposes, the Website Intelligence module should provide capabilities beyond a simple SEO checker. Existing market products such as Semrush Site Audit emphasize technical/on-page analysis, prioritized issues, site-wide crawling and scheduled audits.

---

# 2. BUSINESS OBJECTIVES

## 2.1 Primary Objectives

The platform shall:

1. Provide website owners with an actionable website intelligence report.
2. Help businesses understand why their website is underperforming.
3. Provide AI-generated recommendations rather than only raw technical errors.
4. Identify SEO, AEO and GEO opportunities.
5. Help agencies audit multiple customer websites.
6. Enable businesses to identify potential customers within geographic zones.
7. Build highly qualified business lead databases.
8. Enrich leads using multiple data providers.
9. Reduce duplicate and low-quality leads.
10. Provide AI-driven lead qualification.
11. Synchronize leads with external CRMs.
12. Provide a native CRM as an optional alternative.
13. Enable recurring website audits.
14. Enable recurring lead discovery.
15. Provide usage-based billing.
16. Support enterprise multi-tenancy.
17. Provide APIs for external applications.
18. Provide white-label reporting for agencies.
19. Create a provider-independent AI architecture.
20. Create a provider-independent data-source architecture.

---

# 3. PRODUCT SCOPE

The platform consists of the following major modules:

## 3.1 Platform Modules

### A. SaaS Administration

- Tenant management
- User management
- Role management
- Subscription management
- Plans
- Usage metering
- Billing
- API keys
- Provider configuration
- Feature flags
- Audit logs
- System configuration
- Support administration

### B. Website Intelligence

- Website onboarding
- Website crawling
- Technical SEO audit
- On-page SEO audit
- Content analysis
- Keyword analysis
- Internal linking analysis
- Structured-data analysis
- Local SEO analysis
- AEO/GEO analysis
- Performance analysis
- Accessibility analysis
- Security checks
- Social metadata analysis
- Competitor intelligence
- Website health score
- AI recommendations
- Historical monitoring
- Scheduled audits

### C. Lead Intelligence

- Business profile
- ICP definition
- Market definition
- Location targeting
- Zone generation
- Business discovery
- Multi-source acquisition
- Data normalization
- Data enrichment
- Data validation
- Deduplication
- AI classification
- Lead scoring
- Intent/opportunity scoring
- Lead qualification
- Lead lists
- Saved searches
- Recurring lead discovery

### D. CRM

- Accounts
- Contacts
- Leads
- Opportunities
- Activities
- Tasks
- Notes
- Pipelines
- Stages
- Custom fields
- Tags
- Teams
- Ownership
- Communication history
- Lead scoring
- Automation

### E. Integrations

- HubSpot
- Odoo
- Native CRM
- Google Places
- AI providers
- Email providers
- Webhooks
- REST APIs
- Future CRM connectors

### F. AI Intelligence Layer

- AI provider gateway
- Prompt management
- Structured output
- Classification
- Extraction
- Summarization
- Recommendations
- Lead qualification
- Website analysis
- Competitive intelligence
- Confidence scoring
- Model selection
- Cost optimization

---

# 4. TARGET USERS

## 4.1 Individual Business Owner

Needs:

- Website audit
- SEO recommendations
- Local visibility analysis
- Competitor analysis
- Potential customer discovery

## 4.2 Digital Marketing Agency

Needs:

- Multiple tenants/projects
- White-label reports
- Client management
- Scheduled audits
- Lead generation
- CRM synchronization
- API access
- Bulk processing

## 4.3 Sales Organization

Needs:

- Lead discovery
- Geographic targeting
- Lead scoring
- Enrichment
- CRM synchronization
- Sales pipeline
- Sales intelligence

## 4.4 Enterprise Organization

Needs:

- Multiple departments
- Multiple teams
- Multiple business units
- Advanced permissions
- SSO
- Audit logs
- API integrations
- Data governance
- Enterprise billing

## 4.5 Platform Administrator

Needs:

- Complete system administration
- Tenant management
- Provider management
- Billing
- Usage monitoring
- System health
- Security monitoring

---

# 5. MULTI-TENANCY REQUIREMENTS

The platform MUST be multi-tenant from the beginning.

## 5.1 Tenant Model

Every business/customer account shall represent a Tenant.

A tenant may have:

- Users
- Teams
- Websites
- Projects
- Audit reports
- Lead lists
- Leads
- CRM records
- Integrations
- API keys
- AI usage
- Billing subscription
- Usage limits

## 5.2 Tenant Isolation

Tenant data must never be accessible by another tenant.

Recommended implementation:

- PostgreSQL
- `tenant_id` on tenant-owned records
- Application-level tenant enforcement
- Optional PostgreSQL Row-Level Security for enterprise environments
- Tenant-aware caching
- Tenant-aware background jobs
- Tenant-aware object storage
- Tenant-aware search indexes

## 5.3 Tenant Hierarchy

Recommended:

```text
Platform
 ├── Tenant
 │    ├── Organization
 │    ├── Teams
 │    │    ├── Users
 │    │    └── Roles
 │    ├── Projects
 │    ├── Websites
 │    ├── Lead Lists
 │    ├── Leads
 │    ├── CRM
 │    ├── Integrations
 │    └── Reports
```

---

# 6. AUTHENTICATION & AUTHORIZATION

## 6.1 Authentication

Support:

- Email/password
- Email verification
- Password reset
- Magic link
- Google OAuth
- Microsoft OAuth
- Enterprise SSO
- SAML
- OIDC
- MFA/2FA

## 6.2 Authorization

Use RBAC.

Example roles:

- Platform Super Admin
- Tenant Owner
- Tenant Admin
- Manager
- Analyst
- Sales Manager
- Sales Representative
- Marketing User
- Viewer
- API User

## 6.3 Permissions

Permissions should be granular.

Example:

```text
website.view
website.create
website.audit
website.delete

lead.view
lead.create
lead.enrich
lead.export
lead.delete

crm.view
crm.create
crm.update
crm.delete

report.view
report.export
report.share

integration.view
integration.configure

billing.view
billing.manage
```

---

# 7. MODULE 1 — WEBSITE INTELLIGENCE

# 7.1 Website Onboarding

User enters:

```text
Website URL
```

Optional:

- Business name
- Industry
- Country
- Target market
- Target cities
- Target keywords
- Competitors
- Language
- Search engine
- Business goals

The platform should automatically discover:

- Canonical domain
- HTTP/HTTPS
- redirects
- robots.txt
- sitemap.xml
- sitemap index
- homepage
- major pages
- language
- business identity
- schema
- contact information
- social profiles

---

# 8. WEBSITE CRAWLER

## 8.1 Crawler Responsibilities

The crawler shall:

- Fetch pages
- Follow internal links
- Respect robots.txt where applicable
- Detect canonical URLs
- Detect redirects
- Detect broken links
- Detect duplicate URLs
- Detect orphan-like pages where discoverable
- Extract HTML
- Extract text
- Extract metadata
- Extract structured data
- Extract headings
- Extract images
- Extract links
- Extract hreflang
- Extract Open Graph
- Extract Twitter/X metadata
- Extract schema.org data

## 8.2 Crawl Controls

Tenant plan determines:

- Maximum pages
- Maximum crawl depth
- Crawl frequency
- Concurrent requests
- Crawl timeout
- JavaScript rendering
- Image analysis
- PDF analysis

## 8.3 JavaScript Rendering

For JavaScript-heavy websites:

- Playwright
- Chromium workers
- Rendered DOM extraction
- Screenshot generation
- Performance metrics

---

# 9. WEBSITE AUDIT ENGINE

The audit engine shall generate multiple categories.

## 9.1 Technical SEO

Checks include:

- HTTPS
- HTTP → HTTPS redirect
- WWW/non-WWW consistency
- Canonical URLs
- Robots.txt
- XML sitemap
- Sitemap accessibility
- Indexability
- Noindex
- Nofollow
- X-Robots-Tag
- Redirect chains
- Redirect loops
- 3xx pages
- 4xx pages
- 5xx pages
- Broken internal links
- Broken external links
- Duplicate URLs
- Duplicate content
- Missing titles
- Duplicate titles
- Missing descriptions
- Duplicate descriptions
- Heading structure
- H1 presence
- Multiple H1 issues
- URL structure
- Pagination
- Hreflang
- Internationalization
- Image alt attributes
- Lazy loading
- Crawl depth
- Internal link depth
- Orphan candidates

---

# 10. ON-PAGE SEO

For each page:

- Title
- Meta description
- H1
- H2-H6
- Content length
- Keyword/topic relevance
- Search intent
- Semantic coverage
- Entity coverage
- Internal links
- External links
- Image optimization
- Alt text
- URL quality
- Content freshness indicators
- Duplicate content
- Thin content

---

# 11. CONTENT QUALITY ENGINE

AI shall evaluate:

- Search intent alignment
- Topical relevance
- Content comprehensiveness
- Readability
- Expertise signals
- Trust signals
- Originality indicators
- Entity coverage
- Missing subtopics
- Missing FAQs
- Missing supporting content
- Conversion opportunities

AI output must always distinguish:

```text
Observed Fact
AI Inference
Recommendation
Confidence
```

The system must never represent an AI inference as a verified technical fact.

---

# 12. AEO / GEO / AI SEARCH AUDIT

This is a major differentiator.

The platform shall evaluate whether a website is suitable for discovery and citation by AI/search-answer systems.

Checks:

- Clear entity identity
- Organization information
- Author information
- About page
- Contact information
- Trust signals
- Structured data
- FAQ content
- Question-based content
- Direct answers
- Definition blocks
- Comparison content
- Evidence/citations
- Original data
- Expert content
- Authoritativeness signals
- Content structure
- Semantic entities
- Machine-readable information
- Consistent business information
- AI-readable content
- Conversational search coverage

AI models can be used to simulate queries such as:

```text
Who is this company?

What does this company offer?

Who should use this company?

What locations does it serve?

What makes it different?

What services does it provide?

Would you recommend this business?

What questions would customers ask before buying?
```

The result becomes an:

**AI Visibility / AEO Readiness Score**

---

# 13. LOCAL SEO AUDIT

If business location is available:

Check:

- NAP consistency
- Business name
- Address
- Phone
- Website
- Location pages
- City pages
- Service-area pages
- LocalBusiness schema
- Geo coordinates
- Opening hours
- Contact page
- Google Business presence
- Local keyword coverage
- Local landing pages
- Review signals where legally/technically available

---

# 14. PERFORMANCE AUDIT

Integration options:

- Lighthouse
- PageSpeed Insights
- Chromium
- Core Web Vitals APIs where applicable

Metrics:

- LCP
- INP
- CLS
- TTFB
- FCP
- Speed Index
- Total Blocking Time
- Resource size
- JavaScript size
- CSS size
- Image size
- Font loading
- Render-blocking resources

---

# 15. ACCESSIBILITY AUDIT

Checks:

- WCAG-related issues
- Missing alt text
- Form labels
- Contrast indicators
- Heading hierarchy
- Keyboard navigation indicators
- ARIA problems
- Missing landmarks
- Link accessibility
- Button accessibility

The report must clearly state that automated checks do not constitute complete accessibility certification.

---

# 16. SECURITY-RELATED WEBSITE CHECKS

The system may check publicly observable configuration such as:

- HTTPS
- TLS certificate validity
- Mixed content
- Security headers
- HSTS
- CSP
- X-Content-Type-Options
- Referrer-Policy
- Permissions-Policy
- publicly exposed server information

The system shall NOT perform intrusive exploitation.

No:

- penetration attacks
- credential attacks
- brute force
- unauthorized vulnerability exploitation

---

# 17. SOCIAL / OPEN GRAPH AUDIT

Checks:

- OG title
- OG description
- OG image
- Twitter/X card
- Social profile discovery
- Image dimensions
- Social preview availability

---

# 18. STRUCTURED DATA AUDIT

Detect:

- JSON-LD
- Microdata
- RDFa

Schema types:

- Organization
- LocalBusiness
- Product
- Service
- Article
- BlogPosting
- FAQ
- Breadcrumb
- Person
- Event
- Review
- AggregateRating

The engine should validate syntax and provide recommendations.

---

# 19. WEBSITE SCORE

Recommended score:

```text
Overall Website Intelligence Score: 0–100
```

Categories:

```text
Technical SEO        20%
On-Page SEO          15%
Content              15%
AEO/GEO              15%
Performance          10%
Local SEO            10%
Accessibility         5%
Structured Data       5%
Social Signals        5%
```

Weights should be configurable.

---

# 20. ISSUE PRIORITIZATION

Every issue shall have:

```text
Issue ID
Category
Severity
Affected URLs
Description
Evidence
Impact
Recommendation
Estimated Effort
Priority
Confidence
```

Severity:

- Critical
- High
- Medium
- Low
- Informational

Priority formula:

```text
Priority =
Business Impact
× SEO Impact
× Confidence
÷ Estimated Effort
```

---

# 21. AI WEBSITE REPORT

AI should generate:

### Executive Summary

- Overall score
- Top strengths
- Top weaknesses
- Biggest opportunities
- Critical problems

### Action Plan

```text
Today
This Week
This Month
Next Quarter
```

### AI Recommendations

Each recommendation must include:

- Problem
- Why it matters
- Exact action
- Example
- Expected outcome
- Confidence

---

# 22. WEBSITE MONITORING

Users can schedule:

- Daily
- Weekly
- Monthly
- Custom

The platform compares:

```text
Previous Audit
vs
Current Audit
```

Track:

- Score changes
- New issues
- Resolved issues
- Regressions
- New pages
- Removed pages
- Content changes
- Metadata changes

---

# 23. MODULE 2 — BUSINESS PROFILE / ICP

Before generating leads, tenant defines their target business.

## 23.1 Business Profile

Fields:

- Company name
- Website
- Industry
- Products
- Services
- Target customers
- Geographic market
- Countries
- States/provinces
- Cities
- Postal codes
- Radius
- Business size
- Revenue range
- Employee range
- Technologies
- Keywords
- Competitor exclusions
- Existing customer exclusions

---

# 24. ICP BUILDER

AI can convert natural language into a structured ICP.

Example:

```text
"We sell ERP software to packaging companies
in Karachi, Lahore and Islamabad with more
than 20 employees."
```

AI converts this into:

```json
{
  "industry": ["Packaging"],
  "locations": ["Karachi", "Lahore", "Islamabad"],
  "employee_min": 20,
  "product_interest": ["ERP"]
}
```

The system MUST require user confirmation before large-scale lead generation.

---

# 25. MODULE 3 — GEO / ZONE ENGINE

A core component.

The user can define:

```text
Country
Province
City
District
Postal Code
Radius
Polygon
```

The system generates geographic search zones.

Example:

```text
Karachi
 ├── Zone 1
 ├── Zone 2
 ├── Zone 3
 ├── Zone 4
 └── ...
```

Possible geographic partitioning:

- Grid
- H3
- Geohash
- Administrative boundary
- Radius
- Polygon

H3 is recommended for scalable geographic indexing.

---

# 26. GOOGLE PLACES DISCOVERY

The platform should integrate Google Places API (New) through a dedicated provider adapter.

Google's current Places API supports Text Search and Nearby Search, with location restrictions/biases and type filtering. Text Search uses field masks and has a maximum of 60 results across pages, making geographic/query partitioning essential for large-scale discovery.

Example query:

```text
Dental clinics in Clifton Karachi
```

or:

```text
Packaging manufacturers in Lahore
```

The discovery engine should generate multiple search combinations:

```text
Industry + City
Industry + Zone
Industry + District
Service + City
Keyword + City
Keyword + Zone
```

---

# 27. DATA SOURCE ABSTRACTION

Do NOT hard-code lead generation around Google.

Use:

```text
LeadSourceProvider
```

Interface:

```text
search()
get_details()
get_contacts()
get_company()
get_location()
get_social_profiles()
get_website()
get_metadata()
```

Providers may include:

- Google Places
- Public/open datasets
- Government/business registries where legally available
- Tenant-provided files
- Public APIs
- Licensed data providers
- Website discovery
- Future providers

Every record must contain:

```text
source
source_record_id
source_timestamp
source_url
source_confidence
license/usage metadata where applicable
```

---

# 28. OPEN DATA ENGINE

Open-source/open-data sources should be handled through connectors.

Examples:

- OpenStreetMap
- Government open-data portals
- Public business registries
- Public directories where permitted
- Tenant-owned datasets

The system must maintain source provenance.

---

# 29. WEBSITE DISCOVERY FOR LEADS

For discovered businesses:

1. Identify website.
2. Fetch website.
3. Verify business identity.
4. Extract:
   - Business name
   - Address
   - Phone
   - Email if publicly published and permitted
   - Website
   - Social links
   - Services
   - Industry
   - Location
5. Match against original place record.

---

# 30. LEAD NORMALIZATION

Normalize:

### Phone

```text
+92 300 1234567
0300-1234567
03001234567
```

into canonical representation.

### Domain

Normalize:

```text
https://www.example.com/
http://example.com
example.com
```

into:

```text
example.com
```

### Business name

Normalize:

- Case
- punctuation
- legal suffixes
- whitespace
- transliteration where appropriate

---

# 31. DEDUPLICATION ENGINE

Duplicate detection must use multiple signals.

Signals:

- Place ID
- Website domain
- Phone
- Email
- Business name
- Address
- Geo coordinates
- AI similarity

Recommended match score:

```text
Website = 100
Phone = 90
Email = 90
Place ID = 100
Business + Address = 85
Business + Location = 75
AI similarity = variable
```

Possible statuses:

```text
Exact Duplicate
Probable Duplicate
Possible Duplicate
Unique
```

---

# 32. DATA QUALITY ENGINE

Every lead receives:

```text
Data Quality Score: 0–100
```

Factors:

- Business name
- Website
- Phone
- Email
- Address
- Location
- Industry
- Social profiles
- Source reliability
- Verification age

---

# 33. LEAD ENRICHMENT

Enrichment pipeline:

```text
Raw Lead
 ↓
Normalize
 ↓
Verify
 ↓
Website Discovery
 ↓
Website Analysis
 ↓
Business Classification
 ↓
Contact Extraction
 ↓
Social Discovery
 ↓
AI Classification
 ↓
Lead Scoring
 ↓
Quality Check
 ↓
Deduplication
 ↓
CRM
```

---

# 34. AI PROVIDER GATEWAY

Do not integrate OpenAI, Claude and Grok directly into business modules.

Create:

```text
AI Gateway
```

Architecture:

```text
Website Module
Lead Module
Scoring Module
Report Module
       ↓
    AI Gateway
       ↓
 ┌─────┼─────┐
OpenAI Claude xAI
       ↓
Fallback / Router
```

---

# 35. AI MODEL ROUTING

The gateway shall support:

```text
Provider
Model
Task
Cost
Latency
Context Window
Availability
Quality
```

Example routing:

```text
Simple classification
→ cheaper model

Large content analysis
→ high-context model

Complex reasoning
→ premium model

Fallback
→ secondary provider
```

---

# 36. AI COST CONTROL

Every AI request must record:

- Tenant
- User
- Provider
- Model
- Prompt tokens
- Completion tokens
- Total tokens
- Estimated cost
- Request duration
- Task
- Cache hit
- Success/failure

This enables:

```text
Tenant AI Usage
Platform AI Cost
Cost Per Lead
Cost Per Audit
Cost Per Report
```

---

# 37. AI PROMPT MANAGEMENT

Prompts must be database-managed rather than hard-coded.

Entities:

```text
PromptTemplate
PromptVersion
PromptVariable
PromptExperiment
PromptResult
```

Support:

- Versioning
- Rollback
- A/B testing
- Tenant-specific prompts
- Global prompts
- Model-specific prompts

---

# 38. AI OUTPUT VALIDATION

All important AI outputs must use structured schemas.

Example:

```json
{
  "classification": "high_fit",
  "confidence": 0.91,
  "reasoning_summary": "...",
  "evidence": [],
  "recommendations": []
}
```

The system must validate output before persisting it.

Invalid output:

```text
AI response
→ schema validator
→ retry
→ fallback model
→ mark failed
```

---

# 39. LEAD SCORING ENGINE

Score:

```text
ICP Fit
+
Location Fit
+
Industry Fit
+
Business Size
+
Website Quality
+
Technology Fit
+
Data Quality
+
Opportunity
+
Intent
```

Example:

```text
ICP Fit              25
Industry             15
Location             10
Business Size        10
Website Opportunity  15
Data Quality         10
Intent               10
Technology Fit        5
------------------------
Total                100
```

---

# 40. OPPORTUNITY SCORING

A major differentiator.

Example:

A business has:

- Poor SEO
- No schema
- Slow website
- No local landing pages
- Weak content
- No conversion optimization

The platform can calculate:

```text
Digital Opportunity Score = 92/100
```

This becomes a sales opportunity for a marketing agency.

---

# 41. AI LEAD QUALIFICATION

AI should answer:

```text
Is this business a fit?

Why?

What services might they need?

What evidence supports the recommendation?

What is the estimated opportunity?

What should the sales representative know?

What should NOT be claimed?
```

Every AI-derived claim must be classified as:

```text
Verified
Inferred
Unknown
```

---

# 42. LEAD LISTS

Users can create:

```text
Lead List
```

Example:

```text
"Karachi Packaging Companies"
```

Filters:

- Location
- Industry
- Rating
- Website
- Website score
- Lead score
- Data quality
- Number of employees
- Technology
- Contact availability
- Opportunity score
- Source
- Date discovered

---

# 43. SAVED SEARCHES

A user can save:

```text
Industry:
Packaging

Location:
Karachi

Minimum Lead Score:
70

Minimum Opportunity Score:
60
```

The system can execute the search automatically.

---

# 44. RECURRING LEAD GENERATION

Schedules:

- Daily
- Weekly
- Monthly
- Custom

System should identify:

```text
Previously discovered
vs
New businesses
```

Only new/changed records should be returned.

---

# 45. CRM — NATIVE

The platform should contain an optional native CRM.

## Objects

- Leads
- Contacts
- Companies
- Deals
- Pipelines
- Activities
- Tasks
- Notes
- Calls
- Emails
- Meetings
- Tags
- Custom fields

---

# 46. CRM PIPELINE

Example:

```text
New
 ↓
Qualified
 ↓
Contacted
 ↓
Interested
 ↓
Meeting Scheduled
 ↓
Proposal
 ↓
Negotiation
 ↓
Won / Lost
```

Pipelines must be configurable.

---

# 47. HUBSPOT INTEGRATION

Implement through an adapter:

```text
CRMProvider
```

Methods:

```text
create_company()
update_company()
create_contact()
update_contact()
create_deal()
update_deal()
add_note()
create_task()
search_company()
search_contact()
```

Support:

- OAuth
- API credentials where applicable
- Field mapping
- Owner mapping
- Pipeline mapping
- Stage mapping
- Sync direction
- Conflict resolution
- Retry
- Webhooks

---

# 48. ODOO INTEGRATION

The Odoo adapter should target supported current APIs rather than relying exclusively on legacy RPC mechanisms.

Odoo 19 introduces External JSON-2 with HTTP endpoints such as `/json/2/<model>/<method>`, while older external XML-RPC/JSON-RPC mechanisms have future deprecation/removal considerations.

Supported objects:

- res.partner
- crm.lead
- crm.stage
- res.users
- activities
- custom models where configured

---

# 49. CRM FIELD MAPPING

Example:

```text
Platform Field
      ↓
CRM Field

company.name
→ company.name

company.phone
→ phone

company.website
→ website

lead.score
→ x_lead_score
```

Admin UI:

```text
Source Field
Target Field
Transformation
Required?
Default Value
```

---

# 50. SYNC ENGINE

Use asynchronous synchronization.

```text
Platform
 ↓
Outbox Event
 ↓
Message Queue
 ↓
CRM Worker
 ↓
CRM API
 ↓
Success
```

Failures:

```text
Retry 1
Retry 2
Retry 3
Exponential Backoff
Dead Letter Queue
```

---

# 51. WEBHOOK SYSTEM

Support inbound/outbound webhooks.

Events:

```text
lead.created
lead.updated
lead.qualified
lead.deleted

audit.started
audit.completed
audit.failed

crm.sync.started
crm.sync.completed
crm.sync.failed

subscription.changed
usage.limit_reached
```

---

# 52. API ARCHITECTURE

Django REST Framework shall expose versioned APIs.

Example:

```text
/api/v1/auth/
/api/v1/tenants/
/api/v1/users/
/api/v1/websites/
/api/v1/audits/
/api/v1/reports/
/api/v1/leads/
/api/v1/lead-lists/
/api/v1/searches/
/api/v1/enrichment/
/api/v1/crm/
/api/v1/integrations/
/api/v1/usage/
/api/v1/billing/
/api/v1/ai/
/api/v1/webhooks/
```

---

# 53. API DESIGN PRINCIPLES

APIs must support:

- Pagination
- Filtering
- Sorting
- Search
- Field selection
- Idempotency
- Rate limiting
- API versioning
- Standard errors
- Request IDs
- Audit logging

Example error:

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "API rate limit exceeded.",
    "request_id": "req_xxxxx"
  }
}
```

---

# 54. FRONTEND ARCHITECTURE

Technology:

```text
Next.js
React
MUI
Redux Toolkit
Redux-Saga
TypeScript
```

Recommended structure:

```text
src/
 ├── app/
 ├── components/
 ├── features/
 │    ├── auth/
 │    ├── dashboard/
 │    ├── websites/
 │    ├── audits/
 │    ├── leads/
 │    ├── crm/
 │    ├── reports/
 │    ├── integrations/
 │    ├── billing/
 │    └── settings/
 ├── store/
 ├── services/
 ├── hooks/
 ├── utils/
 └── types/
```

---

# 55. REDUX ARCHITECTURE

Redux Toolkit should manage:

- Authentication
- Current tenant
- User
- Permissions
- Websites
- Audits
- Leads
- CRM
- Notifications
- UI state
- Usage

Redux-Saga should manage long-running/asynchronous workflows such as:

```text
Start Audit
Generate Leads
Enrich Leads
CRM Sync
Report Generation
Export
```

---

# 56. UI/UX MODULES

## Dashboard

Widgets:

- Website Health
- SEO Score
- AEO Score
- GEO Score
- Open Issues
- Lead Count
- Qualified Leads
- Opportunity Score
- CRM Sync Status
- AI Usage
- API Usage

---

# 57. WEBSITE AUDIT UI

Screens:

```text
Website Overview
Audit Summary
Technical SEO
On-Page SEO
Content
AEO/GEO
Performance
Accessibility
Local SEO
Structured Data
Social
Security
Issues
Recommendations
Historical Trends
```

---

# 58. LEAD GENERATION UI

Wizard:

```text
Step 1 — Business Profile
Step 2 — Target Industry
Step 3 — Geography
Step 4 — Search Keywords
Step 5 — Data Sources
Step 6 — Enrichment
Step 7 — Scoring
Step 8 — Preview
Step 9 — Execute
```

Before execution:

```text
Estimated Records
Estimated Provider Usage
Estimated AI Usage
Estimated Cost
```

User confirmation required.

---

# 59. LEAD TABLE

Columns:

```text
☑
Company
Industry
Location
Website
Phone
Email
Lead Score
Opportunity
Data Quality
Source
Status
Owner
CRM
Last Updated
```

Bulk actions:

- Assign
- Tag
- Enrich
- Export
- Delete
- Sync CRM
- Add to list
- Re-score

---

# 60. REPORTING ENGINE

Reports:

### Website Audit Report

- Executive Summary
- Score
- Issues
- Recommendations
- Charts
- URL-level details
- Historical comparison

### Lead Intelligence Report

- Market size
- Businesses discovered
- Qualified businesses
- Geographic distribution
- Industry distribution
- Lead quality
- Opportunity distribution

### Sales Intelligence Report

- Pipeline
- Lead conversion
- CRM sync
- Opportunities
- Activity

---

# 61. PDF REPORT GENERATION

Generate:

- PDF
- CSV
- XLSX
- JSON
- HTML
- Shareable URL

PDF should support:

- Company branding
- Logo
- Colors
- Custom footer
- Agency branding
- White label

---

# 62. WHITE-LABEL SYSTEM

Agency plans should support:

- Custom logo
- Custom domain
- Custom colors
- Email sender
- Report branding
- Favicon
- Custom footer
- Remove platform branding

---

# 63. BILLING

Subscription dimensions:

```text
Plan
Users
Websites
Pages Crawled
Audits
Leads
Enrichment
AI Credits
CRM Sync
API Calls
Storage
Reports
```

Possible plans:

```text
Free
Starter
Professional
Business
Agency
Enterprise
```

---

# 64. USAGE METERING

Every billable event must generate a usage event.

Example:

```text
website_page_crawled
ai_tokens
lead_discovered
lead_enriched
crm_sync
report_generated
api_request
```

Usage:

```text
Tenant
Resource
Quantity
Timestamp
Cost
Billing Period
```

---

# 65. CREDIT SYSTEM

Optional unified credit system:

```text
1 Website Crawl Credit
1 AI Credit
1 Lead Discovery Credit
1 Enrichment Credit
```

However, internal metering should remain granular even if the customer-facing UI uses credits.

---

# 66. DATABASE ARCHITECTURE

PostgreSQL recommended.

Core entities:

```text
Tenant
User
Role
Permission
Team

Subscription
Plan
UsageRecord
Invoice

Website
WebsiteProject
Crawl
CrawlPage
Audit
AuditIssue
AuditRecommendation
AuditScore

BusinessProfile
ICP
GeoZone
LeadSearch
LeadList
Lead
LeadSource
LeadEnrichment
LeadScore
LeadDuplicate
LeadContact

CRMConnection
CRMFieldMapping
CRMObject
CRMEvent
CRMSyncJob

AIProvider
AIModel
AIRequest
AIUsage
PromptTemplate
PromptVersion

Report
ReportTemplate
ReportExport

Webhook
WebhookDelivery
ApiKey
AuditLog
Notification
```

---

# 67. CORE LEAD DATA MODEL

Recommended Lead fields:

```text
id
tenant_id
external_id
source
source_record_id

company_name
legal_name
domain
website

phone
email

address
city
state
country
postal_code

latitude
longitude

industry
category
sub_category

employee_count
revenue_range

rating
review_count

social_links

business_status

lead_score
quality_score
opportunity_score
intent_score

verification_status

first_seen_at
last_seen_at

created_at
updated_at
```

---

# 68. PROVENANCE MODEL

Every important data field should optionally track provenance.

Example:

```text
website
value: example.com

source:
Google Places

source_timestamp:
2026-08-17

confidence:
0.99
```

This is particularly important when combining multiple external sources.

---

# 69. SEARCH ENGINE

OpenSearch/Elasticsearch-compatible search should index:

- Leads
- Companies
- Websites
- Audit issues
- Content
- Locations

Support:

- Full-text
- Fuzzy search
- Geo search
- Filters
- Facets
- Ranking

Example:

```text
"dentists Karachi"
```

with:

```text
radius < 20 km
lead_score > 70
website_score < 50
```

---

# 70. GEO SEARCH

PostgreSQL PostGIS should be considered mandatory for the geographic intelligence layer.

Support:

- Point
- Polygon
- Radius
- Bounding box
- Distance
- Administrative areas
- Zone intersection

Example:

```sql
ST_DWithin(...)
```

---

# 71. ASYNCHRONOUS ARCHITECTURE

Heavy workloads must NEVER execute inside normal HTTP requests.

Use:

```text
Django REST API
      ↓
Redis / RabbitMQ
      ↓
Celery
      ↓
Workers
```

Workers:

```text
Crawler Worker
Audit Worker
AI Worker
Lead Discovery Worker
Enrichment Worker
CRM Worker
Report Worker
Export Worker
Notification Worker
```

---

# 72. QUEUE DESIGN

Recommended queues:

```text
crawl.high
crawl.normal
crawl.low

audit.high
audit.normal

lead.discovery
lead.enrichment
lead.scoring

ai.high
ai.normal
ai.low

crm.sync

report.generate

export.generate

notification
```

---

# 73. RETRY POLICY

Each external operation must support:

- Timeout
- Retry
- Exponential backoff
- Circuit breaker
- Provider fallback
- Dead-letter queue

Example:

```text
1 sec
5 sec
30 sec
2 min
10 min
```

---

# 74. RATE LIMITING

Rate limits required for:

- Tenant
- User
- API key
- IP
- Provider
- Endpoint

Example:

```text
API:
100 requests/minute

Lead Discovery:
10 jobs/hour

Website Audit:
5 concurrent audits
```

Values configurable per subscription.

---

# 75. CACHING

Cache:

- Website crawl results
- DNS results
- robots.txt
- sitemap
- AI results where safe
- business lookups
- geographic zones
- provider metadata

Cache keys MUST contain tenant context where tenant-specific.

---

# 76. SECURITY

## 76.1 General

Follow:

- OWASP principles
- Secure coding
- Least privilege
- Secrets management
- Encryption
- Audit logging

## 76.2 Data Encryption

At rest:

- PostgreSQL encryption where supported
- S3 encryption
- Encrypted backups

In transit:

- TLS 1.2+
- HTTPS only

---

# 77. API SECURITY

Use:

- JWT or secure session authentication
- OAuth2 where appropriate
- API keys
- Refresh token rotation
- Rate limits
- Permission checks
- CORS restrictions
- CSRF protection
- Request validation

---

# 78. SSRF PROTECTION

This is CRITICAL because the user can submit arbitrary URLs.

Website crawling must protect against:

```text
http://localhost
http://127.0.0.1
http://169.254.169.254
private IPs
internal DNS
Docker networks
cloud metadata endpoints
```

The crawler must implement:

- DNS resolution validation
- Private IP blocking
- Redirect re-validation
- IPv4/IPv6 protection
- Port restrictions
- Request timeout
- Response size limits
- Content-type validation

---

# 79. MALICIOUS WEBSITE PROTECTION

Crawler workers should be isolated.

Recommended:

```text
Crawler
 ↓
Sandbox
 ↓
Network policy
 ↓
Browser/container
```

Never allow crawled websites to execute with privileged infrastructure access.

---

# 80. PROMPT INJECTION PROTECTION

Website content is untrusted input.

Example:

```text
Website says:
"Ignore all previous instructions..."
```

The AI system must treat crawled website content strictly as data.

Prompt architecture:

```text
System Instructions
+
Task Instructions
+
Untrusted Website Content
```

Website content must never override system instructions.

---

# 81. PII / PERSONAL DATA

The platform may encounter personal information.

Requirements:

- Minimize collection
- Record source
- Apply retention rules
- Provide deletion
- Access control
- Export capability
- Data-processing controls

Do not intentionally harvest sensitive personal information.

---

# 82. LEAD DATA COMPLIANCE

The platform must distinguish:

```text
Business Data
vs
Personal Contact Data
```

Data-source terms and applicable privacy/marketing laws must be respected.

The product should provide:

- Source attribution
- Collection timestamp
- Opt-out/suppression list
- Do-not-contact flag
- Data deletion
- Tenant retention policy
- Audit trail

The system should not assume that publicly visible information is automatically unrestricted for every downstream use.

---

# 83. GOOGLE DATA GOVERNANCE

Google Places data should be implemented according to the applicable Google Maps Platform terms and API policies.

Do not build the product around unauthorized scraping of Google Maps pages.

Use the official API integration and retain only what the applicable terms permit.

Google's current Places API documentation identifies Places API (New) as the current version and provides official Text Search/Nearby Search functionality.

---

# 84. AI GOVERNANCE

The platform should support:

- Model registry
- Model versions
- Prompt versions
- AI cost tracking
- AI quality tracking
- Human review
- Confidence scores
- AI output validation
- AI audit logs

---

# 85. AI HALLUCINATION CONTROL

Every AI recommendation should be based on available evidence.

Output format:

```text
Finding:
Evidence:
Inference:
Recommendation:
Confidence:
```

Example:

```text
Finding:
Homepage does not contain LocalBusiness JSON-LD.

Evidence:
No LocalBusiness schema detected.

Inference:
Local search machine-readability may be improved.

Confidence:
High
```

---

# 86. AI HUMAN-IN-THE-LOOP

Users should be able to:

- Accept recommendation
- Reject recommendation
- Edit recommendation
- Mark as incorrect
- Mark as verified

Feedback should optionally feed evaluation datasets.

---

# 87. ADMINISTRATION CONSOLE

Platform admin dashboard:

```text
System Health
Tenants
Users
Subscriptions
Usage
AI Costs
Provider Health
Crawler Health
Queue Health
CRM Integrations
Audit Logs
Security Events
Feature Flags
```

---

# 88. PROVIDER MANAGEMENT

Admin can configure:

```text
Google
OpenAI
Anthropic
xAI
Other providers
```

Settings:

- API key
- Model
- Rate limit
- Timeout
- Cost
- Enabled/disabled
- Priority
- Fallback

Secrets must never be returned to frontend.

---

# 89. OBSERVABILITY

Use:

- Structured logging
- Metrics
- Distributed tracing
- Error tracking

Recommended stack:

```text
Prometheus
Grafana
OpenTelemetry
Sentry
```

Metrics:

```text
API latency
API error rate
Crawler success rate
AI success rate
AI cost
Queue length
Worker utilization
CRM sync failures
Database connections
Redis health
```

---

# 90. AUDIT LOGGING

Log:

```text
User
Tenant
Action
Resource
Resource ID
IP
Timestamp
Before
After
Result
Request ID
```

Example:

```text
USER_UPDATED
LEAD_EXPORTED
API_KEY_CREATED
CRM_CONNECTED
WEBSITE_AUDIT_STARTED
```

---

# 91. BACKUP & DISASTER RECOVERY

Requirements:

- Automated PostgreSQL backups
- Point-in-time recovery
- Object-storage versioning
- Backup encryption
- Off-site backups
- Backup monitoring
- Restore testing

Enterprise targets:

```text
RPO: 15 minutes
RTO: 1 hour
```

Final values should be defined per SLA tier.

---

# 92. HIGH AVAILABILITY

Production architecture:

```text
Load Balancer
      ↓
Next.js Instances
      ↓
Django API Instances
      ↓
Redis / RabbitMQ
      ↓
Celery Workers
      ↓
PostgreSQL
      ↓
Object Storage
```

Database should support:

- Primary
- Replica
- Automated backup
- Failover strategy

---

# 93. DEPLOYMENT

Recommended environments:

```text
Development
Testing
Staging
Production
```

CI/CD:

```text
Git
 ↓
CI
 ↓
Lint
 ↓
Unit Tests
 ↓
Integration Tests
 ↓
Security Scan
 ↓
Build
 ↓
Deploy Staging
 ↓
Smoke Tests
 ↓
Production
```

---

# 94. CONTAINERIZATION

Services:

```text
frontend
backend
postgres
redis
rabbitmq
celery-worker
celery-beat
crawler
ai-worker
report-worker
search
object-storage
monitoring
```

Docker Compose can be used for development.

Kubernetes should be supported for enterprise production.

---

# 95. FRONTEND PERFORMANCE

Requirements:

- SSR/streaming where useful
- Code splitting
- Lazy loading
- MUI optimization
- Virtualized large tables
- Pagination
- Server-side filtering
- Debounced search
- Optimistic updates where safe

Large lead tables MUST NOT load thousands of records into browser memory.

---

# 96. INTERNATIONALIZATION

Support:

- English
- Urdu
- Arabic
- Additional languages

Architecture must support:

```text
i18n
RTL
Localized dates
Localized numbers
Localized currency
Timezone
```

---

# 97. TIMEZONE

Every tenant should have:

```text
Timezone
Locale
Currency
Date format
Number format
```

Scheduling must be tenant-timezone aware.

---

# 98. NOTIFICATIONS

Channels:

- In-app
- Email
- Webhook
- Optional SMS

Notifications:

```text
Audit Completed
Audit Failed
Lead Generation Completed
New Leads Available
CRM Sync Completed
Usage Limit Reached
Subscription Expiring
Security Event
```

---

# 99. EXPORT

Supported:

```text
CSV
XLSX
JSON
PDF
```

Large exports must be asynchronous.

```text
Export Requested
 ↓
Queue
 ↓
Worker
 ↓
Object Storage
 ↓
Temporary Download URL
```

---

# 100. SEARCH & FILTERING

All major tables should support:

- Search
- Advanced filters
- Saved filters
- Sorting
- Column configuration
- Export

---

# 101. TENANT CUSTOM FIELDS

Tenant admins can define:

```text
Lead Custom Field
Company Custom Field
Contact Custom Field
Deal Custom Field
Website Custom Field
```

Types:

- Text
- Number
- Boolean
- Date
- Select
- Multi-select
- URL
- Currency

---

# 102. FEATURE FLAGS

Use feature flags for:

- Beta AI features
- New providers
- New scoring engine
- New CRM
- New audit category

Flags can target:

```text
Platform
Tenant
Plan
User
Percentage rollout
```

---

# 103. TESTING STRATEGY

## Unit Tests

Backend:

- Models
- Services
- Scoring
- Parsers
- Provider adapters

Frontend:

- Components
- Hooks
- Redux reducers
- Sagas

## Integration Tests

- API
- Database
- Redis
- Celery
- AI gateway
- CRM integrations

## End-to-End

Use Playwright.

Scenarios:

```text
Register
Create Tenant
Add Website
Run Audit
Generate Report
Create ICP
Generate Leads
Enrich Leads
Score Leads
Push CRM
```

---

# 104. SECURITY TESTING

Required:

- SAST
- DAST
- Dependency scanning
- Container scanning
- Secret scanning
- OWASP testing
- SSRF testing
- Authorization testing
- Tenant isolation testing

---

# 105. PERFORMANCE TESTING

Test:

```text
100 concurrent users
500 concurrent users
1,000 concurrent users
10,000+ lead records
100,000+ lead records
Large website crawl
Large report
Bulk CRM sync
```

Load testing tools:

- k6
- Locust

---

# 106. DATA QUALITY TESTING

Create test datasets containing:

- Duplicate companies
- Duplicate websites
- Different phone formats
- Different business names
- Missing websites
- Missing phones
- Incorrect addresses
- Multiple branches
- Franchise businesses
- Closed businesses

---

# 107. ACCEPTANCE CRITERIA — WEBSITE AUDIT

A website audit is considered successful when:

- URL is validated.
- Crawl is created.
- Crawl respects configured limits.
- Pages are stored.
- Technical checks execute.
- Content checks execute.
- AEO/GEO checks execute.
- Performance checks execute.
- Score is generated.
- Issues are generated.
- Recommendations are generated.
- Report is available.
- Audit history is stored.

---

# 108. ACCEPTANCE CRITERIA — LEAD GENERATION

A lead generation job is successful when:

- ICP is defined.
- Geographic zones are created.
- Search queries are generated.
- Providers execute.
- Results are collected.
- Source provenance is stored.
- Leads are normalized.
- Duplicates are detected.
- Enrichment executes.
- Lead scores are calculated.
- Quality scores are calculated.
- User can review results.
- CRM sync can be initiated.

---

# 109. ACCEPTANCE CRITERIA — CRM

CRM integration is successful when:

- Authentication works.
- Connection status is visible.
- Field mapping works.
- Test connection works.
- Lead can be synchronized.
- Duplicate handling works.
- Errors are logged.
- Retries work.
- User can disconnect.
- Credentials are securely stored.

---

# 110. PRODUCT API — EXTERNAL DEVELOPERS

Enterprise customers should receive:

```text
API Key
Client ID
Client Secret
Webhook Secret
```

API documentation:

```text
OpenAPI 3.x
Swagger UI
ReDoc
```

---

# 111. API RATE LIMIT TIERS

Example:

```text
Starter       60 req/min
Professional  300 req/min
Business      1,000 req/min
Enterprise    Custom
```

These are initial design values and should be configurable.

---

# 112. EVENT-DRIVEN ARCHITECTURE

Important domain events:

```text
WebsiteCreated
AuditRequested
AuditCompleted

LeadSearchCreated
LeadDiscoveryStarted
LeadDiscoveryCompleted

LeadEnrichmentStarted
LeadEnrichmentCompleted

LeadQualified
LeadExported

CRMSyncRequested
CRMSyncCompleted

SubscriptionChanged
UsageLimitReached
```

---

# 113. OUTBOX PATTERN

For critical events:

```text
Database Transaction
       ↓
Business Record
+
Outbox Event
       ↓
Event Dispatcher
       ↓
Message Queue
```

This prevents lost events.

---

# 114. IDEMPOTENCY

External operations must be idempotent.

Example:

```text
tenant_id
+
provider
+
external_record_id
```

should prevent duplicate CRM creation.

---

# 115. CRM CONFLICT RESOLUTION

Strategies:

```text
Platform Wins
CRM Wins
Newest Wins
Manual Resolution
Field-Level Mapping
```

Configurable per integration.

---

# 116. LEAD LIFECYCLE

```text
Discovered
 ↓
Normalized
 ↓
Verified
 ↓
Enriched
 ↓
Qualified
 ↓
Assigned
 ↓
Contacted
 ↓
Engaged
 ↓
Opportunity
 ↓
Customer
```

Alternative:

```text
Disqualified
Suppressed
Duplicate
Invalid
```

---

# 117. WEBSITE LIFECYCLE

```text
Added
 ↓
Verified
 ↓
Crawling
 ↓
Audited
 ↓
Monitored
 ↓
Archived
```

---

# 118. AI TASK CATALOG

Initial AI tasks:

```text
Business Classification
ICP Extraction
Website Summary
Content Classification
Intent Classification
Entity Extraction
SEO Recommendation
AEO Recommendation
GEO Recommendation
Competitor Analysis
Lead Qualification
Opportunity Detection
Lead Summary
Business Summary
Report Generation
Email/Outreach Assistance
```

---

# 119. AI PROVIDER FAILOVER

Example:

```text
Primary:
OpenAI

Failure:
Anthropic

Failure:
xAI

Failure:
Local deterministic rule engine
```

No core feature should become completely unavailable merely because one AI provider is down.

---

# 120. DETERMINISTIC VS AI ENGINE

Important architecture rule:

Do NOT use AI for everything.

Use deterministic code for:

- HTTP status
- redirects
- title presence
- meta tags
- H1
- canonical
- sitemap
- robots.txt
- schema syntax
- page count
- response time
- duplicate URL
- broken links

Use AI for:

- semantic interpretation
- content quality
- intent
- business classification
- recommendations
- opportunity analysis
- lead qualification

This dramatically reduces cost and improves reliability.

---

# 121. WEBSITE AUDIT ENGINE ARCHITECTURE

```text
URL
 ↓
Crawler
 ↓
Raw Page
 ↓
Parser
 ├── HTML Analyzer
 ├── SEO Analyzer
 ├── Schema Analyzer
 ├── Performance Analyzer
 ├── Accessibility Analyzer
 ├── Local Analyzer
 └── Security Analyzer
        ↓
   Rule Engine
        ↓
    AI Engine
        ↓
  Score Engine
        ↓
 Recommendation Engine
        ↓
      Report
```

---

# 122. LEAD INTELLIGENCE ARCHITECTURE

```text
Tenant ICP
 ↓
Geo Engine
 ↓
Query Generator
 ↓
Provider Router
 ├── Google Places
 ├── Open Data
 ├── Public APIs
 └── Licensed Providers
 ↓
Raw Leads
 ↓
Normalization
 ↓
Deduplication
 ↓
Website Discovery
 ↓
Enrichment
 ↓
AI Classification
 ↓
Scoring
 ↓
Quality Engine
 ↓
Human Review
 ↓
CRM
```

---

# 123. COST OPTIMIZATION

The platform should estimate costs before executing expensive jobs.

Example:

```text
Expected Leads: 5,000

Places API:
Estimated usage

Website Crawling:
5,000 websites

AI Classification:
5,000 records

AI Enrichment:
1,500 records

CRM:
1,500 records
```

Display:

```text
Estimated Cost
Estimated Credits
Estimated Processing Time
```

---

# 124. DATA RETENTION

Tenant configurable:

```text
30 days
90 days
1 year
Custom
```

Enterprise customers can define custom retention policies.

Deletion should cascade appropriately while preserving required audit records.

---

# 125. SOFT DELETE

For major entities:

```text
deleted_at
deleted_by
```

Permanent deletion handled by scheduled cleanup according to retention policy.

---

# 126. PLATFORM HEALTH SCORE

Admin dashboard:

```text
API Health
Database Health
Queue Health
Crawler Health
AI Health
CRM Health
Storage Health
Search Health
```

Overall:

```text
Platform Health = 98%
```

---

# 127. SLA

Potential enterprise SLA:

```text
99.9% availability
```

Higher tiers may target:

```text
99.95%
99.99%
```

Subject to infrastructure architecture and commercial agreement.

---

# 128. ENTERPRISE FEATURES

Enterprise tier should support:

- SSO
- SAML
- SCIM
- Audit logs
- IP restrictions
- Custom retention
- Dedicated workers
- Dedicated database
- Private deployment
- Custom AI provider
- Custom CRM
- API access
- Custom SLA
- Data residency options

---

# 129. WHITE-LABEL AGENCY ARCHITECTURE

```text
Agency Tenant
 ├── Client A
 │    ├── Website
 │    └── Reports
 ├── Client B
 │    ├── Website
 │    └── Reports
 └── Client C
      ├── Website
      └── Reports
```

The hierarchy may be implemented as:

```text
Tenant
 └── Workspaces
      └── Client Accounts
```

---

# 130. RECOMMENDED ENTERPRISE ARCHITECTURE

```text
                         INTERNET
                            |
                       CDN / WAF
                            |
                     Load Balancer
                            |
              +-------------+-------------+
              |                           |
         Next.js Web                API Gateway
                                          |
                                   Django REST API
                                          |
             +----------------------------+------------------+
             |              |              |                |
          PostgreSQL      Redis         RabbitMQ        OpenSearch
             |              |              |
             |              |        Celery Workers
             |              |              |
             |              +--------------+----------------+
             |                             |
             |          +------------------+------------------+
             |          |          |          |       |       |
          Crawler     Audit       AI       Leads   CRM    Reports
             |          |          |          |       |       |
             +----------+----------+----------+-------+-------+
                                        |
                                  External Providers
                                        |
              +-------------------------+----------------------+
              |             |             |          |          |
           Google        OpenAI       Anthropic     xAI       CRM APIs
```

---

# 131. RECOMMENDED TECHNOLOGY STACK

## Frontend

```text
Next.js
React
TypeScript
MUI
MUI X
Redux Toolkit
Redux-Saga
React Hook Form
Zod
TanStack/appropriate data utilities where useful
Recharts/ECharts
```

## Backend

```text
Python
Django
Django REST Framework
Celery
Pydantic where appropriate
PostgreSQL
PostGIS
Redis
RabbitMQ
```

## Search

```text
OpenSearch
```

## Browser Automation

```text
Playwright
Chromium
```

## Storage

```text
S3-compatible object storage
```

## Monitoring

```text
Prometheus
Grafana
OpenTelemetry
Sentry
```

## Deployment

```text
Docker
Kubernetes
NGINX/Traefik
Cloudflare/CDN/WAF
```

---

# 132. DJANGO APPLICATION STRUCTURE

Recommended:

```text
backend/
├── config/
├── apps/
│   ├── accounts/
│   ├── tenants/
│   ├── billing/
│   ├── websites/
│   ├── crawler/
│   ├── audits/
│   ├── seo/
│   ├── aeo/
│   ├── geo/
│   ├── performance/
│   ├── accessibility/
│   ├── leads/
│   ├── enrichment/
│   ├── scoring/
│   ├── crm/
│   ├── integrations/
│   ├── ai/
│   ├── reports/
│   ├── notifications/
│   ├── usage/
│   ├── webhooks/
│   └── auditlog/
├── workers/
├── services/
└── tests/
```

---

# 133. SERVICE LAYER

Business logic should NOT be placed entirely inside Django views.

Recommended:

```text
API Layer
 ↓
Application Service
 ↓
Domain Service
 ↓
Repository/ORM
```

Example:

```text
POST /audits

AuditService.start_audit()
```

instead of putting the entire audit implementation inside the API view.

---

# 134. PROVIDER ADAPTER PATTERN

Use interfaces.

```text
WebsiteDataProvider
LeadSourceProvider
AIProvider
CRMProvider
EmailProvider
```

This allows:

```text
Google → Provider A
Open Data → Provider B
HubSpot → CRM A
Odoo → CRM B
OpenAI → AI A
Claude → AI B
xAI → AI C
```

without changing core business logic.

---

# 135. PLUGIN ARCHITECTURE

Future modules should be installable as providers.

Example:

```text
providers/
 ├── google_places/
 ├── openai/
 ├── anthropic/
 ├── xai/
 ├── hubspot/
 ├── odoo/
 └── future_provider/
```

---

# 136. MVP RECOMMENDATION

Although this SRS defines the complete enterprise platform, implementation should be phased.

## MVP 1 — Website Intelligence

Build:

- Authentication
- Multi-tenancy
- Website onboarding
- Crawler
- Technical SEO
- On-page SEO
- Performance
- Schema
- AEO/GEO baseline
- AI recommendations
- Score
- Report
- PDF
- Dashboard
- Subscription/usage foundation

---

# 137. MVP 2 — Lead Intelligence

Build:

- Business profile
- ICP
- Geo zones
- Google Places integration
- Open data connector architecture
- Lead normalization
- Deduplication
- Website enrichment
- Lead scoring
- AI classification
- Lead lists
- CSV/XLSX export

---

# 138. MVP 3 — CRM

Build:

- Native CRM
- HubSpot integration
- Odoo integration
- Field mapping
- CRM sync
- Pipeline
- Activities
- Webhooks
- Automation

---

# 139. MVP 4 — ADVANCED AI

Build:

- Multi-model routing
- AI opportunity detection
- AEO/GEO simulation
- Competitor intelligence
- AI lead qualification
- AI sales intelligence
- AI-generated outreach suggestions
- Prompt experimentation
- AI cost optimization

---

# 140. MVP 5 — ENTERPRISE

Build:

- SSO
- SAML
- SCIM
- White label
- Custom domains
- Dedicated infrastructure
- Advanced audit logs
- Enterprise APIs
- Advanced billing
- Custom integrations
- Private deployment

---

# 141. PHASED DEVELOPMENT APPROACH

## Phase 1

Platform foundation:

```text
Authentication
Tenant
RBAC
Billing foundation
API
Audit logging
```

## Phase 2

Website engine:

```text
Crawler
Audit engine
Score engine
AI
Reports
```

## Phase 3

Lead engine:

```text
ICP
Geo
Discovery
Normalization
Enrichment
Scoring
```

## Phase 4

CRM:

```text
Native CRM
HubSpot
Odoo
```

## Phase 5

Enterprise:

```text
SSO
White label
Advanced API
Enterprise controls
```

---

# 142. KEY PRODUCT DIFFERENTIATOR

The platform should NOT be positioned merely as:

> "Another SEO audit tool."

The stronger product proposition is:

> **AI-powered Business Growth Intelligence Platform**

The workflow becomes:

```text
Audit My Business
       ↓
Understand My Problems
       ↓
Understand My Market
       ↓
Find Businesses Like My Customers
       ↓
Identify Their Digital Problems
       ↓
Score Their Opportunity
       ↓
Enrich Their Business Data
       ↓
Push Qualified Prospects Into CRM
       ↓
Convert Leads Into Customers
```

This connects:

```text
SEO
+
AEO
+
GEO
+
Local Intelligence
+
Business Intelligence
+
Lead Generation
+
AI
+
CRM
```

rather than treating them as isolated features.

---

# 143. FUTURE MARKET INTELLIGENCE

Future versions can add:

## Competitor Intelligence

- Competitor websites
- Competitor SEO
- Competitor content
- Competitor local presence
- Competitor technology
- Competitor visibility

## Market Gap Analysis

Example:

```text
Market:
Karachi Dentists

Businesses:
2,450

High opportunity:
830

Weak websites:
620

No website:
280

Poor local SEO:
710
```

---

# 144. DIGITAL OPPORTUNITY MARKETPLACE

A future module can convert lead intelligence into service opportunities.

Example:

```text
ABC Dental Clinic

Website Score: 38
AEO Score: 22
Performance: Poor
Local SEO: Weak
Schema: Missing

Opportunity:
Website redesign
SEO
Local SEO
Content
AEO
Performance optimization

Opportunity Score:
91
```

This transforms the system from a lead database into a:

**Sales Opportunity Intelligence Platform.**

---

# 145. AI SALES INTELLIGENCE

For each lead:

```text
Business Summary
Potential Problems
Potential Needs
Recommended Service
Evidence
Lead Score
Opportunity Score
Suggested Sales Angle
Suggested Discovery Questions
```

The AI must not invent facts.

---

# 146. FUTURE AUTOMATION

Automation engine:

```text
WHEN
Lead score > 80

AND
Opportunity score > 70

THEN
Assign to Sales Team

AND
Create CRM task

AND
Add to "Hot Prospects"

AND
Notify Sales Manager
```

---

# 147. WORKFLOW ENGINE

Eventually provide a visual workflow builder:

```text
Trigger
 ↓
Condition
 ↓
AI Classification
 ↓
Action
 ↓
CRM
 ↓
Notification
```

Example:

```text
New Lead
 ↓
Lead Score > 80?
 ↓ Yes
Website Score < 50?
 ↓ Yes
Opportunity > 70?
 ↓ Yes
Create CRM Opportunity
 ↓
Assign Sales Rep
 ↓
Notify Manager
```

---

# 148. SUCCESS METRICS

## Product Metrics

- Registered tenants
- Active tenants
- Websites audited
- Pages crawled
- Leads generated
- Qualified leads
- CRM syncs
- Reports generated
- AI requests
- AI cost per tenant

## Business Metrics

- MRR
- ARR
- ARPU
- CAC
- LTV
- Churn
- Conversion
- Expansion revenue

## Product Quality

- Crawl success rate
- Lead accuracy
- Duplicate rate
- Enrichment success
- AI accuracy
- CRM sync success
- API uptime

---

# 149. TECHNICAL SUCCESS CRITERIA

The architecture shall support:

```text
10,000+ tenants
1M+ websites
100M+ leads
10,000+ concurrent background jobs
```

through horizontal scaling.

These are target architectural capabilities rather than initial deployment requirements.

---

# 150. NON-FUNCTIONAL REQUIREMENTS

## Availability

Target:

```text
99.9%+
```

## API Performance

Normal API requests:

```text
P95 < 500ms
```

excluding asynchronous operations.

## Scalability

Horizontal scaling must be possible for:

- API
- Crawlers
- AI workers
- Lead workers
- CRM workers
- Report workers

## Reliability

No single external provider should become a single point of failure for core functionality.

---

# 151. IMPORTANT ARCHITECTURAL PRINCIPLES

### Principle 1

**API-first**

Everything should be accessible through APIs.

### Principle 2

**Multi-tenant from day one**

Do not retrofit tenancy later.

### Principle 3

**Async by default for expensive operations**

Crawling, AI, enrichment and CRM synchronization must be background jobs.

### Principle 4

**Provider agnostic**

Never make Google/OpenAI/HubSpot a hard-coded dependency of the domain layer.

### Principle 5

**Evidence-first AI**

AI should interpret evidence rather than manufacture facts.

### Principle 6

**Deterministic first**

Use rules for objective technical checks and AI for semantic intelligence.

### Principle 7

**Usage-aware**

Every expensive operation must be metered.

### Principle 8

**Security by design**

Especially SSRF, tenant isolation, secrets and untrusted web content.

### Principle 9

**Auditability**

Every important action should be traceable.

### Principle 10

**Enterprise-ready architecture without premature microservices**

Start with a modular Django monolith plus independent workers. Extract services only when scale or team boundaries justify it.

---

# 152. RECOMMENDED INITIAL ARCHITECTURE DECISION

Do NOT start the project as 15–20 independent microservices.

Recommended:

```text
                 Next.js
                    |
              Django Modular API
                    |
       +------------+-------------+
       |            |             |
   PostgreSQL      Redis       RabbitMQ
                                  |
                              Celery
                                  |
             +--------------------+--------------------+
             |         |         |         |            |
          Crawler    Audit       AI       Leads        CRM
```

This provides enterprise scalability while keeping development manageable.

Later:

```text
Crawler Service
AI Service
Lead Discovery Service
CRM Integration Service
```

can be extracted independently.

---

# 153. FINAL PRODUCT ARCHITECTURE

The complete product should ultimately resemble:

```text
                        ┌──────────────────────┐
                        │      PLATFORM        │
                        │   SaaS / MultiTenant  │
                        └──────────┬───────────┘
                                   │
                 ┌─────────────────┴──────────────────┐
                 │                                    │
        ┌────────▼─────────┐                 ┌────────▼─────────┐
        │ WEBSITE          │                 │ LEAD             │
        │ INTELLIGENCE     │                 │ INTELLIGENCE     │
        ├──────────────────┤                 ├──────────────────┤
        │ SEO              │                 │ ICP              │
        │ AEO              │                 │ GEO              │
        │ GEO              │                 │ Discovery        │
        │ Content          │                 │ Enrichment       │
        │ Performance      │                 │ Deduplication    │
        │ Accessibility    │                 │ Scoring          │
        │ Schema           │                 │ Qualification    │
        │ Local SEO        │                 │ Opportunity      │
        └────────┬─────────┘                 └────────┬─────────┘
                 │                                    │
                 └────────────────┬───────────────────┘
                                  │
                         ┌────────▼────────┐
                         │ AI INTELLIGENCE │
                         ├─────────────────┤
                         │ OpenAI          │
                         │ Claude          │
                         │ xAI/Grok        │
                         │ AI Router       │
                         │ Prompt Engine   │
                         │ Cost Engine     │
                         └────────┬────────┘
                                  │
                         ┌────────▼────────┐
                         │      CRM        │
                         ├─────────────────┤
                         │ Native CRM      │
                         │ HubSpot         │
                         │ Odoo            │
                         │ Other CRMs      │
                         └────────┬────────┘
                                  │
                         ┌────────▼────────┐
                         │ AUTOMATION      │
                         ├─────────────────┤
                         │ Workflows       │
                         │ Notifications   │
                         │ Tasks           │
                         │ Webhooks        │
                         │ Reporting       │
                         └─────────────────┘
```

---

# 154. CONCLUSION

The proposed system should be engineered as a **Business Growth Intelligence SaaS**, not merely as an SEO auditing application.

The strategic architecture is:

```text
                    BUSINESS
                       │
            ┌──────────┴──────────┐
            │                     │
        OWN WEBSITE          TARGET MARKET
            │                     │
            ▼                     ▼
      WEBSITE AUDIT         LEAD DISCOVERY
            │                     │
       SEO/AEO/GEO          GEO + INDUSTRY
            │                     │
            ▼                     ▼
      AI OPPORTUNITIES       DATA ENRICHMENT
            │                     │
            └──────────┬──────────┘
                       ▼
                  AI SCORING
                       │
                       ▼
               QUALIFIED LEADS
                       │
                       ▼
                     CRM
                       │
                       ▼
                 SALES PIPELINE
                       │
                       ▼
                   REVENUE
```

The strongest long-term differentiator is the connection between **website intelligence and lead intelligence**.

Instead of merely telling a user:

> "Your website has 47 SEO issues."

the platform can eventually tell the user:

> "We identified 1,240 businesses in your target market. 386 appear to fit your ICP. 214 have significant website/SEO/AEO opportunities. 87 have an opportunity score above 80. Here are the highest-priority prospects, their verified business information, the evidence behind the opportunity, and the CRM records ready for your sales team."

That is a considerably stronger SaaS proposition than a standalone SEO audit product.