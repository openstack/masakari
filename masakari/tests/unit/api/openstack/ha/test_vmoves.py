# Copyright(c) 2022 Inspur
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for the vmoves api."""

from unittest import mock

import ddt
from webob import exc

from masakari.api.openstack.ha import vmoves
from masakari import exception
from masakari.ha import api as ha_api
from masakari.objects import base as obj_base
from masakari.objects import notification as notification_obj
from masakari.objects import vmove as vmove_obj
from masakari import test
from masakari.tests.unit.api.openstack import fakes
from masakari.tests.unit import fakes as fakes_data
from masakari.tests import uuidsentinel


def _make_vmove_obj(vmove_dict):
    return vmove_obj.VMove(**vmove_dict)


def _make_vmoves_list(vmove_list):
    return vmove_obj.VMove(objects=[
        _make_vmove_obj(a) for a in vmove_list])


@ddt.ddt
class VMoveTestCase(test.TestCase):
    """Test Case for vmove api."""

    bad_request = exception.ValidationError

    def _set_up(self):
        self.controller = vmoves.VMovesController()
        self.req = fakes.HTTPRequest.blank(
            '/v1/notifications/%s/vmoves' % (
                uuidsentinel.fake_notification1),
            use_admin_context=True)
        self.context = self.req.environ['masakari.context']

    def setUp(self):
        super(VMoveTestCase, self).setUp()
        self._set_up()
        self.host_type_notification = fakes_data.create_fake_notification(
            id=1,
            type="COMPUTE_HOST",
            source_host_uuid=uuidsentinel.fake_host_1,
            status="running",
            notification_uuid=uuidsentinel.fake_host_type_notification,
            payload={'event': 'STOPPED',
                     'host_status': 'NORMAL',
                     'cluster_status': 'ONLINE'}
        )
        self.vm_type_notification = fakes_data.create_fake_notification(
            id=1,
            type="VM",
            source_host_uuid=uuidsentinel.fake_host_2,
            status="running",
            notification_uuid=uuidsentinel.fake_vm_type_notification,
            payload={'event': 'STOPPED',
                     'host_status': 'NORMAL',
                     'cluster_status': 'ONLINE'}
        )
        self.vmove_1 = fakes_data.create_fake_vmove(
            id=1,
            uuid=uuidsentinel.fake_vmove_1,
            notification_uuid=self.host_type_notification.notification_uuid,
            instance_uuid=uuidsentinel.fake_instance_1,
            instance_name='vm-1',
            source_host='node01',
            dest_host='node02',
            start_time='2022-11-22 14:50:22',
            end_time="2022-11-22 14:50:35",
            type="evacuation",
            status='succeeded',
            message=None
        )
        self.vmove_2 = fakes_data.create_fake_vmove(
            id=1,
            uuid=uuidsentinel.fake_vmove_1,
            notification_uuid=self.host_type_notification.notification_uuid,
            instance_uuid=uuidsentinel.fake_instance_1,
            instance_name='vm-1',
            source_host='node01',
            dest_host='node02',
            start_time="2022-11-22 14:50:23",
            end_time="2022-11-22 14:50:38",
            type="evacuation",
            status='succeeded',
            message=None
        )
        self.vmove_list = [self.vmove_1, self.vmove_2]
        self.vmove_list_obj = _make_vmoves_list(self.vmove_list)

    @property
    def app(self):
        return fakes.wsgi_app_v1(init_only='vmoves')

    def _assert_vmove_data(self, expected, actual):
        self.assertTrue(obj_base.obj_equal_prims(expected, actual),
                        "The vmove objects were not equal")

    @mock.patch.object(notification_obj.Notification, 'get_by_uuid')
    @mock.patch.object(ha_api.VMoveAPI, 'get_all')
    def test_index(self, mock_get_all, mock_notification):
        mock_notification.return_value = mock.Mock()
        mock_get_all.return_value = self.vmove_list

        result = self.controller.index(
            self.req, uuidsentinel.fake_host_type_notification)
        result = result['vmoves']
        self._assert_vmove_data(self.vmove_list_obj,
                                _make_vmoves_list(result))

    @ddt.data('sort_key', 'sort_dir')
    @mock.patch.object(notification_obj.Notification, 'get_by_uuid',
                       return_value=mock.Mock())
    def test_index_invalid(self, sort_by, mock_notification):
        req = fakes.HTTPRequest.blank(
            '/v1/notifications/%s/vmoves?%s=abcd' % (
                uuidsentinel.fake_notification, sort_by),
            use_admin_context=True)
        self.assertRaises(exc.HTTPBadRequest, self.controller.index, req,
                          uuidsentinel.fake_notification1)

    @mock.patch.object(notification_obj.Notification, 'get_by_uuid')
    @mock.patch.object(ha_api.VMoveAPI, 'get_all')
    def test_index_with_valid_notification(self, mock_get_all,
            mock_notification):
        mock_notification.return_value = mock.Mock()
        mock_get_all.side_effect = exception.NotificationWithoutVMoves
        req = fakes.HTTPRequest.blank('/v1/notifications/%s/vmoves' % (
            uuidsentinel.fake_vm_type_notification), use_admin_context=True)
        self.assertRaises(exc.HTTPBadRequest, self.controller.index, req,
                          uuidsentinel.fake_notification1)

    @mock.patch.object(ha_api.VMoveAPI, 'get_vmove')
    def test_show(self, mock_get_vmove):
        mock_get_vmove.return_value = self.vmove_1
        result = self.controller.show(self.req,
                                      uuidsentinel.fake_notification1,
                                      uuidsentinel.fake_vmove_1)
        vmove = result['vmove']
        self._assert_vmove_data(self.vmove_1,
                                _make_vmove_obj(vmove))

    @mock.patch.object(ha_api.VMoveAPI, 'get_vmove')
    def test_show_with_non_existing_id(self, mock_get_vmove):
        mock_get_vmove.side_effect = exception.VMoveNotFound(id="2")
        self.assertRaises(exc.HTTPNotFound,
                          self.controller.show, self.req,
                          uuidsentinel.fake_notification1, "2")


class VMoveTestCasePolicyNotAuthorized(test.NoDBTestCase):
    """Test Case for vmove non admin."""

    def _set_up(self):
        self.controller = vmoves.VMovesController()
        self.req = fakes.HTTPRequest.blank(
            '/v1/notifications/%s/vmoves' % (
                uuidsentinel.fake_notification1))
        self.context = self.req.environ['masakari.context']

    def setUp(self):
        super(VMoveTestCasePolicyNotAuthorized, self).setUp()
        self._set_up()

    def _check_rule(self, exc, rule_name):
        self.assertEqual(
            "Policy doesn't allow %s to be performed." % rule_name,
            exc.format_message())

    def test_index_no_admin(self):
        rule_name = "os_masakari_api:vmoves:index"
        self.policy.set_rules({rule_name: "project:non_fake"})
        exc = self.assertRaises(exception.PolicyNotAuthorized,
                                self.controller.index,
                                self.req, uuidsentinel.fake_notification1)
        self._check_rule(exc, rule_name)

    def test_show_no_admin(self):
        rule_name = "os_masakari_api:vmoves:detail"
        self.policy.set_rules({rule_name: "project:non_fake"})
        exc = self.assertRaises(exception.PolicyNotAuthorized,
                                self.controller.show,
                                self.req, uuidsentinel.fake_notification1,
                                uuidsentinel.fake_vmove_1)
        self._check_rule(exc, rule_name)
