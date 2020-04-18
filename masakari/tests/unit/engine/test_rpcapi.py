#    Copyright (c) 2016 NTT DATA
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

"""
Unit Tests for masakari.engine.rpcapi
"""

import copy
from unittest import mock


from masakari import context
from masakari.engine import rpcapi as engine_rpcapi
from masakari import objects
from masakari import test
from masakari.tests.unit.engine import fake_engine


class EngineRpcAPITestCase(test.TestCase):
    def setUp(self):
        super(EngineRpcAPITestCase, self).setUp()
        self.context = context.RequestContext()
        self.fake_notification_obj = fake_engine.fake_notification_obj(
            self.context)

    def _test_engine_api(self, method, rpc_method, server=None, fanout=False,
                         **kwargs):
        rpcapi = engine_rpcapi.EngineAPI()
        expected_retval = 'foo' if rpc_method == 'call' else None

        target = {
            "server": server,
            "fanout": fanout,
            "version": kwargs.pop('version', rpcapi.RPC_API_VERSION)
        }

        expected_msg = copy.deepcopy(kwargs)

        self.fake_args = None
        self.fake_kwargs = None

        def _fake_prepare_method(*args, **kwds):
            for kwd in kwds:
                self.assertEqual(target[kwd], kwds[kwd])
            return rpcapi.client

        def _fake_rpc_method(*args, **kwargs):
            self.fake_args = args
            self.fake_kwargs = kwargs
            if expected_retval:
                return expected_retval

        with mock.patch.object(rpcapi.client, "prepare") as mock_prepared:
            mock_prepared.side_effect = _fake_prepare_method

            with mock.patch.object(rpcapi.client, rpc_method) as mock_method:
                mock_method.side_effect = _fake_rpc_method
                retval = getattr(rpcapi, method)(self.context, **kwargs)
                self.assertEqual(expected_retval, retval)
                expected_args = [self.context, method, expected_msg]
                for arg, expected_arg in zip(self.fake_args, expected_args):
                    self.assertEqual(expected_arg, arg)

                for kwarg, value in self.fake_kwargs.items():
                    if isinstance(value, objects.Notification):
                        expected_back = expected_msg[kwarg].obj_to_primitive()
                        backup = value.obj_to_primitive()
                        self.assertEqual(expected_back, backup)
                    else:
                        self.assertEqual(expected_msg[kwarg], value)

    @mock.patch("masakari.rpc.get_client")
    def test_process_notification(self, mock_get_client):
        self._test_engine_api('process_notification',
                              rpc_method='cast',
                              notification=self.fake_notification_obj,
                              version='1.0')

    @mock.patch("masakari.rpc.get_client")
    def test_get_notification_recovery_workflow_details(self,
                                                        mock_get_client):
        self._test_engine_api('get_notification_recovery_workflow_details',
                              rpc_method='call',
                              notification=self.fake_notification_obj,
                              version='1.1')
