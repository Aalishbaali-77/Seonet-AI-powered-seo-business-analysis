from collections import defaultdict

from django.http import HttpResponse
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.exceptions import APIError
from apps.common.permissions import HasPermissionCode, HasTenant
from apps.markets.catalog import ensure_geo_catalog
from apps.markets.collect import start_market_collect
from apps.markets.imports import csv_template, start_signal_import
from apps.markets.models import GeoPlace, MarketFocus, MarketSignal, ScoringProfile
from apps.markets.research import market_brief, start_market_analysis
from apps.markets.scoring import DEFAULT_WEIGHTS, normalize_weights, score_from_signals, tenant_weights
from apps.markets.serializers import GeoPlaceSerializer, MarketFocusSerializer, MarketSignalSerializer, ScoringProfileSerializer


class MarketModule:
    required_module = "markets"


def _scores_for_places(tenant, places) -> dict:
    weights = tenant_weights(tenant)
    ids = [place.id for place in places]
    signals = MarketSignal.objects.for_tenant(tenant).filter(place_id__in=ids)
    grouped: dict = defaultdict(list)
    for item in signals:
        grouped[item.place_id].append(item)
    return {str(place_id): score_from_signals(items, weights) for place_id, items in grouped.items()}


class MarketOverviewView(MarketModule, APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "market.view"

    def get(self, request):
        ensure_geo_catalog()
        cities = list(GeoPlace.objects.filter(kind=GeoPlace.Kind.CITY, country_code="PK"))
        scores = _scores_for_places(request.tenant, cities)
        rows = []
        scored = 0
        for city in cities:
            payload = scores.get(str(city.id)) or score_from_signals([], tenant_weights(request.tenant))
            if payload.get("score") is not None:
                scored += 1
            rows.append({"place": GeoPlaceSerializer(city).data, "score": payload})
        rows.sort(key=lambda item: (item["score"]["score"] is None, -(item["score"]["score"] or 0), item["place"]["name"]))
        return Response(
            {
                "country": "Pakistan",
                "cities": rows,
                "weights": tenant_weights(request.tenant),
                "scored_cities": scored,
                "note": "City names are geographic reference data. Opportunity scores appear only after you ingest market signals for this workspace.",
            }
        )


class GeoPlaceListView(MarketModule, generics.ListAPIView):
    serializer_class = GeoPlaceSerializer
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "market.view"
    pagination_class = None
    filterset_fields = ("kind", "parent")
    search_fields = ("name", "code")

    def get_queryset(self):
        ensure_geo_catalog()
        return GeoPlace.objects.select_related("parent")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        places = list(self.filter_queryset(self.get_queryset()))
        context["scores"] = _scores_for_places(self.request.tenant, places)
        return context


class GeoPlaceDetailView(MarketModule, APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "market.view"

    def get(self, request, id):
        ensure_geo_catalog()
        place = GeoPlace.objects.filter(id=id).select_related("parent").first()
        if place is None:
            from apps.common.exceptions import APIError

            raise APIError("Resource not found.", code="NOT_FOUND", status_code=404)
        children = list(place.children.all())
        signals = list(MarketSignal.objects.for_tenant(request.tenant).filter(place=place))
        payload = score_from_signals(signals, tenant_weights(request.tenant))
        return Response(
            {
                "place": GeoPlaceSerializer(place).data,
                "parent": GeoPlaceSerializer(place.parent).data if place.parent_id else None,
                "children": GeoPlaceSerializer(children, many=True).data,
                "signals": MarketSignalSerializer(signals, many=True).data,
                "score": payload,
            }
        )


class ScoringProfileView(MarketModule, APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]

    @property
    def required_permission(self):
        return "market.manage" if self.request.method in {"PUT", "PATCH"} else "market.view"

    def get(self, request):
        profile = ScoringProfile.objects.for_tenant(request.tenant).first()
        weights = tenant_weights(request.tenant)
        return Response({"id": str(profile.id) if profile else None, "weights": weights, "defaults": DEFAULT_WEIGHTS})

    def put(self, request):
        profile = ScoringProfile.objects.for_tenant(request.tenant).first()
        if profile is None:
            profile = ScoringProfile.objects.create(tenant=request.tenant, weights=DEFAULT_WEIGHTS)
        serializer = ScoringProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"id": str(profile.id), "weights": normalize_weights(profile.weights), "defaults": DEFAULT_WEIGHTS})

    def patch(self, request):
        return self.put(request)


class MarketFocusListCreateView(MarketModule, generics.ListCreateAPIView):
    serializer_class = MarketFocusSerializer
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    pagination_class = None

    @property
    def required_permission(self):
        return "market.manage" if self.request.method == "POST" else "market.view"

    def get_queryset(self):
        return MarketFocus.objects.for_tenant(self.request.tenant).select_related("place")


class MarketSignalListCreateView(MarketModule, generics.ListCreateAPIView):
    serializer_class = MarketSignalSerializer
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    filterset_fields = ("place", "kind")
    pagination_class = None

    @property
    def required_permission(self):
        return "market.manage" if self.request.method == "POST" else "market.view"

    def get_queryset(self):
        return MarketSignal.objects.for_tenant(self.request.tenant).select_related("place")


class MarketBriefView(MarketModule, APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "market.view"

    def get(self, request):
        return Response(market_brief(request.tenant))

    def post(self, request):
        from apps.rbac.services import user_has_permission

        body = request.data or {}
        profile = body.get("profile") if isinstance(body.get("profile"), dict) else None
        if profile and not user_has_permission(request.user, request.tenant, "business.manage"):
            raise APIError("You do not have permission to perform this action.", code="PERMISSION_DENIED", status_code=403)
        from apps.jobs.serializers import JobSerializer

        question = str(body.get("question") or "").strip()
        job = start_market_analysis(tenant=request.tenant, user=request.user, question=question, profile=profile)
        return Response(JobSerializer(job).data, status=202)


class MarketSignalImportView(MarketModule, APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]

    @property
    def required_permission(self):
        return "market.manage" if self.request.method == "POST" else "market.view"

    def get(self, request):
        filename, content = csv_template()
        response = HttpResponse(content, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    def post(self, request):
        from apps.jobs.serializers import JobSerializer

        upload = request.FILES.get("file")
        if upload is None:
            raise APIError("Upload a CSV file.", code="VALIDATION_ERROR")
        job = start_signal_import(tenant=request.tenant, user=request.user, raw=upload.read())
        return Response(JobSerializer(job).data, status=202)


class MarketCollectView(MarketModule, APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "market.manage"

    def post(self, request):
        from apps.jobs.serializers import JobSerializer

        job = start_market_collect(tenant=request.tenant, user=request.user)
        return Response(JobSerializer(job).data, status=202)
