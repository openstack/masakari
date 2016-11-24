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

"""Tests for the hosts api."""

import mock
from oslo_serialization import jsonutils
from webob import exc

from masakari.api.openstack.ha import hosts
from masakari import exception
from masakari.ha import api as ha_api
from masakari.objects import base as obj_base
from masakari.objects import host as host_obj
from masakari.objects import segment as segment_obj
from masakari import test
from masakari.tests.unit.api.openstack import fakes
from masakari.tests import uuidsentinel


def _make_host_obj(host_dict):
    return host_obj.Host(**host_dict)


def _make_hosts_list(hosts_list):
    return host_obj.Host(objects=[
        _make_host_obj(a) for a in hosts_list])

HOST_LIST = [
    {"name": "host_1", "id": "1", "reserved": False,
     "on_maintenance": False, "type": "fake",
     "control_attributes": "fake-control_attributes",
     "uuid": uuidsentinel.fake_host_1,
     "failover_segment_id": uuidsentinel.fake_segment1},

    {"name": "host_2", "id": "2", "reserved": False,
     "on_maintenance": False, "type": "fake",
     "control_attributes": "fake-control_attributes",
     "uuid": uuidsentinel.fake_host_2,
     "failover_segment_id": uuidsentinel.fake_segment1}
]

HOST_LIST = _make_hosts_list(HOST_LIST)

HOST = {
    "name": "host_1", "id": "1", "reserved": False,
    "on_maintenance": False, "type": "fake",
    "control_attributes": "fake-control_attributes",
    "uuid": uuidsentinel.fake_host_1,
    "failover_segment_id": uuidsentinel.fake_segment1
}

HOST = _make_host_obj(HOST)


