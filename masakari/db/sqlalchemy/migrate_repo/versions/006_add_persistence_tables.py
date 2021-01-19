# Copyright 2019 NTT Data.
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

import masakari.conf
from masakari.engine import driver

CONF = masakari.conf.CONF


def upgrade(migrate_engine):
    """Upgrade the engine with persistence tables. """

    # Get the taskflow driver configured, default is 'taskflow_driver',
    # to load persistence tables to store progress details.
    taskflow_driver = driver.load_masakari_driver(CONF.notification_driver)

    if CONF.taskflow.connection:
        taskflow_driver.upgrade_backend(CONF.taskflow.connection)
