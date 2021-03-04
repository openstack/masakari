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
from masakari.objects import base as masakari_base
from masakari.objects import fields


@masakari_base.MasakariObjectRegistry.register_notification
class SegmentApiPayloadBase(base.NotificationPayloadBase):
    SCHEMA = {
        'id': ('segment', 'id'),
        'uuid': ('segment', 'uuid'),
        'name': ('segment', 'name'),
        'service_type': ('segment', 'service_type'),
        'description': ('segment', 'description'),
        'recovery_method': ('segment', 'recovery_method'),
        'enabled': ('segment', 'enabled'),
    }
    # Version 1.0: Initial version
    # Version 1.1: Add 'enabled' field
    VERSION = '1.1'
    fields = {
        'id': fields.IntegerField(),
        'uuid': fields.UUIDField(),
        'name': fields.StringField(),
        'service_type': fields.StringField(),
        'description': fields.StringField(nullable=True),
        'recovery_method': fields.FailoverSegmentRecoveryMethodField(),
        'enabled': fields.BooleanField(),
        }

    def __init__(self, segment, **kwargs):
        super(SegmentApiPayloadBase, self).__init__(**kwargs)
        self.populate_schema(segment=segment)


@masakari_base.MasakariObjectRegistry.register_notification
class SegmentApiPayload(SegmentApiPayloadBase):
    # No SCHEMA as all the additional fields are calculated

    VERSION = '1.1'
    fields = {
        'fault': fields.ObjectField('ExceptionPayload', nullable=True),
    }

    def __init__(self, segment, fault, **kwargs):
        super(SegmentApiPayload, self).__init__(
            segment=segment,
            fault=fault,
            **kwargs)


@masakari_base.MasakariObjectRegistry.register_notification
class HostApiPayloadBase(base.NotificationPayloadBase):
    SCHEMA = {
        'id': ('host', 'id'),
        'uuid': ('host', 'uuid'),
        'name': ('host', 'name'),
        'failover_segment': ('host', 'failover_segment'),
        'type': ('host', 'type'),
        'reserved': ('host', 'reserved'),
        'control_attributes': ('host', 'control_attributes'),
        'on_maintenance': ('host', 'on_maintenance'),
    }
    # Version 1.0: Initial version
    # Version 1.1: Removed 'failover_segment_id' parameter
    VERSION = '1.1'
    fields = {
        'id': fields.IntegerField(),
        'uuid': fields.UUIDField(),
        'name': fields.StringField(),
        'failover_segment': fields.ObjectField('FailoverSegment'),
        'type': fields.StringField(),
        'reserved': fields.BooleanField(),
        'control_attributes': fields.StringField(),
        'on_maintenance': fields.BooleanField(),
        }

    def __init__(self, host, **kwargs):
        super(HostApiPayloadBase, self).__init__(**kwargs)
        self.populate_schema(host=host)


@masakari_base.MasakariObjectRegistry.register_notification
class HostApiPayload(HostApiPayloadBase):
    # No SCHEMA as all the additional fields are calculated

    VERSION = '1.0'
    fields = {
        'fault': fields.ObjectField('ExceptionPayload', nullable=True),
    }

    def __init__(self, host, fault, **kwargs):
        super(HostApiPayload, self).__init__(
            host=host,
            fault=fault,
            **kwargs)


@masakari_base.MasakariObjectRegistry.register_notification
class NotificationApiPayloadBase(base.NotificationPayloadBase):
    SCHEMA = {
        'id': ('notification', 'id'),
        'notification_uuid': ('notification', 'notification_uuid'),
        'generated_time': ('notification', 'generated_time'),
        'source_host_uuid': ('notification', 'source_host_uuid'),
        'type': ('notification', 'type'),
        'payload': ('notification', 'payload'),
        'status': ('notification', 'status'),
    }
    # Version 1.0: Initial version
    VERSION = '1.0'
    fields = {
        'id': fields.IntegerField(),
        'notification_uuid': fields.UUIDField(),
        'generated_time': fields.DateTimeField(),
        'source_host_uuid': fields.UUIDField(),
        'type': fields.NotificationTypeField(),
        'payload': fields.DictOfStringsField(),
        'status': fields.NotificationStatusField(),
        }

    def __init__(self, notification, **kwargs):
        super(NotificationApiPayloadBase, self).__init__(**kwargs)
        self.populate_schema(notification=notification)


@masakari_base.MasakariObjectRegistry.register_notification
class NotificationApiPayload(NotificationApiPayloadBase):
    # No SCHEMA as all the additional fields are calculated

    VERSION = '1.0'
    fields = {
        'fault': fields.ObjectField('ExceptionPayload', nullable=True),
    }

    def __init__(self, notification, fault, **kwargs):
        super(NotificationApiPayload, self).__init__(
            notification=notification,
            fault=fault,
            **kwargs)


@base.notification_sample('create-segment-start.json')
@base.notification_sample('create-segment-end.json')
@base.notification_sample('update-segment-start.json')
@base.notification_sample('update-segment-end.json')
@base.notification_sample('delete-segment-start.json')
@base.notification_sample('delete-segment-end.json')
@masakari_base.MasakariObjectRegistry.register_notification
class SegmentApiNotification(base.NotificationBase):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'payload': fields.ObjectField('SegmentApiPayload')
    }


@base.notification_sample('create-host-start.json')
@base.notification_sample('create-host-end.json')
@base.notification_sample('update-host-start.json')
@base.notification_sample('update-host-end.json')
@base.notification_sample('delete-host-start.json')
@base.notification_sample('delete-host-end.json')
@masakari_base.MasakariObjectRegistry.register_notification
class HostApiNotification(base.NotificationBase):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'payload': fields.ObjectField('HostApiPayload')
    }


@base.notification_sample('create-notification-start.json')
@base.notification_sample('create-notification-end.json')
@base.notification_sample('process-notification-start.json')
@base.notification_sample('process-notification-end.json')
@base.notification_sample('process-notification-error.json')
@masakari_base.MasakariObjectRegistry.register_notification
class NotificationApiNotification(base.NotificationBase):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'payload': fields.ObjectField('NotificationApiPayload')
    }
