# Copyright (C) 2019 NTT DATA
# All Rights Reserved.
#
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

import os
import sys

import openstack
from openstack import connection
from oslotest import base

openstack.enable_logging(
    debug=True,
    http_debug=True,
    stream=sys.stdout,
    format_stream=True,
    format_template='%(asctime)s %(name)-32s %(message)s',
)
#: Defines the OpenStack Client Config (OCC) cloud key in your OCC config
#: file, typically in /etc/openstack/clouds.yaml. That configuration
#: will determine where the functional tests will be run and what resource
#: defaults will be used to run the functional tests.
TEST_CLOUD_NAME = os.getenv('OS_CLOUD', 'devstack-admin')


class BaseFunctionalTest(base.BaseTestCase):

    def setUp(self, ha_api_version="1.0"):
        super(BaseFunctionalTest, self).setUp()

        config = openstack.config.get_cloud_region(
            cloud=TEST_CLOUD_NAME,
            ha_api_version=ha_api_version,
        )
        self.admin_conn = connection.Connection(config=config)

        devstack_user = os.getenv('OS_CLOUD', 'devstack')
        devstack_region = openstack.config.get_cloud_region(
            cloud=devstack_user)
        self.conn = connection.Connection(config=devstack_region)

        self.hypervisors = self._hypervisors()

    def _hypervisors(self):
        hypervisors = connection.Connection.list_hypervisors(
            connection.from_config(cloud_name=TEST_CLOUD_NAME))
        return hypervisors
