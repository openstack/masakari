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
Unit Tests for instance failure TaskFlow
"""

from unittest import mock

from masakari.compute import nova
from masakari import context
from masakari.engine.drivers.taskflow import instance_failure
from masakari import exception
from masakari import test
from masakari.tests.unit import fakes


class InstanceFailureTestCase(test.TestCase):

    def setUp(self):
        super(InstanceFailureTestCase, self).setUp()
        self.ctxt = context.get_admin_context()
        self.novaclient = nova.API()
        self.fake_client = fakes.FakeNovaClient()
        self.instance_id = "1"
        # overriding 'wait_period_after_power_off' and
        # 'wait_period_after_power_on' to 2 seconds to
        # reduce the wait period.
        self.override_config('wait_period_after_power_off', 2)
        self.override_config('wait_period_after_power_on', 2)
        self.override_config("process_all_instances",
                             False, "instance_failure")

    def _test_stop_instance(self):
        task = instance_failure.StopInstanceTask(self.ctxt, self.novaclient)
        task.execute(self.instance_id)
        # verify instance is stopped
        instance = self.novaclient.get_server(self.ctxt, self.instance_id)
        self.assertEqual('stopped',
                         getattr(instance, 'OS-EXT-STS:vm_state'))

    def _test_confirm_instance_is_active(self):
        task = instance_failure.ConfirmInstanceActiveTask(self.ctxt,
                                                          self.novaclient)
        task.execute(self.instance_id)
        # verify instance is in active state
        instance = self.novaclient.get_server(self.ctxt, self.instance_id)
        self.assertEqual('active',
                         getattr(instance, 'OS-EXT-STS:vm_state'))

    @mock.patch('masakari.compute.nova.novaclient')
    @mock.patch('masakari.engine.drivers.taskflow.base.MasakariTask.'
                'update_details')
    def test_instance_failure_flow(self, _mock_notify, _mock_novaclient):
        _mock_novaclient.return_value = self.fake_client

        # create test data
        self.fake_client.servers.create(self.instance_id,
                                        host="fake-host",
                                        ha_enabled=True)

        # test StopInstanceTask
        self._test_stop_instance()

        # test StartInstanceTask
        task = instance_failure.StartInstanceTask(self.ctxt, self.novaclient)
        task.execute(self.instance_id)

        # test ConfirmInstanceActiveTask
        self._test_confirm_instance_is_active()

        # verify progress details
        _mock_notify.assert_has_calls([
            mock.call('Stopping instance: ' + self.instance_id),
            mock.call("Stopped instance: '" + self.instance_id + "'", 1.0),
            mock.call("Starting instance: '" + self.instance_id + "'"),
            mock.call("Instance started: '" + self.instance_id + "'", 1.0),
            mock.call("Confirming instance '" + self.instance_id +
                      "' vm_state is ACTIVE"),
            mock.call("Confirmed instance '" + self.instance_id +
                      "' vm_state is ACTIVE", 1.0)
        ])

    @mock.patch('masakari.compute.nova.novaclient')
    @mock.patch('masakari.engine.drivers.taskflow.base.MasakariTask.'
                'update_details')
    def test_instance_failure_flow_custom_ha_key(
            self, _mock_notify, _mock_novaclient):
        _mock_novaclient.return_value = self.fake_client

        ha_enabled_key = 'Ensure-My-HA'

        self.override_config('ha_enabled_instance_metadata_key',
                             ha_enabled_key, 'instance_failure')

        # create test data with custom ha_enabled_key
        self.fake_client.servers.create(self.instance_id,
                                        host="fake-host",
                                        ha_enabled=True,
                                        ha_enabled_key=ha_enabled_key)

        # test StopInstanceTask
        self._test_stop_instance()

        # test StartInstanceTask
        task = instance_failure.StartInstanceTask(self.ctxt, self.novaclient)
        task.execute(self.instance_id)

        # test ConfirmInstanceActiveTask
        self._test_confirm_instance_is_active()

        # verify progress details
        _mock_notify.assert_has_calls([
            mock.call('Stopping instance: ' + self.instance_id),
            mock.call("Stopped instance: '" + self.instance_id + "'", 1.0),
            mock.call("Starting instance: '" + self.instance_id + "'"),
            mock.call("Instance started: '" + self.instance_id + "'", 1.0),
            mock.call("Confirming instance '" + self.instance_id +
                      "' vm_state is ACTIVE"),
            mock.call("Confirmed instance '" + self.instance_id +
                      "' vm_state is ACTIVE", 1.0)
        ])

    @mock.patch('masakari.compute.nova.novaclient')
    @mock.patch('masakari.engine.drivers.taskflow.base.MasakariTask.'
                'update_details')
    def test_instance_failure_flow_resized_instance(self, _mock_notify,
                                                    _mock_novaclient):
        _mock_novaclient.return_value = self.fake_client

        # create test data
        self.fake_client.servers.create(self.instance_id,
                                        host="fake-host",
                                        ha_enabled=True, vm_state="resized")

        # test StopInstanceTask
        self._test_stop_instance()

        # test StartInstanceTask
        task = instance_failure.StartInstanceTask(self.ctxt, self.novaclient)
        task.execute(self.instance_id)

        # test ConfirmInstanceActiveTask
        self._test_confirm_instance_is_active()

        # verify progress details
        _mock_notify.assert_has_calls([
            mock.call('Stopping instance: ' + self.instance_id),
            mock.call("Stopped instance: '" + self.instance_id + "'", 1.0),
            mock.call("Starting instance: '" + self.instance_id + "'"),
            mock.call("Instance started: '" + self.instance_id + "'", 1.0),
            mock.call("Confirming instance '" + self.instance_id +
                      "' vm_state is ACTIVE"),
            mock.call("Confirmed instance '" + self.instance_id +
                      "' vm_state is ACTIVE", 1.0)
        ])

    @mock.patch('masakari.compute.nova.novaclient')
    @mock.patch('masakari.engine.drivers.taskflow.base.MasakariTask.'
                'update_details')
    def test_instance_failure_flow_stop_conflict_instance_in_error(
            self, _mock_notify, _mock_novaclient):
        _mock_novaclient.return_value = self.fake_client

        # create test data
        server = self.fake_client.servers.create(self.instance_id,
                                                 host="fake-host",
                                                 ha_enabled=True,
                                                 vm_state="active")

        def fake_stop_server_conflict(context, uuid):
            # assume that while stopping instance goes into error state
            setattr(server, 'OS-EXT-STS:vm_state', "error")
            raise exception.Conflict(reason="Cannot 'stop' instance 1 "
                                            "while it is in vm_state error")

        # test StopInstanceTask
        task = instance_failure.StopInstanceTask(self.ctxt, self.novaclient)
        with mock.patch.object(self.novaclient, 'stop_server',
                               fake_stop_server_conflict):
            self.assertRaises(
                exception.Conflict, task.execute, self.instance_id)

        # verify progress details
        _mock_notify.assert_has_calls([
            mock.call('Stopping instance: ' + self.instance_id),
            mock.call('Conflict when stopping instance: ' + self.instance_id)
        ])

    @mock.patch('masakari.compute.nova.novaclient')
    @mock.patch('masakari.engine.drivers.taskflow.base.MasakariTask.'
                'update_details')
    def test_instance_failure_flow_stop_conflict_instance_already_stoppped(
            self, _mock_notify, _mock_novaclient):
        _mock_novaclient.return_value = self.fake_client

        # create test data
        server = self.fake_client.servers.create(self.instance_id,
                                                 host="fake-host",
                                                 ha_enabled=True,
                                                 vm_state="active")

        def fake_stop_server_conflict(context, uuid):
            # assume that while stopping instance goes into stopped state
            setattr(server, 'OS-EXT-STS:vm_state', "stopped")
            raise exception.Conflict(reason="Cannot 'stop' instance 1 "
                                            "while it is in vm_state stopped")

        # test StopInstanceTask
        task = instance_failure.StopInstanceTask(self.ctxt, self.novaclient)
        with mock.patch.object(self.novaclient, 'stop_server',
                               fake_stop_server_conflict):
            task.execute(self.instance_id)

        # verify progress details
        _mock_notify.assert_has_calls([
            mock.call('Stopping instance: ' + self.instance_id),
            mock.call('Conflict when stopping instance: ' + self.instance_id),
            mock.call("Stopped instance: '" + self.instance_id + "'", 1.0)
        ])

    @mock.patch('masakari.compute.nova.novaclient')
    @mock.patch('masakari.engine.drivers.taskflow.base.MasakariTask.'
                'update_details')
    def test_instance_failure_flow_stop_failed(self, _mock_notify,
                                               _mock_novaclient):
        _mock_novaclient.return_value = self.fake_client

        # create test data
        server = self.fake_client.servers.create(self.instance_id,
                                                 host="fake-host",
                                                 ha_enabled=True)

        def fake_stop_server(context, uuid):
            # assume that while stopping instance goes into error state
            setattr(server, 'OS-EXT-STS:vm_state', "error")
            return server

        # test StopInstanceTask
        task = instance_failure.StopInstanceTask(self.ctxt, self.novaclient)
        with mock.patch.object(self.novaclient, 'stop_server',
                               fake_stop_server):
            self.assertRaises(
                exception.InstanceRecoveryFailureException, task.execute,
                self.instance_id)

        # verify progress details
        _mock_notify.assert_has_calls([
            mock.call('Stopping instance: ' + self.instance_id),
            mock.call('Failed to stop instance ' + self.instance_id, 1.0)
        ])

    @mock.patch('masakari.compute.nova.novaclient')
    @mock.patch('masakari.engine.drivers.taskflow.base.MasakariTask.'
                'update_details')
    def test_instance_failure_flow_not_ha_enabled(self, _mock_notify,
                                                  _mock_novaclient):
        _mock_novaclient.return_value = self.fake_client

        # create test data
        self.fake_client.servers.create(self.instance_id, host="fake-host")

        # test StopInstanceTask
        task = instance_failure.StopInstanceTask(self.ctxt, self.novaclient)
        self.assertRaises(
            exception.SkipInstanceRecoveryException, task.execute,
            self.instance_id)

        # verify progress details
        _mock_notify.assert_has_calls([
            mock.call('Skipping recovery for instance: ' + self.instance_id +
                      ' as it is not Ha_Enabled', 1.0)
        ])

    @mock.patch('masakari.compute.nova.novaclient')
    @mock.patch('masakari.engine.drivers.taskflow.base.MasakariTask.'
                'update_details')
    def test_instance_failure_flow_vm_in_paused_state(self, _mock_notify,
                                                  _mock_novaclient):
        _mock_novaclient.return_value = self.fake_client

        # create test data
        self.fake_client.servers.create(self.instance_id,
                                        host="fake-host", ha_enabled=True,
                                        vm_state="paused")

        # test StopInstanceTask
        task = instance_failure.StopInstanceTask(self.ctxt, self.novaclient)
        self.assertRaises(
            exception.IgnoreInstanceRecoveryException, task.execute,
            self.instance_id)

        # verify progress details
        _mock_notify.assert_has_calls([
            mock.call("Recovery of instance '" + self.instance_id +
                      "' is ignored as it is in 'paused' state.", 1.0)
        ])

    @mock.patch('masakari.compute.nova.novaclient')
    @mock.patch('masakari.engine.drivers.taskflow.base.MasakariTask.'
                'update_details')
    def test_instance_failure_flow_not_ha_enabled_but_conf_option_is_set(
            self, _mock_notify, _mock_novaclient):
        # Setting this config option to True indicates masakari has to recover
        # the instance irrespective of whether it is HA_Enabled or not.
        self.override_config("process_all_instances",
                             True, "instance_failure")
        _mock_novaclient.return_value = self.fake_client

        # create test data
        self.fake_client.servers.create(self.instance_id,
                                        host="fake-host", vm_state="resized")

        # test StopInstanceTask
        self._test_stop_instance()

        # test StartInstanceTask
        task = instance_failure.StartInstanceTask(self.ctxt, self.novaclient)
        task.execute(self.instance_id)

        # test ConfirmInstanceActiveTask
        self._test_confirm_instance_is_active()

        # verify progress details
        _mock_notify.assert_has_calls([
            mock.call('Stopping instance: ' + self.instance_id),
            mock.call("Stopped instance: '" + self.instance_id + "'", 1.0),
            mock.call("Starting instance: '" + self.instance_id + "'"),
            mock.call("Instance started: '" + self.instance_id + "'", 1.0),
            mock.call("Confirming instance '" + self.instance_id +
                      "' vm_state is ACTIVE"),
            mock.call("Confirmed instance '" + self.instance_id +
                      "' vm_state is ACTIVE", 1.0)
        ])

    @mock.patch('masakari.compute.nova.novaclient')
    @mock.patch('masakari.engine.drivers.taskflow.base.MasakariTask.'
                'update_details')
    def test_instance_failure_flow_start_failed(self, _mock_notify,
                                                _mock_novaclient):
        _mock_novaclient.return_value = self.fake_client

        # create test data
        server = self.fake_client.servers.create(self.instance_id,
                                                 host="fake-host",
                                                 ha_enabled=True)

        # test StopInstanceTask
        self._test_stop_instance()

        def fake_start_server(context, uuid):
            # assume that while starting instance goes into error state
            setattr(server, 'OS-EXT-STS:vm_state', "error")
            return server

        # test StartInstanceTask
        task = instance_failure.StartInstanceTask(self.ctxt, self.novaclient)
        with mock.patch.object(self.novaclient, 'start_server',
                               fake_start_server):
            task.execute(self.instance_id)

        # test ConfirmInstanceActiveTask
        task = instance_failure.ConfirmInstanceActiveTask(self.ctxt,
                                                          self.novaclient)
        self.assertRaises(
            exception.InstanceRecoveryFailureException, task.execute,
            self.instance_id)

        # verify progress details
        _mock_notify.assert_has_calls([
            mock.call('Stopping instance: ' + self.instance_id),
            mock.call("Stopped instance: '" + self.instance_id + "'", 1.0),
            mock.call("Starting instance: '" + self.instance_id + "'"),
            mock.call("Instance started: '" + self.instance_id + "'", 1.0),
            mock.call("Confirming instance '" + self.instance_id +
                      "' vm_state is ACTIVE"),
            mock.call('Failed to start instance 1', 1.0)
        ])
