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

import importlib
from unittest import mock

import eventlet
from oslo_config import cfg
from oslo_context import context as common_context
from oslo_context import fixture as context_fixture

import masakari
from masakari import context
from masakari import exception
from masakari import test
from masakari import utils

CONF = cfg.CONF


class UTF8TestCase(test.NoDBTestCase):
    def test_none_value(self):
        self.assertIsInstance(utils.utf8(None), type(None))

    def test_bytes_value(self):
        some_value = b"fake data"
        return_value = utils.utf8(some_value)
        # check that type of returned value doesn't changed
        self.assertIsInstance(return_value, type(some_value))
        self.assertEqual(some_value, return_value)

    def test_not_text_type(self):
        return_value = utils.utf8(1)
        self.assertEqual(b"1", return_value)
        self.assertIsInstance(return_value, bytes)

    def test_text_type_with_encoding(self):
        some_value = 'test\u2026config'
        self.assertEqual(some_value, utils.utf8(some_value).decode("utf-8"))


class MonkeyPatchTestCase(test.NoDBTestCase):
    """Unit test for utils.monkey_patch()."""
    def setUp(self):
        super(MonkeyPatchTestCase, self).setUp()
        self.example_package = 'masakari.tests.unit.monkey_patch_example.'
        self.flags(
            monkey_patch=True,
            monkey_patch_modules=[self.example_package + 'example_a' + ':' +
            self.example_package + 'example_decorator'])

    def test_monkey_patch(self):
        utils.monkey_patch()
        masakari.tests.unit.monkey_patch_example.CALLED_FUNCTION = []
        from masakari.tests.unit.monkey_patch_example import example_a
        from masakari.tests.unit.monkey_patch_example import example_b

        self.assertEqual('Example function', example_a.example_function_a())
        exampleA = example_a.ExampleClassA()
        exampleA.example_method()
        ret_a = exampleA.example_method_add(3, 5)
        self.assertEqual(ret_a, 8)

        self.assertEqual('Example function', example_b.example_function_b())
        exampleB = example_b.ExampleClassB()
        exampleB.example_method()
        ret_b = exampleB.example_method_add(3, 5)

        self.assertEqual(ret_b, 8)
        package_a = self.example_package + 'example_a.'
        self.assertIn(package_a + 'example_function_a',
                      masakari.tests.unit.monkey_patch_example.CALLED_FUNCTION)

        self.assertIn(package_a + 'ExampleClassA.example_method',
                      masakari.tests.unit.monkey_patch_example.CALLED_FUNCTION)
        self.assertIn(package_a + 'ExampleClassA.example_method_add',
                      masakari.tests.unit.monkey_patch_example.CALLED_FUNCTION)
        package_b = self.example_package + 'example_b.'
        self.assertNotIn(package_b + 'example_function_b', (
            masakari.tests.unit.monkey_patch_example.CALLED_FUNCTION))
        self.assertNotIn(package_b + 'ExampleClassB.example_method', (
            masakari.tests.unit.monkey_patch_example.CALLED_FUNCTION))
        self.assertNotIn(package_b + 'ExampleClassB.example_method_add', (
            masakari.tests.unit.monkey_patch_example.CALLED_FUNCTION))


class MonkeyPatchDefaultTestCase(test.NoDBTestCase):
    """Unit test for default monkey_patch_modules value."""

    def setUp(self):
        super(MonkeyPatchDefaultTestCase, self).setUp()
        self.flags(
            monkey_patch=True)

    def test_monkey_patch_default_mod(self):
        # monkey_patch_modules is defined to be
        #    <module_to_patch>:<decorator_to_patch_with>
        #  Here we check that both parts of the default values are
        # valid
        for module in CONF.monkey_patch_modules:
            m = module.split(':', 1)
            # Check we can import the module to be patched
            importlib.import_module(m[0])
            # check the decorator is valid
            decorator_name = m[1].rsplit('.', 1)
            decorator_module = importlib.import_module(decorator_name[0])
            getattr(decorator_module, decorator_name[1])


