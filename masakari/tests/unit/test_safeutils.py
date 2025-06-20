#    Copyright 2016 NTT DATA
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

from masakari import safe_utils
from masakari.tests.unit import base


class WrappedCodeTestCase(base.NoDBTestCase):
    """Test the get_wrapped_function utility method."""

    def _wrapper(self, function):
        @functools.wraps(function)
        def decorated_function(self, *args, **kwargs):
            function(self, *args, **kwargs)
        return decorated_function

    def test_single_wrapped(self):
        @self._wrapper
        def wrapped(self, instance, red=None, blue=None):
            pass

        func = safe_utils.get_wrapped_function(wrapped)
        func_code = func.__code__
        self.assertEqual(4, len(func_code.co_varnames))
        self.assertIn('self', func_code.co_varnames)
        self.assertIn('instance', func_code.co_varnames)
        self.assertIn('red', func_code.co_varnames)
        self.assertIn('blue', func_code.co_varnames)

    def test_double_wrapped(self):
        @self._wrapper
        @self._wrapper
        def wrapped(self, instance, red=None, blue=None):
            pass

        func = safe_utils.get_wrapped_function(wrapped)
        func_code = func.__code__
        self.assertEqual(4, len(func_code.co_varnames))
        self.assertIn('self', func_code.co_varnames)
        self.assertIn('instance', func_code.co_varnames)
        self.assertIn('red', func_code.co_varnames)
        self.assertIn('blue', func_code.co_varnames)

    def test_triple_wrapped(self):
        @self._wrapper
        @self._wrapper
        @self._wrapper
        def wrapped(self, instance, red=None, blue=None):
            pass

        func = safe_utils.get_wrapped_function(wrapped)
        func_code = func.__code__
        self.assertEqual(4, len(func_code.co_varnames))
        self.assertIn('self', func_code.co_varnames)
        self.assertIn('instance', func_code.co_varnames)
        self.assertIn('red', func_code.co_varnames)
        self.assertIn('blue', func_code.co_varnames)
