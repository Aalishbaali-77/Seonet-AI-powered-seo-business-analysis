from __future__ import annotations

from apps.ai.models import AIRequest
from apps.audits.models import Audit, AuditIssue, CrawlPage
from apps.billing.entitlements import tenant_module_codes
from apps.common.exceptions import APIError
from apps.jobs import services as job_services
from apps.websites.models import KeywordRankRun
from apps.websites.serp import lookup_keyword, resolve_serp_provider
from providers.ai.base import ProviderUnavailable
from services.ai_gateway import AIService

PROVIDER_LABELS = {
    "anthropic": "Claude",
    "openai": "OpenAI",
    "xai": "Grok",
    "google_gemini": "Gemini",
}

KEYWORD_AI_PROMPT = (
    "You are a Seonet SEO keyword advisor. "
    "Return JSON {suggestions: [{keyword, intent, why}]}. "
    "intent must be seo, aeo, or geo. "
    "Suggest the strongest extra search queries for this business using only FACT lines: "
    "stored keywords, working on-page SEO from the last audit, catalog products, industry, markets, "
    "and licensed first-page sample outcomes. "
    "Prefer question forms for AI-agent and answer-engine search, and specific product or market phrases for classic search. "
    "Never invent rankings, traffic, or that a query will reach page one. "
    "Never invent products, cities, or keywords that are not grounded in the FACT list. "
    "If facts are thin, return fewer suggestions and say so in why."
)


def collect_keywords(website) -> list[str]:
    found: list[str] = []
    for item in website.keywords or []:
        value = str(item).strip()
        if value and value not in found:
            found.append(value)
    audit = website.audits.filter(status=Audit.Status.COMPLETED).first()
    if audit and audit.crawl_id:
        page = CrawlPage.objects.filter(crawl=audit.crawl).order_by("id").first()
        extracted = (page.extracted if page else {}) or {}
        title = str(extracted.get("title") or getattr(page, "title", "") or "").strip()
        if title and title.lower() not in {item.lower() for item in found}:
            found.append(title[:80])
    markets = [str(item).strip() for item in (website.target_markets or []) if str(item).strip()]
    expanded = list(found)
    for keyword in found[:4]:
        for market in markets[:3]:
            combo = f"{keyword} in {market}"
            if combo not in expanded:
                expanded.append(combo)
    return expanded[:8]


def _latest_audit(website):
    return website.audits.filter(status=Audit.Status.COMPLETED).first()


def _seo_facts(website, keywords: list[str], results: list[dict] | None = None) -> list[str]:
    facts = [
        f"domain {website.domain}",
        f"website name {website.name or website.business_name or 'empty'}",
        f"industry {website.industry or 'empty'}",
        f"description {str(website.description or 'empty')[:240]}",
        f"stored keywords {', '.join(keywords) or 'empty'}",
        f"target markets {', '.join(str(item) for item in (website.target_markets or []) if str(item).strip()) or 'empty'}",
        f"competitors {', '.join(str(item) for item in (website.competitors or []) if str(item).strip()) or 'empty'}",
    ]
    try:
        from apps.business.models import BusinessProfile, CatalogProduct

        profile = BusinessProfile.objects.for_tenant(website.tenant).first()
        if profile:
            facts.append(
                f"business profile industry {profile.industry or 'empty'}, category {profile.category or 'empty'}, "
                f"type {profile.business_type}, market {profile.current_market or 'empty'}, goal {str(profile.goal or 'empty')[:160]}"
            )
        products = list(CatalogProduct.objects.for_tenant(website.tenant).order_by("-updated_at")[:8])
        if products:
            facts.append("catalog products " + ", ".join(item.name for item in products if item.name))
    except Exception:  # noqa: BLE001
        pass
    audit = _latest_audit(website)
    if audit:
        scores = audit.scores or {}
        facts.append(
            f"last completed audit SEO {scores.get('seo', 'empty')}, AEO {scores.get('aeo', 'empty')}, "
            f"content {scores.get('content', 'empty')}, overall {audit.overall_score if audit.overall_score is not None else 'empty'}"
        )
        if audit.crawl_id:
            page = CrawlPage.objects.filter(crawl=audit.crawl).order_by("id").first()
            extracted = (page.extracted if page else {}) or {}
            title = str(extracted.get("title") or getattr(page, "title", "") or "").strip()
            h1 = " ".join(str(item) for item in (extracted.get("h1") or []) if str(item).strip())
            meta = str((extracted.get("meta") or {}).get("description") or extracted.get("meta_description") or "").strip()
            if title:
                facts.append(f"homepage title {title[:120]}")
            if h1:
                facts.append(f"homepage h1 {h1[:160]}")
            if meta:
                facts.append(f"homepage meta {meta[:200]}")
        issues = (
            AuditIssue.objects.filter(
                audit=audit,
                status=AuditIssue.Status.OPEN,
                category__in=["on_page", "content", "schema", "aeo"],
            )
            .order_by("priority", "id")[:8]
        )
        for issue in issues:
            facts.append(f"open SEO issue {issue.title}")
    for row in (results or [])[:8]:
        keyword = str(row.get("keyword") or "").strip()
        if not keyword:
            continue
        if row.get("in_first_page"):
            facts.append(f"first-page sample includes {website.domain} for {keyword} at position {row.get('position')}")
        else:
            facts.append(f"first-page sample does not include {website.domain} for {keyword}")
    return facts


