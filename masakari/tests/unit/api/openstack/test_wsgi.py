#    Copyright 2016 NTT DATA
#    All Rights Reserved.
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

from http import HTTPStatus
import inspect
from unittest import mock

import testscenarios
import webob

from oslo_serialization import jsonutils

from masakari.api import api_version_request as api_version
from masakari.api.openstack import extensions
from masakari.api.openstack import wsgi
from masakari.api import versioned_method
from masakari import exception
from masakari.tests.unit.api.openstack import fakes
from masakari.tests.unit import base


class MicroversionedTest(testscenarios.WithScenarios, base.NoDBTestCase):

    header_name = 'OpenStack-API-Version'

    def _make_microversion_header(self, value):
        return {self.header_name: 'instance-ha %s' % value}


class RequestTest(MicroversionedTest):

    def test_content_type_missing(self):
        request = wsgi.Request.blank('/tests/123', method='POST')
        request.body = b"<body />"
        self.assertIsNone(request.get_content_type())

    def test_content_type_unsupported(self):
        request = wsgi.Request.blank('/tests/123', method='POST')
        request.headers["Content-Type"] = "text/html"
        request.body = b"asdf<br />"
        self.assertRaises(exception.InvalidContentType,
                          request.get_content_type)

    def test_content_type_with_charset(self):
        request = wsgi.Request.blank('/tests/123')
        request.headers["Content-Type"] = "application/json; charset=UTF-8"
        result = request.get_content_type()
        self.assertEqual(result, "application/json")

    def test_content_type_accept_default(self):
        request = wsgi.Request.blank('/tests/123.unsupported')
        request.headers["Accept"] = "application/unsupported1"
        result = request.best_match_content_type()
        self.assertEqual(result, "application/json")

    def test_from_request(self):
        self.stub_out('masakari.i18n.get_available_languages',
                      fakes.fake_get_available_languages)

        request = wsgi.Request.blank('/')
        accepted = 'bogus;q=1, en-gb;q=0.7,en-us,en;q=0.5,*;q=0.7'
        request.headers = {'Accept-Language': accepted}
        self.assertEqual(request.best_match_language(), 'en_US')

    def test_asterisk(self):
        # asterisk should match first available if there
        # are not any other available matches
        self.stub_out('masakari.i18n.get_available_languages',
                      fakes.fake_get_available_languages)

        request = wsgi.Request.blank('/')
        accepted = '*,es;q=0.5'
        request.headers = {'Accept-Language': accepted}
        self.assertEqual(request.best_match_language(), 'en_GB')

    def test_prefix(self):
        self.stub_out('masakari.i18n.get_available_languages',
                      fakes.fake_get_available_languages)

        request = wsgi.Request.blank('/')
        accepted = 'zh'
        request.headers = {'Accept-Language': accepted}
        self.assertEqual(request.best_match_language(), 'zh_CN')

    def test_secondary(self):
        self.stub_out('masakari.i18n.get_available_languages',
                      fakes.fake_get_available_languages)

        request = wsgi.Request.blank('/')
        accepted = 'nn,en-gb;q=0.5'
        request.headers = {'Accept-Language': accepted}
        self.assertEqual(request.best_match_language(), 'en_GB')

    def test_none_found(self):
        self.stub_out('masakari.i18n.get_available_languages',
                      fakes.fake_get_available_languages)

        request = wsgi.Request.blank('/')
        accepted = 'nb-no'
        request.headers = {'Accept-Language': accepted}
        self.assertIsNone(request.best_match_language())

    def test_no_lang_header(self):
        self.stub_out('masakari.i18n.get_available_languages',
                      fakes.fake_get_available_languages)

        request = wsgi.Request.blank('/')
        accepted = ''
        request.headers = {'Accept-Language': accepted}
        self.assertIsNone(request.best_match_language())

    def test_api_version_request_header_none(self):
        request = wsgi.Request.blank('/')
        request.set_api_version_request()
        self.assertEqual(api_version.APIVersionRequest(
            api_version.DEFAULT_API_VERSION), request.api_version_request)

    @mock.patch("masakari.api.api_version_request.max_api_version")
    def test_api_version_request_header(self, mock_maxver):
        mock_maxver.return_value = api_version.APIVersionRequest("1.0")

        request = wsgi.Request.blank('/')
        request.headers = self._make_microversion_header('1.0')
        request.set_api_version_request()
        self.assertEqual(api_version.APIVersionRequest("1.0"),
                         request.api_version_request)

    def test_api_version_request_header_invalid(self):
        request = wsgi.Request.blank('/')
        request.headers = self._make_microversion_header('1.1.1')
        self.assertRaises(exception.InvalidAPIVersionString,
                          request.set_api_version_request)


