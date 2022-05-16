# -*- coding: utf-8 -*-
from __future__ import annotations

import os

import eventsourcing.system
import pytest
from django.apps.registry import apps
from django.core.management import call_command
from django.test import TransactionTestCase
from eventsourcing.tests.application import BankAccounts

from tests.emails.application import FormalEmailProcess, InformalEmailProcess


class TestSyncCommand(TransactionTestCase):
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


class TestWithSQLiteFileDb(TestSyncCommand):
    django_db_alias = "sqlite_filedb"
    databases = {"default", "sqlite_filedb"}

    @pytest.mark.xfail(reason="Transaction not rolled back?")
    def test_dry_run_sync_one_app(self) -> None:
        super().test_dry_run_sync_one_app()

    @pytest.mark.xfail(reason="Transaction not rolled back?")
    def test_dry_run_sync_all_apps(self) -> None:
        super().test_dry_run_sync_all_apps()


class TestWithPostgres(TestSyncCommand):
    django_db_alias = "postgres"
    databases = {"default", "postgres"}

    @pytest.mark.xfail(reason="Transaction not rolled back?")
    def test_dry_run_sync_one_app(self) -> None:
        super().test_dry_run_sync_one_app()

    @pytest.mark.xfail(reason="Transaction not rolled back?")
    def test_dry_run_sync_all_apps(self) -> None:
        super().test_dry_run_sync_all_apps()
