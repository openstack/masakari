# Copyright 2016 NTT DATA
# All Rights Reserved.

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

"""Test of Policy Engine For Masakari."""

import os.path

from oslo_policy import policy as oslo_policy
from oslo_serialization import jsonutils
import requests_mock

import masakari.conf
from masakari import context
from masakari import exception
from masakari import policy
from masakari import test
from masakari.tests.unit import fake_policy
from masakari.tests.unit import policy_fixture
from masakari import utils

CONF = masakari.conf.CONF


class PolicyFileTestCase(test.NoDBTestCase):
    def setUp(self):
        super(PolicyFileTestCase, self).setUp()
        self.context = context.RequestContext('fake', 'fake')
        self.target = {}

    def test_modified_policy_reloads(self):
        with utils.tempdir() as tmpdir:
            tmpfilename = os.path.join(tmpdir, 'policy')

            self.flags(policy_file=tmpfilename, group='oslo_policy')

            # NOTE(Dinesh_Bhor): context construction invokes policy check to
            # determine is_admin or not. As a side-effect, policy reset is
            # needed here to flush existing policy cache.
            policy.reset()
            policy.init(suppress_deprecation_warnings=True)
            rule = oslo_policy.RuleDefault('example:test', "")
            policy._ENFORCER.register_defaults([rule])

            action = "example:test"
            with open(tmpfilename, "w") as policyfile:
                policyfile.write('{"example:test": ""}')
            policy.authorize(self.context, action, self.target)
            with open(tmpfilename, "w") as policyfile:
                policyfile.write('{"example:test": "!"}')
            policy._ENFORCER.load_rules(True)
            self.assertRaises(exception.PolicyNotAuthorized, policy.authorize,
                              self.context, action, self.target)


class PolicyTestCase(test.NoDBTestCase):
    def setUp(self):
        super(PolicyTestCase, self).setUp()
        rules = [
            oslo_policy.RuleDefault("true", '@'),
            oslo_policy.RuleDefault("example:allowed", '@'),
            oslo_policy.RuleDefault("example:denied", "!"),
            oslo_policy.RuleDefault("example:get_http",
                                    "http://www.example.com"),
            oslo_policy.RuleDefault("example:my_file",
                                    "role:compute_admin or "
                                    "project_id:%(project_id)s"),
            oslo_policy.RuleDefault("example:early_and_fail", "! and @"),
            oslo_policy.RuleDefault("example:early_or_success", "@ or !"),
            oslo_policy.RuleDefault("example:lowercase_admin",
                                    "role:admin or role:sysadmin"),
            oslo_policy.RuleDefault("example:uppercase_admin",
                                    "role:ADMIN or role:sysadmin"),
        ]
        policy.reset()
        policy.init(suppress_deprecation_warnings=True)
        # before a policy rule can be used, its default has to be registered.
        policy._ENFORCER.register_defaults(rules)
        self.context = context.RequestContext('fake', 'fake', roles=['member'])
        self.target = {}

    def test_authorize_nonexistent_action_throws(self):
        action = "example:noexist"
        self.assertRaises(oslo_policy.PolicyNotRegistered, policy.authorize,
                          self.context, action, self.target)

    def test_authorize_bad_action_throws(self):
        action = "example:denied"
        self.assertRaises(exception.PolicyNotAuthorized, policy.authorize,
                          self.context, action, self.target)

    def test_authorize_bad_action_noraise(self):
        action = "example:denied"
        result = policy.authorize(self.context, action, self.target, False)
        self.assertFalse(result)

    def test_authorize_good_action(self):
        action = "example:allowed"
        result = policy.authorize(self.context, action, self.target)
        self.assertTrue(result)

    @requests_mock.mock()
    def test_authorize_http_true(self, req_mock):
        req_mock.post('http://www.example.com/',
                      text='True')
        action = "example:get_http"
        target = {}
        result = policy.authorize(self.context, action, target)
        self.assertTrue(result)

    @requests_mock.mock()
    def test_authorize_http_false(self, req_mock):
        req_mock.post('http://www.example.com/',
                      text='False')
        action = "example:get_http"
        target = {}
        self.assertRaises(exception.PolicyNotAuthorized, policy.authorize,
                          self.context, action, target)

    def test_templatized_authorization(self):
        target_mine = {'project_id': 'fake'}
        target_not_mine = {'project_id': 'another'}
        action = "example:my_file"
        policy.authorize(self.context, action, target_mine)
        self.assertRaises(exception.PolicyNotAuthorized, policy.authorize,
                          self.context, action, target_not_mine)

    def test_early_AND_authorization(self):
        action = "example:early_and_fail"
        self.assertRaises(exception.PolicyNotAuthorized, policy.authorize,
                          self.context, action, self.target)

    def test_early_OR_authorization(self):
        action = "example:early_or_success"
        policy.authorize(self.context, action, self.target)

    def test_ignore_case_role_check(self):
        lowercase_action = "example:lowercase_admin"
        uppercase_action = "example:uppercase_admin"
        admin_context = context.RequestContext('admin',
                                               'fake',
                                               roles=['AdMiN'])
        policy.authorize(admin_context, lowercase_action, self.target)
        policy.authorize(admin_context, uppercase_action, self.target)


