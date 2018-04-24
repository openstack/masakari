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


HOSTS = 'os_masakari_api:os-hosts:%s'

rules = [
    policy.DocumentedRuleDefault(
        name=HOSTS % 'index',
        check_str=base.RULE_ADMIN_API,
        description="Lists IDs, names, type, reserved, on_maintenance for all"
                    " hosts.",
        operations=[
            {
                'method': 'GET',
                'path': '/segments/{segment_id}/hosts'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=HOSTS % 'detail',
        check_str=base.RULE_ADMIN_API,
        description="Shows details for a host.",
        operations=[
            {
                'method': 'GET',
                'path': '/segments/{segment_id}/hosts/{host_id}'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=HOSTS % 'create',
        check_str=base.RULE_ADMIN_API,
        description="Creates a host under given segment.",
        operations=[
            {
                'method': 'POST',
                'path': '/segments/{segment_id}/hosts'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=HOSTS % 'update',
        check_str=base.RULE_ADMIN_API,
        description="Updates the editable attributes of an existing host.",
        operations=[
            {
                'method': 'PUT',
                'path': '/segments/{segment_id}/hosts/{host_id}'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=HOSTS % 'delete',
        check_str=base.RULE_ADMIN_API,
        description="Deletes a host from given segment.",
        operations=[
            {
                'method': 'DELETE',
                'path': '/segments/{segment_id}/hosts/{host_id}'
            }
        ]),
    policy.RuleDefault(
        name=HOSTS % 'discoverable',
        check_str=base.RULE_ADMIN_API,
        description="Host API extensions to change the API.",
        ),
]


def list_rules():
    return rules
