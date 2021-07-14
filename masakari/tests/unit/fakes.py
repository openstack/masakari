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

import datetime
import iso8601
from oslo_utils import timeutils
from oslo_utils import uuidutils

from masakari import objects
from masakari.objects import segment as segment_obj
from masakari.tests import uuidsentinel

NOW = timeutils.utcnow().replace(microsecond=0)


def _make_segment_obj(segment_dict):
    return segment_obj.FailoverSegment(**segment_dict)


FAILOVER_SEGMENT = {"name": "segment1", "id": "1",
                    "service_type": "COMPUTE", "recovery_method": "auto",
                    "uuid": uuidsentinel.fake_segment1,
                    "description": "failover_segment for compute"}


FAILOVER_SEGMENT = _make_segment_obj(FAILOVER_SEGMENT)


class FakeNovaClient(object):
    class Server(object):
        def __init__(self, id=None, uuid=None, host=None, vm_state=None,
                     task_state=None, power_state=1, ha_enabled=None,
                     ha_enabled_key='HA_Enabled', locked=False):
            self.id = id
            self.uuid = uuid or uuidutils.generate_uuid()
            self.host = host
            setattr(self, 'OS-EXT-SRV-ATTR:hypervisor_hostname', host)
            setattr(self, 'OS-EXT-STS:vm_state', vm_state)
            setattr(self, 'OS-EXT-STS:task_state', task_state)
            setattr(self, 'OS-EXT-STS:power_state', power_state)
            self.metadata = {ha_enabled_key: ha_enabled}
            self.locked = locked

    class ServerManager(object):
        def __init__(self):
            self._servers = []
            self.reset_state_calls = []
            self.stop_calls = []

        def create(self, id, uuid=None, host=None, vm_state='active',
                   task_state=None, power_state=1, ha_enabled=False,
                   ha_enabled_key='HA_Enabled'):
            server = FakeNovaClient.Server(id=id, uuid=uuid, host=host,
                                           vm_state=vm_state,
                                           task_state=task_state,
                                           power_state=power_state,
                                           ha_enabled=ha_enabled,
                                           ha_enabled_key=ha_enabled_key)
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
            current_status = getattr(self.get(uuid), "OS-EXT-STS:vm_state")
            self.reset_state_calls.append((uuid, current_status))
            server = self.get(uuid)
            setattr(server, 'OS-EXT-STS:vm_state', status)

        def evacuate(self, uuid, host=None):
            if not host:
                host = 'fake-host-1'
            server = self.get(uuid)
            setattr(server, 'OS-EXT-SRV-ATTR:hypervisor_hostname', host)
            # pretending that instance is evacuated successfully on given host
            if getattr(server, "OS-EXT-STS:vm_state") in ['active', 'error']:
                setattr(server, 'OS-EXT-STS:vm_state', 'active')
            else:
                setattr(server, 'OS-EXT-STS:vm_state', 'stopped')

        def stop(self, id):
            self.stop_calls.append(id)
            server = self.get(id)
            setattr(server, 'OS-EXT-STS:vm_state', 'stopped')

        def start(self, id):
            server = self.get(id)
            setattr(server, 'OS-EXT-STS:vm_state', 'active')

    class Aggregate(object):
        def __init__(self, id=None, uuid=None, name=None, hosts=None):
            self.id = id
            self.uuid = uuid or uuidutils.generate_uuid()
            self.name = name
            self.hosts = hosts

    class AggregatesManager(object):
        def __init__(self):
            self.aggregates = []

        def create(self, id, uuid=None, name=None, hosts=None):
            aggregate = FakeNovaClient.Aggregate(id=id, uuid=uuid, name=name,
                                                 hosts=hosts)
            self.aggregates.append(aggregate)
            return aggregate

        def list(self):
            return self.aggregates

        def add_host(self, aggregate_id, host_name):
            aggregate = self.get(aggregate_id)
            if host_name not in aggregate.hosts:
                aggregate.hosts.append(host_name)

        def get(self, aggregate_id):
            for aggregate in self.aggregates:
                if aggregate.id == aggregate_id:
                    return aggregate

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

        def disable(self, service_id):
            for _service in self._services:
                if _service.id == service_id:
                    service = _service
            service.status = 'disabled'

        def list(self, host=None, binary=None):
            services = []
            for service in self._services:
                if host == service.host and binary == service.binary:
                    services.append(service)
            return services

        def disable_log_reason(self, service_id, reason):
            for _service in self._services:
                if _service.id == service_id:
                    service = _service
            service.status = 'disabled'
            service.disabled_reason = reason

    def __init__(self):
        self.servers = FakeNovaClient.ServerManager()
        self.services = FakeNovaClient.Services()
        self.aggregates = FakeNovaClient.AggregatesManager()


def create_fake_notification(type="VM", id=1, payload=None,
                             source_host_uuid=uuidsentinel.fake_host,
                             generated_time=NOW, status="new",
                             notification_uuid=uuidsentinel.fake_notification):
    return objects.Notification(
        type=type, id=id, payload=payload, source_host_uuid=source_host_uuid,
        generated_time=generated_time, status=status,
        notification_uuid=notification_uuid)


def create_fake_host(**updates):
    host = {
        'name': 'fake_host', 'id': 1, 'reserved': False,
        'on_maintenance': False, 'type': 'SSH',
        'control_attributes': 'fake', 'uuid': uuidsentinel.fake_host,
        'failover_segment': FAILOVER_SEGMENT,
        'created_at': datetime.datetime(
            2019, 8, 8, 0, 0, 0, tzinfo=iso8601.UTC),
        'updated_at': None, 'deleted_at': None, 'deleted': False
    }
    if updates:
        host.update(updates)
    return objects.Host(**host)


def create_fake_failover_segment(name='fake_segment', id=1, description=None,
                                 service_type='COMPUTE',
                                 recovery_method="auto",
                                 uuid=uuidsentinel.fake_segment,
                                 enabled=True):
    return objects.FailoverSegment(
        name=name, id=id, description=description, service_type=service_type,
        recovery_method=recovery_method, uuid=uuid, enabled=enabled)


def create_fake_notification_progress_details(
        name, uuid, progress, state, progress_details):

    return objects.NotificationProgressDetails(
        name=name, uuid=uuid, progress=progress, state=state,
        progress_details=progress_details)