class HostTestCase(test.NoDBTestCase):
    """Test Case for host api."""

    bad_request = exception.ValidationError

    def _set_up(self):
        self.controller = hosts.HostsController()
        self.req = fakes.HTTPRequest.blank(
            '/v1/segments/%s/hosts' % uuidsentinel.fake_segment1,
            use_admin_context=True)
        self.context = self.req.environ['masakari.context']

    def setUp(self):
        super(HostTestCase, self).setUp()
        self._set_up()

    @property
    def app(self):
        return fakes.wsgi_app_v1(init_only='os-hosts')

    def _assert_host_data(self, expected, actual):
        self.assertTrue(obj_base.obj_equal_prims(expected, actual),
                        "The host objects were not equal")

    @mock.patch.object(segment_obj.FailoverSegment, 'get_by_uuid')
    @mock.patch.object(ha_api.HostAPI, 'get_all')
    def test_index(self, mock_get_all, mock_segment):
        mock_segment.return_value = mock.Mock()
        mock_get_all.return_value = HOST_LIST

        result = self.controller.index(self.req, uuidsentinel.fake_segment1)
        result = result['hosts']
        self._assert_host_data(HOST_LIST, _make_hosts_list(result))

    @mock.patch.object(segment_obj.FailoverSegment, 'get_by_uuid')
    @mock.patch.object(ha_api.HostAPI, 'get_all')
    def test_index_marker_not_found(self, mock_get_all, mock_segment):
        req = fakes.HTTPRequest.blank('/v1/segments/%s/hosts?marker=123456' % (
            uuidsentinel.fake_segment1), use_admin_context=True)
        mock_segment.return_value = mock.Mock()
        mock_get_all.side_effect = exception.MarkerNotFound
        self.assertRaises(exc.HTTPBadRequest, self.controller.index,
                          req, uuidsentinel.fake_segment1)

    def test_get_all_marker_negative(self):

        req = fakes.HTTPRequest.blank('/v1/segments/%s/hosts?limit=-1' % (
            uuidsentinel.fake_segment1), use_admin_context=True)
        self.assertRaises(exc.HTTPBadRequest, self.controller.index,
                          req, uuidsentinel.fake_segment1)

    @mock.patch.object(segment_obj.FailoverSegment, 'get_by_uuid',
                       return_value=mock.Mock())
    def test_index_invalid_sort_key(self, mock_segment):

        req = fakes.HTTPRequest.blank('/v1/segments/%s/hosts?sort_key=abcd' % (
            uuidsentinel.fake_segment1), use_admin_context=True)
        self.assertRaises(exc.HTTPBadRequest, self.controller.index, req,
                          uuidsentinel.fake_segment1)

    @mock.patch.object(segment_obj.FailoverSegment, 'get_by_uuid',
                       return_value=mock.Mock())
    def test_index_invalid_sort_dir(self, mock_segment):

        req = fakes.HTTPRequest.blank('/v1/segments/%s/hosts?sort_dir=abcd' % (
            uuidsentinel.fake_segment1), use_admin_context=True)
        self.assertRaises(exc.HTTPBadRequest, self.controller.index, req,
                          uuidsentinel.fake_segment1)

    @mock.patch.object(segment_obj.FailoverSegment, 'get_by_uuid')
    @mock.patch.object(ha_api.HostAPI, 'get_all')
    def test_index_failover_segment_not_found(self, mock_get_all,
                                              mock_segment):
        mock_segment.return_value = mock.Mock()
        mock_get_all.side_effect = exception.FailoverSegmentNotFound
        self.assertRaises(exc.HTTPNotFound, self.controller.index,
                          self.req, uuidsentinel.fake_segment1)

    @mock.patch.object(ha_api.HostAPI, 'create_host')
    def test_create(self, mock_create):
        mock_create.return_value = HOST
        body = {
            "host": {
                "name": "host-1", "type": "fake",
                "reserved": False,
                "on_maintenance": False,
                "control_attributes": "fake-control_attributes"
            }
        }
        result = self.controller.create(self.req,
                                        uuidsentinel.fake_segment1, body=body)
        result = result['host']
        self._assert_host_data(HOST, _make_host_obj(result))

    @mock.patch('masakari.rpc.get_client')
    @mock.patch.object(ha_api.HostAPI, 'create_host')
    def test_create_success_with_201_response_code(
        self, mock_client, mock_create):
        body = {
            "host": {
                "name": "host-1", "type": "fake",
                "reserved": False,
                "on_maintenance": False,
                "control_attributes": "fake-control_attributes"
            }
        }
        fake_req = self.req
        fake_req.headers['Content-Type'] = 'application/json'
        fake_req.method = 'POST'
        fake_req.body = jsonutils.dump_as_bytes(body)
        resp = fake_req.get_response(self.app)
        self.assertEqual(201, resp.status_code)

    @mock.patch.object(ha_api.HostAPI, 'create_host')
    def test_create_with_duplicate_host_name(self, mock_create):

        mock_create.side_effect = (exception.
                                   HostExists(name='host-1'))
        body = {
            "host": {
                "name": "host-1", "type": "fake",
                "reserved": False,
                "on_maintenance": False,
                "control_attributes": "fake-control_attributes"
            }
        }
        self.assertRaises(exc.HTTPConflict, self.controller.create,
                          self.req, uuidsentinel.fake_segment1, body=body)

    def test_create_with_no_host(self):
        body = {
            "name": "host-1", "type": "fake",
            "reserved": False,
            "on_maintenance": False,
            "control_attributes": "fake-control_attributes"
        }
        self.assertRaises(self.bad_request, self.controller.create,
                          self.req, uuidsentinel.fake_segment1, body=body)

    def test_create_with_no_name(self):
        body = {
            "host": {
                "type": "fake",
                "reserved": False,
                "on_maintenance": False,
                "control_attributes": "fake-control_attributes"
            }
        }
        self.assertRaises(self.bad_request, self.controller.create,
                          self.req, uuidsentinel.fake_segment1, body=body)

    def test_create_name_with_leading_trailing_spaces(self):
        body = {
            "host": {
                "name": " host-1 ", "type": "fake",
                "reserved": False,
                "on_maintenance": False,
                "control_attributes": "fake-control_attributes"
            }
        }
        self.assertRaises(self.bad_request, self.controller.create,
                          self.req, uuidsentinel.fake_segment1, body=body)

    def test_create_with_null_name(self):
        body = {
            "host": {
                "name": "", "type": "fake",
                "reserved": False,
                "on_maintenance": False,
                "control_attributes": "fake-control_attributes"
            }
        }
        self.assertRaises(self.bad_request, self.controller.create,
                          self.req, uuidsentinel.fake_segment1, body=body)

    def test_create_with_name_too_long(self):
        body = {
            "host": {
                "name": "host-1" * 255, "type": "fake",
                "reserved": False,
                "on_maintenance": False,
                "control_attributes": "fake-control_attributes"
            }
        }
        self.assertRaises(self.bad_request, self.controller.create,
                          self.req, uuidsentinel.fake_segment1, body=body)

    def test_create_with_extra_invalid_arg(self):
        body = {
            "host": {
                "name": "host-1", "type": "fake",
                "reserved": False,
                "on_maintenance": False,
                "control_attributes": "fake-control_attributes",
                "foo": "bar"
            }
        }
        self.assertRaises(self.bad_request, self.controller.create,
                          self.req, uuidsentinel.fake_segment1, body=body)

    @mock.patch.object(ha_api.HostAPI, 'get_host')
    def test_show(self, mock_get_host):

        mock_get_host.return_value = HOST

        result = self.controller.show(self.req, uuidsentinel.fake_segment1,
                                      uuidsentinel.fake_host_1)
        result = result['host']
        self._assert_host_data(HOST, _make_host_obj(result))

    @mock.patch.object(ha_api.HostAPI, 'get_host')
    def test_show_with_non_existing_id(self, mock_get_host):

        mock_get_host.side_effect = exception.HostNotFound
        self.assertRaises(exc.HTTPNotFound,
                          self.controller.show, self.req,
                          uuidsentinel.fake_segment1, "2")

    @mock.patch.object(ha_api.HostAPI, 'update_host')
    def test_update(self, mock_update_host):

        mock_update_host.return_value = HOST

        body = {
            "host": {
                "name": "host-1", "type": "fake", "reserved": False,
                "on_maintenance": False,
                "control_attributes": "fake-control_attributes"
            }
        }

        result = self.controller.update(self.req, uuidsentinel.fake_segment1,
                                        uuidsentinel.fake_host_1,
                                        body=body)

        result = result['host']
        self._assert_host_data(HOST, _make_host_obj(result))

    @mock.patch.object(ha_api.HostAPI, 'update_host')
    def test_update_with_only_name(self, mock_update_host):
        mock_update_host.return_value = HOST

        body = {"host": {"name": "host-1"}}

        result = self.controller.update(self.req, uuidsentinel.fake_segment1,
                                        uuidsentinel.fake_host_1,
                                        body=body)

        result = result['host']
        self._assert_host_data(HOST, _make_host_obj(result))

    def test_update_with_no_updates(self):
        test_data = {"host": {}}
        self.assertRaises(self.bad_request, self.controller.update,
                          self.req, uuidsentinel.fake_segment1,
                          uuidsentinel.fake_host_1, body=test_data)

    def test_update_with_no_update_key(self):
        test_data = {"asdf": {}}
        self.assertRaises(self.bad_request, self.controller.update,
                          self.req, uuidsentinel.fake_segment1,
                          uuidsentinel.fake_host_1, body=test_data)

    def test_update_with_wrong_updates(self):
        test_data = {"host": {"name": "disable", "foo": "bar"}}
        self.assertRaises(self.bad_request, self.controller.update,
                          self.req, uuidsentinel.fake_segment1,
                          uuidsentinel.fake_host_1, body=test_data)

    def test_update_with_null_name(self):
        test_metadata = {"host": {"name": ""}}
        self.assertRaises(self.bad_request, self.controller.update,
                          self.req, uuidsentinel.fake_segment1,
                          uuidsentinel.fake_host_1, body=test_metadata)

    def test_update_with_name_too_long(self):
        test_metadata = {"host": {"name": "x" * 256}}
        self.assertRaises(self.bad_request, self.controller.update,
                          self.req, uuidsentinel.fake_segment1,
                          uuidsentinel.fake_host_1, body=test_metadata)

    @mock.patch.object(ha_api.HostAPI, 'update_host')
    def test_update_with_non_exising_host(self, mock_update_host):

        test_data = {"host": {"name": "host11"}}
        mock_update_host.side_effect = exception.HostNotFound
        self.assertRaises(exc.HTTPNotFound, self.controller.update,
                self.req, uuidsentinel.fake_segment1, "2", body=test_data)

    @mock.patch.object(ha_api.HostAPI, 'update_host')
    def test_update_with_duplicated_name(self, mock_update_host):
        test_data = {"host": {"name": "host-1"}}
        mock_update_host.side_effect = exception.HostExists
        self.assertRaises(exc.HTTPConflict, self.controller.update,
                self.req, uuidsentinel.fake_segment1,
                          uuidsentinel.fake_host_1, body=test_data)

    @mock.patch.object(ha_api.HostAPI, 'delete_host')
    def test_delete_host(self, mock_delete):

        self.controller.delete(self.req, uuidsentinel.fake_segment1,
                               uuidsentinel.fake_host_1)
        self.assertTrue(mock_delete.called)

    @mock.patch('masakari.rpc.get_client')
    @mock.patch.object(ha_api.HostAPI, 'delete_host')
    def test_delete_host_with_204_status(self, mock_client, mock_delete):
        url = '/v1/segments/%(segment)s/hosts/%(host)s' % {
            'segment': uuidsentinel.fake_segment1,
            'host': uuidsentinel.fake_host_1
        }
        fake_req = fakes.HTTPRequest.blank(url, use_admin_context=True)
        fake_req.headers['Content-Type'] = 'application/json'
        fake_req.method = 'DELETE'
        resp = fake_req.get_response(self.app)
        self.assertEqual(204, resp.status_code)

    @mock.patch.object(ha_api.HostAPI, 'delete_host')
    def test_delete_host_not_found(self, mock_delete):

        mock_delete.side_effect = exception.HostNotFound
        self.assertRaises(exc.HTTPNotFound, self.controller.delete,
                self.req, uuidsentinel.fake_segment1,
                          uuidsentinel.fake_host_3)

    def test_create_with_type_too_long(self):
        body = {
            "host": {
                "name": "host-1", "type": "x" * 256,
                "reserved": False,
                "on_maintenance": False,
                "control_attributes": "fake-control_attributes"
            }
        }
        self.assertRaises(self.bad_request, self.controller.create,
                          self.req, uuidsentinel.fake_segment1, body=body)

    def test_create_with_type_special_characters(self):
        body = {
            "host": {
                "name": "host-1", "type": "x_y",
                "reserved": False,
                "on_maintenance": False,
                "control_attributes": "fake-control_attributes"
            }
        }
        self.assertRaises(self.bad_request, self.controller.create,
                          self.req, uuidsentinel.fake_segment1, body=body)

    def test_update_with_type_too_long(self):
        test_metadata = {"host": {"type": "x" * 256}}
        self.assertRaises(self.bad_request, self.controller.update,
                          self.req, uuidsentinel.fake_segment1,
                          uuidsentinel.fake_host_1, body=test_metadata)

    def test_update_with_type_special_characters(self):
        test_metadata = {"host": {"type": "x_y"}}
        self.assertRaises(self.bad_request, self.controller.update,
                          self.req, uuidsentinel.fake_segment1,
                          uuidsentinel.fake_host_1, body=test_metadata)


