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

import functools
from http import HTTPStatus
import inspect

import microversion_parse
from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import strutils
import webob

from masakari.api import api_version_request as api_version
from masakari.api import versioned_method
from masakari.api import wsgi
from masakari import exception
from masakari import i18n
from masakari.i18n import _


LOG = logging.getLogger(__name__)

_SUPPORTED_CONTENT_TYPES = (
    'application/json',
    'application/vnd.openstack.masakari+json',
)

_MEDIA_TYPE_MAP = {
    'application/vnd.openstack.masakari+json': 'json',
    'application/json': 'json',
}

# These are typically automatically created by routes as either defaults
# collection or member methods.
_ROUTES_METHODS = [
    'create',
    'delete',
    'show',
    'update',
]

_METHODS_WITH_BODY = [
    'POST',
    'PUT',
]

# name of attribute to keep version method information
VER_METHOD_ATTR = 'versioned_methods'

# Names of headers used by clients to request a specific version
# of the REST API
API_VERSION_REQUEST_HEADER = 'OpenStack-API-Version'


def get_supported_content_types():
    return _SUPPORTED_CONTENT_TYPES


def get_media_map():
    return dict(_MEDIA_TYPE_MAP.items())


# NOTE: This function allows a get on both a dict-like and an
# object-like object. cache_db_items() is used on both versioned objects and
# dicts, so the function can't be totally changed over to [] syntax, nor
# can it be changed over to use getattr().
def item_get(item, item_key):
    if hasattr(item, '__getitem__'):
        return item[item_key]
    else:
        return getattr(item, item_key)


class Request(wsgi.Request):
    """Add some OpenStack API-specific logic to the base webob.Request."""

    def __init__(self, *args, **kwargs):
        super(Request, self).__init__(*args, **kwargs)
        self._extension_data = {'db_items': {}}
        if not hasattr(self, 'api_version_request'):
            self.api_version_request = api_version.APIVersionRequest()

    def cache_db_items(self, key, items, item_key='id'):
        """Allow API methods to store objects from a DB query to be
        used by API extensions within the same API request.

        An instance of this class only lives for the lifetime of a
        single API request, so there's no need to implement full
        cache management.
        """
        db_items = self._extension_data['db_items'].setdefault(key, {})
        for item in items:
            db_items[item_get(item, item_key)] = item

    def get_db_items(self, key):
        """Allow an API extension to get previously stored objects within
        the same API request.

        Note that the object data will be slightly stale.
        """
        return self._extension_data['db_items'][key]

    def get_db_item(self, key, item_key):
        """Allow an API extension to get a previously stored object
        within the same API request.

        Note that the object data will be slightly stale.
        """
        return self.get_db_items(key).get(item_key)

    def best_match_content_type(self):
        """Determine the requested response content-type."""
        if 'masakari.best_content_type' not in self.environ:
            # Calculate the best MIME type
            content_type = None

            # Check URL path suffix
            parts = self.path.rsplit('.', 1)
            if len(parts) > 1:
                possible_type = 'application/' + parts[1]
                if possible_type in get_supported_content_types():
                    content_type = possible_type

            if not content_type:
                content_type = self.accept.best_match(
                    get_supported_content_types())

            self.environ['masakari.best_content_type'] = (content_type or
                                                          'application/json')

        return self.environ['masakari.best_content_type']

    def get_content_type(self):
        """Determine content type of the request body.

        Does not do any body introspection, only checks header

        """
        if "Content-Type" not in self.headers:
            return None

        content_type = self.content_type

        # NOTE: text/plain is the default for eventlet and
        # other webservers which use mimetools.Message.gettype()
        # whereas twisted defaults to ''.
        if not content_type or content_type == 'text/plain':
            return None

        if content_type not in get_supported_content_types():
            raise exception.InvalidContentType(content_type=content_type)

        return content_type

    def best_match_language(self):
        """Determine the best available language for the request.

        :returns: the best language match or None if the 'Accept-Language'
                  header was not available in the request.
        """
        if not self.accept_language:
            return None
        return self.accept_language.best_match(i18n.get_available_languages())

    def set_api_version_request(self):
        """Set API version request based on the request header information."""
        hdr_string = microversion_parse.get_version(
            self.headers, service_type='instance-ha')

        if hdr_string is None:
            self.api_version_request = api_version.APIVersionRequest(
                api_version.DEFAULT_API_VERSION)
        elif hdr_string == 'latest':
            # 'latest' is a special keyword which is equivalent to
            # requesting the maximum version of the API supported
            self.api_version_request = api_version.max_api_version()
        else:
            self.api_version_request = api_version.APIVersionRequest(
                hdr_string)

            # Check that the version requested is within the global
            # minimum/maximum of supported API versions
            if not self.api_version_request.matches(
                    api_version.min_api_version(),
                    api_version.max_api_version()):
                raise exception.InvalidGlobalAPIVersion(
                    req_ver=self.api_version_request.get_string(),
                    min_ver=api_version.min_api_version().get_string(),
                    max_ver=api_version.max_api_version().get_string())


