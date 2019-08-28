===============
masakari-manage
===============

-------------------------------------
Control and manage masakari database
-------------------------------------

Synopsis
========

::

  masakari-manage <category> <action> [<args>]

Description
===========

:program:`masakari-manage` controls DB by managing various admin-only aspects
of masakari.

Options
=======

The standard pattern for executing a masakari-manage command is::

  masakari-manage <category> <command> [<args>]

Run without arguments to see a list of available command categories::

  masakari-manage

You can also run with a category argument such as db to see a list of all
commands in that category::

  masakari-manage db

These sections describe the available categories and arguments for masakari-manage.

Masakari Database
~~~~~~~~~~~~~~~~~

``masakari-manage db version``
    Print the current main database version.

``masakari-manage db sync [--version <version>]``
    Upgrade the main database schema up to the most recent version or
    ``--version`` if specified.

``masakari-manage db purge``
    Deleting rows older than 30 day(s) from table hosts, failover_segments and
    notifications.
