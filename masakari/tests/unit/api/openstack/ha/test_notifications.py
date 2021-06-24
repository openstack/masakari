# Copyright (c) 2016 NTT DATA
# All Rights Reserved.
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

"""Tests for the notifications api."""

import copy
from http import HTTPStatus
from unittest import mock

import ddt
from oslo_serialization import jsonutils
from oslo_utils import timeutils
from webob import exc

from masakari.api.openstack.ha import notifications
from masakari.engine import rpcapi as engine_rpcapi
from masakari import exception
from masakari.ha import api as ha_api
from masakari.objects import base as obj_base
from masakari.objects import fields
from masakari.objects import notification as notification_obj
from masakari import test
from masakari.tests.unit.api.openstack import fakes
from masakari.tests.unit.objects import test_objects
from masakari.tests import uuidsentinel

NOW = timeutils.utcnow().replace(microsecond=0)
OPTIONAL = ['recovery_workflow_details']


def _make_notification_obj(notification_dict):
    return notification_obj.Notification(**notification_dict)


def _make_notification_progress_details_obj(progress_details):
    return notification_obj.NotificationProgressDetails(**progress_details)


def _make_notifications_list(notifications_list):
    return notification_obj.Notification(objects=[
        _make_notification_obj(a) for a in notifications_list])


NOTIFICATION_DATA = {"type": "VM", "id": 1,
                     "payload":
                         {'event': 'STOPPED', 'host_status': 'NORMAL',
                          'cluster_status': 'ONLINE'},
                     "source_host_uuid": uuidsentinel.fake_host,
                     "generated_time": NOW,
                     "status": "running",
                     "notification_uuid": uuidsentinel.fake_notification,
                     "created_at": NOW,
                     "updated_at": None,
                     "deleted_at": None,
                     "deleted": 0
                     }

NOTIFICATION = _make_notification_obj(NOTIFICATION_DATA)

RECOVERY_DETAILS = {"progress": 1.0,
                    "state": "SUCCESS",
                    "name": "StopInstanceTask",
                    "progress_details": [
                        {"timestamp": "2019-03-07 13:54:28",
                         "message": "Stopping instance",
                         "progress": "0.0"},
                    ]}

NOTI_DATA_WITH_DETAILS = copy.deepcopy(NOTIFICATION_DATA)

NOTIFICATION_WITH_PROGRESS_DETAILS = _make_notification_obj(
    NOTI_DATA_WITH_DETAILS)
RECOVERY_OBJ = _make_notification_progress_details_obj(RECOVERY_DETAILS)
NOTIFICATION_WITH_PROGRESS_DETAILS.recovery_workflow_details = [RECOVERY_OBJ]

NOTIFICATION_LIST = [
    {"type": "VM", "id": 1, "payload": {'event': 'STOPPED',
                                        'host_status': 'NORMAL',
                                        'cluster_status': 'ONLINE'},
     "source_host_uuid": uuidsentinel.fake_host, "generated_time": NOW,
     "status": "running", "notification_uuid": uuidsentinel.fake_notification,
     "created_at": NOW, "updated_at": None, "deleted_at": None, "deleted": 0},

    {"type": "PROCESS", "id": 2, "payload": {'event': 'STOPPED',
                                             'process_name': 'fake_process'},
     "source_host_uuid": uuidsentinel.fake_host_1, "generated_time": NOW,
     "status": "running", "notification_uuid": uuidsentinel.fake_notification1,
     "created_at": NOW, "updated_at": None, "deleted_at": None, "deleted": 0},
]

NOTIFICATION_LIST = _make_notifications_list(NOTIFICATION_LIST)


