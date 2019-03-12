# Copyright 2016 NTT DATA
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

import contextlib
import os

from oslo_log import log as logging
from oslo_utils import timeutils
from stevedore import named
# For more information please visit: https://wiki.openstack.org/wiki/TaskFlow
import taskflow.engines
from taskflow import exceptions
from taskflow import formatters
from taskflow.listeners import base
from taskflow.listeners import logging as logging_listener
from taskflow.persistence import backends
from taskflow.persistence import models
from taskflow import task

import masakari.conf
from masakari import exception

CONF = masakari.conf.CONF
PERSISTENCE_BACKEND = CONF.taskflow.connection
LOG = logging.getLogger(__name__)


class MasakariTask(task.Task):
    """The root task class for all masakari tasks.

    It automatically names the given task using the module and class that
    implement the given task as the task name.
    """

    def __init__(self, context, novaclient, **kwargs):
        requires = kwargs.get('requires')
        rebind = kwargs.get('rebind')
        provides = kwargs.get('provides')
        super(MasakariTask, self).__init__(self.__class__.__name__,
                                           requires=requires,
                                           rebind=rebind,
                                           provides=provides)
        self.context = context
        self.novaclient = novaclient
        self.progress = []

    def update_details(self, progress_data, progress=0.0):
        progress_details = {
            'timestamp': str(timeutils.utcnow()),
            'progress': progress,
            'message': progress_data
        }

        self.progress.append(progress_details)
        self._notifier.notify('update_progress', {'progress': progress,
                                                  "progress_details":
                                                      self.progress})


class SpecialFormatter(formatters.FailureFormatter):

    # Exception is an excepted case, don't include traceback in log if fails.
    _NO_TRACE_EXCEPTIONS = (exception.SkipInstanceRecoveryException,
                            exception.SkipHostRecoveryException)

    def __init__(self, engine):
        super(SpecialFormatter, self).__init__(engine)

    def format(self, fail, atom_matcher):
        if fail.check(*self._NO_TRACE_EXCEPTIONS) is not None:
            exc_info = None
            exc_details = '%s%s' % (os.linesep, fail.pformat(traceback=False))
            return (exc_info, exc_details)
        else:
            return super(SpecialFormatter, self).format(fail, atom_matcher)


class DynamicLogListener(logging_listener.DynamicLoggingListener):
    """This is used to attach to taskflow engines while they are running.

    It provides a bunch of useful features that expose the actions happening
    inside a taskflow engine, which can be useful for developers for debugging,
    for operations folks for monitoring and tracking of the resource actions
    and more...
    """

    def __init__(self, engine,
                 task_listen_for=base.DEFAULT_LISTEN_FOR,
                 flow_listen_for=base.DEFAULT_LISTEN_FOR,
                 retry_listen_for=base.DEFAULT_LISTEN_FOR,
                 logger=LOG):
        super(DynamicLogListener, self).__init__(
            engine,
            task_listen_for=task_listen_for,
            flow_listen_for=flow_listen_for,
            retry_listen_for=retry_listen_for,
            log=logger, fail_formatter=SpecialFormatter(engine))


def get_recovery_flow(task_list, **kwargs):
    """This is used create extension object from provided task_list.

    This method returns the extension object of the each task provided
    in a list using stevedore extension manager.
    """
    extensions = named.NamedExtensionManager(
        'masakari.task_flow.tasks', names=task_list,
        name_order=True, invoke_on_load=True, invoke_kwds=kwargs)
    for extension in extensions.extensions:
        yield extension.obj


def load_taskflow_into_engine(action, nested_flow,
                              process_what):
    book = None
    backend = None
    if PERSISTENCE_BACKEND:
        backend = backends.fetch(PERSISTENCE_BACKEND)
        with contextlib.closing(backend.get_connection()) as conn:
            try:
                book = conn.get_logbook(process_what['notification_uuid'])
            except exceptions.NotFound:
                pass
            if book is None:
                book = models.LogBook(action,
                                      process_what['notification_uuid'])

    return taskflow.engines.load(nested_flow, store=process_what,
                                 backend=backend, book=book)
