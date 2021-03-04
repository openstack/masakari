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
"""Unit tests for the DB API."""
from oslo_utils import timeutils

from masakari import context
from masakari import db
from masakari import exception
from masakari import test
from masakari.tests import uuidsentinel

NOW = timeutils.utcnow().replace(microsecond=0)


class ModelsObjectComparatorMixin(object):
    def _dict_from_object(self, obj, ignored_keys):
        if ignored_keys is None:
            ignored_keys = []

        return {k: v for k, v in obj.items()
                if k not in ignored_keys}

    def _assertEqualObjects(self, obj1, obj2, ignored_keys=None):
        obj1 = self._dict_from_object(obj1, ignored_keys)
        obj2 = self._dict_from_object(obj2, ignored_keys)

        self.assertEqual(len(obj1),
                         len(obj2),
                         "Keys mismatch: %s" %
                         str(set(obj1.keys()) ^ set(obj2.keys())))
        for key, value in obj1.items():
            self.assertEqual(value, obj2[key])

    def _assertEqualListsOfObjects(self, objs1, objs2, ignored_keys=None):
        obj_to_dict = lambda o: self._dict_from_object(o, ignored_keys)
        sort_key = lambda d: [d[k] for k in sorted(d)]
        conv_and_sort = lambda obj: sorted(map(obj_to_dict, obj), key=sort_key)

        self.assertEqual(conv_and_sort(objs1), conv_and_sort(objs2))


