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


auth_opts = [
    cfg.StrOpt("auth_strategy",
               default="keystone",
               choices=("keystone", "noauth2"),
               help="""
This determines the strategy to use for authentication: keystone or noauth2.
'noauth2' is designed for testing only, as it does no actual credential
checking. 'noauth2' provides administrative credentials only if 'admin' is
specified as the username.

* Possible values:

    Either 'keystone' (default) or 'noauth2'.

* Services that use this:

    ``masakari-api``

* Related options:

    None
"""),
    cfg.BoolOpt("use_forwarded_for",
                default=False,
                help="""
When True, the 'X-Forwarded-For' header is treated as the canonical remote
address. When False (the default), the 'remote_address' header is used.

You should only enable this if you have an HTML sanitizing proxy.

* Possible values:

    True, False (default)

* Services that use this:

    ``masakari-api``

* Related options:

    None
"""),
]


osapi_opts = [
    cfg.IntOpt("osapi_max_limit",
               default=1000,
               help="""
As a query can potentially return many thousands of items, you can limit the
maximum number of items in a single response by setting this option.

* Possible values:

    Any positive integer. Default is 1000.

* Services that use this:

    ``masakari-api``

* Related options:

    None
"""),
    cfg.StrOpt("osapi_masakari_link_prefix",
               help="""
This string is prepended to the normal URL that is returned in links to the
OpenStack Masakari API. If it is empty (the default), the URLs are returned
unchanged.

* Possible values:

    Any string, including an empty string (the default).

* Services that use this:

    ``masakari-api``

* Related options:

    None
"""),
]


ALL_OPTS = (auth_opts + osapi_opts)


def register_opts(conf):
    conf.register_opts(ALL_OPTS)


def list_opts():
    return {"DEFAULT": ALL_OPTS}
