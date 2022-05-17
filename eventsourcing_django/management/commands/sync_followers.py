# -*- coding: utf-8 -*-
import argparse
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    Tuple,
    Type,
    TypeVar,
    cast,
)

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from eventsourcing.application import Application
from eventsourcing.system import Follower, Runner, System

TApplication = TypeVar("TApplication", bound=Application)


def sync_follower_with_leaders(
    follower: Follower, leader_names: Iterable[str]
) -> Dict[str, int]:
    """Synchronize a follower with its leader apps."""
    events_counter = {}

    for leader_name in leader_names:
        # The library isn't telling us how many events it actually processed,
        # so we first do a dry-run selection of all new notifications.
        events_counter[leader_name] = 0
        start = follower.recorder.max_tracking_id(leader_name) + 1
        for batch in follower.pull_notifications(leader_name, start):
            events_counter[leader_name] += len(batch)

        follower.pull_and_process(leader_name, start)

    return events_counter


def discover_followers() -> Dict[str, Type[TApplication]]:
    """Get all followers in the system."""
    return {}  # TODO


def find_eventsourcing_runner() -> Runner:
    """Find an instance of a :class:`~eventsourcing.system.Runner` in Django apps.

    There must be only one Django app exposing a single
    :class:`~eventsourcing.system.Runner` instance as attribute.

    :raise ValueError: If zero or more than one runner were found.
    """
    from django.apps.config import AppConfig
    from django.apps.registry import apps

    runners: List[Runner] = []

    for app_config in apps.get_app_configs():
        assert isinstance(app_config, AppConfig)
        runners.extend(
            getattr(app_config, attr)
            for attr in dir(app_config)
            if not attr.startswith("_")
            and isinstance(getattr(app_config, attr), Runner)
        )

    if not runners:
        raise ValueError("No runner found in Django apps.")
    if len(runners) > 1:
        raise ValueError(f"Found more than one ({len(runners)}) runner in Django apps.")

    return runners[0]


def select_followers(
    all_followers: List[str], requested: Iterable[str]
) -> Tuple[List[str], bool]:
    """Select followers based on a requested selection.

    An empty or undefined request translates to a complete selection.
    """
    requested_followers = list(requested)

    if not requested_followers:
        return all_followers, True

    unknown_followers = set(requested_followers) - set(all_followers)
    if unknown_followers:
        raise CommandError(
            f"Unknown followers selected: {', '.join(unknown_followers)}. "
            f"The known followers are: {', '.join(all_followers)}."
        )

    return requested_followers, len(requested_followers) == len(all_followers)


class Command(BaseCommand):
    """The Follower apps synchronization command."""

    is_printing: bool
    is_verbose: bool
    is_dry_run: bool

    help = "Synchronize follower apps with events from their leader apps."  # noqa

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "args",
            metavar="followers",
            nargs="*",
            help="The followers to synchronize. Defaults to synchronize all followers.",
        )
        parser.add_argument(
            "--dry-run",
            "-n",
            action="store_true",
            default=False,
            help="Dry run, synchronize the followers but do not commit the changes.",
        )

    def handle(self, *followers: str, **options: Any) -> None:
        self.is_printing = options["verbosity"] > 0
        self.is_verbose = options["verbosity"] > 1
        self.is_dry_run = options["dry_run"]

        runner: Runner = find_eventsourcing_runner()
        system: System = runner.system

        selection, is_complete_selection = select_followers(system.followers, followers)
        followers_count = len(selection)
        self._print_header(followers_count, is_complete_selection)
        _print_app_label = self._make_print_app_label(followers_count)

        with transaction.atomic():
            initial_state = transaction.savepoint()

            for position, follower in enumerate(selection, start=1):
                _print_app_label(position, follower)
                follower_app = cast(Follower, runner.get(system.get_app_cls(follower)))
                events_count = sync_follower_with_leaders(
                    follower_app, system.follows[follower]
                )
                self._print_sync_success(events_count)

            if self.is_dry_run:
                transaction.savepoint_rollback(initial_state)

    def _print_header(self, followers_count: int, is_complete_selection: bool) -> None:
        if not self.is_printing:
            return

        if self.is_dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "Dry-run mode, the events will be processed but the "
                    "changes will be rolled back."
                )
            )

        followers_count_msg = (
            "All followers"
            if is_complete_selection
            else f"{followers_count} follower{'' if followers_count == 1 else 's'}"
        )
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"{followers_count_msg} selected for synchronization."
            )
        )

    def _make_print_app_label(self, followers_count: int) -> Callable[[int, str], None]:
        if not self.is_printing:
            return lambda *_: None

        position_format = f"{len(str(followers_count))}d"

        def printer(position: int, follower: str) -> None:
            self.stdout.write(
                f"[{position:{position_format}}/{followers_count}] Synchronizing "
                f"{self.style.MIGRATE_LABEL(follower)}...",
                ending=" ",
            )

        return printer

    def _print_sync_success(self, events_count: Mapping[str, int]) -> None:
        if not self.is_printing:
            return

        if self.is_dry_run:
            success_msg = self.style.WARNING("OK (dry-run)")
        else:
            success_msg = self.style.SUCCESS("OK")
        self.stdout.write(success_msg)

        self._print_sync_success_details(events_count)

    def _print_sync_success_details(self, events_count: Mapping[str, int]) -> None:
        if not self.is_verbose:
            return

        for upstream_app, event_count in events_count.items():
            self.stdout.write(
                f"\t {event_count} event{'' if event_count == 1 else 's'} "
                f"from {upstream_app} processed"
            )