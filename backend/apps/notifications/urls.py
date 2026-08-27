from django.urls import path

from apps.notifications.views import NotificationListView, NotificationReadAllView, NotificationReadView

urlpatterns = [
    path("", NotificationListView.as_view(), name="notification-list"),
    path("read-all/", NotificationReadAllView.as_view(), name="notification-read-all"),
    path("<uuid:id>/read/", NotificationReadView.as_view(), name="notification-read"),
]