def _heuristic_suggestions(website, keywords: list[str], results: list[dict] | None = None) -> list[dict]:
    suggestions: list[dict] = []
    markets = [str(item).strip() for item in (website.target_markets or []) if str(item).strip()]
    for keyword in keywords[:6]:
        suggestions.append(
            {
                "keyword": f"what is {keyword}",
                "intent": "aeo",
                "origin": "recommendation",
                "why": "Question form of a stored keyword for answer-engine and AI-agent queries. Not a predicted rank.",
            }
        )
        suggestions.append(
            {
                "keyword": f"best {keyword}",
                "intent": "seo",
                "origin": "recommendation",
                "why": "Modifier of a stored keyword. Seonet does not claim this will reach page one.",
            }
        )
        if markets:
            suggestions.append(
                {
                    "keyword": f"{keyword} {markets[0]}",
                    "intent": "geo",
                    "origin": "fact",
                    "why": f"Combines the stored keyword with saved target market {markets[0]}.",
                }
            )
    if website.industry and markets:
        suggestions.append(
            {
                "keyword": f"{website.industry} in {markets[0]}",
                "intent": "geo",
                "origin": "fact",
                "why": f"Combines the saved industry {website.industry} with target market {markets[0]}.",
            }
        )
    try:
        from apps.business.models import CatalogProduct

        for product in CatalogProduct.objects.for_tenant(website.tenant).order_by("-updated_at")[:6]:
            name = str(product.name or "").strip()
            if not name:
                continue
            suggestions.append(
                {
                    "keyword": name[:120],
                    "intent": "seo",
                    "origin": "fact",
                    "why": "Catalog product name stored for this business.",
                }
            )
    except Exception:  # noqa: BLE001
        pass
    industry = str(website.industry or "").strip()
    for row in (results or [])[:4]:
        keyword = str(row.get("keyword") or "").strip()
        if not keyword or row.get("in_first_page"):
            continue
        if industry:
            suggestions.append(
                {
                    "keyword": f"{keyword} for {industry}"[:120],
                    "intent": "seo",
                    "origin": "recommendation",
                    "why": "The stored keyword was not in the licensed first-page sample. This is a more specific variant, not a rank forecast.",
                }
            )
    return suggestions


