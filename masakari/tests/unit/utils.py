#    Copyright 2011 OpenStack Foundation
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

import errno
import platform
import socket
import sys

import masakari.conf
import masakari.context
import masakari.utils

CONF = masakari.conf.CONF


def get_test_admin_context():
    return masakari.context.get_admin_context()


def is_linux():
    return platform.system() == 'Linux'


def coreutils_readlink_available():
    _out, err = masakari.utils.trycmd('readlink', '-nm', '/')
    return err == ''


def is_ipv6_supported():
    has_ipv6_support = socket.has_ipv6
    try:
        s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        s.close()
    except socket.error as e:
        if e.errno == errno.EAFNOSUPPORT:
            has_ipv6_support = False
        else:
            raise

    # check if there is at least one interface with ipv6
    if has_ipv6_support and sys.platform.startswith('linux'):
        try:
            with open('/proc/net/if_inet6') as f:
                if not f.read():
                    has_ipv6_support = False
        except IOError:
            has_ipv6_support = False

    return has_ipv6_support


def get_api_version(request):
    if request.path[2:3].isdigit():
        return int(request.path[2:3])


def _compare_args(args1, args2, cmp):
    return all(cmp(*pair) for pair in zip(args1, args2))


def _compare_kwargs(kwargs1, kwargs2, cmp):
    return all(cmp(kwargs1[k], kwargs2[k])
               for k in set(list(kwargs1.keys()) + list(kwargs2.keys())))
