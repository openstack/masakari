# Copyright 2016 NTT Data
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

"""Base classes for our unit tests.

Allows overriding of flags for use of fakes, and some black magic for
inline callbacks.

"""
import contextlib
import datetime
import eventlet
eventlet.monkey_patch(os=False)  # noqa
from unittest import mock

import fixtures

import testtools

from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils

from masakari.tests import fixtures as masakari_fixtures
from masakari.tests.unit import conf_fixture
from masakari.tests.unit import policy_fixture

CONF = cfg.CONF
logging.register_options(CONF)
CONF.set_override('use_stderr', False)
logging.setup(CONF, 'masakari')


@contextlib.contextmanager
def nested(*contexts):
    with contextlib.ExitStack() as stack:
        yield [stack.enter_context(c) for c in contexts]


def _patch_mock_to_raise_for_invalid_assert_calls():
    def raise_for_invalid_assert_calls(wrapped):
        def wrapper(_self, name):
            valid_asserts = [
                'assert_called_with',
                'assert_called_once_with',
                'assert_has_calls',
                'assert_any_calls']

            if name.startswith('assert') and name not in valid_asserts:
                raise AttributeError('%s is not a valid mock assert method'
                                     % name)

            return wrapped(_self, name)
        return wrapper
    mock.Mock.__getattr__ = raise_for_invalid_assert_calls(
        mock.Mock.__getattr__)


# NOTE(abhishekk): needs to be called only once at import time
# to patch the mock lib
_patch_mock_to_raise_for_invalid_assert_calls()


class TestCase(testtools.TestCase):
    """Test case base class for all unit tests.

    Due to the slowness of DB access, please consider deriving from
    `NoDBTestCase` first.
    """
    USES_DB = True

    def setUp(self):
        """Run before each test method to initialize test environment."""
        super(TestCase, self).setUp()

        self.useFixture(conf_fixture.ConfFixture(CONF))
        self.policy = self.useFixture(policy_fixture.PolicyFixture())

        if self.USES_DB:
            self.useFixture(masakari_fixtures.Database())
        else:
            self.useFixture(masakari_fixtures.DatabasePoisonFixture())

    def stub_out(self, old, new):
        """Replace a function for the duration of the test.

        Use the monkey patch fixture to replace a function for the
        duration of a test. Useful when you want to provide fake
        methods instead of mocks during testing.

        This should be used instead of self.stubs.Set (which is based
        on mox) going forward.
        """
        self.useFixture(fixtures.MonkeyPatch(old, new))

    def override_config(self, name, override, group=None):
        """Cleanly override CONF variables."""
        CONF.set_override(name, override, group)
        self.addCleanup(CONF.clear_override, name, group)

    def flags(self, **kw):
        """Override flag variables for a test."""
        group = kw.pop('group', None)
        for k, v in kw.items():
            CONF.set_override(k, v, group)

    def assertJsonEqual(self, expected, observed):
        """Asserts that 2 complex data structures are json equivalent.

        We use data structures which serialize down to json throughout
        the code, and often times we just need to know that these are
        json equivalent. This means that list order is not important,
        and should be sorted.

        Because this is a recursive set of assertions, when failure
        happens we want to expose both the local failure and the
        global view of the 2 data structures being compared. So a
        MismatchError which includes the inner failure as the
        mismatch, and the passed in expected / observed as matchee /
        matcher.

        """
        if isinstance(expected, str):
            expected = jsonutils.loads(expected)
        if isinstance(observed, str):
            observed = jsonutils.loads(observed)

        def sort_key(x):
            if isinstance(x, (set, list)) or isinstance(x, datetime.datetime):
                return str(x)
            if isinstance(x, dict):
                items = ((sort_key(key), sort_key(value))
                         for key, value in x.items())
                return sorted(items)
            return x

        def inner(expected, observed):
            if isinstance(expected, dict) and isinstance(observed, dict):
                self.assertEqual(len(expected), len(observed))
                expected_keys = sorted(expected)
                observed_keys = sorted(observed)
                self.assertEqual(expected_keys, observed_keys)

                for key in expected:
                    inner(expected[key], observed[key])
            elif (isinstance(expected, (list, tuple, set)) and isinstance(
                    observed, (list, tuple, set))):
                self.assertEqual(len(expected), len(observed))

                expected_values_iter = iter(sorted(expected, key=sort_key))
                observed_values_iter = iter(sorted(observed, key=sort_key))

                for i in range(len(expected)):
                    inner(next(expected_values_iter),
                          next(observed_values_iter))
            else:
                self.assertEqual(expected, observed)

        try:
            inner(expected, observed)
        except testtools.matchers.MismatchError as e:
            inner_mismatch = e.mismatch
            # inverting the observed / expected because testtools
            # error messages assume expected is second. Possibly makes
            # reading the error messages less confusing.
            raise testtools.matchers.MismatchError(observed, expected,
                                                   inner_mismatch,
                                                   verbose=True)

    def assertObjEqual(self, expect, actual):
        actual.obj_reset_changes(recursive=True)
        expect.obj_reset_changes(recursive=True)
        self.assertEqual(expect.obj_to_primitive(),
                         actual.obj_to_primitive())

    def assertObjectList(self, expected, actual):
        self.assertEqual(len(expected), len(actual))
        for d1, d2 in zip(expected, actual):
            self.assertObjEqual(d1, d2)


class NoDBTestCase(TestCase):
    """`NoDBTestCase` differs from TestCase in that DB access is not supported.
    This makes tests run significantly faster. If possible, all new tests
    should derive from this class.
    """
    USES_DB = False
