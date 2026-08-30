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

"""Masakari common internal object model"""

import datetime

from oslo_utils import versionutils
from oslo_versionedobjects import base as ovoo_base
from oslo_versionedobjects import fields as obj_fields

from masakari import objects


obj_make_list = ovoo_base.obj_make_list
MasakariObjectDictCompat = ovoo_base.VersionedObjectDictCompat


def get_attrname(name):
    """Return the mangled name of the attribute's underlying storage."""
    return '_obj_' + name


class MasakariObjectRegistry(ovoo_base.VersionedObjectRegistry):
    notification_classes = []

    def registration_hook(self, cls, index):
        # NOTE(Dinesh_Bhor): This is called when an object is registered,
        # and is responsible for maintaining masakari.objects.$OBJECT
        # as the highest-versioned implementation of a given object.
        version = versionutils.convert_version_to_tuple(cls.VERSION)
        if not hasattr(objects, cls.obj_name()):
            setattr(objects, cls.obj_name(), cls)
        else:
            cur_version = versionutils.convert_version_to_tuple(
                getattr(objects, cls.obj_name()).VERSION)
            if version >= cur_version:
                setattr(objects, cls.obj_name(), cls)

    @classmethod
    def register_notification(cls, notification_cls):
        """Register a class as notification.

        Use only to register concrete notification or payload classes,
        do not register base classes intended for inheritance only.
        """
        cls.register_if(False)(notification_cls)
        cls.notification_classes.append(notification_cls)
        return notification_cls

    @classmethod
    def register_notification_objects(cls):
        """Register previously decorated notification as normal ovos.

        This is not intended for production use but only for testing and
        document generation purposes.
        """
        for notification_cls in cls.notification_classes:
            cls.register(notification_cls)


remotable = ovoo_base.remotable


class MasakariObject(ovoo_base.VersionedObject):
    """Base class and object factory.

    This forms the base of all objects that can be remoted or instantiated
    via RPC. Simply defining a class that inherits from this base class
    will make it remotely instantiatable. Objects should implement the
    necessary "get" classmethod routines as well as "save" object methods
    as appropriate.
    """

    OBJ_SERIAL_NAMESPACE = 'masakari_object'
    OBJ_PROJECT_NAMESPACE = 'masakari'

    def masakari_obj_get_changes(self):
        """Returns a dict of changed fields with tz unaware datetimes.

        Any timezone aware datetime field will be converted to UTC timezone
        and returned as timezone unaware datetime.

        This will allow us to pass these fields directly to a db update
        method as they can't have timezone information.
        """
        # Get dirtied/changed fields
        changes = self.obj_get_changes()

        # Look for datetime objects that contain timezone information
        for k, v in changes.items():
            if isinstance(v, datetime.datetime) and v.tzinfo:
                # Remove timezone information and adjust the time according to
                # the timezone information's offset.
                changes[k] = v.replace(tzinfo=None) - v.utcoffset()

        # Return modified dict
        return changes


class MasakariPersistentObject(object):
    """Mixin class for Persistent objects.

    This adds the fields that we use in common for most persistent objects.
    """
    fields = {
        'created_at': obj_fields.DateTimeField(nullable=True),
        'updated_at': obj_fields.DateTimeField(nullable=True),
        'deleted_at': obj_fields.DateTimeField(nullable=True),
        'deleted': obj_fields.BooleanField(default=False),
        }


class ObjectListBase(ovoo_base.ObjectListBase):

    @classmethod
    def _obj_primitive_key(cls, field):
        return 'masakari_object.%s' % field

    @classmethod
    def _obj_primitive_field(cls, primitive, field,
                             default=obj_fields.UnspecifiedDefault):
        key = cls._obj_primitive_key(field)
        if default == obj_fields.UnspecifiedDefault:
            return primitive[key]
        else:
            return primitive.get(key, default)


class MasakariObjectSerializer(ovoo_base.VersionedObjectSerializer):
    """A Masakari Object Serializer.

       This implements the Oslo Serializer interface and provides
       the ability to serialize and deserialize MasakariObject entities.
       Any service that needs to accept or return MasakariObjects
       as arguments or result values should pass this to its RPCClient
       and RPCServer objects.

    """
    OBJ_BASE_CLASS = MasakariObject

    def __init__(self):
        super(MasakariObjectSerializer, self).__init__()


def obj_equal_prims(obj_1, obj_2, ignore=None):
    """Compare two primitives for equivalence ignoring some keys.

    This operation tests the primitives of two objects for equivalence.
    Object primitives may contain a list identifying fields that have been
    changed - this is ignored in the comparison. The ignore parameter lists
    any other keys to be ignored.

    :param:obj1: The first object in the comparison
    :param:obj2: The second object in the comparison
    :param:ignore: A list of fields to ignore
    :returns: True if the primitives are equal ignoring changes
    and specified fields, otherwise False.
    """

    def _strip(prim, keys):
        if isinstance(prim, dict):
            for k in keys:
                prim.pop(k, None)
            for v in prim.values():
                _strip(v, keys)
        if isinstance(prim, list):
            for v in prim:
                _strip(v, keys)
        return prim

    if ignore is not None:
        keys = ['masakari_object.changes'] + ignore
    else:
        keys = ['masakari_object.changes']
    prim_1 = _strip(obj_1.obj_to_primitive(), keys)
    prim_2 = _strip(obj_2.obj_to_primitive(), keys)
    return prim_1 == prim_2
