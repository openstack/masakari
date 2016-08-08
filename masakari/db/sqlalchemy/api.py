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
"""Implementation of SQLAlchemy backend."""

import sys

from oslo_db.sqlalchemy import enginefacade

import masakari.conf


CONF = masakari.conf.CONF

main_context_manager = enginefacade.transaction_context()


def _get_db_conf(conf_group, connection=None):

    return {'connection': connection or conf_group.connection,
            'slave_connection': conf_group.slave_connection,
            'sqlite_fk': False,
            '__autocommit': True,
            'expire_on_commit': False,
            'mysql_sql_mode': conf_group.mysql_sql_mode,
            'idle_timeout': conf_group.idle_timeout,
            'connection_debug': conf_group.connection_debug,
            'max_pool_size': conf_group.max_pool_size,
            'max_overflow': conf_group.max_overflow,
            'pool_timeout': conf_group.pool_timeout,
            'sqlite_synchronous': conf_group.sqlite_synchronous,
            'connection_trace': conf_group.connection_trace,
            'max_retries': conf_group.max_retries,
            'retry_interval': conf_group.retry_interval}


def _context_manager_from_context(context):
    if context:
        try:
            return context.db_connection
        except AttributeError:
            pass


def get_backend():
    """The backend is this module itself."""
    return sys.modules[__name__]


def configure(conf):
    main_context_manager.configure(**_get_db_conf(conf.database))


def get_engine(use_slave=False, context=None):
    """Get a database engine object.

    :param use_slave: Whether to use the slave connection
    :param context: The request context that can contain a context manager
    """
    ctxt_mgr = _context_manager_from_context(context) or main_context_manager
    return ctxt_mgr.get_legacy_facade().get_engine(use_slave=use_slave)
