# -*- coding: utf-8 -*-
from __future__ import annotations

from eventsourcing.persistence import (
    AggregateRecorder,
    ApplicationRecorder,
    InfrastructureFactory,
    ProcessRecorder,
)
from eventsourcing.utils import Environment

from eventsourcing_django.models import SnapshotRecord, StoredEventRecord
from eventsourcing_django.recorders import (
    DjangoAggregateRecorder,
    DjangoApplicationRecorder,
    DjangoProcessRecorder,
)


class Factory(InfrastructureFactory):
    DJANGO_DB_ALIAS = "DJANGO_DB_ALIAS"

    def __init__(self, env: Environment):
        super().__init__(env)
        self.db_alias = self.env.get(self.DJANGO_DB_ALIAS) or None

    def aggregate_recorder(self, purpose: str = "events") -> AggregateRecorder:
        if purpose == "snapshots":
            model = SnapshotRecord
        else:
            model = StoredEventRecord
        return DjangoAggregateRecorder(
            application_name=self.env.name, model=model, using=self.db_alias
        )

    def application_recorder(self) -> ApplicationRecorder:
        return DjangoApplicationRecorder(
            application_name=self.env.name,
            model=StoredEventRecord,
            using=self.db_alias,
        )

    def process_recorder(self) -> ProcessRecorder:
        return DjangoProcessRecorder(
            application_name=self.env.name,
            model=StoredEventRecord,
            using=self.db_alias,
        )
