# Copyright 2016 NTT DATA.  All rights reserved.
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

from masakari.api.validation import parameter_types
from masakari.objects import fields

create = {
    'type': 'object',
    'properties': {
        'notification': {
            'type': 'object',
            'properties': {
                'type': {
                    'type': 'string',
                    'enum': fields.NotificationType.ALL,
                },
                'hostname': parameter_types.hostname,
                'generated_time': {
                    'type': 'string',
                    'format': 'date-time',
                },
                'payload': parameter_types.payload,
            },
            'required': ['type', 'hostname', 'generated_time', 'payload'],
            'additionalProperties': False
        }
    },
    'required': ['notification'],
    'additionalProperties': False
}
