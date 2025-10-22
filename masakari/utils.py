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

"""Utilities and helper functions."""

from concurrent import futures
import contextlib
import functools
import inspect
import pyclbr
import shutil
import sys
import tempfile
import threading

from futurist import ThreadPoolExecutor as DynamicThreadPoolExecutor
from oslo_concurrency import lockutils
from oslo_context import context as common_context
from oslo_log import log as logging
from oslo_utils import importutils
from oslo_utils import strutils
from oslo_utils import timeutils

import masakari.conf
from masakari import exception
from masakari.i18n import _
from masakari import safe_utils


CONF = masakari.conf.CONF

LOG = logging.getLogger(__name__)

# Global thread pool executors for different types of operations
_general_executor = None
_notification_executor = None
_driver_executor = None
_executor_lock = threading.Lock()


def _get_general_executor():
    """Get or create the general-purpose thread pool executor."""
    global _general_executor
    if _general_executor is None:
        with _executor_lock:
            if _general_executor is None:
                _general_executor = futures.ThreadPoolExecutor(
                    max_workers=64, thread_name_prefix='masakari-general-')
    return _general_executor


def _get_notification_executor():
    """Get or create the notification thread pool executor."""
    global _notification_executor
    if _notification_executor is None:
        with _executor_lock:
            if _notification_executor is None:
                _notification_executor = DynamicThreadPoolExecutor(
                    max_workers=32,
                    thread_name_prefix='masakari-notification-')
    return _notification_executor


def _get_driver_executor():
    """Get or create the driver thread pool executor."""
    global _driver_executor
    if _driver_executor is None:
        with _executor_lock:
            if _driver_executor is None:
                _driver_executor = DynamicThreadPoolExecutor(
                    max_workers=16, thread_name_prefix='masakari-driver-')
    return _driver_executor


def _context_wrapper(func, *args, **kwargs):
    """Wrapper to preserve OpenStack context across threads."""
    current_context = common_context.get_current()

    @functools.wraps(func)
    def wrapped():
        if current_context is not None:
            current_context.update_store()
        try:
            return func(*args, **kwargs)
        except Exception as e:
            LOG.exception("Exception in spawned thread: %s", e)
            raise

    return wrapped


def reraise(tp, value, tb=None):
    try:
        if value is None:
            value = tp()
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value
    finally:
        value = None
        tb = None


def utf8(value):
    """Try to turn a string into utf-8 if possible.

    The original code was copied from the utf8 function in
    http://github.com/facebook/tornado/blob/master/tornado/escape.py

    """
    if value is None or isinstance(value, bytes):
        return value

    if not isinstance(value, str):
        value = str(value)

    return value.encode('utf-8')


def check_isinstance(obj, cls):
    """Checks that obj is of type cls, and lets PyLint infer types."""
    if isinstance(obj, cls):
        return obj
    raise Exception(_('Expected object of type: %s') % (str(cls)))


def monkey_patch():
    """If the CONF.monkey_patch set as True,
    this function patches a decorator
    for all functions in specified modules.
    You can set decorators for each modules
    using CONF.monkey_patch_modules.
    The format is "Module path:Decorator function".

    name - name of the function
    function - object of the function
    """
    # If CONF.monkey_patch is not True, this function do nothing.
    if not CONF.monkey_patch:
        return

    def is_method(obj):
        # Unbound methods became regular functions on Python 3
        return inspect.ismethod(obj) or inspect.isfunction(obj)

    # Get list of modules and decorators
    for module_and_decorator in CONF.monkey_patch_modules:
        module, decorator_name = module_and_decorator.split(':')
        # import decorator function
        decorator = importutils.import_class(decorator_name)
        __import__(module)
        # Retrieve module information using pyclbr
        module_data = pyclbr.readmodule_ex(module)
        for key, value in module_data.items():
            # set the decorator for the class methods
            if isinstance(value, pyclbr.Class):
                clz = importutils.import_class("%s.%s" % (module, key))
                for method, func in inspect.getmembers(clz, is_method):
                    setattr(clz, method,
                            decorator("%s.%s.%s" % (module, key,
                                                    method), func))
            # set the decorator for the function
            if isinstance(value, pyclbr.Function):
                func = importutils.import_class("%s.%s" % (module, key))
                setattr(sys.modules[module], key,
                        decorator("%s.%s" % (module, key), func))


def walk_class_hierarchy(clazz, encountered=None):
    """Walk class hierarchy, yielding most derived classes first."""
    if not encountered:
        encountered = []
    for subclass in clazz.__subclasses__():
        if subclass not in encountered:
            encountered.append(subclass)
            # drill down to leaves first
            for subsubclass in walk_class_hierarchy(subclass, encountered):
                yield subsubclass
            yield subclass


