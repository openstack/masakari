# Copyright 2016 NTT DATA
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

from oslo_utils import uuidutils


class FakeNovaClient(object):
    class Server(object):
        def __init__(self, id=None, uuid=None, host=None, vm_state=None,
                     ha_enabled=None):
            self.id = id
            self.uuid = uuid or uuidutils.generate_uuid()
            self.host = host
            setattr(self, 'OS-EXT-SRV-ATTR:hypervisor_hostname', host)
            setattr(self, 'OS-EXT-STS:vm_state', vm_state)
            self.metadata = {"HA_Enabled": ha_enabled}

    class ServerManager(object):
        def __init__(self):
            self._servers = []

        def create(self, id, uuid=None, host=None, vm_state='active',
                   ha_enabled=False):
            server = FakeNovaClient.Server(id=id, uuid=uuid, host=host,
                                           vm_state=vm_state,
                                           ha_enabled=ha_enabled)
            self._servers.append(server)
            return server

        def get(self, id):
            for s in self._servers:
                if s.id == id:
                    return s
            return None

        def list(self, detailed=True, search_opts=None):
            matching = list(self._servers)
            if search_opts:
                for opt, val in search_opts.items():
                    if 'all_tenants' in search_opts:
                        continue
                    matching = [m for m in matching
                                if getattr(m, opt, None) == val]
            return matching

        def reset_state(self, uuid, status):
            server = self.get(uuid)
            setattr(server, 'OS-EXT-STS:vm_state', status)

        def evacuate(self, uuid, host=None, on_shared_storage=False):
            if not host:
                host = 'fake-host-1'
            server = self.get(uuid)
            # pretending that instance is evacuated successfully on given host
            setattr(server, 'OS-EXT-SRV-ATTR:hypervisor_hostname', host)
            setattr(server, 'OS-EXT-STS:vm_state', 'active')

        def stop(self, id):
            server = self.get(id)
            setattr(server, 'OS-EXT-STS:vm_state', 'stopped')

        def start(self, id):
            server = self.get(id)
            setattr(server, 'OS-EXT-STS:vm_state', 'active')

    class Service(object):
        def __init__(self, id=None, host=None, binary=None, status='enabled'):
            self.id = id
            self.host = host
            self.binary = binary
            self.status = status

    class Services(object):
        def __init__(self):
            self._services = []

        def create(self, id, host=None, binary=None,
                   status=None):
            self._services.append(FakeNovaClient.Service(id=id, host=host,
                                                         binary=binary,
                                                         status=status))

        def disable(self, host_name, binary):
            service = self.list(host=host_name, binary=binary)[0]
            service.status = 'disabled'

        def list(self, host=None, binary=None):
            services = []
            for service in self._services:
                if host == service.host and binary == service.binary:
                    services.append(service)
            return services

    def __init__(self):
        self.servers = FakeNovaClient.ServerManager()
        self.services = FakeNovaClient.Services()
