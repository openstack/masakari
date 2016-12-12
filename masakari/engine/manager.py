# Copyright 2016 NTT DATA
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

"""Handles all processes relating to notifications.

The :py:class:`MasakariManager` class is a
:py:class:`masakari.manager.Manager` that handles RPC calls relating to
notifications. It is responsible for processing notifications and executing
workflows.

"""

from oslo_log import log as logging
import oslo_messaging as messaging

import masakari.conf
from masakari.engine import driver
from masakari import exception
from masakari.i18n import _LI, _LW
from masakari import manager
from masakari import objects
from masakari.objects import fields
from masakari import utils

CONF = masakari.conf.CONF

LOG = logging.getLogger(__name__)


class MasakariManager(manager.Manager):
    """Manages the running notifications"""

    target = messaging.Target(version='1.0')

    def __init__(self, masakari_driver=None, *args, **kwargs):
        """Load configuration options"""
        LOG.debug("Initializing Masakari Manager.")
        super(MasakariManager, self).__init__(service_name="engine",
                                             *args, **kwargs)

        self.driver = driver.load_masakari_driver(masakari_driver)

    def _handle_notification_type_process(self, context, notification):
        notification_status = fields.NotificationStatus.FINISHED
        notification_event = notification.payload.get('event')
        process_name = notification.payload.get('process_name')

        if notification_event.upper() == 'STARTED':
            LOG.info(_LI("Notification type '%(type)s' received for host "
                         "'%(host_uuid)s': '%(process_name)s' has been "
                         "%(event)s."), {
                'type': notification.type,
                'host_uuid': notification.source_host_uuid,
                'process_name': process_name,
                'event': notification_event
            })
        elif notification_event.upper() == 'STOPPED':
            host_obj = objects.Host.get_by_uuid(
                context, notification.source_host_uuid)
            host_name = host_obj.name

            # Mark host on_maintenance mode as True
            update_data = {
                'on_maintenance': True,
            }
            host_obj.update(update_data)
            host_obj.save()

            try:
                self.driver.execute_process_failure(
                    context, process_name, host_name,
                    notification.notification_uuid)
            except exception.SkipProcessRecoveryException:
                notification_status = fields.NotificationStatus.FINISHED
            except (exception.MasakariException,
                    exception.ProcessRecoveryFailureException):
                notification_status = fields.NotificationStatus.ERROR
        else:
            LOG.warning(_LW("Invalid event: %(event)s received for "
                            "notification type: %(notification_type)s"), {
                'event': notification_event,
                'notification_type': notification.type
            })
            notification_status = fields.NotificationStatus.IGNORED

        return notification_status

    def _handle_notification_type_instance(self, context, notification):
        notification_status = fields.NotificationStatus.FINISHED
        try:
            self.driver.execute_instance_failure(
                context, notification.payload.get('instance_uuid'),
                notification.notification_uuid)
        except exception.SkipInstanceRecoveryException:
            notification_status = fields.NotificationStatus.FINISHED
        except (exception.MasakariException,
                exception.InstanceRecoveryFailureException):
            notification_status = fields.NotificationStatus.ERROR

        return notification_status

    def _handle_notification_type_host(self, context, notification):
        notification_status = fields.NotificationStatus.FINISHED
        notification_event = notification.payload.get('event')

        if notification_event.upper() == 'STARTED':
            LOG.info(_LI("Notification type '%(type)s' received for host "
                         "'%(host_uuid)s' has been %(event)s."), {
                'type': notification.type,
                'host_uuid': notification.source_host_uuid,
                'event': notification_event
            })
        elif notification_event.upper() == 'STOPPED':
            host_obj = objects.Host.get_by_uuid(
                context, notification.source_host_uuid)
            host_name = host_obj.name
            recovery_method = host_obj.failover_segment.recovery_method

            # Mark host on_maintenance mode as True
            update_data = {
                'on_maintenance': True,
            }
            host_obj.update(update_data)
            host_obj.save()

            try:
                self.driver.execute_host_failure(
                    context, host_name, recovery_method,
                    notification.notification_uuid)
            except (exception.MasakariException,
                    exception.AutoRecoveryFailureException):
                notification_status = fields.NotificationStatus.ERROR
        else:
            LOG.warning(_LW("Invalid event: %(event)s received for "
                            "notification type: %(type)s"), {
                'event': notification_event,
                'type': notification.type
            })
            notification_status = fields.NotificationStatus.IGNORED

        return notification_status

    def process_notification(self, context, notification=None):
        """Processes the notification"""
        @utils.synchronized(notification.source_host_uuid)
        def do_process_notification(notification):
            LOG.info(_LI('Processing notification %(notification_uuid)s of '
                         'type: %(type)s'), {
                'notification_uuid': notification.notification_uuid,
                'type': notification.type
            })

            update_data = {
                'status': fields.NotificationStatus.RUNNING,
            }
            notification.update(update_data)
            notification.save()

            if notification.type == fields.NotificationType.PROCESS:
                notification_status = self._handle_notification_type_process(
                    context, notification)
            elif notification.type == fields.NotificationType.VM:
                notification_status = self._handle_notification_type_instance(
                    context, notification)
            elif notification.type == fields.NotificationType.COMPUTE_HOST:
                notification_status = self._handle_notification_type_host(
                    context, notification)

            LOG.info(_LI("Notification %(notification_uuid)s exits with "
                         "status: %(status)s."), {
                'notification_uuid': notification.notification_uuid,
                'status': notification_status
            })

            update_data = {
                'status': notification_status
            }
            notification.update(update_data)
            notification.save()

        do_process_notification(notification)
