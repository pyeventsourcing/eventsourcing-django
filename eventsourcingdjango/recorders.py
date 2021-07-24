from typing import Any, List, Optional
from uuid import UUID

from django.db import IntegrityError, transaction
from eventsourcing.persistence import (
    AggregateRecorder,
    ApplicationRecorder,
    Notification,
    ProcessRecorder,
    RecordConflictError,
    StoredEvent,
    Tracking,
)

from eventsourcingdjango.models import NotificationTrackingRecord


class DjangoAggregateRecorder(AggregateRecorder):
    def __init__(self, application_name: str, model):
        super().__init__()
        self.application_name = application_name
        self.model = model

    def insert_events(self, stored_events: List[StoredEvent], **kwargs: Any) -> None:
        try:
            with transaction.atomic():
                self._insert_events(stored_events, **kwargs)
        except IntegrityError:
            raise RecordConflictError()

    def _insert_events(self, stored_events: List[StoredEvent], **kwargs):
        records = []
        for stored_event in stored_events:
            record = self.model(
                application_name=self.application_name,
                originator_id=stored_event.originator_id,
                originator_version=stored_event.originator_version,
                topic=stored_event.topic,
                state=stored_event.state,
            )
            records.append(record)
        for record in records:
            record.save()

    def select_events(
        self,
        originator_id: UUID,
        gt: Optional[int] = None,
        lte: Optional[int] = None,
        desc: bool = False,
        limit: Optional[int] = None,
    ) -> List[StoredEvent]:
        f = self.model.objects.filter(
            application_name=self.application_name, originator_id=originator_id
        )
        f = f.order_by(("" if not desc else "-") + "originator_version")
        if gt is not None:
            f = f.filter(originator_version__gt=gt)
        if lte is not None:
            f = f.filter(originator_version__lte=lte)
        if limit is not None:
            f = f[0:limit]
        return [
            StoredEvent(
                originator_id=r.originator_id,
                originator_version=r.originator_version,
                topic=r.topic,
                state=r.state,
            )
            for r in f
        ]


class DjangoApplicationRecorder(DjangoAggregateRecorder, ApplicationRecorder):
    def max_notification_id(self) -> int:
        f = self.model.objects.filter(
            application_name=self.application_name,
        )
        f = f.order_by("-id")
        try:
            return f[0].id
        except IndexError:
            return 0

    def select_notifications(self, start: int, limit: int) -> List[Notification]:
        f = self.model.objects.filter(
            application_name=self.application_name,
        )
        f = f.order_by("id")
        f = f.filter(id__gte=start)
        return [
            Notification(
                id=r.id,
                originator_id=r.originator_id,
                originator_version=r.originator_version,
                topic=r.topic,
                state=r.state,
            )
            for r in f[0:limit]
        ]


class DjangoProcessRecorder(DjangoApplicationRecorder, ProcessRecorder):
    def _insert_events(self, stored_events: List[StoredEvent], **kwargs):
        super(DjangoProcessRecorder, self)._insert_events(stored_events, **kwargs)
        tracking: Optional[Tracking] = kwargs.get("tracking", None)
        if tracking is not None:
            record = NotificationTrackingRecord(
                application_name=self.application_name,
                upstream_application_name=tracking.application_name,
                notification_id=tracking.notification_id,
            )
            record.save()

    def max_tracking_id(self, application_name: str) -> int:
        f = NotificationTrackingRecord.objects.filter(
            application_name=self.application_name,
            upstream_application_name=application_name,
        )
        f = f.order_by("-notification_id")
        try:
            return f[0].notification_id
        except IndexError:
            return 0
