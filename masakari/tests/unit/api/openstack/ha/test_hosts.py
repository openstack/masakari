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

from http import HTTPStatus
from unittest import mock

import ddt
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
from masakari.tests.unit import fakes as fakes_data
from masakari.tests import uuidsentinel


def _make_host_obj(host_dict):
    return host_obj.Host(**host_dict)


def _make_hosts_list(hosts_list):
    return host_obj.Host(objects=[
        _make_host_obj(a) for a in hosts_list])


@ddt.ddt
class HostTestCase(test.TestCase):
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
        self.failover_segment = fakes_data.create_fake_failover_segment(
            name="segment1", id=1, description="failover_segment for compute",
            service_type="COMPUTE", recovery_method="auto",
            uuid=uuidsentinel.fake_segment
        )
        self.host = fakes_data.create_fake_host(
            name="host_1", id=1, reserved=False, on_maintenance=False,
            type="fake", control_attributes="fake-control_attributes",
            uuid=uuidsentinel.fake_host_1,
            failover_segment=self.failover_segment
        )
        self.host_2 = fakes_data.create_fake_host(
            name="host_2", id=2, reserved=False, on_maintenance=False,
            type="fake", control_attributes="fake-control_attributes",
            uuid=uuidsentinel.fake_host_2,
            failover_segment=self.failover_segment
        )
        self.host_list = [self.host, self.host_2]
        self.host_list_obj = _make_hosts_list(self.host_list)

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
        mock_get_all.return_value = self.host_list

        result = self.controller.index(self.req, uuidsentinel.fake_segment1)
        result = result['hosts']
        self._assert_host_data(self.host_list_obj, _make_hosts_list(result))

    @mock.patch.object(segment_obj.FailoverSegment, 'get_by_uuid')
    @mock.patch.object(ha_api.HostAPI, 'get_all')
    def test_index_valid_on_maintenance(self, mock_get_all, mock_segment):
        mock_segment.return_value = mock.Mock()

        self.host_list[0]['on_maintenance'] = True
        self.host_list[1]['on_maintenance'] = True
        mock_get_all.return_value = self.host_list
        for parameter in ['1', 't', 'true', 'on', 'y', 'yes']:
            req = fakes.HTTPRequest.blank(
                '/v1/segments/%s/hosts?on_maintenance=''%s' % (
                    uuidsentinel.fake_segment1, parameter),
                use_admin_context=True)
            result = self.controller.index(req, uuidsentinel.fake_segment1)
            self.assertIn('hosts', result)
            for host in result['hosts']:
                self.assertTrue(host['on_maintenance'])

        self.host_list[0]['on_maintenance'] = False
        self.host_list[1]['on_maintenance'] = False
        mock_get_all.return_value = self.host_list
        for parameter in ['0', 'f', 'false', 'off', 'n', 'no']:
            req = fakes.HTTPRequest.blank(
                '/v1/segments/%s/hosts?on_maintenance=''%s' % (
                    uuidsentinel.fake_segment1, parameter),
                use_admin_context=True)
            result = self.controller.index(req, uuidsentinel.fake_segment1)
            self.assertIn('hosts', result)
            for host in result['hosts']:
                self.assertFalse(host['on_maintenance'])

    @mock.patch.object(segment_obj.FailoverSegment, 'get_by_uuid',
                       return_value=mock.Mock())
    def test_index_invalid_on_maintenance(self, mock_segment):

        req = fakes.HTTPRequest.blank('/v1/segments/%s/hosts?on_maintenance='
                                      'abcd' % uuidsentinel.fake_segment1,
                                      use_admin_context=True)
        self.assertRaises(exc.HTTPBadRequest, self.controller.index, req,
                          uuidsentinel.fake_segment1)

    @mock.patch.object(segment_obj.FailoverSegment, 'get_by_uuid')
    @mock.patch.object(ha_api.HostAPI, 'get_all')
    def test_index_valid_reserved(self, mock_get_all, mock_segment):
        self.host_list[0]['reserved'] = True
        self.host_list[1]['reserved'] = True
        mock_get_all.return_value = self.host_list
        for parameter in ['1', 't', 'true', 'on', 'y', 'yes']:
            req = fakes.HTTPRequest.blank(
                '/v1/segments/%s/hosts?reserved=''%s' % (
                    uuidsentinel.fake_segment1, parameter
                ), use_admin_context=True)
            result = self.controller.index(req, uuidsentinel.fake_segment1)
            self.assertIn('hosts', result)
            for host in result['hosts']:
                self.assertTrue(host['reserved'])

        self.host_list[0]['reserved'] = False
        self.host_list[1]['reserved'] = False
        mock_get_all.return_value = self.host_list
        for parameter in ['0', 'f', 'false', 'off', 'n', 'no']:
            req = fakes.HTTPRequest.blank(
                '/v1/segments/%s/hosts?reserved=''%s' % (
                    uuidsentinel.fake_segment1, parameter),
                use_admin_context=True)
            result = self.controller.index(req, uuidsentinel.fake_segment1)
            self.assertIn('hosts', result)
            for host in result['hosts']:
                self.assertFalse(host['reserved'])

    @mock.patch.object(segment_obj.FailoverSegment, 'get_by_uuid',
                       return_value=mock.Mock())
    def test_index_invalid_reserved(self, mock_segment):

        req = fakes.HTTPRequest.blank('/v1/segments/%s/hosts?reserved='
                                      'abcd' % uuidsentinel.fake_segment1,
                                      use_admin_context=True)
        self.assertRaises(exc.HTTPBadRequest, self.controller.index, req,
                          uuidsentinel.fake_segment1)

    @mock.patch.object(segment_obj.FailoverSegment, 'get_by_uuid')
    @mock.patch.object(ha_api.HostAPI, 'get_all')
    def test_index_marker_not_found(self, mock_get_all, mock_segment):
        req = fakes.HTTPRequest.blank('/v1/segments/%s/hosts?marker=123456' % (
            uuidsentinel.fake_segment1), use_admin_context=True)
        mock_segment.return_value = mock.Mock()
        mock_get_all.side_effect = exception.MarkerNotFound(marker="123456")
        self.assertRaises(exc.HTTPBadRequest, self.controller.index,
                          req, uuidsentinel.fake_segment1)

    def test_get_all_marker_negative(self):

        req = fakes.HTTPRequest.blank('/v1/segments/%s/hosts?limit=-1' % (
            uuidsentinel.fake_segment1), use_admin_context=True)
        self.assertRaises(exc.HTTPBadRequest, self.controller.index,
                          req, uuidsentinel.fake_segment1)

    @ddt.data('sort_key', 'sort_dir')
    @mock.patch.object(segment_obj.FailoverSegment, 'get_by_uuid',
                       return_value=mock.Mock())
    def test_index_invalid(self, sort_by, mock_segment):
        req = fakes.HTTPRequest.blank('/v1/segments/%s/hosts?%s=abcd' % (
            uuidsentinel.fake_segment1, sort_by), use_admin_context=True)
        self.assertRaises(exc.HTTPBadRequest, self.controller.index, req,
                          uuidsentinel.fake_segment1)

    @ddt.data([exception.MarkerNotFound(marker="123456"),
               "/v1/segments/%s/hosts?marker=123456", exc.HTTPBadRequest],
              [exception.FailoverSegmentNotFound(
                  id=uuidsentinel.fake_segment1), "/v1/segments/%s/hosts",
                  exc.HTTPNotFound])
    @ddt.unpack
    @mock.patch.object(segment_obj.FailoverSegment, 'get_by_uuid')
    @mock.patch.object(ha_api.HostAPI, 'get_all')
    def test_index_not_found(self, masakari_exc, url, exc, mock_get_all,
                             mock_segment):
        mock_segment.return_value = mock.Mock()
        mock_get_all.side_effect = masakari_exc

        req = fakes.HTTPRequest.blank(url % uuidsentinel.fake_segment1,
                                      use_admin_context=True)
        self.assertRaises(exc, self.controller.index, req,
                          uuidsentinel.fake_segment1)

    @mock.patch.object(ha_api.HostAPI, 'create_host')
    def test_create(self, mock_create):
        mock_create.return_value = self.host
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
        self._assert_host_data(self.host, _make_host_obj(result))

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
        self.assertEqual(HTTPStatus.CREATED, resp.status_code)

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

    @ddt.data(
        # no_host
        {"body": {
            "name": "host-1", "type": "fake",
            "reserved": False,
            "on_maintenance": False,
            "control_attributes": "fake-control_attributes"}},

        # no_name
        {"body": {
            "host": {
                "type": "fake",
                "reserved": False,
                "on_maintenance": False,
                "control_attributes": "fake-control_attributes"}}},

        # name_with_leading_trailing_spaces
        {"body": {
            "host": {
                "name": " host-1 ", "type": "fake",
                "reserved": False,
                "on_maintenance": False,
                "control_attributes": "fake-control_attributes"}}},

        # null_name
        {"body": {
            "host": {
                "name": "", "type": "fake",
                "reserved": False,
                "on_maintenance": False,
                "control_attributes": "fake-control_attributes"}}},

        # name_too_long
        {"body": {
            "host": {
                "name": "host-1" * 255, "type": "fake",
                "reserved": False,
                "on_maintenance": False,
                "control_attributes": "fake-control_attributes"}}},

        # extra_invalid_arg
        {"body": {
            "host": {
                "name": "host-1", "type": "fake",
                "reserved": False,
                "on_maintenance": False,
                "control_attributes": "fake-control_attributes",
                "foo": "bar"}}},

        # type too long
        {"body": {
            "host": {
                "name": "host-1", "type": "x" * 256,
                "reserved": False,
                "on_maintenance": False,
                "control_attributes": "fake-control_attributes"}}},

        # type special characters
        {"body": {
            "host": {
                "name": "host-1", "type": "x_y",
                "reserved": False,
                "on_maintenance": False,
                "control_attributes": "fake-control_attributes"}}}
    )
    @ddt.unpack
    def test_create_failure(self, body):
        self.assertRaises(self.bad_request, self.controller.create,
                          self.req, uuidsentinel.fake_segment1, body=body)

    @mock.patch.object(ha_api.HostAPI, 'get_host')
    def test_show(self, mock_get_host):

        mock_get_host.return_value = self.host

        result = self.controller.show(self.req, uuidsentinel.fake_segment1,
                                      uuidsentinel.fake_host_1)
        result = result['host']
        self._assert_host_data(self.host, _make_host_obj(result))

    @mock.patch.object(ha_api.HostAPI, 'get_host')
    def test_show_with_non_existing_id(self, mock_get_host):

        mock_get_host.side_effect = exception.HostNotFound(id="2")
        self.assertRaises(exc.HTTPNotFound,
                          self.controller.show, self.req,
                          uuidsentinel.fake_segment1, "2")

    @mock.patch.object(ha_api.HostAPI, 'get_host')
    def test_show_non_assigned_failover_segment(self, mock_get_host):

        mock_get_host.side_effect = exception.HostNotFoundUnderFailoverSegment(
            host_uuid=uuidsentinel.fake_host_3,
            segment_uuid=uuidsentinel.fake_segment1)
        self.assertRaises(exc.HTTPNotFound, self.controller.show,
                          self.req, uuidsentinel.fake_segment1,
                          uuidsentinel.fake_host_3)

    @ddt.data(
        {"body": {
            "host": {
                "name": "host-1", "type": "fake", "reserved": False,
                "on_maintenance": False,
                "control_attributes": "fake-control_attributes"}}},

        # only name
        {"body": {"host": {"name": "host-1"}}}
    )
    @ddt.unpack
    @mock.patch.object(ha_api.HostAPI, 'update_host')
    def test_update(self, mock_update_host, body):
        mock_update_host.return_value = self.host

        result = self.controller.update(self.req, uuidsentinel.fake_segment1,
                                        uuidsentinel.fake_host_1,
                                        body=body)

        result = result['host']
        self._assert_host_data(self.host, _make_host_obj(result))

    @ddt.data(
        # no updates
        {"test_data": {"host": {}}},

        # no update key
        {"test_data": {"asdf": {}}},

        # wrong updates
        {"test_data": {"host": {"name": "disable", "foo": "bar"}}},

        # null name
        {"test_data": {"host": {"name": ""}}},

        # name too long
        {"test_data": {"host": {"name": "x" * 256}}},

        # type too long
        {"test_data": {"host": {"type": "x" * 256}}},

        # type with special characters
        {"test_data": {"host": {"type": "x_y"}}}
    )
    @ddt.unpack
    def test_update_failure(self, test_data):
        self.assertRaises(self.bad_request, self.controller.update,
                          self.req, uuidsentinel.fake_segment1,
                          uuidsentinel.fake_host_1, body=test_data)

    @mock.patch.object(ha_api.HostAPI, 'update_host')
    def test_update_with_non_exising_host(self, mock_update_host):

        test_data = {"host": {"name": "host11"}}
        mock_update_host.side_effect = exception.HostNotFound(id="2")
        self.assertRaises(exc.HTTPNotFound, self.controller.update,
                self.req, uuidsentinel.fake_segment1, "2", body=test_data)

    @mock.patch.object(ha_api.HostAPI, 'update_host')
    def test_update_with_duplicated_name(self, mock_update_host):
        test_data = {"host": {"name": "host-1"}}
        mock_update_host.side_effect = exception.HostExists(name="host-1")
        self.assertRaises(exc.HTTPConflict, self.controller.update,
                self.req, uuidsentinel.fake_segment1,
                          uuidsentinel.fake_host_1, body=test_data)

    @mock.patch.object(ha_api.HostAPI, 'update_host')
    def test_update_non_assigned_failover_segment(self, mock_update_host):
        test_data = {"host": {"name": "host-1"}}
        mock_update_host.side_effect = \
            exception.HostNotFoundUnderFailoverSegment(
                host_uuid=uuidsentinel.fake_host_3,
                segment_uuid=uuidsentinel.fake_segment1)
        self.assertRaises(exc.HTTPNotFound, self.controller.update,
                          self.req, uuidsentinel.fake_segment1,
                          uuidsentinel.fake_host_3, body=test_data)

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
        self.assertEqual(HTTPStatus.NO_CONTENT, resp.status_code)

    @mock.patch.object(ha_api.HostAPI, 'delete_host')
    def test_delete_host_not_found(self, mock_delete):

        mock_delete.side_effect = exception.HostNotFound(id="2")
        self.assertRaises(exc.HTTPNotFound, self.controller.delete,
                self.req, uuidsentinel.fake_segment1,
                          uuidsentinel.fake_host_3)

    @mock.patch.object(ha_api.HostAPI, 'delete_host')
    def test_delete_host_not_found_for_failover_segment(self, mock_delete):

        mock_delete.side_effect = exception.HostNotFoundUnderFailoverSegment(
            host_uuid=uuidsentinel.fake_host_3,
            segment_uuid=uuidsentinel.fake_segment1)
        self.assertRaises(exc.HTTPNotFound, self.controller.delete,
                self.req, uuidsentinel.fake_segment1,
                          uuidsentinel.fake_host_3)