class FailoverSegmentsTestCase(test.TestCase, ModelsObjectComparatorMixin):

    def setUp(self):
        super(FailoverSegmentsTestCase, self).setUp()
        self.ctxt = context.get_admin_context()

    def _get_fake_values(self):
        return {
            'uuid': uuidsentinel.fake_uuid,
            'name': 'fake_name',
            'service_type': 'fake_service_type',
            'description': 'fake_description',
            'recovery_method': 'auto',
            'enabled': True
        }

    def _get_fake_values_list(self):
        return [
            {"id": 1, 'name': 'test_1', 'service_type': 'fake_service_type_1',
             'recovery_method': 'auto', 'uuid': uuidsentinel.uuid_1},
            {"id": 2, 'name': 'test_2', 'service_type': 'fake_service_type_2',
             'recovery_method': 'auto', 'uuid': uuidsentinel.uuid_2},
            {"id": 3, 'name': 'test_3', 'service_type': 'fake_service_type_3',
             'recovery_method': 'reserved_host', 'uuid': uuidsentinel.uuid_3}]

    def _create_failover_segment(self, values):
        return db.failover_segment_create(self.ctxt, values)

    def _test_get_failover_segment(self, method, filter):
        failover_segments = [self._create_failover_segment(p)
                             for p in self._get_fake_values_list()]
        for failover_segment in failover_segments:
            real_failover_segment = method(self.ctxt, failover_segment[filter])
            self._assertEqualObjects(failover_segment, real_failover_segment)

    def test_failover_segment_create(self):
        failover_segment = self._create_failover_segment(self.
                                                         _get_fake_values())
        self.assertIsNotNone(failover_segment['id'])
        ignored_keys = ['deleted', 'created_at', 'updated_at', 'deleted_at',
                        'id']
        self._assertEqualObjects(failover_segment, self._get_fake_values(),
                                 ignored_keys)

    def test_failover_segment_get_by_id(self):
        self._test_get_failover_segment(db.failover_segment_get_by_id, 'id')

    def test_failover_segment_get_by_uuid(self):
        self._test_get_failover_segment(
            db.failover_segment_get_by_uuid, 'uuid')

    def test_failover_segment_get_by_name(self):
        self._test_get_failover_segment(
            db.failover_segment_get_by_name, 'name')

    def test_failover_segment_update(self):
        update = {'name': 'updated_name',
                  'description': 'updated_desc',
                  'enabled': False}
        updated = {'uuid': uuidsentinel.fake_uuid,
                   'name': 'updated_name',
                   'service_type': 'fake_service_type',
                   'description': 'updated_desc',
                   'recovery_method': 'auto',
                   'enabled': False}
        ignored_keys = ['deleted', 'created_at', 'updated_at', 'deleted_at',
                        'id']
        self._create_failover_segment(self._get_fake_values())
        db.failover_segment_update(self.ctxt, uuidsentinel.fake_uuid, update)
        failover_seg_updated = db.failover_segment_get_by_uuid(
            self.ctxt, uuidsentinel.fake_uuid)
        self._assertEqualObjects(updated, failover_seg_updated, ignored_keys)

    def test_failover_segment_delete(self):
        ctxt = context.get_admin_context()
        result = self._create_failover_segment(self._get_fake_values())
        db.failover_segment_delete(ctxt, result['uuid'])
        self.assertRaises(exception.FailoverSegmentNotFound,
                          db.failover_segment_get_by_uuid, self.ctxt,
                          uuidsentinel.fake_uuid)

    def test_failover_segment_get_all_by_filters(self):
        failover_segments = [self._create_failover_segment(p)
                             for p in self._get_fake_values_list()]
        ignored_keys = ['deleted', 'created_at', 'updated_at', 'deleted_at',
                        'id']
        real_failover_segment = db.failover_segment_get_all_by_filters(
            context=self.ctxt,
            filters={'recovery_method': 'auto'},
            marker=1,
            limit=1,
            sort_keys=['id'],
            sort_dirs=['asc'])
        self._assertEqualListsOfObjects([failover_segments[1]],
                                        real_failover_segment, ignored_keys)

    def test_failover_segment_not_found(self):
        self._create_failover_segment(self._get_fake_values())
        self.assertRaises(exception.FailoverSegmentNotFound,
                          db.failover_segment_get_by_id, self.ctxt,
                          500)
        self.assertRaises(exception.FailoverSegmentNotFoundByName,
                          db.failover_segment_get_by_name, self.ctxt,
                          'test')
        self.assertRaises(exception.FailoverSegmentNotFound,
                          db.failover_segment_delete, self.ctxt,
                          uuidsentinel.uuid_4)

    def test_invalid_marker(self):
        [self._create_failover_segment(p)
         for p in self._get_fake_values_list()]
        self.assertRaises(exception.MarkerNotFound,
                          db.failover_segment_get_all_by_filters,
                          context=self.ctxt, marker=6)

    def test_invalid_sort_key(self):
        [self._create_failover_segment(p)
         for p in self._get_fake_values_list()]
        self.assertRaises(exception.InvalidSortKey,
                          db.failover_segment_get_all_by_filters,
                          context=self.ctxt, sort_keys=['invalid_sort_key'])

    def test_create_existing_failover_segment(self):
        self._create_failover_segment(self._get_fake_values())
        self.assertRaises(exception.FailoverSegmentExists,
                          db.failover_segment_create, self.ctxt,
                          self._get_fake_values())

    def test_update_existing_failover_segment(self):
        [self._create_failover_segment(p)
         for p in self._get_fake_values_list()]
        self.assertRaises(exception.FailoverSegmentExists,
                          db.failover_segment_update, self.ctxt,
                          uuidsentinel.uuid_2,
                          {'name': 'test_1'})