class HostTestCasePolicyNotAuthorized(test.NoDBTestCase):
    """Test Case for host non admin."""

    def _set_up(self):
        self.controller = hosts.HostsController()
        self.req = fakes.HTTPRequest.blank(
            '/v1/segments/%s/hosts' % uuidsentinel.fake_segment1)
        self.context = self.req.environ['masakari.context']
        self.rule_name = "os_masakari_api:os-hosts"
        self.policy.set_rules({self.rule_name: "project:non_fake"})

    def setUp(self):
        super(HostTestCasePolicyNotAuthorized, self).setUp()
        self._set_up()

    def _check_rule(self, exc):
        self.assertEqual(
            "Policy doesn't allow %s to be performed." % self.rule_name,
            exc.format_message())

    def test_index_no_admin(self):
        exc = self.assertRaises(exception.PolicyNotAuthorized,
                                self.controller.index,
                                self.req, uuidsentinel.fake_segment1)
        self._check_rule(exc)

    def test_create_no_admin(self):
        body = {
            "host": {
                "name": "host-1", "type": "fake", "reserved": False,
                "on_maintenance": False,
                "control_attributes": "fake-control_attributes"
            }
        }
        exc = self.assertRaises(exception.PolicyNotAuthorized,
                                self.controller.create,
                                self.req, uuidsentinel.fake_segment1,
                                body=body)
        self._check_rule(exc)

    def test_show_no_admin(self):
        exc = self.assertRaises(exception.PolicyNotAuthorized,
                                self.controller.show,
                                self.req, uuidsentinel.fake_segment1,
                                uuidsentinel.fake_host_1)
        self._check_rule(exc)

    def test_update_no_admin(self):
        body = {
            "host": {
                "name": "host-1", "type": "fake", "reserved": False,
                "on_maintenance": False,
                "control_attributes": "fake-control_attributes",
            }
        }
        exc = self.assertRaises(exception.PolicyNotAuthorized,
                                self.controller.update,
                                self.req, uuidsentinel.fake_segment1,
                                uuidsentinel.fake_host_1, body=body)
        self._check_rule(exc)

    def test_delete_no_admin(self):
        exc = self.assertRaises(exception.PolicyNotAuthorized,
                                self.controller.delete,
                                self.req, uuidsentinel.fake_segment1,
                                uuidsentinel.fake_host_1)
        self._check_rule(exc)
