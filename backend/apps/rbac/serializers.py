from rest_framework import serializers

from apps.common.exceptions import APIError
from apps.rbac.models import Permission, Role
from apps.rbac.services import set_role_permissions
from apps.tenants.members import role_code_from_name


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ("id", "code", "name", "module")


class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.SlugRelatedField(many=True, read_only=True, slug_field="code")
    permission_codes = serializers.ListField(child=serializers.CharField(), write_only=True, required=False)

    class Meta:
        model = Role
        fields = ("id", "code", "name", "is_system", "permissions", "permission_codes")
        read_only_fields = ("id", "is_system")
        extra_kwargs = {"code": {"required": False, "allow_blank": True}}

    def validate_code(self, value: str) -> str:
        code = value.strip().lower().replace("-", "_")
        if code == "owner":
            raise serializers.ValidationError("The owner role is reserved.")
        return code

    def create(self, validated_data):
        codes = validated_data.pop("permission_codes", [])
        request = self.context["request"]
        name = validated_data["name"]
        raw_code = (validated_data.get("code") or "").strip()
        code = raw_code or role_code_from_name(name)
        if code == "owner":
            raise APIError("The owner role is reserved.", code="VALIDATION_ERROR")
        if Role.objects.filter(tenant=request.tenant, code=code).exists():
            raise APIError("A role with that code already exists.", code="VALIDATION_ERROR")
        role = Role.objects.create(tenant=request.tenant, code=code, name=name, is_system=False)
        set_role_permissions(role, codes)
        return role

    def update(self, instance, validated_data):
        if instance.code == "owner":
            raise APIError("The owner role cannot be changed.", code="VALIDATION_ERROR")
        validated_data.pop("code", None)
        codes = validated_data.pop("permission_codes", None)
        instance.name = validated_data.get("name", instance.name)
        instance.save()
        if codes is not None:
            set_role_permissions(instance, codes)
        return instance
