#    Copyright 2016 NTT DATA
#    All Rights Reserved.
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

import copy
from unittest import mock

from oslo_utils import timeutils

from masakari.api import utils as api_utils
from masakari import db
from masakari import exception
from masakari.objects import fields
from masakari.objects import host
from masakari.tests.unit import fakes as fakes_data
from masakari.tests.unit.objects import test_objects
from masakari.tests import uuidsentinel

NOW = timeutils.utcnow().replace(microsecond=0)

fake_segment_dict = {
    'name': 'fake_segment',
    'recovery_method': 'auto',
    'description': 'fake',
    'service_type': 'CINDER',
    'enabled': True,
    'id': 123,
    'uuid': uuidsentinel.fake_segment,
    'created_at': NOW,
    'updated_at': None,
    'deleted_at': None,
    'deleted': False
}


def _fake_host(**kwargs):
    fake_host = {
        'created_at': NOW,
        'updated_at': None,
        'deleted_at': None,
        'deleted': False,
        'id': 123,
        'uuid': uuidsentinel.fake_host,
        'name': 'fake-host',
        'reserved': False,
        'on_maintenance': False,
        'control_attributes': 'fake_control_attributes',
        'type': 'SSH',
        'failover_segment': fake_segment_dict
        }
    fake_host.update(kwargs)
    return fake_host


fake_host = _fake_host()


