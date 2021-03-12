# Copyright (C) 2019 NTT DATA
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

import ddt

from masakari.objects import fields
from masakari.tests.functional import base


@ddt.ddt
class TestHosts(base.BaseFunctionalTest):

    def setUp(self):
        super(TestHosts, self).setUp()

        if not self.hypervisors:
            self.skipTest("Skipped as there are no hypervisors "
                          "configured in nova")

        # Create segment
        self.segment = self.admin_conn.ha.create_segment(
            name=self.getUniqueString(),
            recovery_method=fields.FailoverSegmentRecoveryMethod.AUTO,
            service_type='COMPUTE')

        # Delete segment which deletes host/s associated with it
        self.addCleanup(self.admin_conn.ha.delete_segment, self.segment.uuid)

    def test_create_get(self):
        # This test is for testing hosts create/get
        # Create valid host
        host_name = self.hypervisors[0]['name']
        host_data = {'name': host_name,
                     'type': 'COMPUTE',
                     'on_maintenance': False,
                     'reserved': False,
                     'control_attributes': 'SSH'}

        host = self.admin_conn.ha.create_host(self.segment.uuid, **host_data)

        self.assertDictContainsSubset(host_data, host)

        result = self.admin_conn.ha.get_host(host.uuid, self.segment.uuid)

        self.assertEqual('COMPUTE', result.type)
        self.assertEqual(False, result.on_maintenance)
        self.assertEqual(False, result.reserved)
        self.assertEqual('SSH', result.control_attributes)

    def test_list(self):
        # This test is for testing host/s creation and listing the same.

        expected_hosts = []
        for host in self.hypervisors:
            host_data = {
                'name': host.name,
                'type': 'COMPUTE',
                'on_maintenance': False,
                'reserved': False,
                'control_attributes': 'SSH',
            }
            self.admin_conn.ha.create_host(
                segment_id=self.segment.uuid,
                **host_data)

            # NOTE(yoctozepto): 'failover_segment_id' is added in the API
            # response. We can verify it here.
            host_data['failover_segment_id'] = self.segment.uuid

            expected_hosts.append(host_data)

        hosts = self.admin_conn.ha.hosts(self.segment.uuid)
        # NOTE(yoctozepto): We are saving the generator values to a list to
        # compare the length and then iterate over the elements for comparison.
        hosts = list(hosts)
        self.assertEqual(len(expected_hosts), len(hosts))
        for expected_host in expected_hosts:
            found = False
            for host in hosts:
                found = found or (dict(host, **expected_host) == dict(host))
            self.assertEqual(True, found,
                'Host not found: {expected_host}'.format(
                    expected_host=expected_host))

    @ddt.data(
        {'on_maintenance': False, 'host_type': 'COMPUTE', 'reserved': False,
         'control_attributes': 'SSH'},
        {'on_maintenance': True, 'host_type': 'CONTROLLER', 'reserved': True,
         'control_attributes': 'TCP'}
    )
    @ddt.unpack
    def test_create_list_with_filter(self, on_maintenance,
                                     host_type, reserved, control_attributes):
        # This test is for testing host/s creation and listing
        # the same based on filters.
        if len(self.hypervisors) == 1:
            self.skipTest("Skipped as there is only one hypervisor "
                          "configured in nova")

        host_data_1 = {'name': self.hypervisors[0].name,
                       'type': 'COMPUTE',
                       'on_maintenance': False,
                       'reserved': False,
                       'control_attributes': 'SSH'}

        host_data_2 = {'name': self.hypervisors[1].name,
                       'type': 'CONTROLLER',
                       'on_maintenance': True,
                       'reserved': True,
                       'control_attributes': 'TCP'}

        self.admin_conn.ha.create_host(self.segment.uuid, **host_data_1)
        self.admin_conn.ha.create_host(self.segment.uuid, **host_data_2)

        expected_host_data = {'on_maintenance': on_maintenance,
                              'type': host_type,
                              'reserved': reserved,
                              'control_attributes': control_attributes
                              }

        # Returns list of hosts based on filters
        for host in self.admin_conn.ha.hosts(self.segment.uuid,
                                       on_maintenance=on_maintenance,
                                       type=host_type,
                                       reserved=reserved):

            self.assertDictContainsSubset(expected_host_data, host)

    def test_update_get_delete(self):
        # This test is for updating created host and deletion of same
        host_name = self.hypervisors[0]['name']

        host = self.admin_conn.ha.create_host(segment_id=self.segment.uuid,
                                        name=host_name,
                                        on_maintenance='False',
                                        reserved='False',
                                        type='COMPUTE',
                                        control_attributes='SSH')

        self.admin_conn.ha.update_host(host['uuid'],
                                 segment_id=self.segment.uuid,
                                 on_maintenance='True',
                                 control_attributes='TCP',
                                 reserved='True')

        result = self.admin_conn.ha.get_host(host.uuid,
                                       self.segment.uuid)
        # Confirm host update
        self.assertEqual(True, result.on_maintenance)
        self.assertEqual(True, result.reserved)
        self.assertEqual('TCP', result.control_attributes)

    def test_update_host_name(self):
        # This test is for updating host name
        if len(self.hypervisors) == 1:
            self.skipTest("Skipped as there is only one hypervisor "
                          "configured in nova")

        host = self.admin_conn.ha.create_host(segment_id=self.segment.uuid,
                            name=self.hypervisors[0]['name'],
                            type='COMPUTE',
                            control_attributes='SSH')

        # Update host name
        updated_host = self.admin_conn.ha.update_host(host['uuid'],
                segment_id=self.segment.uuid,
                name=self.hypervisors[1]['name'])

        result = self.admin_conn.ha.get_host(host.uuid,
                                       self.segment.uuid)
        self.assertEqual(result.name, updated_host.name)
