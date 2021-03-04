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
from masakari import exception
from masakari.objects import fields
from masakari.objects import segment
from masakari.tests.unit.objects import test_objects
from masakari.tests import uuidsentinel


NOW = timeutils.utcnow().replace(microsecond=0)

fake_segment = {
    'created_at': NOW,
    'updated_at': None,
    'deleted_at': None,
    'deleted': False,
    'id': 123,
    'uuid': uuidsentinel.fake_segment,
    'name': 'foo-segment',
    'service_type': 'COMPUTE',
    'description': 'fake-description',
    'recovery_method': 'auto',
    'enabled': True
    }


class TestFailoverSegmentObject(test_objects._LocalTest):

    @mock.patch('masakari.db.failover_segment_get_by_name')
    def test_get_by_name(self, mock_api_get):

        mock_api_get.return_value = fake_segment

        segment_obj = segment.FailoverSegment.get_by_name(self.context,
                                                          'foo-segment')
        self.compare_obj(segment_obj, fake_segment)

        mock_api_get.assert_called_once_with(self.context, 'foo-segment')

    @mock.patch('masakari.db.failover_segment_get_by_uuid')
    def test_get_by_uuid(self, mock_api_get):

        mock_api_get.return_value = fake_segment

        segment_obj = (segment.FailoverSegment.
                       get_by_uuid(self.context, uuidsentinel.fake_segment))
        self.compare_obj(segment_obj, fake_segment)

        mock_api_get.assert_called_once_with(self.context,
                                             uuidsentinel.fake_segment)

    @mock.patch('masakari.db.failover_segment_get_by_id')
    def test_get_by_id(self, mock_api_get):

        mock_api_get.return_value = fake_segment
        fake_id = 123
        segment_obj = segment.FailoverSegment.get_by_id(self.context, fake_id)
        self.compare_obj(segment_obj, fake_segment)

        mock_api_get.assert_called_once_with(self.context, fake_id)

    def _segment_create_attribute(self):

        segment_obj = segment.FailoverSegment(context=self.context)
        segment_obj.name = 'foo-segment'
        segment_obj.description = 'keydata'
        segment_obj.service_type = 'fake-user'
        segment_obj.recovery_method = 'auto'
        segment_obj.uuid = uuidsentinel.fake_segment

        return segment_obj

    @mock.patch.object(api_utils, 'notify_about_segment_api')
    @mock.patch('masakari.db.failover_segment_create')
    def test_create(self, mock_segment_create, mock_notify_about_segment_api):
        mock_segment_create.return_value = fake_segment

        segment_obj = self._segment_create_attribute()
        segment_obj.create()
        self.compare_obj(segment_obj, fake_segment)

        mock_segment_create.assert_called_once_with(self.context, {
            'uuid': uuidsentinel.fake_segment, 'name': 'foo-segment',
            'description': 'keydata', 'service_type': 'fake-user',
            'recovery_method': 'auto'})
        action = fields.EventNotificationAction.SEGMENT_CREATE
        phase_start = fields.EventNotificationPhase.START
        phase_end = fields.EventNotificationPhase.END
        notify_calls = [
            mock.call(self.context, segment_obj, action=action,
                      phase=phase_start),
            mock.call(self.context, segment_obj, action=action,
                      phase=phase_end)]
        mock_notify_about_segment_api.assert_has_calls(notify_calls)

    @mock.patch.object(api_utils, 'notify_about_segment_api')
    @mock.patch('masakari.db.failover_segment_create')
    def test_recreate_fails(self, mock_segment_create,
                            mock_notify_about_segment_api):
        mock_segment_create.return_value = fake_segment

        segment_obj = self._segment_create_attribute()
        segment_obj.create()
        self.assertRaises(exception.ObjectActionError, segment_obj.create)

        mock_segment_create.assert_called_once_with(self.context, {
            'uuid': uuidsentinel.fake_segment, 'name': 'foo-segment',
            'description': 'keydata', 'service_type': 'fake-user',
            'recovery_method': 'auto'})
        action = fields.EventNotificationAction.SEGMENT_CREATE
        phase_start = fields.EventNotificationPhase.START
        phase_end = fields.EventNotificationPhase.END
        notify_calls = [
            mock.call(self.context, segment_obj, action=action,
                      phase=phase_start),
            mock.call(self.context, segment_obj, action=action,
                      phase=phase_end)]
        mock_notify_about_segment_api.assert_has_calls(notify_calls)

    @mock.patch.object(api_utils, 'notify_about_segment_api')
    @mock.patch('masakari.db.failover_segment_delete')
    def test_destroy(self, mock_segment_destroy,
                     mock_notify_about_segment_api):
        segment_obj = self._segment_create_attribute()
        segment_obj.id = 123
        segment_obj.destroy()

        mock_segment_destroy.assert_called_once_with(
            self.context, uuidsentinel.fake_segment)
        action = fields.EventNotificationAction.SEGMENT_DELETE
        phase_start = fields.EventNotificationPhase.START
        phase_end = fields.EventNotificationPhase.END
        notify_calls = [
            mock.call(self.context, segment_obj, action=action,
                      phase=phase_start),
            mock.call(self.context, segment_obj, action=action,
                      phase=phase_end)]
        mock_notify_about_segment_api.assert_has_calls(notify_calls)

    @mock.patch.object(api_utils, 'notify_about_segment_api')
    @mock.patch('masakari.db.failover_segment_delete')
    def test_destroy_failover_segment_found(self, mock_segment_destroy,
                                            mock_notify_about_segment_api):
        mock_segment_destroy.side_effect = exception.FailoverSegmentNotFound(
            id=123)
        segment_obj = self._segment_create_attribute()
        segment_obj.id = 123
        self.assertRaises(exception.FailoverSegmentNotFound,
                          segment_obj.destroy)
        action = fields.EventNotificationAction.SEGMENT_DELETE
        phase_start = fields.EventNotificationPhase.START
        notify_calls = [
            mock.call(self.context, segment_obj, action=action,
                      phase=phase_start)]
        mock_notify_about_segment_api.assert_has_calls(notify_calls)

    @mock.patch('masakari.db.failover_segment_get_all_by_filters')
    def test_get_segment_by_recovery_method(self, mock_api_get):
        fake_segment2 = copy.deepcopy(fake_segment)
        fake_segment2['name'] = 'fake_segment2'

        mock_api_get.return_value = [fake_segment2, fake_segment]

        segment_result = (segment.FailoverSegmentList.
                          get_all(self.context,
                                  filters={'recovery_method': 'auto'}))
        self.assertEqual(2, len(segment_result))
        self.compare_obj(segment_result[0], fake_segment2)
        self.compare_obj(segment_result[1], fake_segment)
        mock_api_get.assert_called_once_with(self.context, filters={
            'recovery_method': 'auto'
        }, limit=None, marker=None, sort_dirs=None, sort_keys=None)

    @mock.patch('masakari.db.failover_segment_get_all_by_filters')
    def test_get_segment_by_service_type(self, mock_api_get):
        fake_segment2 = copy.deepcopy(fake_segment)
        fake_segment2['name'] = 'fake_segment'

        mock_api_get.return_value = [fake_segment2, fake_segment]

        segment_result = (segment.FailoverSegmentList.
                          get_all(self.context,
                                  filters={'service_type': 'COMPUTE'}))
        self.assertEqual(2, len(segment_result))
        self.compare_obj(segment_result[0], fake_segment2)
        self.compare_obj(segment_result[1], fake_segment)
        mock_api_get.assert_called_once_with(self.context, filters={
            'service_type': 'COMPUTE'
        }, limit=None, marker=None, sort_dirs=None, sort_keys=None)

    @mock.patch('masakari.db.failover_segment_get_all_by_filters')
    def test_get_limit_and_marker_invalid_marker(self, mock_api_get):
        segment_name = 'unknown_segment'
        mock_api_get.side_effect = exception.MarkerNotFound(marker=segment_name
                                                            )

        self.assertRaises(exception.MarkerNotFound,
                          segment.FailoverSegmentList.get_all,
                          self.context, limit=5, marker=segment_name)

    @mock.patch.object(api_utils, 'notify_about_segment_api')
    @mock.patch('masakari.db.failover_segment_update')
    def test_save(self, mock_segment_update, mock_notify_about_segment_api):

        mock_segment_update.return_value = fake_segment

        segment_object = segment.FailoverSegment(context=self.context)
        segment_object.name = "foo-segment"
        segment_object.id = 123
        segment_object.uuid = uuidsentinel.fake_segment
        segment_object.save()

        self.compare_obj(segment_object, fake_segment)
        self.assertTrue(mock_segment_update.called)
        action = fields.EventNotificationAction.SEGMENT_UPDATE
        phase_start = fields.EventNotificationPhase.START
        phase_end = fields.EventNotificationPhase.END
        notify_calls = [
            mock.call(self.context, segment_object, action=action,
                      phase=phase_start),
            mock.call(self.context, segment_object, action=action,
                      phase=phase_end)]
        mock_notify_about_segment_api.assert_has_calls(notify_calls)

    @mock.patch.object(api_utils, 'notify_about_segment_api')
    @mock.patch('masakari.db.failover_segment_update')
    def test_save_failover_segment_not_found(self, mock_segment_update,
                                             mock_notify_about_segment_api):

        mock_segment_update.side_effect = (
            exception.FailoverSegmentNotFound(id=uuidsentinel.fake_segment))

        segment_object = segment.FailoverSegment(context=self.context)
        segment_object.name = "foo-segment"
        segment_object.id = 123
        segment_object.uuid = uuidsentinel.fake_segment

        self.assertRaises(exception.FailoverSegmentNotFound,
                          segment_object.save)
        action = fields.EventNotificationAction.SEGMENT_UPDATE
        phase_start = fields.EventNotificationPhase.START
        notify_calls = [
            mock.call(self.context, segment_object, action=action,
                      phase=phase_start)]
        mock_notify_about_segment_api.assert_has_calls(notify_calls)

    @mock.patch.object(api_utils, 'notify_about_segment_api')
    @mock.patch('masakari.db.failover_segment_update')
    def test_save_failover_segment_already_exists(self, mock_segment_update,
                                            mock_notify_about_segment_api):

        mock_segment_update.side_effect = (
            exception.FailoverSegmentExists(name="foo-segment"))

        segment_object = segment.FailoverSegment(context=self.context)
        segment_object.name = "foo-segment"
        segment_object.id = 123
        segment_object.uuid = uuidsentinel.fake_segment

        self.assertRaises(exception.FailoverSegmentExists, segment_object.save)
        action = fields.EventNotificationAction.SEGMENT_UPDATE
        phase_start = fields.EventNotificationPhase.START
        notify_calls = [
            mock.call(self.context, segment_object, action=action,
                      phase=phase_start)]
        mock_notify_about_segment_api.assert_has_calls(notify_calls)

    def test_obj_make_compatible(self):
        segment_obj = segment.FailoverSegment(context=self.context)
        segment_obj.name = "foo-segment"
        segment_obj.id = 123
        segment_obj.uuid = uuidsentinel.fake_segment
        segment_obj.enabled = True
        primitive = segment_obj.obj_to_primitive('1.1')
        self.assertIn('enabled', primitive['masakari_object.data'])
        primitive = segment_obj.obj_to_primitive('1.0')
        self.assertNotIn('enabled', primitive['masakari_object.data'])
