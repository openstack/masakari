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
from masakari import conf
from masakari import context
from masakari.engine.drivers.taskflow import host_failure
from masakari import exception
from masakari.objects import host as host_obj
from masakari import test
from masakari.tests.unit import fakes

CONF = conf.CONF


class HostFailureTestCase(test.TestCase):

    def setUp(self):
        super(HostFailureTestCase, self).setUp()
        self.ctxt = context.get_admin_context()
        # overriding 'wait_period_after_evacuation' and
        # 'wait_period_after_service_update' to 2 seconds to
        # reduce the wait period.
        self.override_config("wait_period_after_evacuation", 2)
        self.override_config("wait_period_after_service_update", 2)
        self.override_config("evacuate_all_instances",
                             False, "host_failure")
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
        with mock.patch.object(
            self.novaclient,
            "enable_disable_service") as mock_enable_disable_service:
            task.execute(self.ctxt, self.instance_host)

        mock_enable_disable_service.assert_called_once_with(
            self.ctxt, self.instance_host)

    def _test_instance_list(self):
        task = host_failure.PrepareHAEnabledInstancesTask(self.novaclient)
        instance_list = task.execute(
            self.ctxt, self.instance_host)
        evacuate_all_instances = CONF.host_failure.evacuate_all_instances

        if evacuate_all_instances:
            self.assertEqual(len(self.fake_client.servers.list()),
                             len(instance_list['instance_list']))
        else:
            for instance in instance_list['instance_list']:
                self.assertTrue(instance.metadata.get('HA_Enabled', False))

        return instance_list

    def _evacuate_instances(self, instance_list, reserved_host=None):
        task = host_failure.EvacuateInstancesTask(self.novaclient)
        if reserved_host:
            with mock.patch.object(
                self.novaclient,
                    "enable_disable_service") as mock_enable_disable_service:
                instance_list = task.execute(self.ctxt, self.instance_host,
                                             instance_list['instance_list'],
                                             reserved_host=reserved_host)

            mock_enable_disable_service.assert_called_once_with(
                self.ctxt, reserved_host.name, enable=True)
        else:
            instance_list = task.execute(
                self.ctxt, self.instance_host, instance_list['instance_list'])

        return instance_list

    def _test_confirm_evacuate_task(self, instance_list):
        task = host_failure.ConfirmEvacuationTask(self.novaclient)
        task.execute(self.ctxt, instance_list['instance_list'],
                     self.instance_host)
        # make sure instance is active and has different host
        self._verify_instance_evacuated()

    @mock.patch('masakari.compute.nova.novaclient')
    def test_host_failure_flow_for_auto_recovery(self, _mock_novaclient):
        _mock_novaclient.return_value = self.fake_client
        self.override_config("evacuate_all_instances",
                             True, "host_failure")

        # create test data
        self.fake_client.servers.create(id="1", host=self.instance_host,
                                        ha_enabled=True)
        self.fake_client.servers.create(id="2", host=self.instance_host)

        # execute DisableComputeServiceTask
        self._test_disable_compute_service()

        # execute PrepareHAEnabledInstancesTask
        instance_list = self._test_instance_list()

        # execute EvacuateInstancesTask
        instance_list = self._evacuate_instances(instance_list)

        # execute ConfirmEvacuationTask
        self._test_confirm_evacuate_task(instance_list)

    @mock.patch('masakari.compute.nova.novaclient')
    def test_host_failure_flow_for_reserved_host_recovery(
            self, _mock_novaclient):
        _mock_novaclient.return_value = self.fake_client
        self.override_config("evacuate_all_instances",
                             True, "host_failure")
        self.override_config("add_reserved_host_to_aggregate",
                             True, "host_failure")

        # create test data
        self.fake_client.servers.create(id="1", host=self.instance_host,
                                        ha_enabled=True)
        self.fake_client.servers.create(id="2", host=self.instance_host)
        reserved_host = fakes.create_fake_host(name="fake-reserved-host",
                                               reserved=True)
        self.fake_client.aggregates.create(id="1", name='fake_agg',
                                           hosts=[self.instance_host])

        # execute DisableComputeServiceTask
        self._test_disable_compute_service()

        # execute PrepareHAEnabledInstancesTask
        instance_list = self._test_instance_list()

        # execute EvacuateInstancesTask
        with mock.patch.object(host_obj.Host, "save") as mock_save:
            instance_list = self._evacuate_instances(
                instance_list, reserved_host=reserved_host)
            self.assertEqual(1, mock_save.call_count)
            self.assertIn(reserved_host.name,
                          self.fake_client.aggregates.get('1').hosts)

        # execute ConfirmEvacuationTask
        self._test_confirm_evacuate_task(instance_list)

    @mock.patch('masakari.compute.nova.novaclient')
    def test_evacuate_instances_task(self, _mock_novaclient):
        _mock_novaclient.return_value = self.fake_client

        # create test data
        self.fake_client.servers.create(id="1", host=self.instance_host,
                                        ha_enabled=True)
        self.fake_client.servers.create(id="2", host=self.instance_host,
                                        ha_enabled=True)

        # execute DisableComputeServiceTask
        self._test_disable_compute_service()

        # execute PrepareHAEnabledInstancesTask
        instance_list = self._test_instance_list()

        # execute EvacuateInstancesTask
        task = host_failure.EvacuateInstancesTask(self.novaclient)
        # mock evacuate method of FakeNovaClient to confirm that evacuate
        # method is called.
        with mock.patch.object(fakes.FakeNovaClient.ServerManager,
                               "evacuate") as mock_evacuate:
            task.execute(self.ctxt, self.instance_host,
                         instance_list['instance_list'])
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
        self.assertRaises(exception.SkipHostRecoveryException, task.execute,
                          self.ctxt, self.instance_host)

    @mock.patch('masakari.compute.nova.novaclient')
    def test_host_failure_flow_evacuation_failed(self, _mock_novaclient):
        _mock_novaclient.return_value = self.fake_client

        # create ha_enabled test data
        server = self.fake_client.servers.create(id="1",
                                                 host=self.instance_host,
                                                 ha_enabled=True)
        instance_list = {
            "instance_list": self.fake_client.servers.list()
        }

        # execute EvacuateInstancesTask
        instance_list = self._evacuate_instances(
            instance_list)

        def fake_get_server(context, host):
            # assume that while evacuating instance goes into error state
            fake_server = copy.deepcopy(server)
            setattr(fake_server, 'OS-EXT-STS:vm_state', "error")
            return fake_server

        with mock.patch.object(self.novaclient, "get_server", fake_get_server):
            # execute ConfirmEvacuationTask
            task = host_failure.ConfirmEvacuationTask(self.novaclient)
            self.assertRaises(
                exception.HostRecoveryFailureException, task.execute,
                self.ctxt, instance_list['instance_list'],
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
        instance_list = {
            "instance_list": self.fake_client.servers.list()
        }

        # execute EvacuateInstancesTask
        instance_list = self._evacuate_instances(
            instance_list)

        # execute ConfirmEvacuationTask
        self._test_confirm_evacuate_task(instance_list)

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
        instance_list = {
            "instance_list": self.fake_client.servers.list()
        }

        # execute EvacuateInstancesTask
        instance_list = self._evacuate_instances(
            instance_list)

        # execute ConfirmEvacuationTask
        self._test_confirm_evacuate_task(instance_list)

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
        instance_list = {
            "instance_list": self.fake_client.servers.list()
        }

        # execute EvacuateInstancesTask
        instance_list = self._evacuate_instances(
            instance_list)

        # execute ConfirmEvacuationTask
        self._test_confirm_evacuate_task(instance_list)

    @mock.patch('masakari.compute.nova.novaclient')
    def test_host_failure_flow_no_instances_on_host(self, _mock_novaclient):
        _mock_novaclient.return_value = self.fake_client
        self.override_config("evacuate_all_instances",
                             True, "host_failure")

        # execute DisableComputeServiceTask
        self._test_disable_compute_service()

        # execute PrepareHAEnabledInstancesTask
        task = host_failure.PrepareHAEnabledInstancesTask(self.novaclient)
        self.assertRaises(exception.SkipHostRecoveryException, task.execute,
                          self.ctxt, self.instance_host)
