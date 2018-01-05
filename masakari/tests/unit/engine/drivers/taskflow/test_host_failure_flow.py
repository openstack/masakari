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

import ddt
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


@ddt.ddt
@mock.patch.object(nova.API, "enable_disable_service")
@mock.patch.object(nova.API, "lock_server")
@mock.patch.object(nova.API, "unlock_server")
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

    def _verify_instance_evacuated(self, old_instance_list):
        for server in old_instance_list:
            instance = self.novaclient.get_server(self.ctxt, server.id)
            self.assertIn(getattr(instance, 'OS-EXT-STS:vm_state'),
                          ['active', 'stopped', 'error'])

            if CONF.host_failure.ignore_instances_in_error_state and getattr(
                    server, 'OS-EXT-STS:vm_state') == 'error':
                self.assertEqual(
                    self.instance_host, getattr(
                        instance, 'OS-EXT-SRV-ATTR:hypervisor_hostname'))
            else:
                self.assertNotEqual(
                    self.instance_host, getattr(
                        instance, 'OS-EXT-SRV-ATTR:hypervisor_hostname'))

    def _test_disable_compute_service(self, mock_enable_disable):
        task = host_failure.DisableComputeServiceTask(self.novaclient)
        task.execute(self.ctxt, self.instance_host)

        mock_enable_disable.assert_called_once_with(
            self.ctxt, self.instance_host)

    def _test_instance_list(self, instances_evacuation_count):
        task = host_failure.PrepareHAEnabledInstancesTask(self.novaclient)
        instance_list = task.execute(self.ctxt, self.instance_host)

        for instance in instance_list['instance_list']:
            if CONF.host_failure.ignore_instances_in_error_state:
                self.assertNotEqual("error",
                                    getattr(instance, "OS-EXT-STS:vm_state"))
            if not CONF.host_failure.evacuate_all_instances:
                self.assertTrue(instance.metadata.get('HA_Enabled', False))

        self.assertEqual(instances_evacuation_count,
                         len(instance_list['instance_list']))

        return instance_list

    def _evacuate_instances(self, instance_list, mock_enable_disable,
                            reserved_host=None):
        task = host_failure.EvacuateInstancesTask(self.novaclient)
        old_instance_list = copy.deepcopy(instance_list['instance_list'])

        if reserved_host:
            task.execute(self.ctxt, self.instance_host,
                         instance_list['instance_list'],
                         reserved_host=reserved_host)

            self.assertTrue(mock_enable_disable.called)
        else:
            task.execute(
                self.ctxt, self.instance_host, instance_list['instance_list'])

        # make sure instance is active and has different host
        self._verify_instance_evacuated(old_instance_list)

    @mock.patch('masakari.compute.nova.novaclient')
    def test_host_failure_flow_for_auto_recovery(
            self, _mock_novaclient, mock_unlock, mock_lock,
            mock_enable_disable):
        _mock_novaclient.return_value = self.fake_client
        self.override_config("evacuate_all_instances",
                             True, "host_failure")

        # create test data
        self.fake_client.servers.create(id="1", host=self.instance_host,
                                        ha_enabled=True)
        self.fake_client.servers.create(id="2", host=self.instance_host)

        # execute DisableComputeServiceTask
        self._test_disable_compute_service(mock_enable_disable)

        # execute PrepareHAEnabledInstancesTask
        instance_list = self._test_instance_list(2)

        # execute EvacuateInstancesTask
        self._evacuate_instances(instance_list, mock_enable_disable)

    @mock.patch('masakari.compute.nova.novaclient')
    def test_host_failure_flow_for_reserved_host_recovery(
            self, _mock_novaclient, mock_unlock, mock_lock,
            mock_enable_disable):
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
        self._test_disable_compute_service(mock_enable_disable)

        # execute PrepareHAEnabledInstancesTask
        instance_list = self._test_instance_list(2)

        # execute EvacuateInstancesTask
        with mock.patch.object(host_obj.Host, "save") as mock_save:
            self._evacuate_instances(
                instance_list, mock_enable_disable,
                reserved_host=reserved_host)
            self.assertEqual(1, mock_save.call_count)
            self.assertIn(reserved_host.name,
                          self.fake_client.aggregates.get('1').hosts)

    @mock.patch.object(nova.API, 'add_host_to_aggregate')
    @mock.patch('masakari.compute.nova.novaclient')
    @mock.patch('masakari.engine.drivers.taskflow.host_failure.LOG')
    def test_host_failure_flow_ignores_conflict_error(
            self, mock_log, _mock_novaclient, mock_add_host, mock_unlock,
            mock_lock, mock_enable_disable):
        _mock_novaclient.return_value = self.fake_client
        mock_add_host.side_effect = exception.Conflict
        self.override_config("add_reserved_host_to_aggregate",
                             True, "host_failure")

        # create test data
        self.fake_client.servers.create(id="1", host=self.instance_host,
                                        ha_enabled=True)
        reserved_host = fakes.create_fake_host(name="fake-reserved-host",
                                               reserved=True)
        self.fake_client.aggregates.create(id="1", name='fake_agg',
                                           hosts=[self.instance_host,
                                                  reserved_host.name])
        expected_msg_format = "Host '%(reserved_host)s' already has been " \
                              "added to aggregate '%(aggregate)s'."
        expected_msg_params = {'aggregate': 'fake_agg',
                               'reserved_host': u'fake-reserved-host'}

        # execute DisableComputeServiceTask
        self._test_disable_compute_service(mock_enable_disable)

        # execute PrepareHAEnabledInstancesTask
        instance_list = self._test_instance_list(1)

        # execute EvacuateInstancesTask
        with mock.patch.object(host_obj.Host, "save") as mock_save:
            self._evacuate_instances(
                instance_list, mock_enable_disable,
                reserved_host=reserved_host)
            self.assertEqual(1, mock_save.call_count)
            self.assertIn(reserved_host.name,
                          self.fake_client.aggregates.get('1').hosts)
            mock_log.info.assert_any_call(
                expected_msg_format, expected_msg_params)

    @ddt.data('active', 'rescued', 'paused', 'shelved', 'suspended',
              'error', 'stopped', 'resized')
    @mock.patch('masakari.compute.nova.novaclient')
    def test_host_failure_flow_all_instances(
            self, vm_state, _mock_novaclient, mock_unlock, mock_lock,
            mock_enable_disable):
        _mock_novaclient.return_value = self.fake_client

        # create ha_enabled test data
        power_state = 4 if vm_state == 'resized' else None
        self.fake_client.servers.create(id="1", host=self.instance_host,
                                        vm_state=vm_state,
                                        power_state=power_state,
                                        ha_enabled=True)
        self.fake_client.servers.create(id="2", host=self.instance_host,
                                        vm_state=vm_state,
                                        power_state=power_state,
                                        ha_enabled=True)
        instance_list = {
            "instance_list": self.fake_client.servers.list()
        }

        # execute EvacuateInstancesTask
        self._evacuate_instances(instance_list, mock_enable_disable)

    @mock.patch('masakari.compute.nova.novaclient')
    def test_host_failure_flow_ignore_error_instances(
            self, _mock_novaclient, mock_unlock, mock_lock,
            mock_enable_disable):
        self.override_config("ignore_instances_in_error_state",
                             True, "host_failure")
        self.override_config("evacuate_all_instances",
                             True, "host_failure")
        _mock_novaclient.return_value = self.fake_client

        # create ha_enabled test data
        self.fake_client.servers.create(id="1", host=self.instance_host,
                                        vm_state='error',
                                        ha_enabled=True)
        self.fake_client.servers.create(id="2", host=self.instance_host,
                                        vm_state='active',
                                        ha_enabled=True)

        # execute PrepareHAEnabledInstancesTask
        instance_list = self._test_instance_list(1)

        # execute EvacuateInstancesTask
        self._evacuate_instances(instance_list, mock_enable_disable)

    @mock.patch('masakari.compute.nova.novaclient')
    def test_host_failure_flow_ignore_error_instances_raise_skip_host_recovery(
            self, _mock_novaclient, mock_unlock, mock_lock,
            mock_enable_disable):
        self.override_config("ignore_instances_in_error_state",
                             True, "host_failure")
        self.override_config("evacuate_all_instances",
                             False, "host_failure")
        _mock_novaclient.return_value = self.fake_client

        # create ha_enabled test data
        self.fake_client.servers.create(id="1", host=self.instance_host,
                                        vm_state='error',
                                        ha_enabled=True)

        # execute PrepareHAEnabledInstancesTask
        task = host_failure.PrepareHAEnabledInstancesTask(self.novaclient)
        self.assertRaises(exception.SkipHostRecoveryException, task.execute,
                          self.ctxt, self.instance_host)

    @mock.patch('masakari.compute.nova.novaclient')
    def test_host_failure_flow_all_instances_active_resized_instance(
            self, _mock_novaclient, mock_unlock, mock_lock,
            mock_enable_disable):
        _mock_novaclient.return_value = self.fake_client

        # create ha_enabled test data
        self.fake_client.servers.create(id="1", host=self.instance_host,
                                        vm_state='resized',
                                        ha_enabled=True)
        self.fake_client.servers.create(id="2", host=self.instance_host,
                                        vm_state='resized',
                                        ha_enabled=True)
        instance_list = {
            "instance_list": self.fake_client.servers.list()
        }

        # execute EvacuateInstancesTask
        self._evacuate_instances(instance_list, mock_enable_disable)

    @mock.patch('masakari.compute.nova.novaclient')
    def test_host_failure_flow_no_ha_enabled_instances(
            self, _mock_novaclient, mock_unlock, mock_lock,
            mock_enable_disable):
        _mock_novaclient.return_value = self.fake_client

        # create test data
        self.fake_client.servers.create(id="1", host=self.instance_host)
        self.fake_client.servers.create(id="2", host=self.instance_host)

        # execute DisableComputeServiceTask
        self._test_disable_compute_service(mock_enable_disable)

        # execute PrepareHAEnabledInstancesTask
        task = host_failure.PrepareHAEnabledInstancesTask(self.novaclient)
        self.assertRaises(exception.SkipHostRecoveryException, task.execute,
                          self.ctxt, self.instance_host)

    @mock.patch('masakari.compute.nova.novaclient')
    def test_host_failure_flow_evacuation_failed(
            self, _mock_novaclient, mock_unlock, mock_lock,
            mock_enable_disable):
        _mock_novaclient.return_value = self.fake_client

        # create ha_enabled test data
        server = self.fake_client.servers.create(id="1", vm_state='active',
                                                 host=self.instance_host,
                                                 ha_enabled=True)
        instance_list = {
            "instance_list": self.fake_client.servers.list()
        }

        def fake_get_server(context, host):
            # assume that while evacuating instance goes into error state
            fake_server = copy.deepcopy(server)
            setattr(fake_server, 'OS-EXT-STS:vm_state', "error")
            return fake_server

        with mock.patch.object(self.novaclient, "get_server", fake_get_server):
            # execute EvacuateInstancesTask
            self.assertRaises(
                exception.HostRecoveryFailureException,
                self._evacuate_instances, instance_list, mock_enable_disable)

    @mock.patch('masakari.compute.nova.novaclient')
    def test_host_failure_flow_no_instances_on_host(
            self, _mock_novaclient, mock_unlock, mock_lock,
            mock_enable_disable):
        _mock_novaclient.return_value = self.fake_client
        self.override_config("evacuate_all_instances",
                             True, "host_failure")

        # execute DisableComputeServiceTask
        self._test_disable_compute_service(mock_enable_disable)

        # execute PrepareHAEnabledInstancesTask
        task = host_failure.PrepareHAEnabledInstancesTask(self.novaclient)
        self.assertRaises(exception.SkipHostRecoveryException, task.execute,
                          self.ctxt, self.instance_host)

    @mock.patch.object(nova.API, 'stop_server')
    @mock.patch.object(nova.API, 'reset_instance_state')
    @mock.patch('masakari.compute.nova.novaclient')
    def test_host_failure_flow_for_task_state_not_none(
            self, _mock_novaclient, mock_reset, mock_stop, mock_unlock,
            mock_lock, mock_enable_disable):
        _mock_novaclient.return_value = self.fake_client

        # create ha_enabled test data
        self.fake_client.servers.create(id="1", host=self.instance_host,
                                        vm_state='active',
                                        task_state='fake_task_state',
                                        power_state=None,
                                        ha_enabled=True)
        self.fake_client.servers.create(id="2", host=self.instance_host,
                                        vm_state='stopped',
                                        task_state='fake_task_state',
                                        power_state=None,
                                        ha_enabled=True)
        self.fake_client.servers.create(id="3", host=self.instance_host,
                                        vm_state='error',
                                        task_state='fake_task_state',
                                        power_state=None,
                                        ha_enabled=True)
        instance_list = {
            "instance_list": self.fake_client.servers.list()
        }

        # execute EvacuateInstancesTask
        self._evacuate_instances(instance_list, mock_enable_disable)

        reset_calls = [mock.call(self.ctxt, "1"),
                       mock.call(self.ctxt, "2"),
                       mock.call(self.ctxt, "3"),
                       mock.call(self.ctxt, "3")]
        mock_reset.assert_has_calls(reset_calls)
        self.assertEqual(4, mock_reset.call_count)
        stop_calls = [mock.call(self.ctxt, "2"),
                      mock.call(self.ctxt, "3")]
        mock_stop.assert_has_calls(stop_calls)
        self.assertEqual(2, mock_stop.call_count)
