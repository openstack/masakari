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

import datetime
from unittest import mock

from oslo_utils import importutils
from oslo_utils import timeutils

from masakari.compute import nova
import masakari.conf
from masakari import context
from masakari.engine import manager
from masakari.engine import utils as engine_utils
from masakari import exception
from masakari.objects import fields
from masakari.objects import host as host_obj
from masakari.objects import notification as notification_obj
from masakari import rpc
from masakari import test
from masakari.tests.unit import fakes
from masakari.tests import uuidsentinel

CONF = masakari.conf.CONF

NOW = timeutils.utcnow().replace(microsecond=0)
EXPIRED_TIME = timeutils.utcnow().replace(microsecond=0) \
    - datetime.timedelta(seconds=CONF.notifications_expired_interval)


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
        rpc.init(CONF)
        self.engine = importutils.import_object(CONF.engine_manager)
        self.context = context.RequestContext()

    def _fake_notification_workflow(self, exc=None):
        if exc:
            return exc
        # else the workflow executed successfully

    def _get_fake_host(self, segment_enabled):
        segment = fakes.create_fake_failover_segment(enabled=segment_enabled)
        host = fakes.create_fake_host()
        host.failover_segment = segment
        return host

    def _get_process_type_notification(self):
        return fakes.create_fake_notification(
            type="PROCESS", id=1, payload={
                'event': 'stopped', 'process_name': 'fake_service'
            },
            source_host_uuid=uuidsentinel.fake_host,
            generated_time=NOW, status="new",
            notification_uuid=uuidsentinel.fake_notification)

    def _get_compute_host_type_notification(self, expired=False):
        return fakes.create_fake_notification(
            type="COMPUTE_HOST", id=1, payload={
                'event': 'stopped', 'host_status': 'NORMAL',
                'cluster_status': 'ONLINE'
            },
            source_host_uuid=uuidsentinel.fake_host,
            generated_time=EXPIRED_TIME if expired else NOW,
            status="new",
            notification_uuid=uuidsentinel.fake_notification)

    @mock.patch.object(host_obj.Host, "get_by_uuid")
    @mock.patch.object(notification_obj.Notification, "save")
    @mock.patch.object(engine_utils, 'notify_about_notification_update')
    def test_process_notification_with_segment_disabled(
            self, mock_notify_about_notification_update,
            mock_notification_save, mock_host_get, mock_notification_get):
        notification = _get_vm_type_notification()
        mock_notification_get.return_value = notification
        mock_host_get.return_value = self._get_fake_host(
            segment_enabled=False)
        self.assertRaises(exception.FailoverSegmentDisabled,
                          self.engine.process_notification,
                          self.context, notification)

    @mock.patch("masakari.engine.drivers.taskflow."
                "TaskFlowDriver.execute_instance_failure")
    @mock.patch.object(notification_obj.Notification, "save")
    @mock.patch.object(engine_utils, 'notify_about_notification_update')
    def test_process_notification_type_vm_success(self,
                            mock_notify_about_notification_update, mock_save,
                            mock_instance_failure, mock_notification_get):
        mock_instance_failure.side_effect = self._fake_notification_workflow()
        notification = _get_vm_type_notification()
        mock_notification_get.return_value = notification
        self.engine._process_notification(self.context,
                                          notification=notification)
        self.assertEqual("finished", notification.status)
        mock_instance_failure.assert_called_once_with(
            self.context, notification.payload.get('instance_uuid'),
            notification.notification_uuid)
        action = fields.EventNotificationAction.NOTIFICATION_PROCESS
        phase_start = fields.EventNotificationPhase.START
        phase_end = fields.EventNotificationPhase.END
        notify_calls = [
            mock.call(self.context, notification, action=action,
                      phase=phase_start),
            mock.call(self.context, notification, action=action,
                      phase=phase_end)]
        mock_notify_about_notification_update.assert_has_calls(notify_calls)

    @mock.patch("masakari.engine.drivers.taskflow."
                "TaskFlowDriver.execute_instance_failure")
    @mock.patch.object(notification_obj.Notification, "save")
    @mock.patch.object(engine_utils, 'notify_about_notification_update')
    @mock.patch('traceback.format_exc')
    def test_process_notification_type_vm_error(self, mock_format,
                            mock_notify_about_notification_update, mock_save,
                            mock_instance_failure, mock_notification_get):
        mock_format.return_value = mock.ANY
        mock_instance_failure.side_effect = self._fake_notification_workflow(
            exc=exception.InstanceRecoveryFailureException)
        notification = _get_vm_type_notification()
        mock_notification_get.return_value = notification
        self.engine._process_notification(self.context,
                                          notification=notification)
        self.assertEqual("error", notification.status)
        mock_instance_failure.assert_called_once_with(
            self.context, notification.payload.get('instance_uuid'),
            notification.notification_uuid)
        e = exception.InstanceRecoveryFailureException('Failed to execute '
                                                'instance recovery workflow.')
        action = fields.EventNotificationAction.NOTIFICATION_PROCESS
        phase_start = fields.EventNotificationPhase.START
        phase_error = fields.EventNotificationPhase.ERROR
        notify_calls = [
            mock.call(self.context, notification, action=action,
                      phase=phase_start),
            mock.call(self.context, notification, action=action,
                      phase=phase_error,
                      exception=str(e),
                      tb=mock.ANY)]
        mock_notify_about_notification_update.assert_has_calls(notify_calls)

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
        self.engine._process_notification(self.context,
                                          notification=notification)
        self.assertEqual("ignored", notification.status)

    @mock.patch("masakari.engine.drivers.taskflow."
                "TaskFlowDriver.execute_instance_failure")
    @mock.patch.object(notification_obj.Notification, "save")
    @mock.patch.object(engine_utils, 'notify_about_notification_update')
    @mock.patch('traceback.format_exc')
    def test_process_notification_type_vm_skip_recovery(
            self, mock_format, mock_notify_about_notification_update,
            mock_save, mock_instance_failure, mock_notification_get):
        mock_format.return_value = mock.ANY
        notification = _get_vm_type_notification()
        mock_notification_get.return_value = notification
        mock_instance_failure.side_effect = self._fake_notification_workflow(
            exc=exception.SkipInstanceRecoveryException)
        self.engine._process_notification(self.context,
                                          notification=notification)
        self.assertEqual("finished", notification.status)
        mock_instance_failure.assert_called_once_with(
            self.context, notification.payload.get('instance_uuid'),
            notification.notification_uuid)
        action = fields.EventNotificationAction.NOTIFICATION_PROCESS
        phase_start = fields.EventNotificationPhase.START
        phase_end = fields.EventNotificationPhase.END
        notify_calls = [
            mock.call(self.context, notification, action=action,
                      phase=phase_start),
            mock.call(self.context, notification, action=action,
                      phase=phase_end)]
        mock_notify_about_notification_update.assert_has_calls(notify_calls)

    @mock.patch.object(host_obj.Host, "get_by_uuid")
    @mock.patch.object(host_obj.Host, "save")
    @mock.patch("masakari.engine.drivers.taskflow."
                "TaskFlowDriver.execute_process_failure")
    @mock.patch.object(notification_obj.Notification, "save")
    @mock.patch.object(engine_utils, 'notify_about_notification_update')
    def test_process_notification_type_process_event_stopped(
            self, mock_notify_about_notification_update,
            mock_notification_save, mock_process_failure,
            mock_host_save, mock_host_obj, mock_notification_get):
        notification = self._get_process_type_notification()
        mock_notification_get.return_value = notification
        mock_process_failure.side_effect = self._fake_notification_workflow()
        fake_host = fakes.create_fake_host()
        mock_host_obj.return_value = fake_host
        self.engine._process_notification(self.context,
                                          notification=notification)
        self.assertEqual("finished", notification.status)
        mock_host_save.assert_called_once()
        mock_process_failure.assert_called_once_with(
            self.context, notification.payload.get('process_name'),
            fake_host.name,
            notification.notification_uuid)
        action = fields.EventNotificationAction.NOTIFICATION_PROCESS
        phase_start = fields.EventNotificationPhase.START
        phase_end = fields.EventNotificationPhase.END
        notify_calls = [
            mock.call(self.context, notification, action=action,
                      phase=phase_start),
            mock.call(self.context, notification, action=action,
                      phase=phase_end)]
        mock_notify_about_notification_update.assert_has_calls(notify_calls)

    @mock.patch.object(host_obj.Host, "get_by_uuid")
    @mock.patch.object(host_obj.Host, "save")
    @mock.patch("masakari.engine.drivers.taskflow."
                "TaskFlowDriver.execute_process_failure")
    @mock.patch.object(notification_obj.Notification, "save")
    @mock.patch.object(engine_utils, 'notify_about_notification_update')
    @mock.patch('traceback.format_exc')
    def test_process_notification_type_process_skip_recovery(
            self, mock_format, mock_notify_about_notification_update,
            mock_notification_save, mock_process_failure,
            mock_host_save, mock_host_obj, mock_notification_get):
        mock_format.return_value = mock.ANY
        notification = self._get_process_type_notification()
        mock_notification_get.return_value = notification
        fake_host = fakes.create_fake_host()
        mock_host_obj.return_value = fake_host
        mock_process_failure.side_effect = self._fake_notification_workflow(
            exc=exception.SkipProcessRecoveryException)
        self.engine._process_notification(self.context,
                                          notification=notification)
        self.assertEqual("finished", notification.status)
        mock_host_save.assert_called_once()
        action = fields.EventNotificationAction.NOTIFICATION_PROCESS
        phase_start = fields.EventNotificationPhase.START
        phase_end = fields.EventNotificationPhase.END
        notify_calls = [
            mock.call(self.context, notification, action=action,
                      phase=phase_start),
            mock.call(self.context, notification, action=action,
                      phase=phase_end)]
        mock_notify_about_notification_update.assert_has_calls(notify_calls)

    @mock.patch.object(host_obj.Host, "get_by_uuid")
    @mock.patch.object(host_obj.Host, "save")
    @mock.patch("masakari.engine.drivers.taskflow."
                "TaskFlowDriver.execute_process_failure")
    @mock.patch.object(notification_obj.Notification, "save")
    @mock.patch.object(engine_utils, 'notify_about_notification_update')
    @mock.patch('traceback.format_exc')
    def test_process_notification_type_process_recovery_failure(
            self, mock_format, mock_notify_about_notification_update,
            mock_notification_save, mock_process_failure,
            mock_host_save, mock_host_obj, mock_notification_get):
        mock_format.return_value = mock.ANY
        notification = self._get_process_type_notification()
        mock_notification_get.return_value = notification
        fake_host = fakes.create_fake_host()
        mock_host_obj.return_value = fake_host
        mock_process_failure.side_effect = self._fake_notification_workflow(
            exc=exception.ProcessRecoveryFailureException)
        self.engine._process_notification(self.context,
                                          notification=notification)
        self.assertEqual("error", notification.status)
        mock_host_save.assert_called_once()
        e = exception.ProcessRecoveryFailureException('Failed to execute '
                                                'process recovery workflow.')
        action = fields.EventNotificationAction.NOTIFICATION_PROCESS
        phase_start = fields.EventNotificationPhase.START
        phase_error = fields.EventNotificationPhase.ERROR
        notify_calls = [
            mock.call(self.context, notification, action=action,
                      phase=phase_start),
            mock.call(self.context, notification, action=action,
                      phase=phase_error,
                      exception=str(e),
                      tb=mock.ANY)]
        mock_notify_about_notification_update.assert_has_calls(notify_calls)

    @mock.patch.object(host_obj.Host, "get_by_uuid")
    @mock.patch.object(notification_obj.Notification, "save")
    @mock.patch.object(engine_utils, 'notify_about_notification_update')
    @mock.patch("masakari.engine.drivers.taskflow."
                "TaskFlowDriver.execute_process_failure")
    def test_process_notification_type_process_event_started(
            self, mock_process_failure, mock_notify_about_notification_update,
            mock_notification_save, mock_host_obj,
            mock_notification_get):
        notification = self._get_process_type_notification()
        mock_notification_get.return_value = notification
        notification.payload['event'] = 'started'
        fake_host = fakes.create_fake_host()
        mock_host_obj.return_value = fake_host
        self.engine._process_notification(self.context,
                                          notification=notification)
        self.assertEqual("finished", notification.status)
        self.assertFalse(mock_process_failure.called)
        action = fields.EventNotificationAction.NOTIFICATION_PROCESS
        phase_start = fields.EventNotificationPhase.START
        phase_end = fields.EventNotificationPhase.END
        notify_calls = [
            mock.call(self.context, notification, action=action,
                      phase=phase_start),
            mock.call(self.context, notification, action=action,
                      phase=phase_end)]
        mock_notify_about_notification_update.assert_has_calls(notify_calls)

    @mock.patch.object(notification_obj.Notification, "save")
    @mock.patch.object(engine_utils, 'notify_about_notification_update')
    @mock.patch("masakari.engine.drivers.taskflow."
                "TaskFlowDriver.execute_process_failure")
    def test_process_notification_type_process_event_other(
            self, mock_process_failure, mock_notify_about_notification_update,
            mock_notification_save, mock_notification_get):
        notification = self._get_process_type_notification()
        mock_notification_get.return_value = notification
        notification.payload['event'] = 'other'
        self.engine._process_notification(self.context,
                                          notification=notification)
        self.assertEqual("ignored", notification.status)
        self.assertFalse(mock_process_failure.called)
        action = fields.EventNotificationAction.NOTIFICATION_PROCESS
        phase_start = fields.EventNotificationPhase.START
        phase_end = fields.EventNotificationPhase.END
        notify_calls = [
            mock.call(self.context, notification, action=action,
                      phase=phase_start),
            mock.call(self.context, notification, action=action,
                      phase=phase_end)]
        mock_notify_about_notification_update.assert_has_calls(notify_calls)

    @mock.patch.object(host_obj.Host, "get_by_uuid")
    @mock.patch.object(host_obj.Host, "save")
    @mock.patch.object(host_obj.Host, "update")
    @mock.patch.object(host_obj.HostList, "get_all")
    @mock.patch("masakari.engine.drivers.taskflow."
                "TaskFlowDriver.execute_host_failure")
    @mock.patch.object(notification_obj.Notification, "save")
    @mock.patch.object(engine_utils, 'notify_about_notification_update')
    def test_process_notification_type_compute_host_event_stopped(
            self, mock_notify_about_notification_update,
            mock_notification_save, mock_host_failure, mock_get_all,
            mock_host_update, mock_host_save, mock_host_obj,
            mock_notification_get):
        notification = self._get_compute_host_type_notification()
        mock_notification_get.return_value = notification
        mock_host_failure.side_effect = self._fake_notification_workflow()
        fake_host = fakes.create_fake_host()
        mock_get_all.return_value = None
        fake_host.failover_segment = fakes.create_fake_failover_segment()
        mock_host_obj.return_value = fake_host
        self.engine._process_notification(self.context,
                                          notification=notification)

        update_data_by_host_failure = {
            'on_maintenance': True,
        }
        mock_host_update.assert_called_once_with(update_data_by_host_failure)
        mock_host_save.assert_called_once()
        self.assertEqual("finished", notification.status)
        mock_host_failure.assert_called_once_with(
            self.context,
            fake_host.name, fake_host.failover_segment.recovery_method,
            notification.notification_uuid, reserved_host_list=None,
            update_host_method=manager.update_host_method)
        action = fields.EventNotificationAction.NOTIFICATION_PROCESS
        phase_start = fields.EventNotificationPhase.START
        phase_end = fields.EventNotificationPhase.END
        notify_calls = [
            mock.call(self.context, notification, action=action,
                      phase=phase_start),
            mock.call(self.context, notification, action=action,
                      phase=phase_end)]
        mock_notify_about_notification_update.assert_has_calls(notify_calls)

    @mock.patch.object(host_obj.Host, "get_by_uuid")
    @mock.patch.object(host_obj.Host, "save")
    @mock.patch.object(host_obj.Host, "update")
    @mock.patch.object(host_obj.HostList, "get_all")
    @mock.patch.object(notification_obj.Notification, "save")
    @mock.patch.object(engine_utils, 'notify_about_notification_update')
    @mock.patch('traceback.format_exc')
    def test_process_notification_host_failure_without_reserved_hosts(
            self, mock_format, mock_notify_about_notification_update,
            mock_notification_save, mock_get_all,
            mock_host_update, mock_host_save, mock_host_obj,
            mock_notification_get):
        mock_format.return_value = mock.ANY

        fake_host = fakes.create_fake_host()
        fake_host.failover_segment.recovery_method = 'reserved_host'
        mock_host_obj.return_value = fake_host

        notification = self._get_compute_host_type_notification()
        mock_notification_get.return_value = notification

        self.engine._process_notification(self.context,
                                          notification=notification)

        update_data_by_host_failure = {
            'on_maintenance': True,
        }
        mock_host_update.assert_called_once_with(update_data_by_host_failure)
        mock_host_save.assert_called_once()
        self.assertEqual("error", notification.status)
        action = fields.EventNotificationAction.NOTIFICATION_PROCESS
        phase_start = fields.EventNotificationPhase.START
        phase_error = fields.EventNotificationPhase.ERROR
        e = exception.ReservedHostsUnavailable(
            'No reserved_hosts available for evacuation.')
        notify_calls = [
            mock.call(self.context, notification, action=action,
                      phase=phase_start),
            mock.call(self.context, notification, action=action,
                      phase=phase_error,
                      exception=str(e),
                      tb=mock.ANY)]
        mock_notify_about_notification_update.assert_has_calls(notify_calls)

    @mock.patch.object(host_obj.Host, "get_by_uuid")
    @mock.patch.object(host_obj.Host, "save")
    @mock.patch.object(host_obj.Host, "update")
    @mock.patch.object(host_obj.HostList, "get_all")
    @mock.patch("masakari.engine.drivers.taskflow."
                "TaskFlowDriver.execute_host_failure")
    @mock.patch.object(notification_obj.Notification, "save")
    @mock.patch.object(engine_utils, 'notify_about_notification_update')
    def test_process_notification_host_failure_with_reserved_hosts(
            self, mock_notify_about_notification_update,
            mock_notification_save, mock_host_failure, mock_get_all,
            mock_host_update, mock_host_save, mock_host_obj,
            mock_notification_get):
        fake_host = fakes.create_fake_host()
        fake_host.failover_segment.recovery_method = 'reserved_host'
        reserved_host_object_list = [fake_host]
        mock_get_all.return_value = reserved_host_object_list
        mock_host_obj.return_value = fake_host

        reserved_host_list = [host.name for host in
                              reserved_host_object_list]

        notification = self._get_compute_host_type_notification()
        mock_notification_get.return_value = notification
        mock_host_failure.side_effect = self._fake_notification_workflow()

        self.engine._process_notification(self.context,
                                          notification=notification)

        update_data_by_host_failure = {
            'on_maintenance': True,
        }
        mock_host_update.assert_called_once_with(update_data_by_host_failure)
        mock_host_save.assert_called_once()
        self.assertEqual("finished", notification.status)
        mock_host_failure.assert_called_once_with(
            self.context,
            fake_host.name, fake_host.failover_segment.recovery_method,
            notification.notification_uuid,
            reserved_host_list=reserved_host_list,
            update_host_method=manager.update_host_method)
        mock_get_all.assert_called_once_with(self.context, filters={
            'failover_segment_id': fake_host.failover_segment.uuid,
            'reserved': True, 'on_maintenance': False})
        action = fields.EventNotificationAction.NOTIFICATION_PROCESS
        phase_start = fields.EventNotificationPhase.START
        phase_end = fields.EventNotificationPhase.END
        notify_calls = [
            mock.call(self.context, notification, action=action,
                      phase=phase_start),
            mock.call(self.context, notification, action=action,
                      phase=phase_end)]
        mock_notify_about_notification_update.assert_has_calls(notify_calls)

    @mock.patch.object(host_obj.Host, "get_by_uuid")
    @mock.patch.object(host_obj.Host, "save")
    @mock.patch.object(host_obj.Host, "update")
    @mock.patch.object(host_obj.HostList, "get_all")
    @mock.patch("masakari.engine.drivers.taskflow."
                "TaskFlowDriver.execute_host_failure")
    @mock.patch.object(notification_obj.Notification, "save")
    @mock.patch.object(engine_utils, 'notify_about_notification_update')
    def test_process_notification_reserved_host_failure(
            self, mock_notify_about_notification_update,
            mock_notification_save, mock_host_failure, mock_get_all,
            mock_host_update, mock_host_save, mock_host_obj,
            mock_notification_get):
        fake_host = fakes.create_fake_host(reserved=True)
        fake_host.failover_segment.recovery_method = 'reserved_host'
        reserved_host_object_list = [fake_host]
        mock_get_all.return_value = reserved_host_object_list
        mock_host_obj.return_value = fake_host

        notification = self._get_compute_host_type_notification()
        mock_notification_get.return_value = notification
        mock_host_failure.side_effect = self._fake_notification_workflow()

        reserved_host_list = [host.name for host in
                              reserved_host_object_list]

        self.engine._process_notification(self.context,
                                          notification=notification)

        update_data_by_host_failure = {
            'on_maintenance': True,
            'reserved': False,
        }
        mock_host_update.assert_called_once_with(update_data_by_host_failure)
        mock_host_save.assert_called_once()
        self.assertEqual("finished", notification.status)
        mock_host_failure.assert_called_once_with(
            self.context,
            fake_host.name, fake_host.failover_segment.recovery_method,
            notification.notification_uuid,
            reserved_host_list=reserved_host_list,
            update_host_method=manager.update_host_method)
        action = fields.EventNotificationAction.NOTIFICATION_PROCESS
        phase_start = fields.EventNotificationPhase.START
        phase_end = fields.EventNotificationPhase.END
        notify_calls = [
            mock.call(self.context, notification, action=action,
                      phase=phase_start),
            mock.call(self.context, notification, action=action,
                      phase=phase_end)]
        mock_notify_about_notification_update.assert_has_calls(notify_calls)

    @mock.patch.object(host_obj.Host, "get_by_uuid")
    @mock.patch.object(host_obj.Host, "save")
    @mock.patch.object(host_obj.Host, "update")
    @mock.patch.object(host_obj.HostList, "get_all")
    @mock.patch("masakari.engine.drivers.taskflow."
                "TaskFlowDriver.execute_host_failure")
    @mock.patch.object(notification_obj.Notification, "save")
    @mock.patch.object(engine_utils, 'notify_about_notification_update')
    @mock.patch('traceback.format_exc')
    def test_process_notification_type_compute_host_recovery_exception(
            self, mock_format, mock_notify_about_notification_update,
            mock_notification_save, mock_host_failure, mock_get_all,
            mock_host_update, mock_host_save, mock_host_obj,
            mock_notification_get):
        mock_format.return_value = mock.ANY
        notification = self._get_compute_host_type_notification()
        mock_notification_get.return_value = notification
        fake_host = fakes.create_fake_host()
        mock_get_all.return_value = None
        fake_host.failover_segment = fakes.create_fake_failover_segment()
        mock_host_obj.return_value = fake_host
        mock_host_failure.side_effect = self._fake_notification_workflow(
            exc=exception.HostRecoveryFailureException)
        self.engine._process_notification(self.context,
                                          notification=notification)

        update_data_by_host_failure = {
            'on_maintenance': True,
        }
        mock_host_update.assert_called_once_with(update_data_by_host_failure)
        mock_host_save.assert_called_once()
        self.assertEqual("error", notification.status)
        e = exception.HostRecoveryFailureException('Failed to execute host '
                                                   'recovery.')
        action = fields.EventNotificationAction.NOTIFICATION_PROCESS
        phase_start = fields.EventNotificationPhase.START
        phase_error = fields.EventNotificationPhase.ERROR
        notify_calls = [
            mock.call(self.context, notification, action=action,
                      phase=phase_start),
            mock.call(self.context, notification, action=action,
                      phase=phase_error,
                      exception=str(e),
                      tb=mock.ANY)]
        mock_notify_about_notification_update.assert_has_calls(notify_calls)

    @mock.patch.object(host_obj.Host, "get_by_uuid")
    @mock.patch.object(host_obj.Host, "save")
    @mock.patch.object(host_obj.Host, "update")
    @mock.patch.object(host_obj.HostList, "get_all")
    @mock.patch("masakari.engine.drivers.taskflow."
                "TaskFlowDriver.execute_host_failure")
    @mock.patch.object(notification_obj.Notification, "save")
    @mock.patch.object(engine_utils, 'notify_about_notification_update')
    @mock.patch('traceback.format_exc')
    def test_process_notification_type_compute_host_skip_host_recovery(
            self, mock_format, mock_notify_about_notification_update,
            mock_notification_save, mock_host_failure, mock_get_all,
            mock_host_update, mock_host_save, mock_host_obj,
            mock_notification_get):
        mock_format.return_value = mock.ANY
        notification = self._get_compute_host_type_notification()
        mock_notification_get.return_value = notification
        fake_host = fakes.create_fake_host()
        mock_get_all.return_value = None
        fake_host.failover_segment = fakes.create_fake_failover_segment()
        mock_host_obj.return_value = fake_host
        # mock_host_failure.side_effect = str(e)
        mock_host_failure.side_effect = self._fake_notification_workflow(
            exc=exception.SkipHostRecoveryException)
        self.engine._process_notification(self.context,
                                          notification=notification)

        update_data_by_host_failure = {
            'on_maintenance': True,
        }
        mock_host_update.assert_called_once_with(update_data_by_host_failure)
        mock_host_save.assert_called_once()
        self.assertEqual("finished", notification.status)
        action = fields.EventNotificationAction.NOTIFICATION_PROCESS
        phase_start = fields.EventNotificationPhase.START
        phase_end = fields.EventNotificationPhase.END
        notify_calls = [
            mock.call(self.context, notification, action=action,
                      phase=phase_start),
            mock.call(self.context, notification, action=action,
                      phase=phase_end)]
        mock_notify_about_notification_update.assert_has_calls(notify_calls)

    @mock.patch.object(notification_obj.Notification, "save")
    @mock.patch.object(engine_utils, 'notify_about_notification_update')
    @mock.patch("masakari.engine.drivers.taskflow."
                "TaskFlowDriver.execute_host_failure")
    def test_process_notification_type_compute_host_event_started(
            self, mock_host_failure, mock_notify_about_notification_update,
            mock_notification_save, mock_notification_get):
        notification = self._get_compute_host_type_notification()
        mock_notification_get.return_value = notification
        notification.payload['event'] = 'started'
        self.engine._process_notification(self.context,
                                          notification=notification)
        self.assertEqual("finished", notification.status)
        self.assertFalse(mock_host_failure.called)
        action = fields.EventNotificationAction.NOTIFICATION_PROCESS
        phase_start = fields.EventNotificationPhase.START
        phase_end = fields.EventNotificationPhase.END
        notify_calls = [
            mock.call(self.context, notification, action=action,
                      phase=phase_start),
            mock.call(self.context, notification, action=action,
                      phase=phase_end)]
        mock_notify_about_notification_update.assert_has_calls(notify_calls)

    @mock.patch.object(notification_obj.Notification, "save")
    @mock.patch.object(engine_utils, 'notify_about_notification_update')
    @mock.patch("masakari.engine.drivers.taskflow."
                "TaskFlowDriver.execute_host_failure")
    def test_process_notification_type_compute_host_event_other(
            self, mock_host_failure, mock_notify_about_notification_update,
            mock_notification_save, mock_notification_get):
        notification = self._get_compute_host_type_notification()
        mock_notification_get.return_value = notification
        notification.payload['event'] = 'other'
        self.engine._process_notification(self.context,
                                          notification=notification)
        self.assertEqual("ignored", notification.status)
        self.assertFalse(mock_host_failure.called)
        action = fields.EventNotificationAction.NOTIFICATION_PROCESS
        phase_start = fields.EventNotificationPhase.START
        phase_end = fields.EventNotificationPhase.END
        notify_calls = [
            mock.call(self.context, notification, action=action,
                      phase=phase_start),
            mock.call(self.context, notification, action=action,
                      phase=phase_end)]
        mock_notify_about_notification_update.assert_has_calls(notify_calls)

    @mock.patch("masakari.compute.nova.API.stop_server")
    @mock.patch.object(notification_obj.Notification, "save")
    @mock.patch.object(engine_utils, 'notify_about_notification_update')
    @mock.patch('traceback.format_exc')
    @mock.patch("masakari.compute.nova.API.get_server")
    def test_process_notification_type_vm_ignore_instance_in_paused(
            self, mock_get_server, mock_format,
            mock_notify_about_notification_update, mock_notification_save,
            mock_stop_server, mock_notification_get):
        mock_format.return_value = mock.ANY
        notification = _get_vm_type_notification()
        mock_notification_get.return_value = notification
        mock_get_server.return_value = fakes.FakeNovaClient.Server(
            id=1, uuid=uuidsentinel.fake_ins, host='fake_host',
            vm_state='paused', ha_enabled=True)

        self.engine._process_notification(self.context,
                                          notification=notification)
        self.assertEqual("ignored", notification.status)
        self.assertFalse(mock_stop_server.called)
        msg = ("Recovery of instance '%(instance_uuid)s' is ignored as it is "
               "in '%(vm_state)s' state.") % {'instance_uuid':
                uuidsentinel.fake_ins, 'vm_state': 'paused'}
        e = exception.IgnoreInstanceRecoveryException(msg)
        action = fields.EventNotificationAction.NOTIFICATION_PROCESS
        phase_start = fields.EventNotificationPhase.START
        phase_error = fields.EventNotificationPhase.ERROR
        notify_calls = [
            mock.call(self.context, notification, action=action,
                      phase=phase_start),
            mock.call(self.context, notification, action=action,
                      phase=phase_error,
                      exception=str(e),
                      tb=mock.ANY)]
        mock_notify_about_notification_update.assert_has_calls(notify_calls)

    @mock.patch("masakari.compute.nova.API.stop_server")
    @mock.patch.object(notification_obj.Notification, "save")
    @mock.patch.object(engine_utils, 'notify_about_notification_update')
    @mock.patch('traceback.format_exc')
    @mock.patch("masakari.compute.nova.API.get_server")
    def test_process_notification_type_vm_ignore_instance_in_rescued(
            self, mock_get_server, mock_format,
            mock_notify_about_notification_update, mock_notification_save,
            mock_stop_server, mock_notification_get):
        mock_format.return_value = mock.ANY
        notification = _get_vm_type_notification()
        mock_notification_get.return_value = notification
        mock_get_server.return_value = fakes.FakeNovaClient.Server(
            id=1, uuid=uuidsentinel.fake_ins, host='fake_host',
            vm_state='rescued', ha_enabled=True)

        self.engine._process_notification(self.context,
                                          notification=notification)
        self.assertEqual("ignored", notification.status)
        self.assertFalse(mock_stop_server.called)
        msg = ("Recovery of instance '%(instance_uuid)s' is ignored as it is "
               "in '%(vm_state)s' state.") % {'instance_uuid':
                uuidsentinel.fake_ins, 'vm_state': 'rescued'}
        e = exception.IgnoreInstanceRecoveryException(msg)
        action = fields.EventNotificationAction.NOTIFICATION_PROCESS
        phase_start = fields.EventNotificationPhase.START
        phase_error = fields.EventNotificationPhase.ERROR
        notify_calls = [
            mock.call(self.context, notification, action=action,
                      phase=phase_start),
            mock.call(self.context, notification, action=action,
                      phase=phase_error,
                      exception=str(e),
                      tb=mock.ANY)]
        mock_notify_about_notification_update.assert_has_calls(notify_calls)

    def test_process_notification_stop_from_recovery_failure(self,
                                                     mock_get_noti):
        noti_new = _get_vm_type_notification()
        mock_get_noti.return_value = _get_vm_type_notification(
            status="failed")

        with mock.patch("masakari.engine.manager.LOG.warning") as mock_log:
            self.engine._process_notification(self.context,
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
        # For testing purpose setting BACKEND as memory
        masakari.engine.drivers.taskflow.base.PERSISTENCE_BACKEND = 'memory://'
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

    @mock.patch.object(notification_obj.Notification, "save")
    def test_process_notification_host_failure_with_host_status_unknown(
            self, mock_get_noti, mock_notification_save):
        notification = fakes.create_fake_notification(
            type="COMPUTE_HOST", id=1, payload={
                'event': 'stopped', 'host_status': 'UNKNOWN',
                'cluster_status': 'ONLINE'
            },
            source_host_uuid=uuidsentinel.fake_host,
            generated_time=NOW, status=fields.NotificationStatus.NEW,
            notification_uuid=uuidsentinel.fake_notification)

        mock_get_noti.return_value = notification
        notification_new = notification.obj_clone()
        notification_new.status = fields.NotificationStatus.IGNORED
        mock_notification_save.side_effect = [notification, notification_new]

        with mock.patch("masakari.engine.manager.LOG.warning") as mock_log:
            self.engine._process_notification(self.context,
                                              notification=notification)
            mock_log.assert_called_once()
            args = mock_log.call_args[0]
            expected_log = ("Notification '%(uuid)s' ignored as host_status "
                            "is '%(host_status)s'")
            expected_log_args_1 = {
                'uuid': notification.notification_uuid,
                'host_status': fields.HostStatusType.UNKNOWN}

            self.assertEqual(expected_log, args[0])
            self.assertEqual(expected_log_args_1, args[1])
            self.assertEqual(
                fields.NotificationStatus.IGNORED, notification.status)

    @mock.patch.object(notification_obj.Notification, "save")
    def test_process_notification_host_failure_without_host_status(
            self, mock_get_noti, mock_notification_save):
        notification = fakes.create_fake_notification(
            type="COMPUTE_HOST",
            payload={'event': 'stopped', 'cluster_status': 'ONLINE'},
            source_host_uuid=uuidsentinel.fake_host,
            generated_time=NOW, status=fields.NotificationStatus.NEW,
            notification_uuid=uuidsentinel.fake_notification)

        mock_get_noti.return_value = notification
        notification_new = notification.obj_clone()
        notification_new.status = fields.NotificationStatus.IGNORED
        mock_notification_save.side_effect = [notification, notification_new]

        with mock.patch("masakari.engine.manager.LOG.warning") as mock_log:
            self.engine._process_notification(self.context,
                                              notification=notification)
            mock_log.assert_called_once_with(
                "Notification '%(uuid)s' ignored as host_status is not "
                "provided.",
                {'uuid': notification.notification_uuid})
            self.assertEqual(
                fields.NotificationStatus.IGNORED, notification.status)

    @mock.patch('masakari.compute.nova.novaclient')
    @mock.patch.object(nova.API, "enable_disable_service")
    @mock.patch('masakari.engine.drivers.taskflow.host_failure.'
                'PrepareHAEnabledInstancesTask.execute')
    @mock.patch('masakari.engine.drivers.taskflow.host_failure.'
                'EvacuateInstancesTask.execute')
    @mock.patch('masakari.engine.drivers.taskflow.base.MasakariTask.'
                'update_details')
    @mock.patch('masakari.engine.drivers.taskflow.host_failure.LOG')
    def test_host_failure_flow_for_auto_recovery(self, _mock_log,
                                                 _mock_notify,
                                                 _mock_novaclient,
                                                 _mock_enable_disable,
                                                 _mock_task2, _mock_task3,
                                                 _mock_notification_get):
        self.novaclient = nova.API()
        self.fake_client = fakes.FakeNovaClient()
        self.override_config("wait_period_after_evacuation", 2)
        self.override_config("wait_period_after_service_update", 2)
        self.override_config("evacuate_all_instances",
                             True, "host_failure")

        _mock_novaclient.return_value = self.fake_client

        # create test data
        self.fake_client.servers.create(id="1", host="fake-host",
                                        ha_enabled=True)
        self.fake_client.servers.create(id="2", host="fake-host")

        instance_uuid_list = []
        for instance in self.fake_client.servers.list():
            instance_uuid_list.append(instance.id)

        instance_list = {
            "instance_list": ','.join(instance_uuid_list),
        }
        _mock_task2.return_value = instance_list

        # For testing purpose setting BACKEND as memory
        masakari.engine.drivers.taskflow.base.PERSISTENCE_BACKEND = 'memory://'

        self.engine.driver.execute_host_failure(
            self.context, "fake-host",
            fields.FailoverSegmentRecoveryMethod.AUTO,
            uuidsentinel.fake_notification)

        # make sure instance is active and has different host
        for server in instance_uuid_list:
            instance = self.novaclient.get_server(self.context, server)

            if CONF.host_failure.ignore_instances_in_error_state and getattr(
                    instance, 'OS-EXT-STS:vm_state') == 'error':
                self.assertEqual(
                    "fake-host", getattr(
                        instance, 'OS-EXT-SRV-ATTR:hypervisor_hostname'))
            else:
                self.assertNotEqual(
                    "fake-host", getattr(
                        instance, 'OS-EXT-SRV-ATTR:hypervisor_hostname'))

        # verify progress details
        _mock_notify.assert_has_calls([
            mock.call("Disabling compute service on host: 'fake-host'"),
            mock.call("Disabled compute service on host: 'fake-host'", 1.0)
        ])

    @mock.patch('masakari.compute.nova.novaclient')
    @mock.patch('masakari.engine.drivers.taskflow.host_failure.'
                'DisableComputeServiceTask.execute')
    @mock.patch('masakari.engine.drivers.taskflow.host_failure.'
                'PrepareHAEnabledInstancesTask.execute')
    @mock.patch('masakari.engine.drivers.taskflow.host_failure.'
                'EvacuateInstancesTask.execute')
    @mock.patch('masakari.engine.drivers.taskflow.no_op.LOG')
    def test_host_failure_custom_flow_for_rh_recovery(self, _mock_log,
                                                      _mock_task1,
                                                      _mock_task2,
                                                      _mock_task3,
            _mock_novaclient, _mock_notification_get):
        # For testing purpose setting BACKEND as memory
        masakari.engine.drivers.taskflow.base.PERSISTENCE_BACKEND = 'memory://'
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
            update_host_method=manager.update_host_method,
            reserved_host_list=['host-1', 'host-2'])
        # Ensure custom_task added to the 'host_rh_failure_recovery_tasks'
        # is executed.
        _mock_log.info.assert_called_with(expected_msg_format)

    @mock.patch('masakari.compute.nova.novaclient')
    @mock.patch.object(nova.API, "enable_disable_service")
    @mock.patch('masakari.engine.drivers.taskflow.host_failure.'
                'PrepareHAEnabledInstancesTask.execute')
    @mock.patch('masakari.engine.drivers.taskflow.host_failure.'
                'EvacuateInstancesTask.execute')
    @mock.patch('masakari.engine.drivers.taskflow.base.MasakariTask.'
                'update_details')
    @mock.patch('masakari.engine.drivers.taskflow.host_failure.LOG')
    def test_host_failure_flow_for_rh_recovery(self, _mock_log, _mock_notify,
                                               _mock_novaclient,
                                               _mock_enable_disable,
                                               _mock_task2, _mock_task3,
                                               _mock_notification_get):
        self.novaclient = nova.API()
        self.fake_client = fakes.FakeNovaClient()
        self.override_config("wait_period_after_evacuation", 2)
        self.override_config("wait_period_after_service_update", 2)
        self.override_config("evacuate_all_instances",
                             True, "host_failure")

        _mock_novaclient.return_value = self.fake_client

        # create test data
        self.fake_client.servers.create(id="1", host="fake-host",
                                        ha_enabled=True)
        self.fake_client.servers.create(id="2", host="fake-host")

        instance_uuid_list = []
        for instance in self.fake_client.servers.list():
            instance_uuid_list.append(instance.id)

        instance_list = {
            "instance_list": ','.join(instance_uuid_list),
        }
        _mock_task2.return_value = instance_list

        # For testing purpose setting BACKEND as memory
        masakari.engine.drivers.taskflow.base.PERSISTENCE_BACKEND = 'memory://'

        self.engine.driver.execute_host_failure(
            self.context, "fake-host",
            fields.FailoverSegmentRecoveryMethod.RESERVED_HOST,
            uuidsentinel.fake_notification,
            update_host_method=manager.update_host_method,
            reserved_host_list=['host-1', 'host-2'])

        # make sure instance is active and has different host
        for server in instance_uuid_list:
            instance = self.novaclient.get_server(self.context, server)
            self.assertNotEqual(
                "fake-host", getattr(
                    instance, 'OS-EXT-SRV-ATTR:hypervisor_hostname'))

        # verify progress details
        _mock_notify.assert_has_calls([
            mock.call("Disabling compute service on host: 'fake-host'"),
            mock.call("Disabled compute service on host: 'fake-host'", 1.0)
        ])

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
        # For testing purpose setting BACKEND as memory
        masakari.engine.drivers.taskflow.base.PERSISTENCE_BACKEND = 'memory://'
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
    @mock.patch('masakari.engine.drivers.taskflow.base.MasakariTask.'
                'update_details')
    @mock.patch('masakari.engine.drivers.taskflow.instance_failure.LOG')
    def test_instance_failure_flow_recovery(self, _mock_log, _mock_notify,
                                            _mock_novaclient,
                                            _mock_notification_get):
        self.novaclient = nova.API()
        self.fake_client = fakes.FakeNovaClient()
        self.override_config('wait_period_after_power_off', 2)
        self.override_config('wait_period_after_power_on', 2)
        instance_id = uuidsentinel.fake_ins

        _mock_novaclient.return_value = self.fake_client

        # create test data
        self.fake_client.servers.create(instance_id,
                                        host="fake-host",
                                        ha_enabled=True)

        # For testing purpose setting BACKEND as memory
        masakari.engine.drivers.taskflow.base.PERSISTENCE_BACKEND = 'memory://'

        self.engine.driver.execute_instance_failure(
            self.context, instance_id,
            uuidsentinel.fake_notification)

        # verify instance is in active state
        instance = self.novaclient.get_server(self.context, instance_id)
        self.assertEqual('active',
                         getattr(instance, 'OS-EXT-STS:vm_state'))

        _mock_notify.assert_has_calls([
            mock.call('Stopping instance: ' + instance_id),
            mock.call("Stopped instance: '" + instance_id + "'", 1.0),
            mock.call("Starting instance: '" + instance_id + "'"),
            mock.call("Instance started: '" + instance_id + "'", 1.0),
            mock.call("Confirming instance '" + instance_id +
                      "' vm_state is ACTIVE"),
            mock.call("Confirmed instance '" + instance_id +
                      "' vm_state is ACTIVE", 1.0)
        ])

    @mock.patch('masakari.compute.nova.novaclient')
    @mock.patch('masakari.engine.drivers.taskflow.process_failure.'
                'DisableComputeNodeTask.execute')
    @mock.patch('masakari.engine.drivers.taskflow.process_failure.'
                'ConfirmComputeNodeDisabledTask.execute')
    @mock.patch('masakari.engine.drivers.taskflow.no_op.LOG')
    def test_process_failure_custom_flow_recovery(
            self, _mock_log, _mock_task1, _mock_task2, _mock_novaclient,
            _mock_notification_get):
        # For testing purpose setting BACKEND as memory
        masakari.engine.drivers.taskflow.base.PERSISTENCE_BACKEND = 'memory://'
        self.override_config(
            "process_failure_recovery_tasks",
            {'pre': ['disable_compute_node_task', 'no_op'],
             'main': ['confirm_compute_node_disabled_task'],
             'post': []},
            "taskflow_driver_recovery_flows")

        expected_msg_format = "Custom task executed successfully..!!"

        self.engine.driver.execute_process_failure(
            self.context, 'nova-compute', 'fake_host',
            uuidsentinel.fake_notification, )

        _mock_log.info.assert_any_call(expected_msg_format)
        # Ensure custom_task added to the 'process_failure_recovery_tasks'
        # is executed.
        _mock_log.info.assert_called_with(expected_msg_format)

    @mock.patch('masakari.compute.nova.novaclient')
    @mock.patch('masakari.engine.drivers.taskflow.base.MasakariTask.'
                'update_details')
    @mock.patch('masakari.engine.drivers.taskflow.process_failure.LOG')
    def test_process_failure_flow_recovery(self, _mock_log, _mock_notify,
                                           _mock_novaclient,
                                           _mock_notification_get):
        self.novaclient = nova.API()
        self.fake_client = fakes.FakeNovaClient()
        _mock_novaclient.return_value = self.fake_client

        # create test data
        self.fake_client.services.create("1", host="fake-host",
                                         binary="nova-compute",
                                         status="enabled")

        # For testing purpose setting BACKEND as memory
        masakari.engine.drivers.taskflow.base.PERSISTENCE_BACKEND = 'memory://'

        self.engine.driver.execute_process_failure(
            self.context, "nova-compute", "fake-host",
            uuidsentinel.fake_notification)

        # verify service is disabled
        self.assertTrue(self.novaclient.is_service_disabled(self.context,
                                                            "fake-host",
                                                            "nova-compute"))
        # verify progress details
        _mock_notify.assert_has_calls([
            mock.call("Disabling compute service on host: 'fake-host'"),
            mock.call("Disabled compute service on host: 'fake-host'", 1.0),
            mock.call("Confirming compute service is disabled on host: "
                      "'fake-host'"),
            mock.call("Confirmed compute service is disabled on host: "
                      "'fake-host'", 1.0)
        ])

    @mock.patch.object(notification_obj.Notification, "save")
    @mock.patch('masakari.engine.drivers.taskflow.driver.TaskFlowDriver.'
                'get_notification_recovery_workflow_details')
    def test_get_notification_recovery_workflow_details(self,
                                                        mock_progress_details,
                                                        mock_save,
                                                        mock_notification_get):
        notification = fakes.create_fake_notification(
            type="VM", id=1, payload={
                'event': 'fake_event', 'instance_uuid': uuidsentinel.fake_ins,
                'vir_domain_event': 'fake_vir_domain_event'
            },
            source_host_uuid=uuidsentinel.fake_host,
            generated_time=NOW, status="new",
            notification_uuid=uuidsentinel.fake_notification,)

        mock_notification_get.return_value = notification
        self.engine.driver.get_notification_recovery_workflow_details(
            self.context, notification)

        mock_progress_details.assert_called_once_with(
            self.context, notification)

    @mock.patch.object(notification_obj.Notification, "save")
    @mock.patch.object(notification_obj.NotificationList, "get_all")
    def test_check_expired_notifications(self, mock_get_all, mock_save,
                                         mock_notification_get):
        notification = self._get_compute_host_type_notification(expired=True)
        mock_get_all.return_value = [notification]
        self.engine._check_expired_notifications(self.context)
        self.assertEqual("failed", notification.status)