class ActionDispatcherTest(base.NoDBTestCase):
    def test_dispatch(self):
        serializer = wsgi.ActionDispatcher()
        serializer.create = lambda x: 'pants'
        self.assertEqual(serializer.dispatch({}, action='create'), 'pants')

    def test_dispatch_action_None(self):
        serializer = wsgi.ActionDispatcher()
        serializer.create = lambda x: 'pants'
        serializer.default = lambda x: 'trousers'
        self.assertEqual(serializer.dispatch({}, action=None), 'trousers')

    def test_dispatch_default(self):
        serializer = wsgi.ActionDispatcher()
        serializer.create = lambda x: 'pants'
        serializer.default = lambda x: 'trousers'
        self.assertEqual(serializer.dispatch({}, action='update'), 'trousers')


class JSONDictSerializerTest(base.NoDBTestCase):
    def test_json(self):
        input_dict = dict(segments=dict(a=(2, 3)))
        expected_json = '{"segments":{"a":[2,3]}}'
        serializer = wsgi.JSONDictSerializer()
        result = serializer.serialize(input_dict)
        result = result.replace('\n', '').replace(' ', '')
        self.assertEqual(result, expected_json)


class JSONDeserializerTest(base.NoDBTestCase):
    def test_json(self):
        data = """{"a": {
                "a1": "1",
                "a2": "2",
                "bs": ["1", "2", "3", {"c": {"c1": "1"}}],
                "d": {"e": "1"},
                "f": "1"}}"""
        as_dict = {
            'body': {
                'a': {
                    'a1': '1',
                    'a2': '2',
                    'bs': ['1', '2', '3', {'c': {'c1': '1'}}],
                    'd': {'e': '1'},
                    'f': '1',
                },
            },
        }
        deserializer = wsgi.JSONDeserializer()
        self.assertEqual(deserializer.deserialize(data), as_dict)

    def test_json_valid_utf8(self):
        data = b"""{"segment": {"recovery_method": "auto",
                "name": "\xe6\xa6\x82\xe5\xbf\xb5",
                "service_type": "COMPUTE_HOST"
                }} """
        as_dict = {
            'body': {
                'segment': {'recovery_method': 'auto',
                            'name': '\u6982\u5ff5',
                            'service_type': 'COMPUTE_HOST'
                            }
            }
        }
        deserializer = wsgi.JSONDeserializer()
        self.assertEqual(deserializer.deserialize(data), as_dict)

    def test_json_invalid_utf8(self):
        """Send invalid utf-8 to JSONDeserializer."""
        data = b"""{"segment": {
                "name": "\xf0\x28\x8c\x28",
                "recovery_method": "auto",
                "description": "compute hosts with shared storage enabled."
                "service_type": "COMPUTE_HOST"}} """
        deserializer = wsgi.JSONDeserializer()
        self.assertRaises(exception.MalformedRequestBody,
                          deserializer.deserialize, data)