class ExpectedArgsTestCase(test.NoDBTestCase):
    def test_passes(self):
        @utils.expects_func_args('foo', 'baz')
        def dec(f):
            return f

        @dec
        def func(foo, bar, baz="lol"):
            pass

        # Call to ensure nothing errors
        func(None, None)

    def test_raises(self):
        @utils.expects_func_args('foo', 'baz')
        def dec(f):
            return f

        def func(bar, baz):
            pass

        self.assertRaises(TypeError, dec, func)

    def test_var_no_of_args(self):
        @utils.expects_func_args('foo')
        def dec(f):
            return f

        @dec
        def func(bar, *args, **kwargs):
            pass

        # Call to ensure nothing errors
        func(None)

    def test_more_layers(self):
        @utils.expects_func_args('foo', 'baz')
        def dec(f):
            return f

        def dec_2(f):
            def inner_f(*a, **k):
                return f()
            return inner_f

        @dec_2
        def func(bar, baz):
            pass

        self.assertRaises(TypeError, dec, func)


class SpawnNTestCase(test.NoDBTestCase):
    def setUp(self):
        super(SpawnNTestCase, self).setUp()
        self.useFixture(context_fixture.ClearRequestContext())
        self.spawn_name = 'spawn_n'

    def test_spawn_n_no_context(self):
        self.assertIsNone(common_context.get_current())

        def _fake_spawn(func, *args, **kwargs):
            # call the method to ensure no error is raised
            func(*args, **kwargs)
            self.assertEqual('test', args[0])

        def fake(arg):
            pass

        with mock.patch.object(eventlet, self.spawn_name, _fake_spawn):
            getattr(utils, self.spawn_name)(fake, 'test')
        self.assertIsNone(common_context.get_current())

    def test_spawn_n_context(self):
        self.assertIsNone(common_context.get_current())
        ctxt = context.RequestContext('user', 'project')

        def _fake_spawn(func, *args, **kwargs):
            # call the method to ensure no error is raised
            func(*args, **kwargs)
            self.assertEqual(ctxt, args[0])
            self.assertEqual('test', kwargs['kwarg1'])

        def fake(context, kwarg1=None):
            pass

        with mock.patch.object(eventlet, self.spawn_name, _fake_spawn):
            getattr(utils, self.spawn_name)(fake, ctxt, kwarg1='test')
        self.assertEqual(ctxt, common_context.get_current())

    def test_spawn_n_context_different_from_passed(self):
        self.assertIsNone(common_context.get_current())
        ctxt = context.RequestContext('user', 'project')
        ctxt_passed = context.RequestContext('user', 'project',
                overwrite=False)
        self.assertEqual(ctxt, common_context.get_current())

        def _fake_spawn(func, *args, **kwargs):
            # call the method to ensure no error is raised
            func(*args, **kwargs)
            self.assertEqual(ctxt_passed, args[0])
            self.assertEqual('test', kwargs['kwarg1'])

        def fake(context, kwarg1=None):
            pass

        with mock.patch.object(eventlet, self.spawn_name, _fake_spawn):
            getattr(utils, self.spawn_name)(fake, ctxt_passed, kwarg1='test')
        self.assertEqual(ctxt, common_context.get_current())


class SpawnTestCase(SpawnNTestCase):
    def setUp(self):
        super(SpawnTestCase, self).setUp()
        self.spawn_name = 'spawn'


class ValidateIntegerTestCase(test.NoDBTestCase):
    def test_exception_converted(self):
        self.assertRaises(exception.InvalidInput,
                          utils.validate_integer,
                          "im-not-an-int", "not-an-int")
        self.assertRaises(exception.InvalidInput,
                          utils.validate_integer,
                          3.14, "Pie")
        self.assertRaises(exception.InvalidInput,
                          utils.validate_integer,
                          "299", "Sparta no-show",
                          min_value=300, max_value=300)
        self.assertRaises(exception.InvalidInput,
                          utils.validate_integer,
                          55, "doing 55 in a 54",
                          max_value=54)
        self.assertRaises(exception.InvalidInput,
                          utils.validate_integer,
                          chr(129), "UnicodeError",
                          max_value=1000)
