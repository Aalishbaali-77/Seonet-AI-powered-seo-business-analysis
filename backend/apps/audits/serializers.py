from rest_framework import serializers

from apps.audits.models import Audit, AuditIssue, AuditRecommendation


class AuditIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditIssue
        fields = (
            "id",
            "code",
            "severity",
            "category",
            "title",
            "why_it_matters",
            "affected_urls",
            "evidence",
            "recommendation",
            "estimated_effort",
            "status",
            "origin",
            "confidence",
            "priority",
        )
        read_only_fields = (
            "id",
            "code",
            "severity",
            "category",
            "title",
            "why_it_matters",
            "affected_urls",
            "evidence",
            "recommendation",
            "estimated_effort",
            "origin",
            "confidence",
            "priority",
        )


class AuditRecommendationSerializer(serializers.ModelSerializer):
    issue_id = serializers.UUIDField(source="issue.id", read_only=True, allow_null=True)
    effort = serializers.CharField(source="issue.estimated_effort", read_only=True, default="")
    priority = serializers.IntegerField(source="issue.priority", read_only=True, default=50)
    category = serializers.CharField(source="issue.category", read_only=True, default="")
    severity = serializers.CharField(source="issue.severity", read_only=True, default="")

    class Meta:
        model = AuditRecommendation
        fields = (
            "id",
            "issue_id",
            "title",
            "verified_finding",
            "ai_interpretation",
            "recommendation",
            "origin",
            "confidence",
            "effort",
            "priority",
            "category",
            "severity",
        )


class AuditSerializer(serializers.ModelSerializer):
    website_id = serializers.UUIDField(source="website.id", read_only=True)
    website_domain = serializers.CharField(source="website.domain", read_only=True)
    website_name = serializers.CharField(source="website.name", read_only=True)

    class Meta:
        model = Audit
        fields = (
            "id",
            "website",
            "website_id",
            "website_domain",
            "website_name",
            "job",
            "status",
            "overall_score",
            "scores",
            "summary",
            "pages_crawled",
            "issue_count",
            "completed_at",
            "created_at",
        )


class AuditDetailSerializer(AuditSerializer):
    issues = AuditIssueSerializer(many=True, read_only=True)
    recommendations = AuditRecommendationSerializer(many=True, read_only=True)

    class Meta(AuditSerializer.Meta):
        fields = AuditSerializer.Meta.fields + ("issues", "recommendations")
