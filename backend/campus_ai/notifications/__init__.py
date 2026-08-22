"""Public notification contracts and supported delivery channels."""

from campus_ai.notifications.base import NotificationChannel, NotificationEvent, NotificationResult
from campus_ai.notifications.fcm import FcmNotificationChannel
from campus_ai.notifications.unified_push import UnifiedPushNotificationChannel

__all__ = [
    "FcmNotificationChannel",
    "NotificationChannel",
    "NotificationEvent",
    "NotificationResult",
    "UnifiedPushNotificationChannel",
]
