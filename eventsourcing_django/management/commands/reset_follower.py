# -*- coding: utf-8 -*-
import argparse
import contextlib
from typing import Any, Dict, List

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from eventsourcing_django.models import NotificationTrackingRecord

App = str
UpstreamApps = List[App]


def reset_follower(follower: App, upstream_apps: UpstreamApps) -> int:
    """Reset the tracking states of a follower."""
    count, _ = NotificationTrackingRecord.objects.filter(
        application_name=follower, upstream_application_name__in=upstream_apps
    ).delete()
    return count


def list_stateful_followers() -> Dict[App, UpstreamApps]:
    """List the known stateful followers."""
    followers_and_state: Dict[App, UpstreamApps] = {}
    for app_name, upstream_app_name in (
        NotificationTrackingRecord.objects.values_list(
            "application_name", "upstream_application_name"
        )
        .order_by("application_name", "upstream_application_name")
        .distinct()
    ):
        followers_and_state.setdefault(app_name, [])
        followers_and_state[app_name].append(upstream_app_name)
    return followers_and_state


def select_upstream_apps(
    follower: str,
    upstream_apps: UpstreamApps,
    stateful_followers: Dict[App, UpstreamApps],
) -> UpstreamApps:
    """Validate a request to reset a follower tracking states of upstream apps."""
    requested_apps = set(upstream_apps)
    apps_available = set(stateful_followers[follower])
    unknown_upstreams = requested_apps - apps_available

    if unknown_upstreams:
        if len(unknown_upstreams) == 1:
            app = next(iter(unknown_upstreams))
            error_msg = f"{follower} does not (currently) track {app}."
        else:
            error_msg = (
                f"{follower} does not (currently) track: "
                f"{', '.join(sorted(unknown_upstreams))}."
            )
        error_msg += (
            f" Its known upstream apps are: {', '.join(sorted(apps_available))}."
        )
        raise CommandError(error_msg)

    return sorted(requested_apps) or sorted(apps_available)


class DryRun(Exception):
    pass


class Command(BaseCommand):
    """The Follower app tracking states reset command."""

    is_printing: bool
    is_verbose: bool
    is_dry_run: bool
    has_failures: bool

    help = "Reset the tracking states of a follower app."

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "follower",
            nargs="?",
            help=(
                "The follower's application name to reset the tracking states of. Leave"
                " empty (the default) to list all known followers with tracking states."
            ),
        )
        parser.add_argument(
            "-n",
            "--dry-run",
            action="store_true",
            default=False,
            help="Reset the tracking states, and then roll back the changes.",
        )
        parser.add_argument(
            "-u",
            "--upstream-apps",
            nargs="+",
            help=(
                "The upstream apps to reset the tracking state of. Defaults (empty "
                "list) to reset the tracking states of all upstream apps."
            ),
        )

    def handle(self, follower: str, **options: Any) -> None:
        self.is_printing = options["verbosity"] > 0
        self.is_verbose = options["verbosity"] > 1
        self.is_dry_run = options["dry_run"]
        self.has_failures = False

        stateful_followers = list_stateful_followers()

        if not follower:
            self._print_followers_list(stateful_followers)
            return
        if follower not in stateful_followers.keys():
            raise CommandError(
                f"Unknown follower: {follower}. The known followers are:"
                f" {', '.join(sorted(stateful_followers.keys()))}."
            )
        upstream_apps = select_upstream_apps(
            follower, options["upstream_apps"] or [], stateful_followers
        )
        self._print_header(follower, upstream_apps)

        # TODO: support existing `recorder.using`
        with contextlib.suppress(DryRun), transaction.atomic():
            overall_notifications_count = reset_follower(follower, upstream_apps)
            if self.is_dry_run:
                # Raise an uncaught exception to abort the transaction.
                raise DryRun
        self._print_reset_success(upstream_apps, overall_notifications_count)

    def _print_followers_list(
        self, stateful_followers: Dict[App, UpstreamApps]
    ) -> None:
        if not self.is_printing:
            return

        self.stdout.write("No follower selected. Do you need a hint?")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "Known followers which tracking states that can be reset:"
            )
        )

        for follower, upstream_apps in stateful_followers.items():
            upstream_apps_count = len(upstream_apps)
            self.stdout.write(
                f"\t- {self.style.MIGRATE_LABEL(follower)}, tracking "
                f"{upstream_apps_count} upstream "
                f"application{'' if upstream_apps_count == 1 else 's'}"
            )

    def _print_header(self, follower: App, upstream_apps: UpstreamApps) -> None:
        if not self.is_printing:
            return

        if self.is_dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "Dry-run mode, the tracking states will be reset and "
                    "the changes rolled back."
                )
            )

        if self.is_verbose:
            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    f"The following tracking states of {follower} will be reset:"
                )
            )
            for upstream_app in upstream_apps:
                self.stdout.write(f"\t- {self.style.MIGRATE_LABEL(upstream_app)}")
        else:
            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    f"The tracking states of {follower} will be reset ("
                    + self.style.MIGRATE_LABEL(f"{len(upstream_apps)} upstream apps")
                    + ")."
                )
            )

    def _print_reset_success(
        self, upstream_apps: UpstreamApps, overall_reset_count: int
    ) -> None:
        if not self.is_printing:
            return

        total_upstream_apps_reset = len(upstream_apps)
        extra_msg = (
            (
                " (for a total of 1 notification)"
                if overall_reset_count == 1
                else f" (for a total of {overall_reset_count} notifications)"
            )
            if self.is_verbose
            else ""
        )
        if self.is_dry_run:
            upstream_apps_msg = (
                "1 upstream app"
                if total_upstream_apps_reset == 1
                else f"{total_upstream_apps_reset} upstream apps"
            )
            success_msg = self.style.WARNING(
                f"{upstream_apps_msg} would have been un-tracked{extra_msg} (dry-run)."
            )
        else:
            upstream_apps_msg = (
                "1 upstream app has"
                if total_upstream_apps_reset == 1
                else f"{total_upstream_apps_reset} upstream apps have"
            )
            success_msg = self.style.SUCCESS(
                f"{upstream_apps_msg} been un-tracked{extra_msg}."
            )
        self.stdout.write(success_msg)