class HostsTestCase(test.TestCase, ModelsObjectComparatorMixin):

    def setUp(self):
        super(HostsTestCase, self).setUp()
        self.ctxt = context.get_admin_context()
        self.failover_segment = self._get_failover_segment()

    def _get_failover_segment(self):
        values = {'uuid': uuidsentinel.failover_segment_id,
                  'name': 'fake_segment_name',
                  'service_type': 'fake_service_type',
                  'description': 'fake_description',
                  'recovery_method': 'auto'}
        return db.failover_segment_create(self.ctxt, values)

    def _get_fake_values(self):
        return {
            'uuid': uuidsentinel.fake_uuid,
            'name': 'fake_name',
            'reserved': True,
            'type': 'fake_type',
            'control_attributes': 'fake_control_attr',
            'failover_segment': self.failover_segment,
            'failover_segment_id': uuidsentinel.failover_segment_id,
            'on_maintenance': True
        }

    def _get_fake_values_list(self):
        return [
            {'id': 1, 'uuid': uuidsentinel.uuid_1, 'name': 'name_1',
             'type': 'type_1', 'failover_segment': self.failover_segment,
             'reserved': True, 'control_attributes': 'fake_ctrl_attr_1',
             'failover_segment_id': uuidsentinel.failover_segment_id,
             'on_maintenance': True},
            {'id': 2, 'uuid': uuidsentinel.uuid_2, 'name': 'name_2',
             'type': 'type_1', 'failover_segment': self.failover_segment,
             'reserved': True, 'control_attributes': 'fake_ctrl_attr_2',
             'failover_segment_id': uuidsentinel.failover_segment_id,
             'on_maintenance': True},
            {'id': 3, 'uuid': uuidsentinel.uuid_3, 'name': 'name_3',
             'type': 'type_2', 'failover_segment': self.failover_segment,
             'reserved': True, 'control_attributes': 'fake_ctrl_attr_3',
             'failover_segment_id': uuidsentinel.failover_segment_id,
             'on_maintenance': True}]

    def _create_host(self, values):
        return db.host_create(self.ctxt, values)

    def _test_get_host(self, method, host_uuid_filter,
                       failover_segment_id_filter=None):
        hosts = [self._create_host(p) for p in self._get_fake_values_list()]
        ignored_key = ['failover_segment']
        for host in hosts:
            if failover_segment_id_filter:
                real_host = method(self.ctxt, host[host_uuid_filter],
                                   host[failover_segment_id_filter])
            else:
                real_host = method(self.ctxt, host[host_uuid_filter])
            self._assertEqualObjects(host, real_host, ignored_key)
            self.assertEqual(host['failover_segment'].items(),
                             real_host['failover_segment'].items())

    def test_host_create(self):
        host = self._create_host(self._get_fake_values())
        self.assertIsNotNone(host['id'])
        ignored_keys = ['deleted', 'created_at', 'updated_at', 'deleted_at',
                        'id']
        self._assertEqualObjects(host, self._get_fake_values(), ignored_keys)

    def test_host_get_by_id(self):
        self._test_get_host(db.host_get_by_id, 'id')

    def test_host_get_by_uuid(self):
        self._test_get_host(db.host_get_by_uuid, 'uuid')

    def test_host_get_by_name(self):
        self._test_get_host(db.host_get_by_name, 'name')

    def test_host_get_by_host_uuid_and_failover_segment_id(self):
        self._test_get_host(db.host_get_by_uuid, 'uuid', 'failover_segment_id')

    def test_host_get_by_uuid_filter_by_invalid_failover_segment(self):
        # create hosts under failover_segment
        # 'uuidsentinel.failover_segment_id'
        for host in self._get_fake_values_list():
            self._create_host(host)

        # create one more failover_segment
        values = {'uuid': uuidsentinel.failover_segment_id_1,
                  'name': 'fake_segment_name_1',
                  'service_type': 'fake_service_type',
                  'description': 'fake_description',
                  'recovery_method': 'auto'}
        db.failover_segment_create(self.ctxt, values)

        # try to get host with failover_segment
        # 'uuidsentinel.failover_segment_id_1'
        self.assertRaises(
            exception.HostNotFoundUnderFailoverSegment, db.host_get_by_uuid,
            self.ctxt, uuidsentinel.uuid_1, uuidsentinel.failover_segment_id_1)

    def test_host_update(self):
        update = {'name': 'updated_name', 'type': 'updated_type'}
        updated = {'uuid': uuidsentinel.fake_uuid,
                   'name': 'updated_name',
                   'reserved': True,
                   'type': 'updated_type',
                   'control_attributes': 'fake_control_attr',
                   'failover_segment': self.failover_segment,
                   'failover_segment_id': uuidsentinel.failover_segment_id,
                   'on_maintenance': True}
        ignored_keys = ['deleted', 'created_at', 'updated_at', 'deleted_at',
                        'id', 'failover_segment']
        self._create_host(self._get_fake_values())
        db.host_update(self.ctxt, uuidsentinel.fake_uuid, update)
        host_updated = db.host_get_by_uuid(self.ctxt, uuidsentinel.fake_uuid)
        self._assertEqualObjects(updated, host_updated, ignored_keys)
        self.assertEqual(updated['failover_segment'].items(),
                         host_updated['failover_segment'].items())

    def test_host_delete(self):
        ctxt = context.get_admin_context()
        result = self._create_host(self._get_fake_values())
        db.host_delete(ctxt, result['uuid'])
        self.assertRaises(exception.HostNotFound,
                          db.host_get_by_uuid, self.ctxt,
                          uuidsentinel.fake_uuid)

    def test_host_get_all_by_filters(self):
        hosts = [self._create_host(p) for p in self._get_fake_values_list()]
        ignored_keys = ['deleted', 'created_at', 'updated_at', 'deleted_at',
                        'id', 'failover_segment']
        real_host = db.host_get_all_by_filters(
            context=self.ctxt,
            filters={'type': 'type_1'},
            marker=1,
            limit=1,
            sort_keys=['id'],
            sort_dirs=['asc'])
        self._assertEqualListsOfObjects([hosts[1]], real_host, ignored_keys)

    def test_host_get_all_by_filter_on_maintenance(self):
        for p in self._get_fake_values_list():
            # create temporary reserved_hosts, all are on maintenance
            self._create_host(p)

        # create one more reserved_host which is not on maintenance
        temp_host = self._get_fake_values()
        temp_host['on_maintenance'] = False
        temp_host['failover_segment_id'] = uuidsentinel.failover_segment_id
        self._create_host(temp_host)

        ignored_keys = ['deleted', 'created_at', 'updated_at', 'deleted_at',
                        'id', 'failover_segment']
        real_host = db.host_get_all_by_filters(
            context=self.ctxt,
            filters={'on_maintenance': False},
            marker=1,
            limit=1,
            sort_keys=['id'],
            sort_dirs=['asc'])
        self._assertEqualListsOfObjects([temp_host], real_host, ignored_keys)

    def test_host_not_found(self):
        self._create_host(self._get_fake_values())
        self.assertRaises(exception.HostNotFound,
                          db.host_get_by_id, self.ctxt,
                          5)
        self.assertRaises(exception.HostNotFoundByName,
                          db.host_get_by_name, self.ctxt,
                          'test')
        self.assertRaises(exception.HostNotFound,
                          db.host_delete, self.ctxt,
                          uuidsentinel.uuid_4)

    def test_invalid_marker(self):
        [self._create_host(p) for p in self._get_fake_values_list()]
        self.assertRaises(exception.MarkerNotFound,
                          db.host_get_all_by_filters, context=self.ctxt,
                          marker=6)

    def test_invalid_sort_key(self):
        [self._create_host(p) for p in self._get_fake_values_list()]
        self.assertRaises(exception.InvalidSortKey,
                          db.host_get_all_by_filters, context=self.ctxt,
                          sort_keys=['invalid_sort_key'])

    def test_create_existing_host(self):
        self._create_host(self._get_fake_values())
        self.assertRaises(exception.HostExists,
                          db.host_create, self.ctxt,
                          self._get_fake_values())

    def test_update_existing_host(self):
        [self._create_host(p) for p in self._get_fake_values_list()]
        self.assertRaises(exception.HostExists, db.host_update,
                          self.ctxt, uuidsentinel.uuid_2, {'name': 'name_1'})


