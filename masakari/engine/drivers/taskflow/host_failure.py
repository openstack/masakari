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

import eventlet
from eventlet import greenpool
from eventlet import timeout as etimeout

from oslo_config import cfg
from oslo_log import log as logging
from oslo_service import loopingcall
from oslo_utils import excutils
from oslo_utils import strutils
import taskflow.engines
from taskflow.patterns import linear_flow
from taskflow import retry

import masakari.conf
from masakari.engine.drivers.taskflow import base
from masakari import exception
from masakari.i18n import _
from masakari import utils


CONF = masakari.conf.CONF

LOG = logging.getLogger(__name__)

ACTION = 'instance:evacuate'

# Instance power_state
SHUTDOWN = 4

TASKFLOW_CONF = cfg.CONF.taskflow_driver_recovery_flows


class DisableComputeServiceTask(base.MasakariTask):
    def __init__(self, novaclient):
        requires = ["host_name"]
        super(DisableComputeServiceTask, self).__init__(addons=[ACTION],
                                                        requires=requires)
        self.novaclient = novaclient

    def execute(self, context, host_name):
        self.novaclient.enable_disable_service(context, host_name)

        # Sleep until nova-compute service is marked as disabled.
        msg = ("Sleeping %(wait)s sec before starting recovery "
               "thread until nova recognizes the node down.")
        LOG.info(msg, {'wait': CONF.wait_period_after_service_update})
        eventlet.sleep(CONF.wait_period_after_service_update)


class PrepareHAEnabledInstancesTask(base.MasakariTask):
    """Get all HA_Enabled instances."""
    default_provides = set(["instance_list"])

    def __init__(self, novaclient):
        requires = ["host_name"]
        super(PrepareHAEnabledInstancesTask, self).__init__(addons=[ACTION],
                                                            requires=requires)
        self.novaclient = novaclient

    def execute(self, context, host_name):
        def _filter_instances(instance_list):
            ha_enabled_instances = []
            non_ha_enabled_instances = []

            for instance in instance_list:
                is_instance_ha_enabled = strutils.bool_from_string(
                    instance.metadata.get('HA_Enabled', False))
                if CONF.host_failure.ignore_instances_in_error_state and (
                        getattr(instance, "OS-EXT-STS:vm_state") == "error"):
                    if is_instance_ha_enabled:
                        msg = ("Ignoring recovery of HA_Enabled instance "
                               "'%(instance_id)s' as it is in 'error' state.")
                        LOG.info(msg, {'instance_id': instance.id})
                    continue

                if is_instance_ha_enabled:
                    ha_enabled_instances.append(instance)
                else:
                    non_ha_enabled_instances.append(instance)

            if CONF.host_failure.evacuate_all_instances:
                ha_enabled_instances.extend(non_ha_enabled_instances)

            return ha_enabled_instances

        instance_list = self.novaclient.get_servers(context, host_name)

        instance_list = _filter_instances(instance_list)

        if not instance_list:
            msg = _('No instances to evacuate on host: %s.') % host_name
            LOG.info(msg)
            raise exception.SkipHostRecoveryException(message=msg)

        return {
            "instance_list": instance_list,
        }


