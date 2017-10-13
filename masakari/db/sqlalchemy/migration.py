# Copyright 2016 NTT Data.
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

import os
import threading

from oslo_config import cfg
from oslo_db import exception as oslo_exception
from oslo_db import options
from stevedore import driver

from masakari import db
from masakari.db import api as db_api
from masakari import exception
from masakari.i18n import _

INIT_VERSION = 0

_IMPL = None
_LOCK = threading.Lock()

options.set_defaults(cfg.CONF)

MIGRATE_REPO_PATH = os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    'migrate_repo',
)


def get_backend():
    global _IMPL
    if _IMPL is None:
        with _LOCK:
            if _IMPL is None:
                _IMPL = driver.DriverManager(
                    "masakari.database.migration_backend",
                    cfg.CONF.database.backend).driver
    return _IMPL


def db_sync(version=None, init_version=INIT_VERSION, engine=None):
    if engine is None:
        engine = db_api.get_engine()

    current_db_version = get_backend().db_version(engine,
                                                  MIGRATE_REPO_PATH,
                                                  init_version)

    if version and int(version) < current_db_version:
        msg = _('Database schema downgrade is not allowed.')
        raise exception.InvalidInput(reason=msg)

    if version and int(version) > db.MAX_INT:
        message = _('Version should be less than or equal to %(max_version)d.'
                    ) % {'max_version': db.MAX_INT}
        raise exception.InvalidInput(reason=message)

    try:
        return get_backend().db_sync(engine=engine,
                                     abs_path=MIGRATE_REPO_PATH,
                                     version=version,
                                     init_version=init_version)
    except oslo_exception.DBMigrationError as exc:
        raise exception.InvalidInput(reason=exc)
