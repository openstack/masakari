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


coordination_opts = [
    cfg.StrOpt('backend_url',
               default=None,
               help="The backend URL to use for distributed coordination."
                    "By default it's None which means that coordination is "
                    "disabled. The coordination is implemented for "
                    "distributed lock management and was tested with etcd."
                    "Coordination doesn't work for file driver because lock "
                    "files aren't removed after lock releasing."),
]


def register_opts(conf):
    """Registers coordination configuration options
    :param conf: configuration
    """
    conf.register_opts(coordination_opts, group="coordination")


def list_opts():
    """Lists coordination configuration options
    :return: coordination configuration options
    """
    return {"coordination": coordination_opts}
