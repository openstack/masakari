# Copyright (C) 2018 NTT DATA
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


from oslo_policy import policy

from masakari.policies import base


NOTIFICATIONS = 'os_masakari_api:notifications:%s'

rules = [
    policy.DocumentedRuleDefault(
        name=NOTIFICATIONS % 'index',
        check_str=base.RULE_ADMIN_API,
        description="Lists IDs, notification types, host_name, generated_time,"
                    " payload and status for all notifications.",
        operations=[
            {
                'method': 'GET',
                'path': '/notifications'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=NOTIFICATIONS % 'detail',
        check_str=base.RULE_ADMIN_API,
        description="Shows details for a notification.",
        operations=[
            {
                'method': 'GET',
                'path': '/notifications/{notification_id}'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=NOTIFICATIONS % 'create',
        check_str=base.RULE_ADMIN_API,
        description="Creates a notification.",
        operations=[
            {
                'method': 'POST',
                'path': '/notifications'
            }
        ]),
    policy.RuleDefault(
        name=NOTIFICATIONS % 'discoverable',
        check_str=base.RULE_ADMIN_API,
        description="Notification API extensions to change the API.",
        ),
]


def list_rules():
    return rules