class ActionDispatcher(object):
    """Maps method name to local methods through action name."""

    def dispatch(self, *args, **kwargs):
        """Find and call local method."""
        action = kwargs.pop('action', 'default')
        action_method = getattr(self, str(action), self.default)
        return action_method(*args, **kwargs)

    def default(self, data):
        raise NotImplementedError()


class JSONDeserializer(ActionDispatcher):

    def _from_json(self, datastring):
        try:
            return jsonutils.loads(datastring)
        except ValueError:
            msg = _("cannot understand JSON")
            raise exception.MalformedRequestBody(reason=msg)

    def deserialize(self, datastring, action='default'):
        return self.dispatch(datastring, action=action)

    def default(self, datastring):
        return {'body': self._from_json(datastring)}


class JSONDictSerializer(ActionDispatcher):
    """Default JSON request body serialization."""

    def serialize(self, data, action='default'):
        return self.dispatch(data, action=action)

    def default(self, data):
        return str(jsonutils.dumps(data))


def response(code):
    """Attaches response code to a method.

    This decorator associates a response code with a method.  Note
    that the function attributes are directly manipulated; the method
    is not wrapped.
    """

    def decorator(func):
        func.wsgi_code = code
        return func
    return decorator


class ResponseObject(object):
    """Bundles a response object

    Object that app methods may return in order to allow its response
    to be modified by extensions in the code. Its use is optional (and
    should only be used if you really know what you are doing).
    """

    def __init__(self, obj, code=None, headers=None):
        """Builds a response object."""

        self.obj = obj
        self._default_code = HTTPStatus.OK
        self._code = code
        self._headers = headers or {}
        self.serializer = JSONDictSerializer()

    def __getitem__(self, key):
        """Retrieves a header with the given name."""

        return self._headers[key.lower()]

    def __setitem__(self, key, value):
        """Sets a header with the given name to the given value."""

        self._headers[key.lower()] = value

    def __delitem__(self, key):
        """Deletes the header with the given name."""

        del self._headers[key.lower()]

    def serialize(self, request, content_type):
        """Serializes the wrapped object.

        Utility method for serializing the wrapped object.  Returns a
        webob.Response object.
        """

        serializer = self.serializer

        body = None
        if self.obj is not None:
            body = serializer.serialize(self.obj)
        response = webob.Response(body=body)
        if response.headers.get('Content-Length'):
            response.headers['Content-Length'] = (str(
                response.headers['Content-Length']))
        response.status_int = self.code
        for hdr, value in self._headers.items():
            response.headers[hdr] = str(value)
        response.headers['Content-Type'] = str(content_type)
        return response

    @property
    def code(self):
        """Retrieve the response status."""

        return self._code or self._default_code

    @property
    def headers(self):
        """Retrieve the headers."""

        return self._headers.copy()


def action_peek(body):
    """Determine action to invoke.

    This looks inside the json body and fetches out the action method
    name.
    """

    try:
        decoded = jsonutils.loads(body)
    except ValueError:
        msg = _("cannot understand JSON")
        raise exception.MalformedRequestBody(reason=msg)

    # Make sure there's exactly one key...
    if len(decoded) != 1:
        msg = _("too many body keys")
        raise exception.MalformedRequestBody(reason=msg)

    # Return the action name
    return list(decoded.keys())[0]


