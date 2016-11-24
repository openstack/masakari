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

"""Tests for the failover segment api."""

import mock
from oslo_serialization import jsonutils
from webob import exc

from masakari.api.openstack.ha import segments
from masakari import exception
from masakari.ha import api as ha_api
from masakari.objects import base as obj_base
from masakari.objects import segment as segment_obj
from masakari import test
from masakari.tests.unit.api.openstack import fakes
from masakari.tests import uuidsentinel


def _make_segment_obj(segment_dict):
    return segment_obj.FailoverSegment(**segment_dict)


def _make_segments_list(segments_list):
    return segment_obj.FailoverSegment(objects=[
        _make_segment_obj(a) for a in segments_list])

FAILOVER_SEGMENT_LIST = [
    {"name": "segment1", "id": "1", "service_type": "COMPUTE",
     "recovery_method": "auto", "uuid": uuidsentinel.fake_segment,
     "description": "failover_segment for compute"},

    {"name": "segment2", "id": "2", "service_type": "CINDER",
     "recovery_method": "reserved_host", "uuid": uuidsentinel.fake_segment2,
     "description": "failover_segment for cinder"}
]

FAILOVER_SEGMENT_LIST = _make_segments_list(FAILOVER_SEGMENT_LIST)

FAILOVER_SEGMENT = {"name": "segment1", "id": "1",
                    "service_type": "COMPUTE", "recovery_method": "auto",
                    "uuid": uuidsentinel.fake_segment,
                    "description": "failover_segment for compute"}

FAILOVER_SEGMENT = _make_segment_obj(FAILOVER_SEGMENT)


