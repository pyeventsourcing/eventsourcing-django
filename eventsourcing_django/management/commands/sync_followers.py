# -*- coding: utf-8 -*-
import argparse
from collections import defaultdict
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Tuple,
    TypeVar,
    cast,
)

import eventsourcing.system
from django.apps.config import AppConfig
from django.apps.registry import apps
from django.conf import settings
from django.core.exceptions import (
    EmptyResultSet,
    FieldDoesNotExist,
    FieldError,
    MultipleObjectsReturned,
    ObjectDoesNotExist,
)
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from eventsourcing.application import Application
from eventsourcing.domain import EventSourcingError
from eventsourcing.system import Follower, Runner, System

from eventsourcing_django.recorders import DjangoAggregateRecorder

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


def get_eventsourcing_runner() -> Runner:
    """Get the instance of a :class:`~eventsourcing.system.Runner` to run against.

    Try to load the `EVENTSOURCING_RUNNER` Django setting first.
    Fallback to finding a sole runner instance in the installed apps
    with :func:`find_eventsourcing_runner` otherwise.
    """
    try:
        app_attribute_or_function_qualified_name: str = settings.EVENTSOURCING_RUNNER
    except AttributeError:
        return find_eventsourcing_runner()

    path_or_app_name, name = app_attribute_or_function_qualified_name.rsplit(".", 1)

    try:
        app_config = apps.get_app_config(path_or_app_name)
    except LookupError:
        import importlib

        module = importlib.import_module(path_or_app_name)
        get_runner = getattr(module, name, None)
        runner = get_runner() if get_runner is not None else None
    else:
        runner = getattr(app_config, name, None)

    if runner is None or not isinstance(runner, eventsourcing.system.Runner):
        raise ValueError(
            "The Django setting `EVENTSOURCING_RUNNER` is improperly set. Use an"
            " app name with attribute (e.g. `my_event_sourced_app.runner`) or a"
            " function which returns a runner instance (e.g."
            " `djangoproject.runner_utils.get_runner`)."
        )

    return runner


def find_eventsourcing_runner() -> Runner:
    """Find an instance of a :class:`~eventsourcing.system.Runner` in Django apps.

    There must be only one Django app exposing a single
    :class:`~eventsourcing.system.Runner` instance as attribute.

    :raise ValueError: If zero or more than one runner were found.
    """
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


class DryRun(Exception):
    pass


class Command(BaseCommand):
    """The Follower apps synchronization command."""

    is_printing: bool
    is_verbose: bool
    is_dry_run: bool
    has_failures: bool

    help = "Synchronize follower apps with unseen events from their leader apps."

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "args",
            metavar="follower",
            nargs="*",
            help="The followers to synchronize. Defaults to synchronize all followers.",
        )
        parser.add_argument(
            "-n",
            "--dry-run",
            action="store_true",
            default=False,
            help=(
                "Load and process all unseen events for the selected followers, but"
                " roll back all changes at the end."
            ),
        )

    def handle(self, *followers: str, **options: Any) -> None:
        self.is_printing = options["verbosity"] > 0
        self.is_verbose = options["verbosity"] > 1
        self.is_dry_run = options["dry_run"]
        self.has_failures = False

        runner: Runner = get_eventsourcing_runner()
        system: System = runner.system

        selection, is_complete_selection = select_followers(system.followers, followers)
        followers_count = len(selection)
        self._print_header(followers_count, is_complete_selection)
        _print_app_label = self._make_print_app_label(followers_count)

        follower_apps_by_alias: Dict[
            Optional[str], List[Tuple[int, Follower]]
        ] = defaultdict(list)

        for position, follower in enumerate(selection, start=1):
            follower_app = cast(Follower, runner.get(system.get_app_cls(follower)))
            recorder = cast(DjangoAggregateRecorder, follower_app.recorder)
            alias = recorder.using
            follower_apps_by_alias[alias].append((position, follower_app))

        for alias, follower_apps in follower_apps_by_alias.items():
            try:
                with transaction.atomic(using=alias):
                    for position, follower_app in follower_apps:
                        _print_app_label(position, follower_app.name)
                        try:
                            events_count = sync_follower_with_leaders(
                                follower_app, system.follows[follower_app.name]
                            )
                        except (
                            EmptyResultSet,
                            EventSourcingError,
                            FieldDoesNotExist,
                            FieldError,
                            MultipleObjectsReturned,
                            ObjectDoesNotExist,
                        ) as error:
                            self._print_sync_failure(error)
                        else:
                            self._print_sync_success(events_count)

                    if self.is_dry_run:
                        raise DryRun
            except DryRun:
                pass

        if self.is_printing and self.has_failures and not self.is_verbose:
            self.stderr.write(
                "There were errors during synchronisation, please re-run with a higher"
                " verbosity level (try: `--verbosity 2`)."
            )

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

    def _print_sync_failure(self, error: EventSourcingError) -> None:
        self.has_failures = True

        if not self.is_printing:
            return

        if self.is_dry_run:
            failure_msg = self.style.WARNING("FAILED (dry-run)")
        else:
            failure_msg = self.style.ERROR("FAILED")
        self.stdout.write(failure_msg)

        if self.is_verbose:
            error_name = error.__class__.__name__
            error_msg = str(error)
            display_msg = f": {error_msg}" if error_msg else "."
            self.stderr.write(f"\tCaught a {error_name}{display_msg}")
