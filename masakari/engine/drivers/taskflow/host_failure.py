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
from eventlet import timeout as etimeout

from oslo_log import log as logging
from oslo_service import loopingcall
from oslo_utils import strutils
import taskflow.engines
from taskflow.patterns import linear_flow
from taskflow import retry

import masakari.conf
from masakari.engine.drivers.taskflow import base
from masakari import exception
from masakari.i18n import _, _LI
from masakari import utils


CONF = masakari.conf.CONF

LOG = logging.getLogger(__name__)

ACTION = 'instance:evacuate'


class DisableComputeServiceTask(base.MasakariTask):
    def __init__(self, novaclient):
        requires = ["host_name"]
        super(DisableComputeServiceTask, self).__init__(addons=[ACTION],
                                                        requires=requires)
        self.novaclient = novaclient

    def execute(self, context, host_name):
        self.novaclient.enable_disable_service(context, host_name)

        # Sleep until nova-compute service is marked as disabled.
        msg = _LI("Sleeping %(wait)s sec before starting recovery "
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
        instance_list = self.novaclient.get_servers(context, host_name)

        if CONF.host_failure.evacuate_all_instances:
            instance_list = sorted(
                instance_list, key=lambda k: strutils.bool_from_string(
                    k.metadata.get('HA_Enabled', False)), reverse=True)
        else:
            instance_list = (
                [instance for instance in instance_list if
                 strutils.bool_from_string(instance.metadata.get('HA_Enabled',
                                                                 False))])
        if not instance_list:
            msg = _('No instances to evacuate on host: %s.') % host_name
            LOG.info(msg)
            raise exception.SkipHostRecoveryException(message=msg)

        return {
            "instance_list": instance_list,
        }


class EvacuateInstancesTask(base.MasakariTask):
    default_provides = set(["instance_list"])

    def __init__(self, novaclient):
        requires = ["host_name", "instance_list"]
        super(EvacuateInstancesTask, self).__init__(addons=[ACTION],
                                                    requires=requires)
        self.novaclient = novaclient

    def execute(self, context, host_name, instance_list, reserved_host=None):
        def _do_evacuate(context, host_name, instance_list,
                         reserved_host=None):
            if reserved_host:
                if CONF.host_failure.add_reserved_host_to_aggregate:
                    # Assign reserved_host to an aggregate to which the failed
                    # compute host belongs to.
                    aggregates = self.novaclient.get_aggregate_list(context)
                    for aggregate in aggregates:
                        if host_name in aggregate.hosts:
                            self.novaclient.add_host_to_aggregate(
                                context, reserved_host.name, aggregate)
                            # A failed compute host can be associated with
                            # multiple aggregates but operators will not
                            # associate it with multiple aggregates in real
                            # deployment so adding reserved_host to the very
                            # first aggregate from the list.
                            break

                self.novaclient.enable_disable_service(
                    context, reserved_host.name, enable=True)

                # Sleep until nova-compute service is marked as enabled.
                msg = _LI("Sleeping %(wait)s sec before starting recovery "
                          "thread until nova recognizes the node up.")
                LOG.info(msg, {
                    'wait': CONF.wait_period_after_service_update})
                eventlet.sleep(CONF.wait_period_after_service_update)

                # Set reserved property of reserved_host to False
                reserved_host.reserved = False
                reserved_host.save()

            for instance in instance_list:
                vm_state = getattr(instance, "OS-EXT-STS:vm_state")
                if vm_state in ['active', 'error', 'resized', 'stopped']:
                    # Evacuate API only evacuates an instance in
                    # active, stop or error state. If an instance is in
                    # resized status, masakari resets the instance
                    # state to *error* to evacuate it.
                    if vm_state == 'resized':
                        self.novaclient.reset_instance_state(
                            context, instance.id)

                    # evacuate the instance
                    self.novaclient.evacuate_instance(
                        context, instance.id,
                        target=reserved_host.name if reserved_host else None)

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

        return {
            "instance_list": instance_list,
        }


class ConfirmEvacuationTask(base.MasakariTask):
    def __init__(self, novaclient):
        requires = ["instance_list", "host_name"]
        super(ConfirmEvacuationTask, self).__init__(addons=[ACTION],
                                                    requires=requires)
        self.novaclient = novaclient

    def execute(self, context, instance_list, host_name):
        failed_evacuation_instances = []
        for instance in instance_list:
            def _wait_for_evacuation():
                new_instance = self.novaclient.get_server(context, instance.id)
                instance_host = getattr(new_instance,
                                        "OS-EXT-SRV-ATTR:hypervisor_hostname")
                old_vm_state = getattr(instance, "OS-EXT-STS:vm_state")
                new_vm_state = getattr(new_instance,
                                       "OS-EXT-STS:vm_state")

                if instance_host != host_name:
                    if ((old_vm_state == 'error' and
                        new_vm_state == 'active') or
                            old_vm_state == new_vm_state):
                        raise loopingcall.LoopingCallDone()

            periodic_call = loopingcall.FixedIntervalLoopingCall(
                _wait_for_evacuation)
            try:
                # add a timeout to the periodic call.
                periodic_call.start(interval=CONF.verify_interval)
                etimeout.with_timeout(CONF.wait_period_after_evacuation,
                                      periodic_call.wait)
            except etimeout.Timeout:
                # Instance is not evacuated in the expected time_limit.
                failed_evacuation_instances.append(instance.id)
            finally:
                # stop the periodic call, in case of exceptions or Timeout.
                periodic_call.stop()

        if failed_evacuation_instances:
            msg = _("Failed to evacuate instances %(instances)s from "
                    "host %(host_name)s.") % {
                'instances': failed_evacuation_instances,
                'host_name': host_name
            }
            raise exception.HostRecoveryFailureException(message=msg)


def get_auto_flow(novaclient, process_what):
    """Constructs and returns the engine entrypoint flow.

    This flow will do the following:

    1. Disable compute service on source host
    2. Get all HA_Enabled instances.
    3. Evacuate all the HA_Enabled instances.
    4. Confirm evacuation of instances.
    """

    flow_name = ACTION.replace(":", "_") + "_engine"
    auto_evacuate_flow = linear_flow.Flow(flow_name)

    auto_evacuate_flow.add(DisableComputeServiceTask(novaclient),
                           PrepareHAEnabledInstancesTask(novaclient),
                           EvacuateInstancesTask(novaclient),
                           ConfirmEvacuationTask(novaclient))

    return taskflow.engines.load(auto_evacuate_flow, store=process_what)


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

    rh_flow = linear_flow.Flow(
        "retry_%s" % flow_name, retry=retry.ParameterizedForEach(
            rebind=['reserved_host_list'], provides='reserved_host'))

    rh_flow.add(PrepareHAEnabledInstancesTask(novaclient),
                EvacuateInstancesTask(novaclient),
                ConfirmEvacuationTask(novaclient))

    nested_flow.add(DisableComputeServiceTask(novaclient), rh_flow)

    return taskflow.engines.load(nested_flow, store=process_what)
