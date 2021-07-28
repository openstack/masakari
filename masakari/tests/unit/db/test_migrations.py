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

import logging
import os

from migrate.versioning import api as versioning_api
from migrate.versioning import repository
from oslo_db.sqlalchemy import enginefacade
from oslo_db.sqlalchemy import test_fixtures
from oslo_db.sqlalchemy import test_migrations
from oslo_db.sqlalchemy import utils as oslodbutils
from oslotest import base as test_base
import sqlalchemy
from sqlalchemy.engine import reflection
import sqlalchemy.exc

import masakari.conf
from masakari.db.sqlalchemy import migrate_repo
from masakari.db.sqlalchemy import migration as sa_migration
from masakari.db.sqlalchemy import models
from masakari.tests import fixtures as masakari_fixtures


CONF = masakari.conf.CONF


class MasakariMigrationsCheckers(test_migrations.WalkVersionsMixin):
    """Test sqlalchemy-migrate migrations."""

    TIMEOUT_SCALING_FACTOR = 2

    @property
    def INIT_VERSION(self):
        return sa_migration.INIT_VERSION

    @property
    def REPOSITORY(self):
        return repository.Repository(
            os.path.abspath(os.path.dirname(migrate_repo.__file__)))

    @property
    def migration_api(self):
        return versioning_api

    @property
    def migrate_engine(self):
        return self.engine

    def setUp(self):
        super(MasakariMigrationsCheckers, self).setUp()
        migrate_log = logging.getLogger('migrate')
        old_level = migrate_log.level
        migrate_log.setLevel(logging.WARN)
        self.addCleanup(migrate_log.setLevel, old_level)
        self.useFixture(masakari_fixtures.Timeout(
            os.environ.get('OS_TEST_TIMEOUT', 0),
            self.TIMEOUT_SCALING_FACTOR))
        self.engine = enginefacade.writer.get_engine()
        CONF.set_override('connection', str(self.migrate_engine.url),
                          group='taskflow')

    def assertColumnExists(self, engine, table_name, column):
        self.assertTrue(oslodbutils.column_exists(engine, table_name, column),
                        'Column %s.%s does not exist' % (table_name, column))

    def assertColumnNotExists(self, engine, table_name, column):
        self.assertFalse(oslodbutils.column_exists(engine, table_name, column),
                        'Column %s.%s should not exist' % (table_name, column))

    def assertTableNotExists(self, engine, table):
        self.assertRaises(sqlalchemy.exc.NoSuchTableError,
                          oslodbutils.get_table, engine, table)

    def assertIndexExists(self, engine, table_name, index):
        self.assertTrue(oslodbutils.index_exists(engine, table_name, index),
                        'Index %s on table %s does not exist' %
                        (index, table_name))

    def assertIndexNotExists(self, engine, table_name, index):
        self.assertFalse(oslodbutils.index_exists(engine, table_name, index),
                         'Index %s on table %s should not exist' %
                         (index, table_name))

    def assertIndexMembers(self, engine, table, index, members):
        self.assertIndexExists(engine, table, index)

        t = oslodbutils.get_table(engine, table)
        index_columns = None
        for idx in t.indexes:
            if idx.name == index:
                index_columns = [c.name for c in idx.columns]
                break

        self.assertEqual(members, index_columns)

    def include_object(self, object_, name, type_, reflected, compare_to):
        if type_ == 'table':
            # migrate_version is a sqlalchemy-migrate control table and
            # isn't included in the model. shadow_* are generated from
            # the model and have their own tests to ensure they don't
            # drift.
            if name == 'migrate_version' or name.startswith('shadow_'):
                return False

        return True

    # Implementations for ModelsMigrationsSync
    def db_sync(self, engine):
        sa_migration.db_sync(engine=self.migrate_engine)

    def get_engine(self, context=None):
        return self.migrate_engine

    def get_metadata(self):
        return models.BASE.metadata

    def migrate_up(self, version, with_data=False):
        banned = None

        if with_data:
            check = getattr(self, "_check_%03d" % version, None)
            self.assertIsNotNone(check, ('DB Migration %i does not have a '
                                         'test. Please add one!') % version)

        with masakari_fixtures.BannedDBSchemaOperations(banned):
            super(MasakariMigrationsCheckers, self).migrate_up(version,
                                                               with_data)

    def test_walk_versions(self):
        self.walk_versions(snake_walk=False, downgrade=False)

    def _check_001(self, engine, data):
        self.assertColumnExists(engine, 'failover_segments', 'uuid')
        self.assertColumnExists(engine, 'failover_segments', 'name')
        self.assertColumnExists(engine, 'failover_segments', 'service_type')
        self.assertColumnExists(engine, 'failover_segments', 'description')
        self.assertColumnExists(engine, 'failover_segments',
                                'recovery_method')
        self.assertIndexMembers(engine, 'failover_segments',
                                'segments_service_type_idx', ['service_type'])

    def _check_002(self, engine, data):
        self.assertColumnExists(engine, 'hosts', 'uuid')
        self.assertColumnExists(engine, 'hosts', 'name')
        self.assertColumnExists(engine, 'hosts', 'reserved')
        self.assertColumnExists(engine, 'hosts', 'type')
        self.assertColumnExists(engine, 'hosts', 'control_attributes')
        self.assertColumnExists(engine, 'hosts', 'failover_segment_id')
        self.assertColumnExists(engine, 'hosts', 'on_maintenance')
        self.assertColumnExists(engine, 'hosts', 'type')
        self.assertIndexMembers(engine, 'hosts', 'hosts_type_idx', ['type'])

    def _check_003(self, engine, data):
        inspector = reflection.Inspector.from_engine(engine)
        constraints = inspector.get_unique_constraints('hosts')
        constraint_names = [constraint['name'] for constraint in constraints]
        self.assertIn('uniq_host0name0deleted',
                      constraint_names)

    def _check_004(self, engine, data):
        self.assertColumnExists(engine, 'notifications', 'notification_uuid')
        self.assertColumnExists(engine, 'notifications', 'generated_time')
        self.assertColumnExists(engine, 'notifications', 'source_host_uuid')
        self.assertColumnExists(engine, 'notifications', 'type')
        self.assertColumnExists(engine, 'notifications', 'payload')
        self.assertColumnExists(engine, 'notifications', 'status')

    def _check_005(self, engine, data):
        failover_segments = oslodbutils.get_table(engine, 'failover_segments')
        hosts = oslodbutils.get_table(engine, 'hosts')

        for table in [failover_segments, hosts]:
            self.assertTrue(table.c.created_at.nullable)

    def _check_006(self, engine, data):
        self.assertColumnExists(engine, 'logbooks', 'created_at')
        self.assertColumnExists(engine, 'logbooks', 'updated_at')
        self.assertColumnExists(engine, 'logbooks', 'meta')
        self.assertColumnExists(engine, 'logbooks', 'name')
        self.assertColumnExists(engine, 'logbooks', 'uuid')

        self.assertColumnExists(engine, 'flowdetails', 'created_at')
        self.assertColumnExists(engine, 'flowdetails', 'updated_at')
        self.assertColumnExists(engine, 'flowdetails', 'parent_uuid')
        self.assertColumnExists(engine, 'flowdetails', 'meta')
        self.assertColumnExists(engine, 'flowdetails', 'name')
        self.assertColumnExists(engine, 'flowdetails', 'state')
        self.assertColumnExists(engine, 'flowdetails', 'uuid')

        self.assertColumnExists(engine, 'atomdetails', 'created_at')
        self.assertColumnExists(engine, 'atomdetails', 'updated_at')
        self.assertColumnExists(engine, 'atomdetails', 'parent_uuid')
        self.assertColumnExists(engine, 'atomdetails', 'meta')
        self.assertColumnExists(engine, 'atomdetails', 'name')
        self.assertColumnExists(engine, 'atomdetails', 'results')
        self.assertColumnExists(engine, 'atomdetails', 'version')
        self.assertColumnExists(engine, 'atomdetails', 'state')
        self.assertColumnExists(engine, 'atomdetails', 'uuid')
        self.assertColumnExists(engine, 'atomdetails', 'failure')
        self.assertColumnExists(engine, 'atomdetails', 'atom_type')
        self.assertColumnExists(engine, 'atomdetails', 'intention')
        self.assertColumnExists(engine, 'atomdetails', 'revert_results')
        self.assertColumnExists(engine, 'atomdetails', 'revert_failure')

    def _check_007(self, engine, data):
        self.assertColumnExists(engine, 'failover_segments', 'enabled')


