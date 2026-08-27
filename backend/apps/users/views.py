from __future__ import annotations

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.auditlog.services import write_audit
from apps.common.throttling import AuthBurstThrottle
from apps.tenants.services import create_tenant_for_owner
from apps.users.cookies import clear_auth_cookies, set_auth_cookies, tokens_for_user
from apps.users.serializers import (
    LoginSerializer,
    MeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
)

User = get_user_model()


def _client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthBurstThrottle]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = User.objects.create_user(
            email=data["email"],
            password=data["password"],
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
        )
        tenant = create_tenant_for_owner(name=data["company_name"], owner=user)
        request.tenant = tenant
        write_audit(action="USER_REGISTERED", request=request, user=user, tenant=tenant, resource_type="user", resource_id=user.id)
        write_audit(action="TENANT_CREATED", request=request, user=user, tenant=tenant, resource_type="tenant", resource_id=tenant.id)
        refresh = tokens_for_user(user)
        response = Response(MeSerializer(user, context={"request": request}).data, status=status.HTTP_201_CREATED)
        return set_auth_cookies(response, refresh)


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthBurstThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]
        user = authenticate(request, username=email, password=password)
        if user is None:
            candidate = User.objects.filter(email=email).first()
            if candidate is not None and candidate.check_password(password):
                user = candidate
        if user is None or not user.is_active:
            return Response(
                {
                    "error": {
                        "code": "UNAUTHENTICATED",
                        "message": "Invalid email or password.",
                        "details": {},
                        "request_id": getattr(request, "request_id", ""),
                    }
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )
        user.last_login_ip = _client_ip(request)
        user.save(update_fields=["last_login_ip"])
        from apps.tenants.models import Membership

        home = (
            Membership.objects.filter(user=user, status=Membership.Status.ACTIVE)
            .select_related("tenant")
            .order_by("-is_default", "created_at")
            .first()
        )
        write_audit(
            action="USER_LOGIN",
            request=request,
            user=user,
            tenant=home.tenant if home else None,
            scope="workspace" if home else "platform",
            resource_type="user",
            resource_id=user.id,
        )
        refresh = tokens_for_user(user)
        response = Response(MeSerializer(user, context={"request": request}).data)
        return set_auth_cookies(response, refresh)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        raw = request.COOKIES.get(settings.AUTH_COOKIE_REFRESH)
        if raw:
            try:
                token = RefreshToken(raw)
                token.blacklist()
            except (TokenError, InvalidToken):
                pass
        write_audit(
            action="USER_LOGOUT",
            request=request,
            tenant=getattr(request, "tenant", None),
            scope="workspace" if getattr(request, "tenant", None) else "platform",
            resource_type="user",
            resource_id=request.user.id,
        )
        response = Response(status=status.HTTP_204_NO_CONTENT)
        return clear_auth_cookies(response)


class RefreshView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthBurstThrottle]

    def post(self, request):
        raw = request.COOKIES.get(settings.AUTH_COOKIE_REFRESH)
        if not raw:
            return Response(
                {
                    "error": {
                        "code": "UNAUTHENTICATED",
                        "message": "Refresh token missing.",
                        "details": {},
                        "request_id": getattr(request, "request_id", ""),
                    }
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            token = RefreshToken(raw)
            token.blacklist()
            user = User.objects.get(id=token["user_id"])
            refresh = tokens_for_user(user)
        except (TokenError, InvalidToken, User.DoesNotExist, KeyError):
            return Response(
                {
                    "error": {
                        "code": "UNAUTHENTICATED",
                        "message": "Refresh token is invalid.",
                        "details": {},
                        "request_id": getattr(request, "request_id", ""),
                    }
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )
        response = Response({"ok": True})
        return set_auth_cookies(response, refresh)


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = MeSerializer

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return ProfileUpdateSerializer
        return MeSerializer

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        request.user.refresh_from_db()
        return Response(MeSerializer(request.user, context={"request": request}).data)


class PasswordResetRequestView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthBurstThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()
        user = User.objects.filter(email=email).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = f"{settings.CORS_ALLOWED_ORIGINS[0] if settings.CORS_ALLOWED_ORIGINS else 'http://localhost:3000'}/reset-password?uid={uid}&token={token}"
            send_mail(
                subject="Reset your SIPulse password",
                message=f"Reset your password: {reset_url}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        return Response({"ok": True})


class PasswordResetConfirmView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthBurstThrottle]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user_id = force_str(urlsafe_base64_decode(serializer.validated_data["uid"]))
            user = User.objects.get(pk=user_id)
        except (User.DoesNotExist, ValueError, TypeError):
            return Response(
                {
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Invalid reset token.",
                        "details": {},
                        "request_id": getattr(request, "request_id", ""),
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not default_token_generator.check_token(user, serializer.validated_data["token"]):
            return Response(
                {
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Invalid or expired reset token.",
                        "details": {},
                        "request_id": getattr(request, "request_id", ""),
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(serializer.validated_data["password"])
        user.save(update_fields=["password"])
        from apps.tenants.models import Membership

        Membership.objects.filter(user=user, status=Membership.Status.INVITED).update(status=Membership.Status.ACTIVE)
        return Response({"ok": True})
