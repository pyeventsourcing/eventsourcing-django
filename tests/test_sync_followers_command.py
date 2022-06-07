# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib
import os
import types

import eventsourcing.system
from django.apps.registry import apps
from django.core.management import call_command
from django.test import modify_settings, override_settings
from eventsourcing.tests.application import BankAccounts

from tests.emails.application import FormalEmailProcess, InformalEmailProcess
from tests.test_recorders import DjangoTestCase


def load_sync_followers_module() -> types.ModuleType:
    return importlib.import_module(
        "eventsourcing_django.management.commands.sync_followers"
    )


class TestSyncCommand(DjangoTestCase):
    django_db_alias = "default"
    runner: eventsourcing.system.Runner

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        os.environ["PERSISTENCE_MODULE"] = "eventsourcing_django"
        os.environ["DJANGO_DB_ALIAS"] = cls.django_db_alias

    @classmethod
    def tearDownClass(cls) -> None:
        del os.environ["PERSISTENCE_MODULE"]
        del os.environ["DJANGO_DB_ALIAS"]
        super().tearDownClass()

    def setUp(self) -> None:
        runner_django_app = apps.get_app_config("eventsourcing_runner_django")
        self.runner = runner_django_app.make_runner()

    def tearDown(self) -> None:
        self.runner.stop()

    def _create_leader_events(self) -> int:
        accounts = self.runner.get(BankAccounts)
        accounts.open_account(full_name="Alpha", email_address="alpha@example.com")
        accounts.open_account(full_name="Beta", email_address="beta@example.com")
        return accounts.recorder.max_notification_id()

    def test_sync_one_app(self) -> None:
        leader_notification_id = self._create_leader_events()
        formal_emails = self.runner.get(FormalEmailProcess)
        informal_emails = self.runner.get(InformalEmailProcess)

        # Get the system running.
        self.runner.start()

        # Both follower apps are unaware of the leader events.
        self.assertEqual(formal_emails.recorder.max_tracking_id("BankAccounts"), 0)
        self.assertEqual(informal_emails.recorder.max_tracking_id("BankAccounts"), 0)

        call_command("sync_followers", "FormalEmailProcess", verbosity=2)

        # One follower app has been synced.
        self.assertEqual(
            formal_emails.recorder.max_tracking_id("BankAccounts"),
            leader_notification_id,
        )
        # While the other remains unaware.
        self.assertEqual(informal_emails.recorder.max_tracking_id("BankAccounts"), 0)

    def test_dry_run_sync_one_app(self) -> None:
        self._create_leader_events()
        formal_emails = self.runner.get(FormalEmailProcess)
        informal_emails = self.runner.get(InformalEmailProcess)

        # Get the system running.
        self.runner.start()

        # Both follower apps are unaware of the leader events.
        self.assertEqual(formal_emails.recorder.max_tracking_id("BankAccounts"), 0)
        self.assertEqual(informal_emails.recorder.max_tracking_id("BankAccounts"), 0)

        call_command("sync_followers", "FormalEmailProcess", verbosity=2, dry_run=True)

        # Neither of the follower apps have been synced.
        self.assertEqual(formal_emails.recorder.max_tracking_id("BankAccounts"), 0)
        self.assertEqual(informal_emails.recorder.max_tracking_id("BankAccounts"), 0)

    def test_sync_all_apps(self) -> None:
        leader_notification_id = self._create_leader_events()
        formal_emails = self.runner.get(FormalEmailProcess)
        informal_emails = self.runner.get(InformalEmailProcess)

        # Get the system running.
        self.runner.start()

        # Both follower apps are unaware of the leader events.
        self.assertEqual(formal_emails.recorder.max_tracking_id("BankAccounts"), 0)
        self.assertEqual(informal_emails.recorder.max_tracking_id("BankAccounts"), 0)

        call_command("sync_followers", verbosity=2)

        # Both follower apps have been synced.
        self.assertEqual(
            formal_emails.recorder.max_tracking_id("BankAccounts"),
            leader_notification_id,
        )
        self.assertEqual(
            informal_emails.recorder.max_tracking_id("BankAccounts"),
            leader_notification_id,
        )

    def test_dry_run_sync_all_apps(self) -> None:
        self._create_leader_events()
        formal_emails = self.runner.get(FormalEmailProcess)
        informal_emails = self.runner.get(InformalEmailProcess)

        # Get the system running.
        self.runner.start()

        # Both follower apps are unaware of the leader events.
        self.assertEqual(formal_emails.recorder.max_tracking_id("BankAccounts"), 0)
        self.assertEqual(informal_emails.recorder.max_tracking_id("BankAccounts"), 0)

        call_command("sync_followers", verbosity=2, dry_run=True)

        # Neither of the follower apps have been synced.
        self.assertEqual(formal_emails.recorder.max_tracking_id("BankAccounts"), 0)
        self.assertEqual(informal_emails.recorder.max_tracking_id("BankAccounts"), 0)


