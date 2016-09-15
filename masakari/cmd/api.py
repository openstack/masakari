# Copyright 2016 NTT DATA
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""Starter script for Masakari API.

"""

import sys

from oslo_log import log as logging
import six

import masakari.conf
from masakari import config
from masakari import exception
from masakari.i18n import _LE, _LW
from masakari import objects
from masakari import service


CONF = masakari.conf.CONF


def main():
    config.parse_args(sys.argv)
    logging.setup(CONF, "masakari")
    log = logging.getLogger(__name__)
    objects.register_all()

    launcher = service.process_launcher()
    started = 0
    try:
        server = service.WSGIService("masakari_api", use_ssl=CONF.use_ssl)
        launcher.launch_service(server, workers=server.workers or 1)
        started += 1
    except exception.PasteAppNotFound as ex:
        log.warning(
            _LW("%s. ``enabled_apis`` includes bad values. "
                "Fix to remove this warning."), six.text_type(ex))

    if started == 0:
        log.error(_LE('No APIs were started. '
                      'Check the enabled_apis config option.'))
        sys.exit(1)

    launcher.wait()
