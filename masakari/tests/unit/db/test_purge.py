# Copyright 2017 NTT DATA
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Tests for db purge."""

import datetime
import uuid

from oslo_db.sqlalchemy import utils as sqlalchemyutils
from oslo_utils import timeutils
from sqlalchemy.dialects import sqlite
from sqlalchemy.sql import func, select

from masakari import context
from masakari import db
from masakari.db.sqlalchemy import api as db_api
from masakari import test


class PurgeDeletedTest(test.TestCase):

    def setUp(self):
        super(PurgeDeletedTest, self).setUp()
        self.context = context.get_admin_context()
        self.engine = db_api.get_engine()
        self.conn = self.engine.connect()
        self.notifications = sqlalchemyutils.get_table(
            self.engine, "notifications")
        self.failover_segments = sqlalchemyutils.get_table(
            self.engine, "failover_segments")
        # The hosts table has a FK of segment_id
        self.hosts = sqlalchemyutils.get_table(
            self.engine, "hosts")

        # Add 6 rows to table
        self.uuidstrs = []
        self.uuid_fs_segments = []
        self.uuid_hosts = []
        for record in range(6):
            notification_uuid = uuid.uuid4().hex
            fs_segment_uuid = uuid.uuid4().hex
            host_uuid = uuid.uuid4().hex
            ins_stmt = self.notifications.insert().values(
                notification_uuid=notification_uuid,
                generated_time=timeutils.utcnow(),
                source_host_uuid=host_uuid,
                type='demo',
                status='failed')
            self.uuidstrs.append(notification_uuid)
            self.conn.execute(ins_stmt)

            ins_stmt = self.failover_segments.insert().values(
                uuid=fs_segment_uuid,
                name='test',
                service_type='demo',
                recovery_method='auto')
            self.uuid_fs_segments.append(fs_segment_uuid)
            self.conn.execute(ins_stmt)

            ins_stmt = self.hosts.insert().values(
                uuid=host_uuid,
                failover_segment_id=fs_segment_uuid,
                name='host1',
                type='demo',
                control_attributes='test')
            self.uuid_hosts.append(host_uuid)
            self.conn.execute(ins_stmt)

        # Set 4 of them deleted, 2 are 60 days ago, 2 are 20 days ago
        self.age_in_days_20 = timeutils.utcnow() - datetime.timedelta(days=20)
        self.age_in_days_60 = timeutils.utcnow() - datetime.timedelta(days=60)

        make_notifications_old = self.notifications.update().where(
            self.notifications.c.notification_uuid.in_(
                self.uuidstrs[1:3])).values(updated_at=self.age_in_days_20)
        make_notifications_older = self.notifications.update().where(
            self.notifications.c.notification_uuid.in_(
                self.uuidstrs[4:6])).values(updated_at=self.age_in_days_60)
        make_failover_segments_old = self.failover_segments.update().where(
            self.failover_segments.c.uuid.in_(
                self.uuid_fs_segments[1:3])).values(
            deleted_at=self.age_in_days_20)
        make_failover_segments_older = self.failover_segments.update().where(
            self.failover_segments.c.uuid.in_(
                self.uuid_fs_segments[4:6])).values(
            deleted_at=self.age_in_days_60)
        make_hosts_old = self.hosts.update().where(
            self.hosts.c.uuid.in_(self.uuid_hosts[1:3])).values(
            deleted_at=self.age_in_days_20)
        make_hosts_older = self.hosts.update().where(
            self.hosts.c.uuid.in_(self.uuid_hosts[4:6])).values(
            deleted_at=self.age_in_days_60)

        self.conn.execute(make_notifications_old)
        self.conn.execute(make_notifications_older)
        self.conn.execute(make_failover_segments_old)
        self.conn.execute(make_failover_segments_older)
        self.conn.execute(make_hosts_old)
        self.conn.execute(make_hosts_older)

        dialect = self.engine.url.get_dialect()
        if dialect == sqlite.dialect:
            self.conn.execute("PRAGMA foreign_keys = ON")

    def _count(self, table):
        return self.conn.execute(
            select([func.count()]).select_from(table)).scalar()

    def test_purge_deleted_rows_old(self):
        # Purge at 30 days old, should only delete 2 rows
        db.purge_deleted_rows(self.context, age_in_days=30, max_rows=10)

        notifications_rows = self._count(self.notifications)
        failover_segments_rows = self._count(self.failover_segments)
        hosts_rows = self._count(self.hosts)

        # Verify that we only deleted 2
        self.assertEqual(4, notifications_rows)
        self.assertEqual(4, failover_segments_rows)
        self.assertEqual(4, hosts_rows)

    def test_purge_all_deleted_rows(self):
        db.purge_deleted_rows(self.context, age_in_days=20, max_rows=-1)

        notifications_rows = self._count(self.notifications)
        failover_segments_rows = self._count(self.failover_segments)
        hosts_rows = self._count(self.hosts)

        # Verify that we have purged all deleted rows
        self.assertEqual(2, notifications_rows)
        self.assertEqual(2, failover_segments_rows)
        self.assertEqual(2, hosts_rows)

    def test_purge_maximum_rows_partial_deleted_records(self):
        db.purge_deleted_rows(self.context, age_in_days=60, max_rows=3)

        notifications_rows = self._count(self.notifications)
        failover_segments_rows = self._count(self.failover_segments)
        hosts_rows = self._count(self.hosts)

        # Verify that we have deleted 3 rows only
        self.assertEqual(4, notifications_rows)
        self.assertEqual(5, hosts_rows)
        self.assertEqual(6, failover_segments_rows)
