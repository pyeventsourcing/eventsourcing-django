from contextlib import contextmanager
from functools import wraps
from threading import Lock
from typing import Any, List, Optional, Type
from uuid import UUID

import django.db
from django.db import models, transaction
from django.db.transaction import get_connection
from eventsourcing.persistence import (
    AggregateRecorder,
    ApplicationRecorder,
    DataError,
    DatabaseError,
    IntegrityError,
    InterfaceError,
    InternalError,
    NotSupportedError,
    Notification,
    OperationalError,
    PersistenceError,
    ProcessRecorder,
    ProgrammingError,
    StoredEvent,
    Tracking,
)

from eventsourcingdjango.models import NotificationTrackingRecord


from django.db.backends.signals import connection_created


journal_modes = {}


def detect_sqlite(connection):
    return connection.vendor == "sqlite"


def detect_sqlite_memory_mode(connection):
    db_name = str(connection.settings_dict["NAME"])
    return ":memory:" in db_name or "mode=memory" in db_name


def set_journal_mode_wal_on_sqlite_file_db(sender, connection, **kwargs):
    """Enable integrity constraint with sqlite."""
    if detect_sqlite(connection) and not detect_sqlite_memory_mode(connection):
        db_name = str(connection.settings_dict["NAME"])
        if journal_modes.get(db_name) != "WAL":
            cursor = connection.cursor()
            cursor.execute("PRAGMA journal_mode;")
            mode = cursor.fetchall()
            if mode[0][0].upper() != "WAL":
                cursor.execute("PRAGMA journal_mode=WAL;")
            journal_modes[db_name] = "WAL"


connection_created.connect(set_journal_mode_wal_on_sqlite_file_db)


def errors(f):
    @wraps(f)
    def _wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except django.db.InterfaceError as e:
            raise InterfaceError(e)
        except django.db.DataError as e:
            raise DataError(e)
        except django.db.OperationalError as e:
            raise OperationalError(e)
        except django.db.IntegrityError as e:
            raise IntegrityError(e)
        except django.db.InternalError as e:
            raise InternalError(e)
        except django.db.ProgrammingError as e:
            raise ProgrammingError(e)
        except django.db.NotSupportedError as e:
            raise NotSupportedError(e)
        except django.db.DatabaseError as e:
            raise DatabaseError(e)
        except django.db.Error as e:
            raise PersistenceError(e)

    return _wrapper


class DjangoAggregateRecorder(AggregateRecorder):
    def __init__(
        self,
        application_name: str,
        model: Type[models.Model],
        using: Optional[str] = None,
    ):
        super().__init__()
        self.application_name = application_name
        self.model = model
        self.using = using
        connection = get_connection(using=self.using)
        if detect_sqlite(connection) and detect_sqlite_memory_mode(connection):
            self.lock = Lock()
        else:
            self.lock = None

    @contextmanager
    def serialize(self):
        try:
            if self.lock:
                self.lock.acquire()
            yield
        finally:
            if self.lock:
                self.lock.release()

    @errors
    def insert_events(self, stored_events: List[StoredEvent], **kwargs: Any) -> None:
        with self.serialize():
            with transaction.atomic(using=self.using):
                self._insert_events(stored_events, **kwargs)

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
            record.save(using=self.using)

    @errors
    def select_events(
        self,
        originator_id: UUID,
        gt: Optional[int] = None,
        lte: Optional[int] = None,
        desc: bool = False,
        limit: Optional[int] = None,
    ) -> List[StoredEvent]:
        with self.serialize():
            q = self.model.objects.using(alias=self.using).filter(
                application_name=self.application_name, originator_id=originator_id
            )
            q = q.order_by(("" if not desc else "-") + "originator_version")
            if gt is not None:
                q = q.filter(originator_version__gt=gt)
            if lte is not None:
                q = q.filter(originator_version__lte=lte)
            if limit is not None:
                q = q[0:limit]
            records = list(q)
        return [
            StoredEvent(
                originator_id=r.originator_id,
                originator_version=r.originator_version,
                topic=r.topic,
                state=bytes(r.state) if isinstance(r.state, memoryview) else r.state,
            )
            for r in records
        ]


class DjangoApplicationRecorder(DjangoAggregateRecorder, ApplicationRecorder):
    @errors
    def select_notifications(self, start: int, limit: int) -> List[Notification]:
        with self.serialize():
            q = self.model.objects.using(alias=self.using).filter(
                application_name=self.application_name,
            )
            q = q.order_by("id")
            q = q.filter(id__gte=start)
            q = q[0:limit]
            records = list(q)
        return [
            Notification(
                id=r.id,
                originator_id=r.originator_id,
                originator_version=r.originator_version,
                topic=r.topic,
                state=bytes(r.state) if isinstance(r.state, memoryview) else r.state,
            )
            for r in records
        ]

    @errors
    def max_notification_id(self) -> int:
        with self.serialize():
            q = self.model.objects.using(alias=self.using).filter(
                application_name=self.application_name,
            )
            q = q.order_by("-id")
            try:
                max_id = q[0].id
            except IndexError:
                max_id = 0
        return max_id


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
            record.save(using=self.using)

    @errors
    def max_tracking_id(self, application_name: str) -> int:
        with self.serialize():
            q = NotificationTrackingRecord.objects.using(alias=self.using).filter(
                application_name=self.application_name,
                upstream_application_name=application_name,
            )
            q = q.order_by("-notification_id")
            try:
                max_id = q[0].notification_id
            except IndexError:
                max_id = 0
        return max_id
