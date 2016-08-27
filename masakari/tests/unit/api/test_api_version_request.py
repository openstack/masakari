# Copyright 2016 NTT DATA
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

from masakari.api import api_version_request
from masakari import exception
from masakari import test
from masakari.tests.unit.api.openstack import fakes


class APIVersionRequestTests(test.NoDBTestCase):
    def test_valid_version_strings(self):
        def _test_string(version, exp_major, exp_minor):
            v = api_version_request.APIVersionRequest(version)
            self.assertEqual(v.ver_major, exp_major)
            self.assertEqual(v.ver_minor, exp_minor)

        _test_string("1.0", 1, 0)

    def test_null_version(self):
        v = api_version_request.APIVersionRequest()
        self.assertTrue(v.is_null())

    def test_invalid_version_strings(self):
        self.assertRaises(exception.InvalidAPIVersionString,
                          api_version_request.APIVersionRequest, "2")

        self.assertRaises(exception.InvalidAPIVersionString,
                          api_version_request.APIVersionRequest, "200")

        self.assertRaises(exception.InvalidAPIVersionString,
                          api_version_request.APIVersionRequest, "2.1.4")

        self.assertRaises(exception.InvalidAPIVersionString,
                          api_version_request.APIVersionRequest, "200.23.66.3")

        self.assertRaises(exception.InvalidAPIVersionString,
                          api_version_request.APIVersionRequest, "5 .3")

        self.assertRaises(exception.InvalidAPIVersionString,
                          api_version_request.APIVersionRequest, "5. 3")

        self.assertRaises(exception.InvalidAPIVersionString,
                          api_version_request.APIVersionRequest, "5.03")

        self.assertRaises(exception.InvalidAPIVersionString,
                          api_version_request.APIVersionRequest, "02.1")

        self.assertRaises(exception.InvalidAPIVersionString,
                          api_version_request.APIVersionRequest, "2.001")

        self.assertRaises(exception.InvalidAPIVersionString,
                          api_version_request.APIVersionRequest, "")

        self.assertRaises(exception.InvalidAPIVersionString,
                          api_version_request.APIVersionRequest, " 2.1")

        self.assertRaises(exception.InvalidAPIVersionString,
                          api_version_request.APIVersionRequest, "2.1 ")

    def test_get_string(self):
        vers1_string = "1.0"
        vers1 = api_version_request.APIVersionRequest(vers1_string)
        self.assertEqual(vers1_string, vers1.get_string())

        self.assertRaises(ValueError,
                          api_version_request.APIVersionRequest().get_string)

    def test_is_supported_min_version(self):
        req = fakes.HTTPRequest.blank('/fake', version='1.0')

        self.assertTrue(api_version_request.is_supported(
            req, min_version='1.0'))
        self.assertFalse(api_version_request.is_supported(
            req, min_version='2.6'))

    def test_is_supported_max_version(self):
        req = fakes.HTTPRequest.blank('/fake', version='2.4')

        self.assertFalse(api_version_request.is_supported(
            req, max_version='1.0'))
        self.assertTrue(api_version_request.is_supported(
            req, max_version='2.6'))
