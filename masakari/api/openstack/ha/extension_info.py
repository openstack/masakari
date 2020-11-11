# Copyright (c) 2016 NTT DATA
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

from oslo_log import log as logging
import webob.exc

from masakari.api.openstack import extensions
from masakari.api.openstack import wsgi
from masakari import exception
from masakari.policies import base as base_policies
from masakari.policies import extension_info as extension_policies

ALIAS = 'extensions'
LOG = logging.getLogger(__name__)


class FakeExtension(object):
    def __init__(self, name, alias, description=""):
        self.name = name
        self.alias = alias
        self.__doc__ = description
        self.version = -1


class ExtensionInfoController(wsgi.Controller):

    def __init__(self, extension_info):
        self.extension_info = extension_info

    def _translate(self, ext):
        ext_data = {"name": ext.name,
                    "alias": ext.alias,
                    "description": ext.__doc__,
                    "namespace": "", "updated": "",
                    "links": []}
        return ext_data

    def _create_fake_ext(self, name, alias, description=""):
        return FakeExtension(name, alias, description)

    def _get_extensions(self, context):
        """Filter extensions list based on policy."""

        discoverable_extensions = dict()
        for alias, ext in self.extension_info.get_extensions().items():
            action = ':'.join([
                base_policies.MASAKARI_API, alias, 'discoverable'])
            if context.can(action, fatal=False):
                discoverable_extensions[alias] = ext
            else:
                LOG.debug("Filter out extension %s from discover list",
                          alias)

        return discoverable_extensions

    @extensions.expected_errors(())
    def index(self, req):
        context = req.environ['masakari.context']
        context.can(extension_policies.EXTENSIONS % 'index')
        discoverable_extensions = self._get_extensions(context)
        sorted_ext_list = sorted(discoverable_extensions.items())

        extensions = []
        for _alias, ext in sorted_ext_list:
            extensions.append(self._translate(ext))

        return dict(extensions=extensions)

    @extensions.expected_errors(HTTPStatus.NOT_FOUND)
    def show(self, req, id):
        context = req.environ['masakari.context']
        context.can(extension_policies.EXTENSIONS % 'detail')
        try:
            ext = self._get_extensions(context)[id]
        except KeyError:
            raise webob.exc.HTTPNotFound()

        return dict(extension=self._translate(ext))


class ExtensionInfo(extensions.V1APIExtensionBase):
    """Extension information."""

    name = "Extensions"
    alias = ALIAS
    version = 1

    def get_resources(self):
        resources = [
            extensions.ResourceExtension(
                ALIAS, ExtensionInfoController(self.extension_info),
                member_name='extension')]
        return resources

    def get_controller_extensions(self):
        return []


class LoadedExtensionInfo(object):
    """Keep track of all loaded API extensions."""

    def __init__(self):
        self.extensions = {}

    def register_extension(self, ext):
        if not self._check_extension(ext):
            return False

        alias = ext.alias

        if alias in self.extensions:
            raise exception.MasakariException(
                "Found duplicate extension: %s" % alias)
        self.extensions[alias] = ext
        return True

    def _check_extension(self, extension):
        """Checks for required methods in extension objects."""
        try:
            extension.is_valid()
        except AttributeError:
            LOG.exception("Exception loading extension")
            return False

        return True

    def get_extensions(self):
        return self.extensions
