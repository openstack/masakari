# Copyright (c) 2016 NTT Data
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

from http import HTTPStatus

import webob.exc

from masakari.api.openstack import extensions
from masakari.api.openstack.ha import versions
from masakari.api.openstack.ha.views import versions as views_versions
from masakari.api.openstack import wsgi


ALIAS = "versions"


class VersionsController(wsgi.Controller):
    @extensions.expected_errors(HTTPStatus.NOT_FOUND)
    def show(self, req, id='v1.0'):
        builder = views_versions.get_view_builder(req)
        if id not in versions.VERSIONS:
            raise webob.exc.HTTPNotFound()

        return builder.build_version(versions.VERSIONS[id])


class Versions(extensions.V1APIExtensionBase):
    """API Version information."""

    name = "Versions"
    alias = ALIAS
    version = 1

    def get_resources(self):
        resources = [
            extensions.ResourceExtension(ALIAS, VersionsController(),
                                         custom_routes_fn=self.version_map)]
        return resources

    def get_controller_extensions(self):
        return []

    def version_map(self, mapper, wsgi_resource):
        self.map_path(mapper, wsgi_resource, '/')
        self.map_path(mapper, wsgi_resource, '')

    @staticmethod
    def map_path(mapper, wsgi_resource, path):
        mapper.connect("versions", path,
                       controller=wsgi_resource,
                       action='show', conditions={"method": ['GET']})
