# Copyright 2016 NTT DATA
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

"""
Test suites for 'common' code used throughout the OpenStack HTTP API.
"""

from testtools import matchers
from unittest import mock

import webob

from masakari.api.openstack import common
from masakari import test
from masakari.tests.unit.api.openstack import fakes
from masakari.tests import uuidsentinel


class MiscFunctionsTest(test.TestCase):

    def test_remove_trailing_version_from_href(self):
        fixture = 'http://www.testsite.com/v1.1'
        expected = 'http://www.testsite.com'
        actual = common.remove_trailing_version_from_href(fixture)
        self.assertEqual(actual, expected)

    def test_remove_trailing_version_from_href_2(self):
        fixture = 'http://www.testsite.com/ha/v1.1'
        expected = 'http://www.testsite.com/ha'
        actual = common.remove_trailing_version_from_href(fixture)
        self.assertEqual(actual, expected)

    def test_remove_trailing_version_from_href_3(self):
        fixture = 'http://www.testsite.com/v1.1/images/v10.5'
        expected = 'http://www.testsite.com/v1.1/images'
        actual = common.remove_trailing_version_from_href(fixture)
        self.assertEqual(actual, expected)

    def test_remove_trailing_version_from_href_bad_request(self):
        fixture = 'http://www.testsite.com/v1.1/images'
        self.assertRaises(ValueError,
                          common.remove_trailing_version_from_href,
                          fixture)

    def test_remove_trailing_version_from_href_bad_request_2(self):
        fixture = 'http://www.testsite.com/images/v'
        self.assertRaises(ValueError,
                          common.remove_trailing_version_from_href,
                          fixture)

    def test_remove_trailing_version_from_href_bad_request_3(self):
        fixture = 'http://www.testsite.com/v1.1images'
        self.assertRaises(ValueError,
                          common.remove_trailing_version_from_href,
                          fixture)


class TestCollectionLinks(test.NoDBTestCase):
    """Tests the _get_collection_links method."""

    @mock.patch('masakari.api.openstack.common.ViewBuilder._get_next_link')
    def test_items_less_than_limit(self, href_link_mock):
        items = [
            {"uuid": "123"}
        ]
        req = mock.MagicMock()
        params = mock.PropertyMock(return_value=dict(limit=10))
        type(req).params = params

        builder = common.ViewBuilder()
        results = builder._get_collection_links(req, items, "ignored", "uuid")

        self.assertFalse(href_link_mock.called)
        self.assertThat(results, matchers.HasLength(0))

    @mock.patch('masakari.api.openstack.common.ViewBuilder._get_next_link')
    def test_items_equals_given_limit(self, href_link_mock):
        items = [
            {"uuid": "123"}
        ]
        req = mock.MagicMock()
        params = mock.PropertyMock(return_value=dict(limit=1))
        type(req).params = params

        builder = common.ViewBuilder()
        results = builder._get_collection_links(req, items,
                                                mock.sentinel.coll_key,
                                                "uuid")

        href_link_mock.assert_called_once_with(req, "123",
                                               mock.sentinel.coll_key)
        self.assertThat(results, matchers.HasLength(1))

    @mock.patch('masakari.api.openstack.common.ViewBuilder._get_next_link')
    def test_items_equals_default_limit(self, href_link_mock):
        items = [
            {"uuid": "123"}
        ]
        req = mock.MagicMock()
        params = mock.PropertyMock(return_value=dict())
        type(req).params = params
        self.flags(osapi_max_limit=1)

        builder = common.ViewBuilder()
        results = builder._get_collection_links(req, items,
                                                mock.sentinel.coll_key,
                                                "uuid")

        href_link_mock.assert_called_once_with(req, "123",
                                               mock.sentinel.coll_key)
        self.assertThat(results, matchers.HasLength(1))

    @mock.patch('masakari.api.openstack.common.ViewBuilder._get_next_link')
    def test_items_equals_default_limit_with_given(self, href_link_mock):
        items = [
            {"uuid": "123"}
        ]
        req = mock.MagicMock()
        # Given limit is greater than default max, only return default max
        params = mock.PropertyMock(return_value=dict(limit=2))
        type(req).params = params
        self.flags(osapi_max_limit=1)

        builder = common.ViewBuilder()
        results = builder._get_collection_links(req, items,
                                                mock.sentinel.coll_key,
                                                "uuid")

        href_link_mock.assert_called_once_with(req, "123",
                                               mock.sentinel.coll_key)
        self.assertThat(results, matchers.HasLength(1))


