# Copyright 2016 NTT Data.
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

from oslo_utils import timeutils
from webob import exc

from masakari.api.openstack import common
from masakari.api.openstack import extensions
from masakari.api.openstack.ha.schemas import notifications as schema
from masakari.api.openstack import wsgi
from masakari.api import validation
from masakari import exception
from masakari.ha import api as notification_api
from masakari.i18n import _

ALIAS = 'notifications'
authorize = extensions.os_masakari_authorizer(ALIAS)


class NotificationsController(wsgi.Controller):
    """Notifications controller for the OpenStack API."""

    def __init__(self):
        self.api = notification_api.NotificationAPI()

    @wsgi.response(202)
    @extensions.expected_errors((400, 403, 409))
    @validation.schema(schema.create)
    def create(self, req, body):
        """Creates a new notification."""
        context = req.environ['masakari.context']
        authorize(context)

        notification_data = body['notification']
        try:
            notification = self.api.create_notification(
                context, notification_data)
        except exception.HostNotFoundByName as err:
            raise exc.HTTPBadRequest(explanation=err.format_message())
        except (exception.DuplicateNotification,
                exception.HostOnMaintenanceError) as err:
            raise exc.HTTPConflict(explanation=err.format_message())

        return {'notification': notification}

    @extensions.expected_errors((400, 403))
    def index(self, req):
        """Returns a summary list of notifications."""
        context = req.environ['masakari.context']
        authorize(context)
        try:
            limit, marker = common.get_limit_and_marker(req)
            sort_keys, sort_dirs = common.get_sort_params(req.params)

            filters = {}
            if 'status' in req.params:
                filters['status'] = req.params['status']
            if 'source_host_uuid' in req.params:
                filters['source_host_uuid'] = req.params['source_host_uuid']
            if 'type' in req.params:
                filters['type'] = req.params['type']
            if 'generated-since' in req.params:
                try:
                    parsed = timeutils.parse_isotime(
                        req.params['generated-since'])
                except ValueError:
                    msg = _('Invalid generated-since value')
                    raise exc.HTTPBadRequest(explanation=msg)
                filters['generated-since'] = parsed

            notifications = self.api.get_all(context, filters, sort_keys,
                                             sort_dirs, limit, marker)
        except exception.MarkerNotFound as err:
            raise exc.HTTPBadRequest(explanation=err.format_message())
        except exception.Invalid as err:
            raise exc.HTTPBadRequest(explanation=err.format_message())

        return {'notifications': notifications}

    @extensions.expected_errors((403, 404))
    def show(self, req, id):
        """Return data about the given notification id."""
        context = req.environ['masakari.context']
        authorize(context)

        try:
            notification = self.api.get_notification(context, id)
        except exception.NotificationNotFound as err:
            raise exc.HTTPNotFound(explanation=err.format_message())
        return {'notification': notification}


class Notifications(extensions.V1APIExtensionBase):
    """Notifications support."""

    name = "Notifications"
    alias = ALIAS
    version = 1

    def get_resources(self):
        member_actions = {'action': 'POST'}

        resources = [
            extensions.ResourceExtension(ALIAS,
                                         NotificationsController(),
                                         member_name='notification',
                                         member_actions=member_actions)
            ]
        return resources

    def get_controller_extensions(self):
        return []