class ResourceExceptionHandler(object):
    """Context manager to handle Resource exceptions.

    Used when processing exceptions generated by API implementation
    methods (or their extensions).  Converts most exceptions to Fault
    exceptions, with the appropriate logging.
    """

    def __enter__(self):
        return None

    def __exit__(self, ex_type, ex_value, ex_traceback):
        if not ex_value:
            return True

        if isinstance(ex_value, exception.Forbidden):
            raise Fault(webob.exc.HTTPForbidden(
                        explanation=ex_value.format_message()))
        elif isinstance(ex_value, exception.VersionNotFoundForAPIMethod):
            raise
        elif isinstance(ex_value, exception.Invalid):
            raise Fault(exception.ConvertedException(
                        code=ex_value.code,
                        explanation=ex_value.format_message()))
        elif isinstance(ex_value, TypeError):
            exc_info = (ex_type, ex_value, ex_traceback)
            LOG.error('Exception handling resource: %s', ex_value,
                      exc_info=exc_info)
            raise Fault(webob.exc.HTTPBadRequest())
        elif isinstance(ex_value, Fault):
            LOG.info("Fault thrown: %s", ex_value)
            raise ex_value
        elif isinstance(ex_value, webob.exc.HTTPException):
            LOG.info("HTTP exception thrown: %s", ex_value)
            raise Fault(ex_value)

        # We didn't handle the exception
        return False


