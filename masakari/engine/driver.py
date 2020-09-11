# Copyright 2016 NTT DATA
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

"""
Driver base-class:

    (Beginning of) the contract that masakari drivers must follow, and shared
    types that support that contract
"""

import abc
import sys

from oslo_log import log as logging
from stevedore import driver

import masakari.conf
from masakari import utils


CONF = masakari.conf.CONF
LOG = logging.getLogger(__name__)


class NotificationDriver(object, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def execute_host_failure(self, context, host_name, recovery_method,
                             notification_uuid, **kwargs):
        pass

    @abc.abstractmethod
    def execute_instance_failure(self, context, instance_uuid,
                                 notification_uuid):
        pass

    @abc.abstractmethod
    def execute_process_failure(self, context, process_name, host_name,
                                notification_uuid):
        pass

    @abc.abstractmethod
    def get_notification_recovery_workflow_details(self, context,
                                                   recovery_method,
                                                   notification_uuid):
        pass

    @abc.abstractmethod
    def upgrade_backend(self, backend):
        pass


def load_masakari_driver(masakari_driver=None):
    """Load a masakari driver module.

    Load the masakari driver module specified by the notification_driver
    configuration option or, if supplied, the driver name supplied as an
    argument.

    :param masakari_driver: a masakari driver name to override the config opt
    :returns: a NotificationDriver instance
    """
    if not masakari_driver:
        masakari_driver = CONF.notification_driver

    if not masakari_driver:
        LOG.error("Notification driver option required, but not specified")
        sys.exit(1)

    LOG.info("Loading masakari notification driver '%s'", masakari_driver)
    try:
        notification_driver = driver.DriverManager('masakari.driver',
                                                   masakari_driver,
                                                   invoke_on_load=True).driver
        return utils.check_isinstance(notification_driver, NotificationDriver)
    except ImportError:
        LOG.exception("Failed to load notification driver '%s'.",
                      masakari_driver)
        sys.exit(1)
