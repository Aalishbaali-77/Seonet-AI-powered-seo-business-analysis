from __future__ import annotations

SCORE_KEYS = (
    "technical_seo",
    "on_page_seo",
    "content",
    "schema",
    "accessibility",
    "aeo",
    "geo",
    "local_seo",
    "performance",
)


def intelligence_compare(*, baseline, followup) -> dict:
    before_scores = dict(baseline.scores or {})
    after_scores = dict(followup.scores or {})
    rows = [
        {
            "metric": "Overall audit score",
            "before": baseline.overall_score,
            "after": followup.overall_score,
            "delta": _delta(followup.overall_score, baseline.overall_score),
        }
    ]
    for key in SCORE_KEYS:
        rows.append(
            {
                "metric": key.replace("_", " "),
                "before": before_scores.get(key),
                "after": after_scores.get(key),
                "delta": _delta(after_scores.get(key), before_scores.get(key)),
            }
        )
    before_titles = {item.title for item in baseline.issues.all()}
    after_titles = {item.title for item in followup.issues.all()}
    return {
        "available": True,
        "origin": "audit_scores",
        "why": (
            "This compares the saved pre-fix audit to the re-audit after allowlisted file or WordPress changes. "
            "It is not a Google ranking, Search Console position, or invented SERP."
        ),
        "baseline_audit_id": str(baseline.id),
        "followup_audit_id": str(followup.id),
        "before_issues": baseline.issue_count,
        "after_issues": followup.issue_count,
        "resolved_titles": sorted(before_titles - after_titles),
        "new_titles": sorted(after_titles - before_titles),
        "still_open_titles": sorted(before_titles & after_titles),
        "rows": rows,
    }


def _delta(after, before):
    if after is None or before is None:
        return None
    return int(after) - int(before)