def _dedupe_suggestions(suggestions: list[dict], keywords: list[str], limit: int = 16) -> list[dict]:
    seen: set[str] = {value.lower() for value in keywords}
    unique: list[dict] = []
    for item in suggestions:
        key = str(item.get("keyword") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique[:limit]


def draft_keyword_suggestions(website, keywords: list[str], *, user=None, results: list[dict] | None = None) -> tuple[list[dict], dict]:
    suggestions = _heuristic_suggestions(website, keywords, results)
    ai = {
        "used": False,
        "provider": "",
        "model": "",
        "origin": "heuristic",
        "reason": "",
    }
    if "ai" not in tenant_module_codes(website.tenant):
        ai["reason"] = (
            "AI keyword suggestions use the AI module on Scale and Enterprise packages. "
            "Heuristic queries below still come from the business profile and working SEO."
        )
        return _dedupe_suggestions(suggestions, keywords), ai
    if user is None:
        ai["reason"] = "AI suggestions need the signed-in user who started the job."
        return _dedupe_suggestions(suggestions, keywords), ai
    prompt = AIService.active_prompt("keyword_suggestions") or KEYWORD_AI_PROMPT
    try:
        result = AIService.complete(
            tenant=website.tenant,
            user=user,
            task="keyword_suggestions",
            prompt=prompt,
            untrusted="\n".join(f"FACT: {line}" for line in _seo_facts(website, keywords, results)),
            schema={"type": "object"},
        )
    except ProviderUnavailable as exc:
        ai["reason"] = str(exc) or "No AI provider is enabled. Add a Claude, OpenAI, Grok, or Gemini key in the platform console."
        return _dedupe_suggestions(suggestions, keywords), ai
    except APIError as exc:
        if getattr(exc, "error_code", "") == "QUOTA_EXCEEDED":
            ai["reason"] = str(exc.detail)
            return _dedupe_suggestions(suggestions, keywords), ai
        raise
    for item in (result or {}).get("suggestions") or []:
        keyword = str(item.get("keyword") or "").strip()
        if not keyword:
            continue
        suggestions.append(
            {
                "keyword": keyword[:120],
                "intent": str(item.get("intent") or "seo")[:20],
                "origin": "inference",
                "why": str(item.get("why") or "Drafted from the business and working SEO. Not a rank forecast.")[:400],
            }
        )
    request = (
        AIRequest.objects.for_tenant(website.tenant)
        .filter(task="keyword_suggestions", status="completed")
        .order_by("-created_at")
        .first()
    )
    provider = getattr(request, "provider", "") or ""
    model = getattr(request, "model", "") or ""
    label = PROVIDER_LABELS.get(provider, provider or "package AI")
    ai.update(
        {
            "used": True,
            "provider": provider,
            "model": model,
            "origin": "ai",
            "reason": (
                f"{label} drafted extra queries from this business and the last working SEO audit, "
                "using this package’s AI credits. Tagged inference, not a #1 forecast."
            ),
        }
    )
    return _dedupe_suggestions(suggestions, keywords), ai


def suggest_keywords(website, keywords: list[str], *, user=None, results: list[dict] | None = None) -> list[dict]:
    suggestions, _ai = draft_keyword_suggestions(website, keywords, user=user, results=results)
    return suggestions


def start_keyword_rank(*, website, user):
    job = job_services.create_job(
        tenant=website.tenant,
        user=user,
        job_type="check_keyword_ranks",
        payload={"website_id": str(website.id)},
    )
    run = KeywordRankRun.objects.create(tenant=website.tenant, website=website, job=job, status=KeywordRankRun.Status.PENDING)
    job.result = {"stage": "Queued", "keyword_run_id": str(run.id)}
    job.save(update_fields=["result", "updated_at"])
    job.celery_task_id = _enqueue(str(job.id))
    job.save(update_fields=["celery_task_id", "updated_at"])
    job.refresh_from_db()
    return job


def _enqueue(job_id: str) -> str:
    from threading import Thread

    from django.conf import settings
    from django.db import connections, transaction

    from workers.tasks import check_keyword_ranks

    eager = getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False)
    propagate = getattr(settings, "CELERY_TASK_EAGER_PROPAGATES", False)
    if eager and not propagate:
        def runner() -> None:
            connections.close_all()
            check_keyword_ranks(job_id)

        transaction.on_commit(lambda: Thread(target=runner, daemon=True).start())
        return "thread"
    return str(check_keyword_ranks.delay(job_id).id)


def execute_keyword_rank(job) -> dict:
    run = KeywordRankRun.objects.select_related("website").filter(job=job).first()
    if run is None:
        job_services.mark_failed(job, error="Keyword run was not found.", result={"stage": "Failed"})
        return {}
    website = run.website
    try:
        return _execute_keyword_rank(job, run, website)
    except Exception as exc:  # noqa: BLE001
        run.status = KeywordRankRun.Status.FAILED
        run.error = str(exc)[:4000]
        run.save(update_fields=["status", "error", "updated_at"])
        job_services.mark_failed(job, error=run.error, result={"stage": "Failed", "keyword_run_id": str(run.id)})
        return {"error": run.error}


