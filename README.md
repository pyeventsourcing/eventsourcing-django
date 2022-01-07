# Event Sourcing with Django

This package supports using the Python
[eventsourcing](https://github.com/pyeventsourcing/eventsourcing) library
with [Django ORM](https://www.djangoproject.com/).

To use SQLAlchemy with your Python eventsourcing applications:
* install the Python package `eventsourcing_django`
* add `'eventsourcing_django'` to your Django project's `INSTALLED_APPS` setting
* migrate your database for this Django app
* set the environment variable `PERSISTENCE_MODULE` to `'eventsourcing_django'`

See below for more information.


## Installation

Use pip to install the [stable distribution](https://pypi.org/project/eventsourcing_django/)
from the Python Package Index. Please note, it is recommended to
install Python packages into a Python virtual environment.

    $ pip install eventsourcing_django


## Configuration

If you are using Django 2.2, 3.0 or 3.1, please add
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

Define aggregates and applications in the usual way.

```python
from eventsourcing.application import Application
from eventsourcing.domain import Aggregate, event
from uuid import uuid5, NAMESPACE_URL


class TrainingSchool(Application):
    def register(self, name):
        dog = Dog(name)
        self.save(dog)

    def add_trick(self, name, trick):
        dog = self.repository.get(Dog.create_id(name))
        dog.add_trick(trick)
        self.save(dog)

    def get_tricks(self, name):
        dog = self.repository.get(Dog.create_id(name))
        return dog.tricks


class Dog(Aggregate):
    @event('Registered')
    def __init__(self, name):
        self.name = name
        self.tricks = []

    @staticmethod
    def create_id(name):
        return uuid5(NAMESPACE_URL, f'/dogs/{name}')

    @event('TrickAdded')
    def add_trick(self, trick):
        self.tricks.append(trick)
```



When using this module, you need to set the environment variable `SQLALCHEMY_URL` to an
SQLAlchemy database URL for your database.
Please refer to the [SQLAlchemy documentation](https://docs.sqlalchemy.org/en/14/core/engines.html)
for more information about SQLAlchemy Database URLs.

## Initialize application object

To use this module as the persistence module for your event-sourced application, set
the environment variable `PERSISTENCE_MODULE` to `'eventsourcing_django'`.

```python
school = TrainingSchool(env={
    "PERSISTENCE_MODULE": "eventsourcing_django",
})
```

You may wish to construct the application object on a signal
when the Django project is "ready". You can use the `ready()`
method of the `AppConfig` class in the `apps.py` module of a
Django app.


## Django views and forms

The application's methods may be called from Django views and forms.

```python
school.register('Fido')
school.add_trick('Fido', 'roll over')
school.add_trick('Fido', 'play dead')
tricks = school.get_tricks('Fido')
assert tricks == ['roll over', 'play dead']
```

For more information, please refer to the Python
[eventsourcing](https://github.com/johnbywater/eventsourcing) library
and the [Django](https://www.djangoproject.com/) project.
