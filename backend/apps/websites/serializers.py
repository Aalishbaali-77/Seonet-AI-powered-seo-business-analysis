from __future__ import annotations

from urllib.parse import urlparse

from rest_framework import serializers

from apps.audits.models import Audit
from apps.crawler.ssrf import validate_public_http_url
from apps.websites.models import AuditFixRun, Website, WebsiteAccess


class WebsiteSerializer(serializers.ModelSerializer):
    last_audit = serializers.SerializerMethodField()
    access_connected = serializers.SerializerMethodField()

    class Meta:
        model = Website
        fields = (
            "id",
            "url",
            "domain",
            "name",
            "status",
            "business_name",
            "industry",
            "description",
            "target_markets",
            "keywords",
            "competitors",
            "audit_config",
            "last_audit",
            "access_connected",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "domain", "created_at", "updated_at", "last_audit", "access_connected")

    def validate_url(self, value: str) -> str:
        return validate_public_http_url(value)

    def create(self, validated_data):
        url = validated_data["url"]
        validated_data["domain"] = urlparse(url).hostname or ""
        if not validated_data.get("name"):
            validated_data["name"] = validated_data.get("business_name") or validated_data["domain"]
        validated_data["tenant"] = self.context["request"].tenant
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.get("url"):
            validated_data["domain"] = urlparse(validated_data["url"]).hostname or instance.domain
        return super().update(instance, validated_data)

    def get_last_audit(self, obj):
        audit = obj.audits.filter(status=Audit.Status.COMPLETED).first()
        if not audit:
            return None
        return {
            "id": str(audit.id),
            "overall_score": audit.overall_score,
            "scores": audit.scores,
            "summary": audit.summary,
            "completed_at": audit.completed_at.isoformat() if audit.completed_at else None,
            "issue_count": audit.issue_count,
            "status": audit.status,
            "pages_crawled": audit.pages_crawled,
        }

    def get_access_connected(self, obj) -> bool:
        try:
            access = obj.code_access
        except WebsiteAccess.DoesNotExist:
            return False
        return access.status == WebsiteAccess.Status.CONNECTED


def access_public(access: WebsiteAccess) -> dict:
    config = dict(access.config or {})
    return {
        "kind": access.kind,
        "status": access.status,
        "host": config.get("host") or "",
        "port": config.get("port") or "",
        "root_path": config.get("root_path") or "",
        "wp_url": config.get("wp_url") or "",
        "username": config.get("username") or "",
        "has_secret": bool(access.secret_blob),
        "last_tested_at": access.last_tested_at.isoformat() if access.last_tested_at else None,
        "last_error": access.last_error,
    }


def fix_run_public(run: AuditFixRun) -> dict:
    return {
        "id": str(run.id),
        "status": run.status,
        "baseline_audit_id": str(run.baseline_audit_id),
        "followup_audit_id": str(run.followup_audit_id) if run.followup_audit_id else None,
        "plan": run.plan or {},
        "result": run.result or {},
        "comparison": run.comparison or {},
        "error": run.error,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }
