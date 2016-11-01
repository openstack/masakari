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

from oslo_log import log as logging

from masakari.compute import nova
from masakari.engine import driver
from masakari.engine.drivers.taskflow import base
from masakari.engine.drivers.taskflow import host_failure
from masakari.engine.drivers.taskflow import instance_failure
from masakari.engine.drivers.taskflow import process_failure
from masakari import exception
from masakari.i18n import _, _LW
from masakari.objects import fields


LOG = logging.getLogger(__name__)


class TaskFlowDriver(driver.NotificationDriver):
    def __init__(self):
        super(TaskFlowDriver, self).__init__()

    def execute_host_failure(self, context, host_name, recovery_method,
                             notification_uuid):
        novaclient = nova.API()
        # get flow for host failure
        process_what = {
            'context': context,
            'host_name': host_name
        }

        try:
            if recovery_method == fields.FailoverSegmentRecoveryMethod.AUTO:
                flow_engine = host_failure.get_auto_flow(novaclient,
                                                         process_what)
            elif recovery_method == (
                    fields.FailoverSegmentRecoveryMethod.RESERVED_HOST):
                raise NotImplementedError(_("Flow not implemented for "
                                            "recovery_method"),
                                          recovery_method)
            elif recovery_method == (
                    fields.FailoverSegmentRecoveryMethod.AUTO_PRIORITY):
                raise NotImplementedError(_("Flow not implemented for "
                                            "recovery_method"),
                                          recovery_method)
            elif recovery_method == (
                    fields.FailoverSegmentRecoveryMethod.RH_PRIORITY):
                raise NotImplementedError(_("Flow not implemented for "
                                            "recovery_method"),
                                          recovery_method)
        except Exception:
            msg = (_('Failed to create host failure flow.'),
                   notification_uuid)
            LOG.exception(msg)
            raise exception.MasakariException(msg)

        # Attaching this listener will capture all of the notifications that
        # taskflow sends out and redirect them to a more useful log for
        # masakari's debugging (or error reporting) usage.
        with base.DynamicLogListener(flow_engine, logger=LOG):
            flow_engine.run()

    def execute_instance_failure(self, context, instance_uuid,
                                 notification_uuid):
        novaclient = nova.API()
        # get flow for instance failure
        process_what = {
            'context': context,
            'instance_uuid': instance_uuid
        }

        try:
            flow_engine = instance_failure.get_instance_recovery_flow(
                novaclient, process_what)
        except Exception:
            msg = (_('Failed to create instance failure flow.'),
                   notification_uuid)
            LOG.exception(msg)
            raise exception.MasakariException(msg)

        # Attaching this listener will capture all of the notifications that
        # taskflow sends out and redirect them to a more useful log for
        # masakari's debugging (or error reporting) usage.
        with base.DynamicLogListener(flow_engine, logger=LOG):
            flow_engine.run()

    def execute_process_failure(self, context, process_name, host_name,
                                notification_uuid):
        novaclient = nova.API()
        # get flow for process failure
        process_what = {
            'context': context,
            'process_name': process_name,
            'host_name': host_name
        }

        # TODO(abhishekk) We need to create a map for process_name and
        # respective python-client so that we can pass appropriate client
        # as a input to the process.
        if process_name == "nova-compute":
            recovery_flow = process_failure.get_compute_process_recovery_flow
        else:
            LOG.warning(_LW("Skipping recovery for process: %s."),
                        process_name)
            raise exception.SkipProcessRecoveryException()

        try:
            flow_engine = recovery_flow(novaclient, process_what)
        except Exception:
            msg = (_('Failed to create process failure flow.'),
                   notification_uuid)
            LOG.exception(msg)
            raise exception.MasakariException(msg)

        # Attaching this listener will capture all of the notifications that
        # taskflow sends out and redirect them to a more useful log for
        # masakari's debugging (or error reporting) usage.
        with base.DynamicLogListener(flow_engine, logger=LOG):
            flow_engine.run()
