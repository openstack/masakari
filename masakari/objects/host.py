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

from oslo_log import log as logging
from oslo_utils import uuidutils

from masakari import db
from masakari import exception
from masakari import objects
from masakari.objects import base
from masakari.objects import fields

LOG = logging.getLogger(__name__)


@base.MasakariObjectRegistry.register
class Host(base.MasakariPersistentObject, base.MasakariObject,
           base.MasakariObjectDictCompat):

    # Version 1.0: Initial version
    # Version 1.1: Added 'segment_uuid' parameter to 'get_by_uuid' method
    VERSION = '1.1'

    fields = {
        'id': fields.IntegerField(),
        'uuid': fields.UUIDField(),
        'name': fields.StringField(),
        'failover_segment_id': fields.UUIDField(),
        'failover_segment': fields.ObjectField('FailoverSegment'),
        'type': fields.StringField(),
        'reserved': fields.BooleanField(),
        'control_attributes': fields.StringField(),
        'on_maintenance': fields.BooleanField(),
        }

    @staticmethod
    def _from_db_object(context, host, db_host):

        for key in host.fields:
            db_value = db_host.get(key)
            if key == "failover_segment":
                db_value = objects.FailoverSegment._from_db_object(
                    host._context, objects.FailoverSegment(), db_value)

            setattr(host, key, db_value)

        host.obj_reset_changes()
        host._context = context
        return host

    @base.remotable_classmethod
    def get_by_id(cls, context, id):
        db_inst = db.host_get_by_id(context, id)
        return cls._from_db_object(context, cls(), db_inst)

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid, segment_uuid=None):
        db_inst = db.host_get_by_uuid(context, uuid, segment_uuid=segment_uuid)
        return cls._from_db_object(context, cls(), db_inst)

    @base.remotable_classmethod
    def get_by_name(cls, context, name):
        db_inst = db.host_get_by_name(context, name)
        return cls._from_db_object(context, cls(), db_inst)

    @base.remotable
    def create(self):
        if self.obj_attr_is_set('id'):
            raise exception.ObjectActionError(action='create',
                                              reason='already created')
        updates = self.masakari_obj_get_changes()

        if 'uuid' not in updates:
            updates['uuid'] = uuidutils.generate_uuid()
            LOG.debug('Generated uuid %(uuid)s for host',
                      dict(uuid=updates['uuid']))

        if 'failover_segment' in updates:
            raise exception.ObjectActionError(action='create',
                                              reason='failover segment '
                                                     'assigned')
        db_host = db.host_create(self._context, updates)
        self._from_db_object(self._context, self, db_host)

    @base.remotable
    def save(self):
        updates = self.masakari_obj_get_changes()
        if 'failover_segment' in updates:
            raise exception.ObjectActionError(action='save',
                                              reason='failover segment '
                                                     'changed')
        updates.pop('id', None)
        db_host = db.host_update(self._context, self.uuid, updates)
        self._from_db_object(self._context, self, db_host)

    @base.remotable
    def destroy(self):
        if not self.obj_attr_is_set('id'):
            raise exception.ObjectActionError(action='destroy',
                                              reason='already destroyed')
        if not self.obj_attr_is_set('uuid'):
            raise exception.ObjectActionError(action='destroy',
                                              reason='no uuid')

        db.host_delete(self._context, self.uuid)
        delattr(self, base.get_attrname('id'))


@base.MasakariObjectRegistry.register
class HostList(base.ObjectListBase, base.MasakariObject):

    VERSION = '1.0'

    fields = {
        'objects': fields.ListOfObjectsField('Host'),
        }

    @base.remotable_classmethod
    def get_all(cls, context, filters=None, sort_keys=None, sort_dirs=None,
                limit=None, marker=None):

        groups = db.host_get_all_by_filters(context, filters=filters,
                                            sort_keys=sort_keys,
                                            sort_dirs=sort_dirs,
                                            limit=limit, marker=marker)

        return base.obj_make_list(context, cls(context), objects.Host, groups)
