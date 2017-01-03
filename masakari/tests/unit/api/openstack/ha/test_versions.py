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

import copy

import mock
from oslo_serialization import jsonutils
from six.moves import http_client as http
import webob

from masakari.api import api_version_request as avr
from masakari.api.openstack.ha.views import versions
from masakari import test
from masakari.tests.unit.api.openstack import fakes


NS = {
    'atom': 'http://www.w3.org/2005/Atom',
    'ns': 'http://docs.openstack.org/common/api/v1.0'
}

MAX_API_VERSION = avr.max_api_version().get_string()

EXP_LINKS = {'v1.0': {'html': 'http://docs.openstack.org/', }}


EXP_VERSIONS = {
    "v1.0": {
        "id": "v1.0",
        "status": "SUPPORTED",
        "version": "",
        "min_version": "",
        "updated": "2011-01-21T11:33:21Z",
        "links": [
            {
                "rel": "describedby",
                "type": "text/html",
                "href": EXP_LINKS['v1.0']['html'],
            },
        ],
        "media-types": [
            {
                "base": "application/json",
                "type": "application/vnd.openstack.ha+json;version=1",
            },
        ],
    },
    "v1": {
        "id": "v1",
        "status": "CURRENT",
        "version": MAX_API_VERSION,
        "min_version": "1.0",
        "updated": "2013-07-23T11:33:21Z",
        "links": [
            {
                "rel": "self",
                "href": "http://localhost/v1/",
            },
            {
                "rel": "describedby",
                "type": "text/html",
                "href": EXP_LINKS['v1.0']['html'],
            },
        ],
        "media-types": [
            {
                "base": "application/json",
                "type": "application/vnd.openstack.ha+json;version=1.0",
            }
        ],
    }
}


def _get_self_href(response):
    """Extract the URL to self from response data."""
    data = jsonutils.loads(response.body)
    for link in data['versions'][0]['links']:
        if link['rel'] == 'self':
            return link['href']
    return ''


class VersionsViewBuilderTests(test.NoDBTestCase):
    def test_view_builder(self):
        base_url = "http://example.org/"

        version_data = {
            "v3.2.1": {
                "id": "3.2.1",
                "status": "CURRENT",
                "version": "1",
                "min_version": "1.0",
                "updated": "2011-07-18T11:30:00Z",
            }
        }

        expected = {
            "versions": [
                {
                    "id": "3.2.1",
                    "status": "CURRENT",
                    "version": "1",
                    "min_version": "1.0",
                    "updated": "2011-07-18T11:30:00Z",
                    "links": [
                        {
                            "rel": "self",
                            "href": "http://example.org/v1/",
                        },
                    ],
                }
            ]
        }

        builder = versions.ViewBuilder(base_url)
        output = builder.build_versions(version_data)

        self.assertEqual(expected, output)

    def _test_view_builder_osapi_ha_link_prefix(self, href=None):
        base_url = "http://example.org/v1/"
        if href is None:
            href = base_url

        version_data = {
            "id": "v1",
            "status": "CURRENT",
            "version": "1.0",
            "min_version": "1.0",
            "updated": "2013-07-23T11:33:21Z",
            "links": [
                {
                    "rel": "describedby",
                    "type": "text/html",
                    "href": EXP_LINKS['v1.0']['html'],
                }
            ],
            "media-types": [
                {
                    "base": "application/json",
                    "type": ("application/vnd.openstack."
                             "ha+json;version=1.0")
                }
            ],
        }
        expected_data = copy.deepcopy(version_data)
        expected = {'version': expected_data}
        expected['version']['links'].insert(0, {"rel": "self", "href": href, })
        builder = versions.ViewBuilder(base_url)
        output = builder.build_version(version_data)
        self.assertEqual(expected, output)

    def test_view_builder_without_osapi_ha_link_prefix(self):
        self._test_view_builder_osapi_ha_link_prefix()

    def test_generate_href(self):
        base_url = "http://example.org/app/"

        expected = "http://example.org/app/v1/"

        builder = versions.ViewBuilder(base_url)
        actual = builder.generate_href('v1')

        self.assertEqual(expected, actual)

    def test_generate_href_unknown(self):
        base_url = "http://example.org/app/"

        expected = "http://example.org/app/v1/"

        builder = versions.ViewBuilder(base_url)
        actual = builder.generate_href('foo')

        self.assertEqual(expected, actual)

    def test_generate_href_with_path(self):
        path = "random/path"
        base_url = "http://example.org/app/"
        expected = "http://example.org/app/v1/%s" % path
        builder = versions.ViewBuilder(base_url)
        actual = builder.generate_href("v1", path)
        self.assertEqual(actual, expected)

    def test_generate_href_with_empty_path(self):
        path = ""
        base_url = "http://example.org/app/"
        expected = "http://example.org/app/v1/"
        builder = versions.ViewBuilder(base_url)
        actual = builder.generate_href("v1", path)
        self.assertEqual(actual, expected)


class VersionsTest(test.NoDBTestCase):
    exp_versions = copy.deepcopy(EXP_VERSIONS)
    exp_versions['v1.0']['links'].insert(0, {
        'href': 'http://localhost/v1/', 'rel': 'self'},
    )

    @property
    def wsgi_app(self):
        return fakes.wsgi_app_v1(init_only=('versions',))

    @mock.patch('masakari.rpc.get_client')
    def test_get_version_list_302(self, mock_get_client):
        req = webob.Request.blank('/v1')
        req.accept = "application/json"
        res = req.get_response(self.wsgi_app)
        self.assertEqual(http.FOUND, res.status_int)
        redirect_req = webob.Request.blank('/v1/')
        self.assertEqual(redirect_req.url, res.location)

    @mock.patch('masakari.rpc.get_client')
    def test_get_version_1_versions_invalid(self, mock_get_client):
        req = webob.Request.blank('/v1/versions/1234/foo')
        req.accept = "application/json"
        res = req.get_response(self.wsgi_app)
        self.assertEqual(http.NOT_FOUND, res.status_int)