@ddt.ddt
class NotificationTestCase(test.TestCase):
    """Test Case for notifications api."""

    bad_request = exception.ValidationError

    @mock.patch.object(engine_rpcapi, 'EngineAPI')
    def setUp(self, mock_rpc):
        super(NotificationTestCase, self).setUp()
        self.controller = notifications.NotificationsController()
        self.req = fakes.HTTPRequest.blank('/v1/notifications',
                                           use_admin_context=True)
        self.context = self.req.environ['masakari.context']

    @property
    def app(self):
        return fakes.wsgi_app_v1(init_only='os-hosts')

    def _assert_notification_data(self, expected, actual):
        self.assertTrue(obj_base.obj_equal_prims(expected, actual),
                        "The notifications objects were not equal")

    @mock.patch.object(ha_api.NotificationAPI, 'get_all')
    def test_index(self, mock_get_all):

        mock_get_all.return_value = NOTIFICATION_LIST

        result = self.controller.index(self.req)
        result = result['notifications']
        self._assert_notification_data(NOTIFICATION_LIST,
                                       _make_notifications_list(result))

    @ddt.data(
        # limit negative
        "limit=-1",

        # invalid sort key
        "sort_key=abcd",

        # invalid sort dir
        "sort_dir=abcd")
    def test_index_invalid(self, param):
        req = fakes.HTTPRequest.blank("/v1/notifications?%s" % param,
                                      use_admin_context=True)

        self.assertRaises(exc.HTTPBadRequest, self.controller.index, req)

    @mock.patch.object(ha_api.NotificationAPI, 'get_all')
    def test_index_marker_not_found(self, mock_get_all):
        fake_request = fakes.HTTPRequest.blank('/v1/notifications?marker=1234',
                                               use_admin_context=True)
        mock_get_all.side_effect = exception.MarkerNotFound(marker="1234")
        self.assertRaises(exc.HTTPBadRequest, self.controller.index,
                          fake_request)

    def test_index_invalid_generated_since(self):

        req = fakes.HTTPRequest.blank('/v1/notifications?generated-since=abcd',
                                      use_admin_context=True)
        self.assertRaises(exc.HTTPBadRequest, self.controller.index, req)

    @mock.patch.object(ha_api.NotificationAPI, 'get_all')
    def test_index_valid_generated_since(self, mock_get_all):
        url = '/v1/notifications?generated-since=%s' % str(NOW)
        req = fakes.HTTPRequest.blank(url, use_admin_context=True)
        mock_get_all.return_value = NOTIFICATION_LIST
        result = self.controller.index(req)
        result = result['notifications']
        self._assert_notification_data(NOTIFICATION_LIST,
                                       _make_notifications_list(result))

    @mock.patch.object(ha_api.NotificationAPI, 'create_notification')
    def test_create(self, mock_create):

        mock_create.return_value = NOTIFICATION
        result = self.controller.create(self.req, body={
            "notification": {
                "hostname": "fake_host",
                "payload": {
                    "instance_uuid": uuidsentinel.instance_uuid,
                    "vir_domain_event": "STOPPED_FAILED",
                    "event": "LIFECYCLE"
                },
                "type": "VM",
                "generated_time": "2016-09-13T09:11:21.656788"}})
        result = result['notification']
        test_objects.compare_obj(self, result, NOTIFICATION_DATA,
                                 allow_missing=OPTIONAL)

    @mock.patch.object(ha_api.NotificationAPI, 'create_notification')
    def test_create_process_notification(self, mock_create):
        mock_create.return_value = NOTIFICATION
        result = self.controller.create(self.req, body={
            "notification": {
                "hostname": "fake_host",
                "payload": {
                    "process_name": "nova-compute",
                    "event": "STOPPED"
                },
                "type": "PROCESS",
                "generated_time": "2016-09-13T09:11:21.656788"}})
        result = result['notification']
        test_objects.compare_obj(self, result, NOTIFICATION_DATA,
                                 allow_missing=OPTIONAL)

    @mock.patch('masakari.rpc.get_client')
    @mock.patch.object(ha_api.NotificationAPI, 'create_notification')
    def test_create_success_with_201_response_code(
        self, mock_client, mock_create):
        body = {
            "notification": {
                "hostname": "fake_host",
                "payload": {
                    "instance_uuid": uuidsentinel.instance_uuid,
                    "vir_domain_event": "STOPPED_FAILED",
                    "event": "LIFECYCLE"
                },
                "type": "VM",
                "generated_time": NOW
            }
        }
        fake_req = self.req
        fake_req.headers['Content-Type'] = 'application/json'
        fake_req.method = 'POST'
        fake_req.body = jsonutils.dump_as_bytes(body)
        resp = fake_req.get_response(self.app)
        self.assertEqual(HTTPStatus.ACCEPTED, resp.status_code)

    @mock.patch.object(ha_api.NotificationAPI, 'create_notification')
    def test_create_host_not_found(self, mock_create):
        body = {
            "notification": {
                "hostname": "fake_host",
                "payload": {
                    "instance_uuid": uuidsentinel.instance_uuid,
                    "vir_domain_event": "STOPPED_FAILED",
                    "event": "LIFECYCLE"
                },
                "type": "VM",
                "generated_time": "2016-09-13T09:11:21.656788"
            }
        }
        mock_create.side_effect = exception.HostNotFoundByName(
            host_name="fake_host")
        self.assertRaises(exc.HTTPBadRequest, self.controller.create,
                          self.req, body=body)

    @ddt.data(
        # invalid type
        {"body": {
            "notification": {"hostname": "fake_host",
                             "payload": {"event": "STOPPED",
                                         "host_status": "NORMAL",
                                         "cluster_status": "ONLINE"},
                             "type": "Fake",
                             "generated_time": "2016-09-13T09:11:21.656788"}}},

        # no notification in body
        {"body": {"hostname": "fake_host",
                  "payload": {"event": "STOPPED",
                              "host_status": "NORMAL",
                              "cluster_status": "ONLINE"},
                  "type": "VM",
                  "generated_time": "2016-09-13T09:11:21.656788"}},

        # no payload
        {"body": {"notification": {"hostname": "fake_host",
                                   "type": "VM",
                                   "generated_time":
                                       "2016-09-13T09:11:21.656788"}}},

        # no hostname
        {"body": {"notification": {"payload": {"event": "STOPPED",
                                               "host_status": "NORMAL",
                                               "cluster_status": "ONLINE"},
                                   "type": "VM",
                                   "generated_time":
                                       "2016-09-13T09:11:21.656788"}}},

        # no type
        {"body": {"notification": {"hostname": "fake_host",
                                   "payload": {"event": "STOPPED",
                                               "host_status": "NORMAL",
                                               "cluster_status": "ONLINE"},
                                   "generated_time":
                                       "2016-09-13T09:11:21.656788"}}},

        # no generated time
        {"body": {"notification": {"hostname": "fake_host",
                                   "payload": {"event": "STOPPED",
                                               "host_status": "NORMAL",
                                               "cluster_status": "ONLINE"},
                                   "type": "VM",
                                   }}},

        # hostname too long
        {"body": {
            "notification": {"hostname": "fake_host" * 255,
                             "payload": {"event": "STOPPED",
                                         "host_status": "NORMAL",
                                         "cluster_status": "ONLINE"},
                             "type": "VM",
                             "generated_time": "2016-09-13T09:11:21.656788"}}},

        # extra invalid args
        {"body": {
            "notification": {"hostname": "fake_host",
                             "payload": {"event": "STOPPED",
                                         "host_status": "NORMAL",
                                         "cluster_status": "ONLINE"},
                             "type": "VM",
                             "generated_time": "2016-09-13T09:11:21.656788",
                             "invalid_extra": "non_expected_parameter"}}}
    )
    @ddt.unpack
    def test_create_failure(self, body):
        self.assertRaises(self.bad_request, self.controller.create,
                          self.req, body=body)

    @ddt.data(
        # invalid event for PROCESS type
        {"params": {"payload": {"event": "invalid",
                                "process_name": "nova-compute"},
                    "type": fields.NotificationType.PROCESS}},

        # invalid event for VM type
        {"params": {"payload": {"event": "invalid",
                                "host_status": fields.HostStatusType.NORMAL,
                          "cluster_status": fields.ClusterStatusType.ONLINE},
                    "type": fields.NotificationType.VM}},

        # invalid event for HOST_COMPUTE type
        {"params": {"payload": {"event": "invalid"},
                    "type": fields.NotificationType.COMPUTE_HOST}},

        # empty payload
        {"params": {"payload": {},
                    "type": fields.NotificationType.COMPUTE_HOST}},

        # empty process_name
        {"params": {"payload": {"event": fields.EventType.STOPPED,
                                "process_name": ""},
                    "type": fields.NotificationType.PROCESS}},

        # process_name too long value
        {"params": {"payload": {"event": fields.EventType.STOPPED,
                              "process_name": "a" * 4097},
                  "type": fields.NotificationType.PROCESS}},

        # process_name invalid data_type
        {"params": {"payload": {"event": fields.EventType.STOPPED,
                              "process_name": 123},
                  "type": fields.NotificationType.PROCESS}}
    )
    @ddt.unpack
    def test_create_with_invalid_payload(self, params):
        body = {
            "notification": {"hostname": "fake_host",
                             "generated_time": "2016-09-13T09:11:21.656788"
                             }
        }

        body['notification']['payload'] = params['payload']
        body['notification']['type'] = params['type']
        self.assertRaises(self.bad_request, self.controller.create,
                          self.req, body=body)

    @mock.patch.object(ha_api.NotificationAPI, 'create_notification')
    def test_create_duplicate_notification(self, mock_create_notification):
        mock_create_notification.side_effect = exception.DuplicateNotification(
            type="COMPUTE_HOST")
        body = {
            "notification": {"hostname": "fake_host",
                             "payload": {"event": "STOPPED",
                                         "host_status": "NORMAL",
                                         "cluster_status": "ONLINE"},
                             "type": "COMPUTE_HOST",
                             "generated_time": str(NOW)}}
        self.assertRaises(exc.HTTPConflict, self.controller.create,
                          self.req, body=body)

    @mock.patch.object(ha_api.NotificationAPI, 'create_notification')
    def test_create_host_on_maintenance(self, mock_create_notification):
        mock_create_notification.side_effect = (
            exception.HostOnMaintenanceError(host_name="fake_host"))
        body = {
            "notification": {"hostname": "fake_host",
                             "payload": {"event": "STOPPED",
                                         "host_status": "NORMAL",
                                         "cluster_status": "ONLINE"},
                             "type": "COMPUTE_HOST",
                             "generated_time": str(NOW)}}
        self.assertRaises(exc.HTTPConflict, self.controller.create,
                          self.req, body=body)

    @mock.patch.object(ha_api.NotificationAPI, 'get_notification')
    def test_show(self, mock_get_notification):

        mock_get_notification.return_value = NOTIFICATION

        result = self.controller.show(self.req, uuidsentinel.fake_notification)
        result = result['notification']
        self._assert_notification_data(NOTIFICATION,
                                       _make_notification_obj(result))

    @mock.patch.object(ha_api.NotificationAPI, 'get_notification')
    def test_show_with_non_existing_uuid(self, mock_get_notification):

        mock_get_notification.side_effect = exception.NotificationNotFound(
            id="2")
        self.assertRaises(exc.HTTPNotFound,
                          self.controller.show, self.req, "2")

    @ddt.data('DELETE', 'PUT')
    @mock.patch('masakari.rpc.get_client')
    def test_delete_and_update_notification(self, method, mock_client):
        url = '/v1/notifications/%s' % uuidsentinel.fake_notification
        fake_req = fakes.HTTPRequest.blank(url, use_admin_context=True)
        fake_req.headers['Content-Type'] = 'application/json'
        fake_req.method = method
        resp = fake_req.get_response(self.app)
        self.assertEqual(HTTPStatus.METHOD_NOT_ALLOWED, resp.status_code)


