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

import socket

from oslo_config import cfg

service_opts = [
    cfg.HostAddressOpt('host',
               default=socket.gethostname(),
               help='''
Hostname, FQDN or IP address of this host. Must be valid within AMQP key.

Possible values:

* String with hostname, FQDN or IP address. Default is hostname of this host.
'''),
    cfg.StrOpt('engine_manager',
               default='masakari.engine.manager.MasakariManager',
               help='Full class name for the Manager for masakari engine'),
    cfg.IntOpt('report_interval',
               default=10,
               help='Seconds between nodes reporting state to datastore'),
    cfg.BoolOpt('periodic_enable',
                default=True,
                help='Enable periodic tasks'),
    cfg.IntOpt('periodic_interval_max',
               default=300,
               help='Max interval time between periodic tasks execution in '
                    'seconds.'),
    cfg.IntOpt('periodic_fuzzy_delay',
               default=60,
               help='Range of seconds to randomly delay when starting the'
                    ' periodic task scheduler to reduce stampeding.'
                    ' (Disable by setting to 0)'),
    cfg.BoolOpt('use_ssl',
                default=False,
                help='Use APIs with SSL enabled'),
    cfg.HostAddressOpt('masakari_api_listen',
               default="0.0.0.0",
               help='The IP address on which the Masakari API will listen.'),
    cfg.IntOpt('masakari_api_listen_port',
               default=15868,
               min=1,
               max=65535,
               help='The port on which the Masakari API will listen.'),
    cfg.IntOpt('masakari_api_workers',
               help='Number of workers for Masakari API service. The default '
                    'will be the number of CPUs available.'),
    cfg.IntOpt('service_down_time',
               default=60,
               help='Maximum time since last check-in for up service'),
    ]


def register_opts(conf):
    conf.register_opts(service_opts)


def list_opts():
    return {'DEFAULT': service_opts}
