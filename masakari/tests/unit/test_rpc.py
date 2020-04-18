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

import copy
from unittest import mock

import fixtures
import oslo_messaging as messaging
from oslo_messaging.rpc import dispatcher
from oslo_serialization import jsonutils
import testtools

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
        access_policy = dispatcher.DefaultRPCAccessPolicy

        server = rpc.get_server(tgt, ends, serializer='foo')

        mock_ser.assert_called_once_with('foo')
        mock_get.assert_called_once_with(rpc.TRANSPORT, tgt, ends,
                                         executor='eventlet', serializer=ser,
                                         access_policy=access_policy)
        self.assertEqual('server', server)


class RPCResetFixture(fixtures.Fixture):
    def _setUp(self):
        self.trans = copy.copy(rpc.TRANSPORT)
        self.noti_trans = copy.copy(rpc.NOTIFICATION_TRANSPORT)
        self.noti = copy.copy(rpc.NOTIFIER)
        self.all_mods = copy.copy(rpc.ALLOWED_EXMODS)
        self.ext_mods = copy.copy(rpc.EXTRA_EXMODS)
        self.addCleanup(self._reset_everything)

    def _reset_everything(self):
        rpc.TRANSPORT = self.trans
        rpc.NOTIFICATION_TRANSPORT = self.noti_trans
        rpc.NOTIFIER = self.noti
        rpc.ALLOWED_EXMODS = self.all_mods
        rpc.EXTRA_EXMODS = self.ext_mods


class TestRPC(testtools.TestCase):
    def setUp(self):
        super(TestRPC, self).setUp()
        self.useFixture(RPCResetFixture())

    @mock.patch.object(rpc, 'get_allowed_exmods')
    @mock.patch.object(rpc, 'RequestContextSerializer')
    @mock.patch.object(messaging, 'get_notification_transport')
    @mock.patch.object(messaging, 'Notifier')
    def test_init_versioned(self, mock_notif, mock_noti_trans,
                            mock_ser, mock_exmods):
        expected = [{'topics': ['versioned_notifications']}]
        self._test_init(mock_notif, mock_noti_trans, mock_ser,
                        mock_exmods, 'versioned', expected)

    def test_cleanup_transport_null(self):
        rpc.TRANSPORT = None
        rpc.NOTIFICATION_TRANSPORT = mock.Mock()
        rpc.NOTIFIER = mock.Mock()
        self.assertRaises(AssertionError, rpc.cleanup)

    def test_cleanup_notification_transport_null(self):
        rpc.TRANSPORT = mock.Mock()
        rpc.NOTIFICATION_TRANSPORT = None
        rpc.NOTIFIER = mock.Mock()
        self.assertRaises(AssertionError, rpc.cleanup)

    def test_cleanup_notifier_null(self):
        rpc.TRANSPORT = mock.Mock()
        rpc.NOTIFICATION_TRANSPORT = mock.Mock()
        rpc.NOTIFIER = None
        self.assertRaises(AssertionError, rpc.cleanup)

    def test_cleanup(self):
        rpc.NOTIFIER = mock.Mock()
        rpc.NOTIFICATION_TRANSPORT = mock.Mock()
        rpc.TRANSPORT = mock.Mock()
        trans_cleanup = mock.Mock()
        not_trans_cleanup = mock.Mock()
        rpc.TRANSPORT.cleanup = trans_cleanup
        rpc.NOTIFICATION_TRANSPORT.cleanup = not_trans_cleanup

        rpc.cleanup()

        trans_cleanup.assert_called_once_with()
        not_trans_cleanup.assert_called_once_with()
        self.assertIsNone(rpc.TRANSPORT)
        self.assertIsNone(rpc.NOTIFICATION_TRANSPORT)
        self.assertIsNone(rpc.NOTIFIER)

    def test_get_versioned_notifier(self):
        rpc.NOTIFIER = mock.Mock()
        mock_prep = mock.Mock()
        mock_prep.return_value = 'notifier'
        rpc.NOTIFIER.prepare = mock_prep

        notifier = rpc.get_versioned_notifier('service.foo')

        mock_prep.assert_called_once_with(publisher_id='service.foo')
        self.assertEqual('notifier', notifier)

    def _test_init(self, mock_notif, mock_noti_trans, mock_ser,
                   mock_exmods, notif_format, expected_driver_topic_kwargs,
                   versioned_notification_topics=['versioned_notifications']):
        notifier = mock.Mock()
        notif_transport = mock.Mock()
        transport = mock.Mock()
        serializer = mock.Mock()
        conf = mock.Mock()

        conf.transport_url = None
        conf.notification_format = notif_format
        mock_exmods.return_value = ['foo']
        conf.notifications.versioned_notifications_topics = (
            versioned_notification_topics)
        mock_noti_trans.return_value = notif_transport
        mock_ser.return_value = serializer
        mock_notif.side_effect = [notifier]

        @mock.patch.object(rpc, 'CONF', new=conf)
        @mock.patch.object(rpc, 'create_transport')
        @mock.patch.object(rpc, 'get_transport_url')
        def _test(get_url, create_transport):
            create_transport.return_value = transport
            rpc.init(conf)
            create_transport.assert_called_once_with(get_url.return_value)

        _test()

        self.assertTrue(mock_exmods.called)
        self.assertIsNotNone(rpc.TRANSPORT)
        self.assertIsNotNone(rpc.NOTIFIER)
        self.assertEqual(notifier, rpc.NOTIFIER)

        expected_calls = []
        for kwargs in expected_driver_topic_kwargs:
            expected_kwargs = {'serializer': serializer}
            expected_kwargs.update(kwargs)
            expected_calls.append(((notif_transport,), expected_kwargs))

        self.assertEqual(expected_calls, mock_notif.call_args_list,
                         "The calls to messaging.Notifier() did not create "
                         "the versioned notifiers properly.")


class TestJsonPayloadSerializer(test.NoDBTestCase):
    def test_serialize_entity(self):
        with mock.patch.object(jsonutils, 'to_primitive') as mock_prim:
            rpc.JsonPayloadSerializer.serialize_entity('context', 'entity')

        mock_prim.assert_called_once_with('entity', convert_instances=True)


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
