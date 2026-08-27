from rest_framework import serializers

from apps.markets.models import GeoPlace, MarketFocus, MarketSignal, ScoringProfile
from apps.markets.scoring import DEFAULT_WEIGHTS, normalize_weights


class GeoPlaceSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name", read_only=True, default="")
    score = serializers.SerializerMethodField()

    class Meta:
        model = GeoPlace
        fields = ("id", "code", "name", "kind", "country_code", "parent", "parent_name", "score")

    def get_score(self, obj):
        by_place = self.context.get("scores") or {}
        return by_place.get(str(obj.id)) or by_place.get(obj.id)


class ScoringProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScoringProfile
        fields = ("id", "weights", "updated_at")
        read_only_fields = ("id", "updated_at")

    def validate_weights(self, value):
        return normalize_weights(value or DEFAULT_WEIGHTS)


class MarketFocusSerializer(serializers.ModelSerializer):
    place_name = serializers.CharField(source="place.name", read_only=True)
    place_code = serializers.CharField(source="place.code", read_only=True)
    kind = serializers.CharField(source="place.kind", read_only=True)

    class Meta:
        model = MarketFocus
        fields = ("id", "place", "place_name", "place_code", "kind", "notes", "created_at")
        read_only_fields = ("id", "place_name", "place_code", "kind", "created_at")

    def create(self, validated_data):
        validated_data["tenant"] = self.context["request"].tenant
        return super().create(validated_data)


class MarketSignalSerializer(serializers.ModelSerializer):
    place_name = serializers.CharField(source="place.name", read_only=True)
    place_code = serializers.CharField(source="place.code", read_only=True)

    class Meta:
        model = MarketSignal
        fields = (
            "id",
            "place",
            "place_name",
            "place_code",
            "kind",
            "value",
            "source",
            "source_url",
            "source_provider",
            "retrieved_at",
            "confidence",
            "verification_status",
            "created_at",
        )
        read_only_fields = ("id", "place_name", "place_code", "created_at")

    def create(self, validated_data):
        validated_data["tenant"] = self.context["request"].tenant
        return super().create(validated_data)

    
    def validate_value(self, value):
        if value > 100:
            raise serializers.ValidationError("Value must be between 0 and 100.")
        return value
