# Event Sourcing in Python with Django

This package is a Django app that supports using the Python
[eventsourcing](https://github.com/johnbywater/eventsourcing) library
with the [Django ORM](https://www.djangoproject.com/).

## Installation

Use pip to install the [stable distribution](https://pypi.org/project/eventsourcing_django/)
from the Python Package Index. Please note, it is recommended to
install Python packages into a Python virtual environment.

    $ pip install eventsourcing_django


## Synopsis

To use Django with your Python eventsourcing application, use the topic `eventsourcing_django.factory:Factory` as the `INFRASTRUCTURE_FACTORY`
environment variable.

First define a domain model and application, in the usual way. You may set the
`INFRASTRUCTURE_FACTORY` environment variable on the application class, so it
can always use the Django ORM for storing events.

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
    env = {
        "INFRASTRUCTURE_FACTORY": "eventsourcing_django.factory:Factory",
        "IS_SNAPSHOTTING_ENABLED": "yes",
    }
    snapshotting_intervals = {
        World: 5,
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

Setup Django, in the usual way.

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

The application's environment can use other environment variables
supported by the library, for example to enable application-level
compression and encryption of stored events, set `COMPRESSOR_TOPIC`
and `CIPHER_KEY`.

```python
from eventsourcing.cipher import AESCipher


# Generate a cipher key (keep this safe).
cipher_key = AESCipher.create_key(num_bytes=32)

# Set environment variables.
os.environ.update({
    "COMPRESSOR_TOPIC": "zlib",
    "CIPHER_KEY": cipher_key,
})
```

Construct and use the application. You may wish to do this
within your Django project. The application can be created
on a signal when the project is ready (use the ready() method
of the AppConfig class in your Django app's apps.py module).
The application command and query methods may be called
from Django view and form classes.

```python
# Construct the application.
app = Worlds()

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

We can see the automatic snapshotting is working, by looking
in the snapshots store.

```python
snapshots = list(app.snapshots.get(world_id))
assert len(snapshots) == 1
```

We can see the application is using the Django infrastructure,
and that compression and encryption are enabled, by checking the
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
assert isinstance(app.mapper.cipher, AESCipher)
assert app.mapper.compressor == zlib
```

For more information, please refer to the Python
[eventsourcing](https://github.com/johnbywater/eventsourcing) library
and the [Django](https://www.djangoproject.com/) project.