def expects_func_args(*args):
    def _decorator_checker(dec):
        @functools.wraps(dec)
        def _decorator(f):
            base_f = safe_utils.get_wrapped_function(f)
            arg_names, a, kw, _, _, _, _ = inspect.getfullargspec(base_f)
            if a or kw or set(args) <= set(arg_names):
                # NOTE : We can't really tell if correct stuff will
                # be passed if it's a function with *args or **kwargs so
                # we still carry on and hope for the best
                return dec(f)
            else:
                raise TypeError("Decorated function %(f_name)s does not "
                                "have the arguments expected by the "
                                "decorator %(d_name)s" %
                                {'f_name': base_f.__name__,
                                 'd_name': dec.__name__})
        return _decorator
    return _decorator_checker


def isotime(at=None):
    """Current time as ISO string,
    as timeutils.isotime() is deprecated

    :returns: Current time in ISO format
    """
    if not at:
        at = timeutils.utcnow()
    date_string = at.strftime("%Y-%m-%dT%H:%M:%S")
    tz = at.tzinfo.tzname(None) if at.tzinfo else 'UTC'
    date_string += ('Z' if tz in ['UTC', 'UTC+00:00'] else tz)
    return date_string


def strtime(at):
    return at.strftime("%Y-%m-%dT%H:%M:%S.%f")


class ExceptionHelper(object):
    """Class to wrap another and translate the ClientExceptions raised by its
    function calls to the actual ones.
    """

    def __init__(self, target):
        self._target = target

    def __getattr__(self, name):
        func = getattr(self._target, name)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                reraise(*e.exc_info)
        return wrapper


def spawn(func, *args, **kwargs):
    """Spawn a function in a thread with context preservation.

    This utility exists so that it can be stubbed for testing without
    interfering with the service spawns.

    It will also grab the context from the threadlocal store and add it to
    the store on the new thread.  This allows for continuity in logging the
    context when using this method to spawn a new thread.

    Note: Now using standard ThreadPoolExecutor for threading.
    """
    executor = _get_general_executor()
    wrapped_func = _context_wrapper(func, *args, **kwargs)
    return executor.submit(wrapped_func)


def spawn_n(func, *args, **kwargs):
    """Spawn a function in a thread without waiting for result.

    This utility exists so that it can be stubbed for testing without
    interfering with the service spawns.

    It will also grab the context from the threadlocal store and add it to
    the store on the new thread.  This allows for continuity in logging the
    context when using this method to spawn a new thread.

    Note: Now using standard ThreadPoolExecutor for threading.
    """
    executor = _get_general_executor()
    wrapped_func = _context_wrapper(func, *args, **kwargs)
    executor.submit(wrapped_func)  # Fire and forget, don't return future


def spawn_notification(func, *args, **kwargs):
    """Spawn a notification processing function with dedicated thread pool.

    This utility provides optimized execution for notification processing
    using futurist's DynamicThreadPoolExecutor with dedicated resources.

    Args:
        func: The notification processing function to execute
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function

    Returns:
        Future: A Future object representing the execution
    """
    executor = _get_notification_executor()
    wrapped_func = _context_wrapper(func, *args, **kwargs)
    return executor.submit(wrapped_func)


def spawn_driver(func, *args, **kwargs):
    """Spawn a driver execution function with dedicated thread pool.

    This utility provides optimized execution for driver operations
    using futurist's DynamicThreadPoolExecutor with dedicated resources.

    Args:
        func: The driver function to execute
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function

    Returns:
        Future: A Future object representing the execution
    """
    executor = _get_driver_executor()
    wrapped_func = _context_wrapper(func, *args, **kwargs)
    return executor.submit(wrapped_func)


@contextlib.contextmanager
def tempdir(**kwargs):
    argdict = kwargs.copy()
    if 'dir' not in argdict:
        argdict['dir'] = CONF.tempdir
    tmpdir = tempfile.mkdtemp(**argdict)
    try:
        yield tmpdir
    finally:
        try:
            shutil.rmtree(tmpdir)
        except OSError as e:
            LOG.error('Could not remove tmpdir: %s', e)


def validate_integer(value, name, min_value=None, max_value=None):
    """Make sure that value is a valid integer, potentially within range."""
    try:
        return strutils.validate_integer(value, name, min_value, max_value)
    except ValueError as e:
        raise exception.InvalidInput(reason=e)


def synchronized(name, semaphores=None, blocking=False):
    def wrap(f):
        @functools.wraps(f)
        def inner(*args, **kwargs):
            lock_name = 'masakari-%s' % name
            int_lock = lockutils.internal_lock(lock_name,
                                               semaphores=semaphores)
            LOG.debug("Acquiring lock: %(lock_name)s on resource: "
                      "%(resource)s", {'lock_name': lock_name,
                                       'resource': f.__name__})

            if not int_lock.acquire(blocking=blocking):
                raise exception.LockAlreadyAcquired(resource=name)
            try:
                return f(*args, **kwargs)
            finally:
                LOG.debug("Releasing lock: %(lock_name)s on resource: "
                          "%(resource)s", {'lock_name': lock_name,
                                           'resource': f.__name__})
                int_lock.release()
        return inner
    return wrap
