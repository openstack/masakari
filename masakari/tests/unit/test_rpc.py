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

import mock
import oslo_messaging as messaging

from masakari import context
from masakari import rpc
from masakari import test


class FakeAPI(rpc.RPCAPI):
    RPC_API_VERSION = '1.0'
    TOPIC = 'engine'
    BINARY = 'masakari-engine'


class RPCAPITestCase(test.TestCase):
    """Tests RPCAPI mixin aggregating stuff related to RPC compatibility."""

    def setUp(self):
        super(RPCAPITestCase, self).setUp()

    @mock.patch('masakari.rpc.get_client')
    def test_init(self, get_client):
        def fake_get_client(target, version_cap=None, serializer=None):
            self.assertEqual(FakeAPI.TOPIC, target.topic)
            self.assertEqual(FakeAPI.RPC_API_VERSION, target.version)

        get_client.side_effect = fake_get_client
        FakeAPI()

    @mock.patch('masakari.rpc.get_client')
    def test_init_cached_caps(self, get_client):
        def fake_get_client(target, version_cap=None, serializer=None):
            self.assertEqual(FakeAPI.TOPIC, target.topic)
            self.assertEqual(FakeAPI.RPC_API_VERSION, target.version)

        get_client.side_effect = fake_get_client
        FakeAPI()

    @mock.patch.object(messaging, 'set_transport_defaults')
    def test_set_defaults(self, mock_set):
        control_exchange = mock.Mock()

        rpc.set_defaults(control_exchange)

        mock_set.assert_called_once_with(control_exchange)

    def test_add_extra_exmods(self):
        rpc.EXTRA_EXMODS = []

        rpc.add_extra_exmods('foo', 'bar')

        self.assertEqual(['foo', 'bar'], rpc.EXTRA_EXMODS)

    def test_clear_extra_exmods(self):
        rpc.EXTRA_EXMODS = ['foo', 'bar']

        rpc.clear_extra_exmods()

        self.assertEqual(0, len(rpc.EXTRA_EXMODS))

    def test_get_allowed_exmods(self):
        rpc.ALLOWED_EXMODS = ['foo']
        rpc.EXTRA_EXMODS = ['bar']

        exmods = rpc.get_allowed_exmods()

        self.assertEqual(['foo', 'bar'], exmods)

    @mock.patch.object(rpc, 'RequestContextSerializer')
    @mock.patch.object(messaging, 'RPCClient')
    def test_get_client(self, mock_client, mock_ser):
        rpc.TRANSPORT = mock.Mock()
        tgt = mock.Mock()
        ser = mock.Mock()
        mock_client.return_value = 'client'
        mock_ser.return_value = ser

        client = rpc.get_client(tgt, version_cap='1.0', serializer='foo')

        mock_ser.assert_called_once_with('foo')
        mock_client.assert_called_once_with(rpc.TRANSPORT,
                                            tgt, version_cap='1.0',
                                            serializer=ser)
        self.assertEqual('client', client)

    @mock.patch.object(rpc, 'RequestContextSerializer')
    @mock.patch.object(messaging, 'get_rpc_server')
    def test_get_server(self, mock_get, mock_ser):
        rpc.TRANSPORT = mock.Mock()
        ser = mock.Mock()
        tgt = mock.Mock()
        ends = mock.Mock()
        mock_ser.return_value = ser
        mock_get.return_value = 'server'

        server = rpc.get_server(tgt, ends, serializer='foo')

        mock_ser.assert_called_once_with('foo')
        mock_get.assert_called_once_with(rpc.TRANSPORT, tgt, ends,
                                         executor='eventlet', serializer=ser)
        self.assertEqual('server', server)


class TestRequestContextSerializer(test.NoDBTestCase):
    def setUp(self):
        super(TestRequestContextSerializer, self).setUp()
        self.mock_base = mock.Mock()
        self.ser = rpc.RequestContextSerializer(self.mock_base)
        self.ser_null = rpc.RequestContextSerializer(None)

    def test_serialize_entity(self):
        self.mock_base.serialize_entity.return_value = 'foo'

        ser_ent = self.ser.serialize_entity('context', 'entity')

        self.mock_base.serialize_entity.assert_called_once_with('context',
                                                                'entity')
        self.assertEqual('foo', ser_ent)

    def test_serialize_entity_null_base(self):
        ser_ent = self.ser_null.serialize_entity('context', 'entity')

        self.assertEqual('entity', ser_ent)

    def test_deserialize_entity(self):
        self.mock_base.deserialize_entity.return_value = 'foo'

        deser_ent = self.ser.deserialize_entity('context', 'entity')

        self.mock_base.deserialize_entity.assert_called_once_with('context',
                                                                  'entity')
        self.assertEqual('foo', deser_ent)

    def test_deserialize_entity_null_base(self):
        deser_ent = self.ser_null.deserialize_entity('context', 'entity')

        self.assertEqual('entity', deser_ent)

    def test_serialize_context(self):
        context = mock.Mock()

        self.ser.serialize_context(context)

        context.to_dict.assert_called_once_with()

    @mock.patch.object(context, 'RequestContext')
    def test_deserialize_context(self, mock_req):
        self.ser.deserialize_context('context')

        mock_req.from_dict.assert_called_once_with('context')
