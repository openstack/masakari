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


instance_recovery_group = cfg.OptGroup(
    'instance_failure',
    title='Instance failure recovery options',
    help="Configuration options for instance failure recovery")

host_recovery_group = cfg.OptGroup(
    'host_failure',
    title='Host failure recovery options',
    help="Configuration options for host failure recovery")


host_failure_opts = [
    cfg.BoolOpt('evacuate_all_instances',
                default=True,
                help="""
Operators can decide whether all instances or only those instances which
contain metadata key 'HA_Enabled=True' should be allowed for evacuation from
a failed source compute node. When set to True, it will evacuate all instances
from a failed source compute node. First preference will be given to those
instances which contain 'HA_Enabled=True' metadata key, and then it will
evacuate the remaining ones. When set to False, it will evacuate only those
instances which contain 'HA_Enabled=True' metadata key."""),

    cfg.BoolOpt('ignore_instances_in_error_state',
                default=False,
                help="""
Operators can decide whether error instances should be allowed for evacuation
from a failed source compute node or not. When set to True, it will ignore
error instances from evacuation from a failed source compute node. When set to
False, it will evacuate error instances along with other instances from a
failed source compute node."""),

    cfg.BoolOpt("add_reserved_host_to_aggregate",
                default=False,
                help="""
Operators can decide whether reserved_host should be added to aggregate group
of failed compute host. When set to True, reserved host will be added to the
aggregate group of failed compute host. When set to False, the reserved_host
will not be added to the aggregate group of failed compute host."""),
]

instance_failure_options = [
    cfg.BoolOpt('process_all_instances',
                default=False,
                help="""
Operators can decide whether all instances or only those instances which
contain metadata key 'HA_Enabled=True' should be taken into account to
recover from instance failure events. When set to True, it will execute
instance failure recovery actions for an instance irrespective of whether
that particular instance contains metadata key 'HA_Enabled=True' or not.
When set to False, it will only execute instance failure recovery actions
for an instance which contain metadata key 'HA_Enabled=True'."""),
]


def register_opts(conf):
    conf.register_group(instance_recovery_group)
    conf.register_group(host_recovery_group)
    conf.register_opts(instance_failure_options, group=instance_recovery_group)
    conf.register_opts(host_failure_opts, group=host_recovery_group)


def list_opts():
    return {
        instance_recovery_group.name: instance_failure_options,
        host_recovery_group.name: host_failure_opts
    }