class FailoverSegmentTestCase(test.NoDBTestCase):
    """Test Case for failover segment api."""

    bad_request = exception.ValidationError

    def setUp(self):
        super(FailoverSegmentTestCase, self).setUp()
        self.controller = segments.SegmentsController()
        self.req = fakes.HTTPRequest.blank('/v1/segments',
                                           use_admin_context=True)
        self.context = self.req.environ['masakari.context']

    @property
    def app(self):
        return fakes.wsgi_app_v1(init_only='segments')

    def _assert_segment_data(self, expected, actual):
        self.assertTrue(obj_base.obj_equal_prims(expected, actual),
                        "The failover segment objects were not equal")

    @mock.patch.object(ha_api.FailoverSegmentAPI, 'get_all')
    def test_index(self, mock_get_all):

        mock_get_all.return_value = FAILOVER_SEGMENT_LIST

        result = self.controller.index(self.req)
        result = result['segments']
        self._assert_segment_data(FAILOVER_SEGMENT_LIST,
                                  _make_segments_list(result))

    @mock.patch.object(ha_api.FailoverSegmentAPI, 'get_all')
    def test_index_marker_not_found(self, mock_get_all):
        fake_request = fakes.HTTPRequest.blank('/v1/segments?marker=12345',
                                               use_admin_context=True)
        mock_get_all.side_effect = exception.MarkerNotFound
        self.assertRaises(exc.HTTPBadRequest, self.controller.index,
                          fake_request)

    def test_get_all_marker_negative(self):

        fake_request = fakes.HTTPRequest.blank('/v1/segments?limit=-1',
                                               use_admin_context=True)
        self.assertRaises(exc.HTTPBadRequest, self.controller.index,
                          fake_request)

    def test_index_invalid_sort_key(self):

        req = fakes.HTTPRequest.blank('/v1/segments?sort_key=abcd',
                                      use_admin_context=True)
        self.assertRaises(exc.HTTPBadRequest, self.controller.index, req)

    def test_index_invalid_sort_dir(self):

        req = fakes.HTTPRequest.blank('/v1/segments?sort_dir=abcd',
                                      use_admin_context=True)
        self.assertRaises(exc.HTTPBadRequest, self.controller.index, req)

    @mock.patch.object(ha_api.FailoverSegmentAPI, 'create_segment')
    def test_create(self, mock_create):
        body = {
            "segment": {
                "name": "segment1",
                "service_type": "COMPUTE",
                "recovery_method": "auto",
                "description": "failover_segment for compute"
            }
        }
        mock_create.return_value = FAILOVER_SEGMENT
        result = self.controller.create(self.req, body=body)
        result = result['segment']
        self._assert_segment_data(FAILOVER_SEGMENT, _make_segment_obj(result))

    @mock.patch.object(ha_api.FailoverSegmentAPI, 'create_segment')
    def test_create_with_duplicate_segment_name(self, mock_create):
        body = {
            "segment": {
                "name": "segment1",
                "service_type": "COMPUTE",
                "recovery_method": "auto",
                "description": "failover_segment for compute"
            }
        }
        mock_create.side_effect = (exception.
                                   FailoverSegmentExists(name='segment1'))
        self.assertRaises(exc.HTTPConflict, self.controller.create,
                          self.req, body=body)

    @mock.patch('masakari.rpc.get_client')
    @mock.patch.object(ha_api.FailoverSegmentAPI, 'create_segment')
    def test_create_success_with_201_response_code(
        self, mock_client, mock_create):
        body = {
            "segment": {
                "name": "segment1",
                "service_type": "COMPUTE",
                "recovery_method": "auto",
                "description": "failover_segment for compute"
            }
        }
        fake_req = self.req
        fake_req.headers['Content-Type'] = 'application/json'
        fake_req.method = 'POST'
        fake_req.body = jsonutils.dump_as_bytes(body)
        resp = fake_req.get_response(self.app)
        self.assertEqual(201, resp.status_code)

    def test_create_with_no_segment(self):
        body = {
            "name": "segment1",
            "service_type": "COMPUTE",
            "recovery_method": "auto",
            "description": "failover_segment for compute"
        }
        self.assertRaises(self.bad_request, self.controller.create,
                          self.req, body=body)

    def test_create_with_no_name(self):
        body = {
            "segment": {
                "service_type": "COMPUTE",
                "recovery_method": "auto",
                "description": "failover_segment for compute"
            }
        }
        self.assertRaises(self.bad_request, self.controller.create,
                          self.req, body=body)

    def test_create_name_with_leading_trailing_spaces(self):
        body = {
            "segment": {
                "name": "    segment1    ",
                "service_type": "COMPUTE",
                "recovery_method": "auto",
                "description": "failover_segment for compute"
            }
        }
        self.assertRaises(self.bad_request, self.controller.create,
                          self.req, body=body)

    def test_create_with_null_name(self):
        body = {
            "segment": {
                "name": "",
                "service_type": "COMPUTE",
                "recovery_method": "auto",
                "description": "failover_segment for compute"
            }
        }
        self.assertRaises(self.bad_request, self.controller.create,
                          self.req, body=body)

    def test_create_with_name_too_long(self):
        body = {
            "segment": {
                "name": "segment1" * 255,
                "service_type": "COMPUTE",
                "recovery_method": "auto",
                "description": "failover_segment for compute"
            }
        }
        self.assertRaises(self.bad_request, self.controller.create,
                          self.req, body=body)

    def test_create_with_extra_invalid_arg(self):
        body = {
            "segment": {
                "name": "segment1" * 255,
                "service_type": "COMPUTE",
                "recovery_method": "auto",
                "description": "failover_segment for compute",
                "foo": "fake_foo"
            }
        }
        self.assertRaises(self.bad_request, self.controller.create,
                          self.req, body=body)

    @mock.patch.object(ha_api.FailoverSegmentAPI, 'get_segment')
    def test_show(self, mock_get_segment):

        mock_get_segment.return_value = FAILOVER_SEGMENT

        result = self.controller.show(self.req, uuidsentinel.fake_segment)
        result = result['segment']
        self._assert_segment_data(FAILOVER_SEGMENT, _make_segment_obj(result))

    @mock.patch.object(ha_api.FailoverSegmentAPI, 'get_segment')
    def test_show_with_non_existing_id(self, mock_get_segment):

        mock_get_segment.side_effect = exception.FailoverSegmentNotFound
        self.assertRaises(exc.HTTPNotFound,
                          self.controller.show, self.req, "2")

    @mock.patch.object(ha_api.FailoverSegmentAPI, 'update_segment')
    def test_update(self, mock_update_segment):

        mock_update_segment.return_value = FAILOVER_SEGMENT

        body = {"segment": {"name": "segment1", "service_type": "COMPUTE",
                            "recovery_method": "auto"}}

        result = self.controller.update(self.req, uuidsentinel.fake_segment,
                                        body=body)

        result = result['segment']
        self._assert_segment_data(FAILOVER_SEGMENT, _make_segment_obj(result))

    @mock.patch.object(ha_api.FailoverSegmentAPI, 'update_segment')
    def test_update_with_only_name(self, mock_update_segment):
        mock_update_segment.return_value = FAILOVER_SEGMENT

        body = {"segment": {"name": "segment1"}}

        result = self.controller.update(self.req, uuidsentinel.fake_segment,
                                        body=body)

        result = result['segment']
        self._assert_segment_data(FAILOVER_SEGMENT, _make_segment_obj(result))

    def test_update_with_no_updates(self):
        test_data = {"segment": {}}
        self.assertRaises(self.bad_request, self.controller.update,
                          self.req, uuidsentinel.fake_segment, body=test_data)

    def test_update_with_no_update_key(self):
        test_data = {"asdf": {}}
        self.assertRaises(self.bad_request, self.controller.update,
                          self.req, uuidsentinel.fake_segment, body=test_data)

    def test_update_with_wrong_updates(self):
        test_data = {"segment": {"name": "disable", "foo": "bar"}}
        self.assertRaises(self.bad_request, self.controller.update,
                          self.req, uuidsentinel.fake_segment, body=test_data)

    def test_update_with_null_name(self):
        test_metadata = {"segment": {"name": ""}}
        self.assertRaises(self.bad_request, self.controller.update,
                          self.req, uuidsentinel.fake_segment,
                          body=test_metadata)

    def test_update_with_name_too_long(self):
        test_metadata = {"segment": {"name": "x" * 256}}
        self.assertRaises(self.bad_request, self.controller.update,
                          self.req, uuidsentinel.fake_segment,
                          body=test_metadata)

    @mock.patch.object(ha_api.FailoverSegmentAPI, 'update_segment')
    def test_update_with_non_exising_segment(self, mock_update_segment):

        test_data = {"segment": {"name": "segment11"}}
        mock_update_segment.side_effect = exception.FailoverSegmentNotFound
        self.assertRaises(exc.HTTPNotFound, self.controller.update,
                self.req, "2", body=test_data)

    @mock.patch.object(ha_api.FailoverSegmentAPI, 'update_segment')
    def test_update_with_duplicated_name(self, mock_update_segment):
        test_data = {"segment": {"name": "segment1"}}
        mock_update_segment.side_effect = exception.FailoverSegmentExists
        self.assertRaises(exc.HTTPConflict, self.controller.update,
                self.req, uuidsentinel.fake_segment, body=test_data)

    @mock.patch.object(ha_api.FailoverSegmentAPI, 'delete_segment')
    def test_delete_segment(self, mock_delete):

        self.controller.delete(self.req, uuidsentinel.fake_segment)
        self.assertTrue(mock_delete.called)

    @mock.patch.object(ha_api.FailoverSegmentAPI, 'delete_segment')
    def test_delete_segment_not_found(self, mock_delete):

        mock_delete.side_effect = exception.FailoverSegmentNotFound
        self.assertRaises(exc.HTTPNotFound, self.controller.delete,
                self.req, uuidsentinel.fake_segment)

    @mock.patch('masakari.rpc.get_client')
    @mock.patch.object(ha_api.FailoverSegmentAPI, 'delete_segment')
    def test_delete_segment_with_204_status(self, mock_client, mock_delete):
        url = '/v1/segments/%s' % uuidsentinel.fake_segment
        fake_req = fakes.HTTPRequest.blank(url, use_admin_context=True)
        fake_req.headers['Content-Type'] = 'application/json'
        fake_req.method = 'DELETE'
        resp = fake_req.get_response(self.app)
        self.assertEqual(204, resp.status_code)


