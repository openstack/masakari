# Copyright 2016 NTT DATA.
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

from webob import exc

from masakari.api.openstack import common
from masakari.api.openstack import extensions
from masakari.api.openstack.ha.schemas import segments as schema
from masakari.api.openstack import wsgi
from masakari.api import validation
from masakari import exception
from masakari.ha import api as segment_api
from masakari.policies import segments as segment_policies


ALIAS = 'segments'


class SegmentsController(wsgi.Controller):
    """Segments controller for the OpenStack API."""

    def __init__(self):
        self.api = segment_api.FailoverSegmentAPI()

    @extensions.expected_errors((HTTPStatus.BAD_REQUEST, HTTPStatus.FORBIDDEN))
    def index(self, req):
        """Returns a summary list of failover segments."""
        context = req.environ['masakari.context']
        context.can(segment_policies.SEGMENTS % 'index')

        try:
            limit, marker = common.get_limit_and_marker(req)
            sort_keys, sort_dirs = common.get_sort_params(req.params)

            filters = {}
            for field in ['recovery_method', 'service_type', 'enabled']:
                if field in req.params:
                    filters[field] = req.params[field]

            segments = self.api.get_all(context, filters=filters,
                                        sort_keys=sort_keys,
                                        sort_dirs=sort_dirs, limit=limit,
                                        marker=marker)
        except exception.MarkerNotFound as e:
            raise exc.HTTPBadRequest(explanation=e.format_message())
        except exception.Invalid as e:
            raise exc.HTTPBadRequest(explanation=e.format_message())

        return {'segments': segments}

    @extensions.expected_errors((HTTPStatus.FORBIDDEN, HTTPStatus.NOT_FOUND))
    def show(self, req, id):
        """Return data about the given segment id."""
        context = req.environ['masakari.context']
        context.can(segment_policies.SEGMENTS % 'detail')

        try:
            segment = self.api.get_segment(context, id)
        except exception.FailoverSegmentNotFound as e:
            raise exc.HTTPNotFound(explanation=e.format_message())
        return {'segment': segment}

    @wsgi.response(HTTPStatus.CREATED)
    @extensions.expected_errors((HTTPStatus.FORBIDDEN, HTTPStatus.CONFLICT))
    @validation.schema(schema.create, '1.0', '1.1')
    @validation.schema(schema.create_v12, '1.2')
    def create(self, req, body):
        """Creates a new failover segment."""
        context = req.environ['masakari.context']
        context.can(segment_policies.SEGMENTS % 'create')

        segment_data = body['segment']
        try:
            segment = self.api.create_segment(context, segment_data)
        except exception.FailoverSegmentExists as e:
            raise exc.HTTPConflict(explanation=e.format_message())
        return {'segment': segment}

    @extensions.expected_errors((HTTPStatus.FORBIDDEN, HTTPStatus.NOT_FOUND,
                                 HTTPStatus.CONFLICT))
    @validation.schema(schema.update, '1.0', '1.1')
    @validation.schema(schema.update_v12, '1.2')
    def update(self, req, id, body):
        """Updates the existing segment."""
        context = req.environ['masakari.context']
        context.can(segment_policies.SEGMENTS % 'update')
        segment_data = body['segment']

        try:
            segment = self.api.update_segment(context, id, segment_data)
        except exception.FailoverSegmentNotFound as e:
            raise exc.HTTPNotFound(explanation=e.format_message())
        except (exception.FailoverSegmentExists, exception.Conflict) as e:
            raise exc.HTTPConflict(explanation=e.format_message())

        return {'segment': segment}

    @wsgi.response(HTTPStatus.NO_CONTENT)
    @extensions.expected_errors((HTTPStatus.FORBIDDEN, HTTPStatus.NOT_FOUND,
                                 HTTPStatus.CONFLICT))
    def delete(self, req, id):
        """Removes a segment by uuid."""
        context = req.environ['masakari.context']
        context.can(segment_policies.SEGMENTS % 'delete')

        try:
            self.api.delete_segment(context, id)
        except exception.FailoverSegmentNotFound as e:
            raise exc.HTTPNotFound(explanation=e.format_message())
        except exception.Conflict as e:
            raise exc.HTTPConflict(explanation=e.format_message())


class Segments(extensions.V1APIExtensionBase):
    """Segments Extension."""
    name = "Segments"
    alias = ALIAS
    version = 1

    def get_resources(self):
        member_actions = {'action': 'POST'}

        resources = [
            extensions.ResourceExtension(ALIAS,
                                         SegmentsController(),
                                         member_name='segment',
                                         member_actions=member_actions)
            ]
        return resources

    def get_controller_extensions(self):
        return []
