# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from django.db import connection
from django.test import TransactionTestCase
from eventsourcing.tests.aggregaterecorder_testcase import AggregateRecorderTestCase
from eventsourcing.tests.applicationrecorder_testcase import ApplicationRecorderTestCase
from eventsourcing.tests.processrecorder_testcase import ProcessRecorderTestCase
from eventsourcing.tests.test_postgres import pg_close_all_connections

from eventsourcing_django.models import SnapshotRecord, StoredEventRecord
from eventsourcing_django.recorders import (
    DjangoAggregateRecorder,
    DjangoApplicationRecorder,
    DjangoProcessRecorder,
    journal_modes,
)

if TYPE_CHECKING:
    from typing import Any, Optional


class DjangoTestCase(TransactionTestCase):
    reset_sequences = True

    def tearDown(self) -> None:
        journal_modes.clear()
        super().tearDown()


class TestDjangoAggregateRecorder(DjangoTestCase, AggregateRecorderTestCase):
    def create_recorder(self) -> DjangoAggregateRecorder:
        return DjangoAggregateRecorder(application_name="app", model=StoredEventRecord)

    def close_db_connection(self, *args: Any) -> None:
        connection.close()


class TestDjangoSnapshotRecorder(DjangoTestCase, AggregateRecorderTestCase):
    def create_recorder(self) -> DjangoAggregateRecorder:
        return DjangoAggregateRecorder(application_name="app", model=SnapshotRecord)

    def close_db_connection(self, *args: Any) -> None:
        connection.close()


class TestDjangoApplicationRecorder(DjangoTestCase, ApplicationRecorderTestCase):
    db_alias: Optional[str] = None

    def create_recorder(self) -> DjangoApplicationRecorder:
        return DjangoApplicationRecorder(
            application_name="app", model=StoredEventRecord, using=self.db_alias
        )

    def test_insert_select(self) -> None:
        super(TestDjangoApplicationRecorder, self).test_insert_select()

    def test_concurrent_no_conflicts(self) -> None:
        super().test_concurrent_no_conflicts()

    def close_db_connection(self, *args: Any) -> None:
        connection.close()


class TestDjangoApplicationRecorderWithSQLiteFileDb(TestDjangoApplicationRecorder):
    db_alias = "sqlite_filedb"
    databases = {"default", "sqlite_filedb"}


class TestDjangoApplicationRecorderWithPostgres(TestDjangoApplicationRecorder):
    db_alias = "postgres"
    databases = {"default", "postgres"}

    @classmethod
    def tearDownClass(cls) -> None:
        # Need to close all connections Django made from other threads,
        # otherwise Django can't tear down the database.
        super().tearDownClass()
        pg_close_all_connections(
            host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
            name="test_" + os.getenv("POSTGRES_DB", "eventsourcing_django"),
            user=os.getenv("POSTGRES_USER", "eventsourcing"),
            password=os.getenv("POSTGRES_PASSWORD", "eventsourcing"),
        )


class TestDjangoProcessRecorder(DjangoTestCase, ProcessRecorderTestCase):
    def create_recorder(self) -> DjangoProcessRecorder:
        return DjangoProcessRecorder(application_name="app", model=StoredEventRecord)

    def test_insert_select(self) -> None:
        super(TestDjangoProcessRecorder, self).test_insert_select()

    def test_performance(self) -> None:
        super().test_performance()


del AggregateRecorderTestCase
del ApplicationRecorderTestCase
del ProcessRecorderTestCase
