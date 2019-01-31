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

import oslo_messaging as messaging

import masakari.conf
from masakari.objects import base as objects_base
from masakari import rpc

CONF = masakari.conf.CONF


class EngineAPI(rpc.RPCAPI):
    """Client side of the engine rpc API.

    API version history:

    .. code-block:: none

        1.0 - Initial version.
        1.1 - Added get_notification_recovery_workflow_details method to
              retrieve progress details from notification driver.
    """

    RPC_API_VERSION = '1.1'
    TOPIC = CONF.masakari_topic
    BINARY = 'masakari-engine'

    def __init__(self):
        super(EngineAPI, self).__init__()
        target = messaging.Target(topic=self.TOPIC,
                                  version=self.RPC_API_VERSION)
        serializer = objects_base.MasakariObjectSerializer()
        self.client = rpc.get_client(target, serializer=serializer)

    def process_notification(self, context, notification):
        version = '1.0'
        cctxt = self.client.prepare(version=version)
        cctxt.cast(context, 'process_notification', notification=notification)

    def get_notification_recovery_workflow_details(self, context,
                                                   notification):
        version = '1.1'
        cctxt = self.client.prepare(version=version)
        return cctxt.call(context,
                          'get_notification_recovery_workflow_details',
                          notification=notification)
