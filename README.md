# Event Sourcing with Django

This package is a Django app that uses the
[Django ORM](https://www.djangoproject.com/)
as persistence infrastructure for the
[Python eventsourcing library](https://github.com/johnbywater/eventsourcing).


## Install package

You can use pip to install the [stable distribution](https://pypi.org/project/eventsourcing_django/)
from the Python Package Index. Please note, it is recommended to
install Python packages into a Python virtual environment.

    $ pip install eventsourcing_django


## Event-sourced model and application

You can define an event-sourced domain model and application
methods independently of persistence infrastructure.

```python
from eventsourcing.application import Application
from eventsourcing.domain import Aggregate, event


class World(Aggregate):
    def __init__(self):
        self.history = []

    @event("SomethingHappened")
    def make_it_so(self, what):
        self.history.append(what)


class Worlds(Application):
    snapshotting_intervals = {
        World: 5,  # automatic snapshotting
    }

    def create_world(self):
        world = World()
        self.save(world)
        return world.id

    def make_it_so(self, world_id, what):
        world = self.repository.get(world_id)
        world.make_it_so(what)
        self.save(world)

    def get_world_history(self, world_id):
        world = self.repository.get(world_id)
        return world.history
```

Please refer to the [core library docs](https://eventsourcing.readthedocs.io/)
for more information.


## Migrate Django database

Include `eventsourcing_django` in the `INSTALLED_APPS` list in
your Django project's `settings.py` file.

    INSTALLED_APPS = [
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.messages",
        "django.contrib.staticfiles",
        "eventsourcing_django",
    ]


Setup Django and run migrations in the usual way, setting
`DJANGO_SETTINGS_MODULE` and running the `migrate` command.

In this example, we use the [example Django project](https://github.com/pyeventsourcing/eventsourcing-django/tree/main/tests/djangoproject)
in this package's repository.

```python
import os

import django
from django.core.management import call_command


# Set DJANGO_SETTINGS_MODULE.
os.environ.update({
    "DJANGO_SETTINGS_MODULE": "tests.djangoproject.settings",
})

# Setup Django.
django.setup()

# Setup the database.
call_command('migrate', 'eventsourcing_django')
```

## Construct application object

Construct your event sourced application object. You may wish
to do this within a Django app in your Django project.

You may wish to construct the application object on a signal
when the project is ready. Use the ready() method of the AppConfig
class in your Django app's apps.py module.

To use the Django ORM as the application's persistence infrastructure,
set the application's environment variable `INFRASTRUCTURE_FACTORY`
to `eventsourcing_django.factory:Factory`. Environment variables
can be set in the environment, or set on the application class, or
passed in when constructing the application object.

The application can use other environment variables supported by
the library, for example to enable application-level compression
of stored events, set `COMPRESSOR_TOPIC`.

You may also wish to arrange for settings to be defined in
and used from your Django project's `settings.py`.

```python
# Construct the application.
app = Worlds(env={
    "INFRASTRUCTURE_FACTORY": "eventsourcing_django.factory:Factory",
    "COMPRESSOR_TOPIC": "zlib",
})
```

# Call application methods

The application command and query methods may be called from Django
view and form classes.

```python

# Call application command methods.
world_id = app.create_world()

app.make_it_so(world_id, "dinosaurs")
app.make_it_so(world_id, "trucks")
app.make_it_so(world_id, "internet")
app.make_it_so(world_id, "covid")

# Call application query methods.
history = app.get_world_history(world_id)
assert history == ["dinosaurs", "trucks", "internet", "covid"]
```

# Is it working?

We can see the application is using the Django ORM infrastructure,
and that snapshotting and compression are enabled, by checking the
attributes of the application object.

```python
from eventsourcing_django.factory import Factory
from eventsourcing_django.recorders import DjangoAggregateRecorder
from eventsourcing_django.recorders import DjangoApplicationRecorder
from eventsourcing_django.models import StoredEventRecord
from eventsourcing_django.models import SnapshotRecord
import zlib

assert isinstance(app.factory, Factory)
assert isinstance(app.events.recorder, DjangoApplicationRecorder)
assert isinstance(app.snapshots.recorder, DjangoAggregateRecorder)
assert issubclass(app.events.recorder.model, StoredEventRecord)
assert issubclass(app.snapshots.recorder.model, SnapshotRecord)
assert app.mapper.compressor == zlib
```

We can see the automatic snapshotting is working, by looking
in the snapshots store.

```python
snapshots = list(app.snapshots.get(world_id))
assert len(snapshots) == 1
```

For more information, please refer to the Python
[eventsourcing](https://github.com/johnbywater/eventsourcing) library
and the [Django](https://www.djangoproject.com/) project.
