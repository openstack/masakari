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
from masakari.objects import fields

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


class HostAPI(object):
    """The Host API to manage hosts"""

    def get_host(self, context, segment_uuid, host_uuid):
        """Get a host by id"""
        objects.FailoverSegment.get_by_uuid(context, segment_uuid)
        if uuidutils.is_uuid_like(host_uuid):
            LOG.debug("Fetching host by "
                      "UUID", host_uuid=host_uuid)

            host = objects.Host.get_by_uuid(context, host_uuid)
        else:
            LOG.debug("Failed to fetch host by uuid %s", host_uuid)
            raise exception.HostNotFound(id=host_uuid)

        return host

    def get_all(self, context, req, segment_uuid):
        """Get all hosts by filter"""
        filters = {}
        sort_keys = req.params.get('sort_key') or 'id'
        sort_dirs = req.params.get('sort_dir') or 'asc'
        limit, marker = common.get_limit_and_marker(req)

        segment = objects.FailoverSegment.get_by_uuid(context, segment_uuid)

        filters['failover_segment_id'] = segment.uuid
        if 'name' in req.params:
            filters['name'] = req.params['name']

        if 'type' in req.params:
            filters['type'] = req.params['type']

        if 'control_attributes' in req.params:
            filters['control_attributes'] = req.params['control_attributes']

        if 'on_maintenance' in req.params:
            filters['on_maintenance'] = req.params['on_maintenance']

        if 'reserved' in req.params:
            filters['reserved'] = req.params['reserved']

        limited_hosts = objects.HostList.get_all(context,
                                                 filters=filters,
                                                 sort_keys=[sort_keys],
                                                 sort_dirs=[sort_dirs],
                                                 limit=limit,
                                                 marker=marker)

        return limited_hosts

    def create_host(self, context, segment_uuid, host_data):
        """Create host"""
        segment = objects.FailoverSegment.get_by_uuid(context, segment_uuid)
        host = objects.Host(context=context)

        # Populate host object for create
        host.name = host_data.get('name')
        host.failover_segment_id = segment.uuid
        host.type = host_data.get('type')
        host.control_attributes = host_data.get('control_attributes')
        host.on_maintenance = host_data.get('on_maintenance', False)
        host.reserved = host_data.get('reserved', False)

        host.create()
        return host

    def update_host(self, context, segment_uuid, id, host_data):
        """Update the host"""
        objects.FailoverSegment.get_by_uuid(context, segment_uuid)

        # TODO(Dinesh_Bhor): Updating a host will depend on many factors
        # for e.g. whether a recovery action is in progress for the host
        # or not. Various constraints will be applied for updating host
        # in future.
        host = objects.Host.get_by_uuid(context, id)
        host.update(host_data)

        host.save()

        return host

    def delete_host(self, context, segment_uuid, id):
        """Delete the host"""
        objects.FailoverSegment.get_by_uuid(context, segment_uuid)

        # TODO(Dinesh_Bhor): Deleting a host will depend on many factors
        # for e.g. whether a recovery action is in progress for the host
        # or not. Various constraints will be applied for deleting host
        # in future.
        host = objects.Host.get_by_uuid(context, id)
        host.destroy()


class NotificationAPI(object):

    def create_notification(self, context, notification_data):
        """Create notification"""

        # Check whether host from which the notification came is already
        # present in failover segment or not
        host_name = notification_data.get('hostname')
        host_object = objects.Host.get_by_name(context, host_name)

        notification = objects.Notification(context=context)

        # Populate notification object for create
        notification.type = notification_data.get('type')
        notification.generated_time = notification_data.get('generated_time')
        notification.status = fields.NotificationStatus.NEW
        notification.source_host_uuid = host_object.uuid
        notification.payload = notification_data.get('payload')

        # TODO(Dinesh_Bhor) Duplicate notifications will be decided in
        # masakari-engine and rejected accordingly.

        notification.create()

        # TODO(Dinesh_Bhor) RPC CAST call will be made to masakari-engine
        # service along with notification_object to process this notification.

        return notification

    def get_all(self, context, filters=None, sort_keys=None,
                sort_dirs=None, limit=None, marker=None):
        """Get all notifications filtered by one of the given parameters.

        If there is no filter it will retrieve all notifications in the system.

        The results will be sorted based on the list of sort keys in the
        'sort_keys' parameter (first value is primary sort key, second value is
        secondary sort ket, etc.). For each sort key, the associated sort
        direction is based on the list of sort directions in the 'sort_dirs'
        parameter.
        """
        LOG.debug("Searching by: %s", str(filters))

        limited_notifications = (objects.NotificationList.
                                 get_all(context, filters, sort_keys,
                                         sort_dirs, limit, marker))

        return limited_notifications

    def get_notification(self, context, notification_uuid):
        """Get a single notification with the given notification_uuid."""
        if uuidutils.is_uuid_like(notification_uuid):
            LOG.debug("Fetching notification by "
                      "UUID", notification_uuid=notification_uuid)

            notification = objects.Notification.get_by_uuid(context,
                                                            notification_uuid)
        else:
            LOG.debug("Failed to fetch notification by "
                      "uuid %s", notification_uuid)
            raise exception.NotificationNotFound(id=notification_uuid)

        return notification
