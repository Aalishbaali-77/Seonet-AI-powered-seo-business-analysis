from django.apps import AppConfig


class RbacConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.rbac"
    label = "rbac"
    verbose_name = "RBAC"

    def ready(self) -> None:
        from apps.rbac import signals  # noqa: F401
