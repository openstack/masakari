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


import itertools

from masakari.policies import base
from masakari.policies import extension_info
from masakari.policies import hosts
from masakari.policies import notifications
from masakari.policies import segments
from masakari.policies import versions


def list_rules():
    return itertools.chain(
        base.list_rules(),
        extension_info.list_rules(),
        hosts.list_rules(),
        notifications.list_rules(),
        segments.list_rules(),
        versions.list_rules()
    )
