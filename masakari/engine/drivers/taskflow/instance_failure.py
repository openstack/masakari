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

from eventlet import timeout as etimeout

from oslo_config import cfg
from oslo_log import log as logging
from oslo_service import loopingcall
from oslo_utils import strutils
import taskflow.engines
from taskflow.patterns import linear_flow

import masakari.conf
from masakari.engine.drivers.taskflow import base
from masakari import exception
from masakari.i18n import _


CONF = masakari.conf.CONF

LOG = logging.getLogger(__name__)

ACTION = "instance:recovery"

TASKFLOW_CONF = cfg.CONF.taskflow_driver_recovery_flows


class StopInstanceTask(base.MasakariTask):
    def __init__(self, novaclient):
        requires = ["instance_uuid"]
        super(StopInstanceTask, self).__init__(addons=[ACTION],
                                               requires=requires)
        self.novaclient = novaclient

    def execute(self, context, instance_uuid):
        """Stop the instance for recovery."""
        instance = self.novaclient.get_server(context, instance_uuid)

        # If an instance is not HA_Enabled and "process_all_instances" config
        # option is also disabled, then there is no need to take any recovery
        # action.
        if not CONF.instance_failure.process_all_instances and not (
                strutils.bool_from_string(
                    instance.metadata.get('HA_Enabled', False))):
            LOG.info("Skipping recovery for instance: %s as it is "
                     "not Ha_Enabled.", instance_uuid)
            raise exception.SkipInstanceRecoveryException()

        vm_state = getattr(instance, 'OS-EXT-STS:vm_state')
        if vm_state in ['paused', 'rescued']:
            msg = _("Recovery of instance '%(instance_uuid)s' is ignored as"
                    " it is in '%(vm_state)s' state.") % {
                'instance_uuid': instance_uuid, 'vm_state': vm_state}
            LOG.warning(msg)
            raise exception.IgnoreInstanceRecoveryException(msg)

        if vm_state != 'stopped':
            if vm_state == 'resized':
                self.novaclient.reset_instance_state(
                    context, instance.id, 'active')

            self.novaclient.stop_server(context, instance.id)

        def _wait_for_power_off():
            new_instance = self.novaclient.get_server(context, instance_uuid)
            vm_state = getattr(new_instance, 'OS-EXT-STS:vm_state')
            if vm_state == 'stopped':
                raise loopingcall.LoopingCallDone()

        periodic_call = loopingcall.FixedIntervalLoopingCall(
            _wait_for_power_off)

        try:
            # add a timeout to the periodic call.
            periodic_call.start(interval=CONF.verify_interval)
            etimeout.with_timeout(CONF.wait_period_after_power_off,
                                  periodic_call.wait)
        except etimeout.Timeout:
            msg = _("Failed to stop instance %(instance)s") % {
                'instance': instance.id
            }
            raise exception.InstanceRecoveryFailureException(message=msg)
        finally:
            # stop the periodic call, in case of exceptions or Timeout.
            periodic_call.stop()


class StartInstanceTask(base.MasakariTask):
    def __init__(self, novaclient):
        requires = ["instance_uuid"]
        super(StartInstanceTask, self).__init__(addons=[ACTION],
                                                requires=requires)
        self.novaclient = novaclient

    def execute(self, context, instance_uuid):
        """Start the instance."""
        instance = self.novaclient.get_server(context, instance_uuid)
        vm_state = getattr(instance, 'OS-EXT-STS:vm_state')
        if vm_state == 'stopped':
            self.novaclient.start_server(context, instance.id)
        else:
            msg = _("Invalid state for Instance %(instance)s. Expected state: "
                    "'STOPPED', Actual state: '%(actual_state)s'") % {
                'instance': instance_uuid,
                'actual_state': vm_state
            }
            raise exception.InstanceRecoveryFailureException(message=msg)


class ConfirmInstanceActiveTask(base.MasakariTask):
    def __init__(self, novaclient):
        requires = ["instance_uuid"]
        super(ConfirmInstanceActiveTask, self).__init__(addons=[ACTION],
                                                        requires=requires)
        self.novaclient = novaclient

    def execute(self, context, instance_uuid):
        def _wait_for_active():
            new_instance = self.novaclient.get_server(context, instance_uuid)
            vm_state = getattr(new_instance, 'OS-EXT-STS:vm_state')
            if vm_state == 'active':
                raise loopingcall.LoopingCallDone()

        periodic_call = loopingcall.FixedIntervalLoopingCall(
            _wait_for_active)
        try:
            # add a timeout to the periodic call.
            periodic_call.start(interval=CONF.verify_interval)
            etimeout.with_timeout(CONF.wait_period_after_power_on,
                                  periodic_call.wait)
        except etimeout.Timeout:
            msg = _("Failed to start instance %(instance)s") % {
                'instance': instance_uuid
            }
            raise exception.InstanceRecoveryFailureException(message=msg)
        finally:
            # stop the periodic call, in case of exceptions or Timeout.
            periodic_call.stop()


def get_instance_recovery_flow(novaclient, process_what):
    """Constructs and returns the engine entrypoint flow.

    This flow will do the following:

    1. Stop the instance
    2. Start the instance.
    3. Confirm instance is in active state.
    """

    flow_name = ACTION.replace(":", "_") + "_engine"
    nested_flow = linear_flow.Flow(flow_name)

    task_dict = TASKFLOW_CONF.instance_failure_recovery_tasks

    instance_recovery_workflow_pre = linear_flow.Flow('pre_tasks')
    for plugin in base.get_recovery_flow(task_dict['pre'],
                                         novaclient=novaclient):
        instance_recovery_workflow_pre.add(plugin)

    instance_recovery_workflow_main = linear_flow.Flow('main_tasks')
    for plugin in base.get_recovery_flow(task_dict['main'],
                                         novaclient=novaclient):
        instance_recovery_workflow_main.add(plugin)

    instance_recovery_workflow_post = linear_flow.Flow('post_tasks')
    for plugin in base.get_recovery_flow(task_dict['post'],
                                         novaclient=novaclient):
        instance_recovery_workflow_post.add(plugin)

    nested_flow.add(instance_recovery_workflow_pre)
    nested_flow.add(instance_recovery_workflow_main)
    nested_flow.add(instance_recovery_workflow_post)

    return taskflow.engines.load(nested_flow, store=process_what)
