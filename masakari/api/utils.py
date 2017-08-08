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

from masakari.notifications.objects import base as notification_base
from masakari.notifications.objects import exception as notification_exception
from masakari.notifications.objects import notification as event_notification
from masakari.objects import fields


def _get_fault_and_priority_from_exc_and_tb(exception, tb):
    fault = None
    priority = fields.EventNotificationPriority.INFO

    if exception:
        priority = fields.EventNotificationPriority.ERROR
        fault = notification_exception.ExceptionPayload.from_exc_and_traceback(
            exception, tb)

    return fault, priority


def notify_about_segment_api(context, segment, action, phase=None,
                             binary='masakari-api', exception=None, tb=None):
    """Send versioned notification about a segment API.

    :param segment: FailoverSegment object
    :param action: the name of the action
    :param phase: the phase of the action
    :param binary: the binary emitting the notification
    :param exception: the thrown exception (used in error notifications)
    :param tb: the traceback (used in error notifications)
    """
    fault, priority = _get_fault_and_priority_from_exc_and_tb(exception, tb)
    payload = event_notification.SegmentApiPayload(
        segment=segment, fault=fault)
    api_notification = event_notification.SegmentApiNotification(
        context=context,
        priority=priority,
        publisher=notification_base.NotificationPublisher(
            context=context, host=socket.gethostname(), binary=binary),
        event_type=notification_base.EventType(
            action=action,
            phase=phase),
        payload=payload)
    api_notification.emit(context)


def notify_about_host_api(context, host, action, phase=None,
                          binary='masakari-api', exception=None, tb=None):
    """Send versioned notification about a host API.

    :param host: Host object
    :param action: the name of the action
    :param phase: the phase of the action
    :param binary: the binary emitting the notification
    :param exception: the thrown exception (used in error notifications)
    :param tb: the traceback (used in error notifications)
    """
    fault, priority = _get_fault_and_priority_from_exc_and_tb(exception, tb)
    payload = event_notification.HostApiPayload(host=host, fault=fault)
    api_notification = event_notification.HostApiNotification(
        context=context,
        priority=priority,
        publisher=notification_base.NotificationPublisher(
            context=context, host=socket.gethostname(), binary=binary),
        event_type=notification_base.EventType(
            action=action,
            phase=phase),
        payload=payload)
    api_notification.emit(context)


def notify_about_notification_api(context, notification, action, phase=None,
                          binary='masakari-api', exception=None, tb=None):
    """Send versioned notification about a notification api.

    :param notification: Notification object
    :param action: the name of the action
    :param phase: the phase of the action
    :param binary: the binary emitting the notification
    :param exception: the thrown exception (used in error notifications)
    :param tb: the traceback (used in error notifications)
    """
    fault, priority = _get_fault_and_priority_from_exc_and_tb(exception, tb)
    payload = event_notification.NotificationApiPayload(
        notification=notification, fault=fault)
    api_notification = event_notification.NotificationApiNotification(
        context=context,
        priority=priority,
        publisher=notification_base.NotificationPublisher(
            context=context, host=socket.gethostname(), binary=binary),
        event_type=notification_base.EventType(
            action=action,
            phase=phase),
        payload=payload)
    api_notification.emit(context)