class Resource(wsgi.Application):
    """WSGI app that handles (de)serialization and controller dispatch.

    WSGI app that reads routing information supplied by RoutesMiddleware
    and calls the requested action method upon its controller.  All
    controller action methods must accept a 'req' argument, which is the
    incoming wsgi.Request. If the operation is a PUT or POST, the controller
    method must also accept a 'body' argument (the deserialized request body).
    They may raise a webob.exc exception or return a dict, which will be
    serialized by requested content type.

    Exceptions derived from webob.exc.HTTPException will be automatically
    wrapped in Fault() to provide API friendly error responses.

    """
    support_api_request_version = False

    def __init__(self, controller, inherits=None):
        """:param controller: object that implement methods created by routes
                              lib
           :param inherits: another resource object that this resource should
                            inherit extensions from. Any action extensions that
                            are applied to the parent resource will also apply
                            to this resource.
        """

        self.controller = controller

        self.default_serializers = dict(json=JSONDictSerializer)

        # Copy over the actions dictionary
        self.wsgi_actions = {}
        if controller:
            self.register_actions(controller)

        # Save a mapping of extensions
        self.wsgi_extensions = {}
        self.wsgi_action_extensions = {}
        self.inherits = inherits

    def register_actions(self, controller):
        """Registers controller actions with this resource."""

        actions = getattr(controller, 'wsgi_actions', {})
        for key, method_name in actions.items():
            self.wsgi_actions[key] = getattr(controller, method_name)

    def register_extensions(self, controller):
        """Registers controller extensions with this resource."""

        extensions = getattr(controller, 'wsgi_extensions', [])
        for method_name, action_name in extensions:
            # Look up the extending method
            extension = getattr(controller, method_name)

            if action_name:
                # Extending an action...
                if action_name not in self.wsgi_action_extensions:
                    self.wsgi_action_extensions[action_name] = []
                self.wsgi_action_extensions[action_name].append(extension)
            else:
                # Extending a regular method
                if method_name not in self.wsgi_extensions:
                    self.wsgi_extensions[method_name] = []
                self.wsgi_extensions[method_name].append(extension)

    def get_action_args(self, request_environment):
        """Parse dictionary created by routes library."""

        # NOTE: Check for get_action_args() override in the
        # controller
        if hasattr(self.controller, 'get_action_args'):
            return self.controller.get_action_args(request_environment)

        try:
            args = request_environment['wsgiorg.routing_args'][1].copy()
        except (KeyError, IndexError, AttributeError):
            return {}

        try:
            del args['controller']
        except KeyError:
            pass

        try:
            del args['format']
        except KeyError:
            pass

        return args

    def get_body(self, request):
        content_type = request.get_content_type()

        return content_type, request.body

    def deserialize(self, body):
        return JSONDeserializer().deserialize(body)

    def pre_process_extensions(self, extensions, request, action_args):
        # List of callables for post-processing extensions
        post = []

        for ext in extensions:
            if inspect.isgeneratorfunction(ext):
                response = None

                # If it's a generator function, the part before the
                # yield is the preprocessing stage
                try:
                    with ResourceExceptionHandler():
                        gen = ext(req=request, **action_args)
                        response = next(gen)
                except Fault as ex:
                    response = ex

                # We had a response...
                if response:
                    return response, []

                # No response, queue up generator for post-processing
                post.append(gen)
            else:
                # Regular functions only perform post-processing
                post.append(ext)

        # None is response, it means we keep going. We reverse the
        # extension list for post-processing.
        return None, reversed(post)

    def post_process_extensions(self, extensions, resp_obj, request,
                                action_args):
        for ext in extensions:
            response = None
            if inspect.isgenerator(ext):
                # If it's a generator, run the second half of
                # processing
                try:
                    with ResourceExceptionHandler():
                        response = ext.send(resp_obj)
                except StopIteration:
                    # Normal exit of generator
                    continue
                except Fault as ex:
                    response = ex
            else:
                # Regular functions get post-processing...
                try:
                    with ResourceExceptionHandler():
                        response = ext(req=request, resp_obj=resp_obj,
                                       **action_args)
                except exception.VersionNotFoundForAPIMethod:
                    # If an attached extension (@wsgi.extends) for the
                    # method has no version match its not an error. We
                    # just don't run the extends code
                    continue
                except Fault as ex:
                    response = ex

            # We had a response...
            if response:
                return response

        return None

    def _should_have_body(self, request):
        return request.method in _METHODS_WITH_BODY

    @webob.dec.wsgify(RequestClass=Request)
    def __call__(self, request):
        """WSGI method that controls (de)serialization and method dispatch."""

        if self.support_api_request_version:
            # Set the version of the API requested based on the header
            try:
                request.set_api_version_request()
            except exception.InvalidAPIVersionString as e:
                return Fault(webob.exc.HTTPBadRequest(
                    explanation=e.format_message()))
            except exception.InvalidGlobalAPIVersion as e:
                return Fault(webob.exc.HTTPNotAcceptable(
                    explanation=e.format_message()))

        # Identify the action, its arguments, and the requested
        # content type
        action_args = self.get_action_args(request.environ)
        action = action_args.pop('action', None)

        # NOTE: we filter out InvalidContentTypes early so we
        # know everything is good from here on out.
        try:
            content_type, body = self.get_body(request)
            accept = request.best_match_content_type()
        except exception.InvalidContentType:
            msg = _("Unsupported Content-Type")
            return Fault(webob.exc.HTTPUnsupportedMediaType(explanation=msg))

        # NOTE: Splitting the function up this way allows for
        #       auditing by external tools that wrap the existing
        #       function.  If we try to audit __call__(), we can
        #       run into troubles due to the @webob.dec.wsgify()
        #       decorator.
        return self._process_stack(request, action, action_args,
                                   content_type, body, accept)

    def _process_stack(self, request, action, action_args,
                       content_type, body, accept):
        """Implement the processing stack."""

        # Get the implementing method
        try:
            meth, extensions = self.get_method(request, action,
                                               content_type, body)
        except (AttributeError, TypeError):
            return Fault(webob.exc.HTTPNotFound())
        except KeyError as ex:
            msg = _("There is no such action: %s") % ex.args[0]
            return Fault(webob.exc.HTTPBadRequest(explanation=msg))
        except exception.MalformedRequestBody:
            msg = _("Malformed request body")
            return Fault(webob.exc.HTTPBadRequest(explanation=msg))
        except webob.exc.HTTPMethodNotAllowed as e:
            return Fault(e)

        if body:
            msg = _("Action: '%(action)s', calling method: %(meth)s, body: "
                    "%(body)s") % {'action': action,
                                   'body': str(body, 'utf-8'),
                                   'meth': str(meth)}
            LOG.debug(strutils.mask_password(msg))
        else:
            LOG.debug("Calling method '%(meth)s'",
                      {'meth': str(meth)})

        # Now, deserialize the request body...
        try:
            contents = {}
            if self._should_have_body(request):
                # allow empty body with PUT and POST
                if request.content_length == 0:
                    contents = {'body': None}
                else:
                    contents = self.deserialize(body)
        except exception.MalformedRequestBody:
            msg = _("Malformed request body")
            return Fault(webob.exc.HTTPBadRequest(explanation=msg))

        # Update the action args
        action_args.update(contents)

        project_id = action_args.pop("project_id", None)
        context = request.environ.get('masakari.context')
        if (context and project_id and (project_id != context.project_id)):
            msg = _("Malformed request URL: URL's project_id '%(project_id)s'"
                    " doesn't match Context's project_id"
                    " '%(context_project_id)s'") % {
                'project_id': project_id,
                'context_project_id': context.project_id
            }
            return Fault(webob.exc.HTTPBadRequest(explanation=msg))

        # Run pre-processing extensions
        response, post = self.pre_process_extensions(extensions,
                                                     request, action_args)

        if not response:
            try:
                with ResourceExceptionHandler():
                    action_result = self.dispatch(meth, request, action_args)
            except Fault as ex:
                response = ex

        if not response:
            # No exceptions; convert action_result into a
            # ResponseObject
            resp_obj = None
            if type(action_result) is dict or action_result is None:
                resp_obj = ResponseObject(action_result)
            elif isinstance(action_result, ResponseObject):
                resp_obj = action_result
            else:
                response = action_result

            # Run post-processing extensions
            if resp_obj:
                # Do a preserialize to set up the response object
                if hasattr(meth, 'wsgi_code'):
                    resp_obj._default_code = meth.wsgi_code
                # Process post-processing extensions
                response = self.post_process_extensions(post, resp_obj,
                                                        request, action_args)

            if resp_obj and not response:
                response = resp_obj.serialize(request, accept)

        if hasattr(response, 'headers'):
            for hdr, val in list(response.headers.items()):
                response.headers[hdr] = str(val)

            if not request.api_version_request.is_null():
                response.headers[API_VERSION_REQUEST_HEADER] = \
                    'masakari ' + request.api_version_request.get_string()
                response.headers.add('Vary', API_VERSION_REQUEST_HEADER)

        return response

    def get_method(self, request, action, content_type, body):
        meth, extensions = self._get_method(request,
                                            action,
                                            content_type,
                                            body)
        if self.inherits:
            _meth, parent_ext = self.inherits.get_method(request,
                                                         action,
                                                         content_type,
                                                         body)
            extensions.extend(parent_ext)
        return meth, extensions

    def _get_method(self, request, action, content_type, body):
        """Look up the action-specific method and its extensions."""
        # Look up the method
        try:
            if not self.controller:
                meth = getattr(self, action)
            else:
                meth = getattr(self.controller, action)
        except AttributeError:
            if (not self.wsgi_actions or
                    action not in _ROUTES_METHODS + ['action']):
                if self.controller:
                    msg = _("The request method: '%(method)s' with action: "
                            "'%(action)s' is not allowed on this "
                            "resource") % {
                                'method': request.method, 'action': action
                        }
                    raise webob.exc.HTTPMethodNotAllowed(
                        explanation=msg, body_template='${explanation}')
                # Propagate the error
                raise
        else:
            return meth, self.wsgi_extensions.get(action, [])

        if action == 'action':
            action_name = action_peek(body)
        else:
            action_name = action

        # Look up the action method
        return (self.wsgi_actions[action_name],
                self.wsgi_action_extensions.get(action_name, []))

    def dispatch(self, method, request, action_args):
        """Dispatch a call to the action-specific method."""

        try:
            return method(req=request, **action_args)
        except exception.VersionNotFoundForAPIMethod:
            # We deliberately don't return any message information
            # about the exception to the user so it looks as if
            # the method is simply not implemented.
            return Fault(webob.exc.HTTPNotFound())


