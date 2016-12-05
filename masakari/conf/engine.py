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
            default="ha_engine",
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


driver_opts = [
    cfg.StrOpt(
        'notification_driver',
        default='taskflow_driver',
        help="""
Defines which driver to use for executing notification workflows.
"""),
]


notification_opts = [
    cfg.IntOpt('duplicate_notification_detection_interval',
               default=180,
               min=0,
               help="Interval in seconds for identifying duplicate "
                    "notifications. If the notification received is identical "
                    "to the previous ones whose status is either new or "
                    "running and if it's created_timestamp and the current "
                    "timestamp is less than this config option value, then "
                    "the notification will be considered as duplicate and "
                    "it will be ignored."
               ),
    cfg.IntOpt('wait_period_after_service_disabled',
               default=180,
               help='Wait until service is disabled'),
    cfg.IntOpt('wait_period_after_evacuation',
               default=90,
               help='Wait until instance is evacuated'),
    cfg.IntOpt('verify_interval',
               default=1,
               help='The monitoring interval for looping'),
    cfg.IntOpt('wait_period_after_power_off',
               default=60,
               help='Number of seconds to wait for instance to shut down'),
    cfg.IntOpt('wait_period_after_power_on',
               default=60,
               help='Number of seconds to wait for instance to start'),
]


ALL_OPTS = (rpcapi_opts + notification_opts + driver_opts)


def register_opts(conf):
    conf.register_opts(ALL_OPTS)


def list_opts():
    return {'DEFAULT': ALL_OPTS}
