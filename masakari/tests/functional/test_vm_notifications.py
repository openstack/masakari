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


class NotificationVMTestCase(base.NotificationTestBase):

    NOTIFICATION_TYPE = "VM"
    NOTIFICATION_WAIT_INTERVAL = 1
    NOTIFICATION_WAIT_PERIOD = 600

    def setUp(self, ha_api_version="1.0"):
        super(NotificationVMTestCase, self).setUp(ha_api_version)

    def _test_create_notification(self):
        # Create server
        server = self.conn.compute.create_server(
            name='masakari_test', flavorRef=self.flavors[0],
            imageRef=self.image_uuids[0],
            networks=[{'uuid': self.private_net}],
            metadata={'HA_Enabled': 'True'})

        self.addCleanup(self.conn.compute.delete_server, server)
        self.check_server_status(server, 'ACTIVE')

        self.admin_conn.compute.stop_server(server.id)

        self.check_server_status(server, 'SHUTOFF')

        notification = self.admin_conn.ha.create_notification(
            type=self.NOTIFICATION_TYPE,
            hostname=self.host.name,
            generated_time=timeutils.utcnow().replace(microsecond=0),
            payload={"instance_uuid": server.id,
                     "vir_domain_event": "STOPPED_FAILED",
                     "event": "LIFECYCLE"})

        self.check_notification_status(notification,
                                       self.NOTIFICATION_WAIT_INTERVAL,
                                       self.NOTIFICATION_WAIT_PERIOD)

        notification = self.admin_conn.instance_ha.get_notification(
            notification.notification_uuid)

        result = self.admin_conn.compute.get_server(server.id)

        self.assertEqual(fields.NotificationStatus.FINISHED,
                         notification.status)
        self.assertEqual('ACTIVE', result.status)

        return notification

    def test_create_notification(self):
        # Test to create notification for VM notification type

        self._test_create_notification()


class NotificationVMTestCase_V1_1(NotificationVMTestCase):

    def setUp(self):
        super(NotificationVMTestCase, self).setUp("1.1")

    def test_create_notification(self):
        notification = self._test_create_notification()
        self.assertIsNotNone(notification.recovery_workflow_details)
        recovery_details = notification.recovery_workflow_details
        # check the status of each task is successful
        for details in recovery_details:
            self.assertEqual("SUCCESS", details.state)