class TestHostObject(test_objects._LocalTest):

    def _compare_segment_and_host_data(self, obj):

        self.compare_obj(obj.failover_segment, fake_segment_dict)
        self.assertEqual(obj.name, fake_host.get('name'))
        self.assertEqual(obj.reserved, fake_host.get('reserved'))
        self.assertEqual(obj.on_maintenance, fake_host.get('on_maintenance'))
        self.assertEqual(obj.type, fake_host.get('type'))
        self.assertEqual(obj.control_attributes, fake_host.get('control_attri'
                                                               'butes'))
        self.assertEqual(obj.id, 123)

    def _test_query(self, db_method, obj_method, *args, **kwargs):
        with mock.patch.object(db, db_method) as mock_db:

            db_exception = kwargs.pop('db_exception', None)
            if db_exception:
                mock_db.side_effect = db_exception
            else:
                mock_db.return_value = fake_host

            obj = getattr(host.Host, obj_method)(self.context, *args, **kwargs)
            if db_exception:
                self.assertIsNone(obj)

            self._compare_segment_and_host_data(obj)

    def test_get_by_id(self):
        self._test_query('host_get_by_id', 'get_by_id', 123)

    def test_get_by_uuid(self):
        self._test_query('host_get_by_uuid', 'get_by_uuid',
                         uuidsentinel.fake_segment)

    def test_get_by_name(self):
        self._test_query('host_get_by_name', 'get_by_name',
                         'fake-host')

    def _host_create_attributes(self):

        failover_segment = fakes_data.create_fake_failover_segment(
            name="fake_segment", id=123, description="fakefake",
            service_type="COMPUTE", recovery_method="auto",
            uuid=uuidsentinel.fake_segment
        )

        host_obj = host.Host(context=self.context)
        host_obj.name = 'foo-host'
        host_obj.failover_segment = failover_segment
        host_obj.type = 'fake-type'
        host_obj.reserved = False
        host_obj.on_maintenance = False
        host_obj.control_attributes = 'fake_attributes'
        host_obj.uuid = uuidsentinel.fake_host

        return host_obj

    @mock.patch.object(api_utils, 'notify_about_host_api')
    @mock.patch.object(db, 'host_create')
    def test_create(self, mock_db_create, mock_notify_about_host_api):

        mock_db_create.return_value = fake_host
        host_obj = self._host_create_attributes()
        host_obj.create()
        self._compare_segment_and_host_data(host_obj)
        mock_db_create.assert_called_once_with(self.context, {
            'failover_segment_id': uuidsentinel.fake_segment,
            'on_maintenance': False, 'uuid': uuidsentinel.fake_host,
            'reserved': False, 'name': 'foo-host',
            'control_attributes': 'fake_attributes',
            'type': 'fake-type'})
        action = fields.EventNotificationAction.HOST_CREATE
        phase_start = fields.EventNotificationPhase.START
        phase_end = fields.EventNotificationPhase.END
        notify_calls = [
            mock.call(self.context, host_obj, action=action,
                      phase=phase_start),
            mock.call(self.context, host_obj, action=action,
                      phase=phase_end)]
        mock_notify_about_host_api.assert_has_calls(notify_calls)

    @mock.patch.object(api_utils, 'notify_about_host_api')
    @mock.patch.object(db, 'host_create')
    def test_recreate_fails(self, mock_host_create,
                            mock_notify_about_host_api):
        mock_host_create.return_value = fake_host
        host_obj = self._host_create_attributes()
        host_obj.create()

        self.assertRaises(exception.ObjectActionError, host_obj.create)
        action = fields.EventNotificationAction.HOST_CREATE
        phase_start = fields.EventNotificationPhase.START
        phase_end = fields.EventNotificationPhase.END
        notify_calls = [
            mock.call(self.context, host_obj, action=action,
                      phase=phase_start),
            mock.call(self.context, host_obj, action=action,
                      phase=phase_end)]
        mock_notify_about_host_api.assert_has_calls(notify_calls)

        mock_host_create.assert_called_once_with(self.context, {
            'uuid': uuidsentinel.fake_host, 'name': 'foo-host',
            'failover_segment_id': uuidsentinel.fake_segment,
            'type': 'fake-type', 'reserved': False, 'on_maintenance': False,
            'control_attributes': 'fake_attributes'})

    @mock.patch.object(api_utils, 'notify_about_host_api')
    @mock.patch.object(db, 'host_delete')
    def test_destroy(self, mock_host_destroy, mock_notify_about_host_api):
        host_obj = self._host_create_attributes()
        host_obj.id = 123
        host_obj.destroy()

        mock_host_destroy.assert_called_once_with(
            self.context, uuidsentinel.fake_host)
        action = fields.EventNotificationAction.HOST_DELETE
        phase_start = fields.EventNotificationPhase.START
        phase_end = fields.EventNotificationPhase.END
        notify_calls = [
            mock.call(self.context, host_obj, action=action,
                      phase=phase_start),
            mock.call(self.context, host_obj, action=action,
                      phase=phase_end)]
        mock_notify_about_host_api.assert_has_calls(notify_calls)

    @mock.patch.object(api_utils, 'notify_about_host_api')
    @mock.patch.object(db, 'host_delete')
    def test_destroy_host_not_found(self, mock_host_destroy,
                                    mock_notify_about_host_api):
        mock_host_destroy.side_effect = exception.HostNotFound(id=123)
        host_obj = self._host_create_attributes()
        host_obj.id = 123
        self.assertRaises(exception.HostNotFound, host_obj.destroy)
        action = fields.EventNotificationAction.HOST_DELETE
        phase_start = fields.EventNotificationPhase.START
        notify_calls = [
            mock.call(self.context, host_obj, action=action,
                      phase=phase_start)]
        mock_notify_about_host_api.assert_has_calls(notify_calls)

    @mock.patch.object(db, 'host_get_all_by_filters')
    def test_get_host_by_filters(self, mock_api_get):
        fake_host2 = copy.deepcopy(fake_host)
        fake_host2['name'] = 'fake_host22'

        mock_api_get.return_value = [fake_host2, fake_host]

        filters = {'reserved': False}
        host_result = host.HostList.get_all(self.context, filters=filters)
        self.assertEqual(2, len(host_result))
        mock_api_get.assert_called_once_with(self.context, filters={
            'reserved': False
        }, limit=None, marker=None, sort_dirs=None, sort_keys=None)

    @mock.patch.object(db, 'host_get_all_by_filters')
    def test_get_limit_and_marker_invalid_marker(self, mock_api_get):
        host_name = 'fake-host'
        mock_api_get.side_effect = exception.MarkerNotFound(marker=host_name)

        self.assertRaises(exception.MarkerNotFound,
                          host.HostList.get_all,
                          self.context, limit=5, marker=host_name)

    @mock.patch.object(api_utils, 'notify_about_host_api')
    @mock.patch('masakari.objects.base.MasakariObject'
                '.masakari_obj_get_changes')
    @mock.patch.object(db, 'host_update')
    def test_save(
            self, mock_host_update, mock_masakari_obj_get_changes,
            mock_notify_about_host_api):

        mock_host_update.return_value = fake_host

        host_data = {
            'name': 'foo-host',
            "uuid": uuidsentinel.fake_host,
            'id': 123
        }

        mock_masakari_obj_get_changes.return_value = host_data
        host_obj = self._host_create_attributes()
        host_obj.id = 123
        host_obj.save()
        self._compare_segment_and_host_data(host_obj)
        (mock_host_update.
         assert_called_once_with(self.context, uuidsentinel.fake_host,
                                 {'name': 'foo-host',
                                  'uuid': uuidsentinel.fake_host
                                  }))
        action = fields.EventNotificationAction.HOST_UPDATE
        phase_start = fields.EventNotificationPhase.START
        phase_end = fields.EventNotificationPhase.END
        notify_calls = [
            mock.call(self.context, host_obj, action=action,
                      phase=phase_start),
            mock.call(self.context, host_obj, action=action,
                      phase=phase_end)]
        mock_notify_about_host_api.assert_has_calls(notify_calls)

    @mock.patch.object(db, 'host_update')
    def test_save_lazy_attribute_changed(self, mock_host_update):

        mock_host_update.return_value = fake_host

        host_obj = self._host_create_attributes()
        host_obj.id = 123
        self.assertRaises(exception.ObjectActionError, host_obj.save)

    @mock.patch.object(api_utils, 'notify_about_host_api')
    @mock.patch.object(db, 'host_update')
    def test_save_host_already_exists(self, mock_host_update,
                                      mock_notify_about_host_api):

        mock_host_update.side_effect = exception.HostExists(name="foo-host")

        host_object = host.Host(context=self.context)
        host_object.name = "foo-host"
        host_object.id = 123
        host_object.uuid = uuidsentinel.fake_host

        self.assertRaises(exception.HostExists, host_object.save)
        action = fields.EventNotificationAction.HOST_UPDATE
        phase_start = fields.EventNotificationPhase.START
        notify_calls = [
            mock.call(self.context, host_object, action=action,
                      phase=phase_start)]
        mock_notify_about_host_api.assert_has_calls(notify_calls)

    @mock.patch.object(api_utils, 'notify_about_host_api')
    @mock.patch.object(db, 'host_update')
    def test_save_host_not_found(self, mock_host_update,
                                 mock_notify_about_host_api):

        mock_host_update.side_effect = exception.HostNotFound(id="foo-host")

        host_object = host.Host(context=self.context)
        host_object.name = "foo-host"
        host_object.id = 123
        host_object.uuid = uuidsentinel.fake_host

        self.assertRaises(exception.HostNotFound, host_object.save)
        action = fields.EventNotificationAction.HOST_UPDATE
        phase_start = fields.EventNotificationPhase.START
        notify_calls = [
            mock.call(self.context, host_object, action=action,
                      phase=phase_start)]
        mock_notify_about_host_api.assert_has_calls(notify_calls)

    def _host_create_attributes2(self):

        failover_segment = fakes_data.create_fake_failover_segment(
            name="fake_segment", id=123, description="fakefake",
            service_type="COMPUTE", recovery_method="auto",
            uuid=uuidsentinel.fake_segment
        )

        host_obj = self._host_create_attributes()
        host_obj.failover_segment_id = failover_segment.uuid

        return host_obj

    def test_obj_make_compatible(self):
        host_obj = self._host_create_attributes2()
        primitive = host_obj.obj_to_primitive()
        self.assertIn('failover_segment', primitive['masakari_object.data'])
        self.assertNotIn(
            'failover_segment_id', primitive['masakari_object.data'])
