# All Rights Reserved.
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

import mock
from oslo_utils import importutils
from oslo_utils import timeutils

import masakari.conf
from masakari import context
from masakari import exception
from masakari.objects import fields
from masakari.objects import host as host_obj
from masakari.objects import notification as notification_obj
from masakari import test
from masakari.tests.unit import fakes
from masakari.tests import uuidsentinel

CONF = masakari.conf.CONF

NOW = timeutils.utcnow().replace(microsecond=0)


def _get_vm_type_notification(status="new"):
    return fakes.create_fake_notification(
        type="VM", id=1, payload={
            'event': 'LIFECYCLE', 'instance_uuid': uuidsentinel.fake_ins,
            'vir_domain_event': 'STOPPED_FAILED'
        },
        source_host_uuid=uuidsentinel.fake_host,
        generated_time=NOW, status=status,
        notification_uuid=uuidsentinel.fake_notification)


@mock.patch.object(notification_obj.Notification, "get_by_uuid")
class EngineManagerUnitTestCase(test.NoDBTestCase):
    def setUp(self):
        super(EngineManagerUnitTestCase, self).setUp()
        self.engine = importutils.import_object(CONF.engine_manager)
        self.context = context.RequestContext()

    def _fake_notification_workflow(self, exc=None):
        if exc:
            return exc
        # else the workflow executed successfully

    def _get_process_type_notification(self):
        return fakes.create_fake_notification(
            type="PROCESS", id=1, payload={
                'event': 'stopped', 'process_name': 'fake_service'
            },
            source_host_uuid=uuidsentinel.fake_host,
            generated_time=NOW, status="new",
            notification_uuid=uuidsentinel.fake_notification)

    def _get_compute_host_type_notification(self):
        return fakes.create_fake_notification(
            type="COMPUTE_HOST", id=1, payload={
                'event': 'stopped', 'host_status': 'NORMAL',
                'cluster_status': 'ONLINE'
            },
            source_host_uuid=uuidsentinel.fake_host,
            generated_time=NOW, status="new",
            notification_uuid=uuidsentinel.fake_notification)

    @mock.patch("masakari.engine.drivers.taskflow."
                "TaskFlowDriver.execute_instance_failure")
    @mock.patch.object(notification_obj.Notification, "save")
    def test_process_notification_type_vm_success(self, mock_save,
                             mock_instance_failure, mock_notification_get):
        mock_instance_failure.side_effect = self._fake_notification_workflow()
        notification = _get_vm_type_notification()
        mock_notification_get.return_value = notification
        self.engine.process_notification(self.context,
                                         notification=notification)
        self.assertEqual("finished", notification.status)
        mock_instance_failure.assert_called_once_with(
            self.context, notification.payload.get('instance_uuid'),
            notification.notification_uuid)

    @mock.patch("masakari.engine.drivers.taskflow."
                "TaskFlowDriver.execute_instance_failure")
    @mock.patch.object(notification_obj.Notification, "save")
    def test_process_notification_type_vm_error(self, mock_save,
                             mock_instance_failure, mock_notification_get):
        mock_instance_failure.side_effect = self._fake_notification_workflow(
            exc=exception.InstanceRecoveryFailureException)
        notification = _get_vm_type_notification()
        mock_notification_get.return_value = notification
        self.engine.process_notification(self.context,
                                         notification=notification)
        self.assertEqual("error", notification.status)
        mock_instance_failure.assert_called_once_with(
            self.context, notification.payload.get('instance_uuid'),
            notification.notification_uuid)

    @mock.patch.object(notification_obj.Notification, "save")
    def test_process_notification_type_vm_error_event_unmatched(
            self, mock_save, mock_notification_get):
        notification = fakes.create_fake_notification(
            type="VM", id=1, payload={
                'event': 'fake_event', 'instance_uuid': uuidsentinel.fake_ins,
                'vir_domain_event': 'fake_vir_domain_event'
            },
            source_host_uuid=uuidsentinel.fake_host,
            generated_time=NOW, status="new",
            notification_uuid=uuidsentinel.fake_notification)

        mock_notification_get.return_value = notification
        self.engine.process_notification(self.context,
                                         notification=notification)
        self.assertEqual("ignored", notification.status)

    @mock.patch("masakari.engine.drivers.taskflow."
                "TaskFlowDriver.execute_instance_failure")
    @mock.patch.object(notification_obj.Notification, "save")
    def test_process_notification_type_vm_skip_recovery(
            self, mock_save, mock_instance_failure, mock_notification_get):
        notification = _get_vm_type_notification()
        mock_notification_get.return_value = notification
        mock_instance_failure.side_effect = self._fake_notification_workflow(
            exc=exception.SkipInstanceRecoveryException)
        self.engine.process_notification(self.context,
                                         notification=notification)
        self.assertEqual("finished", notification.status)
        mock_instance_failure.assert_called_once_with(
            self.context, notification.payload.get('instance_uuid'),
            notification.notification_uuid)

    @mock.patch.object(host_obj.Host, "get_by_uuid")
    @mock.patch.object(host_obj.Host, "save")
    @mock.patch("masakari.engine.drivers.taskflow."
                "TaskFlowDriver.execute_process_failure")
    @mock.patch.object(notification_obj.Notification, "save")
    def test_process_notification_type_process_event_stopped(
            self, mock_notification_save, mock_process_failure,
            mock_host_save, mock_host_obj, mock_notification_get):
        notification = self._get_process_type_notification()
        mock_notification_get.return_value = notification
        mock_process_failure.side_effect = self._fake_notification_workflow()
        fake_host = fakes.create_fake_host()
        mock_host_obj.return_value = fake_host
        self.engine.process_notification(self.context,
                                         notification=notification)
        self.assertEqual("finished", notification.status)
        mock_process_failure.assert_called_once_with(
            self.context, notification.payload.get('process_name'),
            fake_host.name,
            notification.notification_uuid)

    @mock.patch.object(host_obj.Host, "get_by_uuid")
    @mock.patch.object(host_obj.Host, "save")
    @mock.patch("masakari.engine.drivers.taskflow."
                "TaskFlowDriver.execute_process_failure")
    @mock.patch.object(notification_obj.Notification, "save")
    def test_process_notification_type_process_skip_recovery(
            self, mock_notification_save, mock_process_failure,
            mock_host_save, mock_host_obj, mock_notification_get):
        notification = self._get_process_type_notification()
        mock_notification_get.return_value = notification
        fake_host = fakes.create_fake_host()
        mock_host_obj.return_value = fake_host
        mock_process_failure.side_effect = self._fake_notification_workflow(
            exc=exception.SkipProcessRecoveryException)
        self.engine.process_notification(self.context,
                                         notification=notification)
        self.assertEqual("finished", notification.status)

    @mock.patch.object(host_obj.Host, "get_by_uuid")
    @mock.patch.object(host_obj.Host, "save")
    @mock.patch("masakari.engine.drivers.taskflow."
                "TaskFlowDriver.execute_process_failure")
    @mock.patch.object(notification_obj.Notification, "save")
    def test_process_notification_type_process_recovery_failure(
            self, mock_notification_save, mock_process_failure,
            mock_host_save, mock_host_obj, mock_notification_get):
        notification = self._get_process_type_notification()
        mock_notification_get.return_value = notification
        fake_host = fakes.create_fake_host()
        mock_host_obj.return_value = fake_host
        mock_process_failure.side_effect = self._fake_notification_workflow(
            exc=exception.ProcessRecoveryFailureException)
        self.engine.process_notification(self.context,
                                         notification=notification)
        self.assertEqual("error", notification.status)

    @mock.patch.object(host_obj.Host, "get_by_uuid")
    @mock.patch.object(host_obj.Host, "save")
    @mock.patch.object(notification_obj.Notification, "save")
    @mock.patch("masakari.engine.drivers.taskflow."
                "TaskFlowDriver.execute_process_failure")
    def test_process_notification_type_process_event_started(
            self, mock_process_failure, mock_notification_save,
            mock_host_save, mock_host_obj, mock_notification_get):
        notification = self._get_process_type_notification()
        mock_notification_get.return_value = notification
        notification.payload['event'] = 'started'
        fake_host = fakes.create_fake_host()
        mock_host_obj.return_value = fake_host
        self.engine.process_notification(self.context,
                                         notification=notification)
        self.assertEqual("finished", notification.status)
        self.assertFalse(mock_process_failure.called)

    @mock.patch.object(notification_obj.Notification, "save")
    @mock.patch("masakari.engine.drivers.taskflow."
                "TaskFlowDriver.execute_process_failure")
    def test_process_notification_type_process_event_other(
            self, mock_process_failure, mock_notification_save,
            mock_notification_get):
        notification = self._get_process_type_notification()
        mock_notification_get.return_value = notification
        notification.payload['event'] = 'other'
        self.engine.process_notification(self.context,
                                         notification=notification)
        self.assertEqual("ignored", notification.status)
        self.assertFalse(mock_process_failure.called)

    @mock.patch.object(host_obj.Host, "get_by_uuid")
    @mock.patch.object(host_obj.Host, "save")
    @mock.patch.object(host_obj.Host, "update")
    @mock.patch.object(host_obj.HostList, "get_all")
    @mock.patch("masakari.engine.drivers.taskflow."
                "TaskFlowDriver.execute_host_failure")
    @mock.patch.object(notification_obj.Notification, "save")
    def test_process_notification_type_compute_host_event_stopped(
            self, mock_notification_save, mock_host_failure, mock_get_all,
            mock_host_update, mock_host_save, mock_host_obj,
            mock_notification_get):
        notification = self._get_compute_host_type_notification()
        mock_notification_get.return_value = notification
        mock_host_failure.side_effect = self._fake_notification_workflow()
        fake_host = fakes.create_fake_host()
        mock_get_all.return_value = None
        fake_host.failover_segment = fakes.create_fake_failover_segment()
        mock_host_obj.return_value = fake_host
        self.engine.process_notification(self.context,
                                         notification=notification)

        update_data_by_host_failure = {
            'on_maintenance': True,
        }
        mock_host_update.assert_called_once_with(update_data_by_host_failure)
        self.assertEqual("finished", notification.status)
        mock_host_failure.assert_called_once_with(
            self.context,
            fake_host.name, fake_host.failover_segment.recovery_method,
            notification.notification_uuid, reserved_host_list=None)

    @mock.patch.object(host_obj.Host, "get_by_uuid")
    @mock.patch.object(host_obj.Host, "save")
    @mock.patch.object(host_obj.Host, "update")
    @mock.patch.object(host_obj.HostList, "get_all")
    @mock.patch.object(notification_obj.Notification, "save")
    def test_process_notification_host_failure_without_reserved_hosts(
            self, mock_notification_save, mock_get_all,
            mock_host_update, mock_host_save, mock_host_obj,
            mock_notification_get):
        reserved_host_list = []
        mock_get_all.return_value = reserved_host_list

        fake_host = fakes.create_fake_host()
        fake_host.failover_segment = fakes.create_fake_failover_segment(
            recovery_method='reserved_host')
        mock_host_obj.return_value = fake_host

        notification = self._get_compute_host_type_notification()
        mock_notification_get.return_value = notification

        self.engine.process_notification(self.context,
                                         notification=notification)

        update_data_by_host_failure = {
            'on_maintenance': True,
        }
        mock_host_update.assert_called_once_with(update_data_by_host_failure)
        self.assertEqual("error", notification.status)

    @mock.patch.object(host_obj.Host, "get_by_uuid")
    @mock.patch.object(host_obj.Host, "save")
    @mock.patch.object(host_obj.Host, "update")
    @mock.patch.object(host_obj.HostList, "get_all")
    @mock.patch("masakari.engine.drivers.taskflow."
                "TaskFlowDriver.execute_host_failure")
    @mock.patch.object(notification_obj.Notification, "save")
    def test_process_notification_host_failure_with_reserved_hosts(
            self, mock_notification_save, mock_host_failure, mock_get_all,
            mock_host_update, mock_host_save, mock_host_obj,
            mock_notification_get):
        fake_host = fakes.create_fake_host()
        fake_host.failover_segment = fakes.create_fake_failover_segment(
            recovery_method='reserved_host')
        reserved_host_list = [fake_host]
        mock_get_all.return_value = reserved_host_list
        mock_host_obj.return_value = fake_host

        notification = self._get_compute_host_type_notification()
        mock_notification_get.return_value = notification
        mock_host_failure.side_effect = self._fake_notification_workflow()

        self.engine.process_notification(self.context,
                                         notification=notification)

        update_data_by_host_failure = {
            'on_maintenance': True,
        }
        mock_host_update.assert_called_once_with(update_data_by_host_failure)
        self.assertEqual("finished", notification.status)
        mock_host_failure.assert_called_once_with(
            self.context,
            fake_host.name, fake_host.failover_segment.recovery_method,
            notification.notification_uuid,
            reserved_host_list=reserved_host_list)
        mock_get_all.assert_called_once_with(self.context, filters={
            'failover_segment_id': fake_host.failover_segment.uuid,
            'reserved': True, 'on_maintenance': False})

    @mock.patch.object(host_obj.Host, "get_by_uuid")
    @mock.patch.object(host_obj.Host, "save")
    @mock.patch.object(host_obj.Host, "update")
    @mock.patch.object(host_obj.HostList, "get_all")
    @mock.patch("masakari.engine.drivers.taskflow."
                "TaskFlowDriver.execute_host_failure")
    @mock.patch.object(notification_obj.Notification, "save")
    def test_process_notification_reserved_host_failure(
            self, mock_notification_save, mock_host_failure, mock_get_all,
            mock_host_update, mock_host_save, mock_host_obj,
            mock_notification_get):
        fake_host = fakes.create_fake_host(reserved=True)
        fake_host.failover_segment = fakes.create_fake_failover_segment(
            recovery_method='reserved_host')
        reserved_host_list = [fake_host]
        mock_get_all.return_value = reserved_host_list
        mock_host_obj.return_value = fake_host

        notification = self._get_compute_host_type_notification()
        mock_notification_get.return_value = notification
        mock_host_failure.side_effect = self._fake_notification_workflow()

        self.engine.process_notification(self.context,
                                         notification=notification)

        update_data_by_host_failure = {
            'on_maintenance': True,
            'reserved': False,
        }
        mock_host_update.assert_called_once_with(update_data_by_host_failure)
        self.assertEqual("finished", notification.status)
        mock_host_failure.assert_called_once_with(
            self.context,
            fake_host.name, fake_host.failover_segment.recovery_method,
            notification.notification_uuid,
            reserved_host_list=reserved_host_list)

    @mock.patch.object(host_obj.Host, "get_by_uuid")
    @mock.patch.object(host_obj.Host, "save")
    @mock.patch.object(host_obj.Host, "update")
    @mock.patch.object(host_obj.HostList, "get_all")
    @mock.patch("masakari.engine.drivers.taskflow."
                "TaskFlowDriver.execute_host_failure")
    @mock.patch.object(notification_obj.Notification, "save")
    def test_process_notification_type_compute_host_recovery_exception(
            self, mock_notification_save, mock_host_failure, mock_get_all,
            mock_host_update, mock_host_save, mock_host_obj,
            mock_notification_get):
        notification = self._get_compute_host_type_notification()
        mock_notification_get.return_value = notification
        fake_host = fakes.create_fake_host()
        mock_get_all.return_value = None
        fake_host.failover_segment = fakes.create_fake_failover_segment()
        mock_host_obj.return_value = fake_host
        mock_host_failure.side_effect = self._fake_notification_workflow(
            exc=exception.HostRecoveryFailureException)
        self.engine.process_notification(self.context,
                                         notification=notification)

        update_data_by_host_failure = {
            'on_maintenance': True,
        }
        mock_host_update.assert_called_once_with(update_data_by_host_failure)
        self.assertEqual("error", notification.status)

    @mock.patch.object(notification_obj.Notification, "save")
    @mock.patch("masakari.engine.drivers.taskflow."
                "TaskFlowDriver.execute_host_failure")
    def test_process_notification_type_compute_host_event_started(
            self, mock_host_failure, mock_notification_save,
            mock_notification_get):
        notification = self._get_compute_host_type_notification()
        mock_notification_get.return_value = notification
        notification.payload['event'] = 'started'
        self.engine.process_notification(self.context,
                                         notification=notification)
        self.assertEqual("finished", notification.status)
        self.assertFalse(mock_host_failure.called)

    @mock.patch.object(notification_obj.Notification, "save")
    @mock.patch("masakari.engine.drivers.taskflow."
                "TaskFlowDriver.execute_host_failure")
    def test_process_notification_type_compute_host_event_other(
            self, mock_host_failure, mock_notification_save,
            mock_notification_get):
        notification = self._get_compute_host_type_notification()
        mock_notification_get.return_value = notification
        notification.payload['event'] = 'other'
        self.engine.process_notification(self.context,
                                         notification=notification)
        self.assertEqual("ignored", notification.status)
        self.assertFalse(mock_host_failure.called)

    @mock.patch("masakari.compute.nova.API.stop_server")
    @mock.patch.object(notification_obj.Notification, "save")
    @mock.patch("masakari.compute.nova.API.get_server")
    def test_process_notification_type_vm_ignore_instance_in_paused(
            self, mock_get_server, mock_notification_save, mock_stop_server,
            mock_notification_get):
        notification = _get_vm_type_notification()
        mock_notification_get.return_value = notification
        mock_get_server.return_value = fakes.FakeNovaClient.Server(
            id=1, uuid=uuidsentinel.fake_ins, host='fake_host',
            vm_state='paused', ha_enabled=True)

        self.engine.process_notification(self.context,
                                         notification=notification)
        self.assertEqual("ignored", notification.status)
        self.assertFalse(mock_stop_server.called)

    @mock.patch("masakari.compute.nova.API.stop_server")
    @mock.patch.object(notification_obj.Notification, "save")
    @mock.patch("masakari.compute.nova.API.get_server")
    def test_process_notification_type_vm_ignore_instance_in_rescued(
            self, mock_get_server, mock_notification_save, mock_stop_server,
            mock_notification_get):
        notification = _get_vm_type_notification()
        mock_notification_get.return_value = notification
        mock_get_server.return_value = fakes.FakeNovaClient.Server(
            id=1, uuid=uuidsentinel.fake_ins, host='fake_host',
            vm_state='rescued', ha_enabled=True)

        self.engine.process_notification(self.context,
                                         notification=notification)
        self.assertEqual("ignored", notification.status)
        self.assertFalse(mock_stop_server.called)

    def test_process_notification_stop_from_recovery_failure(self,
                                                     mock_get_noti):
        noti_new = _get_vm_type_notification()
        mock_get_noti.return_value = _get_vm_type_notification(
            status="failed")

        with mock.patch("masakari.engine.manager.LOG.warning") as mock_log:
            self.engine.process_notification(self.context,
                                             notification=noti_new)
            mock_log.assert_called_once()
            args = mock_log.call_args[0]
            expected_log = ("Processing of notification is skipped to avoid "
                            "recovering from failure twice. "
                            "Notification received is '%(uuid)s' "
                            "and it's status is '%(new_status)s' and the "
                            "current status of same notification in db "
                            "is '%(old_status)s'")
            expected_log_args_1 = {'uuid': noti_new.notification_uuid,
                                   'new_status': noti_new.status,
                                   'old_status': "failed"}

            self.assertEqual(expected_log, args[0])
            self.assertEqual(expected_log_args_1, args[1])

    @mock.patch('masakari.compute.nova.novaclient')
    @mock.patch('masakari.engine.drivers.taskflow.host_failure.'
                'DisableComputeServiceTask.execute')
    @mock.patch('masakari.engine.drivers.taskflow.host_failure.'
                'PrepareHAEnabledInstancesTask.execute')
    @mock.patch('masakari.engine.drivers.taskflow.host_failure.'
                'EvacuateInstancesTask.execute')
    @mock.patch('masakari.engine.drivers.taskflow.no_op.LOG')
    def test_host_failure_custom_flow_for_auto_recovery(
            self, _mock_log, _mock_task1, _mock_task2, _mock_task3,
            _mock_novaclient, _mock_notification_get):
        self.override_config(
            "host_auto_failure_recovery_tasks",
            {'pre': ['disable_compute_service_task', 'no_op'],
             'main': ['prepare_HA_enabled_instances_task'],
             'post': ['evacuate_instances_task']},
            "taskflow_driver_recovery_flows")

        expected_msg_format = "Custom task executed successfully..!!"

        self.engine.driver.execute_host_failure(
            self.context, 'fake_host',
            fields.FailoverSegmentRecoveryMethod.AUTO,
            uuidsentinel.fake_notification)
        # Ensure custom_task added to the 'host_auto_failure_recovery_tasks'
        # is executed.
        _mock_log.info.assert_called_with(expected_msg_format)

    @mock.patch('masakari.compute.nova.novaclient')
    @mock.patch('masakari.engine.drivers.taskflow.host_failure.'
                'DisableComputeServiceTask.execute')
    @mock.patch('masakari.engine.drivers.taskflow.host_failure.'
                'PrepareHAEnabledInstancesTask.execute')
    @mock.patch('masakari.engine.drivers.taskflow.host_failure.'
                'EvacuateInstancesTask.execute')
    @mock.patch('masakari.engine.drivers.taskflow.no_op.LOG')
    def test_host_failure_custom_flow_for_rh_recovery(
            self, _mock_log, _mock_task1, _mock_task2, _mock_task3,
            _mock_novaclient, _mock_notification_get):
        self.override_config(
            "host_rh_failure_recovery_tasks",
            {'pre': ['disable_compute_service_task'],
             'main': [],
             'post': ['no_op']},
            "taskflow_driver_recovery_flows")

        expected_msg_format = "Custom task executed successfully..!!"

        self.engine.driver.execute_host_failure(
            self.context, 'fake_host',
            fields.FailoverSegmentRecoveryMethod.RESERVED_HOST,
            uuidsentinel.fake_notification,
            reserved_host_list=['host-1', 'host-2'])
        # Ensure custom_task added to the 'host_rh_failure_recovery_tasks'
        # is executed.
        _mock_log.info.assert_called_with(expected_msg_format)

    @mock.patch('masakari.compute.nova.novaclient')
    @mock.patch('masakari.engine.drivers.taskflow.instance_failure.'
                'StopInstanceTask.execute')
    @mock.patch('masakari.engine.drivers.taskflow.instance_failure.'
                'StartInstanceTask.execute')
    @mock.patch('masakari.engine.drivers.taskflow.instance_failure.'
                'ConfirmInstanceActiveTask.execute')
    @mock.patch('masakari.engine.drivers.taskflow.no_op.LOG')
    def test_instance_failure_custom_flow_recovery(
            self, _mock_log, _mock_task1, _mock_task2, _mock_task3,
            _mock_novaclient, _mock_notification_get):
        self.override_config(
            "instance_failure_recovery_tasks",
            {'pre': ['stop_instance_task', 'no_op'],
             'main': ['start_instance_task'],
             'post': ['confirm_instance_active_task']},
            "taskflow_driver_recovery_flows")

        expected_msg_format = "Custom task executed successfully..!!"

        self.engine.driver.execute_instance_failure(
            self.context, uuidsentinel.fake_ins,
            uuidsentinel.fake_notification)
        # Ensure custom_task added to the 'instance_failure_recovery_tasks'
        # is executed.
        _mock_log.info.assert_called_with(expected_msg_format)

    @mock.patch('masakari.compute.nova.novaclient')
    @mock.patch('masakari.engine.drivers.taskflow.process_failure.'
                'DisableComputeNodeTask.execute')
    @mock.patch('masakari.engine.drivers.taskflow.process_failure.'
                'ConfirmComputeNodeDisabledTask.execute')
    @mock.patch('masakari.engine.drivers.taskflow.no_op.LOG')
    def test_process_failure_custom_flow_recovery(
            self, _mock_log, _mock_task1, _mock_task2, _mock_novaclient,
            _mock_notification_get):
        self.override_config(
            "process_failure_recovery_tasks",
            {'pre': ['disable_compute_node_task', 'no_op'],
             'main': ['confirm_compute_node_disabled_task'],
             'post': []},
            "taskflow_driver_recovery_flows")

        expected_msg_format = "Custom task executed successfully..!!"

        self.engine.driver.execute_process_failure(
            self.context, 'nova-compute', 'fake_host',
            uuidsentinel.fake_notification)
        _mock_log.info.assert_any_call(expected_msg_format)
        # Ensure custom_task added to the 'process_failure_recovery_tasks'
        # is executed.
        _mock_log.info.assert_called_with(expected_msg_format)