class EvacuateInstancesTask(base.MasakariTask):

    def __init__(self, novaclient):
        requires = ["host_name", "instance_list"]
        super(EvacuateInstancesTask, self).__init__(addons=[ACTION],
                                                    requires=requires)
        self.novaclient = novaclient

    def _get_state_and_host_of_instance(self, context, instance):
        new_instance = self.novaclient.get_server(context, instance.id)
        instance_host = getattr(new_instance,
                                "OS-EXT-SRV-ATTR:hypervisor_hostname")
        old_vm_state = getattr(instance, "OS-EXT-STS:vm_state")
        new_vm_state = getattr(new_instance, "OS-EXT-STS:vm_state")

        return (old_vm_state, new_vm_state, instance_host)

    def _stop_after_evacuation(self, context, instance):
        def _wait_for_stop_confirmation():
            old_vm_state, new_vm_state, _ = (
                self._get_state_and_host_of_instance(context, instance))

            if new_vm_state == 'stopped':
                raise loopingcall.LoopingCallDone()

        periodic_call_stopped = loopingcall.FixedIntervalLoopingCall(
            _wait_for_stop_confirmation)

        try:
            self.novaclient.stop_server(context, instance.id)
            # confirm instance is stopped after recovery
            periodic_call_stopped.start(interval=CONF.verify_interval)
            etimeout.with_timeout(
                CONF.wait_period_after_power_off,
                periodic_call_stopped.wait)
        except etimeout.Timeout:
            with excutils.save_and_reraise_exception():
                msg = ("Instance '%s' is successfully evacuated but "
                       "failed to stop.")
                LOG.warning(msg, instance.id)
        finally:
            periodic_call_stopped.stop()

    def _evacuate_and_confirm(self, context, instance, host_name,
                              failed_evacuation_instances, reserved_host=None):
        # Before locking the instance check whether it is already locked
        # by user, if yes don't lock the instance
        instance_already_locked = self.novaclient.get_server(
            context, instance.id).locked

        if not instance_already_locked:
            # lock the instance so that until evacuation and confirmation
            # is not complete, user won't be able to perform any actions
            # on the instance.
            self.novaclient.lock_server(context, instance.id)

        def _wait_for_evacuation_confirmation():
            old_vm_state, new_vm_state, instance_host = (
                self._get_state_and_host_of_instance(context, instance))

            if instance_host != host_name:
                if ((old_vm_state == 'error' and
                    new_vm_state == 'active') or
                        old_vm_state == new_vm_state):
                    raise loopingcall.LoopingCallDone()

        try:
            vm_state = getattr(instance, "OS-EXT-STS:vm_state")
            task_state = getattr(instance, "OS-EXT-STS:task_state")

            # Nova evacuates an instance only when vm_state is in active,
            # stopped or error state. If an instance is in other than active,
            # error and stopped vm_state, masakari resets the instance state
            # to *error* so that the instance can be evacuated.
            stop_instance = True
            if vm_state not in ['active', 'error', 'stopped']:
                self.novaclient.reset_instance_state(context, instance.id)
                instance = self.novaclient.get_server(context, instance.id)
                power_state = getattr(instance, "OS-EXT-STS:power_state")
                if vm_state == 'resized' and power_state != SHUTDOWN:
                    stop_instance = False

                vm_state = getattr(instance, "OS-EXT-STS:vm_state")

            elif task_state is not None:
                # Nova fails evacuation when the instance's task_state is not
                # none. In this case, masakari resets the instance's vm_state
                # to 'error' and task_state to none.
                self.novaclient.reset_instance_state(context, instance.id)
                instance = self.novaclient.get_server(context, instance.id)
                if vm_state == 'active':
                    stop_instance = False

            # evacuate the instance
            self.novaclient.evacuate_instance(
                context, instance.id,
                target=reserved_host.name if reserved_host else None)

            periodic_call = loopingcall.FixedIntervalLoopingCall(
                _wait_for_evacuation_confirmation)

            try:
                # add a timeout to the periodic call.
                periodic_call.start(interval=CONF.verify_interval)
                etimeout.with_timeout(
                    CONF.wait_period_after_evacuation,
                    periodic_call.wait)

                if vm_state != 'active':
                    if stop_instance:
                        self._stop_after_evacuation(context, instance)
                        # If the instance was in 'error' state before failure
                        # it should be set to 'error' after recovery.
                        if vm_state == 'error':
                            self.novaclient.reset_instance_state(
                                context, instance.id)
            except etimeout.Timeout:
                # Instance is not evacuated in the expected time_limit.
                failed_evacuation_instances.append(instance.id)
            finally:
                # stop the periodic call, in case of exceptions or
                # Timeout.
                periodic_call.stop()
        except Exception:
            # Exception is raised while resetting instance state or
            # evacuating the instance itself.
            failed_evacuation_instances.append(instance.id)
        finally:
            if not instance_already_locked:
                # Unlock the server after evacuation and confirmation
                self.novaclient.unlock_server(context, instance.id)

    def execute(self, context, host_name, instance_list, reserved_host=None):
        def _do_evacuate(context, host_name, instance_list,
                         reserved_host=None):
            failed_evacuation_instances = []
            if reserved_host:
                if CONF.host_failure.add_reserved_host_to_aggregate:
                    # Assign reserved_host to an aggregate to which the failed
                    # compute host belongs to.
                    aggregates = self.novaclient.get_aggregate_list(context)
                    for aggregate in aggregates:
                        if host_name in aggregate.hosts:
                            try:
                                self.novaclient.add_host_to_aggregate(
                                    context, reserved_host.name, aggregate)
                            except exception.Conflict:
                                msg = ("Host '%(reserved_host)s' already has "
                                       "been added to aggregate "
                                       "'%(aggregate)s'.")
                                LOG.info(msg,
                                         {'reserved_host': reserved_host.name,
                                          'aggregate': aggregate.name})

                            # A failed compute host can be associated with
                            # multiple aggregates but operators will not
                            # associate it with multiple aggregates in real
                            # deployment so adding reserved_host to the very
                            # first aggregate from the list.
                            break

                self.novaclient.enable_disable_service(
                    context, reserved_host.name, enable=True)

                # Set reserved property of reserved_host to False
                reserved_host.reserved = False
                reserved_host.save()

            thread_pool = greenpool.GreenPool(
                CONF.host_failure_recovery_threads)
            for instance in instance_list:
                thread_pool.spawn_n(self._evacuate_and_confirm, context,
                                    instance, host_name,
                                    failed_evacuation_instances, reserved_host)
            thread_pool.waitall()

            if failed_evacuation_instances:
                msg = _("Failed to evacuate instances %(instances)s from "
                        "host %(host_name)s.") % {
                    'instances': failed_evacuation_instances,
                    'host_name': host_name
                }
                raise exception.HostRecoveryFailureException(message=msg)

        lock_name = reserved_host.name if reserved_host else None

        @utils.synchronized(lock_name)
        def do_evacuate_with_reserved_host(context, host_name, instance_list,
                                           reserved_host):
            _do_evacuate(context, host_name, instance_list,
                         reserved_host=reserved_host)

        if lock_name:
            do_evacuate_with_reserved_host(context, host_name, instance_list,
                                           reserved_host)
        else:
            # No need to acquire lock on reserved_host when recovery_method is
            # 'auto' as the selection of compute host will be decided by nova.
            _do_evacuate(context, host_name, instance_list)


