# Copyright (C) 2019 NTT DATA
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_utils import timeutils

from masakari.objects import fields
from masakari.tests.functional import notification_base as base


class NotificationProcessTestCase(base.NotificationTestBase):

    NOTIFICATION_TYPE = "PROCESS"
    NOTIFICATION_WAIT_INTERVAL = 1
    NOTIFICATION_WAIT_PERIOD = 120

    def setUp(self, ha_api_version="1.0"):
        super(NotificationProcessTestCase, self).setUp(ha_api_version)

    def _test_create_notification_event_stopped(self):
        # Test to create notification for process with 'STOPPED' event type

        notification = self.admin_conn.ha.create_notification(
            type=self.NOTIFICATION_TYPE, hostname=self.host.name,
            generated_time=timeutils.utcnow().replace(microsecond=0),
            payload={"process_name": "nova-compute",
                     "event": fields.EventType.STOPPED})

        self.check_notification_status(notification,
                                       self.NOTIFICATION_WAIT_INTERVAL,
                                       self.NOTIFICATION_WAIT_PERIOD)

        notification = self.admin_conn.ha.get_notification(
            notification.notification_uuid)

        self.assertEqual(fields.NotificationStatus.FINISHED,
                         notification.status)

        host = self.admin_conn.ha.get_host(self.host.uuid,
                                           self.segment.uuid)
        self.assertEqual(True, host.on_maintenance)

        services = self.admin_conn.compute.services()
        for service in services:
            if service.binary == 'nova-compute':
                if service.host == self.host.name:
                    # Enable n-cpu service which is disabled during
                    # DisableComputeNodetask of process recovery notification
                    # created above.
                    self.admin_conn.compute.enable_service(service,
                                                service.host,
                                                service.binary)
        return notification

    def _test_create_notification_event_start(self):
        # Test to create notification for process with 'STARTED' event type

        notification = self.admin_conn.ha.create_notification(
            type=self.NOTIFICATION_TYPE, hostname=self.host.name,
            generated_time=timeutils.utcnow().replace(microsecond=0),
            payload={"process_name": "nova-compute",
                     "event": fields.EventType.STARTED})

        self.check_notification_status(notification,
                                       self.NOTIFICATION_WAIT_INTERVAL,
                                       self.NOTIFICATION_WAIT_PERIOD)

        notification = self.admin_conn.ha.get_notification(
            notification.notification_uuid)
        self.assertEqual(fields.NotificationStatus.FINISHED,
                         notification.status)

        return notification

    def test_create_notification_event_stopped(self):
        # Test to create notification for process with 'STOPPED' event type

        self._test_create_notification_event_stopped()

    def test_create_notification_event_start(self):
        # Test to create notification for process with 'STARTED' event type

        self._test_create_notification_event_start()


class NotificationProcessTestCase_V1_1(NotificationProcessTestCase):

    def setUp(self):
        super(NotificationProcessTestCase, self).setUp("1.1")

    def test_create_notification_event_stopped(self):
        # Test to create notification for process with 'STOPPED' event type

        notification = self._test_create_notification_event_stopped()
        self.assertIsNotNone(notification.recovery_workflow_details)
        recovery_details = notification.recovery_workflow_details
        # check the status of each task is successful
        for details in recovery_details:
            self.assertEqual("SUCCESS", details.state)

    def test_create_notification_event_start(self):
        # Test to create notification for process with 'STARTED' event type

        notification = self._test_create_notification_event_start()
        self.assertIsNotNone(notification.recovery_workflow_details)
        recovery_details = notification.recovery_workflow_details
        # check the status of each task is successful
        for details in recovery_details:
            self.assertEqual("SUCCESS", details.state)