class NotificationCasePolicyNotAuthorized(test.NoDBTestCase):
    """Test Case for notifications non admin."""

    @mock.patch.object(engine_rpcapi, 'EngineAPI')
    def setUp(self, mock_rpc):
        super(NotificationCasePolicyNotAuthorized, self).setUp()
        self.controller = notifications.NotificationsController()
        self.req = fakes.HTTPRequest.blank('/v1/notifications')
        self.context = self.req.environ['masakari.context']

    def _check_rule(self, exc, rule_name):
        self.assertEqual(
            "Policy doesn't allow %s to be performed." % rule_name,
            exc.format_message())

    def test_create_no_admin(self):
        rule_name = "os_masakari_api:notifications:create"
        self.policy.set_rules({rule_name: "project:non_fake"})
        body = {
            "notification": {"hostname": "fake_host",
                             "payload": {"event": "STOPPED",
                                         "host_status": "NORMAL",
                                         "cluster_status": "ONLINE"},
                             "type": "VM",
                             "generated_time": "2016-09-13T09:11:21.656788"}}
        exc = self.assertRaises(exception.PolicyNotAuthorized,
                                self.controller.create,
                                self.req, body=body)
        self._check_rule(exc, rule_name)

    def test_show_no_admin(self):
        rule_name = "os_masakari_api:notifications:detail"
        self.policy.set_rules({rule_name: "project:non_fake"})
        exc = self.assertRaises(exception.PolicyNotAuthorized,
                                self.controller.show,
                                self.req, uuidsentinel.fake_notification)
        self._check_rule(exc, rule_name)

    def test_index_no_admin(self):
        rule_name = "os_masakari_api:notifications:index"
        self.policy.set_rules({rule_name: "project:non_fake"})
        exc = self.assertRaises(exception.PolicyNotAuthorized,
                                self.controller.index,
                                self.req)
        self._check_rule(exc, rule_name)


class NotificationV1_1_TestCase(NotificationTestCase):
    """Test Case for notifications api for 1.1 API"""
    api_version = '1.1'

    @mock.patch.object(engine_rpcapi, 'EngineAPI')
    def setUp(self, mock_rpc):
        super(NotificationV1_1_TestCase, self).setUp()
        self.controller = notifications.NotificationsController()
        self.req = fakes.HTTPRequest.blank('/v1/notifications',
                                           use_admin_context=True,
                                           version=self.api_version)
        self.context = self.req.environ['masakari.context']

    @mock.patch.object(ha_api.NotificationAPI,
                       'get_notification_recovery_workflow_details')
    def test_show(self, mock_get_notification_recovery_workflow_details):
        (mock_get_notification_recovery_workflow_details
         .return_value) = NOTIFICATION_WITH_PROGRESS_DETAILS

        result = self.controller.show(self.req, uuidsentinel.fake_notification)
        result = result['notification']
        self.assertCountEqual([RECOVERY_OBJ],
                              result.recovery_workflow_details)
        self._assert_notification_data(NOTIFICATION_WITH_PROGRESS_DETAILS,
                                       _make_notification_obj(result))
