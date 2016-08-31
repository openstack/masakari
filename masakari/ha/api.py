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

from oslo_log import log as logging
from oslo_utils import uuidutils

from masakari.api.openstack import common
from masakari import exception
from masakari import objects

LOG = logging.getLogger(__name__)


class FailoverSegmentAPI(object):

    def get_segment(self, context, segment_uuid):
        """Get a single failover segment with the given segment_uuid."""
        if uuidutils.is_uuid_like(segment_uuid):
            LOG.debug("Fetching failover segment by "
                      "UUID", segment_uuid=segment_uuid)

            segment = objects.FailoverSegment.get_by_uuid(context, segment_uuid
                                                          )
        else:
            LOG.debug("Failed to fetch failover "
                      "segment by uuid %s", segment_uuid)
            raise exception.FailoverSegmentNotFound(id=segment_uuid)

        return segment

    def get_all(self, context, req):
        """Get all failover segments filtered by one of the given parameters.

        If there is no filter it will retrieve all segments in the system.

        The results will be sorted based on the list of sort keys in the
        'sort_keys' parameter (first value is primary sort key, second value is
        secondary sort ket, etc.). For each sort key, the associated sort
        direction is based on the list of sort directions in the 'sort_dirs'
        parameter.
        """
        sort_key = req.params.get('sort_key') or 'name'
        sort_dir = req.params.get('sort_dir') or 'asc'
        limit, marker = common.get_limit_and_marker(req)

        filters = {}
        if 'recovery_method' in req.params:
            filters['recovery_method'] = req.params['recovery_method']
        if 'service_type' in req.params:
            filters['service_type'] = req.params['service_type']

        limited_segments = (objects.FailoverSegmentList.
                            get_all(context, filters=filters,
                                    sort_keys=[sort_key],
                                    sort_dirs=[sort_dir], limit=limit,
                                    marker=marker))

        return limited_segments

    def create_segment(self, context, segment_data):
        """Create segment"""
        segment = objects.FailoverSegment(context=context)
        # Populate segment object for create
        segment.name = segment_data.get('name')
        segment.description = segment_data.get('description')
        segment.recovery_method = segment_data.get('recovery_method')
        segment.service_type = segment_data.get('service_type')

        segment.create()

        return segment

    def update_segment(self, context, uuid, segment_data):
        """Update the properties of a failover segment."""
        segment = objects.FailoverSegment.get_by_uuid(context, uuid)

        # TODO(Dinesh_Bhor): Updating a segment will depend on many factors
        # for e.g. whether a recovery action is in progress for the segment
        # or not. Various constraints will be applied for updating failover
        # segment in future.
        segment.update(segment_data)
        segment.save()
        return segment

    def delete_segment(self, context, uuid):
        """Deletes the segment."""
        segment = objects.FailoverSegment.get_by_uuid(context, uuid)
        # TODO(Dinesh_Bhor): Deleting a segment will depend on many factors
        # for e.g. whether a recovery action is in progress for the segment
        # or not. Various constraints will be applied for deleting failover
        # segment in future.
        segment.destroy()
