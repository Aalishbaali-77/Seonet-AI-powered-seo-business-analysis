from rest_framework import serializers

from apps.leads.models import ICP, Lead, LeadList, LeadSearch
from apps.leads.services import parse_icp_from_text


class ICPSerializer(serializers.ModelSerializer):
    class Meta:
        model = ICP
        fields = (
            "id",
            "name",
            "raw_input",
            "industry",
            "employee_count",
            "locations",
            "keywords",
            "origin",
            "status",
            "confirmed_at",
            "created_at",
        )
        read_only_fields = ("id", "origin", "status", "confirmed_at", "created_at")

    def create(self, validated_data):
        request = self.context["request"]
        parsed = parse_icp_from_text(validated_data.get("raw_input") or "", tenant=request.tenant, user=request.user)
        validated_data.setdefault("industry", parsed["industry"])
        validated_data.setdefault("employee_count", parsed["employee_count"])
        if not validated_data.get("locations"):
            validated_data["locations"] = parsed["locations"]
        if not validated_data.get("keywords"):
            validated_data["keywords"] = parsed["keywords"]
        validated_data["origin"] = parsed["origin"]
        validated_data["tenant"] = request.tenant
        if not validated_data.get("name"):
            validated_data["name"] = validated_data.get("industry") or "Ideal customer"
        return super().create(validated_data)


class LeadSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadSearch
        fields = (
            "id",
            "icp",
            "job",
            "status",
            "zones",
            "queries",
            "discovered",
            "duplicates",
            "unique_count",
            "qualified",
            "error",
            "created_at",
        )


class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = (
            "id",
            "company_name",
            "industry",
            "location",
            "website",
            "phone",
            "email",
            "linkedin_url",
            "description",
            "employee_count",
            "enriched_at",
            "enrichment",
            "source",
            "status",
            "lead_score",
            "opportunity_score",
            "quality_score",
            "icp_fit",
            "location_fit",
            "industry_fit",
            "crm_synced",
            "notes",
            "ai_summary",
            "origin",
            "list_ids",
            "updated_at",
        )
        read_only_fields = ("id", "source", "crm_synced", "origin", "list_ids", "enriched_at", "enrichment", "updated_at")

    list_ids = serializers.PrimaryKeyRelatedField(source="lists", many=True, read_only=True)

    def create(self, validated_data):
        validated_data["tenant"] = self.context["request"].tenant
        validated_data.setdefault("source", "manual")
        validated_data.setdefault("source_record_id", validated_data["company_name"].lower())
        lead = super().create(validated_data)
        from apps.leads.scoring import apply_lead_score

        apply_lead_score(lead)
        return lead


class LeadListSerializer(serializers.ModelSerializer):
    lead_count = serializers.SerializerMethodField()

    class Meta:
        model = LeadList
        fields = ("id", "name", "description", "lead_count", "created_at")
        read_only_fields = ("id", "lead_count", "created_at")

    def get_lead_count(self, obj) -> int:
        value = getattr(obj, "lead_count", None)
        if value is not None:
            return int(value)
        return obj.leads.count()

    def create(self, validated_data):
        validated_data["tenant"] = self.context["request"].tenant
        return super().create(validated_data)
