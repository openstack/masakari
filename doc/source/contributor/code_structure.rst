..
      Copyright 2020 Leafcloud B.V.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

=======================
Masakari Code Structure
=======================

Getting started with any codebase requires some getting used to the layout of the project,
this guide is meant to make your journey navigating the code easier.
All paths are relative to the repository root.

Code layout
===========

The Python source code for the project can be found in
``masakari``:

- ``masakari/api`` contains the api service,
- ``masakari/engine`` contains the engine service.

The data model
==============

The oslo objects
----------------

The base datamodel can be found in ``masakari/objects``.
It uses ``oslo_versionedobjects``.

These objects are used throughout the code, including RPC, REST API and database persistence.

The oslo notifications
----------------------

The datamodel for oslo notifications (not to be confused with Masakari notifications
which are one type of Masakari data objects) can be found in
``masakari/notifications``.

The REST API
------------

Mappings of the models for the API are in ``masakari/api/openstack/ha/schemas``.

The controllers are in ``masakari/api/openstack/ha``.

The implementations of the actions are in ``masakari/ha/api.py``.

The database (persistence)
--------------------------

Some objects can be persisted (saved) to the database,
currently only ``sqlalchemy`` is supported as the backend.

The general interface is in ``masakari/db/api.py``.

The sqlalchemy implementation is in ``masakari/db/sqlalchemy/api.py``.

Database mappings are in ``masakari/db/sqlalchemy/models.py``.

The entry points
================

The Masakari project has a variety of entry points.

The entry points can be found in the ``entry_points`` section of ``setup.cfg``.

The main entry points
---------------------

The main entry points are for the engine and the api:

- ``masakari.cmd.api:main``,
- ``masakari.cmd.engine:main``.

Another interesting one is the entry point for the management CLI, ``masakari.cmd.manage:main``.

The tests
=========

The tests are located in: ``masakari/tests``.
