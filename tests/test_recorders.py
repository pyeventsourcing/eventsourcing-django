from django.db import connection
from django.test import TransactionTestCase
from eventsourcing.tests.test_postgres import pg_close_all_connections

from eventsourcing_django.models import SnapshotRecord, StoredEventRecord
from eventsourcing_django.recorders import (
    DjangoAggregateRecorder,
    DjangoApplicationRecorder,
    DjangoProcessRecorder,
    journal_modes,
)


from eventsourcing.tests.aggregaterecorder_testcase import (
    AggregateRecorderTestCase,
)
from eventsourcing.tests.applicationrecorder_testcase import (
    ApplicationRecorderTestCase,
)
from eventsourcing.tests.processrecorder_testcase import ProcessRecorderTestCase


class DjangoTestCase(TransactionTestCase):
    reset_sequences = True

    def tearDown(self) -> None:
        journal_modes.clear()
        super().tearDown()


class TestDjangoAggregateRecorder(DjangoTestCase, AggregateRecorderTestCase):
    def create_recorder(self):
        return DjangoAggregateRecorder(application_name="app", model=StoredEventRecord)

    def close_db_connection(self, *args):
        connection.close()

class TestDjangoSnapshotRecorder(DjangoTestCase, AggregateRecorderTestCase):
    def create_recorder(self):
        return DjangoAggregateRecorder(application_name="app", model=SnapshotRecord)

    def close_db_connection(self, *args):
        connection.close()


class TestDjangoApplicationRecorder(DjangoTestCase, ApplicationRecorderTestCase):
    db_alias = None

    def create_recorder(self):
        return DjangoApplicationRecorder(
            application_name="app", model=StoredEventRecord, using=self.db_alias
        )

    def test_insert_select(self):
        super(TestDjangoApplicationRecorder, self).test_insert_select()

    def test_concurrent_no_conflicts(self):
        super().test_concurrent_no_conflicts()

    def close_db_connection(self, *args):
        connection.close()


class TestDjangoApplicationRecorderWithSQLiteFileDb(TestDjangoApplicationRecorder):
    db_alias = "sqlite_filedb"
    databases = {"default", "sqlite_filedb"}


class TestDjangoApplicationRecorderWithPostgres(TestDjangoApplicationRecorder):
    db_alias = "postgres"
    databases = {"default", "postgres"}

    @classmethod
    def tearDownClass(cls):
        # Need to close all connections Django made from other threads,
        # otherwise Django can't tear down the database.
        super().tearDownClass()
        pg_close_all_connections(
            name="test_eventsourcing_django",
        )


class TestDjangoProcessRecorder(DjangoTestCase, ProcessRecorderTestCase):
    def create_recorder(self):
        return DjangoProcessRecorder(application_name="app", model=StoredEventRecord)

    def test_insert_select(self):
        super(TestDjangoProcessRecorder, self).test_insert_select()

    def test_performance(self):
        super().test_performance()


del AggregateRecorderTestCase
del ApplicationRecorderTestCase
del ProcessRecorderTestCase
