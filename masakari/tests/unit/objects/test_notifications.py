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
from oslo_utils import uuidutils

from masakari.api import utils as api_utils
from masakari import db
from masakari import exception
from masakari.objects import fields
from masakari.objects import notification
from masakari.tests.unit.objects import test_objects
from masakari.tests import uuidsentinel

NOW = timeutils.utcnow().replace(microsecond=0)
OPTIONAL = ['recovery_workflow_details']


def _fake_db_notification(**kwargs):
    fake_notification = {
        'created_at': NOW,
        'updated_at': None,
        'deleted_at': None,
        'deleted': False,
        'id': 123,
        'notification_uuid': uuidsentinel.fake_notification,
        'generated_time': NOW,
        'type': 'COMPUTE_HOST',
        'payload': '{"fake_key": "fake_value"}',
        'status': 'new',
        'source_host_uuid': uuidsentinel.fake_host,
        }
    fake_notification.update(kwargs)
    return fake_notification


def _fake_object_notification(**kwargs):
    fake_notification = {
        'created_at': NOW,
        'updated_at': None,
        'deleted_at': None,
        'deleted': False,
        'id': 123,
        'notification_uuid': uuidsentinel.fake_notification,
        'generated_time': NOW,
        'type': 'COMPUTE_HOST',
        'payload': {"fake_key": "fake_value"},
        'status': 'new',
        'source_host_uuid': uuidsentinel.fake_host,
        }
    fake_notification.update(kwargs)
    return fake_notification


fake_object_notification = _fake_object_notification()

fake_db_notification = _fake_db_notification()