class NotificationsTestCase(test.TestCase, ModelsObjectComparatorMixin):

    def setUp(self):
        super(NotificationsTestCase, self).setUp()
        self.ctxt = context.get_admin_context()

    def _get_fake_values(self):
        return {
            'notification_uuid': uuidsentinel.notification,
            'generated_time': NOW,
            'source_host_uuid': uuidsentinel.source_host,
            'type': 'fake_type',
            'payload': 'fake_payload',
            'status': 'new'
        }

    def _get_fake_values_list(self):
        return [
            {'id': 1, 'notification_uuid': uuidsentinel.notification_1,
             'generated_time': NOW,
             'source_host_uuid': uuidsentinel.s_host_1, 'type': 'fake_type',
             'payload': 'fake_payload', 'status': 'new'},
            {'id': 2, 'notification_uuid': uuidsentinel.notification_2,
             'generated_time': NOW,
             'source_host_uuid': uuidsentinel.s_host_2, 'type': 'fake_type',
             'payload': 'fake_payload', 'status': 'new'},
            {'id': 3, 'notification_uuid': uuidsentinel.notification_3,
             'generated_time': NOW,
             'source_host_uuid': uuidsentinel.s_host_3, 'type': 'fake_type',
             'payload': 'fake_payload', 'status': 'failed'}]

    def _create_notification(self, values):
        return db.notification_create(self.ctxt, values)

    def _test_get_notification(self, method, filter):
        notifications = [self._create_notification(p)
                         for p in self._get_fake_values_list()]
        for notification in notifications:
            real_notification = method(self.ctxt, notification[filter])
            self._assertEqualObjects(notification, real_notification)

    def test_notification_create(self):
        notification = self._create_notification(self._get_fake_values())
        self.assertIsNotNone(notification['id'])
        ignored_keys = ['deleted', 'created_at', 'updated_at', 'deleted_at',
                        'id']
        self._assertEqualObjects(notification, self._get_fake_values(),
                                 ignored_keys)

    def test_notification_get_by_id(self):
        self._test_get_notification(db.notification_get_by_id, 'id')

    def test_notification_get_by_uuid(self):
        self._test_get_notification(db.notification_get_by_uuid,
                                    'notification_uuid')

    def test_notification_update(self):
        update = {'type': 'updated_type', 'payload': 'updated_payload'}
        updated = {'notification_uuid': uuidsentinel.notification,
                   'generated_time': NOW,
                   'source_host_uuid': uuidsentinel.source_host,
                   'type': 'updated_type',
                   'payload': 'updated_payload',
                   'status': 'new'}
        ignored_keys = ['deleted', 'created_at', 'updated_at', 'deleted_at',
                        'id']
        self._create_notification(self._get_fake_values())
        db.notification_update(self.ctxt, uuidsentinel.notification, update)
        notification_updated = db.notification_get_by_uuid(
            self.ctxt, uuidsentinel.notification)
        self._assertEqualObjects(updated, notification_updated, ignored_keys)

    def test_notification_delete(self):
        ctxt = context.get_admin_context()
        result = self._create_notification(self._get_fake_values())
        db.notification_delete(ctxt, result['notification_uuid'])
        self.assertRaises(exception.NotificationNotFound,
                          db.notification_get_by_uuid, self.ctxt,
                          uuidsentinel.notification)

    def test_notification_get_all_by_filters(self):
        notifications = [self._create_notification(p)
                         for p in self._get_fake_values_list()]
        ignored_keys = ['deleted', 'created_at', 'updated_at', 'deleted_at',
                        'id']
        real_notification = db.notifications_get_all_by_filters(
            context=self.ctxt,
            filters={'status': 'new'},
            marker=1,
            limit=1,
            sort_keys=['id'],
            sort_dirs=['asc'])
        self._assertEqualListsOfObjects([notifications[1]],
                                        real_notification, ignored_keys)

    def test_notification_not_found(self):
        self._create_notification(self._get_fake_values())
        self.assertRaises(exception.NotificationNotFound,
                          db.notification_get_by_id, self.ctxt,
                          500)
        self.assertRaises(exception.NotificationNotFound,
                          db.notification_delete, self.ctxt,
                          uuidsentinel.fake_uuid)

    def test_invalid_marker(self):
        [self._create_notification(p) for p in self._get_fake_values_list()]
        self.assertRaises(exception.MarkerNotFound,
                          db.notifications_get_all_by_filters,
                          context=self.ctxt, marker=6)

    def test_invalid_sort_key(self):
        [self._create_notification(p) for p in self._get_fake_values_list()]
        self.assertRaises(exception.InvalidSortKey,
                          db.notifications_get_all_by_filters,
                          context=self.ctxt, sort_keys=['invalid_sort_key'])
