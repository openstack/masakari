#!/usr/bin/env python3
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
  CLI interface for masakari management.
"""


import logging as python_logging
import sys
import time

from oslo_config import cfg
from oslo_db.sqlalchemy import migration
from oslo_log import log as logging

import masakari.conf
from masakari import context
from masakari import db
from masakari.db import api as db_api
from masakari.db.sqlalchemy import migration as db_migration
from masakari import exception
from masakari.i18n import _
from masakari import utils
from masakari import version


CONF = masakari.conf.CONF
logging.register_options(CONF)


# Decorators for actions
def args(*args, **kwargs):
    def _decorator(func):
        func.__dict__.setdefault('args', []).insert(0, (args, kwargs))
        return func
    return _decorator


def _db_error(caught_exception):
    print('%s' % caught_exception)
    print(_("The above error may show that the database has not "
            "been created.\nPlease create a database using "
            "'masakari-manage db sync' before running this command."))
    sys.exit(1)


class DbCommands(object):
    """Class for managing the database."""

    def __init__(self):
        pass

    @args('version', nargs='?', default=None, type=int,
          help='Database version')
    def sync(self, version=None):
        """Sync the database up to the most recent version."""
        try:
            return db_migration.db_sync(version)
        except exception.InvalidInput as ex:
            print(ex)
            sys.exit(1)

    def version(self):
        """Print the current database version."""
        print(migration.db_version(db_api.get_engine(),
                                   db_migration.MIGRATE_REPO_PATH,
                                   db_migration.INIT_VERSION))

    @args('--age_in_days', type=int, default=30,
          help='Purge deleted rows older than age in days (default: '
               '%(default)d)')
    @args('--max_rows', type=int, default=-1,
          help='Limit number of records to delete (default: %(default)d)')
    def purge(self, age_in_days, max_rows):
        """Purge rows older than a given age from masakari tables."""
        try:
            max_rows = utils.validate_integer(
                max_rows, 'max_rows', -1, db.MAX_INT)
        except exception.Invalid as exc:
            sys.exit(str(exc))

        try:
            age_in_days = int(age_in_days)
        except ValueError:
            msg = 'Invalid value for age, %(age)s' % {'age': age_in_days}
            sys.exit(str(msg))

        if max_rows == 0:
            sys.exit(_("Must supply value greater than 0 for max_rows."))
        if age_in_days < 0:
            sys.exit(_("Must supply a non-negative value for age."))
        if age_in_days >= (int(time.time()) / 86400):
            sys.exit(_("Maximal age is count of days since epoch."))
        ctx = context.get_admin_context()

        db_api.purge_deleted_rows(ctx, age_in_days, max_rows)


CATEGORIES = {
    'db': DbCommands,
}


def methods_of(obj):
    """Return non-private methods from an object.

    Get all callable methods of an object that don't start with underscore
    :return: a list of tuples of the form (method_name, method)
    """
    result = []
    for i in dir(obj):
        if callable(getattr(obj, i)) and not i.startswith('_'):
            result.append((i, getattr(obj, i)))
    return result


def add_command_parsers(subparsers):
    for category in CATEGORIES:
        command_object = CATEGORIES[category]()

        parser = subparsers.add_parser(category)
        parser.set_defaults(command_object=command_object)

        category_subparsers = parser.add_subparsers(dest='action')

        for (action, action_fn) in methods_of(command_object):
            parser = category_subparsers.add_parser(action)

            action_kwargs = []
            for args, kwargs in getattr(action_fn, 'args', []):
                parser.add_argument(*args, **kwargs)

            parser.set_defaults(action_fn=action_fn)
            parser.set_defaults(action_kwargs=action_kwargs)


command_opt = cfg.SubCommandOpt('category',
                                title='Command categories',
                                help='Available categories',
                                handler=add_command_parsers)


def get_arg_string(args):
    arg = None
    if args[0] == '-':
        # NOTE(Dinesh_Bhor): args starts with FLAGS.oparser.prefix_chars
        # is optional args. Notice that cfg module takes care of
        # actual ArgParser so prefix_chars is always '-'.
        if args[1] == '-':
            # This is long optional arg
            arg = args[2:]
        else:
            arg = args[1:]
    else:
        arg = args

    return arg


def fetch_func_args(func):
    fn_args = []
    for args, kwargs in getattr(func, 'args', []):
        arg = get_arg_string(args[0])
        fn_args.append(getattr(CONF.category, arg))

    return fn_args


def main():
    """Parse options and call the appropriate class/method."""
    CONF.register_cli_opt(command_opt)
    script_name = sys.argv[0]
    if len(sys.argv) < 2:
        print(_("\nOpenStack masakari version: %(version)s\n") %
              {'version': version.version_string()})
        print(script_name + " category action [<args>]")
        print(_("Available categories:"))
        for category in CATEGORIES:
            print(_("\t%s") % category)
        sys.exit(2)

    try:
        CONF(sys.argv[1:], project='masakari',
             version=version.version_string())
        logging.setup(CONF, "masakari")
        python_logging.captureWarnings(True)
    except cfg.ConfigDirNotFoundError as details:
        print(_("Invalid directory: %s") % details)
        sys.exit(2)
    except cfg.ConfigFilesNotFoundError as e:
        cfg_files = ', '.join(e.config_files)
        print(_("Failed to read configuration file(s): %s") % cfg_files)
        sys.exit(2)

    fn = CONF.category.action_fn
    fn_args = fetch_func_args(fn)
    fn(*fn_args)