class HostTestCasePolicyNotAuthorized(test.NoDBTestCase):
    """Test Case for host non admin."""

    def _set_up(self):
        self.controller = hosts.HostsController()
        self.req = fakes.HTTPRequest.blank(
            '/v1/segments/%s/hosts' % uuidsentinel.fake_segment1)
        self.context = self.req.environ['masakari.context']

    def setUp(self):
        super(HostTestCasePolicyNotAuthorized, self).setUp()
        self._set_up()

    def _check_rule(self, exc, rule_name):
        self.assertEqual(
            "Policy doesn't allow %s to be performed." % rule_name,
            exc.format_message())

    def test_index_no_admin(self):
        rule_name = "os_masakari_api:os-hosts:index"
        self.policy.set_rules({rule_name: "project:non_fake"})
        exc = self.assertRaises(exception.PolicyNotAuthorized,
                                self.controller.index,
                                self.req, uuidsentinel.fake_segment1)
        self._check_rule(exc, rule_name)

    def test_create_no_admin(self):
        rule_name = "os_masakari_api:os-hosts:create"
        self.policy.set_rules({rule_name: "project:non_fake"})
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
        self._check_rule(exc, rule_name)

    def test_show_no_admin(self):
        rule_name = "os_masakari_api:os-hosts:detail"
        self.policy.set_rules({rule_name: "project:non_fake"})
        exc = self.assertRaises(exception.PolicyNotAuthorized,
                                self.controller.show,
                                self.req, uuidsentinel.fake_segment1,
                                uuidsentinel.fake_host_1)
        self._check_rule(exc, rule_name)

    def test_update_no_admin(self):
        rule_name = "os_masakari_api:os-hosts:update"
        self.policy.set_rules({rule_name: "project:non_fake"})
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
        self._check_rule(exc, rule_name)

    def test_delete_no_admin(self):
        rule_name = "os_masakari_api:os-hosts:delete"
        self.policy.set_rules({rule_name: "project:non_fake"})
        exc = self.assertRaises(exception.PolicyNotAuthorized,
                                self.controller.delete,
                                self.req, uuidsentinel.fake_segment1,
                                uuidsentinel.fake_host_1)
        self._check_rule(exc, rule_name)
