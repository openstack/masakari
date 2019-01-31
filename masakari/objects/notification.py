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
from oslo_serialization import jsonutils
from oslo_utils import uuidutils

from masakari.api import utils as api_utils
from masakari import db
from masakari import exception
from masakari import objects
from masakari.objects import base
from masakari.objects import fields

LOG = logging.getLogger(__name__)


NOTIFICATION_OPTIONAL_FIELDS = ['recovery_workflow_details']


@base.MasakariObjectRegistry.register
class Notification(base.MasakariPersistentObject, base.MasakariObject,
                   base.MasakariObjectDictCompat):

    # Version 1.0: Initial version
    # Version 1.1: Added recovery_workflow_details field.
    #              Note: This field shouldn't be persisted.
    VERSION = '1.1'

    fields = {
        'id': fields.IntegerField(),
        'notification_uuid': fields.UUIDField(),
        'generated_time': fields.DateTimeField(),
        'source_host_uuid': fields.UUIDField(),
        'type': fields.NotificationTypeField(),
        'payload': fields.DictOfStringsField(),
        'status': fields.NotificationStatusField(),
        # NOTE(ShilpaSD): This field shouldn't be stored in db.
        # The recovery workflow details read from the 'notification_driver'
        # will be set to this field.
        'recovery_workflow_details': fields.ListOfObjectsField(
            'NotificationProgressDetails', default=[])
        }

    @staticmethod
    def _from_db_object(context, notification, db_notification):

        for key in notification.fields:
            if key in NOTIFICATION_OPTIONAL_FIELDS:
                continue
            if key != 'payload':
                setattr(notification, key, db_notification.get(key))
            else:
                payload = db_notification.get("payload")
                notification.payload = jsonutils.loads(payload)

        notification.obj_reset_changes()
        notification._context = context
        return notification

    @base.remotable_classmethod
    def get_by_id(cls, context, id):
        db_notification = db.notification_get_by_id(context, id)
        return cls._from_db_object(context, cls(), db_notification)

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid):
        db_notification = db.notification_get_by_uuid(context, uuid)
        return cls._from_db_object(context, cls(), db_notification)

    @base.remotable
    def create(self):
        if self.obj_attr_is_set('id'):
            raise exception.ObjectActionError(action='create',
                                              reason='already created')
        updates = self.masakari_obj_get_changes()
        # NOTE(ShilpaSD): This field doesn't exist in the Notification
        # db model so don't save it.
        updates.pop('recovery_workflow_details', None)

        if 'notification_uuid' not in updates:
            updates['notification_uuid'] = uuidutils.generate_uuid()
            LOG.debug('Generated uuid %(uuid)s for notifications',
                      dict(uuid=updates['notification_uuid']))

        if 'payload' in updates:
            updates['payload'] = jsonutils.dumps(updates['payload'])

        api_utils.notify_about_notification_api(self._context, self,
            action=fields.EventNotificationAction.NOTIFICATION_CREATE,
            phase=fields.EventNotificationPhase.START)

        db_notification = db.notification_create(self._context, updates)

        api_utils.notify_about_notification_api(self._context, self,
            action=fields.EventNotificationAction.NOTIFICATION_CREATE,
            phase=fields.EventNotificationPhase.END)

        self._from_db_object(self._context, self, db_notification)

    @base.remotable
    def save(self):
        updates = self.masakari_obj_get_changes()

        updates.pop('id', None)
        # NOTE(ShilpaSD): This field doesn't exist in the Notification
        # db model so don't save it.
        updates.pop('recovery_workflow_details', None)

        db_notification = db.notification_update(self._context,
                                                 self.notification_uuid,
                                                 updates)
        self._from_db_object(self._context, self, db_notification)

    @base.remotable
    def destroy(self):
        if not self.obj_attr_is_set('id'):
            raise exception.ObjectActionError(action='destroy',
                                              reason='already destroyed')
        if not self.obj_attr_is_set('notification_uuid'):
            raise exception.ObjectActionError(action='destroy',
                                              reason='no uuid')

        db.notification_delete(self._context, self.notification_uuid)
        delattr(self, base.get_attrname('id'))


@base.MasakariObjectRegistry.register
class NotificationList(base.ObjectListBase, base.MasakariObject):

    VERSION = '1.0'

    fields = {
        'objects': fields.ListOfObjectsField('Notification'),
        }

    @base.remotable_classmethod
    def get_all(cls, context, filters=None, sort_keys=None,
                sort_dirs=None, limit=None, marker=None):

        groups = db.notifications_get_all_by_filters(context, filters=filters,
                                                     sort_keys=sort_keys,
                                                     sort_dirs=sort_dirs,
                                                     limit=limit, marker=marker
                                                     )

        return base.obj_make_list(context, cls(context), objects.Notification,
                                  groups)


def notification_sample(sample):
    """Class decorator to attach the notification sample information
    to the notification object for documentation generation purposes.
     :param sample: the path of the sample json file relative to the
                   doc/notification_samples/ directory in the nova repository
                   root.
    """
    def wrap(cls):
        cls.sample = sample
        return cls
    return wrap


@base.MasakariObjectRegistry.register
class NotificationProgressDetails(base.MasakariObject,
                                  base.MasakariObjectDictCompat):

    VERSION = '1.0'

    fields = {
        'name': fields.StringField(),
        'progress': fields.FloatField(),
        'progress_details': fields.ListOfDictOfNullableStringsField(
            default=[]),
        'state': fields.StringField()
    }

    @classmethod
    def create(cls, name, progress, progress_details, state,):
        return cls(name=name, progress=progress,
                   progress_details=progress_details, state=state)
