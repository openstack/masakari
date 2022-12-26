# Copyright(c) 2022 Inspur
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo_log import log as logging
from oslo_utils import uuidutils

from masakari import db
from masakari import exception
from masakari import objects
from masakari.objects import base
from masakari.objects import fields

LOG = logging.getLogger(__name__)


@base.MasakariObjectRegistry.register
class VMove(base.MasakariPersistentObject, base.MasakariObject,
            base.MasakariObjectDictCompat):
    VERSION = '1.0'

    fields = {
        'id': fields.IntegerField(),
        'uuid': fields.UUIDField(),
        'notification_uuid': fields.UUIDField(),
        'instance_uuid': fields.UUIDField(),
        'instance_name': fields.StringField(),
        'source_host': fields.StringField(nullable=True),
        'dest_host': fields.StringField(nullable=True),
        'start_time': fields.DateTimeField(nullable=True),
        'end_time': fields.DateTimeField(nullable=True),
        'type': fields.VMoveTypeField(nullable=True),
        'status': fields.VMoveStatusField(nullable=True),
        'message': fields.StringField(nullable=True),
        }

    @staticmethod
    def _from_db_object(context, vmove, db_vmove):
        for key in vmove.fields:
            setattr(vmove, key, db_vmove[key])

        vmove._context = context
        vmove.obj_reset_changes()
        return vmove

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid):
        db_inst = db.vmove_get_by_uuid(context, uuid)
        return cls._from_db_object(context, cls(), db_inst)

    @base.remotable
    def create(self):
        if self.obj_attr_is_set('id'):
            raise exception.ObjectActionError(action='create',
                                              reason='already created')
        updates = self.masakari_obj_get_changes()

        if 'uuid' not in updates:
            updates['uuid'] = uuidutils.generate_uuid()

        vmove = db.vmove_create(self._context, updates)
        self._from_db_object(self._context, self, vmove)

    @base.remotable
    def save(self):
        updates = self.masakari_obj_get_changes()
        updates.pop('id', None)

        vmove = db.vmove_update(self._context, self.uuid, updates)
        self._from_db_object(self._context, self, vmove)


@base.MasakariObjectRegistry.register
class VMoveList(base.ObjectListBase, base.MasakariObject):

    VERSION = '1.0'

    fields = {
        'objects': fields.ListOfObjectsField('VMove'),
        }

    @base.remotable_classmethod
    def get_all(cls, ctxt, filters=None, sort_keys=None,
                sort_dirs=None, limit=None, marker=None):

        groups = db.vmoves_get_all_by_filters(ctxt, filters=filters,
                                              sort_keys=sort_keys,
                                              sort_dirs=sort_dirs,
                                              limit=limit,
                                              marker=marker)

        return base.obj_make_list(ctxt, cls(ctxt), objects.VMove,
                                  groups)

    @base.remotable_classmethod
    def get_all_vmoves(cls, ctxt, notification_uuid, status=None):
        filters = {
            'notification_uuid': notification_uuid
            }
        if status:
            filters['status'] = status

        groups = db.vmoves_get_all_by_filters(ctxt, filters=filters)
        return base.obj_make_list(ctxt, cls(ctxt), objects.VMove,
                                  groups)
