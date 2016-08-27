# Copyright 2016 NTT DATA
# Administrator of the National Aeronautics and Space Administration.
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

import inspect

import six
from webob.util import status_reasons

from masakari import exception
from masakari import test


class MasakariExceptionTestCase(test.NoDBTestCase):
    def test_default_error_msg(self):
        class FakeMasakariException(exception.MasakariException):
            msg_fmt = "default message"

        exc = FakeMasakariException()
        self.assertEqual('default message', six.text_type(exc))

    def test_error_msg(self):
        self.assertEqual('test',
                         six.text_type(exception.MasakariException('test')))

    def test_default_error_msg_with_kwargs(self):
        class FakeMasakariException(exception.MasakariException):
            msg_fmt = "default message: %(code)s"

        exc = FakeMasakariException(code=500)
        self.assertEqual('default message: 500', six.text_type(exc))
        self.assertEqual('default message: 500', exc.message)

    def test_error_msg_exception_with_kwargs(self):
        class FakeMasakariException(exception.MasakariException):
            msg_fmt = "default message: %(misspelled_code)s"

        exc = FakeMasakariException(code=500, misspelled_code='blah')
        self.assertEqual('default message: blah', six.text_type(exc))
        self.assertEqual('default message: blah', exc.message)

    def test_default_error_code(self):
        class FakeMasakariException(exception.MasakariException):
            code = 404

        exc = FakeMasakariException()
        self.assertEqual(404, exc.kwargs['code'])

    def test_error_code_from_kwarg(self):
        class FakeMasakariException(exception.MasakariException):
            code = 500

        exc = FakeMasakariException(code=404)
        self.assertEqual(exc.kwargs['code'], 404)

    def test_format_message_local(self):
        class FakeMasakariException(exception.MasakariException):
            msg_fmt = "some message"

        exc = FakeMasakariException()
        self.assertEqual(six.text_type(exc), exc.format_message())

    def test_format_message_remote(self):
        class FakeMasakariException_Remote(exception.MasakariException):
            msg_fmt = "some message"

            if six.PY2:
                def __unicode__(self):
                    return u"print the whole trace"
            else:
                def __str__(self):
                    return "print the whole trace"

        exc = FakeMasakariException_Remote()
        self.assertEqual(u"print the whole trace", six.text_type(exc))
        self.assertEqual("some message", exc.format_message())

    def test_format_message_remote_error(self):
        class FakeMasakariException_Remote(exception.MasakariException):
            msg_fmt = "some message %(somearg)s"

            def __unicode__(self):
                return u"print the whole trace"

        self.flags(fatal_exception_format_errors=False)
        exc = FakeMasakariException_Remote(lame_arg='lame')
        self.assertEqual("some message %(somearg)s", exc.format_message())


class ConvertedExceptionTestCase(test.NoDBTestCase):
    def test_instantiate(self):
        exc = exception.ConvertedException(400, 'Bad Request', 'reason')
        self.assertEqual(exc.code, 400)
        self.assertEqual(exc.title, 'Bad Request')
        self.assertEqual(exc.explanation, 'reason')

    def test_instantiate_without_title_known_code(self):
        exc = exception.ConvertedException(500)
        self.assertEqual(exc.title, status_reasons[500])

    def test_instantiate_without_title_unknown_code(self):
        exc = exception.ConvertedException(499)
        self.assertEqual(exc.title, 'Unknown Client Error')

    def test_instantiate_bad_code(self):
        self.assertRaises(KeyError, exception.ConvertedException, 10)


class ExceptionTestCase(test.NoDBTestCase):
    @staticmethod
    def _raise_exc(exc):
        raise exc(500)

    def test_exceptions_raise(self):
        # NOTE(Dinesh_Bhor): disable format errors since we are not passing
        # kwargs
        self.flags(fatal_exception_format_errors=False)
        for name in dir(exception):
            exc = getattr(exception, name)
            if isinstance(exc, type):
                self.assertRaises(exc, self._raise_exc, exc)


class ExceptionValidMessageTestCase(test.NoDBTestCase):

    def test_messages(self):
        failures = []

        for name, obj in inspect.getmembers(exception):
            if name in ['MasakariException', 'InstanceFaultRollback']:
                continue

            if not inspect.isclass(obj):
                continue

            if not issubclass(obj, exception.MasakariException):
                continue

            e = obj
            if e.msg_fmt == "An unknown exception occurred.":
                failures.append('%s needs a more specific msg_fmt' % name)

        if failures:
            self.fail('\n'.join(failures))