class ResourceV1(Resource):
    support_api_request_version = True


def action(name):
    """Mark a function as an action.

    The given name will be taken as the action key in the body.

    This is also overloaded to allow extensions to provide
    non-extending definitions of create and delete operations.
    """

    def decorator(func):
        func.wsgi_action = name
        return func
    return decorator


def extends(*args, **kwargs):
    """Indicate a function extends an operation.

    Can be used as either::

        @extends
        def index(...):
            pass

    or as::

        @extends(action='resize')
        def _action_resize(...):
            pass
    """

    def decorator(func):
        # Store enough information to find what we're extending
        func.wsgi_extends = (func.__name__, kwargs.get('action'))
        return func

    # If we have positional arguments, call the decorator
    if args:
        return decorator(*args)

    # OK, return the decorator instead
    return decorator


class ControllerMetaclass(type):
    """Controller metaclass.

    This metaclass automates the task of assembling a dictionary
    mapping action keys to method names.
    """

    def __new__(mcs, name, bases, cls_dict):
        """Adds the wsgi_actions dictionary to the class."""

        # Find all actions
        actions = {}
        extensions = []
        versioned_methods = None
        # start with wsgi actions from base classes
        for base in bases:
            actions.update(getattr(base, 'wsgi_actions', {}))

            if base.__name__ == "Controller":
                # NOTE: This resets the VER_METHOD_ATTR attribute
                # between API controller class creations. This allows us
                # to use a class decorator on the API methods that doesn't
                # require naming explicitly what method is being versioned as
                # it can be implicit based on the method decorated. It is a bit
                # ugly.
                if VER_METHOD_ATTR in base.__dict__:
                    versioned_methods = getattr(base, VER_METHOD_ATTR)
                    delattr(base, VER_METHOD_ATTR)

        for key, value in cls_dict.items():
            if not callable(value):
                continue
            if getattr(value, 'wsgi_action', None):
                actions[value.wsgi_action] = key
            elif getattr(value, 'wsgi_extends', None):
                extensions.append(value.wsgi_extends)

        # Add the actions and extensions to the class dict
        cls_dict['wsgi_actions'] = actions
        cls_dict['wsgi_extensions'] = extensions
        if versioned_methods:
            cls_dict[VER_METHOD_ATTR] = versioned_methods

        return super(ControllerMetaclass, mcs).__new__(mcs, name, bases,
                                                       cls_dict)


