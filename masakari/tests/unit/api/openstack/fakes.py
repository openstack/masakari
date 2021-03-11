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

from oslo_utils import timeutils
import routes
import webob.dec

from masakari.api import api_version_request as api_version
from masakari.api import auth as api_auth
from masakari.api import openstack as openstack_api
from masakari.api.openstack import ha
from masakari.api.openstack.ha import versions
from masakari.api.openstack import wsgi as os_wsgi
from masakari.api import urlmap
from masakari import context
from masakari.tests import uuidsentinel
from masakari import wsgi


@webob.dec.wsgify
def fake_wsgi(self, req):
    return self.application


def wsgi_app_v1(fake_auth_context=None, init_only=None):

    inner_app_v1 = ha.APIRouterV1()

    if fake_auth_context is not None:
        ctxt = fake_auth_context
    else:
        ctxt = context.RequestContext('fake', 'fake', auth_token=True)
    api_v1 = (
        openstack_api.FaultWrapper(api_auth.InjectContext(ctxt, inner_app_v1)))
    mapper = urlmap.URLMap()
    mapper['/v1'] = api_v1
    mapper['/'] = openstack_api.FaultWrapper(versions.Versions())
    return mapper


class FakeToken(object):
    id_count = 0

    def __getitem__(self, key):
        return getattr(self, key)

    def __init__(self, **kwargs):
        FakeToken.id_count += 1
        self.id = FakeToken.id_count
        for k, v in kwargs.items():
            setattr(self, k, v)


class FakeRequestContext(context.RequestContext):
    def __init__(self, *args, **kwargs):
        kwargs['auth_token'] = kwargs.get('auth_token', 'fake_auth_token')
        super(FakeRequestContext, self).__init__(*args, **kwargs)


class HTTPRequest(os_wsgi.Request):

    @staticmethod
    def blank(*args, **kwargs):
        kwargs['base_url'] = 'http://localhost/v1'
        use_admin_context = kwargs.pop('use_admin_context', False)
        project_id = kwargs.pop('project_id', uuidsentinel.fake_project_id)
        version = kwargs.pop('version', api_version.DEFAULT_API_VERSION)
        out = os_wsgi.Request.blank(*args, **kwargs)
        out.environ['masakari.context'] = FakeRequestContext(
            user_id=uuidsentinel.fake_user_id,
            project_id=project_id,
            is_admin=use_admin_context)
        out.api_version_request = api_version.APIVersionRequest(version)
        return out


class TestRouter(wsgi.Router):
    def __init__(self, controller, mapper=None):
        if not mapper:
            mapper = routes.Mapper()
        mapper.resource("test", "tests",
                        controller=os_wsgi.Resource(controller))
        super(TestRouter, self).__init__(mapper)


class FakeAuthDatabase(object):
    data = {}

    @staticmethod
    def auth_token_get(context, token_hash):
        return FakeAuthDatabase.data.get(token_hash, None)

    @staticmethod
    def auth_token_create(context, token):
        fake_token = FakeToken(created_at=timeutils.utcnow(), **token)
        FakeAuthDatabase.data[fake_token.token_hash] = fake_token
        FakeAuthDatabase.data['id_%i' % fake_token.id] = fake_token
        return fake_token

    @staticmethod
    def auth_token_destroy(context, token_id):
        token = FakeAuthDatabase.data.get('id_%i' % token_id)
        if token and token.token_hash in FakeAuthDatabase.data:
            del FakeAuthDatabase.data[token.token_hash]
            del FakeAuthDatabase.data['id_%i' % token_id]


def fake_get_available_languages():
    existing_translations = ['en_GB', 'en_AU', 'de', 'zh_CN', 'en_US']
    return existing_translations


def fake_not_implemented(*args, **kwargs):
    raise NotImplementedError()
