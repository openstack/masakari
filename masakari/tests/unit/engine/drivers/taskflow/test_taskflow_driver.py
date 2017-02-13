# Copyright 2017 NTT DATA
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

import mock

from masakari import context
from masakari.engine.drivers.taskflow import base
from masakari.engine.drivers.taskflow import driver
from masakari.engine.drivers.taskflow import host_failure
from masakari import exception
from masakari.objects import fields
from masakari import test
from masakari.tests import uuidsentinel


class FakeFlow(object):
    """Fake flow class of taskflow."""

    def run(self):
        # run method which actually runs the flow
        pass


class TaskflowDriverTestCase(test.TestCase):

    def setUp(self):
        super(TaskflowDriverTestCase, self).setUp()
        self.taskflow_driver = driver.TaskFlowDriver()
        self.ctxt = context.get_admin_context()

    @mock.patch.object(base, 'DynamicLogListener')
    @mock.patch.object(host_failure, 'get_auto_flow')
    @mock.patch.object(host_failure, 'get_rh_flow')
    def test_auto_priority_recovery_flow_auto_success(
        self, mock_rh_flow, mock_auto_flow, mock_listener):
        mock_auto_flow.return_value = FakeFlow
        FakeFlow.run = mock.Mock(return_value=None)
        self.taskflow_driver.execute_host_failure(
            self.ctxt, 'fake_host',
            fields.FailoverSegmentRecoveryMethod.AUTO_PRIORITY,
            uuidsentinel.fake_notification, reserved_host_list=[
                'host-1', 'host-2'])

        # Ensures that 'auto' flow executes successfully
        self.assertTrue(mock_auto_flow.called)
        # Ensures that 'reserved_host' flow will not execute
        self.assertFalse(mock_rh_flow.called)

    @mock.patch.object(base, 'DynamicLogListener')
    @mock.patch.object(host_failure, 'get_auto_flow')
    @mock.patch.object(host_failure, 'get_rh_flow')
    def test_auto_priority_recovery_flow_rh_success(
        self, mock_rh_flow, mock_auto_flow, mock_listener):
        mock_auto_flow.return_value = FakeFlow
        FakeFlow.run = mock.Mock(
            side_effect=exception.HostRecoveryFailureException)
        self.taskflow_driver.execute_host_failure(
            self.ctxt, 'fake_host',
            fields.FailoverSegmentRecoveryMethod.AUTO_PRIORITY,
            uuidsentinel.fake_notification, reserved_host_list=[
                'host-1', 'host-2'])

        # Ensures that 'auto' flow fails to recover instances
        self.assertTrue(mock_auto_flow.called)
        # Ensures that 'reserved_host' flow executes as 'auto' flow fails
        self.assertTrue(mock_rh_flow.called)

    @mock.patch.object(base, 'DynamicLogListener')
    @mock.patch.object(host_failure, 'get_auto_flow')
    @mock.patch.object(host_failure, 'get_rh_flow')
    def test_rh_priority_recovery_flow_rh_success(
        self, mock_rh_flow, mock_auto_flow, mock_listener):
        mock_rh_flow.return_value = FakeFlow
        FakeFlow.run = mock.Mock(return_value=None)
        self.taskflow_driver.execute_host_failure(
            self.ctxt, 'fake_host',
            fields.FailoverSegmentRecoveryMethod.RH_PRIORITY,
            uuidsentinel.fake_notification, reserved_host_list=[
                'host-1', 'host-2'])

        # Ensures that 'reserved_host' flow executes successfully
        self.assertTrue(mock_rh_flow.called)
        # Ensures that 'auto' flow will not execute
        self.assertFalse(mock_auto_flow.called)

    @mock.patch.object(base, 'DynamicLogListener')
    @mock.patch.object(host_failure, 'get_auto_flow')
    @mock.patch.object(host_failure, 'get_rh_flow')
    def test_rh_priority_recovery_flow_auto_success(
        self, mock_rh_flow, mock_auto_flow, mock_listener):
        mock_rh_flow.return_value = FakeFlow
        FakeFlow.run = mock.Mock(
            side_effect=exception.HostRecoveryFailureException)
        self.taskflow_driver.execute_host_failure(
            self.ctxt, 'fake_host',
            fields.FailoverSegmentRecoveryMethod.RH_PRIORITY,
            uuidsentinel.fake_notification, reserved_host_list=[
                'host-1', 'host-2'])

        # Ensures that 'reserved_host' flow fails to recover instances
        self.assertTrue(mock_rh_flow.called)
        # Ensures that 'auto' flow executes as 'reserved_host' flow fails
        self.assertTrue(mock_auto_flow.called)

    @mock.patch.object(base, 'DynamicLogListener')
    @mock.patch.object(host_failure, 'get_auto_flow')
    @mock.patch.object(host_failure, 'get_rh_flow')
    def test_complete_auto_priority_recovery_flow_failure(
        self, mock_rh_flow, mock_auto_flow, mock_listener):

        mock_auto_flow.return_value = FakeFlow
        mock_rh_flow.return_value = FakeFlow
        FakeFlow.run = mock.Mock(
            side_effect=exception.HostRecoveryFailureException)

        # Ensures that both 'auto' and 'reserved_host' flow fails to
        # evacuate instances
        self.assertRaises(
            exception.HostRecoveryFailureException,
            self.taskflow_driver.execute_host_failure, self.ctxt, 'fake_host',
            fields.FailoverSegmentRecoveryMethod.AUTO_PRIORITY,
            uuidsentinel.fake_notification,
            reserved_host_list=['host-1', 'host-2'])

    @mock.patch.object(base, 'DynamicLogListener')
    @mock.patch.object(host_failure, 'get_auto_flow')
    @mock.patch.object(host_failure, 'get_rh_flow')
    def test_complete_rh_priority_recovery_flow_failure(
        self, mock_rh_flow, mock_auto_flow, mock_listener):

        mock_rh_flow.return_value = FakeFlow
        mock_auto_flow.return_value = FakeFlow
        FakeFlow.run = mock.Mock(
            side_effect=exception.HostRecoveryFailureException)

        # Ensures that both 'reserved_host' and 'auto' flow fails to
        # evacuate instances
        self.assertRaises(
            exception.HostRecoveryFailureException,
            self.taskflow_driver.execute_host_failure, self.ctxt, 'fake_host',
            fields.FailoverSegmentRecoveryMethod.RH_PRIORITY,
            uuidsentinel.fake_notification,
            reserved_host_list=['host-1', 'host-2'])

    @mock.patch.object(base, 'DynamicLogListener')
    @mock.patch.object(host_failure, 'get_auto_flow')
    @mock.patch.object(host_failure, 'get_rh_flow')
    def test_rh_priority_recovery_flow_skip_recovery(
        self, mock_rh_flow, mock_auto_flow, mock_listener):

        mock_rh_flow.return_value = FakeFlow
        FakeFlow.run = mock.Mock(
            side_effect=exception.SkipHostRecoveryException)

        self.assertRaises(
            exception.SkipHostRecoveryException,
            self.taskflow_driver.execute_host_failure, self.ctxt, 'fake_host',
            fields.FailoverSegmentRecoveryMethod.RH_PRIORITY,
            uuidsentinel.fake_notification,
            reserved_host_list=['host-1', 'host-2'])

        # Ensures that 'reserved_host' flow executes but skip the host
        # recovery
        self.assertTrue(mock_rh_flow.called)
        # Ensures that 'auto' flow will not execute
        self.assertFalse(mock_auto_flow.called)

    @mock.patch.object(base, 'DynamicLogListener')
    @mock.patch.object(host_failure, 'get_auto_flow')
    @mock.patch.object(host_failure, 'get_rh_flow')
    def test_auto_priority_recovery_flow_skip_recovery(
        self, mock_rh_flow, mock_auto_flow, mock_listener):

        mock_auto_flow.return_value = FakeFlow
        FakeFlow.run = mock.Mock(
            side_effect=exception.SkipHostRecoveryException)

        self.assertRaises(
            exception.SkipHostRecoveryException,
            self.taskflow_driver.execute_host_failure, self.ctxt, 'fake_host',
            fields.FailoverSegmentRecoveryMethod.AUTO_PRIORITY,
            uuidsentinel.fake_notification,
            reserved_host_list=['host-1', 'host-2'])

        # Ensures that 'auto' flow executes but skip the host recovery
        self.assertTrue(mock_auto_flow.called)
        # Ensures that 'reserved_host' flow will not execute
        self.assertFalse(mock_rh_flow.called)

    @mock.patch.object(base, 'DynamicLogListener')
    @mock.patch.object(host_failure, 'get_auto_flow')
    @mock.patch.object(host_failure, 'get_rh_flow')
    def test_rh_priority_recovery_flow_reserved_hosts_not_available(
        self, mock_rh_flow, mock_auto_flow, mock_listener):

        self.taskflow_driver.execute_host_failure(
            self.ctxt, 'fake_host',
            fields.FailoverSegmentRecoveryMethod.RH_PRIORITY,
            uuidsentinel.fake_notification)

        # Ensures that if there are no reserved_hosts for recovery
        # 'reserved_host' flow will not execute
        self.assertFalse(mock_rh_flow.called)
        # Ensures that 'auto' flow executes as 'reserved_host' flow fails
        self.assertTrue(mock_auto_flow.called)
