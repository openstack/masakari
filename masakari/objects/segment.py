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
from oslo_utils import versionutils

from masakari.api import utils as api_utils
from masakari import db
from masakari import exception
from masakari import objects
from masakari.objects import base
from masakari.objects import fields

LOG = logging.getLogger(__name__)


@base.MasakariObjectRegistry.register
class FailoverSegment(base.MasakariPersistentObject, base.MasakariObject,
                      base.MasakariObjectDictCompat):
    # 1.0, init
    # 1.1, add enabled field
    VERSION = '1.1'

    fields = {
        'id': fields.IntegerField(),
        'uuid': fields.UUIDField(),
        'name': fields.StringField(),
        'service_type': fields.StringField(),
        'enabled': fields.BooleanField(default=True),
        'description': fields.StringField(nullable=True),
        'recovery_method': fields.FailoverSegmentRecoveryMethodField(),
        }

    def obj_make_compatible(self, primitive, target_version):
        super(FailoverSegment, self).obj_make_compatible(primitive,
                                                         target_version)
        target_version = versionutils.convert_version_to_tuple(target_version)
        if target_version < (1, 1) and 'enabled' in primitive:
            del primitive['enabled']

    @staticmethod
    def _from_db_object(context, segment, db_segment):
        for key in segment.fields:
            setattr(segment, key, db_segment[key])
        segment._context = context
        segment.obj_reset_changes()
        return segment

    @base.remotable_classmethod
    def get_by_id(cls, context, id):
        db_inst = db.failover_segment_get_by_id(context, id)
        return cls._from_db_object(context, cls(), db_inst)

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid):
        db_inst = db.failover_segment_get_by_uuid(context, uuid)
        return cls._from_db_object(context, cls(), db_inst)

    @base.remotable_classmethod
    def get_by_name(cls, context, name):
        db_inst = db.failover_segment_get_by_name(context, name)
        return cls._from_db_object(context, cls(), db_inst)

    @base.remotable
    def create(self):
        if self.obj_attr_is_set('id'):
            raise exception.ObjectActionError(action='create',
                                              reason='already created')
        updates = self.masakari_obj_get_changes()

        if 'uuid' not in updates:
            updates['uuid'] = uuidutils.generate_uuid()
            LOG.debug('Generated uuid %(uuid)s for failover segment',
                      dict(uuid=updates['uuid']))

        api_utils.notify_about_segment_api(self._context, self,
            action=fields.EventNotificationAction.SEGMENT_CREATE,
            phase=fields.EventNotificationPhase.START)

        db_segment = db.failover_segment_create(self._context, updates)

        api_utils.notify_about_segment_api(self._context, self,
            action=fields.EventNotificationAction.SEGMENT_CREATE,
            phase=fields.EventNotificationPhase.END)

        self._from_db_object(self._context, self, db_segment)

    @base.remotable
    def save(self):
        updates = self.masakari_obj_get_changes()
        updates.pop('id', None)

        api_utils.notify_about_segment_api(self._context, self,
            action=fields.EventNotificationAction.SEGMENT_UPDATE,
            phase=fields.EventNotificationPhase.START)

        db_segment = db.failover_segment_update(self._context,
                                                self.uuid, updates)

        api_utils.notify_about_segment_api(self._context, self,
            action=fields.EventNotificationAction.SEGMENT_UPDATE,
            phase=fields.EventNotificationPhase.END)

        self._from_db_object(self._context, self, db_segment)

    @base.remotable
    def destroy(self):
        if not self.obj_attr_is_set('id'):
            raise exception.ObjectActionError(action='destroy',
                                              reason='already destroyed')
        if not self.obj_attr_is_set('uuid'):
            raise exception.ObjectActionError(action='destroy',
                                              reason='no uuid')

        api_utils.notify_about_segment_api(self._context, self,
            action=fields.EventNotificationAction.SEGMENT_DELETE,
            phase=fields.EventNotificationPhase.START)

        db.failover_segment_delete(self._context, self.uuid)

        api_utils.notify_about_segment_api(self._context, self,
            action=fields.EventNotificationAction.SEGMENT_DELETE,
            phase=fields.EventNotificationPhase.END)

        delattr(self, base.get_attrname('id'))

    def is_under_recovery(self, filters=None):
        return db.is_failover_segment_under_recovery(self._context, self.uuid,
                                                     filters=filters)


@base.MasakariObjectRegistry.register
class FailoverSegmentList(base.ObjectListBase, base.MasakariObject):

    VERSION = '1.0'

    fields = {
        'objects': fields.ListOfObjectsField('FailoverSegment'),
        }

    @base.remotable_classmethod
    def get_all(cls, ctxt, filters=None, sort_keys=None,
                sort_dirs=None, limit=None, marker=None):

        groups = db.failover_segment_get_all_by_filters(ctxt, filters=filters,
                                                        sort_keys=sort_keys,
                                                        sort_dirs=sort_dirs,
                                                        limit=limit,
                                                        marker=marker)

        return base.obj_make_list(ctxt, cls(ctxt), objects.FailoverSegment,
                                  groups)
