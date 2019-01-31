# Copyright 2016 NTT Data.
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

from oslo_versionedobjects import fields


# Import fields from oslo.versionedobjects
BooleanField = fields.BooleanField
IntegerField = fields.IntegerField
StringField = fields.StringField
EnumField = fields.EnumField
UUIDField = fields.UUIDField
DateTimeField = fields.DateTimeField
DictOfStringsField = fields.DictOfStringsField
ObjectField = fields.ObjectField
BaseEnumField = fields.BaseEnumField
ListOfObjectsField = fields.ListOfObjectsField
ListOfStringsField = fields.ListOfStringsField
FloatField = fields.FloatField
ListOfDictOfNullableStringsField = fields.ListOfDictOfNullableStringsField


Field = fields.Field
Enum = fields.Enum
FieldType = fields.FieldType


class BaseMasakariEnum(Enum):
    def __init__(self, **kwargs):
        super(BaseMasakariEnum, self).__init__(
            valid_values=self.__class__.ALL)


class FailoverSegmentRecoveryMethod(Enum):
    """Represents possible recovery_methods for failover segment."""

    AUTO = "auto"
    RESERVED_HOST = "reserved_host"
    AUTO_PRIORITY = "auto_priority"
    RH_PRIORITY = "rh_priority"

    ALL = (AUTO, RESERVED_HOST, AUTO_PRIORITY, RH_PRIORITY)

    def __init__(self):
        super(FailoverSegmentRecoveryMethod,
              self).__init__(valid_values=FailoverSegmentRecoveryMethod.ALL)

    @classmethod
    def index(cls, value):
        """Return an index into the Enum given a value."""
        return cls.ALL.index(value)

    @classmethod
    def from_index(cls, index):
        """Return the Enum value at a given index."""
        return cls.ALL[index]


class NotificationType(Enum):
    """Represents possible notification types."""

    COMPUTE_HOST = "COMPUTE_HOST"
    VM = "VM"
    PROCESS = "PROCESS"

    ALL = (COMPUTE_HOST, VM, PROCESS)

    def __init__(self):
        super(NotificationType,
              self).__init__(valid_values=NotificationType.ALL)

    @classmethod
    def index(cls, value):
        """Return an index into the Enum given a value."""
        return cls.ALL.index(value)

    @classmethod
    def from_index(cls, index):
        """Return the Enum value at a given index."""
        return cls.ALL[index]


class EventType(Enum):
    """Represents possible event types."""

    STARTED = "STARTED"
    STOPPED = "STOPPED"

    ALL = (STARTED, STOPPED)

    def __init__(self):
        super(EventType,
              self).__init__(valid_values=EventType.ALL)

    @classmethod
    def index(cls, value):
        """Return an index into the Enum given a value."""
        return cls.ALL.index(value)

    @classmethod
    def from_index(cls, index):
        """Return the Enum value at a given index."""
        return cls.ALL[index]


class HostStatusType(Enum):
    """Represents possible event types for Host status."""

    NORMAL = "NORMAL"
    UNKNOWN = "UNKNOWN"

    ALL = (NORMAL, UNKNOWN)

    def __init__(self):
        super(HostStatusType,
              self).__init__(valid_values=HostStatusType.ALL)

    @classmethod
    def index(cls, value):
        """Return an index into the Enum given a value."""
        return cls.ALL.index(value)

    @classmethod
    def from_index(cls, index):
        """Return the Enum value at a given index."""
        return cls.ALL[index]


class ClusterStatusType(Enum):
    """Represents possible event types for Cluster status."""

    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"

    ALL = (ONLINE, OFFLINE)

    def __init__(self):
        super(ClusterStatusType,
              self).__init__(valid_values=ClusterStatusType.ALL)

    @classmethod
    def index(cls, value):
        """Return an index into the Enum given a value."""
        return cls.ALL.index(value)

    @classmethod
    def from_index(cls, index):
        """Return the Enum value at a given index."""
        return cls.ALL[index]


class NotificationStatus(Enum):
    """Represents possible statuses for notifications."""

    NEW = "new"
    RUNNING = "running"
    ERROR = "error"
    FAILED = "failed"
    IGNORED = "ignored"
    FINISHED = "finished"

    ALL = (NEW, RUNNING, ERROR, FAILED, IGNORED, FINISHED)

    def __init__(self):
        super(NotificationStatus,
              self).__init__(valid_values=NotificationStatus.ALL)

    @classmethod
    def index(cls, value):
        """Return an index into the Enum given a value."""
        return cls.ALL.index(value)

    @classmethod
    def from_index(cls, index):
        """Return the Enum value at a given index."""
        return cls.ALL[index]


class EventNotificationAction(Enum):
    # Actions of segments
    SEGMENT_CREATE = 'segment.create'
    SEGMENT_UPDATE = 'segment.update'
    SEGMENT_DELETE = 'segment.delete'

    # Actions of hosts
    HOST_CREATE = 'host.create'
    HOST_UPDATE = 'host.update'
    HOST_DELETE = 'host.delete'

    # Actions of notifications
    NOTIFICATION_CREATE = 'notification.create'
    NOTIFICATION_PROCESS = 'notification.process'

    ALL = (SEGMENT_CREATE, SEGMENT_UPDATE, SEGMENT_DELETE, HOST_CREATE,
           HOST_UPDATE, HOST_DELETE, NOTIFICATION_CREATE,
           NOTIFICATION_PROCESS)

    def __init__(self):
        super(EventNotificationAction,
              self).__init__(valid_values=EventNotificationAction.ALL)

    @classmethod
    def index(cls, value):
        """Return an index into the Enum given a value."""
        return cls.ALL.index(value)

    @classmethod
    def from_index(cls, index):
        """Return the Enum value at a given index."""
        return cls.ALL[index]


class EventNotificationPriority(BaseMasakariEnum):
    AUDIT = 'audit'
    CRITICAL = 'critical'
    DEBUG = 'debug'
    INFO = 'info'
    ERROR = 'error'
    SAMPLE = 'sample'
    WARN = 'warn'

    ALL = (AUDIT, CRITICAL, DEBUG, INFO, ERROR, SAMPLE, WARN)


class EventNotificationPhase(Enum):
    START = 'start'
    END = 'end'
    ERROR = 'error'

    ALL = (START, END, ERROR)

    def __init__(self):
        super(EventNotificationPhase,
              self).__init__(valid_values=EventNotificationPhase.ALL)

    @classmethod
    def index(cls, value):
        """Return an index into the Enum given a value."""
        return cls.ALL.index(value)

    @classmethod
    def from_index(cls, index):
        """Return the Enum value at a given index."""
        return cls.ALL[index]


class FailoverSegmentRecoveryMethodField(BaseEnumField):
    AUTO_TYPE = FailoverSegmentRecoveryMethod()


class NotificationTypeField(BaseEnumField):
    AUTO_TYPE = NotificationType()


class NotificationStatusField(BaseEnumField):
    AUTO_TYPE = NotificationStatus()


class EventNotificationActionField(BaseEnumField):
    AUTO_TYPE = EventNotificationAction()


class EventNotificationPriorityField(BaseEnumField):
    AUTO_TYPE = EventNotificationPriority()


class EventNotificationPhaseField(BaseEnumField):
    AUTO_TYPE = EventNotificationPhase()
