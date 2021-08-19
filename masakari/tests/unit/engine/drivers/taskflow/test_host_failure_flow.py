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
from unittest import mock

import ddt

from masakari.compute import nova
from masakari import conf
from masakari import context
from masakari.engine.drivers.taskflow import host_failure
from masakari.engine import manager
from masakari import exception
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
        self.disabled_reason = CONF.host_failure.service_disable_reason

    def _verify_instance_evacuated(self, old_instance_list):
        for server in old_instance_list:
            instance = self.novaclient.get_server(self.ctxt, server)

            if getattr(instance, 'OS-EXT-STS:vm_state') in \
                    ['active', 'stopped', 'error']:
                self.assertIn(getattr(instance, 'OS-EXT-STS:vm_state'),
                              ['active', 'stopped', 'error'])
            else:
                if getattr(instance, 'OS-EXT-STS:vm_state') == 'resized' and \
                        getattr(instance, 'OS-EXT-STS:power_state') != 4:
                    self.assertEqual('active',
                                     getattr(instance, 'OS-EXT-STS:vm_state'))
                else:
                    self.assertEqual('stopped',
                                     getattr(instance, 'OS-EXT-STS:vm_state'))

            if CONF.host_failure.ignore_instances_in_error_state and getattr(
                    instance, 'OS-EXT-STS:vm_state') == 'error':
                self.assertEqual(
                    self.instance_host, getattr(
                        instance, 'OS-EXT-SRV-ATTR:hypervisor_hostname'))
            else:
                self.assertNotEqual(
                    self.instance_host, getattr(
                        instance, 'OS-EXT-SRV-ATTR:hypervisor_hostname'))

    def _test_disable_compute_service(self, mock_enable_disable):
        task = host_failure.DisableComputeServiceTask(self.ctxt,
                                                      self.novaclient)
        task.execute(self.instance_host)

        mock_enable_disable.assert_called_once_with(
            self.ctxt, self.instance_host, reason=self.disabled_reason)

    def _test_instance_list(self, instances_evacuation_count):
        task = host_failure.PrepareHAEnabledInstancesTask(self.ctxt,
                                                          self.novaclient)
        instances = task.execute(self.instance_host)
        instance_uuid_list = []
        for instance_id in instances['instance_list']:
            instance = self.novaclient.get_server(self.ctxt, instance_id)
            if CONF.host_failure.ignore_instances_in_error_state:
                self.assertNotEqual("error",
                                    getattr(instance, "OS-EXT-STS:vm_state"))
            if not CONF.host_failure.evacuate_all_instances:
                ha_enabled_key = (CONF.host_failure
                                      .ha_enabled_instance_metadata_key)
                self.assertTrue(instance.metadata.get(ha_enabled_key, False))

            instance_uuid_list.append(instance.id)

        self.assertEqual(instances_evacuation_count,
                         len(instances['instance_list']))

        return {
            "instance_list": instance_uuid_list,
        }

    def _evacuate_instances(self, instance_list, mock_enable_disable,
                            reserved_host=None):
        task = host_failure.EvacuateInstancesTask(
            self.ctxt, self.novaclient,
            update_host_method=manager.update_host_method)
        old_instance_list = copy.deepcopy(instance_list['instance_list'])

        if reserved_host:
            task.execute(self.instance_host,
                         instance_list['instance_list'],
                         reserved_host=reserved_host)

            self.assertTrue(mock_enable_disable.called)
        else:
            task.execute(
                self.instance_host, instance_list['instance_list'])

        # make sure instance is active and has different host
        self._verify_instance_evacuated(old_instance_list)

    @mock.patch.object(nova.API, "get_server")
    @mock.patch.object(nova.API, "evacuate_instance")
    @mock.patch('masakari.engine.drivers.taskflow.host_failure.LOG')
    def test_instance_evacute_error(self, _mock_log, _mock_evacuate,
            _mock_get, mock_unlock, mock_lock, mock_enable_disable):
        task = host_failure.EvacuateInstancesTask(
            self.ctxt, self.novaclient,
            update_host_method=manager.update_host_method)

        def get_fake_server(server, status):
            fake_server = copy.deepcopy(server)
            setattr(fake_server, 'OS-EXT-SRV-ATTR:hypervisor_hostname',
                    self.instance_host)
            setattr(fake_server, 'OS-EXT-STS:vm_state', status)

            return fake_server

        failed_evacuation_instances = []
        fake_instance = self.fake_client.servers.create(
            id="1", host=self.instance_host, ha_enabled=True)

        _mock_get.side_effect = [
            get_fake_server(fake_instance, 'active'),
            get_fake_server(fake_instance, 'error'),
        ]
        task._evacuate_and_confirm(self.ctxt, fake_instance,
                                   self.instance_host,
                                   failed_evacuation_instances)
        self.assertIn(fake_instance.id, failed_evacuation_instances)
        expected_log = 'Failed to evacuate instance %s' % fake_instance.id
        _mock_log.warning.assert_called_once_with(expected_log)

    @mock.patch('masakari.compute.nova.novaclient')
    @mock.patch('masakari.engine.drivers.taskflow.base.MasakariTask.'
                'update_details')
    def test_host_failure_flow_for_auto_recovery(
            self, _mock_notify, _mock_novaclient, mock_unlock, mock_lock,
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

        # verify progress details
        _mock_notify.assert_has_calls([
            mock.call("Disabling compute service on host: 'fake-host'"),
            mock.call("Disabled compute service on host: 'fake-host'", 1.0),
            mock.call('Preparing instances for evacuation'),
            mock.call("Total instances running on failed host 'fake-host' is 2"
                      "", 0.3),
            mock.call("Total HA Enabled instances count: '1'", 0.6),
            mock.call("Total Non-HA Enabled instances count: '1'", 0.7),
            mock.call("All instances (HA Enabled/Non-HA Enabled) should be "
                      "considered for evacuation. Total count is: '2'", 0.8),
            mock.call("Instances to be evacuated are: '1,2'", 1.0),
            mock.call("Start evacuation of instances from failed host "
                      "'fake-host', instance uuids are: '1,2'"),
            mock.call("Evacuation of instance started: '1'", 0.5),
            mock.call("Evacuation of instance started: '2'", 0.5),
            mock.call("Successfully evacuate instances '1,2' from host "
                      "'fake-host'", 0.7),
            mock.call('Evacuation process completed!', 1.0)
        ])

    @mock.patch('masakari.compute.nova.novaclient')
    @mock.patch('masakari.engine.drivers.taskflow.base.MasakariTask.'
                'update_details')
    def test_host_failure_flow_for_auto_recovery_custom_ha_key(
            self, _mock_notify, _mock_novaclient, mock_unlock, mock_lock,
            mock_enable_disable):
        _mock_novaclient.return_value = self.fake_client
        self.override_config("evacuate_all_instances",
                             False, "host_failure")

        ha_enabled_key = 'Ensure-My-HA'

        self.override_config('ha_enabled_instance_metadata_key',
                             ha_enabled_key, 'host_failure')

        # create test data
        self.fake_client.servers.create(id="1", host=self.instance_host,
                                        ha_enabled=True)
        self.fake_client.servers.create(id="2", host=self.instance_host,
                                        ha_enabled=True,
                                        ha_enabled_key=ha_enabled_key)

        # execute DisableComputeServiceTask
        self._test_disable_compute_service(mock_enable_disable)

        # execute PrepareHAEnabledInstancesTask
        instance_list = self._test_instance_list(1)

        # execute EvacuateInstancesTask
        self._evacuate_instances(instance_list, mock_enable_disable)

        # verify progress details
        _mock_notify.assert_has_calls([
            mock.call("Disabling compute service on host: 'fake-host'"),
            mock.call("Disabled compute service on host: 'fake-host'", 1.0),
            mock.call('Preparing instances for evacuation'),
            mock.call("Total instances running on failed host 'fake-host' is 2"
                      "", 0.3),
            mock.call("Total HA Enabled instances count: '1'", 0.6),
            mock.call("Instances to be evacuated are: '2'", 1.0),
            mock.call("Start evacuation of instances from failed host "
                      "'fake-host', instance uuids are: '2'"),
            mock.call("Evacuation of instance started: '2'", 0.5),
            mock.call("Successfully evacuate instances '2' from host "
                      "'fake-host'", 0.7),
            mock.call('Evacuation process completed!', 1.0)
        ])

    @mock.patch('masakari.compute.nova.novaclient')
    @mock.patch('masakari.engine.drivers.taskflow.base.MasakariTask.'
                'update_details')
    def test_host_failure_flow_for_reserved_host_recovery(
            self, _mock_notify, _mock_novaclient, mock_unlock, mock_lock,
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
        with mock.patch.object(manager, "update_host_method") as mock_save:
            self._evacuate_instances(
                instance_list, mock_enable_disable,
                reserved_host=reserved_host.name)
            self.assertEqual(1, mock_save.call_count)
            self.assertIn(reserved_host.name,
                          self.fake_client.aggregates.get('1').hosts)

        # verify progress details
        _mock_notify.assert_has_calls([
            mock.call("Disabling compute service on host: 'fake-host'"),
            mock.call("Disabled compute service on host: 'fake-host'", 1.0),
            mock.call('Preparing instances for evacuation'),
            mock.call("Total instances running on failed host 'fake-host' is 2"
                      "", 0.3),
            mock.call("Total HA Enabled instances count: '1'", 0.6),
            mock.call("Total Non-HA Enabled instances count: '1'", 0.7),
            mock.call("All instances (HA Enabled/Non-HA Enabled) should be "
                      "considered for evacuation. Total count is: '2'", 0.8),
            mock.call("Instances to be evacuated are: '1,2'", 1.0),
            mock.call("Start evacuation of instances from failed host "
                      "'fake-host', instance uuids are: '1,2'"),
            mock.call("Enabling reserved host: 'fake-reserved-host'", 0.1),
            mock.call('Add host fake-reserved-host to aggregate fake_agg',
                      0.2),
            mock.call('Added host fake-reserved-host to aggregate fake_agg',
                      0.3),
            mock.call("Evacuation of instance started: '1'", 0.5),
            mock.call("Evacuation of instance started: '2'", 0.5),
            mock.call("Successfully evacuate instances '1,2' from host "
                      "'fake-host'", 0.7),
            mock.call('Evacuation process completed!', 1.0)
        ])

    @mock.patch('masakari.compute.nova.novaclient')
    @mock.patch('masakari.engine.drivers.taskflow.base.MasakariTask.'
                'update_details')
    def test_host_failure_flow_for_multiple_aggregates(
            self, _mock_notify, _mock_novaclient, mock_unlock, mock_lock,
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
        # Set multiple aggregates to the failure host
        self.fake_client.aggregates.create(id="1", name='fake_agg_1',
                                           hosts=[self.instance_host])
        self.fake_client.aggregates.create(id="2", name='fake_agg_2',
                                           hosts=[self.instance_host])

        # execute DisableComputeServiceTask
        self._test_disable_compute_service(mock_enable_disable)

        # execute PrepareHAEnabledInstancesTask
        instance_list = self._test_instance_list(2)

        # execute EvacuateInstancesTask
        with mock.patch.object(manager, "update_host_method") as mock_save:
            self._evacuate_instances(
                instance_list, mock_enable_disable,
                reserved_host=reserved_host.name)
            self.assertEqual(1, mock_save.call_count)
            self.assertIn(reserved_host.name,
                          self.fake_client.aggregates.get('1').hosts)
            self.assertIn(reserved_host.name,
                          self.fake_client.aggregates.get('2').hosts)

        # verify progress details
        _mock_notify.assert_has_calls([
            mock.call("Disabling compute service on host: 'fake-host'"),
            mock.call("Disabled compute service on host: 'fake-host'", 1.0),
            mock.call('Preparing instances for evacuation'),
            mock.call("Total instances running on failed host 'fake-host' is 2"
                      "", 0.3),
            mock.call("Total HA Enabled instances count: '1'", 0.6),
            mock.call("Total Non-HA Enabled instances count: '1'", 0.7),
            mock.call("All instances (HA Enabled/Non-HA Enabled) should be "
                      "considered for evacuation. Total count is: '2'", 0.8),
            mock.call("Instances to be evacuated are: '1,2'", 1.0),
            mock.call("Start evacuation of instances from failed host "
                      "'fake-host', instance uuids are: '1,2'"),
            mock.call("Enabling reserved host: 'fake-reserved-host'", 0.1),
            mock.call('Add host fake-reserved-host to aggregate fake_agg_1',
                      0.2),
            mock.call('Added host fake-reserved-host to aggregate fake_agg_1',
                      0.3),
            mock.call('Add host fake-reserved-host to aggregate fake_agg_2',
                      0.2),
            mock.call('Added host fake-reserved-host to aggregate fake_agg_2',
                      0.3),
            mock.call("Evacuation of instance started: '1'", 0.5),
            mock.call("Evacuation of instance started: '2'", 0.5),
            mock.call("Successfully evacuate instances '1,2' from host "
                      "'fake-host'", 0.7),
            mock.call('Evacuation process completed!', 1.0)
        ])

    @mock.patch.object(nova.API, 'add_host_to_aggregate')
    @mock.patch('masakari.compute.nova.novaclient')
    @mock.patch('masakari.engine.drivers.taskflow.base.MasakariTask.'
                'update_details')
    @mock.patch('masakari.engine.drivers.taskflow.host_failure.LOG')
    def test_host_failure_flow_ignores_conflict_error(
            self, mock_log, _mock_notify, _mock_novaclient, mock_add_host,
            mock_unlock, mock_lock, mock_enable_disable):
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
        expected_msg_format = ("Host '%(reserved_host)s' already has been "
                               "added to aggregate '%(aggregate)s'.") % {
            'reserved_host': 'fake-reserved-host', 'aggregate': 'fake_agg'
        }

        # execute DisableComputeServiceTask
        self._test_disable_compute_service(mock_enable_disable)

        # execute PrepareHAEnabledInstancesTask
        instance_list = self._test_instance_list(1)

        # execute EvacuateInstancesTask
        with mock.patch.object(manager, "update_host_method") as mock_save:
            self._evacuate_instances(
                instance_list, mock_enable_disable,
                reserved_host=reserved_host.name)
            self.assertEqual(1, mock_save.call_count)
            self.assertIn(reserved_host.name,
                          self.fake_client.aggregates.get('1').hosts)
            mock_log.info.assert_any_call(expected_msg_format)

        # verify progress details
        _mock_notify.assert_has_calls([
            mock.call("Disabling compute service on host: 'fake-host'"),
            mock.call("Disabled compute service on host: 'fake-host'", 1.0),
            mock.call('Preparing instances for evacuation'),
            mock.call("Total instances running on failed host 'fake-host' is 1"
                      "", 0.3),
            mock.call("Total HA Enabled instances count: '1'", 0.6),
            mock.call("Instances to be evacuated are: '1'", 1.0),
            mock.call("Start evacuation of instances from failed host "
                      "'fake-host', instance uuids are: '1'"),
            mock.call("Enabling reserved host: 'fake-reserved-host'", 0.1),
            mock.call('Add host fake-reserved-host to aggregate fake_agg',
                      0.2),
            mock.call("Host 'fake-reserved-host' already has been added to "
                      "aggregate 'fake_agg'.", 1.0),
            mock.call("Evacuation of instance started: '1'", 0.5),
            mock.call("Successfully evacuate instances '1' from host "
                      "'fake-host'", 0.7),
            mock.call('Evacuation process completed!', 1.0)
        ])

    @ddt.data('rescued', 'paused', 'shelved', 'suspended',
              'error', 'resized', 'active', 'resized', 'stopped')
    @mock.patch('masakari.compute.nova.novaclient')
    @mock.patch('masakari.engine.drivers.taskflow.base.MasakariTask.'
                'update_details')
    def test_host_failure_flow_all_instances(
            self, vm_state, _mock_notify, _mock_novaclient, mock_unlock,
            mock_lock, mock_enable_disable):
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

        instance_uuid_list = []
        for instance in self.fake_client.servers.list():
            instance_uuid_list.append(instance.id)

        instance_list = {
            "instance_list": instance_uuid_list,
        }

        # execute EvacuateInstancesTask
        self._evacuate_instances(instance_list, mock_enable_disable)

        # verify progress details
        _mock_notify.assert_has_calls([
            mock.call("Start evacuation of instances from failed host "
                      "'fake-host', instance uuids are: '1,2'"),
            mock.call("Evacuation of instance started: '1'", 0.5),
            mock.call("Evacuation of instance started: '2'", 0.5),
            mock.call("Successfully evacuate instances '1,2' from host "
                      "'fake-host'", 0.7),
            mock.call('Evacuation process completed!', 1.0)
        ])

    @mock.patch('masakari.compute.nova.novaclient')
    @mock.patch('masakari.engine.drivers.taskflow.base.MasakariTask.'
                'update_details')
    def test_host_failure_flow_ignore_error_instances(
            self, _mock_notify, _mock_novaclient, mock_unlock, mock_lock,
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

        # verify progress details
        _mock_notify.assert_has_calls([
            mock.call('Preparing instances for evacuation'),
            mock.call("Total instances running on failed host 'fake-host' is 2"
                      "", 0.3),
            mock.call("Ignoring recovery of HA_Enabled instance '1' as it is "
                      "in 'error' state.", 0.4),
            mock.call("Total HA Enabled instances count: '1'", 0.6),
            mock.call("Total Non-HA Enabled instances count: '0'", 0.7),
            mock.call("All instances (HA Enabled/Non-HA Enabled) should be "
                      "considered for evacuation. Total count is: '1'", 0.8),
            mock.call("Instances to be evacuated are: '2'", 1.0),
            mock.call("Start evacuation of instances from failed host "
                      "'fake-host', instance uuids are: '2'"),
            mock.call("Evacuation of instance started: '2'", 0.5),
            mock.call("Successfully evacuate instances '2' from host "
                      "'fake-host'", 0.7),
            mock.call('Evacuation process completed!', 1.0)
        ])

    @mock.patch('masakari.compute.nova.novaclient')
    @mock.patch('masakari.engine.drivers.taskflow.base.MasakariTask.'
                'update_details')
    def test_host_failure_flow_ignore_error_instances_raise_skip_host_recovery(
            self, _mock_notify, _mock_novaclient, mock_unlock, mock_lock,
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
        task = host_failure.PrepareHAEnabledInstancesTask(self.ctxt,
                                                          self.novaclient)
        self.assertRaises(exception.SkipHostRecoveryException, task.execute,
                          self.instance_host)

        # verify progress details
        _mock_notify.assert_has_calls([
            mock.call('Preparing instances for evacuation'),
            mock.call("Total instances running on failed host 'fake-host' is 1"
                      "", 0.3),
            mock.call("Ignoring recovery of HA_Enabled instance '1' as it is "
                      "in 'error' state.", 0.4),
            mock.call("Total HA Enabled instances count: '0'", 0.6),
            mock.call("Skipped host 'fake-host' recovery as no instances needs"
                      " to be evacuated", 1.0)
        ])

    @mock.patch('masakari.compute.nova.novaclient')
    @mock.patch('masakari.engine.drivers.taskflow.base.MasakariTask.'
                'update_details')
    def test_host_failure_flow_no_ha_enabled_instances(
            self, _mock_notify, _mock_novaclient, mock_unlock, mock_lock,
            mock_enable_disable):
        _mock_novaclient.return_value = self.fake_client

        # create test data
        self.fake_client.servers.create(id="1", host=self.instance_host)
        self.fake_client.servers.create(id="2", host=self.instance_host)

        # execute DisableComputeServiceTask
        self._test_disable_compute_service(mock_enable_disable)

        # execute PrepareHAEnabledInstancesTask
        task = host_failure.PrepareHAEnabledInstancesTask(self.ctxt,
                                                          self.novaclient)
        self.assertRaises(exception.SkipHostRecoveryException, task.execute,
                          self.instance_host)

        # verify progress details
        _mock_notify.assert_has_calls([
            mock.call("Disabling compute service on host: 'fake-host'"),
            mock.call("Disabled compute service on host: 'fake-host'", 1.0),
            mock.call('Preparing instances for evacuation'),
            mock.call("Total instances running on failed host 'fake-host' is 2"
                      "", 0.3),
            mock.call("Total HA Enabled instances count: '0'", 0.6),
            mock.call("Skipped host 'fake-host' recovery as no instances needs"
                      " to be evacuated", 1.0)
        ])

    @mock.patch('masakari.compute.nova.novaclient')
    @mock.patch('masakari.engine.drivers.taskflow.base.MasakariTask.'
                'update_details')
    def test_host_failure_flow_evacuation_failed(
            self, _mock_notify, _mock_novaclient, mock_unlock, mock_lock,
            mock_enable_disable):
        # overriding 'wait_period_after_power_off' to 2 seconds to reduce the
        # wait period, default is 180 seconds.
        self.override_config("wait_period_after_power_off", 2)
        _mock_novaclient.return_value = self.fake_client

        # create ha_enabled test data
        server = self.fake_client.servers.create(id="1", vm_state='active',
                                                 host=self.instance_host,
                                                 ha_enabled=True)

        instance_uuid_list = []
        for instance in self.fake_client.servers.list():
            instance_uuid_list.append(instance.id)

        instance_list = {
            "instance_list": instance_uuid_list,
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

        # verify progress details
        _mock_notify.assert_has_calls([
            mock.call("Start evacuation of instances from failed host "
                      "'fake-host', instance uuids are: '1'"),
            mock.call("Evacuation of instance started: '1'", 0.5),
            mock.call("Failed to evacuate instances '1' from host 'fake-host'"
                      "", 0.7)
        ])

    @mock.patch('masakari.compute.nova.novaclient')
    @mock.patch('masakari.engine.drivers.taskflow.base.MasakariTask.'
                'update_details')
    def test_host_failure_flow_no_instances_on_host(
            self, _mock_notify, _mock_novaclient, mock_unlock, mock_lock,
            mock_enable_disable):
        _mock_novaclient.return_value = self.fake_client
        self.override_config("evacuate_all_instances",
                             True, "host_failure")

        # execute DisableComputeServiceTask
        self._test_disable_compute_service(mock_enable_disable)

        # execute PrepareHAEnabledInstancesTask
        task = host_failure.PrepareHAEnabledInstancesTask(self.ctxt,
                                                          self.novaclient)
        self.assertRaises(exception.SkipHostRecoveryException, task.execute,
                          self.instance_host)

        # verify progress details
        _mock_notify.assert_has_calls([
            mock.call("Disabling compute service on host: 'fake-host'"),
            mock.call("Disabled compute service on host: 'fake-host'", 1.0),
            mock.call('Preparing instances for evacuation'),
            mock.call("Total instances running on failed host 'fake-host' is 0"
                      "", 0.3),
            mock.call("Total HA Enabled instances count: '0'", 0.6),
            mock.call("Total Non-HA Enabled instances count: '0'", 0.7),
            mock.call("All instances (HA Enabled/Non-HA Enabled) should be "
                      "considered for evacuation. Total count is: '0'", 0.8),
            mock.call("Skipped host 'fake-host' recovery as no instances needs"
                      " to be evacuated", 1.0)
        ])

    @mock.patch('masakari.compute.nova.novaclient')
    @mock.patch('masakari.engine.drivers.taskflow.base.MasakariTask.'
                'update_details')
    def test_host_failure_flow_for_task_state_not_none(
            self, _mock_notify, _mock_novaclient, mock_unlock, mock_lock,
            mock_enable_disable):
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
        instance_uuid_list = []
        for instance in self.fake_client.servers.list():
            instance_uuid_list.append(instance.id)

        instance_list = {
            "instance_list": instance_uuid_list,
        }

        # execute EvacuateInstancesTask
        self._evacuate_instances(instance_list, mock_enable_disable)

        reset_calls = [('1', 'active'),
                       ('2', 'stopped'),
                       ('3', 'error'),
                       ('3', 'stopped')]
        stop_calls = ['2', '3']
        self.assertEqual(reset_calls,
                         self.fake_client.servers.reset_state_calls)
        self.assertEqual(stop_calls,
                         self.fake_client.servers.stop_calls)

        # verify progress details
        _mock_notify.assert_has_calls([
            mock.call("Start evacuation of instances from failed host "
                      "'fake-host', instance uuids are: '1,2,3'"),
            mock.call("Evacuation of instance started: '1'", 0.5),
            mock.call("Evacuation of instance started: '2'", 0.5),
            mock.call("Evacuation of instance started: '3'", 0.5),
            mock.call("Successfully evacuate instances '1,2,3' from host "
                      "'fake-host'", 0.7),
            mock.call('Evacuation process completed!', 1.0)
        ])

    @mock.patch('masakari.compute.nova.novaclient')
    @mock.patch('masakari.engine.drivers.taskflow.base.MasakariTask.'
                'update_details')
    def test_host_failure_flow_for_RH_recovery(
            self, _mock_notify, _mock_novaclient, mock_unlock, mock_lock,
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
        with mock.patch.object(manager, "update_host_method") as mock_save:
            self._evacuate_instances(
                instance_list, mock_enable_disable,
                reserved_host=reserved_host.name)
            self.assertEqual(1, mock_save.call_count)
            self.assertIn(reserved_host.name,
                          self.fake_client.aggregates.get('1').hosts)

        # verify progress details
        _mock_notify.assert_has_calls([
            mock.call("Disabling compute service on host: 'fake-host'"),
            mock.call("Disabled compute service on host: 'fake-host'", 1.0),
            mock.call('Preparing instances for evacuation'),
            mock.call("Total instances running on failed host 'fake-host' is 2"
                      "", 0.3),
            mock.call("Total HA Enabled instances count: '1'", 0.6),
            mock.call("Total Non-HA Enabled instances count: '1'", 0.7),
            mock.call("All instances (HA Enabled/Non-HA Enabled) should be "
                      "considered for evacuation. Total count is: '2'", 0.8),
            mock.call("Instances to be evacuated are: '1,2'", 1.0),
            mock.call("Start evacuation of instances from failed host "
                      "'fake-host', instance uuids are: '1,2'"),
            mock.call("Enabling reserved host: 'fake-reserved-host'", 0.1),
            mock.call('Add host fake-reserved-host to aggregate fake_agg',
                      0.2),
            mock.call('Added host fake-reserved-host to aggregate fake_agg',
                      0.3),
            mock.call("Evacuation of instance started: '1'", 0.5),
            mock.call("Evacuation of instance started: '2'", 0.5),
            mock.call("Successfully evacuate instances '1,2' from host "
                      "'fake-host'", 0.7),
            mock.call('Evacuation process completed!', 1.0)
        ])

    @mock.patch('masakari.compute.nova.novaclient')
    def test_host_failure_flow_for_stopped_instances(
            self, _mock_novaclient, mock_unlock, mock_lock,
            mock_enable_disable):
        _mock_novaclient.return_value = self.fake_client

        # create ha_enabled test data
        self.fake_client.servers.create(id="1", host=self.instance_host,
                                        vm_state='stopped',
                                        task_state=None,
                                        power_state=None,
                                        ha_enabled=True)
        instance_uuid_list = []
        for instance in self.fake_client.servers.list():
            instance_uuid_list.append(instance.id)

        instance_list = {
            "instance_list": instance_uuid_list,
        }

        # execute EvacuateInstancesTask
        self._evacuate_instances(instance_list, mock_enable_disable)

        # If vm_state=stopped and task_state=None, reset_state and stop API
        # will not be called.
        self.assertEqual(0, len(self.fake_client.servers.reset_state_calls))
        self.assertEqual(0, len(self.fake_client.servers.stop_calls))
