from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from campus_ai.models import NotificationDelivery
from campus_ai.notifications.base import NotificationChannel, NotificationEvent, NotificationResult


def send_once(
    session: Session,
    *,
    channel: NotificationChannel,
    device_id: str,
    endpoint: str,
    event: NotificationEvent,
) -> tuple[NotificationDelivery, bool]:
    existing = session.scalar(
        select(NotificationDelivery).where(
            NotificationDelivery.channel == channel.name,
            NotificationDelivery.device_id == device_id,
            NotificationDelivery.event_key == event.event_key,
        )
    )
    if existing is not None and existing.status == "accepted":
        return existing, False

    try:
        result: NotificationResult = channel.send(endpoint=endpoint, event=event)
    except Exception as exc:
        delivery = existing or NotificationDelivery(
            channel=channel.name, device_id=device_id, event_key=event.event_key, status="failed"
        )
        delivery.status = "failed"
        delivery.response = {"error": f"{type(exc).__name__}: {exc}"[:1000]}
        if existing is None:
            session.add(delivery)
        session.commit()
        raise

    delivery = existing or NotificationDelivery(
        channel=channel.name, device_id=device_id, event_key=event.event_key, status="accepted"
    )
    delivery.status = "accepted"
    delivery.response = {"provider_message_id": result.provider_message_id, **result.response}
    if existing is None:
        session.add(delivery)
    session.commit()
    session.refresh(delivery)
    return delivery, True
