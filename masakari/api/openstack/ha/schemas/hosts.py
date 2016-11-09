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

import copy

from masakari.api.validation import parameter_types


_base = {
    'type': 'object',
    'properties': {
        'host': {
            'type': 'object',
            'properties': {
                'name': parameter_types.name,
                'type': parameter_types.type,
                'control_attributes': parameter_types.description,
                'reserved': parameter_types.boolean,
                'on_maintenance': parameter_types.boolean
            },
            'additionalProperties': False
        }
    },
    'required': ['host'],
    'additionalProperties': False
}


create = copy.deepcopy(_base)
create['properties']['host']['required'] = ['name', 'type',
                                            'control_attributes']


update = copy.deepcopy(_base)
update['properties']['host']['anyOf'] = [{'required': ['name']},
                                         {'required': ['type']},
                                         {'required': ['control_attributes']},
                                         {'required': ['reserved']},
                                         {'required': ['on_maintenance']},
                                         ]
