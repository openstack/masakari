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


rpcapi_opts = [
    cfg.StrOpt("masakari_topic",
            default="engine",
            help="""
This is the message queue topic that the masakari engine 'listens' on. It is
used when the masakari engine is started up to configure the queue, and
whenever an RPC call to the masakari engine is made.

* Possible values:

    Any string, but there is almost never any reason to ever change this value
    from its default of 'engine'.

* Services that use this:

    ``masakari-engine``

* Related options:

    None
"""),
]


ALL_OPTS = (rpcapi_opts)


def register_opts(conf):
    conf.register_opts(ALL_OPTS)


def list_opts():
    return {'DEFAULT': ALL_OPTS}
