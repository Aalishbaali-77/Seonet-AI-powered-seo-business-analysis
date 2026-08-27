from rest_framework import serializers

from apps.business.models import BusinessProfile, CatalogProduct, CommerceCustomer, CommerceOrder, CommerceOrderItem, CommerceReview, ImportBatch


class BusinessProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessProfile
        fields = ("id", "business_type", "industry", "category", "current_market", "goal", "notes", "updated_at")
        read_only_fields = ("id", "updated_at")


class CatalogProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = CatalogProduct
        fields = ("id", "sku", "name", "category", "unit_price", "cost_price", "source", "verification_status", "created_at")
        read_only_fields = ("id", "source", "verification_status", "created_at")

    def create(self, validated_data):
        validated_data["tenant"] = self.context["request"].tenant
        return super().create(validated_data)


class CommerceCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommerceCustomer
        fields = ("id", "name", "city", "email", "source", "verification_status", "created_at")
        read_only_fields = ("id", "source", "verification_status", "created_at")


class CommerceOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommerceOrderItem
        fields = ("id", "sku", "name", "quantity", "unit_price", "discount", "cost")


class CommerceOrderSerializer(serializers.ModelSerializer):
    items = CommerceOrderItemSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True, default="")

    class Meta:
        model = CommerceOrder
        fields = ("id", "external_id", "ordered_at", "customer_name", "city", "channel", "status", "currency", "source", "items", "created_at")
        read_only_fields = ("id", "external_id", "source", "created_at")


class ImportBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportBatch
        fields = ("id", "file_name", "kind", "status", "rows_total", "rows_imported", "created_at")


class CommerceReviewSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()

    class Meta:
        model = CommerceReview
        fields = ("id", "product_name", "rating", "title", "body", "reviewer", "source", "sentiment", "origin", "created_at")

    def get_product_name(self, obj) -> str:
        return obj.product.name if obj.product_id else ""
