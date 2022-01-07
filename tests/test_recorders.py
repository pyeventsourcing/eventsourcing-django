# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from typing import TYPE_CHECKING
from unittest import skip

import django
from django.test import TransactionTestCase
from eventsourcing.base_test_cases import (
    AggregateRecorderTestCase,
    ApplicationRecorderTestCase,
    ProcessRecorderTestCase,
)
from eventsourcing.tests.persistence_tests.test_postgres import pg_close_all_connections

from eventsourcing_django.models import SnapshotRecord, StoredEventRecord
from eventsourcing_django.recorders import (
    DjangoAggregateRecorder,
    DjangoApplicationRecorder,
    DjangoProcessRecorder,
    journal_modes,
)

if TYPE_CHECKING:
    from typing import Any, Optional

from django.db import connection
from django.db.backends.sqlite3.operations import DatabaseOperations


def _monkey_patch_sqlite_sql_flush_with_sequence_reset():  # type: ignore
    original_sql_flush = DatabaseOperations.sql_flush

    def sql_flush_with_sequence_reset(  # type: ignore
        self, style, tables, sequences, allow_cascade=False
    ):
        sql_statement_list = original_sql_flush(
            self, style, tables, sequences, allow_cascade
        )
        if tables:
            # DELETE FROM sqlite_sequence WHERE name IN ($tables)
            sql = "%s %s %s %s %s %s (%s);" % (
                style.SQL_KEYWORD("DELETE"),
                style.SQL_KEYWORD("FROM"),
                style.SQL_TABLE(self.quote_name("sqlite_sequence")),
                style.SQL_KEYWORD("WHERE"),
                style.SQL_FIELD(self.quote_name("name")),
                style.SQL_KEYWORD("IN"),
                ", ".join(style.SQL_FIELD(f"'{table}'") for table in tables),
            )
            sql_statement_list.append(sql)
        return sql_statement_list

    DatabaseOperations.sql_flush = sql_flush_with_sequence_reset


class DjangoTestCase(TransactionTestCase):
    reset_sequences = True

    @classmethod
    def setUpClass(cls):  # type: ignore
        super().setUpClass()
        if django.VERSION[0:2] <= (3, 0):
            if connection.vendor == "sqlite":
                _monkey_patch_sqlite_sql_flush_with_sequence_reset()

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

    def close_db_connection(self, *args: Any) -> None:
        connection.close()


class TestDjangoApplicationRecorderWithSQLiteInMemory(TestDjangoApplicationRecorder):
    @skip(reason="Get 'Database is locked' error with GitHub Actions")
    def test_concurrent_no_conflicts(self) -> None:
        super().test_concurrent_no_conflicts()


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


del AggregateRecorderTestCase
del ApplicationRecorderTestCase
del ProcessRecorderTestCase
del TestDjangoApplicationRecorder
