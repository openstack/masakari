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

from oslo_config import cfg

from masakari.api import api_version_request
from masakari.api.openstack.ha.views import versions as views_versions
from masakari.api.openstack import wsgi


CONF = cfg.CONF

LINKS = {
    'v1.0': {
        'html': 'https://docs.openstack.org/'
    },
}


VERSIONS = {
    "v1.0": {
        "id": "v1.0",
        "status": "CURRENT",
        "version": api_version_request._MAX_API_VERSION,
        "min_version": api_version_request._MIN_API_VERSION,
        "updated": "2016-07-01T11:33:21Z",
        "links": [
            {
                "rel": "describedby",
                "type": "text/html",
                "href": LINKS['v1.0']['html'],
            },
        ],
        "media-types": [
            {
                "base": "application/json",
                "type": "application/vnd.openstack.masakari+json;version=1",
            }
        ],
    }
}


class Versions(wsgi.Resource):
    def __init__(self):
        super(Versions, self).__init__(None)

    def index(self, req, body=None):
        """Return all versions."""
        builder = views_versions.get_view_builder(req)
        return builder.build_versions(VERSIONS)

    @wsgi.response(HTTPStatus.MULTIPLE_CHOICES)
    def multi(self, req, body=None):
        """Return multiple choices."""
        builder = views_versions.get_view_builder(req)
        return builder.build_choices(VERSIONS, req)

    def get_action_args(self, request_environment):
        """Parse dictionary created by routes library."""
        args = {}
        if request_environment['PATH_INFO'] == '/':
            args['action'] = 'index'
        else:
            args['action'] = 'multi'

        return args
