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
from oslo_config import types


instance_recovery_group = cfg.OptGroup(
    'instance_failure',
    title='Instance failure recovery options',
    help="Configuration options for instance failure recovery")

host_recovery_group = cfg.OptGroup(
    'host_failure',
    title='Host failure recovery options',
    help="Configuration options for host failure recovery")

process_recovery_group = cfg.OptGroup(
    'process_failure',
    title='Process failure recovery options',
    help="Configuration options for process failure recovery")

customized_recovery_flow_group = cfg.OptGroup(
    'taskflow_driver_recovery_flows',
    title='Customized recovery flow Options',
    help="Configuration options for customizing various failure recovery"
         "workflow tasks.")

taskflow_group = cfg.OptGroup(
    'taskflow',
    title='Taskflow driver options',
    help="Configuration options for taskflow driver")


host_failure_opts = [
    cfg.BoolOpt('evacuate_all_instances',
                default=True,
                help="""
Operators can decide whether all instances or only those instances which have
``[host_failure]\\ha_enabled_instance_metadata_key`` set to ``True`` should be
allowed for evacuation from a failed source compute node.
When set to True, it will evacuate all instances from a failed source compute
node.
First preference will be given to those instances which have
``[host_failure]\\ha_enabled_instance_metadata_key`` set to ``True``,
and then it will evacuate the remaining ones.
When set to False, it will evacuate only those instances which have
``[host_failure]\\ha_enabled_instance_metadata_key`` set to ``True``.
    """),

    cfg.StrOpt('ha_enabled_instance_metadata_key',
               default='HA_Enabled',
               help="""
Operators can decide on the instance metadata key naming that affects the
per-instance behaviour of ``[host_failure]\\evacuate_all_instances``.
The default is the same for both failure types (host, instance) but the value
can be overridden to make the metadata key different per failure type.
    """),

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
    cfg.StrOpt("service_disable_reason",
               default="Masakari detected host failed.",
               help="Compute disable reason in case Masakari detects host "
                    "failure."),
]

instance_failure_options = [
    cfg.BoolOpt('process_all_instances',
                default=False,
                help="""
Operators can decide whether all instances or only those instances which
have ``[instance_failure]\\ha_enabled_instance_metadata_key`` set to ``True``
should be taken into account to recover from instance failure events.
When set to True, it will execute instance failure recovery actions for an
instance irrespective of whether that particular instance has
``[instance_failure]\\ha_enabled_instance_metadata_key`` set to ``True``.
When set to False, it will only execute instance failure recovery actions
for an instance which has
``[instance_failure]\\ha_enabled_instance_metadata_key`` set to ``True``.
    """),

    cfg.StrOpt('ha_enabled_instance_metadata_key',
               default='HA_Enabled',
               help="""
Operators can decide on the instance metadata key naming that affects the
per-instance behaviour of ``[instance_failure]\\process_all_instances``.
The default is the same for both failure types (host, instance) but the value
can be overridden to make the metadata key different per failure type.
    """),
]

taskflow_options = [
    cfg.StrOpt('connection',
               help="""
The SQLAlchemy connection string to use to connect to the taskflow database.
"""),
]

