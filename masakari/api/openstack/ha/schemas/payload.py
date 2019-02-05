# Copyright 2018 NTT DATA.  All rights reserved.
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

from masakari.objects import fields


create_compute_host_payload = {
    'type': 'object',
    'properties': {
        'host_status': {
            'enum': fields.HostStatusType.ALL,
            'type': 'string'},
        'cluster_status': {
            'enum': fields.ClusterStatusType.ALL,
            'type': 'string'},
        'event': {
            'enum': fields.EventType.ALL,
            'type': 'string'},
    },
    'required': ['event'],
    'additionalProperties': False
}

create_process_payload = {
    'type': 'object',
    'properties': {
        'process_name': {
            'type': 'string',
            'minLength': 1,
            'maxLength': 4096},
        'event': {
            'enum': fields.EventType.ALL,
            'type': 'string'},
        },
    'required': ['process_name', 'event'],
    'additionalProperties': False
}

create_vm_payload = {
    'type': 'object',
    'properties': {
        'instance_uuid': {
            'type': 'string',
            'format': 'uuid'},
        'vir_domain_event': {
            'type': 'string',
            'minLength': 1,
            'maxLength': 255},
        'event': {
            'type': 'string',
            'minLength': 1,
            'maxLength': 255},
    },
    'required': ['instance_uuid', 'vir_domain_event', 'event'],
    'additionalProperties': False
}
