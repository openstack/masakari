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

"""
Driver TaskFlowDriver:

    Execute notification workflows using taskflow.
"""
from collections import OrderedDict
import contextlib

from oslo_log import log as logging
from oslo_utils import excutils
from taskflow import exceptions
from taskflow.persistence import backends

from masakari.compute import nova
import masakari.conf
from masakari.engine import driver
from masakari.engine.drivers.taskflow import base
from masakari.engine.drivers.taskflow import host_failure
from masakari.engine.drivers.taskflow import instance_failure
from masakari.engine.drivers.taskflow import process_failure
from masakari import exception
from masakari.i18n import _
from masakari import objects
from masakari.objects import fields


CONF = masakari.conf.CONF
TASKFLOW_CONF = CONF.taskflow_driver_recovery_flows
PERSISTENCE_BACKEND = CONF.taskflow.connection
LOG = logging.getLogger(__name__)


class TaskFlowDriver(driver.NotificationDriver):
    def __init__(self):
        super(TaskFlowDriver, self).__init__()

    def _execute_auto_workflow(self, context, novaclient, process_what):
        flow_engine = host_failure.get_auto_flow(context, novaclient,
                                                 process_what)

        # Attaching this listener will capture all of the notifications
        # that taskflow sends out and redirect them to a more useful
        # log for masakari's debugging (or error reporting) usage.
        with base.DynamicLogListener(flow_engine, logger=LOG):
            flow_engine.run()

    def _execute_rh_workflow(self, context, novaclient, process_what,
                             **kwargs):
        if not kwargs['reserved_host_list']:
            msg = _('No reserved_hosts available for evacuation.')
            raise exception.ReservedHostsUnavailable(message=msg)

        process_what['reserved_host_list'] = kwargs.pop('reserved_host_list')
        flow_engine = host_failure.get_rh_flow(context, novaclient,
                                               process_what,
                                               **kwargs)

        with base.DynamicLogListener(flow_engine, logger=LOG):
            try:
                flow_engine.run()
            except exception.LockAlreadyAcquired as ex:
                raise exception.HostRecoveryFailureException(ex.message)

    def _execute_auto_priority_workflow(self, context, novaclient,
                                        process_what, **kwargs):
        try:
            self._execute_auto_workflow(context, novaclient, process_what)
        except Exception as ex:
            with excutils.save_and_reraise_exception(reraise=False) as ctxt:
                if isinstance(ex, exception.SkipHostRecoveryException):
                    ctxt.reraise = True
                    return

                # Caught generic Exception to make sure that any failure
                # should lead to execute 'reserved_host' recovery workflow.
                msg = ("Failed to evacuate all instances from "
                       "failed_host: '%(failed_host)s' using "
                       "'%(auto)s' workflow, retrying using "
                       "'%(reserved_host)s' workflow.")
                LOG.warning(msg, {
                    'failed_host': process_what['host_name'],
                    'auto': fields.FailoverSegmentRecoveryMethod.AUTO,
                    'reserved_host':
                        fields.FailoverSegmentRecoveryMethod.RESERVED_HOST
                })
                self._execute_rh_workflow(context,
                                          novaclient, process_what,
                                          **kwargs)

    def _execute_rh_priority_workflow(self, context, novaclient, process_what,
                                      **kwargs):
        try:
            self._execute_rh_workflow(context, novaclient, process_what,
                                      **kwargs)
        except Exception as ex:
            with excutils.save_and_reraise_exception(reraise=False) as ctxt:
                if isinstance(ex, exception.SkipHostRecoveryException):
                    ctxt.reraise = True
                    return

                # Caught generic Exception to make sure that any failure
                # should lead to execute 'auto' recovery workflow.
                msg = ("Failed to evacuate all instances from "
                       "failed_host '%(failed_host)s' using "
                       "'%(reserved_host)s' workflow, retrying using "
                       "'%(auto)s' workflow")
                LOG.warning(msg, {
                    'failed_host': process_what['host_name'],
                    'reserved_host':
                        fields.FailoverSegmentRecoveryMethod.RESERVED_HOST,
                    'auto': fields.FailoverSegmentRecoveryMethod.AUTO
                })
                self._execute_auto_workflow(context, novaclient, process_what)

    def execute_host_failure(self, context, host_name, recovery_method,
                             notification_uuid, **kwargs):
        novaclient = nova.API()
        # get flow for host failure
        process_what = {
            'host_name': host_name,
            'notification_uuid': notification_uuid
        }

        try:
            if recovery_method == fields.FailoverSegmentRecoveryMethod.AUTO:
                self._execute_auto_workflow(context, novaclient, process_what)
            elif recovery_method == (
                    fields.FailoverSegmentRecoveryMethod.RESERVED_HOST):
                self._execute_rh_workflow(context, novaclient, process_what,
                                          **kwargs)
            elif recovery_method == (
                    fields.FailoverSegmentRecoveryMethod.AUTO_PRIORITY):
                self._execute_auto_priority_workflow(
                    context, novaclient,
                    process_what, **kwargs)
            else:
                self._execute_rh_priority_workflow(context, novaclient,
                                                   process_what, **kwargs)
        except Exception as exc:
            with excutils.save_and_reraise_exception(reraise=False) as ctxt:
                if isinstance(exc, (exception.SkipHostRecoveryException,
                                    exception.HostRecoveryFailureException,
                                    exception.ReservedHostsUnavailable)):
                    ctxt.reraise = True
                    return
                msg = _("Failed to execute host failure flow for "
                        "notification '%s'.") % notification_uuid
                raise exception.MasakariException(msg)

    def execute_instance_failure(self, context, instance_uuid,
                                 notification_uuid):
        novaclient = nova.API()
        # get flow for instance failure
        process_what = {
            'instance_uuid': instance_uuid,
            'notification_uuid': notification_uuid
        }

        try:
            flow_engine = instance_failure.get_instance_recovery_flow(
                context, novaclient, process_what)
        except Exception:
            msg = _("Failed to create instance failure flow for "
                    "notification '%s'.") % notification_uuid
            LOG.exception(msg)
            raise exception.MasakariException(msg)

        # Attaching this listener will capture all of the notifications that
        # taskflow sends out and redirect them to a more useful log for
        # masakari's debugging (or error reporting) usage.
        with base.DynamicLogListener(flow_engine, logger=LOG):
            try:
                flow_engine.run()
            except Exception as exc:
                with excutils.save_and_reraise_exception(reraise=False) as e:
                    if isinstance(
                            exc, (exception.SkipInstanceRecoveryException,
                                  exception.IgnoreInstanceRecoveryException,
                                  exception.InstanceRecoveryFailureException)):
                        e.reraise = True
                        return
                    msg = _("Failed to execute instance failure flow for "
                            "notification '%s'.") % notification_uuid
                    raise exception.MasakariException(msg)

    def execute_process_failure(self, context, process_name, host_name,
                                notification_uuid):
        novaclient = nova.API()
        # get flow for process failure
        process_what = {
            'process_name': process_name,
            'host_name': host_name,
            'notification_uuid': notification_uuid
        }

        # TODO(abhishekk) We need to create a map for process_name and
        # respective python-client so that we can pass appropriate client
        # as a input to the process.
        if process_name == "nova-compute":
            recovery_flow = process_failure.get_compute_process_recovery_flow
        else:
            LOG.warning("Skipping recovery for process: %s.",
                        process_name)
            raise exception.SkipProcessRecoveryException()

        try:
            flow_engine = recovery_flow(context, novaclient, process_what)
        except Exception:
            msg = _("Failed to create process failure flow for "
                    "notification '%s'.") % notification_uuid
            LOG.exception(msg)
            raise exception.MasakariException(msg)

        # Attaching this listener will capture all of the notifications that
        # taskflow sends out and redirect them to a more useful log for
        # masakari's debugging (or error reporting) usage.
        with base.DynamicLogListener(flow_engine, logger=LOG):
            try:
                flow_engine.run()
            except Exception as exc:
                with excutils.save_and_reraise_exception(reraise=False) as e:
                    if isinstance(
                            exc, exception.ProcessRecoveryFailureException):
                        e.reraise = True
                        return
                    msg = _("Failed to execute instance failure flow for "
                            "notification '%s'.") % notification_uuid
                    raise exception.MasakariException(msg)

    @contextlib.contextmanager
    def upgrade_backend(self, persistence_backend):
        try:
            backend = backends.fetch(persistence_backend)
            with contextlib.closing(backend.get_connection()) as conn:
                conn.upgrade()
        except exceptions.NotFound as e:
            raise e

    def _get_taskflow_sequence(self, context, recovery_method, notification):
        # Get the taskflow sequence based on the recovery method.

        novaclient = nova.API()
        task_list = []

        # Get linear task flow based on notification type
        if notification.type == fields.NotificationType.VM:
            tasks = TASKFLOW_CONF.instance_failure_recovery_tasks
        elif notification.type == fields.NotificationType.PROCESS:
            tasks = TASKFLOW_CONF.process_failure_recovery_tasks
        elif notification.type == fields.NotificationType.COMPUTE_HOST:
            if recovery_method in [
                    fields.FailoverSegmentRecoveryMethod.AUTO,
                    fields.FailoverSegmentRecoveryMethod.AUTO_PRIORITY]:
                tasks = TASKFLOW_CONF.host_auto_failure_recovery_tasks
            elif recovery_method in [
                    fields.FailoverSegmentRecoveryMethod.RESERVED_HOST,
                    fields.FailoverSegmentRecoveryMethod.RH_PRIORITY]:
                tasks = TASKFLOW_CONF.host_rh_failure_recovery_tasks

        for plugin in base.get_recovery_flow(
                tasks['pre'], context=context, novaclient=novaclient,
                update_host_method=None):
            task_list.append(plugin.name)

        for plugin in base.get_recovery_flow(
                tasks['main'], context=context, novaclient=novaclient,
                update_host_method=None):
            task_list.append(plugin.name)

        for plugin in base.get_recovery_flow(
                tasks['post'], context=context, novaclient=novaclient,
                update_host_method=None):
            task_list.append(plugin.name)

        return task_list

    def get_notification_recovery_workflow_details(self, context,
                                                   recovery_method,
                                                   notification):
        """Retrieve progress details in notification"""

        backend = backends.fetch(PERSISTENCE_BACKEND)
        with contextlib.closing(backend.get_connection()) as conn:
            progress_details = []
            flow_details = conn.get_flows_for_book(
                notification.notification_uuid)
            for flow in flow_details:
                od = OrderedDict()
                atom_details = list(conn.get_atoms_for_flow(flow.uuid))

                # TODO(ShilpaSD): In case recovery_method is auto_priority/
                # rh_priority, there is no way to figure out whether the
                # recovery was done successfully using AUTO or RH flow.
                # Taskflow stores 'retry_instance_evacuate_engine_retry' task
                # in case of RH flow so if
                # 'retry_instance_evacuate_engine_retry' is stored in the
                # given flow details then the sorting of task details should
                # happen based on the RH flow.
                # This logic won't be required after LP #1815738 is fixed.
                if recovery_method in ['AUTO_PRIORITY', 'RH_PRIORITY']:
                    persisted_task_list = [atom.name for atom in
                                           atom_details]
                    if ('retry_instance_evacuate_engine_retry' in
                            persisted_task_list):
                        recovery_method = (
                            fields.FailoverSegmentRecoveryMethod.
                            RESERVED_HOST)
                    else:
                        recovery_method = (
                            fields.FailoverSegmentRecoveryMethod.AUTO)

                # TODO(ShilpaSD): Taskflow doesn't support to return task
                # details in the same sequence in which all tasks are
                # executed. Reported this issue in LP #1815738. To resolve
                # this issue load the tasks based on the recovery method and
                # later sort it based on this task list so progress_details
                # can be returned in the expected order.
                task_list = self._get_taskflow_sequence(context,
                                                        recovery_method,
                                                        notification)

                for task in task_list:
                    for atom in atom_details:
                        if task == atom.name:
                            od[atom.name] = atom

                for key, value in od.items():
                    # Add progress_details only if tasks are executed and meta
                    # is available in which progress_details are stored.
                    if value.meta and value.meta.get("progress_details"):
                        progress_details_obj = (
                            objects.NotificationProgressDetails.create(
                                value.name,
                                value.meta['progress'],
                                value.meta['progress_details']['details']
                                ['progress_details'],
                                value.state))

                        progress_details.append(progress_details_obj)

        return progress_details
