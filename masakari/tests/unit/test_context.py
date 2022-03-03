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

from oslo_context import context as o_context
from oslo_context import fixture as o_fixture

from masakari import context
from masakari import test


class ContextTestCase(test.NoDBTestCase):

    def setUp(self):
        super(ContextTestCase, self).setUp()
        self.useFixture(o_fixture.ClearRequestContext())

    def test_request_context_elevated(self):
        user_ctxt = context.RequestContext('111',
                                           '222',
                                           is_admin=False)
        self.assertFalse(user_ctxt.is_admin)
        admin_ctxt = user_ctxt.elevated()
        self.assertTrue(admin_ctxt.is_admin)
        self.assertIn('admin', admin_ctxt.roles)
        self.assertFalse(user_ctxt.is_admin)
        self.assertNotIn('admin', user_ctxt.roles)

    def test_request_context_sets_is_admin(self):
        ctxt = context.RequestContext('111',
                                      '222',
                                      roles=['admin', 'weasel'])
        self.assertTrue(ctxt.is_admin)

    def test_request_context_sets_is_admin_upcase(self):
        ctxt = context.RequestContext('111',
                                      '222',
                                      roles=['Admin', 'weasel'])
        self.assertTrue(ctxt.is_admin)

    def test_request_context_read_deleted(self):
        ctxt = context.RequestContext('111',
                                      '222',
                                      read_deleted='yes')
        self.assertEqual('yes', ctxt.read_deleted)

        ctxt.read_deleted = 'no'
        self.assertEqual('no', ctxt.read_deleted)

    def test_request_context_read_deleted_invalid(self):
        self.assertRaises(ValueError,
                          context.RequestContext,
                          '111',
                          '222',
                          read_deleted=True)

        ctxt = context.RequestContext('111', '222')
        self.assertRaises(ValueError,
                          setattr,
                          ctxt,
                          'read_deleted',
                          True)

    def test_service_catalog_default(self):
        ctxt = context.RequestContext('111', '222')
        self.assertEqual([], ctxt.service_catalog)

        ctxt = context.RequestContext('111', '222',
                service_catalog=[])
        self.assertEqual([], ctxt.service_catalog)

        ctxt = context.RequestContext('111', '222',
                service_catalog=None)
        self.assertEqual([], ctxt.service_catalog)

    def test_store_when_no_overwrite(self):
        # If no context exists we store one even if overwrite is false
        # (since we are not overwriting anything).
        ctx = context.RequestContext('111',
                                     '222',
                                     overwrite=False)
        self.assertIs(o_context.get_current(), ctx)

    def test_no_overwrite(self):
        # If there is already a context in the cache a new one will
        # not overwrite it if overwrite=False.
        ctx1 = context.RequestContext('111',
                                      '222',
                                      overwrite=True)
        context.RequestContext('333',
                               '444',
                               overwrite=False)
        self.assertIs(o_context.get_current(), ctx1)

    def test_admin_no_overwrite(self):
        # If there is already a context in the cache creating an admin
        # context will not overwrite it.
        ctx1 = context.RequestContext('111',
                                      '222',
                                      overwrite=True)
        context.get_admin_context()
        self.assertIs(o_context.get_current(), ctx1)

    def test_convert_from_rc_to_dict(self):
        ctx = context.RequestContext(
            111, 222, request_id='req-679033b7-1755-4929-bf85-eb3bfaef7e0b',
            timestamp='2016-03-02T22:31:56.641629')
        values2 = ctx.to_dict()
        expected_values = {'is_admin': False,
                           'project_id': 222,
                           'project_name': None,
                           'read_deleted': 'no',
                           'remote_address': None,
                           'request_id':
                               'req-679033b7-1755-4929-bf85-eb3bfaef7e0b',
                           'service_catalog': [],
                           'timestamp': '2016-03-02T22:31:56.641629',
                           'user_id': 111,
                           'user_name': None}
        self.assertDictContainsSubset(expected_values, values2)

    def test_convert_from_dict_then_to_dict(self):
        # TODO(tkajiam): Remove tenant once oslo.context is bumped to >= 4.0
        values = {'is_admin': True,
                  'tenant': '222',
                  'project_id': '222',
                  'project_name': 'projname',
                  'read_deleted': 'yes',
                  'remote_address': '192.0.2.1',
                  'request_id': 'req-679033b7-1755-4929-bf85-eb3bfaef7e0b',
                  'service_catalog': [],
                  'timestamp': '2016-03-02T22:31:56.641629',
                  'user': '111',
                  'user_id': '111',
                  'user_name': 'username'}

        ctx = context.RequestContext.from_dict(values)
        self.assertEqual('111', ctx.user)
        self.assertEqual('222', ctx.project_id)
        self.assertEqual('111', ctx.user_id)
        self.assertEqual('222', ctx.project_id)
        values2 = ctx.to_dict()
        # TODO(tkajiam): Remove this once oslo.context is bumped to >= 4.0
        values2.setdefault('tenant', values2.get('project_id'))
        self.assertDictContainsSubset(values, values2)
