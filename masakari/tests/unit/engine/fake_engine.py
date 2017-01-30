#    Copyright (c) 2016 NTT DATA
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

from oslo_utils import timeutils
from oslo_versionedobjects import fields

from masakari import objects
from masakari.tests import uuidsentinel

NOW = timeutils.utcnow().replace(microsecond=0)


def fake_db_notification(**updates):
    db_notification = {
        "type": "VM",
        "id": 1,
        "payload":
            {'event': 'STOPPED', 'host_status': 'NORMAL',
             'cluster_status': 'ONLINE'
             },
        "source_host_uuid": uuidsentinel.fake_host,
        "generated_time": NOW,
        "status": "running",
        "notification_uuid": uuidsentinel.fake_notification,
        "created_at": NOW,
        "updated_at": None,
        "deleted_at": None,
        "deleted": 0
    }

    for name, field in objects.Notification.fields.items():
        if name in db_notification:
            continue
        if field.nullable:
            db_notification[name] = None
        elif field.default != fields.UnspecifiedDefault:
            db_notification[name] = field.default
        else:
            raise Exception('fake_db_notification needs help with %s' % name)

    if updates:
        db_notification.update(updates)

    return db_notification


def fake_notification_obj(context, **updates):
    return objects.Notification(**updates)
