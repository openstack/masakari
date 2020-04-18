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

"""
Unit Tests for remote procedure calls using queue
"""

from unittest import mock

from oslo_concurrency import processutils
from oslo_config import cfg
from oslo_service import service as _service

from masakari import exception
from masakari import manager
from masakari import rpc
from masakari import service
from masakari import test

CONF = cfg.CONF


class FakeManager(manager.Manager):
    """Fake manager for tests."""
    def test_method(self):
        return 'manager'


class ServiceManagerTestCase(test.NoDBTestCase):
    """Test cases for Services."""

    @mock.patch.object(rpc, 'init')
    def test_message_gets_to_manager(self, mock_rpc_init):
        serv = service.Service('test',
                               'test',
                               'test',
                               'masakari.tests.unit.test_service.FakeManager')
        self.assertEqual('manager', serv.test_method())


class ServiceTestCase(test.NoDBTestCase):
    """Test cases for Services."""

    def setUp(self):
        super(ServiceTestCase, self).setUp()
        self.host = 'foo'
        self.binary = 'masakari-engine'
        self.topic = 'fake'

    @mock.patch.object(rpc, 'init')
    def test_create(self, mock_rpc_init):

        app = service.Service.create(host=self.host, binary=self.binary,
                topic=self.topic)

        self.assertTrue(app)

    @mock.patch.object(rpc, 'init')
    def test_repr(self, mock_rpc_init):
        # Test if a Service object is correctly represented, for example in
        # log files.
        serv = service.Service(self.host,
                               self.binary,
                               self.topic,
                               'masakari.tests.unit.test_service.FakeManager')
        exp = "<Service: host=foo, binary=masakari-engine, " \
              "manager_class_name=masakari.tests.unit." \
              "test_service.FakeManager>"
        self.assertEqual(exp, repr(serv))

    @mock.patch.object(_service.Service, 'stop')
    @mock.patch.object(rpc, 'init')
    @mock.patch.object(rpc, 'get_server')
    def test_parent_graceful_shutdown(self, mock_rpc, mock_rpc_init,
                                      mock_stop):
        serv = service.Service(self.host,
                               self.binary,
                               self.topic,
                               'masakari.tests.unit.test_service.FakeManager')

        serv.manager = mock.Mock()
        serv.manager.service_name = self.topic

        serv.start()

        serv.stop()

        serv.rpcserver.start.assert_called_once_with()
        serv.rpcserver.stop.assert_called_once_with()
        mock_stop.assert_called_once_with()

    @mock.patch.object(rpc, 'init')
    def test_reset(self, mock_rpc_init):
        serv = service.Service(self.host,
                               self.binary,
                               self.topic,
                               'masakari.tests.unit.test_service.FakeManager')
        with mock.patch.object(serv.manager, 'reset') as mock_reset:
            serv.reset()
            mock_reset.assert_called_once_with()


class TestWSGIService(test.NoDBTestCase):

    def setUp(self):
        super(TestWSGIService, self).setUp()
        self.stub_out('masakari.wsgi.Loader.load_app', mock.MagicMock())

    def test_workers_set_default(self):
        test_service = service.WSGIService("masakari_api")
        self.assertEqual(test_service.workers, processutils.get_worker_count())

    def test_workers_set_good_user_setting(self):
        CONF.set_override('masakari_api_workers', 8)
        test_service = service.WSGIService("masakari_api")
        self.assertEqual(test_service.workers, 8)

    def test_workers_set_zero_user_setting(self):
        CONF.set_override('masakari_api_workers', 0)
        test_service = service.WSGIService("masakari_api")
        # If a value less than 1 is used, defaults to number of procs available
        self.assertEqual(test_service.workers, processutils.get_worker_count())

    def test_service_start_with_illegal_workers(self):
        CONF.set_override("masakari_api_workers", -1)
        self.assertRaises(exception.InvalidInput,
                          service.WSGIService, "masakari_api")

    def test_reset_pool_size_to_default(self):
        test_service = service.WSGIService("test_service")
        test_service.start()

        # Stopping the service, which in turn sets pool size to 0
        test_service.stop()
        self.assertEqual(test_service.server._pool.size, 0)

        # Resetting pool size to default
        test_service.reset()
        test_service.start()
        self.assertEqual(test_service.server._pool.size,
                         CONF.wsgi.default_pool_size)


class TestLauncher(test.NoDBTestCase):

    @mock.patch.object(_service, 'launch')
    def test_launch_app(self, mock_launch):
        service._launcher = None
        service.serve(mock.sentinel.service)
        mock_launch.assert_called_once_with(mock.ANY,
                                            mock.sentinel.service,
                                            workers=None,
                                            restart_method='mutate')

    @mock.patch.object(_service, 'launch')
    def test_launch_app_with_workers(self, mock_launch):
        service._launcher = None
        service.serve(mock.sentinel.service, workers=mock.sentinel.workers)
        mock_launch.assert_called_once_with(mock.ANY,
                                            mock.sentinel.service,
                                            workers=mock.sentinel.workers,
                                            restart_method='mutate')

    @mock.patch.object(_service, 'launch')
    def test_launch_app_more_than_once_raises(self, mock_launch):
        service._launcher = None
        service.serve(mock.sentinel.service)
        self.assertRaises(RuntimeError, service.serve, mock.sentinel.service)
