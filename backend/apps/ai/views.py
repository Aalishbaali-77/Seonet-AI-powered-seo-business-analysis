from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.advisors import advise
from apps.ai.query import answer_question
from apps.common.exceptions import APIError
from apps.common.permissions import HasPermissionCode, HasTenant
from apps.rbac.services import user_has_permission
from services.ai_gateway import AIService


class AIUsageView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "billing.view"

    def get(self, request):
        return Response(AIService.usage_summary(request.tenant))


class AdvisorView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant]

    def post(self, request):
        domain = (request.data.get("domain") or "business").strip()
        permission = {
            "business": "business.view",
            "market": "market.view",
            "opportunity": "opportunity.view",
            "lead": "lead.view",
            "marketing": "marketing.view",
        }.get(domain, "business.view")
        if not user_has_permission(request.user, request.tenant, permission):
            raise APIError("You do not have permission to perform this action.", code="PERMISSION_DENIED", status_code=403)
        return Response(advise(tenant=request.tenant, user=request.user, domain=domain))


class QueryView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant]

    def post(self, request):
        question = str(request.data.get("question") or "").strip()
        if not question:
            raise APIError("Enter a question.", code="VALIDATION_ERROR")
        return Response(answer_question(tenant=request.tenant, user=request.user, question=question))