class LinkPrefixTest(test.NoDBTestCase):

    def test_update_link_prefix(self):
        vb = common.ViewBuilder()
        result = vb._update_link_prefix("http://192.168.0.243:24/",
                                        "http://127.0.0.1/ha")
        self.assertEqual("http://127.0.0.1/ha", result)

        result = vb._update_link_prefix("http://foo.x.com/v1",
                                        "http://new.prefix.com")
        self.assertEqual("http://new.prefix.com/v1", result)

        result = vb._update_link_prefix("http://foo.x.com/v1",
                                        "http://new.prefix.com:20455/"
                                        "new_extra_prefix")
        self.assertEqual("http://new.prefix.com:20455/new_extra_prefix/v1",
                         result)


class UrlJoinTest(test.NoDBTestCase):
    def test_url_join(self):
        pieces = ["one", "two", "three"]
        joined = common.url_join(*pieces)
        self.assertEqual("one/two/three", joined)

    def test_url_join_extra_slashes(self):
        pieces = ["one/", "/two//", "/three/"]
        joined = common.url_join(*pieces)
        self.assertEqual("one/two/three", joined)

    def test_url_join_trailing_slash(self):
        pieces = ["one", "two", "three", ""]
        joined = common.url_join(*pieces)
        self.assertEqual("one/two/three/", joined)

    def test_url_join_empty_list(self):
        pieces = []
        joined = common.url_join(*pieces)
        self.assertEqual("", joined)

    def test_url_join_single_empty_string(self):
        pieces = [""]
        joined = common.url_join(*pieces)
        self.assertEqual("", joined)

    def test_url_join_single_slash(self):
        pieces = ["/"]
        joined = common.url_join(*pieces)
        self.assertEqual("", joined)


class ViewBuilderLinkTest(test.NoDBTestCase):
    project_id = uuidsentinel.fake_project_id
    api_version = "1.0"

    def setUp(self):
        super(ViewBuilderLinkTest, self).setUp()
        self.request = self.req("/%s" % self.project_id)
        self.vb = common.ViewBuilder()

    def req(self, url, use_admin_context=False):
        return fakes.HTTPRequest.blank(url,
                use_admin_context=use_admin_context, version=self.api_version)

    def test_get_project_id(self):
        proj_id = self.vb._get_project_id(self.request)
        self.assertEqual(self.project_id, proj_id)

    def test_get_next_link(self):
        identifier = "identifier"
        collection = "collection"
        next_link = self.vb._get_next_link(self.request, identifier,
                                           collection)
        expected = "/".join((self.request.url,
                             "%s?marker=%s" % (collection, identifier)))
        self.assertEqual(expected, next_link)

    def test_get_href_link(self):
        identifier = "identifier"
        collection = "collection"
        href_link = self.vb._get_href_link(self.request, identifier,
                                           collection)
        expected = "/".join((self.request.url, collection, identifier))
        self.assertEqual(expected, href_link)

    def test_get_bookmark_link(self):
        identifier = "identifier"
        collection = "collection"
        bookmark_link = self.vb._get_bookmark_link(self.request, identifier,
                                                   collection)
        bmk_url = (
            common.remove_trailing_version_from_href((
                self.request.application_url)))
        expected = "/".join((bmk_url, self.project_id, collection, identifier))
        self.assertEqual(expected, bookmark_link)