class TestNotificationObject(test_objects._LocalTest):

    def _test_query(self, db_method, obj_method, *args, **kwargs):
        with mock.patch.object(db, db_method) as mock_db:

            db_exception = kwargs.pop('db_exception', None)
            if db_exception:
                mock_db.side_effect = db_exception
            else:
                mock_db.return_value = fake_db_notification

            obj = getattr(notification.Notification, obj_method
                          )(self.context, *args, **kwargs)
            if db_exception:
                self.assertIsNone(obj)

            self.compare_obj(obj, fake_object_notification,
                             allow_missing=OPTIONAL)

    def test_get_by_id(self):
        self._test_query('notification_get_by_id', 'get_by_id', 123)

    def test_get_by_uuid(self):
        self._test_query('notification_get_by_uuid', 'get_by_uuid',
                         uuidsentinel.fake_segment)

    def _notification_create_attributes(self, skip_uuid=False):

        notification_obj = notification.Notification(context=self.context)
        notification_obj.generated_time = NOW
        notification_obj.type = "COMPUTE_HOST"
        notification_obj.payload = {'fake_key': 'fake_value'}
        notification_obj.status = "new"
        if not skip_uuid:
            notification_obj.notification_uuid = uuidsentinel.fake_notification
        notification_obj.source_host_uuid = uuidsentinel.fake_host

        return notification_obj

    @mock.patch.object(api_utils, 'notify_about_notification_api')
    @mock.patch.object(db, 'notification_create')
    def test_create(self, mock_db_create, mock_notify_about_notification_api):

        mock_db_create.return_value = fake_db_notification
        notification_obj = self._notification_create_attributes()
        notification_obj.create()

        self.compare_obj(notification_obj, fake_object_notification,
                         allow_missing=OPTIONAL)
        mock_db_create.assert_called_once_with(self.context, {
            'source_host_uuid': uuidsentinel.fake_host,
            'notification_uuid': uuidsentinel.fake_notification,
            'generated_time': NOW, 'status': 'new',
            'type': 'COMPUTE_HOST', 'payload': '{"fake_key": "fake_value"}'})
        action = fields.EventNotificationAction.NOTIFICATION_CREATE
        phase_start = fields.EventNotificationPhase.START
        phase_end = fields.EventNotificationPhase.END
        notify_calls = [
            mock.call(self.context, notification_obj, action=action,
                      phase=phase_start),
            mock.call(self.context, notification_obj, action=action,
                      phase=phase_end)]
        mock_notify_about_notification_api.assert_has_calls(notify_calls)

    @mock.patch.object(api_utils, 'notify_about_notification_api')
    @mock.patch.object(db, 'notification_create')
    def test_recreate_fails(self, mock_notification_create,
                            mock_notify_about_notification_api):
        mock_notification_create.return_value = fake_db_notification
        notification_obj = self._notification_create_attributes()
        notification_obj.create()

        self.assertRaises(exception.ObjectActionError, notification_obj.create)

        mock_notification_create.assert_called_once_with(self.context, {
            'source_host_uuid': uuidsentinel.fake_host,
            'notification_uuid': uuidsentinel.fake_notification,
            'generated_time': NOW, 'status': 'new',
            'type': 'COMPUTE_HOST', 'payload': '{"fake_key": "fake_value"}'})
        action = fields.EventNotificationAction.NOTIFICATION_CREATE
        phase_start = fields.EventNotificationPhase.START
        phase_end = fields.EventNotificationPhase.END
        notify_calls = [
            mock.call(self.context, notification_obj, action=action,
                      phase=phase_start),
            mock.call(self.context, notification_obj, action=action,
                      phase=phase_end)]
        mock_notify_about_notification_api.assert_has_calls(notify_calls)

    @mock.patch.object(api_utils, 'notify_about_notification_api')
    @mock.patch.object(db, 'notification_create')
    @mock.patch.object(uuidutils, 'generate_uuid')
    def test_create_without_passing_uuid_in_updates(self, mock_generate_uuid,
                        mock_db_create, mock_notify_about_notification_api):

        mock_db_create.return_value = fake_db_notification
        mock_generate_uuid.return_value = uuidsentinel.fake_notification
        notification_obj = self._notification_create_attributes(skip_uuid=True)

        notification_obj.create()

        self.compare_obj(notification_obj, fake_object_notification,
                         allow_missing=OPTIONAL)
        mock_db_create.assert_called_once_with(self.context, {
            'source_host_uuid': uuidsentinel.fake_host,
            'notification_uuid': uuidsentinel.fake_notification,
            'generated_time': NOW, 'status': 'new',
            'type': 'COMPUTE_HOST', 'payload': '{"fake_key": "fake_value"}'})
        self.assertTrue(mock_generate_uuid.called)
        action = fields.EventNotificationAction.NOTIFICATION_CREATE
        phase_start = fields.EventNotificationPhase.START
        notify_calls = [
            mock.call(self.context, notification_obj, action=action,
                      phase=phase_start)]
        mock_notify_about_notification_api.assert_has_calls(notify_calls)

    @mock.patch.object(db, 'notification_delete')
    def test_destroy(self, mock_notification_delete):
        notification_obj = self._notification_create_attributes()
        notification_obj.id = 123
        notification_obj.destroy()

        (mock_notification_delete.
         assert_called_once_with(self.context, uuidsentinel.fake_notification))
        self.assertRaises(NotImplementedError, lambda: notification_obj.id)

    @mock.patch.object(db, 'notification_delete')
    def test_destroy_without_id(self, mock_destroy):
        notification_obj = self._notification_create_attributes()
        self.assertRaises(exception.ObjectActionError,
                          notification_obj.destroy)
        self.assertFalse(mock_destroy.called)

    @mock.patch.object(db, 'notification_delete')
    def test_destroy_without_notification_uuid(self, mock_destroy):
        notification_obj = self._notification_create_attributes(skip_uuid=True)
        notification_obj.id = 123

        self.assertRaises(exception.ObjectActionError,
                          notification_obj.destroy)
        self.assertFalse(mock_destroy.called)

    @mock.patch.object(db, 'notifications_get_all_by_filters')
    def test_get_notification_by_filters(self, mock_api_get):
        fake_db_notification2 = copy.deepcopy(fake_db_notification)
        fake_db_notification2['type'] = 'PROCESS'
        fake_db_notification2['id'] = 124
        fake_db_notification2[
            'notification_uuid'] = uuidsentinel.fake_db_notification2

        mock_api_get.return_value = [fake_db_notification2,
                                     fake_db_notification]

        filters = {'status': 'new'}
        notification_result = (notification.NotificationList.
                               get_all(self.context, filters=filters))
        self.assertEqual(2, len(notification_result))
        mock_api_get.assert_called_once_with(self.context, filters={
            'status': 'new'
        }, limit=None, marker=None, sort_dirs=None, sort_keys=None)

    @mock.patch.object(db, 'notifications_get_all_by_filters')
    def test_get_limit_and_marker_invalid_marker(self, mock_api_get):
        notification_uuid = uuidsentinel.fake_notification
        mock_api_get.side_effect = (exception.
                                    MarkerNotFound(marker=notification_uuid))

        self.assertRaises(exception.MarkerNotFound,
                          notification.NotificationList.get_all,
                          self.context, limit=5, marker=notification_uuid)

    @mock.patch.object(db, 'notification_update')
    def test_save(self, mock_notification_update):

        mock_notification_update.return_value = fake_db_notification

        notification_obj = self._notification_create_attributes()
        notification_obj.id = 123
        notification_obj.save()

        self.compare_obj(notification_obj, fake_object_notification,
                         allow_missing=OPTIONAL)
        (mock_notification_update.
         assert_called_once_with(self.context, uuidsentinel.fake_notification,
                                 {'source_host_uuid': uuidsentinel.fake_host,
                                  'notificati'
                                  'on_uuid': uuidsentinel.fake_notification,
                                  'status': 'new', 'generated_time': NOW,
                                  'payload': {'fake_key': 'fake_value'},
                                  'type': 'COMPUTE_HOST'}
                                 ))
