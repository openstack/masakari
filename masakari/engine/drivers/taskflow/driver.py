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

"""
Driver TaskFlowDriver:

    Execute notification workflows using taskflow.
"""


from masakari.engine import driver


class TaskFlowDriver(driver.NotificationDriver):
    def __init__(self):
        super(TaskFlowDriver, self).__init__()

    def execute_host_failure(self, context, host_name, recovery_method,
                             notification_uuid):
        raise NotImplementedError()

    def execute_instance_failure(self, context, instance_uuid,
                                 notification_uuid):
        raise NotImplementedError()

    def execute_process_failure(self, context, process_name, host_name,
                                notification_uuid):
        raise NotImplementedError()
