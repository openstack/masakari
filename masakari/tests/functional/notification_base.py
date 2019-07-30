# Copyright (C) 2019 NTT DATA
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

from oslo_service import loopingcall

from masakari.objects import fields
from masakari.tests.functional import base


class NotificationTestBase(base.BaseFunctionalTest):

    SERVICE_TYPE = "COMPUTE"
    HOST_TYPE = "COMPUTE"
    CONTROL_ATTRIBUTES = "SSH"

    SERVER_WAIT_INTERVAL = 1
    SERVER_WAIT_PERIOD = 300

    def setUp(self, ha_api_version="1.0", recovery_method="auto"):
        super(NotificationTestBase, self).setUp(ha_api_version=ha_api_version)
        self.recovery_method = recovery_method

        if not self.hypervisors:
            self.skipTest("Skip Test as there are no hypervisors "
                          "configured in nova")

        # Get image, flavor and network to create server
        self.image_uuids = [image.id for image in self.conn.compute.images()]
        self.flavors = [flavor.id for flavor in self.conn.compute.flavors()]

        self.private_net = next((
            net.id for net in self.conn.network.networks()
            if net.name == 'private'), '')

        if not self.image_uuids:
            self.skipTest("Skip Test as there are no images "
                          "configured in glance")
        if not self.flavors:
            self.skipTest("Skip Test as there are no flavors "
                          "configured in nova")
        if not self.private_net:
            self.skipTest("Skip Test as there is no private network "
                          "configured in neutron")

        # Create segment
        self.segment = self.admin_conn.ha.create_segment(
            name=self.getUniqueString(), recovery_method=self.recovery_method,
            service_type=self.SERVICE_TYPE)

        # Create valid host
        host_name = self.hypervisors[0]['name']
        self.host = self.admin_conn.ha.create_host(
            segment_id=self.segment.uuid, name=host_name,
            type=self.HOST_TYPE,
            control_attributes=self.CONTROL_ATTRIBUTES)

        # Delete segment which delete all hosts associated with it
        self.addCleanup(self.admin_conn.ha.delete_segment, self.segment.uuid)

    def check_notification_status(self, notification, wait_interval,
                                  wait_period):
        def wait_for_notification_status_finished():
            result = self.admin_conn.ha.get_notification(
                notification.notification_uuid)
            if result.status == fields.NotificationStatus.FINISHED:
                raise loopingcall.LoopingCallDone()

        timer = loopingcall.FixedIntervalWithTimeoutLoopingCall(
            wait_for_notification_status_finished)

        try:
            timer.start(interval=wait_interval, initial_delay=1,
                        timeout=wait_period).wait()
        except loopingcall.LoopingCallTimeOut:
            self.fail("Timed out: Notification is not processed and "
                      "it's not in the finished status")

    def check_server_status(self, server, status):

        def wait_for_server_status_change():
            instance = self.admin_conn.compute.get_server(server.id)
            if instance.status == status:
                raise loopingcall.LoopingCallDone()

        timer = loopingcall.FixedIntervalWithTimeoutLoopingCall(
            wait_for_server_status_change)

        try:
            timer.start(interval=self.SERVER_WAIT_INTERVAL,
                        timeout=self.SERVER_WAIT_PERIOD).wait()
        except loopingcall.LoopingCallTimeOut:
            self.fail("Timed out: Instance is not in the expected"
                      " status: %s" % status)