class Controller(object, metaclass=ControllerMetaclass):
    """Default controller."""

    _view_builder_class = None

    def __init__(self, view_builder=None):
        """Initialize controller with a view builder instance."""
        if view_builder:
            self._view_builder = view_builder
        elif self._view_builder_class:
            self._view_builder = self._view_builder_class()
        else:
            self._view_builder = None

    def __getattribute__(self, key):

        def version_select(*args, **kwargs):
            """Look for the method which matches the name supplied and version
            constraints and calls it with the supplied arguments.

            @return: Returns the result of the method called
            @raises: VersionNotFoundForAPIMethod if there is no method which
                 matches the name and version constraints
            """

            # The first arg to all versioned methods is always the request
            # object. The version for the request is attached to the
            # request object
            if len(args) == 0:
                ver = kwargs['req'].api_version_request
            else:
                ver = args[0].api_version_request

            func_list = self.versioned_methods[key]
            for func in func_list:
                if ver.matches(func.start_version, func.end_version):
                    # Update the version_select wrapper function so
                    # other decorator attributes like wsgi.response
                    # are still respected.
                    functools.update_wrapper(version_select, func.func)
                    return func.func(self, *args, **kwargs)

            # No version match
            raise exception.VersionNotFoundForAPIMethod(version=ver)

        try:
            version_meth_dict = object.__getattribute__(self, VER_METHOD_ATTR)
        except AttributeError:
            # No versioning on this class
            return object.__getattribute__(self, key)

        if version_meth_dict and key in object.__getattribute__(
                self, VER_METHOD_ATTR):
            return version_select

        return object.__getattribute__(self, key)

    # NOTE: This decorator MUST appear first (the outermost
    # decorator) on an API method for it to work correctly
    @classmethod
    def api_version(cls, min_ver, max_ver=None):
        """Decorator for versioning api methods.

        Add the decorator to any method which takes a request object
        as the first parameter and belongs to a class which inherits from
        wsgi.Controller.

        @min_ver: string representing minimum version
        @max_ver: optional string representing maximum version
        """

        def decorator(f):
            obj_min_ver = api_version.APIVersionRequest(min_ver)
            if max_ver:
                obj_max_ver = api_version.APIVersionRequest(max_ver)
            else:
                obj_max_ver = api_version.APIVersionRequest()

            # Add to list of versioned methods registered
            func_name = f.__name__
            new_func = versioned_method.VersionedMethod(
                func_name, obj_min_ver, obj_max_ver, f)

            func_dict = getattr(cls, VER_METHOD_ATTR, {})
            if not func_dict:
                setattr(cls, VER_METHOD_ATTR, func_dict)

            func_list = func_dict.get(func_name, [])
            if not func_list:
                func_dict[func_name] = func_list
            func_list.append(new_func)
            # Ensure the list is sorted by minimum version (reversed)
            # so later when we work through the list in order we find
            # the method which has the latest version which supports
            # the version requested.
            is_intersect = Controller.check_for_versions_intersection(
                func_list)

            if is_intersect:
                raise exception.ApiVersionsIntersect(
                    name=new_func.name,
                    min_ver=new_func.start_version,
                    max_ver=new_func.end_version,
                )

            func_list.sort(key=lambda f: f.start_version, reverse=True)

            return f

        return decorator

    @staticmethod
    def is_valid_body(body, entity_name):
        if not (body and entity_name in body):
            return False

        def is_dict(d):
            try:
                d.get(None)
                return True
            except AttributeError:
                return False

        return is_dict(body[entity_name])

    @staticmethod
    def check_for_versions_intersection(func_list):
        """Determines function list contains version intervals intersections.

        General algorithm:
        https://en.wikipedia.org/wiki/Intersection_algorithm

        :param func_list: list of VersionedMethod objects
        :return: boolean
        """
        pairs = []
        counter = 0

        for f in func_list:
            pairs.append((f.start_version, 1, f))
            pairs.append((f.end_version, -1, f))

        def compare(x):
            return x[0]

        pairs.sort(key=compare)

        for p in pairs:
            counter += p[1]

            if counter > 1:
                return True

        return False


