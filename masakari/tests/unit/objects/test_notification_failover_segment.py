# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import uuid

from oslo_utils import timeutils

from masakari.objects import notification
from masakari.tests.unit import base


class TestNotificationFailoverSegment(base.TestCase):

    def test_notification_has_failover_segment_uuid_field(self):
        """Verify notification object has failover_segment_uuid field."""
        self.assertIn('failover_segment_uuid',
                      notification.Notification.fields)

    def test_notification_serialization_with_failover_segment_uuid(self):
        """Test that notification can be serialized with all fields."""
        now = timeutils.utcnow()

        notif_dict = {
            'id': 1,
            'notification_uuid': str(uuid.uuid4()),
            'generated_time': now,
            'payload': {'event': 'STOPPED'},
            'source_host_uuid': str(uuid.uuid4()),
            'failover_segment_uuid': str(uuid.uuid4()),
            'status': 'new',
            'created_at': now,
            'updated_at': None,
        }

        notif = notification.Notification(**notif_dict)

        self.assertEqual(notif.failover_segment_uuid,
                         notif_dict['failover_segment_uuid'])

        # Use dict(notif.items()) instead of .to_dict()
        result = dict(notif.items())
        self.assertIn('failover_segment_uuid', result)

    def test_notification_serialization_with_none_failover_segment_uuid(self):
        """Verify object accepts None for failover_segment_uuid.

        Addresses Bug #2150102.
        """
        now = timeutils.utcnow()

        notif_dict = {
            'id': 2,
            'notification_uuid': str(uuid.uuid4()),
            'generated_time': now,
            'payload': {'event': 'STOPPED'},
            'source_host_uuid': str(uuid.uuid4()),
            'failover_segment_uuid': None,
            'status': 'new',
            'created_at': now,
            'updated_at': None,
        }

        # This will pass cleanly once nullable=True is added
        notif = notification.Notification(**notif_dict)
        self.assertIsNone(notif.failover_segment_uuid)
