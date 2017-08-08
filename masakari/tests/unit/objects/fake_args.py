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

from masakari.notifications.objects import base
from masakari.notifications.objects import exception
from masakari.notifications.objects import notification as event_notification
from masakari.objects import host as host_obj
from masakari.objects import notification as notification_obj
from masakari.objects import segment as segment_obj


segment = segment_obj.FailoverSegment()
host = host_obj.Host()
notification = notification_obj.Notification()
fault = None


init_args = {
    event_notification.SegmentApiPayloadBase: [segment],
    event_notification.SegmentApiPayload: [segment, fault],
    event_notification.HostApiPayloadBase: [host],
    event_notification.HostApiPayload: [host, fault],
    event_notification.NotificationApiPayloadBase: [notification],
    event_notification.NotificationApiPayload: [notification, fault],
    event_notification.SegmentApiNotification: [],
    event_notification.HostApiNotification: [],
    event_notification.NotificationApiNotification: [],
    exception.ExceptionPayload: [],
    exception.ExceptionNotification: [],
    base.EventType: [],
    base.NotificationPublisher: [],
    segment_obj.FailoverSegment: [],
    segment_obj.FailoverSegmentList: [],
    host_obj.Host: [],
    host_obj.HostList: [],
    notification_obj.Notification: [],
    notification_obj.NotificationList: [],
}


init_kwargs = {
    event_notification.SegmentApiPayloadBase: {},
    event_notification.SegmentApiPayload: {},
    event_notification.HostApiPayloadBase: {},
    event_notification.HostApiPayload: {},
    event_notification.NotificationApiPayloadBase: {},
    event_notification.NotificationApiPayload: {},
    event_notification.SegmentApiNotification: {},
    event_notification.HostApiNotification: {},
    event_notification.NotificationApiNotification: {},
    exception.ExceptionPayload: {},
    exception.ExceptionNotification: {},
    base.EventType: {},
    base.NotificationPublisher: {},
    segment_obj.FailoverSegment: {},
    segment_obj.FailoverSegmentList: {},
    host_obj.Host: {},
    host_obj.HostList: {},
    notification_obj.Notification: {},
    notification_obj.NotificationList: {},
}
