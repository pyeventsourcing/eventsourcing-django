# -*- coding: utf-8 -*-
import os

from eventsourcing.tests.example_application import (
    TIMEIT_FACTOR,
    ExampleApplicationTestCase,
)

from tests.test_recorders import DjangoTestCase


class TestApplicationWithDjango(DjangoTestCase, ExampleApplicationTestCase):
    timeit_number = 30 * TIMEIT_FACTOR
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
    timeit_number = 5 * TIMEIT_FACTOR
    django_db_alias = "postgres"
    databases = {"default", "postgres"}


del ExampleApplicationTestCase
