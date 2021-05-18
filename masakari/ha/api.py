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

import datetime
import traceback

from oslo_log import log as logging
from oslo_utils import excutils
from oslo_utils import strutils
from oslo_utils import uuidutils

from masakari.api import utils as api_utils
from masakari.compute import nova
import masakari.conf
from masakari.engine import rpcapi as engine_rpcapi
from masakari import exception
from masakari.i18n import _
from masakari import objects
from masakari.objects import fields


CONF = masakari.conf.CONF

LOG = logging.getLogger(__name__)


def is_failover_segment_under_recovery(segment):
    filters = {
        'status': [fields.NotificationStatus.NEW,
                   fields.NotificationStatus.RUNNING,
                   fields.NotificationStatus.ERROR]
    }

    return segment.is_under_recovery(filters=filters)


class FailoverSegmentAPI(object):

    def get_segment(self, context, segment_uuid):
        """Get a single failover segment with the given segment_uuid."""
        if uuidutils.is_uuid_like(segment_uuid):
            LOG.debug("Fetching failover segment by uuid %s", segment_uuid)
            segment = objects.FailoverSegment.get_by_uuid(context,
                                                          segment_uuid)
        else:
            LOG.debug("Failed to fetch failover "
                      "segment by uuid %s", segment_uuid)
            raise exception.FailoverSegmentNotFound(id=segment_uuid)

        return segment

    def get_all(self, context, filters=None, sort_keys=None,
                sort_dirs=None, limit=None, marker=None):
        """Get all failover segments filtered by one of the given parameters.

        If there is no filter it will retrieve all segments in the system.

        The results will be sorted based on the list of sort keys in the
        'sort_keys' parameter (first value is primary sort key, second value is
        secondary sort ket, etc.). For each sort key, the associated sort
        direction is based on the list of sort directions in the 'sort_dirs'
        parameter.
        """

        LOG.debug("Searching by: %s", str(filters))

        limited_segments = (objects.FailoverSegmentList.
                            get_all(context, filters=filters,
                                    sort_keys=sort_keys,
                                    sort_dirs=sort_dirs, limit=limit,
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
        segment.enabled = strutils.bool_from_string(
            segment_data.get('enabled', True), strict=True)

        try:
            segment.create()
        except Exception as e:
            with excutils.save_and_reraise_exception():
                tb = traceback.format_exc()
                api_utils.notify_about_segment_api(context, segment,
                    action=fields.EventNotificationAction.SEGMENT_CREATE,
                    phase=fields.EventNotificationPhase.ERROR, exception=e,
                    tb=tb)
        return segment

    def update_segment(self, context, uuid, segment_data):
        """Update the properties of a failover segment."""
        segment = objects.FailoverSegment.get_by_uuid(context, uuid)
        if is_failover_segment_under_recovery(segment):
            msg = _("Failover segment %s can't be updated as "
                    "it is in-use to process notifications.") % uuid
            LOG.error(msg)
            raise exception.FailoverSegmentInUse(msg)

        try:
            segment.update(segment_data)
            segment.save()
        except Exception as e:
            with excutils.save_and_reraise_exception():
                tb = traceback.format_exc()
                api_utils.notify_about_segment_api(context, segment,
                    action=fields.EventNotificationAction.SEGMENT_UPDATE,
                    phase=fields.EventNotificationPhase.ERROR, exception=e,
                    tb=tb)
        return segment

    def delete_segment(self, context, uuid):
        """Deletes the segment."""
        segment = objects.FailoverSegment.get_by_uuid(context, uuid)
        if is_failover_segment_under_recovery(segment):
            msg = _("Failover segment (%s) can't be deleted as "
                    "it is in-use to process notifications.") % uuid
            LOG.error(msg)
            raise exception.FailoverSegmentInUse(msg)

        try:
            segment.destroy()
        except Exception as e:
            with excutils.save_and_reraise_exception():
                tb = traceback.format_exc()
                api_utils.notify_about_segment_api(context, segment,
                    action=fields.EventNotificationAction.SEGMENT_DELETE,
                    phase=fields.EventNotificationPhase.ERROR, exception=e,
                    tb=tb)


class HostAPI(object):
    """The Host API to manage hosts"""

    def _is_valid_host_name(self, context, name):
        novaclient = nova.API()
        novaclient.find_compute_service(context, name)

    def get_host(self, context, segment_uuid, host_uuid):
        """Get a host by id"""

        if uuidutils.is_uuid_like(host_uuid):
            LOG.debug("Fetching host by uuid %s", host_uuid)
            host = objects.Host.get_by_uuid(
                context, host_uuid, segment_uuid=segment_uuid)
        else:
            LOG.debug("Failed to fetch host by uuid %s", host_uuid)
            raise exception.HostNotFound(id=host_uuid)

        return host

    def get_all(self, context, filters=None, sort_keys=None,
                sort_dirs=None, limit=None, marker=None):
        """Get all hosts by filter"""

        LOG.debug("Searching by: %s", str(filters))

        limited_hosts = objects.HostList.get_all(context,
                                                 filters=filters,
                                                 sort_keys=sort_keys,
                                                 sort_dirs=sort_dirs,
                                                 limit=limit,
                                                 marker=marker)

        return limited_hosts

    def create_host(self, context, segment_uuid, host_data):
        """Create host"""
        segment = objects.FailoverSegment.get_by_uuid(context, segment_uuid)
        host = objects.Host(context=context)

        # Populate host object for create
        host.name = host_data.get('name')
        host.failover_segment = segment
        host.type = host_data.get('type')
        host.control_attributes = host_data.get('control_attributes')
        host.on_maintenance = strutils.bool_from_string(
            host_data.get('on_maintenance', False), strict=True)
        host.reserved = strutils.bool_from_string(
            host_data.get('reserved', False), strict=True)

        self._is_valid_host_name(context, host.name)

        try:
            host.create()
        except Exception as e:
            with excutils.save_and_reraise_exception():
                tb = traceback.format_exc()
                api_utils.notify_about_host_api(context, host,
                    action=fields.EventNotificationAction.HOST_CREATE,
                    phase=fields.EventNotificationPhase.ERROR, exception=e,
                    tb=tb)

        return host

    def update_host(self, context, segment_uuid, id, host_data):
        """Update the host"""

        host = objects.Host.get_by_uuid(
            context, id, segment_uuid=segment_uuid)

        if is_failover_segment_under_recovery(host.failover_segment):
            msg = _("Host %s can't be updated as "
                    "it is in-use to process notifications.") % host.uuid
            LOG.error(msg)
            raise exception.HostInUse(msg)

        if 'name' in host_data:
            self._is_valid_host_name(context, host_data.get('name'))

        if 'on_maintenance' in host_data:
            host_data['on_maintenance'] = strutils.bool_from_string(
                host_data['on_maintenance'], strict=True)
        if 'reserved' in host_data:
            host_data['reserved'] = strutils.bool_from_string(
                host_data['reserved'], strict=True)

        try:
            host.update(host_data)
            host.save()
        except Exception as e:
            with excutils.save_and_reraise_exception():
                tb = traceback.format_exc()
                api_utils.notify_about_host_api(context, host,
                    action=fields.EventNotificationAction.HOST_UPDATE,
                    phase=fields.EventNotificationPhase.ERROR, exception=e,
                    tb=tb)
        return host

    def delete_host(self, context, segment_uuid, id):
        """Delete the host"""

        host = objects.Host.get_by_uuid(context, id, segment_uuid=segment_uuid)
        if is_failover_segment_under_recovery(host.failover_segment):
            msg = _("Host %s can't be deleted as "
                    "it is in-use to process notifications.") % host.uuid
            LOG.error(msg)
            raise exception.HostInUse(msg)

        try:
            host.destroy()
        except Exception as e:
            with excutils.save_and_reraise_exception():
                tb = traceback.format_exc()
                api_utils.notify_about_host_api(context, host,
                    action=fields.EventNotificationAction.HOST_DELETE,
                    phase=fields.EventNotificationPhase.ERROR, exception=e,
                    tb=tb)


class NotificationAPI(object):

    def __init__(self):
        self.engine_rpcapi = engine_rpcapi.EngineAPI()

    @staticmethod
    def _is_duplicate_notification(context, notification):
        # Get all the notifications by filters

        filters = {
            'type': notification.type,
            'source_host_uuid': notification.source_host_uuid,
            'generated-since': (notification.generated_time -
                datetime.timedelta(
                    seconds=CONF.duplicate_notification_detection_interval))
        }
        notifications_list = objects.NotificationList.get_all(context,
                                                              filters=filters)
        for db_notification in notifications_list:
            # if payload is same notification should be considered as
            # duplicate
            if db_notification.payload == notification.payload:
                return True

        return False

    def create_notification(self, context, notification_data):
        """Create notification"""

        # Check whether host from which the notification came is already
        # present in failover segment or not
        host_name = notification_data.get('hostname')
        host_object = objects.Host.get_by_name(context, host_name)
        host_on_maintenance = host_object.on_maintenance

        if host_on_maintenance:
            message = (_("Notification received from host %(host)s of type "
                         "'%(type)s' is ignored as the host is already under "
                         "maintenance.") % {
                'host': host_name,
                'type': notification_data.get('type')
            })
            raise exception.HostOnMaintenanceError(message=message)

        notification = objects.Notification(context=context)

        # Populate notification object for create
        notification.type = notification_data.get('type')
        notification.generated_time = notification_data.get('generated_time')
        notification.source_host_uuid = host_object.uuid
        notification.payload = notification_data.get('payload')
        notification.status = fields.NotificationStatus.NEW

        if self._is_duplicate_notification(context, notification):
            message = (_("Notification received from host %(host)s of "
                         " type '%(type)s' is duplicate.") %
                       {'host': host_name, 'type': notification.type})
            raise exception.DuplicateNotification(message=message)

        try:
            notification.create()
            self.engine_rpcapi.process_notification(context, notification)
        except Exception as e:
            with excutils.save_and_reraise_exception():
                tb = traceback.format_exc()
                api_utils.notify_about_notification_api(context, notification,
                    action=fields.EventNotificationAction.NOTIFICATION_CREATE,
                    phase=fields.EventNotificationPhase.ERROR, exception=e,
                    tb=tb)
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
            LOG.debug("Fetching notification by uuid %s", notification_uuid)
            notification = objects.Notification.get_by_uuid(context,
                                                            notification_uuid)
        else:
            LOG.debug("Failed to fetch notification by "
                      "uuid %s", notification_uuid)
            raise exception.NotificationNotFound(id=notification_uuid)

        return notification

    def get_notification_recovery_workflow_details(self, context,
                                                   notification_uuid):
        """Get recovery workflow details details of the notification"""
        notification = self.get_notification(context, notification_uuid)

        LOG.debug("Fetching recovery workflow details of a notification %s ",
                  notification_uuid)
        notification = (self.engine_rpcapi.
                        get_notification_recovery_workflow_details(
                            context, notification))
        return notification
