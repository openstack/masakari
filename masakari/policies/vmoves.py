# Copyright(c) 2022 Inspur
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo_policy import policy

from masakari.policies import base


VMOVES = 'os_masakari_api:vmoves:%s'

rules = [
    policy.DocumentedRuleDefault(
        name=VMOVES % 'index',
        check_str=base.RULE_ADMIN_API,
        description="Lists IDs, notification_id, instance_id, source_host, "
                    "dest_host, status and type for all VM moves.",
        operations=[
            {
                'method': 'GET',
                'path': '/notifications/{notification_id}/vmoves'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=VMOVES % 'detail',
        check_str=base.RULE_ADMIN_API,
        description="Shows details for one VM move.",
        operations=[
            {
                'method': 'GET',
                'path': '/notifications/{notification_id}/vmoves/'
                        '{vmove_id}'
            }
        ]),
    policy.RuleDefault(
        name=VMOVES % 'discoverable',
        check_str=base.RULE_ADMIN_API,
        description="VM moves API extensions to change the API.",
        ),
]


def list_rules():
    return rules
