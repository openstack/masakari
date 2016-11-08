# Copyright 2016 NTT DATA
# All Rights Reserved.

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

"""
Unit Tests for host failure TaskFlow
"""
import copy

import mock

from masakari.compute import nova
from masakari import context
from masakari.engine.drivers.taskflow import host_failure
from masakari import exception
from masakari import test
from masakari.tests.unit import fakes


class HostFailureTestCase(test.TestCase):

    def setUp(self):
        super(HostFailureTestCase, self).setUp()
        self.ctxt = context.get_admin_context()
        # overriding 'wait_period_after_evacuation' and
        # 'wait_period_after_service_disabled' to 2 seconds to
        # reduce the wait period.
        self.override_config("wait_period_after_evacuation", 2)
        self.override_config("wait_period_after_service_disabled", 2)
        self.instance_host = "fake-host"
        self.novaclient = nova.API()
        self.fake_client = fakes.FakeNovaClient()

    def _verify_instance_evacuated(self):
        for server in self.novaclient.get_servers(self.ctxt,
                                                  self.instance_host):
            instance = self.novaclient.get_server(self.ctxt, server.id)
            self.assertEqual('active',
                             getattr(instance, 'OS-EXT-STS:vm_state'))
            self.assertNotEqual(self.instance_host,
                                getattr(instance,
                                        'OS-EXT-SRV-ATTR:hypervisor_hostname'))

    def _test_disable_compute_service(self):
        task = host_failure.DisableComputeServiceTask(self.novaclient)
        with mock.patch.object(fakes.FakeNovaClient.Services,
                               "disable") as mock_disable:
            task.execute(self.ctxt, self.instance_host)
        mock_disable.assert_called_once_with(self.instance_host,
                                             "nova-compute")

    def _test_ha_enabled_instances(self):
        task = host_failure.PrepareHAEnabledInstancesTask(self.novaclient)
        ha_enabled_instances = task.execute(self.ctxt, self.instance_host)

        for instance in ha_enabled_instances['ha_enabled_instances']:
            self.assertTrue(instance.metadata.get(
                'HA_Enabled'))

        return ha_enabled_instances

    def _auto_evacuate_instances(self, ha_enabled_instances):
        task = host_failure.AutoEvacuationInstancesTask(self.novaclient)
        ha_enabled_instances = task.execute(
            self.ctxt, ha_enabled_instances['ha_enabled_instances'])

        return ha_enabled_instances

    def _test_confirm_evacuate_task(self, ha_enabled_instances):
        task = host_failure.ConfirmEvacuationTask(self.novaclient)
        task.execute(self.ctxt, ha_enabled_instances['ha_enabled_instances'],
                     self.instance_host)
        # make sure instance is active and has different host
        self._verify_instance_evacuated()

    @mock.patch('masakari.compute.nova.novaclient')
    def test_host_failure_flow(self, _mock_novaclient):
        _mock_novaclient.return_value = self.fake_client

        # create test data
        self.fake_client.servers.create(id="1", host=self.instance_host,
                                        ha_enabled=True)
        self.fake_client.servers.create(id="2", host=self.instance_host,
                                        ha_enabled=True)

        # execute DisableComputeServiceTask
        self._test_disable_compute_service()

        # execute PrepareHAEnabledInstancesTask
        ha_enabled_instances = self._test_ha_enabled_instances()

        # execute AutoEvacuationInstancesTask
        ha_enabled_instances = self._auto_evacuate_instances(
            ha_enabled_instances)

        # execute ConfirmEvacuationTask
        self._test_confirm_evacuate_task(ha_enabled_instances)

    @mock.patch('masakari.compute.nova.novaclient')
    def test_auto_evacuate_instances_task(self, _mock_novaclient):
        _mock_novaclient.return_value = self.fake_client

        # create test data
        self.fake_client.servers.create(id="1", host=self.instance_host,
                                        ha_enabled=True)
        self.fake_client.servers.create(id="2", host=self.instance_host,
                                        ha_enabled=True)

        # execute DisableComputeServiceTask
        self._test_disable_compute_service()

        # execute PrepareHAEnabledInstancesTask
        ha_enabled_instances = self._test_ha_enabled_instances()

        # execute AutoEvacuationInstancesTask
        task = host_failure.AutoEvacuationInstancesTask(self.novaclient)
        # mock evacuate method of FakeNovaClient to confirm that evacuate
        # method is called.
        with mock.patch.object(fakes.FakeNovaClient.ServerManager,
                               "evacuate") as mock_evacuate:
            task.execute(self.ctxt,
                         ha_enabled_instances['ha_enabled_instances'])
            self.assertEqual(2, mock_evacuate.call_count)

    @mock.patch('masakari.compute.nova.novaclient')
    def test_host_failure_flow_no_ha_enabled_instances(self, _mock_novaclient):
        _mock_novaclient.return_value = self.fake_client

        # create test data
        self.fake_client.servers.create(id="1", host=self.instance_host)
        self.fake_client.servers.create(id="2", host=self.instance_host)

        # execute DisableComputeServiceTask
        self._test_disable_compute_service()

        # execute PrepareHAEnabledInstancesTask
        task = host_failure.PrepareHAEnabledInstancesTask(self.novaclient)
        ha_enabled_instances = task.execute(self.ctxt, self.instance_host)
        self.assertEqual(0, len(ha_enabled_instances['ha_enabled_instances']))

    @mock.patch('masakari.compute.nova.novaclient')
    def test_host_failure_flow_evacuation_failed(self, _mock_novaclient):
        _mock_novaclient.return_value = self.fake_client

        # create ha_enabled test data
        server = self.fake_client.servers.create(id="1",
                                                 host=self.instance_host,
                                                 ha_enabled=True)
        ha_enabled_instances = {
            "ha_enabled_instances": self.fake_client.servers.list()
        }

        # execute AutoEvacuationInstancesTask
        ha_enabled_instances = self._auto_evacuate_instances(
            ha_enabled_instances)

        def fake_get_server(context, host):
            # assume that while evacuating instance goes into error state
            fake_server = copy.deepcopy(server)
            setattr(fake_server, 'OS-EXT-STS:vm_state', "error")
            return fake_server

        with mock.patch.object(self.novaclient, "get_server", fake_get_server):
            # execute ConfirmEvacuationTask
            task = host_failure.ConfirmEvacuationTask(self.novaclient)
            self.assertRaises(
                exception.AutoRecoveryFailureException, task.execute,
                self.ctxt, ha_enabled_instances['ha_enabled_instances'],
                self.instance_host)

    @mock.patch('masakari.compute.nova.novaclient')
    def test_host_failure_flow_resized_instance(self, _mock_novaclient):
        _mock_novaclient.return_value = self.fake_client

        # create ha_enabled test data
        self.fake_client.servers.create(id="1", host=self.instance_host,
                                        vm_state="resized",
                                        ha_enabled=True)
        self.fake_client.servers.create(id="2", host=self.instance_host,
                                        vm_state="resized",
                                        ha_enabled=True)
        ha_enabled_instances = {
            "ha_enabled_instances": self.fake_client.servers.list()
        }

        # execute AutoEvacuationInstancesTask
        ha_enabled_instances = self._auto_evacuate_instances(
            ha_enabled_instances)

        # execute ConfirmEvacuationTask
        self._test_confirm_evacuate_task(ha_enabled_instances)

    @mock.patch('masakari.compute.nova.novaclient')
    def test_host_failure_flow_shutdown_instance(self, _mock_novaclient):
        _mock_novaclient.return_value = self.fake_client

        # create ha_enabled test data
        self.fake_client.servers.create(id="1", host=self.instance_host,
                                        vm_state="stopped",
                                        ha_enabled=True)
        self.fake_client.servers.create(id="2", host=self.instance_host,
                                        vm_state="stopped",
                                        ha_enabled=True)
        ha_enabled_instances = {
            "ha_enabled_instances": self.fake_client.servers.list()
        }

        # execute AutoEvacuationInstancesTask
        ha_enabled_instances = self._auto_evacuate_instances(
            ha_enabled_instances)

        # execute ConfirmEvacuationTask
        self._test_confirm_evacuate_task(ha_enabled_instances)

    @mock.patch('masakari.compute.nova.novaclient')
    def test_host_failure_flow_instance_in_error(self, _mock_novaclient):
        _mock_novaclient.return_value = self.fake_client

        # create ha_enabled test data
        self.fake_client.servers.create(id="1", host=self.instance_host,
                                        vm_state="error",
                                        ha_enabled=True)
        self.fake_client.servers.create(id="2", host=self.instance_host,
                                        vm_state="error",
                                        ha_enabled=True)
        ha_enabled_instances = {
            "ha_enabled_instances": self.fake_client.servers.list()
        }

        # execute AutoEvacuationInstancesTask
        ha_enabled_instances = self._auto_evacuate_instances(
            ha_enabled_instances)

        # execute ConfirmEvacuationTask
        self._test_confirm_evacuate_task(ha_enabled_instances)
