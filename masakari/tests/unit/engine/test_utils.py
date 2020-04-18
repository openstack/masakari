# Copyright (c) 2018 NTT DATA
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import socket
import testtools
from unittest import mock

from masakari.engine import utils as engine_utils
from masakari.notifications.objects import base as notification_base
from masakari.notifications.objects import exception as notification_exception
from masakari.notifications.objects import notification as event_notification
from masakari.objects import fields
from masakari.objects import notification as notification_obj


class TestApiUtils(testtools.TestCase):
    def setUp(self):
        super(TestApiUtils, self).setUp()

    @mock.patch.object(notification_base, 'EventType')
    @mock.patch.object(notification_base, 'NotificationPublisher')
    @mock.patch.object(event_notification, 'NotificationApiNotification')
    @mock.patch.object(event_notification, 'NotificationApiPayload')
    @mock.patch.object(notification_exception.ExceptionPayload,
                       'from_exc_and_traceback')
    def test_notify_about_notification_update(
        self, mock_from_exception, mock_NotificationApiPayload,
        mock_NotificationApiNotification, mock_NotificationPublisher,
        mock_EventType):
        mock_fault = mock.Mock()
        mock_from_exception.return_value = mock_fault
        mock_payload = mock.Mock()
        mock_NotificationApiPayload.return_value = mock_payload
        mock_engine_notification = mock.Mock()
        mock_NotificationApiNotification.return_value = (
            mock_engine_notification)
        mock_engine_notification.emit.return_value = None
        mock_publisher = mock.Mock()
        mock_NotificationPublisher.return_value = mock_publisher
        mock_event_type = mock.Mock()
        mock_EventType.return_value = mock_event_type

        mock_context = mock.Mock()
        notification = notification_obj.Notification()
        action = fields.EventNotificationAction.NOTIFICATION_PROCESS
        phase = fields.EventNotificationPhase.ERROR
        e = Exception()

        engine_utils.notify_about_notification_update(mock_context,
            notification, action=action, phase=phase, exception=e)

        mock_from_exception.assert_called_once_with(e, None)
        mock_NotificationApiPayload.assert_called_once_with(
            notification=notification, fault=mock_fault)
        mock_NotificationApiNotification.assert_called_once_with(
            context=mock_context,
            priority=fields.EventNotificationPriority.ERROR,
            publisher=mock_publisher,
            event_type=mock_event_type,
            payload=mock_payload)
        mock_NotificationPublisher.assert_called_once_with(
            context=mock_context, host=socket.gethostname(),
            binary='masakari-engine')
        mock_engine_notification.emit.assert_called_once_with(mock_context)
