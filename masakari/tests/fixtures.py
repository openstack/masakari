# Copyright (c) 2016 NTT DATA
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Fixtures for Masakari tests."""

import fixtures
from oslo_config import cfg

from masakari.db import migration
from masakari.db.sqlalchemy import api as session
from masakari import exception

CONF = cfg.CONF
DB_SCHEMA = {'main': ""}
SESSION_CONFIGURED = False


class Timeout(fixtures.Fixture):
    """Setup per test timeouts.

    In order to avoid test deadlocks we support setting up a test
    timeout parameter read from the environment. In almost all
    cases where the timeout is reached this means a deadlock.

    A class level TIMEOUT_SCALING_FACTOR also exists, which allows
    extremely long tests to specify they need more time.
    """

    def __init__(self, timeout, scaling=1):
        super(Timeout, self).__init__()
        try:
            self.test_timeout = int(timeout)
        except ValueError:
            # If timeout value is invalid do not set a timeout.
            self.test_timeout = 0
        if scaling >= 1:
            self.test_timeout *= scaling
        else:
            raise ValueError('scaling value must be >= 1')

    def setUp(self):
        super(Timeout, self).setUp()
        if self.test_timeout > 0:
            self.useFixture(fixtures.Timeout(self.test_timeout, gentle=True))


class BannedDBSchemaOperations(fixtures.Fixture):
    """Ban some operations for migrations"""
    def __init__(self, banned_resources=None):
        super(BannedDBSchemaOperations, self).__init__()
        self._banned_resources = banned_resources or []

    @staticmethod
    def _explode(resource, op):
        raise exception.DBNotAllowed(
            'Operation %s.%s() is not allowed in a database migration' % (
                resource, op))

    def setUp(self):
        super(BannedDBSchemaOperations, self).setUp()
        for thing in self._banned_resources:
            self.useFixture(fixtures.MonkeyPatch(
                'sqlalchemy.%s.drop' % thing,
                lambda *a, **k: self._explode(thing, 'drop')))
            self.useFixture(fixtures.MonkeyPatch(
                'sqlalchemy.%s.alter' % thing,
                lambda *a, **k: self._explode(thing, 'alter')))


class DatabasePoisonFixture(fixtures.Fixture):
    def setUp(self):
        super(DatabasePoisonFixture, self).setUp()
        self.useFixture(fixtures.MonkeyPatch(
            'oslo_db.sqlalchemy.enginefacade._TransactionFactory.'
            '_create_session',
            self._poison_configure))

    def _poison_configure(self, *a, **k):
        raise Exception('This test uses methods that set internal oslo_db '
                        'state, but it does not claim to use the database. '
                        'This will conflict with the setup of tests that '
                        'do use the database and cause failures later.')


class Database(fixtures.Fixture):
    def __init__(self, database='main', connection=None):
        """Create a database fixture.

        :param database: The type of database, 'main'
        :param connection: The connection string to use
        """
        super(Database, self).__init__()
        global SESSION_CONFIGURED
        if not SESSION_CONFIGURED:
            session.configure(CONF)
            SESSION_CONFIGURED = True
        self.database = database
        if connection is not None:
            ctxt_mgr = session.create_context_manager(
                connection=connection)
            facade = ctxt_mgr.get_legacy_facade()
            self.get_engine = facade.get_engine
        else:
            self.get_engine = session.get_engine

    def _cache_schema(self):
        global DB_SCHEMA
        if not DB_SCHEMA[self.database]:
            engine = self.get_engine()
            conn = engine.connect()
            migration.db_sync()
            DB_SCHEMA[self.database] = "".join(line for line
                                               in conn.connection.iterdump())
            engine.dispose()

    def cleanup(self):
        engine = self.get_engine()
        engine.dispose()

    def reset(self):
        self._cache_schema()
        engine = self.get_engine()
        engine.dispose()
        conn = engine.connect()
        conn.connection.executescript(DB_SCHEMA[self.database])

    def setUp(self):
        super(Database, self).setUp()
        self.reset()
        self.addCleanup(self.cleanup)
