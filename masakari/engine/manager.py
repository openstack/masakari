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

"""Handles all processes relating to notifications.

The :py:class:`MasakariManager` class is a
:py:class:`masakari.manager.Manager` that handles RPC calls relating to
notifications. It is responsible for processing notifications and executing
workflows.

"""

from oslo_log import log as logging
import oslo_messaging as messaging

from masakari import manager


LOG = logging.getLogger(__name__)


class MasakariManager(manager.Manager):
    """Manages the running notifications"""

    target = messaging.Target(version='1.0')

    def __init__(self, masakari_driver=None, *args, **kwargs):
        """Load configuration options"""
        LOG.debug("Initializing Masakari Manager.")
        super(MasakariManager, self).__init__(service_name="engine",
                                             *args, **kwargs)
