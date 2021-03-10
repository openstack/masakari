# Copyright 2016 NTT DATA.
# All rights reserved.
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
        'segment': {
            'type': 'object',
            'properties': {
                'name': parameter_types.name,
                'description': parameter_types.description,
                'recovery_method': {
                    'type': 'string',
                    'enum': ["auto", "reserved_host",
                             "auto_priority", "rh_priority"]
                },
                'service_type': parameter_types.name
            },
            'additionalProperties': False
        }
    },
    'required': ['segment'],
    'additionalProperties': False
}


create = copy.deepcopy(_base)
create['properties']['segment']['required'] = ['name', 'recovery_method',
                                               'service_type']

create_v12 = copy.deepcopy(create)
create_v12['properties']['segment']['properties']['enabled'] = \
    parameter_types.boolean

update = copy.deepcopy(_base)
update['properties']['segment']['anyOf'] = [{'required': ['name']},
                                            {'required': ['description']},
                                            {'required': ['recovery_method']},
                                            {'required': ['service_type']},
                                            ]

update_v12 = copy.deepcopy(update)
update_v12['properties']['segment']['properties']['enabled'] = \
    parameter_types.boolean
update_v12['properties']['segment']['anyOf'].append({'required': ['enabled']})
