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

import mock
from testtools import matchers

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
