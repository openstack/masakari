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

from unittest import mock

from oslo_utils import timeutils
from taskflow.persistence import models
from taskflow.persistence import path_based

from masakari import context
from masakari.engine.drivers.taskflow import base
from masakari.engine.drivers.taskflow import driver
from masakari.engine.drivers.taskflow import host_failure
from masakari import exception
from masakari.objects import fields
from masakari import test
from masakari.tests.unit import fakes
from masakari.tests import uuidsentinel


NOW = timeutils.utcnow().replace(microsecond=0)


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

    @mock.patch.object(path_based.PathBasedConnection, 'get_atoms_for_flow')
    @mock.patch.object(path_based.PathBasedConnection, 'get_flows_for_book')
    def test_get_notification_recovery_workflow_details(
            self, mock_get_flows_for_book, mock_get_atoms_for_flow):

        notification = fakes.create_fake_notification(
            payload={
                'event': 'LIFECYCLE', 'instance_uuid': uuidsentinel.fake_ins,
                'vir_domain_event': 'STOPPED_FAILED'},
            source_host_uuid=uuidsentinel.fake_host,
            notification_uuid=uuidsentinel.fake_notification)

        fd = models.FlowDetail('test', uuid=notification.notification_uuid)
        atom1 = models.TaskDetail('StopInstanceTask',
                                  uuid=uuidsentinel.atom_id_1)
        atom1.meta = {
            'progress': 1.0,
            'progress_details': {
                'at_progress': 1.0,
                'details': {
                    'progress_details': [
                        {'timestamp': '2019-03-11 05:22:20.329171',
                         'message': 'Stopping instance: '
                                    '87c8ebc3-2a70-49f0-9280-d34662dc203d',
                         'progress': 0.0},
                        {'timestamp': '2019-03-11 05:22:28.902665',
                         'message': "Stopped instance: "
                                    "'87c8ebc3-2a70-49f0-9280-d34662dc203d'",
                         'progress': 1.0}]}}}
        atom1.state = 'SUCCESS'

        atom2 = models.TaskDetail('ConfirmInstanceActiveTask',
                                  uuid=uuidsentinel.atom_id_2)
        atom2.meta = {
            'progress': 1.0,
            'progress_details': {
                'at_progress': 1.0,
                'details': {
                    'progress_details': [
                        {'timestamp': '2019-03-11 05:22:29.597303',
                         'message': "Confirming instance "
                                    "'87c8ebc3-2a70-49f0-9280-d34662dc203d' "
                                    "vm_state is ACTIVE",
                         'progress': 0.0},
                        {'timestamp': '2019-03-11 05:22:31.916620',
                         'message': "Confirmed instance "
                                    "'87c8ebc3-2a70-49f0-9280-d34662dc203d'"
                                    " vm_state is ACTIVE", 'progress': 1.0}]
                }}}
        atom2.state = 'SUCCESS'

        atom3 = models.TaskDetail('StartInstanceTask',
                                  uuid=uuidsentinel.atom_id_3)
        atom3.meta = {
            'progress': 1.0,
            'progress_details': {
                'at_progress': 1.0,
                'details': {'progress_details': [
                    {'timestamp': '2019-03-11 05:22:29.130876',
                     'message': "Starting instance: "
                                "'87c8ebc3-2a70-49f0-9280-d34662dc203d'",
                     'progress': 0.0},
                    {'timestamp': '2019-03-11 05:22:29.525882', 'message':
                        "Instance started: "
                        "'87c8ebc3-2a70-49f0-9280-d34662dc203d'", 'progress':
                        1.0}]}}}
        atom3.state = 'SUCCESS'

        def fd_generator():
            yield fd

        def atom_detail_generator():
            for atom in [atom1, atom2, atom3]:
                yield atom

        flow_details = fd_generator()
        atom_details = atom_detail_generator()
        mock_get_flows_for_book.return_value = flow_details
        mock_get_atoms_for_flow.return_value = atom_details
        driver.PERSISTENCE_BACKEND = 'memory://'

        progress_details = (
            self.taskflow_driver.get_notification_recovery_workflow_details(
                self.ctxt, 'auto', notification))

        # list of NotificationProgressDetails object
        expected_result = []
        expected_result.append((
            fakes.create_fake_notification_progress_details(
                name=atom1.name,
                uuid=atom1.uuid,
                progress=atom1.meta['progress'],
                state=atom1.state,
                progress_details=atom1.meta['progress_details']
                ['details']['progress_details'])))
        expected_result.append((
            fakes.create_fake_notification_progress_details(
                name=atom3.name,
                uuid=atom3.uuid,
                progress=atom3.meta['progress'],
                state=atom3.state,
                progress_details=atom3.meta['progress_details']
                ['details']['progress_details'])))
        expected_result.append((
            fakes.create_fake_notification_progress_details(
                name=atom2.name,
                uuid=atom2.uuid,
                progress=atom2.meta['progress'],
                state=atom2.state,
                progress_details=atom2.meta['progress_details']
                ['details']['progress_details'])))

        self.assertIsNotNone(progress_details)
        mock_get_flows_for_book.assert_called_once()
        mock_get_atoms_for_flow.assert_called_once()

        self.assertObjectList(expected_result, progress_details)

    @mock.patch.object(path_based.PathBasedConnection, 'get_atoms_for_flow')
    @mock.patch.object(path_based.PathBasedConnection, 'get_flows_for_book')
    def test_get_notification_recovery_workflow_details_raises_keyerror(
            self, mock_get_flows_for_book, mock_get_atoms_for_flow):

        notification = fakes.create_fake_notification(
            payload={
                'event': 'LIFECYCLE', 'instance_uuid': uuidsentinel.fake_ins,
                'vir_domain_event': 'STOPPED_FAILED'},
            source_host_uuid=uuidsentinel.fake_host,
            notification_uuid=uuidsentinel.fake_notification)

        fd = models.FlowDetail('test', uuid=notification.notification_uuid)
        atom1 = models.TaskDetail('StopInstanceTask',
                                  uuid=uuidsentinel.atom_id_1)
        atom1.meta = {
            'progress': 1.0,
            'progress_details': {
                'at_progress': 1.0,
                'details': {
                    'progress_details': [
                        {'timestamp': '2019-03-11 05:22:20.329171',
                         'message': 'Stopping instance: '
                                    '87c8ebc3-2a70-49f0-9280-d34662dc203d',
                         'progress': 0.0},
                        {'timestamp': '2019-03-11 05:22:28.902665',
                         'message': "Stopped instance: "
                                    "'87c8ebc3-2a70-49f0-9280-d34662dc203d'",
                         'progress': 1.0}]}}}
        atom1.state = 'SUCCESS'

        atom2 = models.TaskDetail('ConfirmInstanceActiveTask',
                                  uuid=uuidsentinel.atom_id_2)
        atom2.meta = {
            'progress': 1.0,
            'progress_details': {
                'at_progress': 1.0,
                'details': {
                    'progress_details': [
                        {'timestamp': '2019-03-11 05:22:29.597303',
                         'message': "Confirming instance "
                                    "'87c8ebc3-2a70-49f0-9280-d34662dc203d' "
                                    "vm_state is ACTIVE",
                         'progress': 0.0},
                        {'timestamp': '2019-03-11 05:22:31.916620',
                         'message': "Confirmed instance "
                                    "'87c8ebc3-2a70-49f0-9280-d34662dc203d'"
                                    " vm_state is ACTIVE", 'progress': 1.0}]
                }}}
        atom2.state = 'SUCCESS'

        atom3 = models.TaskDetail('StartInstanceTask',
                                  uuid=uuidsentinel.atom_id_3)
        atom3.state = 'RUNNING'

        def fd_generator():
            yield fd

        def atom_detail_generator():
            for atom in [atom1, atom2, atom3]:
                yield atom

        flow_details = fd_generator()
        atom_details = atom_detail_generator()
        mock_get_flows_for_book.return_value = flow_details
        mock_get_atoms_for_flow.return_value = atom_details
        driver.PERSISTENCE_BACKEND = 'memory://'

        progress_details = (
            self.taskflow_driver.get_notification_recovery_workflow_details(
                self.ctxt, 'auto', notification))

        # list of NotificationProgressDetails object
        expected_result = []
        expected_result.append((
            fakes.create_fake_notification_progress_details(
                name=atom1.name,
                uuid=atom1.uuid,
                progress=atom1.meta['progress'],
                state=atom1.state,
                progress_details=atom1.meta['progress_details']
                ['details']['progress_details'])))
        expected_result.append((
            fakes.create_fake_notification_progress_details(
                name=atom2.name,
                uuid=atom2.uuid,
                progress=atom2.meta['progress'],
                state=atom2.state,
                progress_details=atom2.meta['progress_details']
                ['details']['progress_details'])))

        self.assertIsNotNone(progress_details)
        mock_get_flows_for_book.assert_called_once()
        mock_get_atoms_for_flow.assert_called_once()

        self.assertObjectList(expected_result, progress_details)
