from rest_framework import serializers

from apps.auditlog.services import write_audit
from apps.crm.models import Activity, Company, Contact, Deal, Pipeline, Stage
from apps.tenants.models import Membership
from apps.users.models import User


def _owner_name(user) -> str:
    if user is None:
        return ""
    return ((user.first_name or "") + " " + (user.last_name or "")).strip() or user.email


def _same_tenant(instance, tenant, message: str):
    if instance is None:
        return
    if getattr(instance, "tenant_id", None) != tenant.id:
        raise serializers.ValidationError(message)


def _require_member(user, tenant):
    if user is None:
        return
    if not Membership.objects.filter(tenant=tenant, user=user, status=Membership.Status.ACTIVE).exists():
        raise serializers.ValidationError("Owner must be an active member of this workspace.")


def _audit(request, action: str, instance, metadata: dict | None = None):
    write_audit(
        action=action,
        request=request,
        tenant=getattr(request, "tenant", None) or instance.tenant,
        resource_type=instance.__class__.__name__.lower(),
        resource_id=instance.id,
        metadata=metadata or {},
    )


def _mark_lead_synced(deal):
    if not deal.lead_id:
        return
    from apps.leads.models import Lead

    Lead.objects.filter(id=deal.lead_id, tenant=deal.tenant).update(crm_synced=True)


class StageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stage
        fields = ("id", "name", "code", "order", "is_won", "is_lost")
        read_only_fields = ("id",)

    def validate(self, attrs):
        if attrs.get("is_won") and attrs.get("is_lost"):
            raise serializers.ValidationError("A stage cannot be both won and lost.")
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        pipeline = validated_data["pipeline"]
        _same_tenant(pipeline, request.tenant, "That pipeline is not in this workspace.")
        validated_data["tenant"] = request.tenant
        if not validated_data.get("code"):
            from django.utils.text import slugify

            validated_data["code"] = (slugify(validated_data.get("name") or "stage") or "stage")[:40]
        stage = super().create(validated_data)
        _audit(request, "CRM_STAGE_CREATED", stage)
        return stage

    def update(self, instance, validated_data):
        validated_data.pop("pipeline", None)
        stage = super().update(instance, validated_data)
        _audit(self.context["request"], "CRM_STAGE_UPDATED", stage)
        return stage


class PipelineSerializer(serializers.ModelSerializer):
    stages = StageSerializer(many=True, read_only=True)

    class Meta:
        model = Pipeline
        fields = ("id", "name", "is_default", "stages")
        read_only_fields = ("id",)

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["tenant"] = request.tenant
        if validated_data.get("is_default"):
            Pipeline.objects.for_tenant(request.tenant).update(is_default=False)
        pipeline = super().create(validated_data)
        from apps.crm.services import seed_pipeline_stages

        seed_pipeline_stages(pipeline)
        _audit(request, "CRM_PIPELINE_CREATED", pipeline)
        return pipeline

    def update(self, instance, validated_data):
        request = self.context["request"]
        if validated_data.get("is_default"):
            Pipeline.objects.for_tenant(request.tenant).exclude(pk=instance.pk).update(is_default=False)
        elif instance.is_default and validated_data.get("is_default") is False:
            raise serializers.ValidationError({"is_default": "Assign another default pipeline first."})
        pipeline = super().update(instance, validated_data)
        _audit(request, "CRM_PIPELINE_UPDATED", pipeline)
        return pipeline


