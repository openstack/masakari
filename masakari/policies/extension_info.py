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

EXTENSIONS = 'os_masakari_api:extensions:%s'

rules = [
    policy.DocumentedRuleDefault(
        name=EXTENSIONS % 'index',
        check_str=base.RULE_ADMIN_API,
        description="List available extensions.",
        operations=[
            {
                'method': 'GET',
                'path': '/extensions'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=EXTENSIONS % 'detail',
        check_str=base.RULE_ADMIN_API,
        description="Shows information for an extension.",
        operations=[
            {
                'method': 'GET',
                'path': '/extensions/{extensions_id}'
            }
        ]),
    policy.RuleDefault(
        name=EXTENSIONS % 'discoverable',
        check_str=base.RULE_ADMIN_API,
        description="Extension Info API extensions to change the API.",
        ),
]


def list_rules():
    return rules
