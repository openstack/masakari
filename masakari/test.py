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

import eventlet
eventlet.monkey_patch(os=False)

import fixtures
import mock

import six
import testtools

from oslo_config import cfg
from oslo_log import log as logging
from oslotest import moxstubout

from masakari.tests.unit import conf_fixture
from masakari.tests.unit import policy_fixture

CONF = cfg.CONF
logging.register_options(CONF)
CONF.set_override('use_stderr', False)
logging.setup(CONF, 'masakari')


if six.PY2:
    nested = contextlib.nested
else:
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
        mox_fixture = self.useFixture(moxstubout.MoxStubout())
        self.mox = mox_fixture.mox
        self.stubs = mox_fixture.stubs
        self.policy = self.useFixture(policy_fixture.PolicyFixture())

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
        for k, v in six.iteritems(kw):
            CONF.set_override(k, v, group)


class NoDBTestCase(TestCase):
    """`NoDBTestCase` differs from TestCase in that DB access is not supported.
    This makes tests run significantly faster. If possible, all new tests
    should derive from this class.
    """
    USES_DB = False
