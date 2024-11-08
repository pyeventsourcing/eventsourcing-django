# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib
import os
import types
from io import StringIO
from textwrap import dedent
from uuid import uuid4

from django.core.management import CommandError, call_command
from eventsourcing.persistence import ProcessRecorder, StoredEvent, Tracking

from eventsourcing_django.models import StoredEventRecord
from eventsourcing_django.recorders import DjangoProcessRecorder
from tests.test_recorders import DjangoTestCase


def load_reset_followers_module() -> types.ModuleType:
    return importlib.import_module(
        "eventsourcing_django.management.commands.reset_followers"
    )


class TestResetCommand(DjangoTestCase):
    django_db_alias = "default"
    recorder: ProcessRecorder

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
        self.recorder = DjangoProcessRecorder(
            application_name="Application", model=StoredEventRecord
        )
        other_recorder = DjangoProcessRecorder(
            application_name="AnotherApplication", model=StoredEventRecord
        )

        originator_id1 = uuid4()
        originator_id2 = uuid4()

        originator1_events = [
            StoredEvent(
                originator_id=originator_id1,
                originator_version=1,
                topic="topic1",
                state=b"state1",
            ),
            StoredEvent(
                originator_id=originator_id1,
                originator_version=2,
                topic="topic2",
                state=b"state2",
            ),
        ]
        originator2_events = [
            StoredEvent(
                originator_id=originator_id2,
                originator_version=1,
                topic="topic3",
                state=b"state3",
            ),
            StoredEvent(
                originator_id=originator_id2,
                originator_version=2,
                topic="topic4",
                state=b"state4",
            ),
        ]

        self.recorder.insert_events(
            stored_events=originator1_events,
            tracking=Tracking(
                application_name="upstream_app_1",
                notification_id=1,
            ),
        )
        self.recorder.insert_events(
            stored_events=originator2_events[:1],
            tracking=Tracking(
                application_name="upstream_app_2",
                notification_id=1,
            ),
        )
        self.recorder.insert_events(
            stored_events=originator2_events[1:],
            tracking=Tracking(
                application_name="upstream_app_2",
                notification_id=2,
            ),
        )
        other_recorder.insert_events(
            stored_events=originator2_events,
            tracking=Tracking(
                application_name="upstream_app_2",
                notification_id=2,
            ),
        )

    def test_reset_follower(self) -> None:
        out = StringIO()
        self.assertEqual(self.recorder.max_tracking_id("upstream_app_1"), 1)
        self.assertEqual(self.recorder.max_tracking_id("upstream_app_2"), 2)

        call_command("reset_follower", "Application", no_color=True, stdout=out)

        self.assertEqual(self.recorder.max_tracking_id("upstream_app_1"), 0)
        self.assertEqual(self.recorder.max_tracking_id("upstream_app_2"), 0)
        self.assertEqual(
            out.getvalue(),
            dedent(
                """\
                The tracking states of Application will be reset (2 upstream apps).
                2 upstream apps have been un-tracked.
                """
            ),
        )

    def test_reset_follower_with_upstream(self) -> None:
        out = StringIO()
        self.assertEqual(self.recorder.max_tracking_id("upstream_app_1"), 1)
        self.assertEqual(self.recorder.max_tracking_id("upstream_app_2"), 2)

        call_command(
            "reset_follower",
            "Application",
            upstream_apps=["upstream_app_1"],
            no_color=True,
            stdout=out,
        )

        self.assertEqual(self.recorder.max_tracking_id("upstream_app_1"), 0)
        self.assertEqual(self.recorder.max_tracking_id("upstream_app_2"), 2)
        self.assertEqual(
            out.getvalue(),
            dedent(
                """\
                The tracking states of Application will be reset (1 upstream apps).
                1 upstream app has been un-tracked.
                """
            ),
        )

    def test_reset_follower_very_verbosely(self) -> None:
        out = StringIO()
        self.assertEqual(self.recorder.max_tracking_id("upstream_app_1"), 1)
        self.assertEqual(self.recorder.max_tracking_id("upstream_app_2"), 2)

        call_command(
            "reset_follower", "Application", no_color=True, stdout=out, verbosity=3
        )

        self.assertEqual(self.recorder.max_tracking_id("upstream_app_1"), 0)
        self.assertEqual(self.recorder.max_tracking_id("upstream_app_2"), 0)
        self.assertEqual(
            out.getvalue(),
            dedent(
                """\
                The following tracking states of Application will be reset:
                \t- upstream_app_1
                \t- upstream_app_2
                2 upstream apps have been un-tracked (for a total of 3 notifications).
                """
            ),
        )

    def test_reset_follower_with_upstream_very_verbosely(self) -> None:
        out = StringIO()
        self.assertEqual(self.recorder.max_tracking_id("upstream_app_1"), 1)
        self.assertEqual(self.recorder.max_tracking_id("upstream_app_2"), 2)

        call_command(
            "reset_follower",
            "Application",
            upstream_apps=["upstream_app_1"],
            no_color=True,
            stdout=out,
            verbosity=3,
        )

        self.assertEqual(self.recorder.max_tracking_id("upstream_app_1"), 0)
        self.assertEqual(self.recorder.max_tracking_id("upstream_app_2"), 2)
        self.assertEqual(
            out.getvalue(),
            dedent(
                """\
                The following tracking states of Application will be reset:
                \t- upstream_app_1
                1 upstream app has been un-tracked (for a total of 1 notification).
                """
            ),
        )

    def test_reset_unknown_follower(self) -> None:
        out = StringIO()
        self.assertEqual(self.recorder.max_tracking_id("upstream_app_1"), 1)
        self.assertEqual(self.recorder.max_tracking_id("upstream_app_2"), 2)

        with self.assertRaises(CommandError) as error:
            call_command("reset_follower", "UnknownApp", no_color=True, stdout=out)

        self.assertEqual(self.recorder.max_tracking_id("upstream_app_1"), 1)
        self.assertEqual(self.recorder.max_tracking_id("upstream_app_2"), 2)
        self.assertEqual(
            str(error.exception),
            "Unknown follower: UnknownApp. The known followers are: AnotherApplication,"
            " Application.",
        )

    def test_reset_unknown_upstream_of_follower(self) -> None:
        out = StringIO()
        self.assertEqual(self.recorder.max_tracking_id("upstream_app_1"), 1)
        self.assertEqual(self.recorder.max_tracking_id("upstream_app_2"), 2)

        with self.assertRaises(CommandError) as error:
            call_command(
                "reset_follower",
                "Application",
                upstream_apps=["upstream"],
                no_color=True,
                stdout=out,
            )

        self.assertEqual(self.recorder.max_tracking_id("upstream_app_1"), 1)
        self.assertEqual(self.recorder.max_tracking_id("upstream_app_2"), 2)
        self.assertEqual(
            str(error.exception),
            "Application does not (currently) track upstream. "
            "Its known upstream apps are: upstream_app_1, upstream_app_2.",
        )

    def test_reset_unknown_upstreams_of_follower(self) -> None:
        out = StringIO()
        self.assertEqual(self.recorder.max_tracking_id("upstream_app_1"), 1)
        self.assertEqual(self.recorder.max_tracking_id("upstream_app_2"), 2)

        with self.assertRaises(CommandError) as error:
            call_command(
                "reset_follower",
                "Application",
                upstream_apps=["upstream", "downstream"],
                no_color=True,
                stdout=out,
            )

        self.assertEqual(self.recorder.max_tracking_id("upstream_app_1"), 1)
        self.assertEqual(self.recorder.max_tracking_id("upstream_app_2"), 2)
        self.assertEqual(
            str(error.exception),
            "Application does not (currently) track: downstream, upstream. "
            "Its known upstream apps are: upstream_app_1, upstream_app_2.",
        )

    def test_dry_run_reset_follower(self) -> None:
        out = StringIO()
        self.assertEqual(self.recorder.max_tracking_id("upstream_app_1"), 1)
        self.assertEqual(self.recorder.max_tracking_id("upstream_app_2"), 2)

        call_command(
            "reset_follower", "Application", dry_run=True, no_color=True, stdout=out
        )

        self.assertEqual(self.recorder.max_tracking_id("upstream_app_1"), 1)
        self.assertEqual(self.recorder.max_tracking_id("upstream_app_2"), 2)
        self.assertEqual(
            out.getvalue(),
            dedent(
                """\
                Dry-run mode, the tracking states will be reset and the changes rolled back.
                The tracking states of Application will be reset (2 upstream apps).
                2 upstream apps would have been un-tracked (dry-run).
                """
            ),
        )

    def test_dry_run_reset_follower_very_verbosely(self) -> None:
        out = StringIO()
        self.assertEqual(self.recorder.max_tracking_id("upstream_app_1"), 1)
        self.assertEqual(self.recorder.max_tracking_id("upstream_app_2"), 2)

        call_command(
            "reset_follower",
            "Application",
            dry_run=True,
            no_color=True,
            stdout=out,
            verbosity=3,
        )

        self.assertEqual(self.recorder.max_tracking_id("upstream_app_1"), 1)
        self.assertEqual(self.recorder.max_tracking_id("upstream_app_2"), 2)
        self.assertEqual(
            out.getvalue(),
            dedent(
                """\
                Dry-run mode, the tracking states will be reset and the changes rolled back.
                The following tracking states of Application will be reset:
                \t- upstream_app_1
                \t- upstream_app_2
                2 upstream apps would have been un-tracked (for a total of 3 notifications) (dry-run).
                """  # noqa: B950
            ),
        )

    def test_list_followers(self) -> None:
        out = StringIO()

        call_command("reset_follower", no_color=True, stdout=out)
        value = out.getvalue()
        expected = dedent(
            """\
                No follower selected. Do you need a hint?
                Known followers which tracking states that can be reset:
                \t- AnotherApplication, tracking 1 upstream application
                \t- Application, tracking 2 upstream applications
                """
        )

        assert value == expected


class TestWithSQLiteFileDb(TestResetCommand):
    django_db_alias = "sqlite_filedb"
    databases = {"default", "sqlite_filedb"}


class TestWithPostgres(TestResetCommand):
    django_db_alias = "postgres"
    databases = {"default", "postgres"}