taskflow_driver_recovery_flows = [
    cfg.Opt('host_auto_failure_recovery_tasks',
            type=types.Dict(
                bounds=False,
                value_type=types.List(bounds=True,
                                      item_type=types.String(quotes=True))),
            default={'pre': ['disable_compute_service_task'],
                     'main': ['prepare_HA_enabled_instances_task'],
                     'post': ['evacuate_instances_task']},
            help=("""
This option allows operator to customize tasks to be executed for host failure
auto recovery workflow.

Provide list of strings reflecting to the task classes that should be included
to the host failure recovery workflow. The full classname path of all task
classes should be defined in the 'masakari.task_flow.tasks' of setup.cfg and
these classes may be implemented by OpenStack Masaskari project team, deployer
or third party.

By default below three tasks will be part of this config option:-
1. disable_compute_service_task
2. prepare_HA_enabled_instances_task
3. evacuate_instances_task

The allowed values for this option is comma separated dictionary of object
names in between ``{`` and ``}``.""")),

    cfg.Opt('host_rh_failure_recovery_tasks',
            type=types.Dict(
                bounds=False,
                value_type=types.List(bounds=True,
                                      item_type=types.String(quotes=True))),
            default={'pre': ['disable_compute_service_task'],
                     'main': ['prepare_HA_enabled_instances_task',
                              'evacuate_instances_task'],
                     'post': []},
            help=("""
This option allows operator to customize tasks to be executed for host failure
reserved_host recovery workflow.

Provide list of strings reflecting to the task classes that should be included
to the host failure recovery workflow. The full classname path of all task
classes should be defined in the 'masakari.task_flow.tasks' of setup.cfg and
these classes may be implemented by OpenStack Masaskari project team, deployer
or third party.

By default below three tasks will be part of this config option:-
1. disable_compute_service_task
2. prepare_HA_enabled_instances_task
3. evacuate_instances_task

The allowed values for this option is comma separated dictionary of object
names in between ``{`` and ``}``.""")),

    cfg.Opt('instance_failure_recovery_tasks',
            type=types.Dict(
                bounds=False,
                value_type=types.List(bounds=True,
                                      item_type=types.String(quotes=True))),
            default={'pre': ['stop_instance_task'],
                     'main': ['start_instance_task'],
                     'post': ['confirm_instance_active_task']},
            help=("""
This option allows operator to customize tasks to be executed for instance
failure recovery workflow.

Provide list of strings reflecting to the task classes that should be included
to the instance failure recovery workflow. The full classname path of all task
classes should be defined in the 'masakari.task_flow.tasks' of setup.cfg and
these classes may be implemented by OpenStack Masaskari project team, deployer
or third party.

By default below three tasks will be part of this config option:-
1. stop_instance_task
2. start_instance_task
3. confirm_instance_active_task

The allowed values for this option is comma separated dictionary of object
names in between ``{`` and ``}``.""")),

    cfg.Opt('process_failure_recovery_tasks',
            type=types.Dict(
                bounds=False,
                value_type=types.List(bounds=True,
                                      item_type=types.String(quotes=True))),
            default={'pre': ['disable_compute_node_task'],
                     'main': ['confirm_compute_node_disabled_task'],
                     'post': []},
            help=("""
This option allows operator to customize tasks to be executed for process
failure recovery workflow.

Provide list of strings reflecting to the task classes that should be included
to the process failure recovery workflow. The full classname path of all task
classes should be defined in the 'masakari.task_flow.tasks' of setup.cfg and
these classes may be implemented by OpenStack Masaskari project team, deployer
or third party.

By default below two tasks will be part of this config option:-
1. disable_compute_node_task
2. confirm_compute_node_disabled_task

The allowed values for this option is comma separated dictionary of object
names in between ``{`` and ``}``."""))
]

process_failure_opts = [
    cfg.StrOpt("service_disable_reason",
               default="Masakari detected process failed.",
               help="Compute disable reason in case Masakari detects process "
                    "failure."),
]


def register_opts(conf):
    conf.register_group(instance_recovery_group)
    conf.register_group(host_recovery_group)
    conf.register_group(process_recovery_group)
    conf.register_group(customized_recovery_flow_group)
    conf.register_group(taskflow_group)
    conf.register_opts(instance_failure_options, group=instance_recovery_group)
    conf.register_opts(host_failure_opts, group=host_recovery_group)
    conf.register_opts(process_failure_opts, group=process_recovery_group)
    conf.register_opts(taskflow_driver_recovery_flows,
                       group=customized_recovery_flow_group)
    conf.register_opts(taskflow_options, group=taskflow_group)


def list_opts():
    return {
        instance_recovery_group.name: instance_failure_options,
        host_recovery_group.name: host_failure_opts,
        process_recovery_group.name: process_failure_opts,
        taskflow_group.name: taskflow_options
    }


def customized_recovery_flow_list_opts():
    return {
        customized_recovery_flow_group.name: taskflow_driver_recovery_flows
    }