class FailoverSegmentTestCasePolicyNotAuthorized(test.NoDBTestCase):
    """Test Case for failover segment non admin."""

    def setUp(self):
        super(FailoverSegmentTestCasePolicyNotAuthorized, self).setUp()
        self.controller = segments.SegmentsController()
        self.req = fakes.HTTPRequest.blank('/v1/segments')
        self.context = self.req.environ['masakari.context']
        self.rule_name = "os_masakari_api:segments"
        self.policy.set_rules({self.rule_name: "project:non_fake"})

    def _check_rule(self, exc):
        self.assertEqual(
            "Policy doesn't allow %s to be performed." % self.rule_name,
            exc.format_message())

    def test_index_no_admin(self):
        exc = self.assertRaises(exception.PolicyNotAuthorized,
                                self.controller.index,
                                self.req)
        self._check_rule(exc)

    def test_create_no_admin(self):
        body = {
            "segment": {
                "name": "segment1",
                "service_type": "COMPUTE",
                "recovery_method": "auto",
                "description": "failover_segment for compute"
            }
        }
        exc = self.assertRaises(exception.PolicyNotAuthorized,
                                self.controller.create,
                                self.req, body=body)
        self._check_rule(exc)

    def test_show_no_admin(self):
        exc = self.assertRaises(exception.PolicyNotAuthorized,
                                self.controller.show,
                                self.req, uuidsentinel.fake_segment)
        self._check_rule(exc)

    def test_update_no_admin(self):
        body = {
            "segment": {
                "name": "segment1",
                "service_type": "COMPUTE",
                "recovery_method": "auto",
                "description": "failover_segment for compute"
            }
        }
        exc = self.assertRaises(exception.PolicyNotAuthorized,
                                self.controller.update,
                                self.req, uuidsentinel.fake_segment, body=body)
        self._check_rule(exc)

    def test_delete_no_admin(self):
        exc = self.assertRaises(exception.PolicyNotAuthorized,
                                self.controller.delete,
                                self.req, uuidsentinel.fake_segment)
        self._check_rule(exc)
