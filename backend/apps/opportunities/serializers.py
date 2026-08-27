from rest_framework import serializers

from apps.leads.models import Lead
from apps.opportunities.models import Opportunity


class OpportunitySerializer(serializers.ModelSerializer):
    geo_place_name = serializers.CharField(source="geo_place.name", read_only=True, default="")
    related_lead_ids = serializers.ListField(child=serializers.UUIDField(), write_only=True, required=False)
    related_leads = serializers.SerializerMethodField()

    class Meta:
        model = Opportunity
        fields = (
            "id",
            "title",
            "type",
            "score",
            "evidence",
            "recommended_action",
            "potential_impact",
            "confidence",
            "origin",
            "status",
            "geo_place",
            "geo_place_name",
            "related_lead_ids",
            "related_leads",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "origin", "created_at", "updated_at")

    def get_related_leads(self, obj):
        return [
            {
                "id": str(lead.id),
                "company_name": lead.company_name,
                "location": lead.location,
                "lead_score": lead.lead_score,
                "status": lead.status,
            }
            for lead in obj.related_leads.all()
        ]

    def _set_related_leads(self, instance, ids):
        tenant = instance.tenant
        instance.related_leads.set(Lead.objects.for_tenant(tenant).filter(id__in=ids))

    def create(self, validated_data):
        ids = validated_data.pop("related_lead_ids", [])
        validated_data["tenant"] = self.context["request"].tenant
        validated_data["origin"] = "user"
        instance = super().create(validated_data)
        if ids:
            self._set_related_leads(instance, ids)
        return instance

    def update(self, instance, validated_data):
        ids = validated_data.pop("related_lead_ids", None)
        instance = super().update(instance, validated_data)
        if ids is not None:
            self._set_related_leads(instance, ids)
        return instance