@override_settings(EVENTSOURCING_RUNNER="eventsourcing_runner_django.es_runner")
class TestWithAppAttribute(TestSyncCommand):
    pass


@override_settings(EVENTSOURCING_RUNNER="tests.djangoproject.runner_utils.get_runner")
class TestWithGetterFunction(TestSyncCommand):
    pass


class TestWithSQLiteFileDb(TestSyncCommand):
    django_db_alias = "sqlite_filedb"
    databases = {"default", "sqlite_filedb"}


class TestWithPostgres(TestSyncCommand):
    django_db_alias = "postgres"
    databases = {"default", "postgres"}


class TestDefaultBehaviourWithNewSingleThreadedRunner(TestSyncCommand):
    def setUp(self) -> None:
        runner_django_app = apps.get_app_config("eventsourcing_runner_django")
        self.runner = runner_django_app.make_runner(
            eventsourcing.system.NewSingleThreadedRunner
        )


class TestDefaultBehaviourWithMultiThreadedRunner(TestSyncCommand):
    def setUp(self) -> None:
        runner_django_app = apps.get_app_config("eventsourcing_runner_django")
        self.runner = runner_django_app.make_runner(
            eventsourcing.system.MultiThreadedRunner
        )


class TestDefaultBehaviourWithNewMultiThreadedRunner(TestSyncCommand):
    def setUp(self) -> None:
        runner_django_app = apps.get_app_config("eventsourcing_runner_django")
        self.runner = runner_django_app.make_runner(
            eventsourcing.system.NewMultiThreadedRunner
        )


@modify_settings(
    INSTALLED_APPS={
        "append": (
            "tests.extra_eventsourcing_runner.apps.ExtraEventSourcingSystemRunnerConfig"
        )
    }
)
class TestDefaultBehaviourWithTwoRunners(DjangoTestCase):
    """The default configuration does not handle multiple runners."""

    def test_cannot_sync_all_apps(self) -> None:
        with self.assertRaisesMessage(
            ValueError, "Found more than one (2) runner in Django apps."
        ):
            call_command("sync_followers", verbosity=2)

    def test_cannot_dry_run_sync_all_apps(self) -> None:
        with self.assertRaisesMessage(
            ValueError, "Found more than one (2) runner in Django apps."
        ):
            call_command("sync_followers", dry_run=True, verbosity=2)

    def test_cannot_sync_one_app(self) -> None:
        with self.assertRaisesMessage(
            ValueError, "Found more than one (2) runner in Django apps."
        ):
            call_command("sync_followers", "FormalEmailProcess", verbosity=2)

    def test_cannot_dry_run_sync_one_app(self) -> None:
        with self.assertRaisesMessage(
            ValueError, "Found more than one (2) runner in Django apps."
        ):
            call_command(
                "sync_followers", "FormalEmailProcess", dry_run=True, verbosity=2
            )


class WithTwoRunnersMixin:
    runner: eventsourcing.system.Runner

    def setUp(self) -> None:
        runner_django_app = apps.get_app_config("extra_eventsourcing_runner")
        self.runner = runner_django_app.make_runner()

    def test_get_eventsourcing_runner(self) -> None:
        sync_followers = load_sync_followers_module()

        runner = sync_followers.get_eventsourcing_runner()
        self.assertIs(runner, self.runner)  # type: ignore[attr-defined]


@modify_settings(
    INSTALLED_APPS={
        "append": (
            "tests.extra_eventsourcing_runner.apps.ExtraEventSourcingSystemRunnerConfig"
        )
    }
)
@override_settings(EVENTSOURCING_RUNNER="extra_eventsourcing_runner.the_runner")
class TestWithAppAttributeAndTwoRunners(WithTwoRunnersMixin, TestSyncCommand):
    pass


@modify_settings(
    INSTALLED_APPS={
        "append": (
            "tests.extra_eventsourcing_runner.apps.ExtraEventSourcingSystemRunnerConfig"
        )
    }
)
@override_settings(
    EVENTSOURCING_RUNNER="tests.djangoproject.runner_utils.get_extra_runner"
)
class TestWithGetterFunctionAndTwoRunners(WithTwoRunnersMixin, TestSyncCommand):
    pass
