# Event Sourcing with Django

The Python package `eventsourcing-django` provides a Django app
that uses the [Django ORM](https://www.djangoproject.com/)
to define alternative persistence infrastructure for the
[Python eventsourcing library](https://github.com/pyeventsourcing/eventsourcing).
This package is [available on PyPI](https://pypi.org/project/eventsourcing-django/).

This package is designed and tested to work with version 9.1 of
the Python eventsourcing library, Django versions 3.0, 3.1, and
3.2, and Python versions 3.7, 3.8, 3.9, and 3.10.

The functionality provided by this package was previously included
in the Python eventsourcing package, but was moved out to a separate
package during development of version 9.

This is package is maintained by the Python eventsourcing project.
Please [raise issues on GitHub](https://github.com/pyeventsourcing/eventsourcing-django/issues)
and [join the community](https://join.slack.com/t/eventsourcinginpython/shared_invite/enQtMjczNTc2MzcxNDI0LTJjMmJjYTc3ODQ3M2YwOTMwMDJlODJkMjk3ZmE1MGYyZDM4MjIxODZmYmVkZmJkODRhZDg5N2MwZjk1YzU3NmY)
discussion on Slack.


## Installation

You can use `pip` to install the package. It is recommended to install
Python packages into a Python virtual environment.

    $ pip install eventsourcing-django


## Configuration

If you are using Django 3.0 or 3.1, please add
`'eventsourcing_django.apps.EventsourcingConfig'` to your Django
project's `INSTALLED_APPS` setting.

    INSTALLED_APPS = [
        ...
        'eventsourcing_django.apps.EventsourcingConfig',
    ]


If you are using Django 3.2 or later, you only need to add `'eventsourcing_django'`
to your Django project's `INSTALLED_APPS` setting, although the above will work also.

    INSTALLED_APPS = [
        ...
        'eventsourcing_django',
    ]


## Database migration

To migrate your database, please run Django's `manage.py migrate` command.

    $ python manage.py migrate eventsourcing_django


## Event-sourced aggregates and application

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

```python
from eventsourcing.application import Application

class Universe(Application):
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


## Initialize application object

The application object brings together the domain model and the
persistence infrastructure, and provides an interface for views
and forms.

To use the Django ORM as the application's persistence infrastructure,
you must set the application's environment variable
`INFRASTRUCTURE_FACTORY` to `eventsourcing_django.factory:Factory`.
Environment variables can be set in the environment, or set on the
application class, or passed in when constructing the application
object as seen below.

```python
# Construct the application.
app = Universe(env={
    "INFRASTRUCTURE_FACTORY": "eventsourcing_django.factory:Factory",
})
```

You may wish to construct the application object on a signal
when the Django project is "ready". You can use the `ready()`
method of the `AppConfig` class in the `apps.py` module of a
Django app.


## Views and forms

After migrating the database and constructing the application object,
the application object's methods can be called. The application object's
methods may be called from Django views and forms.

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

For more information, please refer to the Python
[eventsourcing](https://github.com/johnbywater/eventsourcing) library
and the [Django](https://www.djangoproject.com/) project.
