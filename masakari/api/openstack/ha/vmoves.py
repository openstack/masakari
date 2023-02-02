# Copyright(c) 2022 Inspur
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""The VM Move API extension."""

from http import HTTPStatus
from webob import exc

from masakari.api.openstack import common
from masakari.api.openstack import extensions
from masakari.api.openstack import wsgi
from masakari import exception
from masakari.ha import api as vmove_api
from masakari.policies import vmoves as vmove_policies

ALIAS = "vmoves"


class VMovesController(wsgi.Controller):
    """The VM move API controller for the Instance HA."""

    def __init__(self):
        self.api = vmove_api.VMoveAPI()

    @extensions.expected_errors((HTTPStatus.BAD_REQUEST, HTTPStatus.FORBIDDEN,
                                 HTTPStatus.NOT_FOUND))
    def index(self, req, notification_id):
        """Returns a list of vmoves."""
        context = req.environ['masakari.context']
        context.can(vmove_policies.VMOVES % 'index')

        try:
            filters = {}
            limit, marker = common.get_limit_and_marker(req)
            sort_keys, sort_dirs = common.get_sort_params(req.params)

            if 'status' in req.params:
                filters['status'] = req.params['status']
            if 'type' in req.params:
                filters['type'] = req.params['type']

            vmoves = self.api.get_all(context,
                                      notification_id,
                                      filters=filters,
                                      sort_keys=sort_keys,
                                      sort_dirs=sort_dirs,
                                      limit=limit,
                                      marker=marker)
        except exception.MarkerNotFound as ex:
            raise exc.HTTPBadRequest(explanation=ex.format_message())
        except exception.Invalid as e:
            raise exc.HTTPBadRequest(explanation=e.format_message())
        except exception.NotificationWithoutVMoves as e:
            raise exc.HTTPBadRequest(explanation=e.format_message())
        except exception.NotificationNotFound as ex:
            raise exc.HTTPNotFound(explanation=ex.format_message())

        return {'vmoves': vmoves}

    @extensions.expected_errors((HTTPStatus.BAD_REQUEST, HTTPStatus.FORBIDDEN,
                                 HTTPStatus.NOT_FOUND))
    def show(self, req, notification_id, id):
        """Shows the details of one vmove."""
        context = req.environ['masakari.context']
        context.can(vmove_policies.VMOVES % 'detail')
        try:
            vmove = self.api.get_vmove(context, notification_id, id)
        except exception.NotificationWithoutVMoves as e:
            raise exc.HTTPBadRequest(explanation=e.format_message())
        except exception.VMoveNotFound as e:
            raise exc.HTTPNotFound(explanation=e.format_message())

        return {'vmove': vmove}


class VMoves(extensions.V1APIExtensionBase):
    """vmoves controller"""

    name = "vmoves"
    alias = ALIAS
    version = 1

    def get_resources(self):
        parent = {'member_name': 'notification',
                  'collection_name': 'notifications'}
        resources = [
            extensions.ResourceExtension(
                'vmoves', VMovesController(), parent=parent,
                member_name='vmove')]

        return resources

    def get_controller_extensions(self):
        return []
