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

base_options = [
    cfg.StrOpt(
        'tempdir',
        help='Explicitly specify the temporary working directory.'),
    cfg.BoolOpt(
        'monkey_patch',
        default=False,
        help="""
Determine if monkey patching should be applied.

Related options:

  * ``monkey_patch_modules``: This must have values set for this option to have
  any effect
"""),
    cfg.ListOpt(
        'monkey_patch_modules',
        default=['masakari.api:masakari.cmd'],
        help="""
List of modules/decorators to monkey patch.

This option allows you to patch a decorator for all functions in specified
modules.

Related options:

  * ``monkey_patch``: This must be set to ``True`` for this option to
    have any effect
"""),
]


def register_opts(conf):
    conf.register_opts(base_options)


def list_opts():
    return {'DEFAULT': base_options}