class IsAdminCheckTestCase(test.NoDBTestCase):
    def setUp(self):
        super(IsAdminCheckTestCase, self).setUp()
        policy.init(suppress_deprecation_warnings=True)

    def test_init_true(self):
        check = policy.IsAdminCheck('is_admin', 'True')

        self.assertEqual(check.kind, 'is_admin')
        self.assertEqual(check.match, 'True')
        self.assertTrue(check.expected)

    def test_init_false(self):
        check = policy.IsAdminCheck('is_admin', 'nottrue')

        self.assertEqual(check.kind, 'is_admin')
        self.assertEqual(check.match, 'False')
        self.assertFalse(check.expected)

    def test_call_true(self):
        check = policy.IsAdminCheck('is_admin', 'True')

        self.assertEqual(check('target', dict(is_admin=True),
                               policy._ENFORCER), True)
        self.assertEqual(check('target', dict(is_admin=False),
                               policy._ENFORCER), False)

    def test_call_false(self):
        check = policy.IsAdminCheck('is_admin', 'False')

        self.assertEqual(check('target', dict(is_admin=True),
                               policy._ENFORCER), False)
        self.assertEqual(check('target', dict(is_admin=False),
                               policy._ENFORCER), True)


class AdminRolePolicyTestCase(test.NoDBTestCase):
    def setUp(self):
        super(AdminRolePolicyTestCase, self).setUp()
        self.policy = self.useFixture(policy_fixture.RoleBasedPolicyFixture())
        self.context = context.RequestContext('fake', 'fake', roles=['member'])
        self.actions = policy.get_rules().keys()
        self.target = {}

    def test_authorize_admin_actions_with_nonadmin_context_throws(self):
        """Check if non-admin context passed to admin actions throws
           Policy not authorized exception
        """
        for action in self.actions:
            self.assertRaises(exception.PolicyNotAuthorized, policy.authorize,
                          self.context, action, self.target)


class RealRolePolicyTestCase(test.NoDBTestCase):
    def setUp(self):
        super(RealRolePolicyTestCase, self).setUp()
        self.policy = self.useFixture(policy_fixture.RealPolicyFixture())
        self.admin_context = context.RequestContext('fake', 'fake', True,
                                                    roles=['member'])
        self.non_admin_context = context.RequestContext('fake', 'fake',
                                                        roles=['member'])
        self.target = {}
        self.fake_policy = jsonutils.loads(fake_policy.policy_data)

        self.admin_only_rules = (
            "os_masakari_api:extensions:index",
            "os_masakari_api:extensions:detail",
            "os_masakari_api:os-hosts:index",
            "os_masakari_api:os-hosts:detail",
            "os_masakari_api:os-hosts:create",
            "os_masakari_api:os-hosts:update",
            "os_masakari_api:os-hosts:delete",
            "os_masakari_api:segments:index",
            "os_masakari_api:segments:detail",
            "os_masakari_api:segments:create",
            "os_masakari_api:segments:update",
            "os_masakari_api:segments:delete",
            "os_masakari_api:notifications:index",
            "os_masakari_api:notifications:detail",
            "os_masakari_api:notifications:create"
        )

    def test_all_rules_in_sample_file(self):
        special_rules = ["context_is_admin", "admin_or_owner", "default"]
        for (name, rule) in self.fake_policy.items():
            if name in special_rules:
                continue
            self.assertIn(name, policy.get_rules())

    def test_admin_only_rules(self):
        for rule in self.admin_only_rules:
            self.assertRaises(exception.PolicyNotAuthorized, policy.authorize,
                              self.non_admin_context, rule,
                              {'project_id': 'fake', 'user_id': 'fake'})
            policy.authorize(self.admin_context, rule, self.target)
