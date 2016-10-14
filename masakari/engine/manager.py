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
from masakari.i18n import _LI
from masakari import manager
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

    def process_notification(self, context, notification=None):
        """Processes the notification"""
        @utils.synchronized(notification.source_host_uuid)
        def do_process_notification(notification):
            LOG.info(_LI('Processing notification %s'),
                     notification.notification_uuid)

            update_data = {
                'status': fields.NotificationStatus.RUNNING,
            }
            notification.update(update_data)
            notification.save()

            if notification.type == fields.NotificationType.PROCESS:
                # TODO(Dinesh_Bhor) Execute workflow for process-failure
                #  notification.
                pass
            elif notification.type == fields.NotificationType.VM:
                # TODO(Dinesh_Bhor) Execute workflow for instnace-failure
                # notification.
                pass
            elif notification.type == fields.NotificationType.COMPUTE_HOST:
                # TODO(Dinesh_Bhor) Execute workflow for host-failure
                # notification.
                pass

        do_process_notification(notification)