class PaginationParamsTest(test.NoDBTestCase):
    """Unit tests for the `masakari.api.openstack.common.get_pagination_params`
    method which takes in a request object and returns 'marker' and 'limit'
    GET params.
    """

    def test_no_params(self):
        # Test no params.
        req = webob.Request.blank('/')
        self.assertEqual(common.get_pagination_params(req), {})

    def test_valid_marker(self):
        # Test valid marker param.
        req = webob.Request.blank('/?marker=263abb28-1de6-412f-b00'
                                  'b-f0ee0c4333c2')
        self.assertEqual(common.get_pagination_params(req),
                         {'marker': '263abb28-1de6-412f-b00b-f0ee0c4333c2'})

    def test_valid_limit(self):
        # Test valid limit param.
        req = webob.Request.blank('/?limit=10')
        self.assertEqual(common.get_pagination_params(req), {'limit': 10})

    def test_invalid_limit(self):
        # Test invalid limit param.
        req = webob.Request.blank('/?limit=-2')
        self.assertRaises(
            webob.exc.HTTPBadRequest, common.get_pagination_params, req)

    def test_valid_limit_and_marker(self):
        # Test valid limit and marker parameters.
        marker = '263abb28-1de6-412f-b00b-f0ee0c4333c2'
        req = webob.Request.blank('/?limit=20&marker=%s' % marker)
        self.assertEqual(common.get_pagination_params(req),
                         {'marker': marker, 'limit': 20})

    def test_valid_page_size(self):
        # Test valid page_size param.
        req = webob.Request.blank('/?page_size=10')
        self.assertEqual(common.get_pagination_params(req),
                         {'page_size': 10})

    def test_invalid_page_size(self):
        # Test invalid page_size param.
        req = webob.Request.blank('/?page_size=-2')
        self.assertRaises(
            webob.exc.HTTPBadRequest, common.get_pagination_params, req)

    def test_valid_limit_and_page_size(self):
        # Test valid limit and page_size parameters.
        req = webob.Request.blank('/?limit=20&page_size=5')
        self.assertEqual(common.get_pagination_params(req),
                         {'page_size': 5, 'limit': 20})


class SortParamTest(test.NoDBTestCase):

    def test_get_sort_params_defaults(self):
        # Verifies the default sort key and direction.
        sort_keys, sort_dirs = common.get_sort_params({})
        self.assertEqual(['created_at'], sort_keys)
        self.assertEqual(['desc'], sort_dirs)

    def test_get_sort_params_override_defaults(self):
        # Verifies that the defaults can be overriden.
        sort_keys, sort_dirs = common.get_sort_params({}, default_key='key1',
                                                      default_dir='dir1')
        self.assertEqual(['key1'], sort_keys)
        self.assertEqual(['dir1'], sort_dirs)

        sort_keys, sort_dirs = common.get_sort_params({}, default_key=None,
                                                      default_dir=None)
        self.assertEqual([], sort_keys)
        self.assertEqual([], sort_dirs)

    def test_get_sort_params_single_value(self):
        # Verifies a single sort key and direction.
        params = webob.multidict.MultiDict()
        params.add('sort_key', 'key1')
        params.add('sort_dir', 'dir1')
        sort_keys, sort_dirs = common.get_sort_params(params)
        self.assertEqual(['key1'], sort_keys)
        self.assertEqual(['dir1'], sort_dirs)

    def test_get_sort_params_single_with_default(self):
        # Verifies a single sort value with a default.
        params = webob.multidict.MultiDict()
        params.add('sort_key', 'key1')
        sort_keys, sort_dirs = common.get_sort_params(params)
        self.assertEqual(['key1'], sort_keys)
        # sort_key was supplied, sort_dir should be defaulted
        self.assertEqual(['desc'], sort_dirs)

        params = webob.multidict.MultiDict()
        params.add('sort_dir', 'dir1')
        sort_keys, sort_dirs = common.get_sort_params(params)
        self.assertEqual(['created_at'], sort_keys)
        # sort_dir was supplied, sort_key should be defaulted
        self.assertEqual(['dir1'], sort_dirs)

    def test_get_sort_params_multiple_values(self):
        # Verifies multiple sort parameter values.
        params = webob.multidict.MultiDict()
        params.add('sort_key', 'key1')
        params.add('sort_key', 'key2')
        params.add('sort_key', 'key3')
        params.add('sort_dir', 'dir1')
        params.add('sort_dir', 'dir2')
        params.add('sort_dir', 'dir3')
        sort_keys, sort_dirs = common.get_sort_params(params)
        self.assertEqual(['key1', 'key2', 'key3'], sort_keys)
        self.assertEqual(['dir1', 'dir2', 'dir3'], sort_dirs)
        # Also ensure that the input parameters are not modified
        sort_key_vals = []
        sort_dir_vals = []
        while 'sort_key' in params:
            sort_key_vals.append(params.pop('sort_key'))
        while 'sort_dir' in params:
            sort_dir_vals.append(params.pop('sort_dir'))
        self.assertEqual(['key1', 'key2', 'key3'], sort_key_vals)
        self.assertEqual(['dir1', 'dir2', 'dir3'], sort_dir_vals)
        self.assertEqual(0, len(params))
