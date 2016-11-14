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

from oslo_config import cfg

from masakari.conf import api
from masakari.conf import base
from masakari.conf import database
from masakari.conf import engine
from masakari.conf import engine_driver
from masakari.conf import exceptions
from masakari.conf import nova
from masakari.conf import osapi_v1
from masakari.conf import paths
from masakari.conf import service
from masakari.conf import ssl
from masakari.conf import wsgi

CONF = cfg.CONF

api.register_opts(CONF)
base.register_opts(CONF)
database.register_opts(CONF)
engine.register_opts(CONF)
engine_driver.register_opts(CONF)
exceptions.register_opts(CONF)
nova.register_opts(CONF)
osapi_v1.register_opts(CONF)
paths.register_opts(CONF)
ssl.register_opts(CONF)
service.register_opts(CONF)
wsgi.register_opts(CONF)
