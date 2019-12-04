# Copyright (c) 2020 NTT Data
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

from masakari.api.openstack import common


def get_view_builder(req):
    base_url = req.application_url
    return ViewBuilder(base_url)


class ViewBuilder(common.ViewBuilder):

    def __init__(self, base_url):
        """:param base_url: url of the root wsgi application."""
        self.prefix = self._update_masakari_link_prefix(base_url)
        self.base_url = base_url

    def _host_details(self, host):
        return {
            'id': host.id,
            'uuid': host.uuid,
            'name': host.name,
            'failover_segment_id': host.failover_segment.uuid,
            'failover_segment': host.failover_segment,
            'type': host.type,
            'reserved': host.reserved,
            'control_attributes': host.control_attributes,
            'on_maintenance': host.on_maintenance,
            'created_at': host.created_at,
            'updated_at': host.updated_at,
            'deleted_at': host.deleted_at,
            'deleted': host.deleted
        }

    def build_host(self, host):
        get_host_response = self._host_details(host)
        return get_host_response

    def build_hosts(self, hosts):
        host_objs = []
        for host in hosts:
            get_host_response = self._host_details(host)
            host_objs.append(get_host_response)
        return dict(hosts=host_objs)
