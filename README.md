# Event Sourcing with Django

This package is a Django app that uses the
[Django ORM](https://www.djangoproject.com/)
as persistence infrastructure for the
[Python eventsourcing library](https://github.com/johnbywater/eventsourcing).


## Installation

Install using `pip`. It is recommended to install Python
packages into a Python virtual environment.

    $ pip install eventsourcing_django


Add `'eventsourcing_django'` to your Django project's `INSTALLED_APPS` setting.

    INSTALLED_APPS = [
        ...
        'eventsourcing_django',
    ]


## Applications and aggregates

You can develop event-sourced aggregates and applications
independently of persistence infrastructure. Please refer
to the [core library docs](https://eventsourcing.readthedocs.io/)
for more information.

The example below defines an event-sourced aggregate `World`. It
will be created with a `history` attribute. The command method
`make_it_so()` triggers an event `SomethingHappened`
that appends the command argument `what` to the `history`.

```python
from eventsourcing.domain import Aggregate, event


class World(Aggregate):
    def __init__(self):
        self.history = []

    @event("SomethingHappened")
    def make_it_so(self, what):
        self.history.append(what)
```

The application class `Universe` has three methods. The method `create_world()`
creates a new `World` aggregate. The method `make_it_so()` calls `make_it_so()`
on an existing `World` aggregate. The method `get_world_history()`
returns the current `history` value of an existing `World` aggregate.

Automatic snapshotting is enabled by using the `snapshotting_intervals`
attribute of the application class.

```python
from eventsourcing.application import Application

class Universe(Application):
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


## Database migration

Set `DJANGO_SETTINGS_MODULE` and run Django's `manage.py migrate` command.

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

## Application object

After migrating the database and defining an application, we can
construct the application object. The application object binds
the domain model and the persistence infrastructure, and provides
an interface for views and forms.

To use the Django ORM as the application's persistence infrastructure,
you must set the application's environment variable
`INFRASTRUCTURE_FACTORY` to `eventsourcing_django.factory:Factory`.
Environment variables can be set in the environment, or set on the
application class, or passed in when constructing the application
object as seen below.

You may wish to construct the application object on a signal
when the Django project is "ready". You can use the `ready()`
method of the `AppConfig` class in the `apps.py` module of a
Django app.

The application can use other environment variables supported by
the library, for example to enable application-level compression
of stored events, set `COMPRESSOR_TOPIC`. You may wish to
arrange for settings to be defined in and used from your Django
project's `settings.py`.

```python
# Construct the application.
app = Universe(env={
    "INFRASTRUCTURE_FACTORY": "eventsourcing_django.factory:Factory",
    "COMPRESSOR_TOPIC": "zlib",
})
```

# Views and forms

After migrating the database and constructing the application object,
the application object's methods can be called. The application object's
methods may be called from Django view and form classes.

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

We can see automatic snapshotting is working, by looking
in the snapshots store.

```python
snapshots = list(app.snapshots.get(world_id))
assert len(snapshots) == 1
```

For more information, please refer to the Python
[eventsourcing](https://github.com/johnbywater/eventsourcing) library
and the [Django](https://www.djangoproject.com/) project.