def get_auto_flow(novaclient, process_what):
    """Constructs and returns the engine entrypoint flow.

    This flow will do the following:

    1. Disable compute service on source host
    2. Get all HA_Enabled instances.
    3. Evacuate all the HA_Enabled instances.
    4. Confirm evacuation of instances.
    """

    flow_name = ACTION.replace(":", "_") + "_engine"
    nested_flow = linear_flow.Flow(flow_name)

    task_dict = TASKFLOW_CONF.host_auto_failure_recovery_tasks

    auto_evacuate_flow_pre = linear_flow.Flow('pre_tasks')
    for plugin in base.get_recovery_flow(task_dict['pre'],
                                         novaclient=novaclient):
        auto_evacuate_flow_pre.add(plugin)

    auto_evacuate_flow_main = linear_flow.Flow('main_tasks')
    for plugin in base.get_recovery_flow(task_dict['main'],
                                         novaclient=novaclient):
        auto_evacuate_flow_main.add(plugin)

    auto_evacuate_flow_post = linear_flow.Flow('post_tasks')
    for plugin in base.get_recovery_flow(task_dict['post'],
                                         novaclient=novaclient):
        auto_evacuate_flow_post.add(plugin)

    nested_flow.add(auto_evacuate_flow_pre)
    nested_flow.add(auto_evacuate_flow_main)
    nested_flow.add(auto_evacuate_flow_post)

    return taskflow.engines.load(nested_flow, store=process_what)


def get_rh_flow(novaclient, process_what):
    """Constructs and returns the engine entrypoint flow.

    This flow will do the following:

    1. Disable compute service on source host
    2. Get all HA_Enabled instances.
    3. Evacuate all the HA_Enabled instances using reserved_host.
    4. Confirm evacuation of instances.
    """
    flow_name = ACTION.replace(":", "_") + "_engine"
    nested_flow = linear_flow.Flow(flow_name)

    task_dict = TASKFLOW_CONF.host_rh_failure_recovery_tasks

    rh_evacuate_flow_pre = linear_flow.Flow('pre_tasks')
    for plugin in base.get_recovery_flow(task_dict['pre'],
                                         novaclient=novaclient):
        rh_evacuate_flow_pre.add(plugin)

    rh_evacuate_flow_main = linear_flow.Flow(
        "retry_%s" % flow_name, retry=retry.ParameterizedForEach(
            rebind=['reserved_host_list'], provides='reserved_host'))

    for plugin in base.get_recovery_flow(task_dict['main'],
                                         novaclient=novaclient):
        rh_evacuate_flow_main.add(plugin)

    rh_evacuate_flow_post = linear_flow.Flow('post_tasks')
    for plugin in base.get_recovery_flow(task_dict['post'],
                                         novaclient=novaclient):
        rh_evacuate_flow_post.add(plugin)

    nested_flow.add(rh_evacuate_flow_pre)
    nested_flow.add(rh_evacuate_flow_main)
    nested_flow.add(rh_evacuate_flow_post)

    return taskflow.engines.load(nested_flow, store=process_what)