class TestMasakariMigrationsSQLite(
    MasakariMigrationsCheckers,
    test_fixtures.OpportunisticDBTestMixin,
    test_base.BaseTestCase,
):

    def _check_006(self, engine, data):
        # NOTE(ShilpaSD): DB script '006_add_persistence_tables.py' adds db
        # tables required for taskflow which doesn't support Sqlite using
        # alembic migration.
        pass


class TestMasakariMigrationsMySQL(
    MasakariMigrationsCheckers,
    test_fixtures.OpportunisticDBTestMixin,
    test_base.BaseTestCase,
):
    FIXTURE = test_fixtures.MySQLOpportunisticFixture

    def test_innodb_tables(self):
        sa_migration.db_sync(engine=self.migrate_engine)

        total = self.migrate_engine.execute(
            "SELECT count(*) "
            "FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = '%(database)s'" %
            {'database': self.migrate_engine.url.database})
        self.assertGreater(total.scalar(), 0, "No tables found. Wrong schema?")

        noninnodb = self.migrate_engine.execute(
            "SELECT count(*) "
            "FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA='%(database)s' "
            "AND ENGINE != 'InnoDB' "
            "AND TABLE_NAME != 'migrate_version'" %
            {'database': self.migrate_engine.url.database})
        count = noninnodb.scalar()
        self.assertEqual(count, 0, "%d non InnoDB tables created" % count)


class TestMasakariMigrationsPostgreSQL(
    MasakariMigrationsCheckers,
    test_fixtures.OpportunisticDBTestMixin,
    test_base.BaseTestCase,
):
    FIXTURE = test_fixtures.PostgresqlOpportunisticFixture
