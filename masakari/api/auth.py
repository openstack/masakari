# Copyright (c) 2016 NTT DATA
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
Common Auth Middleware.
"""

from oslo_log import log as logging
from oslo_middleware import request_id
from oslo_serialization import jsonutils
import webob.dec
import webob.exc

from masakari.api import wsgi
import masakari.conf
from masakari import context
from masakari.i18n import _


CONF = masakari.conf.CONF
LOG = logging.getLogger(__name__)


def _load_pipeline(loader, pipeline):
    filters = [loader.get_filter(n) for n in pipeline[:-1]]
    app = loader.get_app(pipeline[-1])
    filters.reverse()
    for filter in filters:
        app = filter(app)
    return app


def pipeline_factory_v1(loader, global_conf, **local_conf):
    """A paste pipeline replica that keys off of auth_strategy."""

    return _load_pipeline(loader, local_conf[CONF.auth_strategy].split())


class InjectContext(wsgi.Middleware):
    """Add a 'masakari.context' to WSGI environ."""

    def __init__(self, context, *args, **kwargs):
        self.context = context
        super(InjectContext, self).__init__(*args, **kwargs)

    @webob.dec.wsgify(RequestClass=wsgi.Request)
    def __call__(self, req):
        req.environ['masakari.context'] = self.context
        return self.application


class MasakariKeystoneContext(wsgi.Middleware):
    """Make a request context from keystone headers."""

    @webob.dec.wsgify(RequestClass=wsgi.Request)
    def __call__(self, req):
        user_id = req.headers.get('X_USER')
        user_id = req.headers.get('X_USER_ID', user_id)
        if user_id is None:
            LOG.debug("Neither X_USER_ID nor X_USER found in request")
            return webob.exc.HTTPUnauthorized()

        roles = self._get_roles(req)

        if 'X_TENANT_ID' in req.headers:
            # This is the new header since Keystone went to ID/Name
            project_id = req.headers['X_TENANT_ID']
        else:
            # This is for legacy compatibility
            project_id = req.headers['X_TENANT']
        project_name = req.headers.get('X_TENANT_NAME')
        user_name = req.headers.get('X_USER_NAME')

        req_id = req.environ.get(request_id.ENV_REQUEST_ID)

        # Get the auth token
        auth_token = req.headers.get('X_AUTH_TOKEN',
                                     req.headers.get('X_STORAGE_TOKEN'))

        # Build a context, including the auth_token...
        remote_address = req.remote_addr
        if CONF.use_forwarded_for:
            remote_address = req.headers.get('X-Forwarded-For', remote_address)

        service_catalog = None
        if req.headers.get('X_SERVICE_CATALOG') is not None:
            try:
                catalog_header = req.headers.get('X_SERVICE_CATALOG')
                service_catalog = jsonutils.loads(catalog_header)
            except ValueError:
                raise webob.exc.HTTPInternalServerError(
                    _('Invalid service catalog json.'))

        # NOTE: This is a full auth plugin set by auth_token
        # middleware in newer versions.
        user_auth_plugin = req.environ.get('keystone.token_auth')

        ctx = context.RequestContext(user_id,
                                     project_id,
                                     user_name=user_name,
                                     project_name=project_name,
                                     roles=roles,
                                     auth_token=auth_token,
                                     remote_address=remote_address,
                                     service_catalog=service_catalog,
                                     request_id=req_id,
                                     user_auth_plugin=user_auth_plugin)

        req.environ['masakari.context'] = ctx
        return self.application

    def _get_roles(self, req):
        """Get the list of roles."""

        roles = req.headers.get('X_ROLES', '')
        return [r.strip() for r in roles.split(',')]


class NoAuthMiddleware(wsgi.Middleware):
    """Return a fake token if one isn't specified.

    noauth2 provides admin privs if 'admin' is provided as the user id.

    """

    @webob.dec.wsgify(RequestClass=wsgi.Request)
    def __call__(self, req):
        user_id = req.headers.get('X_USER', 'admin')
        user_id = req.headers.get('X_USER_ID', user_id)

        project_name = req.headers.get('X_TENANT_NAME')
        user_name = req.headers.get('X_USER_NAME')

        req_id = req.environ.get(request_id.ENV_REQUEST_ID)

        remote_address = req.remote_addr
        if CONF.use_forwarded_for:
            remote_address = req.headers.get('X-Forwarded-For', remote_address)

        service_catalog = None
        if req.headers.get('X_SERVICE_CATALOG') is not None:
            try:
                catalog_header = req.headers.get('X_SERVICE_CATALOG')
                service_catalog = jsonutils.loads(catalog_header)
            except ValueError:
                raise webob.exc.HTTPInternalServerError(
                    _('Invalid service catalog json.'))

        ctx = context.RequestContext(user_id,
                                     user_name=user_name,
                                     project_name=project_name,
                                     remote_address=remote_address,
                                     service_catalog=service_catalog,
                                     request_id=req_id,
                                     is_admin=True)

        req.environ['masakari.context'] = ctx
        return self.application