class CompanySerializer(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = (
            "id",
            "name",
            "domain",
            "industry",
            "location",
            "phone",
            "email",
            "notes",
            "tags",
            "last_activity_at",
            "owner",
            "owner_name",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "owner_name", "last_activity_at", "created_at", "updated_at")

    def get_owner_name(self, obj) -> str:
        return _owner_name(getattr(obj, "owner", None))

    def validate_owner(self, owner):
        _require_member(owner, self.context["request"].tenant)
        return owner

    def validate_tags(self, tags):
        if not tags:
            return []
        if not isinstance(tags, list):
            raise serializers.ValidationError("Tags must be a list of names.")
        return [str(item).strip()[:40] for item in tags if str(item).strip()][:12]

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["tenant"] = request.tenant
        validated_data.setdefault("owner", request.user)
        company = super().create(validated_data)
        _audit(request, "CRM_COMPANY_CREATED", company)
        return company

    def update(self, instance, validated_data):
        company = super().update(instance, validated_data)
        _audit(self.context["request"], "CRM_COMPANY_UPDATED", company)
        return company


class ContactSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True, default="")
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = Contact
        fields = (
            "id",
            "company",
            "company_name",
            "first_name",
            "last_name",
            "title",
            "email",
            "phone",
            "owner",
            "owner_name",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "company_name", "owner_name", "created_at", "updated_at")

    def get_owner_name(self, obj) -> str:
        return _owner_name(getattr(obj, "owner", None))

    def validate_company(self, company):
        _same_tenant(company, self.context["request"].tenant, "That company is not in this workspace.")
        return company

    def validate_owner(self, owner):
        _require_member(owner, self.context["request"].tenant)
        return owner

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["tenant"] = request.tenant
        validated_data.setdefault("owner", request.user)
        contact = super().create(validated_data)
        _audit(request, "CRM_CONTACT_CREATED", contact)
        return contact

    def update(self, instance, validated_data):
        contact = super().update(instance, validated_data)
        _audit(self.context["request"], "CRM_CONTACT_UPDATED", contact)
        return contact


class DealSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True, default="")
    contact_name = serializers.SerializerMethodField()
    stage_name = serializers.CharField(source="stage.name", read_only=True, default="")
    stage_code = serializers.CharField(source="stage.code", read_only=True, default="")
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = Deal
        fields = (
            "id",
            "pipeline",
            "stage",
            "stage_name",
            "stage_code",
            "company",
            "company_name",
            "contact",
            "contact_name",
            "name",
            "amount",
            "currency",
            "expected_close_at",
            "priority",
            "next_step",
            "won_reason",
            "lost_reason",
            "closed_at",
            "last_activity_at",
            "lead",
            "owner",
            "owner_name",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "company_name",
            "contact_name",
            "stage_name",
            "stage_code",
            "owner_name",
            "last_activity_at",
            "created_at",
            "updated_at",
        )

    def get_contact_name(self, obj) -> str:
        person = getattr(obj, "contact", None)
        if person is None:
            return ""
        return f"{person.first_name} {person.last_name}".strip()

    def get_owner_name(self, obj) -> str:
        return _owner_name(getattr(obj, "owner", None))

    def validate_owner(self, owner):
        _require_member(owner, self.context["request"].tenant)
        return owner

    def validate_lead(self, lead):
        _same_tenant(lead, self.context["request"].tenant, "That lead is not in this workspace.")
        return lead

    def validate(self, attrs):
        tenant = self.context["request"].tenant
        pipeline = attrs["pipeline"] if "pipeline" in attrs else getattr(self.instance, "pipeline", None)
        stage = attrs["stage"] if "stage" in attrs else getattr(self.instance, "stage", None)
        company = attrs["company"] if "company" in attrs else getattr(self.instance, "company", None)
        contact = attrs["contact"] if "contact" in attrs else getattr(self.instance, "contact", None)
        _same_tenant(pipeline, tenant, "That pipeline is not in this workspace.")
        _same_tenant(stage, tenant, "That stage is not in this workspace.")
        _same_tenant(company, tenant, "That company is not in this workspace.")
        _same_tenant(contact, tenant, "That contact is not in this workspace.")
        if pipeline and stage and stage.pipeline_id != pipeline.id:
            raise serializers.ValidationError({"stage": "Stage must belong to the selected pipeline."})
        if contact and company and contact.company_id != company.id:
            raise serializers.ValidationError({"contact": "Contact must belong to the selected company."})
        if stage is not None and "closed_at" not in attrs:
            if stage.is_won or stage.is_lost:
                from django.utils import timezone

                attrs.setdefault("closed_at", timezone.now().date())
            elif self.instance is not None:
                attrs["closed_at"] = None
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["tenant"] = request.tenant
        validated_data.setdefault("owner", request.user)
        deal = super().create(validated_data)
        _mark_lead_synced(deal)
        _audit(request, "CRM_DEAL_CREATED", deal)
        from apps.integrations.push import push_deal

        push_deal(deal.tenant, deal, event="deal.created")
        return deal

    def update(self, instance, validated_data):
        previous_stage = instance.stage_id
        deal = super().update(instance, validated_data)
        _mark_lead_synced(deal)
        _audit(self.context["request"], "CRM_DEAL_UPDATED", deal, {"stage_changed": previous_stage != deal.stage_id})
        if previous_stage != deal.stage_id:
            from apps.integrations.push import push_deal

            push_deal(deal.tenant, deal, event="deal.updated")
        return deal


class ActivitySerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True, default="")
    deal_name = serializers.CharField(source="deal.name", read_only=True, default="")
    contact_name = serializers.SerializerMethodField()
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = (
            "id",
            "company",
            "company_name",
            "deal",
            "deal_name",
            "contact",
            "contact_name",
            "kind",
            "title",
            "body",
            "due_at",
            "completed_at",
            "owner",
            "owner_name",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "company_name", "deal_name", "contact_name", "owner_name", "created_at", "updated_at")

    def get_contact_name(self, obj) -> str:
        person = getattr(obj, "contact", None)
        if person is None:
            return ""
        return f"{person.first_name} {person.last_name}".strip()

    def get_owner_name(self, obj) -> str:
        return _owner_name(getattr(obj, "owner", None))

    def validate_owner(self, owner):
        _require_member(owner, self.context["request"].tenant)
        return owner

    def validate(self, attrs):
        tenant = self.context["request"].tenant
        company = attrs["company"] if "company" in attrs else getattr(self.instance, "company", None)
        deal = attrs["deal"] if "deal" in attrs else getattr(self.instance, "deal", None)
        contact = attrs["contact"] if "contact" in attrs else getattr(self.instance, "contact", None)
        _same_tenant(company, tenant, "That company is not in this workspace.")
        _same_tenant(deal, tenant, "That deal is not in this workspace.")
        _same_tenant(contact, tenant, "That contact is not in this workspace.")
        if deal and company and deal.company_id != company.id:
            raise serializers.ValidationError({"deal": "Deal must belong to the selected company."})
        if contact and company and contact.company_id != company.id:
            raise serializers.ValidationError({"contact": "Contact must belong to the selected company."})
        if contact and deal and contact.company_id != deal.company_id:
            raise serializers.ValidationError({"contact": "Contact must belong to the deal company."})
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        deal = validated_data.get("deal")
        contact = validated_data.get("contact")
        if not validated_data.get("company") and deal is not None:
            validated_data["company"] = deal.company
        if not validated_data.get("company") and contact is not None:
            validated_data["company"] = contact.company
        validated_data["tenant"] = request.tenant
        validated_data.setdefault("owner", request.user)
        activity = super().create(validated_data)
        _touch_last_activity(activity)
        _audit(request, "CRM_ACTIVITY_CREATED", activity)
        return activity

    def update(self, instance, validated_data):
        activity = super().update(instance, validated_data)
        _touch_last_activity(activity)
        _audit(self.context["request"], "CRM_ACTIVITY_UPDATED", activity)
        return activity


def _touch_last_activity(activity):
    stamp = activity.updated_at or activity.created_at
    if activity.company_id:
        Company.objects.filter(id=activity.company_id).update(last_activity_at=stamp)
    if activity.deal_id:
        Deal.objects.filter(id=activity.deal_id).update(last_activity_at=stamp)
