==============
Django Extents
==============

The Django Extents is a safe way to declaratively extend any model beyond your
application. Possible conflicts are resolved automatically by adding the
app_label prefix to each contributed field or method name.

Currently Django Extents provides the following features:

- Declarative way of extending of a foreign app's models (using monkey patching
  technique under the hood)

- Using your Extent subclass instead of the original model's one, including
  all (I hope) of the django ORM features without specifying any prefixes
  (Extents take care of them on any underlying layer).

- Registering extent model in django-admin, implemented just for the sake of
  compatibility (the original model should be unregistered first)

In general, Extent subclasses try to look and act just like normal django
models.

Installation
============

#. Add the `django_extents` directory to your Python path.

Running tests
=============

#. Enable the `django_extents` application in your project's `settings.py` file
#. Run `./manage.py test django_extents` command in project root directory

Code samples
============

For code samples see tests sources.

TODOs and BUGS
==============
See: http://github.com/TrashNRoll/django-extents/issues
