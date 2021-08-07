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

"""Masakari base exception handling.

Includes decorator for re-raising Masakari-type exceptions.

SHOULD include dedicated exception logging.

"""

import functools
from http import HTTPStatus
import inspect
import sys

from oslo_log import log as logging
from oslo_utils import excutils
import webob.exc
from webob import util as woutil

import masakari.conf
from masakari.i18n import _
from masakari import safe_utils
from masakari import utils

LOG = logging.getLogger(__name__)


CONF = masakari.conf.CONF


class ConvertedException(webob.exc.WSGIHTTPException):
    def __init__(self, code, title="", explanation=""):
        self.code = int(code)
        # There is a strict rule about constructing status line for HTTP:
        # '...Status-Line, consisting of the protocol version followed by a
        # numeric status code and its associated textual phrase, with each
        # element separated by SP characters'
        # (http://www.faqs.org/rfcs/rfc2616.html)
        # 'code' and 'title' can not be empty because they correspond
        # to numeric status code and its associated text
        if title:
            self.title = title
        else:
            try:
                self.title = woutil.status_reasons[self.code]
            except KeyError:
                msg = "Improper or unknown HTTP status code used: %d"
                LOG.error(msg, code)
                self.title = woutil.status_generic_reasons[self.code // 100]
        self.explanation = explanation
        super(ConvertedException, self).__init__()


def _cleanse_dict(original):
    """Strip all admin_password, new_pass, rescue_pass keys from a dict."""
    return {k: v for k, v in original.items() if "_pass" not in k}


def wrap_exception(notifier=None, get_notifier=None):
    """This decorator wraps a method to catch any exceptions that may
    get thrown. It also optionally sends the exception to the notification
    system.
    """
    def inner(f):
        def wrapped(self, context, *args, **kw):
            # Don't store self or context in the payload, it now seems to
            # contain confidential information.
            try:
                return f(self, context, *args, **kw)
            except Exception as e:
                with excutils.save_and_reraise_exception():
                    if notifier or get_notifier:
                        payload = dict(exception=e)
                        wrapped_func = safe_utils.get_wrapped_function(f)
                        call_dict = inspect.getcallargs(wrapped_func, self,
                                                        context, *args, **kw)
                        # self can't be serialized and shouldn't be in the
                        # payload
                        call_dict.pop('self', None)
                        cleansed = _cleanse_dict(call_dict)
                        payload.update({'args': cleansed})

                        # If f has multiple decorators, they must use
                        # functools.wraps to ensure the name is
                        # propagated.
                        event_type = f.__name__

                        (notifier or get_notifier()).error(context,
                                                           event_type,
                                                           payload)

        return functools.wraps(f)(wrapped)
    return inner


class MasakariException(Exception):
    """Base Masakari Exception

    To correctly use this class, inherit from it and define
    a 'msg_fmt' property. That msg_fmt will get printf'd
    with the keyword arguments provided to the constructor.

    """
    msg_fmt = _("An unknown exception occurred.")
    code = HTTPStatus.INTERNAL_SERVER_ERROR
    headers = {}
    safe = False

    def __init__(self, message=None, **kwargs):
        self.kwargs = kwargs

        if 'code' not in self.kwargs:
            try:
                self.kwargs['code'] = self.code
            except AttributeError:
                pass

        if not message:
            try:
                message = self.msg_fmt % kwargs

            except Exception:
                exc_info = sys.exc_info()
                # kwargs doesn't match a variable in the message
                # log the issue and the kwargs
                LOG.exception('Exception in string format operation')
                for name, value in kwargs.items():
                    LOG.error("%s: %s" % (name, value))    # noqa

                if CONF.fatal_exception_format_errors:
                    utils.reraise(*exc_info)
                else:
                    # at least get the core message out if something happened
                    message = self.msg_fmt

        self.message = message
        super(MasakariException, self).__init__(message)

    def format_message(self):
        # NOTE: use the first argument to the python Exception object
        # which should be our full MasakariException message, (see __init__)
        return self.args[0]


class APIException(MasakariException):
    msg_fmt = _("Error while requesting %(service)s API.")

    def __init__(self, message=None, **kwargs):
        if 'service' not in kwargs:
            kwargs['service'] = 'unknown'
        super(APIException, self).__init__(message, **kwargs)


class APITimeout(APIException):
    msg_fmt = _("Timeout while requesting %(service)s API.")


class Conflict(MasakariException):
    msg_fmt = _("Conflict")
    code = HTTPStatus.CONFLICT


class Invalid(MasakariException):
    msg_fmt = _("Bad Request - Invalid Parameters")
    code = HTTPStatus.BAD_REQUEST


class InvalidName(Invalid):
    msg_fmt = _("An invalid 'name' value was provided. "
                "The name must be: %(reason)s")


class InvalidInput(Invalid):
    msg_fmt = _("Invalid input received: %(reason)s")


class InvalidAPIVersionString(Invalid):
    msg_fmt = _("API Version String %(version)s is of invalid format. Must "
                "be of format MajorNum.MinorNum.")


class MalformedRequestBody(MasakariException):
    msg_fmt = _("Malformed message body: %(reason)s")


# NOTE: NotFound should only be used when a 404 error is
# appropriate to be returned
class NotFound(MasakariException):
    msg_fmt = _("Resource could not be found.")
    code = HTTPStatus.NOT_FOUND


class ConfigNotFound(NotFound):
    msg_fmt = _("Could not find config at %(path)s")


class Forbidden(MasakariException):
    msg_fmt = _("Forbidden")
    code = HTTPStatus.FORBIDDEN


class AdminRequired(Forbidden):
    msg_fmt = _("User does not have admin privileges")


class PolicyNotAuthorized(Forbidden):
    msg_fmt = _("Policy doesn't allow %(action)s to be performed.")


class PasteAppNotFound(MasakariException):
    msg_fmt = _("Could not load paste app '%(name)s' from %(path)s")


class InvalidContentType(Invalid):
    msg_fmt = _("Invalid content type %(content_type)s.")


class VersionNotFoundForAPIMethod(Invalid):
    msg_fmt = _("API version %(version)s is not supported on this method.")


class InvalidGlobalAPIVersion(Invalid):
    msg_fmt = _("Version %(req_ver)s is not supported by the API. Minimum "
                "is %(min_ver)s and maximum is %(max_ver)s.")


class ApiVersionsIntersect(Invalid):
    msg_fmt = _("Version of %(name) %(min_ver) %(max_ver) intersects "
                "with another versions.")


class ValidationError(Invalid):
    msg_fmt = "%(detail)s"


class InvalidSortKey(Invalid):
    msg_fmt = _("Sort key supplied was not valid.")


class MarkerNotFound(NotFound):
    msg_fmt = _("Marker %(marker)s could not be found.")


class FailoverSegmentNotFound(NotFound):
    msg_fmt = _("No failover segment with id %(id)s.")


class HostNotFound(NotFound):
    msg_fmt = _("No host with id %(id)s.")


class NotificationNotFound(NotFound):
    msg_fmt = _("No notification with id %(id)s.")


class FailoverSegmentNotFoundByName(FailoverSegmentNotFound):
    msg_fmt = _("Failover segment with name %(segment_name)s could not "
                "be found.")


class HostNotFoundByName(HostNotFound):
    msg_fmt = _("Host with name %(host_name)s could not be found.")


class ComputeNotFoundByName(NotFound):
    msg_fmt = _("Compute service with name %(compute_name)s could not "
                "be found.")


class FailoverSegmentExists(MasakariException):
    msg_fmt = _("Failover segment with name %(name)s already exists.")


class HostExists(MasakariException):
    msg_fmt = _("Host with name %(name)s already exists.")


class Unauthorized(MasakariException):
    msg_fmt = _("Not authorized.")
    code = HTTPStatus.UNAUTHORIZED


class ObjectActionError(MasakariException):
    msg_fmt = _('Object action %(action)s failed because: %(reason)s')


class OrphanedObjectError(MasakariException):
    msg_fmt = _('Cannot call %(method)s on orphaned %(objtype)s object')


class DuplicateNotification(Invalid):
    msg_fmt = _('Duplicate notification received for type: %(type)s')
    code = HTTPStatus.CONFLICT


class HostOnMaintenanceError(Invalid):
    msg_fmt = _('Host %(host_name)s is already under maintenance.')
    code = HTTPStatus.CONFLICT


class HostRecoveryFailureException(MasakariException):
    msg_fmt = _('Failed to execute host recovery.')


class InstanceRecoveryFailureException(MasakariException):
    msg_fmt = _('Failed to execute instance recovery workflow.')


class SkipInstanceRecoveryException(MasakariException):
    msg_fmt = _('Skipping execution of instance recovery workflow.')


class SkipProcessRecoveryException(MasakariException):
    msg_fmt = _('Skipping execution of process recovery workflow.')


class SkipHostRecoveryException(MasakariException):
    msg_fmt = _('Skipping execution of host recovery workflow.')


class ProcessRecoveryFailureException(MasakariException):
    msg_fmt = _('Failed to execute process recovery workflow.')


class DBNotAllowed(MasakariException):
    msg_fmt = _('%(binary)s attempted direct database access which is '
                'not allowed by policy')


class FailoverSegmentInUse(Conflict):
    msg_fmt = _("Failover segment %(uuid)s can't be updated as it is in-use "
                "to process notifications.")


class HostInUse(Conflict):
    msg_fmt = _("Host %(uuid)s can't be updated as it is in-use to process "
                "notifications.")


class ReservedHostsUnavailable(MasakariException):
    msg_fmt = _('No reserved_hosts available for evacuation.')


class LockAlreadyAcquired(MasakariException):
    msg_fmt = _('Lock is already acquired on %(resource)s.')


class IgnoreInstanceRecoveryException(MasakariException):
    msg_fmt = _('Instance recovery is ignored.')


class HostNotFoundUnderFailoverSegment(HostNotFound):
    msg_fmt = _("Host '%(host_uuid)s' under failover_segment "
                "'%(segment_uuid)s' could not be found.")


class InstanceEvacuateFailed(MasakariException):
    msg_fmt = _("Failed to evacuate instance %(instance_uuid)s")


class FailoverSegmentDisabled(MasakariException):
    msg_fmt = _('Failover segment is disabled.')
