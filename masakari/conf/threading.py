# Copyright 2024 NTT DATA
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

"""Threading configuration options for Masakari.

This module defines configuration options for the native Python threading
used throughout the Masakari service architecture.
"""

from oslo_config import cfg

threading_opts = [
    cfg.IntOpt('executor_thread_pool_size',
               default=64,
               min=1,
               help="""
Size of the thread pool for general async operations.

This controls the number of threads available for general utility
operations such as utils.spawn() calls. These threads handle
miscellaneous background tasks and I/O operations.

The optimal size depends on your workload characteristics:
* I/O-heavy workloads: 2-4x number of CPU cores
* CPU-heavy workloads: 1-2x number of CPU cores
* Mixed workloads: 2-3x number of CPU cores

Related options:
* notification_thread_pool_size
* driver_thread_pool_size
"""),

    cfg.IntOpt('notification_thread_pool_size',
               default=32,
               min=1,
               help="""
Size of the thread pool for notification processing.

This controls the number of threads dedicated to processing failure
notifications using futurist's DynamicThreadPoolExecutor. These
threads handle the core business logic of notification validation,
status updates, and workflow coordination.

The size should be based on:
* Expected notification volume
* Average notification processing time
* Database connection pool size
* Coordination backend capacity

Typical recommendations:
* Small deployments (< 100 hosts): 8-16 threads
* Medium deployments (100-1000 hosts): 16-32 threads
* Large deployments (> 1000 hosts): 32-64 threads

Related options:
* executor_thread_pool_size
* driver_thread_pool_size
"""),

    cfg.IntOpt('driver_thread_pool_size',
               default=16,
               min=1,
               help="""
Size of the thread pool for driver operations.

This controls the number of threads dedicated to executing recovery
drivers (host failure, instance failure, process failure workflows).
These threads perform the actual recovery operations like evacuation,
reboot, and service restart.

Driver operations are typically long-running and resource-intensive,
so this pool should be sized conservatively:

* Each thread may run for several minutes
* Operations involve external API calls (Nova, etc.)
* Resource contention can occur with too many concurrent operations

Typical recommendations:
* Small deployments: 4-8 threads
* Medium deployments: 8-16 threads
* Large deployments: 16-32 threads

Consider your Nova API rate limits and compute node capacity when
sizing this pool.

Related options:
* executor_thread_pool_size
* notification_thread_pool_size
"""),
]


def register_opts(conf):
    """Register threading configuration options.

    Args:
        conf: Oslo configuration object to register options with
    """
    conf.register_opts(threading_opts)


def list_opts():
    """Return a list of oslo_config options for threading configuration.

    Returns:
        List of (group, options) tuples for oslo-config-generator
    """
    return [
        (None, threading_opts),
    ]
