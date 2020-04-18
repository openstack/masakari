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

from masakari.api import utils as api_utils
from masakari.notifications.objects import base as notification_base
from masakari.notifications.objects import exception as notification_exception
from masakari.notifications.objects import notification as event_notification
from masakari import objects
from masakari.objects import fields
from masakari.objects import host as host_obj
from masakari.objects import notification as notification_obj


class TestApiUtils(testtools.TestCase):
    def setUp(self):
        super(TestApiUtils, self).setUp()

    @mock.patch.object(notification_base, 'EventType')
    @mock.patch.object(notification_base, 'NotificationPublisher')
    @mock.patch.object(event_notification, 'SegmentApiNotification')
    @mock.patch.object(event_notification, 'SegmentApiPayload')
    @mock.patch.object(notification_exception.ExceptionPayload,
                       'from_exc_and_traceback')
    def test_notify_about_segment_api(
        self, mock_from_exception, mock_SegmentApiPayload,
        mock_SegmentApiNotification, mock_NotificationPublisher,
        mock_EventType):
        mock_fault = mock.Mock()
        mock_from_exception.return_value = mock_fault
        mock_payload = mock.Mock()
        mock_SegmentApiPayload.return_value = mock_payload
        mock_api_notification = mock.Mock()
        mock_SegmentApiNotification.return_value = mock_api_notification
        mock_api_notification.emit.return_value = None
        mock_publisher = mock.Mock()
        mock_NotificationPublisher.return_value = mock_publisher
        mock_event_type = mock.Mock()
        mock_EventType.return_value = mock_event_type

        mock_context = mock.Mock()
        segment = objects.FailoverSegment()
        action = fields.EventNotificationAction.SEGMENT_CREATE
        phase = fields.EventNotificationPhase.ERROR
        e = Exception()

        api_utils.notify_about_segment_api(mock_context, segment,
            action=action, phase=phase, exception=e)

        mock_from_exception.assert_called_once_with(e, None)
        mock_SegmentApiPayload.assert_called_once_with(
            segment=segment, fault=mock_fault)
        mock_SegmentApiNotification.assert_called_once_with(
            context=mock_context,
            priority=fields.EventNotificationPriority.ERROR,
            publisher=mock_publisher,
            event_type=mock_event_type,
            payload=mock_payload)
        mock_NotificationPublisher.assert_called_once_with(
            context=mock_context, host=socket.gethostname(),
            binary='masakari-api')
        mock_EventType.assert_called_once_with(
            action=action, phase=phase)
        mock_api_notification.emit.assert_called_once_with(mock_context)

    @mock.patch.object(notification_base, 'EventType')
    @mock.patch.object(notification_base, 'NotificationPublisher')
    @mock.patch.object(event_notification, 'HostApiNotification')
    @mock.patch.object(event_notification, 'HostApiPayload')
    @mock.patch.object(notification_exception.ExceptionPayload,
                       'from_exc_and_traceback')
    def test_notify_about_host_api(
        self, mock_from_exception, mock_HostApiPayload,
        mock_HostApiNotification, mock_NotificationPublisher, mock_EventType):
        mock_fault = mock.Mock()
        mock_from_exception.return_value = mock_fault
        mock_payload = mock.Mock()
        mock_HostApiPayload.return_value = mock_payload
        mock_api_notification = mock.Mock()
        mock_HostApiNotification.return_value = mock_api_notification
        mock_api_notification.emit.return_value = None
        mock_publisher = mock.Mock()
        mock_NotificationPublisher.return_value = mock_publisher
        mock_event_type = mock.Mock()
        mock_EventType.return_value = mock_event_type

        mock_context = mock.Mock()
        host = host_obj.Host()
        action = fields.EventNotificationAction.HOST_CREATE
        phase = fields.EventNotificationPhase.ERROR
        e = Exception()

        api_utils.notify_about_host_api(mock_context, host, action=action,
            phase=phase, exception=e)

        mock_from_exception.assert_called_once_with(e, None)
        mock_HostApiPayload.assert_called_once_with(
            host=host, fault=mock_fault)
        mock_HostApiNotification.assert_called_once_with(
            context=mock_context,
            priority=fields.EventNotificationPriority.ERROR,
            publisher=mock_publisher,
            event_type=mock_event_type,
            payload=mock_payload)
        mock_NotificationPublisher.assert_called_once_with(
            context=mock_context, host=socket.gethostname(),
            binary='masakari-api')
        mock_api_notification.emit.assert_called_once_with(mock_context)
        mock_EventType.assert_called_once_with(
            action=action, phase=phase)

    @mock.patch.object(notification_base, 'EventType')
    @mock.patch.object(notification_base, 'NotificationPublisher')
    @mock.patch.object(event_notification, 'NotificationApiNotification')
    @mock.patch.object(event_notification, 'NotificationApiPayload')
    @mock.patch.object(notification_exception.ExceptionPayload,
                       'from_exc_and_traceback')
    def test_notify_about_notification_api(
        self, mock_from_exception, mock_NotificationApiPayload,
        mock_NotificationApiNotification, mock_NotificationPublisher,
        mock_EventType):
        mock_fault = mock.Mock()
        mock_from_exception.return_value = mock_fault
        mock_payload = mock.Mock()
        mock_NotificationApiPayload.return_value = mock_payload
        mock_api_notification = mock.Mock()
        mock_NotificationApiNotification.return_value = mock_api_notification
        mock_api_notification.emit.return_value = None
        mock_publisher = mock.Mock()
        mock_NotificationPublisher.return_value = mock_publisher
        mock_event_type = mock.Mock()
        mock_EventType.return_value = mock_event_type

        mock_context = mock.Mock()
        notification = notification_obj.Notification()
        action = fields.EventNotificationAction.NOTIFICATION_CREATE
        phase = fields.EventNotificationPhase.ERROR
        e = Exception()

        api_utils.notify_about_notification_api(mock_context, notification,
            action=action, phase=phase, exception=e)

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
            binary='masakari-api')
        mock_api_notification.emit.assert_called_once_with(mock_context)
