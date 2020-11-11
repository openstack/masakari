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

from http import HTTPStatus
import inspect

from webob.util import status_reasons

from masakari import exception
from masakari import test


class MasakariExceptionTestCase(test.NoDBTestCase):
    def test_default_error_msg(self):
        class FakeMasakariException(exception.MasakariException):
            msg_fmt = "default message"

        exc = FakeMasakariException()
        self.assertEqual('default message', str(exc))

    def test_error_msg(self):
        self.assertEqual('test',
                         str(exception.MasakariException('test')))

    def test_default_error_msg_with_kwargs(self):
        class FakeMasakariException(exception.MasakariException):
            msg_fmt = "default message: %(code)s"

        exc = FakeMasakariException(code=int(HTTPStatus.INTERNAL_SERVER_ERROR))
        self.assertEqual('default message: 500', str(exc))
        self.assertEqual('default message: 500', exc.message)

    def test_error_msg_exception_with_kwargs(self):
        class FakeMasakariException(exception.MasakariException):
            msg_fmt = "default message: %(misspelled_code)s"

        exc = FakeMasakariException(code=int(HTTPStatus.INTERNAL_SERVER_ERROR),
                                    misspelled_code='blah')
        self.assertEqual('default message: blah', str(exc))
        self.assertEqual('default message: blah', exc.message)

    def test_default_error_code(self):
        class FakeMasakariException(exception.MasakariException):
            code = HTTPStatus.NOT_FOUND

        exc = FakeMasakariException()
        self.assertEqual(HTTPStatus.NOT_FOUND, exc.kwargs['code'])

    def test_error_code_from_kwarg(self):
        class FakeMasakariException(exception.MasakariException):
            code = HTTPStatus.INTERNAL_SERVER_ERROR

        exc = FakeMasakariException(code=HTTPStatus.NOT_FOUND)
        self.assertEqual(exc.kwargs['code'], HTTPStatus.NOT_FOUND)

    def test_format_message_local(self):
        class FakeMasakariException(exception.MasakariException):
            msg_fmt = "some message"

        exc = FakeMasakariException()
        self.assertEqual(str(exc), exc.format_message())

    def test_format_message_remote(self):
        class FakeMasakariException_Remote(exception.MasakariException):
            msg_fmt = "some message"

            def __str__(self):
                return "print the whole trace"

        exc = FakeMasakariException_Remote()
        self.assertEqual(u"print the whole trace", str(exc))
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
        exc = exception.ConvertedException(int(HTTPStatus.BAD_REQUEST),
                                           'Bad Request', 'reason')
        self.assertEqual(exc.code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(exc.title, 'Bad Request')
        self.assertEqual(exc.explanation, 'reason')

    def test_instantiate_without_title_known_code(self):
        exc = exception.ConvertedException(
            int(HTTPStatus.INTERNAL_SERVER_ERROR))
        self.assertEqual(exc.title,
                         status_reasons[HTTPStatus.INTERNAL_SERVER_ERROR])

    def test_instantiate_without_title_unknown_code(self):
        exc = exception.ConvertedException(499)
        self.assertEqual(exc.title, 'Unknown Client Error')

    def test_instantiate_bad_code(self):
        self.assertRaises(KeyError, exception.ConvertedException, 10)


class ExceptionTestCase(test.NoDBTestCase):
    @staticmethod
    def _raise_exc(exc):
        raise exc(int(HTTPStatus.INTERNAL_SERVER_ERROR))

    def test_exceptions_raise(self):
        # NOTE(Dinesh_Bhor): disable format errors since we are not passing
        # kwargs
        self.flags(fatal_exception_format_errors=False)
        for name in dir(exception):
            exc = getattr(exception, name)
            # NOTE(yoctozepto): we skip HTTPStatus as it is not an exception
            # but a type also present in that module.
            if isinstance(exc, type) and name != 'HTTPStatus':
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
