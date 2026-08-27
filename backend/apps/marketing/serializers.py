from rest_framework import serializers

from apps.marketing.models import Campaign
from apps.marketing.services import audience_count


class CampaignSerializer(serializers.ModelSerializer):
    lead_list_name = serializers.CharField(source="lead_list.name", read_only=True, default="")
    opportunity_title = serializers.CharField(source="opportunity.title", read_only=True, default="")
    live_audience_count = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = (
            "id",
            "name",
            "status",
            "channel",
            "audience_type",
            "lead_list",
            "lead_list_name",
            "city",
            "opportunity",
            "opportunity_title",
            "offer_title",
            "offer_body",
            "audience_count",
            "live_audience_count",
            "sent_at",
            "send_note",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "audience_count", "live_audience_count", "sent_at", "send_note", "created_at", "updated_at")

    def get_live_audience_count(self, obj) -> int:
        preview = audience_count(
            obj.tenant,
            audience_type=obj.audience_type,
            lead_list_id=obj.lead_list_id,
            city=obj.city,
            opportunity_id=obj.opportunity_id,
        )
        return int(preview["count"])

    def create(self, validated_data):
        validated_data["tenant"] = self.context["request"].tenant
        return super().create(validated_data)