def _execute_keyword_rank(job, run, website) -> dict:
    from apps.auditlog.services import write_audit

    job_services.mark_running(job, progress=10, result={"stage": "Collecting SEO keywords", "keyword_run_id": str(run.id)})
    run.status = KeywordRankRun.Status.RUNNING
    run.save(update_fields=["status", "updated_at"])
    keywords = collect_keywords(website)
    run.keywords = keywords
    run.save(update_fields=["keywords", "updated_at"])
    if not keywords:
        run.status = KeywordRankRun.Status.FAILED
        run.error = "Save SEO keywords on the website, or complete an audit so a homepage title exists."
        run.save(update_fields=["status", "error", "updated_at"])
        job_services.mark_failed(job, error=run.error, result={"stage": "Failed", "keyword_run_id": str(run.id)})
        return {"error": run.error}
    provider, api_key, cx = resolve_serp_provider()
    results = []
    if provider:
        job_services.mark_progress(job, progress=35, result={"stage": "Checking search results", "keyword_run_id": str(run.id), "total": len(keywords)})
        for index, keyword in enumerate(keywords):
            try:
                results.append(lookup_keyword(query=keyword, domain=website.domain, provider=provider, api_key=api_key, cx=cx))
            except (ProviderUnavailable, APIError) as exc:
                results.append({"keyword": keyword, "position": None, "in_first_page": False, "origin": "none", "error": str(exc)[:240], "source": provider})
            job_services.mark_progress(
                job,
                progress=min(35 + int(((index + 1) / len(keywords)) * 40), 74),
                result={"stage": "Checking search results", "keyword_run_id": str(run.id), "processed": index + 1, "total": len(keywords)},
            )
    else:
        for keyword in keywords:
            results.append(
                {
                    "keyword": keyword,
                    "position": None,
                    "in_first_page": False,
                    "origin": "none",
                    "error": "Enable Google Custom Search or SerpAPI in the platform console.",
                    "source": "",
                }
            )
    job_services.mark_progress(job, progress=80, result={"stage": "Drafting keyword suggestions", "keyword_run_id": str(run.id)})
    suggestions, ai = draft_keyword_suggestions(website, keywords, user=job.user, results=results)
    run.source = provider or ""
    run.results = results
    run.suggestions = suggestions
    run.ai = ai
    run.status = KeywordRankRun.Status.COMPLETED
    run.save(update_fields=["source", "results", "suggestions", "ai", "status", "updated_at"])
    write_audit(
        action="KEYWORD_RANKS_CHECKED",
        tenant=website.tenant,
        user=job.user,
        resource_type="website",
        resource_id=website.id,
        metadata={"source": provider or "none", "keywords": len(keywords), "ai_used": bool(ai.get("used")), "ai_provider": ai.get("provider") or ""},
    )
    first_page = sum(1 for item in results if item.get("in_first_page"))
    result = {
        "stage": "Completed",
        "keyword_run_id": str(run.id),
        "source": provider or "none",
        "checked": len(results),
        "first_page": first_page,
        "suggestions": len(suggestions),
        "ai_used": bool(ai.get("used")),
        "ai_provider": ai.get("provider") or "",
    }
    job_services.mark_completed(job, result=result)
    return result


def run_public(run: KeywordRankRun) -> dict:
    return {
        "id": str(run.id),
        "status": run.status,
        "source": run.source,
        "keywords": run.keywords or [],
        "results": run.results or [],
        "suggestions": run.suggestions or [],
        "ai": run.ai or {},
        "error": run.error,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "why": (
            "Positions come from a licensed Google Custom Search or SerpAPI sample of the first page. "
            "Missing position means the domain was not in that sample. "
            "AI suggestions use Claude or another enabled provider only when the package includes the AI module and credits remain. "
            "Suggestions are not a #1 rank forecast."
        ),
    }
