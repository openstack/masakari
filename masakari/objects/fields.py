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
ObjectField = fields.ObjectField
BaseEnumField = fields.BaseEnumField
ListOfObjectsField = fields.ListOfObjectsField
ListOfStringsField = fields.ListOfStringsField


Field = fields.Field
Enum = fields.Enum
FieldType = fields.FieldType


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


class FailoverSegmentRecoveryMethodField(BaseEnumField):
    AUTO_TYPE = FailoverSegmentRecoveryMethod()
