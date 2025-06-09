# -*- coding: utf-8 -*-
import os

from eventsourcing.tests.application import ExampleApplicationTestCase

from tests.test_recorders import DjangoTestCase


class TestApplicationWithDjango(DjangoTestCase, ExampleApplicationTestCase):
    expected_factory_topic = "eventsourcing_django.factory:Factory"
    django_db_alias = ""

    def setUp(self) -> None:
        super().setUp()
        os.environ["PERSISTENCE_MODULE"] = "eventsourcing_django"
        os.environ["DJANGO_DB_ALIAS"] = self.django_db_alias

    def tearDown(self) -> None:
        del os.environ["PERSISTENCE_MODULE"]
        del os.environ["DJANGO_DB_ALIAS"]
        super().tearDown()


class TestWithSQLiteFileDb(TestApplicationWithDjango):
    django_db_alias = "sqlite_filedb"
    databases = {"default", "sqlite_filedb"}


class TestWithPostgres(TestApplicationWithDjango):
    django_db_alias = "postgres"
    databases = {"default", "postgres"}


del ExampleApplicationTestCase
