# Copyright (c) 2016 NTT DATA
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


policy_data = """
{
    "context_is_admin": "role:admin or role:administrator",

    "os_masakari_api:extensions:index": "",
    "os_masakari_api:extensions:detail": "",
    "os_masakari_api:segments:index": "",
    "os_masakari_api:segments:detail": "",
    "os_masakari_api:segments:create": "",
    "os_masakari_api:segments:update": "",
    "os_masakari_api:segments:delete": "",
    "os_masakari_api:os-hosts:index": "",
    "os_masakari_api:os-hosts:detail": "",
    "os_masakari_api:os-hosts:create": "",
    "os_masakari_api:os-hosts:update": "",
    "os_masakari_api:os-hosts:delete": "",
    "os_masakari_api:notifications:index": "",
    "os_masakari_api:notifications:detail": "",
    "os_masakari_api:notifications:create": ""
}
"""
