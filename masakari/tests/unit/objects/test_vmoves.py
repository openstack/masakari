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

from unittest import mock

from oslo_utils import timeutils

from masakari import exception
from masakari.objects import vmove
from masakari.tests.unit.objects import test_objects
from masakari.tests import uuidsentinel

NOW = timeutils.utcnow().replace(microsecond=0)


fake_vmove = {
    'created_at': NOW,
    'updated_at': None,
    'deleted_at': None,
    'deleted': False,
    'id': 1,
    'uuid': uuidsentinel.fake_vmove,
    'notification_uuid': uuidsentinel.fake_notification,
    'instance_uuid': uuidsentinel.fake_instance,
    'instance_name': 'fake_vm',
    'source_host': 'fake_host1',
    'dest_host': None,
    'start_time': None,
    'end_time': None,
    'status': 'pending',
    'type': 'evacuation',
    'message': None
    }


class TestVMoveObject(test_objects._LocalTest):

    @mock.patch('masakari.db.vmove_get_by_uuid')
    def test_get_by_uuid(self, mock_api_get):

        mock_api_get.return_value = fake_vmove

        vmove_obj = vmove.VMove.get_by_uuid(
            self.context, uuidsentinel.fake_vmove)
        self.compare_obj(vmove_obj, fake_vmove)

        mock_api_get.assert_called_once_with(self.context,
                                             uuidsentinel.fake_vmove)

    def _vmove_create_attributes(self):

        vmove_obj = vmove.VMove(context=self.context)
        vmove_obj.uuid = uuidsentinel.fake_vmove
        vmove_obj.notification_uuid = uuidsentinel.fake_notification
        vmove_obj.instance_uuid = uuidsentinel.fake_instance
        vmove_obj.instance_name = 'fake_vm1'
        vmove_obj.source_host = 'fake_host1'
        vmove_obj.status = 'pending'
        vmove_obj.type = 'evacuation'

        return vmove_obj

    @mock.patch('masakari.db.vmove_create')
    def test_create(self, mock_vmove_create):

        mock_vmove_create.return_value = fake_vmove
        vmove_obj = self._vmove_create_attributes()
        vmove_obj.create()

        self.compare_obj(vmove_obj, fake_vmove)
        mock_vmove_create.assert_called_once_with(self.context, {
            'uuid': uuidsentinel.fake_vmove,
            'notification_uuid': uuidsentinel.fake_notification,
            'instance_uuid': uuidsentinel.fake_instance,
            'instance_name': 'fake_vm1',
            'source_host': 'fake_host1',
            'status': 'pending',
            'type': 'evacuation'
        })

    @mock.patch('masakari.db.vmoves_get_all_by_filters')
    def test_get_limit_and_marker_invalid_marker(self, mock_api_get):
        vmove_uuid = uuidsentinel.fake_vmove
        mock_api_get.side_effect = (exception.
                                    MarkerNotFound(marker=vmove_uuid))

        self.assertRaises(exception.MarkerNotFound,
                          vmove.VMoveList.get_all,
                          self.context, limit=5, marker=vmove_uuid)

    @mock.patch('masakari.db.vmove_update')
    def test_save(self, mock_vmove_update):

        mock_vmove_update.return_value = fake_vmove

        vmove_obj = self._vmove_create_attributes()
        vmove_obj.uuid = uuidsentinel.fake_vmove
        vmove_obj.save()

        self.compare_obj(vmove_obj, fake_vmove)
        (mock_vmove_update.assert_called_once_with(
            self.context, uuidsentinel.fake_vmove,
            {'uuid': uuidsentinel.fake_vmove,
             'notification_uuid': uuidsentinel.fake_notification,
             'instance_uuid': uuidsentinel.fake_instance,
             'instance_name': 'fake_vm1',
             'source_host': 'fake_host1',
             'status': 'pending',
             'type': 'evacuation'}))
