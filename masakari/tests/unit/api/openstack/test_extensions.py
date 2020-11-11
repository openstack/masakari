# Copyright 2016 NTT DATA
# All rights reserved.
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

from http import HTTPStatus
from unittest import mock

from oslo_config import cfg
import webob.exc

from masakari.api.openstack import extensions
from masakari.api.openstack import ha
from masakari.api.openstack.ha import extension_info
from masakari import exception
from masakari import test

CONF = cfg.CONF


class fake_bad_extension(object):
    name = "fake_bad_extension"
    alias = "fake-bad"


class ExtensionLoadingTestCase(test.NoDBTestCase):

    @mock.patch('masakari.rpc.get_client')
    def test_extensions_loaded(self, mock_get_client):
        app = ha.APIRouterV1()
        self.assertIn('extensions', app._loaded_extension_info.extensions)

    def test_check_bad_extension(self):
        loaded_ext_info = extension_info.LoadedExtensionInfo()
        self.assertFalse(loaded_ext_info._check_extension(fake_bad_extension))

    @mock.patch('masakari.rpc.get_client')
    @mock.patch('masakari.api.openstack.APIRouterV1._register_resources_list')
    def test_extensions_inherit(self, mock_register, mock_get_client):
        app = ha.APIRouterV1()
        self.assertIn('extensions', app._loaded_extension_info.extensions)

        ext_no_inherits = mock_register.call_args_list[0][0][0]
        mock_register.assert_called_with(mock.ANY, mock.ANY)
        name_list = [ext.obj.alias for ext in ext_no_inherits]
        self.assertIn('extensions', name_list)

    def test_extensions_expected_error(self):
        @extensions.expected_errors(HTTPStatus.NOT_FOUND)
        def fake_func():
            raise webob.exc.HTTPNotFound()

        self.assertRaises(webob.exc.HTTPNotFound, fake_func)

    def test_extensions_expected_error_from_list(self):
        @extensions.expected_errors((HTTPStatus.NOT_FOUND,
                                     HTTPStatus.FORBIDDEN))
        def fake_func():
            raise webob.exc.HTTPNotFound()

        self.assertRaises(webob.exc.HTTPNotFound, fake_func)

    def test_extensions_unexpected_error(self):
        @extensions.expected_errors(HTTPStatus.NOT_FOUND)
        def fake_func():
            raise webob.exc.HTTPConflict()

        self.assertRaises(webob.exc.HTTPInternalServerError, fake_func)

    def test_extensions_unexpected_error_from_list(self):
        @extensions.expected_errors((HTTPStatus.NOT_FOUND,
                                     HTTPStatus.REQUEST_ENTITY_TOO_LARGE))
        def fake_func():
            raise webob.exc.HTTPConflict()

        self.assertRaises(webob.exc.HTTPInternalServerError, fake_func)

    def test_extensions_unexpected_policy_not_authorized_error(self):
        @extensions.expected_errors(HTTPStatus.NOT_FOUND)
        def fake_func():
            raise exception.PolicyNotAuthorized(action="foo")

        self.assertRaises(exception.PolicyNotAuthorized, fake_func)
