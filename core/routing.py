"""WebSocket URL routing for Django Channels."""

from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path("ws/dashboard/", consumers.DashboardConsumer.as_asgi()),
    path("ws/notifications/", consumers.NotificationConsumer.as_asgi()),
]
