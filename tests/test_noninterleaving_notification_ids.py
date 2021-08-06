# -*- coding: utf-8 -*-
from typing import TYPE_CHECKING

from eventsourcing.tests.noninterleaving_notification_ids_testcase import (
    NonInterleavingNotificationIDsBaseCase,
)
from eventsourcing.tests.test_postgres import pg_close_all_connections

from eventsourcing_django.models import StoredEventRecord
from eventsourcing_django.recorders import DjangoApplicationRecorder
from tests.test_recorders import DjangoTestCase

if TYPE_CHECKING:
    from typing import Optional


class TestNonInterleaving(DjangoTestCase, NonInterleavingNotificationIDsBaseCase):
    db_alias: Optional[str] = None

    def create_recorder(self) -> DjangoApplicationRecorder:
        return DjangoApplicationRecorder(
            application_name="app", model=StoredEventRecord, using=self.db_alias
        )


class TestNonInterleavingSQLiteFileDB(TestNonInterleaving):
    insert_num = 1000
    db_alias = "sqlite_filedb"
    databases = {"default", "sqlite_filedb"}


class TestNonInterleavingPostgres(TestNonInterleaving):
    insert_num = 10
    db_alias = "postgres"
    databases = {"default", "postgres"}

    @classmethod
    def tearDownClass(cls) -> None:
        # Need to close all connections Django made from other threads,
        # otherwise Django can't tear down the database.
        super().tearDownClass()
        pg_close_all_connections(
            name="test_eventsourcing_django",
        )


del NonInterleavingNotificationIDsBaseCase
