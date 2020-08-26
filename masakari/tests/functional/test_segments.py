# Copyright (C) 2019 NTT DATA
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

from openstack import exceptions

from masakari.objects import fields
from masakari.tests.functional import base


class TestSegments(base.BaseFunctionalTest):
    def test_create_get_delete(self):
        # This test will create, get and delete a segment
        segment_data = {'name': self.getUniqueString(),
                'recovery_method': fields.FailoverSegmentRecoveryMethod.AUTO,
                'service_type': 'COMPUTE'}
        segment = self.admin_conn.ha.create_segment(**segment_data)

        self.assertDictContainsSubset(segment_data, segment)

        result = self.admin_conn.ha.get_segment(segment.uuid)

        self.assertEqual(segment.name, result.name)
        self.assertEqual(segment.recovery_method, result.recovery_method)
        self.assertEqual(segment.service_type, result.service_type)

        self.admin_conn.ha.delete_segment(segment.uuid)
        self.assertRaises(exceptions.ResourceNotFound,
                          self.admin_conn.ha.get_segment, segment.uuid)

    def test_create_delete_with_host(self):
        # This test is for deleting a segment with hosts
        if not self.hypervisors:
            self.skipTest("Skipped as there are no hypervisors "
                          "configured in nova")

        segment = self.admin_conn.ha.create_segment(
            name=self.getUniqueString(),
            recovery_method=fields.FailoverSegmentRecoveryMethod.AUTO,
            service_type='COMPUTE')

        # Create valid host
        host_name = self.hypervisors[0]['name']

        host = self.admin_conn.ha.create_host(segment_id=segment.uuid,
                                        name=host_name,
                                        type='COMPUTE',
                                        control_attributes='SSH')

        result = self.admin_conn.ha.get_segment(segment.uuid)
        self.assertEqual(segment.name, result.name)

        # Delete segment, which should delete hosts as well
        self.admin_conn.ha.delete_segment(segment['uuid'])
        self.assertRaises(exceptions.ResourceNotFound,
                          self.admin_conn.ha.get_segment, segment.uuid)
        self.assertRaises(exceptions.ResourceNotFound,
                          self.admin_conn.ha.get_host, host.uuid, segment.uuid)

    def test_list(self):
        # This test is for listing segments using filters
        segment_data_1 = {'name': self.getUniqueString(),
                  'recovery_method': fields.FailoverSegmentRecoveryMethod.AUTO,
                  'service_type': 'COMPUTE'}

        segment_data_2 = {'name': self.getUniqueString(),
                  'recovery_method':
                      fields.FailoverSegmentRecoveryMethod.RESERVED_HOST,
                  'service_type': 'COMPUTE'}

        # Create segments
        segment_1 = self.admin_conn.ha.create_segment(**segment_data_1)
        segment_2 = self.admin_conn.ha.create_segment(**segment_data_2)

        # Delete segments
        self.addCleanup(self.admin_conn.ha.delete_segment, segment_1.uuid)
        self.addCleanup(self.admin_conn.ha.delete_segment, segment_2.uuid)

        segments = self.admin_conn.ha.segments()
        self.assertCountEqual([segment_1, segment_2], segments)

    def test_list_with_filter(self):
        # This test is for listing segments using filters
        segment_data_1 = {'name': self.getUniqueString(),
                  'recovery_method': fields.FailoverSegmentRecoveryMethod.AUTO,
                  'service_type': 'COMPUTE'}

        segment_data_2 = {'name': self.getUniqueString(),
                  'recovery_method':
                      fields.FailoverSegmentRecoveryMethod.RESERVED_HOST,
                  'service_type': 'COMPUTE'}

        # Create segments
        segment_1 = self.admin_conn.ha.create_segment(**segment_data_1)
        segment_2 = self.admin_conn.ha.create_segment(**segment_data_2)

        # Delete segments
        self.addCleanup(self.admin_conn.ha.delete_segment, segment_1.uuid)
        self.addCleanup(self.admin_conn.ha.delete_segment, segment_2.uuid)

        for seg_object in self.admin_conn.ha.segments(
                recovery_method=fields.FailoverSegmentRecoveryMethod.AUTO):

            self.assertDictContainsSubset(segment_data_1, seg_object)

        for seg_object in self.admin_conn.ha.segments(
                recovery_method=fields.FailoverSegmentRecoveryMethod.
                RESERVED_HOST):

            self.assertDictContainsSubset(segment_data_2, seg_object)

    def test_update_with_host(self):
        # This test is for updating segment with host
        if not self.hypervisors:
            self.skipTest("Skipped as there are no hypervisors "
                          "configured in nova")

        segment = self.admin_conn.ha.create_segment(
            name=self.getUniqueString(),
            recovery_method=fields.FailoverSegmentRecoveryMethod.AUTO,
            service_type='COMPUTE')

        # Delete segment
        self.addCleanup(self.admin_conn.ha.delete_segment, segment.uuid)

        # Create valid host
        host_name = self.hypervisors[0]['name']

        self.admin_conn.ha.create_host(segment_id=segment.uuid, name=host_name,
                                type='COMPUTE', control_attributes='SSH')

        # Update segment
        segment_1 = self.admin_conn.ha.update_segment(segment.uuid,
            name=self.getUniqueString(),
            recovery_method=fields.FailoverSegmentRecoveryMethod.RESERVED_HOST,
            service_type='CONTROLLER')

        result = self.admin_conn.ha.get_segment(segment.uuid)
        self.assertEqual(segment_1.name, result.name)
        self.assertEqual(segment_1.recovery_method, result.recovery_method)
        self.assertEqual(segment_1.service_type, result.service_type)
