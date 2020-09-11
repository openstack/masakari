# Copyright 2016 NTT DATA
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os
import yaml

import fixtures
from oslo_policy import policy as oslo_policy

import masakari.conf
from masakari.conf import paths
from masakari import policies
import masakari.policy
from masakari.tests.unit import fake_policy

CONF = masakari.conf.CONF


class RealPolicyFixture(fixtures.Fixture):
    """Load the live policy for tests.

    A base policy fixture that starts with the assumption that you'd
    like to load and enforce the shipped default policy in tests.

    Provides interfaces to tinker with both the contents and location
    of the policy file before loading to allow overrides. To do this
    implement ``_prepare_policy`` in the subclass, and adjust the
    ``policy_file`` accordingly.

    """
    def _prepare_policy(self):
        """Allow changing of the policy before we get started"""
        pass

    def setUp(self):
        super(RealPolicyFixture, self).setUp()
        # policy_file can be overridden by subclasses
        self.policy_file = paths.state_path_def('etc/masakari/policy.yaml')
        self._prepare_policy()
        CONF.set_override('policy_file', self.policy_file, group='oslo_policy')
        masakari.policy.reset()
        masakari.policy.init(suppress_deprecation_warnings=True)
        self.addCleanup(masakari.policy.reset)

    def set_rules(self, rules, overwrite=True):
        policy = masakari.policy._ENFORCER
        policy.set_rules(oslo_policy.Rules.from_dict(rules),
                         overwrite=overwrite)


class PolicyFixture(RealPolicyFixture):
    """Load a fake policy from masakari.tests.unit.fake_policy

    This overrides the policy with a completely fake and synthetic
    policy file.

    """
    def _prepare_policy(self):
        self.policy_dir = self.useFixture(fixtures.TempDir())
        self.policy_file = os.path.join(self.policy_dir.path, 'policy.yaml')

        # load the fake_policy data and add the missing default rules.
        policy_rules = yaml.safe_load(fake_policy.policy_data)

        with open(self.policy_file, 'w') as f:
            yaml.dump(policy_rules, f)
        CONF.set_override('policy_dirs', [], group='oslo_policy')


class RoleBasedPolicyFixture(RealPolicyFixture):
    """Load a modified policy which allows all actions only be a single roll.

    This fixture can be used for testing role based permissions as it
    provides a version of the policy which stomps over all previous
    declaration and makes every action only available to a single
    role.

    """

    def __init__(self, role="admin", *args, **kwargs):
        super(RoleBasedPolicyFixture, self).__init__(*args, **kwargs)
        self.role = role

    def _prepare_policy(self):
        # Convert all actions to require the specified role
        policy = {}
        for rule in policies.list_rules():
            policy[rule.name] = 'role:%s' % self.role

        self.policy_dir = self.useFixture(fixtures.TempDir())
        self.policy_file = os.path.join(self.policy_dir.path, 'policy.yaml')
        with open(self.policy_file, 'w') as f:
            yaml.dump(policy, f)