class ResourceTest(MicroversionedTest):

    def get_req_id_header_name(self, request):
        return 'x-openstack-request-id'

    def test_resource_call_with_method_get(self):
        class Controller(object):
            def index(self, req):
                return 'success'

        app = fakes.TestRouter(Controller())
        # the default method is GET
        req = webob.Request.blank('/tests')
        response = req.get_response(app)
        self.assertEqual(b'success', response.body)
        self.assertEqual(response.status_int, HTTPStatus.OK)
        req.body = b'{"body": {"key": "value"}}'
        response = req.get_response(app)
        self.assertEqual(b'success', response.body)
        self.assertEqual(response.status_int, HTTPStatus.OK)
        req.content_type = 'application/json'
        response = req.get_response(app)
        self.assertEqual(b'success', response.body)
        self.assertEqual(response.status_int, HTTPStatus.OK)

    def test_resource_call_with_method_post(self):
        class Controller(object):
            @extensions.expected_errors(HTTPStatus.BAD_REQUEST)
            def create(self, req, body):
                if expected_body != body:
                    raise exception.ConvertedException(
                        code=HTTPStatus.BAD_REQUEST,
                        explanation="The request body invalid")
                return "success"
        # verify the method: POST
        app = fakes.TestRouter(Controller())
        req = webob.Request.blank('/tests', method="POST",
                                  content_type='application/json')
        req.body = b'{"body": {"key": "value"}}'
        expected_body = {'body': {
            "key": "value"
            }
        }
        response = req.get_response(app)
        self.assertEqual(response.status_int, HTTPStatus.OK)
        self.assertEqual(b'success', response.body)
        # verify without body
        expected_body = None
        req.body = None
        response = req.get_response(app)
        self.assertEqual(response.status_int, HTTPStatus.OK)
        self.assertEqual(b'success', response.body)
        # the body is validated in the controller
        expected_body = {'body': None}
        response = req.get_response(app)
        expected_unsupported_type_body = {'badRequest':
            {'message': 'The request body invalid',
             'code': HTTPStatus.BAD_REQUEST}}
        self.assertEqual(response.status_int, HTTPStatus.BAD_REQUEST)
        self.assertEqual(expected_unsupported_type_body,
                         jsonutils.loads(response.body))

    def test_resource_call_with_method_put(self):
        class Controller(object):
            def update(self, req, id, body):
                if expected_body != body:
                    msg = "The request body invalid"
                    raise webob.exc.HTTPBadRequest(explanation=msg)
                return "success"
        # verify the method: PUT
        app = fakes.TestRouter(Controller())
        req = webob.Request.blank('/tests/test_id', method="PUT",
                                  content_type='application/json')
        req.body = b'{"body": {"key": "value"}}'
        expected_body = {'body': {
            "key": "value"
            }
        }
        response = req.get_response(app)
        self.assertEqual(b'success', response.body)
        self.assertEqual(response.status_int, HTTPStatus.OK)
        req.body = None
        expected_body = None
        response = req.get_response(app)
        self.assertEqual(response.status_int, HTTPStatus.OK)
        # verify no content_type is contained in the request
        req = webob.Request.blank('/tests/test_id', method="PUT",
                                  content_type='application/xml')
        req.content_type = 'application/xml'
        req.body = b'{"body": {"key": "value"}}'
        response = req.get_response(app)
        expected_unsupported_type_body = {'badMediaType':
            {'message': 'Unsupported Content-Type',
             'code': HTTPStatus.UNSUPPORTED_MEDIA_TYPE}}
        self.assertEqual(response.status_int,
                         HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
        self.assertEqual(expected_unsupported_type_body,
                         jsonutils.loads(response.body))

    def test_resource_call_with_method_delete(self):
        class Controller(object):
            def delete(self, req, id):
                return "success"

        # verify the method: DELETE
        app = fakes.TestRouter(Controller())
        req = webob.Request.blank('/tests/test_id', method="DELETE")
        response = req.get_response(app)
        self.assertEqual(response.status_int, HTTPStatus.OK)
        self.assertEqual(b'success', response.body)
        # ignore the body
        req.body = b'{"body": {"key": "value"}}'
        response = req.get_response(app)
        self.assertEqual(response.status_int, HTTPStatus.OK)
        self.assertEqual(b'success', response.body)

    def test_resource_not_authorized(self):
        class Controller(object):
            def index(self, req):
                raise exception.Forbidden()

        req = webob.Request.blank('/tests')
        app = fakes.TestRouter(Controller())
        response = req.get_response(app)
        self.assertEqual(response.status_int, HTTPStatus.FORBIDDEN)

    def test_dispatch(self):
        class Controller(object):
            def index(self, req, pants=None):
                return pants

        controller = Controller()
        resource = wsgi.Resource(controller)
        method, extensions = resource.get_method(None, 'index', None, '')
        actual = resource.dispatch(method, None, {'pants': 'off'})
        expected = 'off'
        self.assertEqual(actual, expected)

    def test_get_method_unknown_controller_method(self):
        class Controller(object):
            def index(self, req, pants=None):
                return pants

        controller = Controller()
        resource = wsgi.Resource(controller)
        self.assertRaises(AttributeError, resource.get_method,
                          None, 'create', None, '')

    def test_get_method_action_json(self):
        class Controller(wsgi.Controller):
            @wsgi.action('fooAction')
            def _action_foo(self, req, id, body):
                return body

        controller = Controller()
        resource = wsgi.Resource(controller)
        method, extensions = resource.get_method(None, 'action',
                                                 'application/json',
                                                 '{"fooAction": true}')
        self.assertEqual(controller._action_foo, method)

    def test_get_method_action_bad_body(self):
        class Controller(wsgi.Controller):
            @wsgi.action('fooAction')
            def _action_foo(self, req, id, body):
                return body

        controller = Controller()
        resource = wsgi.Resource(controller)
        self.assertRaises(exception.MalformedRequestBody, resource.get_method,
                          None, 'action', 'application/json', '{}')

    def test_get_method_unknown_controller_action(self):
        class Controller(wsgi.Controller):
            @wsgi.action('fooAction')
            def _action_foo(self, req, id, body):
                return body

        controller = Controller()
        resource = wsgi.Resource(controller)
        self.assertRaises(KeyError, resource.get_method,
                          None, 'action', 'application/json',
                          '{"barAction": true}')

    def test_get_method_action_method(self):
        class Controller(object):
            def action(self, req, pants=None):
                return pants

        controller = Controller()
        resource = wsgi.Resource(controller)
        method, extensions = resource.get_method(None, 'action',
                                                 'application/xml',
                                                 '<fooAction>true</fooAction')
        self.assertEqual(controller.action, method)

    def test_get_action_args(self):
        class Controller(object):
            def index(self, req, pants=None):
                return pants

        controller = Controller()
        resource = wsgi.Resource(controller)

        env = {
            'wsgiorg.routing_args': [None, {
                'controller': None,
                'format': None,
                'action': 'update',
                'id': 12,
            }],
        }

        expected = {'action': 'update', 'id': 12}

        self.assertEqual(resource.get_action_args(env), expected)

    def test_get_body_bad_content(self):
        class Controller(object):
            def index(self, req, pants=None):
                return pants

        controller = Controller()
        resource = wsgi.Resource(controller)

        request = wsgi.Request.blank('/', method='POST')
        request.headers['Content-Type'] = 'application/none'
        request.body = b'foo'

        self.assertRaises(exception.InvalidContentType,
                          resource.get_body, request)

    def test_get_body_no_content_type(self):
        class Controller(object):
            def index(self, req, pants=None):
                return pants

        controller = Controller()
        resource = wsgi.Resource(controller)

        request = wsgi.Request.blank('/', method='POST')
        request.body = b'foo'

        content_type, body = resource.get_body(request)
        self.assertIsNone(content_type)
        self.assertEqual(b'foo', body)

    def test_get_body_no_content_body(self):
        class Controller(object):
            def index(self, req, pants=None):
                return pants

        controller = Controller()
        resource = wsgi.Resource(controller)

        request = wsgi.Request.blank('/', method='POST')
        request.headers['Content-Type'] = 'application/json'
        request.body = b''

        content_type, body = resource.get_body(request)
        self.assertEqual('application/json', content_type)
        self.assertEqual(b'', body)

    def test_get_body(self):
        class Controller(object):
            def index(self, req, pants=None):
                return pants

        controller = Controller()
        resource = wsgi.Resource(controller)

        request = wsgi.Request.blank('/', method='POST')
        request.headers['Content-Type'] = 'application/json'
        request.body = b'foo'

        content_type, body = resource.get_body(request)
        self.assertEqual(content_type, 'application/json')
        self.assertEqual(b'foo', body)

    def test_get_dict_response_body(self):

        class Controller(wsgi.Controller):
            def index(self, req):
                return {'foo': 'bar'}

        req = fakes.HTTPRequest.blank('/tests')
        app = fakes.TestRouter(Controller())
        response = req.get_response(app)
        self.assertIn('masakari.context', req.environ)
        self.assertEqual(b'{"foo": "bar"}', response.body)
        self.assertEqual(response.status_int, HTTPStatus.OK)

    def test_str_response_body(self):

        class Controller(wsgi.Controller):
            def index(self, req):
                return 'foo'

        req = fakes.HTTPRequest.blank('/tests')
        app = fakes.TestRouter(Controller())
        response = req.get_response(app)
        expected_header = self.get_req_id_header_name(req)
        self.assertFalse(hasattr(response.headers, expected_header))
        self.assertEqual(b'foo', response.body)
        self.assertEqual(response.status_int, HTTPStatus.OK)

    def test_get_no_response_body(self):

        class Controller(object):
            def index(self, req):
                pass

        req = fakes.HTTPRequest.blank('/tests')
        app = fakes.TestRouter(Controller())
        response = req.get_response(app)
        self.assertIn('masakari.context', req.environ)
        self.assertEqual(b'', response.body)
        self.assertEqual(response.status_int, HTTPStatus.OK)

    def test_deserialize_default(self):
        class Controller(object):
            def index(self, req, pants=None):
                return pants

        controller = Controller()
        resource = wsgi.Resource(controller)

        obj = resource.deserialize('["foo"]')
        self.assertEqual(obj, {'body': ['foo']})

    def test_register_actions(self):
        class Controller(object):
            def index(self, req, pants=None):
                return pants

        class ControllerExtended(wsgi.Controller):
            @wsgi.action('fooAction')
            def _action_foo(self, req, id, body):
                return body

            @wsgi.action('barAction')
            def _action_bar(self, req, id, body):
                return body

        controller = Controller()
        resource = wsgi.Resource(controller)
        self.assertEqual({}, resource.wsgi_actions)

        extended = ControllerExtended()
        resource.register_actions(extended)
        self.assertEqual({'fooAction': extended._action_foo,
                          'barAction': extended._action_bar
                          }, resource.wsgi_actions)

    def test_register_extensions(self):
        class Controller(object):
            def index(self, req, pants=None):
                return pants

        class ControllerExtended(wsgi.Controller):
            @wsgi.extends
            def index(self, req, resp_obj, pants=None):
                return None

            @wsgi.extends(action='fooAction')
            def _action_foo(self, req, resp, id, body):
                return None

        controller = Controller()
        resource = wsgi.Resource(controller)
        self.assertEqual({}, resource.wsgi_extensions)
        self.assertEqual({}, resource.wsgi_action_extensions)

        extended = ControllerExtended()
        resource.register_extensions(extended)
        self.assertEqual({'index': [extended.index]}, resource.wsgi_extensions)
        self.assertEqual({'fooAction': [extended._action_foo]},
                         resource.wsgi_action_extensions)

    def test_get_method_extensions(self):
        class Controller(object):
            def index(self, req, pants=None):
                return pants

        class ControllerExtended(wsgi.Controller):
            @wsgi.extends
            def index(self, req, resp_obj, pants=None):
                return None

        controller = Controller()
        extended = ControllerExtended()
        resource = wsgi.Resource(controller)
        resource.register_extensions(extended)
        method, extensions = resource.get_method(None, 'index', None, '')
        self.assertEqual(method, controller.index)
        self.assertEqual(extensions, [extended.index])

    def test_get_method_action_extensions(self):
        class Controller(wsgi.Controller):
            def index(self, req, pants=None):
                return pants

            @wsgi.action('fooAction')
            def _action_foo(self, req, id, body):
                return body

        class ControllerExtended(wsgi.Controller):
            @wsgi.extends(action='fooAction')
            def _action_foo(self, req, resp_obj, id, body):
                return None

        controller = Controller()
        extended = ControllerExtended()
        resource = wsgi.Resource(controller)
        resource.register_extensions(extended)
        method, extensions = resource.get_method(None, 'action',
                                                 'application/json',
                                                 '{"fooAction": true}')
        self.assertEqual(method, controller._action_foo)
        self.assertEqual(extensions, [extended._action_foo])

    def test_get_method_action_whitelist_extensions(self):
        class Controller(wsgi.Controller):
            def index(self, req, pants=None):
                return pants

        class ControllerExtended(wsgi.Controller):
            @wsgi.action('create')
            def _create(self, req, body):
                pass

            @wsgi.action('delete')
            def _delete(self, req, id):
                pass

        controller = Controller()
        extended = ControllerExtended()
        resource = wsgi.Resource(controller)
        resource.register_actions(extended)

        method, extensions = resource.get_method(None, 'create',
                                                 'application/json',
                                                 '{"create": true}')
        self.assertEqual(method, extended._create)
        self.assertEqual(extensions, [])

        method, extensions = resource.get_method(None, 'delete', None, None)
        self.assertEqual(method, extended._delete)
        self.assertEqual(extensions, [])

    def test_pre_process_extensions_regular(self):
        class Controller(object):
            def index(self, req, pants=None):
                return pants

        controller = Controller()
        resource = wsgi.Resource(controller)

        called = []

        def extension1(req, resp_obj):
            called.append(1)
            return None

        def extension2(req, resp_obj):
            called.append(2)
            return None

        extensions = [extension1, extension2]
        response, post = resource.pre_process_extensions(extensions, None, {})
        self.assertEqual(called, [])
        self.assertIsNone(response)
        self.assertEqual(list(post), [extension2, extension1])

    def test_pre_process_extensions_generator(self):
        class Controller(object):
            def index(self, req, pants=None):
                return pants

        controller = Controller()
        resource = wsgi.Resource(controller)

        called = []

        def extension1(req):
            called.append('pre1')
            yield
            called.append('post1')

        def extension2(req):
            called.append('pre2')
            yield
            called.append('post2')

        extensions = [extension1, extension2]
        response, post = resource.pre_process_extensions(extensions, None, {})
        post = list(post)
        self.assertEqual(called, ['pre1', 'pre2'])
        self.assertIsNone(response)
        self.assertEqual(len(post), 2)
        self.assertTrue(inspect.isgenerator(post[0]))
        self.assertTrue(inspect.isgenerator(post[1]))

        for gen in post:
            try:
                gen.send(None)
            except StopIteration:
                continue

        self.assertEqual(called, ['pre1', 'pre2', 'post2', 'post1'])

    def test_pre_process_extensions_generator_response(self):
        class Controller(object):
            def index(self, req, pants=None):
                return pants

        controller = Controller()
        resource = wsgi.Resource(controller)

        called = []

        def extension1(req):
            called.append('pre1')
            yield 'foo'

        def extension2(req):
            called.append('pre2')

        extensions = [extension1, extension2]
        response, post = resource.pre_process_extensions(extensions, None, {})
        self.assertEqual(called, ['pre1'])
        self.assertEqual(response, 'foo')
        self.assertEqual(post, [])

    def test_post_process_extensions_regular(self):
        class Controller(object):
            def index(self, req, pants=None):
                return pants

        controller = Controller()
        resource = wsgi.Resource(controller)

        called = []

        def extension1(req, resp_obj):
            called.append(1)
            return None

        def extension2(req, resp_obj):
            called.append(2)
            return None

        response = resource.post_process_extensions([extension2, extension1],
                                                    None, None, {})
        self.assertEqual(called, [2, 1])
        self.assertIsNone(response)

    def test_post_process_extensions_regular_response(self):
        class Controller(object):
            def index(self, req, pants=None):
                return pants

        controller = Controller()
        resource = wsgi.Resource(controller)

        called = []

        def extension1(req, resp_obj):
            called.append(1)
            return None

        def extension2(req, resp_obj):
            called.append(2)
            return 'foo'

        response = resource.post_process_extensions([extension2, extension1],
                                                    None, None, {})
        self.assertEqual(called, [2])
        self.assertEqual(response, 'foo')

    def test_post_process_extensions_generator(self):
        class Controller(object):
            def index(self, req, pants=None):
                return pants

        controller = Controller()
        resource = wsgi.Resource(controller)

        called = []

        def extension1(req):
            yield
            called.append(1)

        def extension2(req):
            yield
            called.append(2)

        ext1 = extension1(None)
        next(ext1)
        ext2 = extension2(None)
        next(ext2)

        response = resource.post_process_extensions([ext2, ext1],
                                                    None, None, {})

        self.assertEqual(called, [2, 1])
        self.assertIsNone(response)

    def test_post_process_extensions_generator_response(self):
        class Controller(object):
            def index(self, req, pants=None):
                return pants

        controller = Controller()
        resource = wsgi.Resource(controller)

        called = []

        def extension1(req):
            yield
            called.append(1)

        def extension2(req):
            yield
            called.append(2)
            yield 'foo'

        ext1 = extension1(None)
        next(ext1)
        ext2 = extension2(None)
        next(ext2)

        response = resource.post_process_extensions([ext2, ext1],
                                                    None, None, {})

        self.assertEqual(called, [2])
        self.assertEqual(response, 'foo')

    def test_resource_exception_handler_type_error(self):
        # A TypeError should be translated to a Fault/HTTP 400.
        def foo(a,):
            return a

        try:
            with wsgi.ResourceExceptionHandler():
                foo()  # generate a TypeError
            self.fail("Should have raised a Fault (HTTP 400)")
        except wsgi.Fault as fault:
            self.assertEqual(HTTPStatus.BAD_REQUEST, fault.status_int)

    def test_resource_headers_py2_are_utf8(self):
        resp = webob.Response(status_int=HTTPStatus.ACCEPTED)
        resp.headers['x-header1'] = 1
        resp.headers['x-header2'] = 'header2'
        resp.headers['x-header3'] = 'header3'

        class Controller(object):
            def index(self, req):
                return resp

        req = webob.Request.blank('/tests')
        app = fakes.TestRouter(Controller())
        response = req.get_response(app)

        self.assertEqual('1', response.headers['x-header1'])
        self.assertEqual('header2', response.headers['x-header2'])
        self.assertEqual('header3', response.headers['x-header3'])

    def test_resource_valid_utf8_body(self):
        class Controller(object):
            def update(self, req, id, body):
                return body

        req = webob.Request.blank('/tests/test_id', method="PUT")
        body = b""" {"name": "\xe6\xa6\x82\xe5\xbf\xb5" } """
        expected_body = b'{"name": "\\u6982\\u5ff5"}'
        req.body = body
        req.headers['Content-Type'] = 'application/json'
        app = fakes.TestRouter(Controller())
        response = req.get_response(app)
        self.assertEqual(response.body, expected_body)
        self.assertEqual(response.status_int, HTTPStatus.OK)

    def test_resource_invalid_utf8(self):
        class Controller(object):
            def update(self, req, id, body):
                return body

        req = webob.Request.blank('/tests/test_id', method="PUT")
        body = b""" {"name": "\xf0\x28\x8c\x28" } """
        req.body = body
        req.headers['Content-Type'] = 'application/json'
        app = fakes.TestRouter(Controller())
        self.assertRaises(UnicodeDecodeError, req.get_response, app)


class ResponseObjectTest(base.NoDBTestCase):
    def test_default_code(self):
        robj = wsgi.ResponseObject({})
        self.assertEqual(robj.code, HTTPStatus.OK)

    def test_modified_code(self):
        robj = wsgi.ResponseObject({})
        robj._default_code = HTTPStatus.ACCEPTED
        self.assertEqual(robj.code, HTTPStatus.ACCEPTED)

    def test_override_default_code(self):
        robj = wsgi.ResponseObject({}, code=HTTPStatus.NOT_FOUND)
        self.assertEqual(robj.code, HTTPStatus.NOT_FOUND)

    def test_override_modified_code(self):
        robj = wsgi.ResponseObject({}, code=HTTPStatus.NOT_FOUND)
        robj._default_code = HTTPStatus.ACCEPTED
        self.assertEqual(robj.code, HTTPStatus.NOT_FOUND)

    def test_set_header(self):
        robj = wsgi.ResponseObject({})
        robj['Header'] = 'foo'
        self.assertEqual(robj.headers, {'header': 'foo'})

    def test_get_header(self):
        robj = wsgi.ResponseObject({})
        robj['Header'] = 'foo'
        self.assertEqual(robj['hEADER'], 'foo')

    def test_del_header(self):
        robj = wsgi.ResponseObject({})
        robj['Header'] = 'foo'
        del robj['hEADER']
        self.assertNotIn('header', robj.headers)

    def test_header_isolation(self):
        robj = wsgi.ResponseObject({})
        robj['Header'] = 'foo'
        hdrs = robj.headers
        hdrs['hEADER'] = 'bar'
        self.assertEqual(robj['hEADER'], 'foo')


class ValidBodyTest(base.NoDBTestCase):

    def setUp(self):
        super(ValidBodyTest, self).setUp()
        self.controller = wsgi.Controller()

    def test_is_valid_body(self):
        body = {'foo': {}}
        self.assertTrue(self.controller.is_valid_body(body, 'foo'))

    def test_is_valid_body_none(self):
        wsgi.Resource(controller=None)
        self.assertFalse(self.controller.is_valid_body(None, 'foo'))

    def test_is_valid_body_empty(self):
        wsgi.Resource(controller=None)
        self.assertFalse(self.controller.is_valid_body({}, 'foo'))

    def test_is_valid_body_no_entity(self):
        wsgi.Resource(controller=None)
        body = {'bar': {}}
        self.assertFalse(self.controller.is_valid_body(body, 'foo'))

    def test_is_valid_body_malformed_entity(self):
        wsgi.Resource(controller=None)
        body = {'foo': 'bar'}
        self.assertFalse(self.controller.is_valid_body(body, 'foo'))


class TestController(base.NoDBTestCase):
    def test_check_for_versions_intersection_negative(self):
        func_list = [
            versioned_method.VersionedMethod('foo', (
                api_version.APIVersionRequest('2.1'
                                              )
            ), api_version.APIVersionRequest('2.4'), None),
            versioned_method.VersionedMethod('foo', (
                api_version.APIVersionRequest('2.11'
                                              )
            ), (api_version.APIVersionRequest('3.1')), None),
            versioned_method.VersionedMethod('foo', (
                api_version.APIVersionRequest('2.8')
            ), api_version.APIVersionRequest('2.9'), None),
        ]

        result = (
            wsgi.Controller.check_for_versions_intersection(func_list=func_list
                                                            ))
        self.assertFalse(result)

        func_list = [
            versioned_method.VersionedMethod('foo', (
                api_version.APIVersionRequest('2.12'
                                              )
            ), api_version.APIVersionRequest('2.14'), None),
            versioned_method.VersionedMethod('foo', (
                api_version.APIVersionRequest('3.0'
                                              )
            ), api_version.APIVersionRequest('3.4'), None)]

        result = (
            wsgi.Controller.check_for_versions_intersection(func_list=func_list
                                                            ))
        self.assertFalse(result)

    def test_check_for_versions_intersection_positive(self):
        func_list = [
            versioned_method.VersionedMethod('foo', (
                api_version.APIVersionRequest('2.1'
                                              )
            ), api_version.APIVersionRequest('2.4'), None),
            versioned_method.VersionedMethod('foo', (
                api_version.APIVersionRequest('2.3'
                                              )
            ), api_version.APIVersionRequest('3.0'), None),
            versioned_method.VersionedMethod('foo', (
                api_version.APIVersionRequest('2.8'
                                              )
            ), api_version.APIVersionRequest('2.9'), None), ]

        result = (
            wsgi.Controller.check_for_versions_intersection(func_list=func_list
                                                            ))
        self.assertTrue(result)