class Fault(webob.exc.HTTPException):
    """Wrap webob.exc.HTTPException to provide API friendly response."""

    _fault_names = {
        HTTPStatus.BAD_REQUEST: "badRequest",
        HTTPStatus.UNAUTHORIZED: "unauthorized",
        HTTPStatus.FORBIDDEN: "forbidden",
        HTTPStatus.NOT_FOUND: "itemNotFound",
        HTTPStatus.METHOD_NOT_ALLOWED: "badMethod",
        HTTPStatus.CONFLICT: "conflictingRequest",
        HTTPStatus.REQUEST_ENTITY_TOO_LARGE: "overLimit",
        HTTPStatus.UNSUPPORTED_MEDIA_TYPE: "badMediaType",
        HTTPStatus.NOT_IMPLEMENTED: "notImplemented",
        HTTPStatus.SERVICE_UNAVAILABLE: "serviceUnavailable",
        HTTPStatus.TOO_MANY_REQUESTS: "overLimit"
    }

    def __init__(self, exception):
        """Create a Fault for the given webob.exc.exception."""
        self.wrapped_exc = exception
        for key, value in list(self.wrapped_exc.headers.items()):
            self.wrapped_exc.headers[key] = str(value)
        self.status_int = exception.status_int

    @webob.dec.wsgify(RequestClass=Request)
    def __call__(self, req):
        """Generate a WSGI response based on the exception passed to ctor."""

        user_locale = req.best_match_language()
        # Replace the body with fault details.
        code = self.wrapped_exc.status_int
        fault_name = self._fault_names.get(code, "masakariFault")
        explanation = self.wrapped_exc.explanation
        LOG.debug("Returning %(code)s to user: %(explanation)s",
                  {'code': code, 'explanation': explanation})

        explanation = i18n.translate(explanation, user_locale)
        fault_data = {
            fault_name: {
                'code': code,
                'message': explanation}}
        if code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE or code == 429:
            retry = self.wrapped_exc.headers.get('Retry-After', None)
            if retry:
                fault_data[fault_name]['retryAfter'] = retry

        if not req.api_version_request.is_null():
            self.wrapped_exc.headers[API_VERSION_REQUEST_HEADER] = \
                'instance-ha ' + req.api_version_request.get_string()
            self.wrapped_exc.headers.add('Vary', API_VERSION_REQUEST_HEADER)

        self.wrapped_exc.content_type = 'application/json'
        self.wrapped_exc.charset = 'UTF-8'
        self.wrapped_exc.text = JSONDictSerializer().serialize(fault_data)

        return self.wrapped_exc

    def __str__(self):
        return self.wrapped_exc.__str__()
