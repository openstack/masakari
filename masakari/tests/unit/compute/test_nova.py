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

from keystoneauth1 import exceptions as keystone_exception
from novaclient import exceptions as nova_exception

from masakari.compute import nova
from masakari import context
from masakari import exception
from masakari import test
from masakari.tests import uuidsentinel


class NovaClientTestCase(test.TestCase):
    def setUp(self):
        super(NovaClientTestCase, self).setUp()

        self.ctx = context.RequestContext('regularuser', 'e3f0833dc08b4cea',
                                          auth_token='token', is_admin=False)
        self.ctx.service_catalog = [
            {'type': 'compute', 'name': 'nova', 'endpoints':
                [{'publicURL': 'http://novahost:8774/v2/e3f0833dc08b4cea'}]},
            {'type': 'identity', 'name': 'keystone', 'endpoints':
                [{'publicURL': 'http://keystonehost:5000/v2.0'}]}]

        self.override_config('nova_endpoint_template',
                             'http://novahost:8774/v2/%(project_id)s')
        self.override_config('nova_endpoint_admin_template',
                             'http://novaadmhost:4778/v2/%(project_id)s')
        self.override_config('os_privileged_user_name', 'adminuser')
        self.override_config('os_privileged_user_password', 'strongpassword')

    @mock.patch('novaclient.api_versions.APIVersion')
    @mock.patch('novaclient.client.Client')
    @mock.patch('keystoneauth1.loading.get_plugin_loader')
    @mock.patch('keystoneauth1.session.Session')
    def test_nova_client_regular(self, p_session, p_plugin_loader, p_client,
                                 p_api_version):
        nova.novaclient(self.ctx)
        p_plugin_loader.return_value.load_from_options.assert_called_once_with(
            auth_url='http://novahost:8774/v2/e3f0833dc08b4cea',
            password='token', project_name=None, username='regularuser'
        )
        p_client.assert_called_once_with(
            p_api_version(nova.NOVA_API_VERSION),
            session=p_session.return_value, region_name=None,
            insecure=False, endpoint_type='publicURL', cacert=None,
            timeout=None, extensions=nova.nova_extensions)

    @mock.patch('novaclient.api_versions.APIVersion')
    @mock.patch('novaclient.client.Client')
    @mock.patch('keystoneauth1.loading.get_plugin_loader')
    @mock.patch('keystoneauth1.session.Session')
    def test_nova_client_admin_endpoint(self, p_session, p_plugin_loader,
                                        p_client, p_api_version):
        nova.novaclient(self.ctx, admin_endpoint=True)
        p_plugin_loader.return_value.load_from_options.assert_called_once_with(
            auth_url='http://novaadmhost:4778/v2/e3f0833dc08b4cea',
            password='token', project_name=None, username='regularuser'
        )
        p_client.assert_called_once_with(
            p_api_version(nova.NOVA_API_VERSION),
            session=p_session.return_value, region_name=None,
            insecure=False, endpoint_type='adminURL', cacert=None,
            timeout=None, extensions=nova.nova_extensions)

    @mock.patch('novaclient.api_versions.APIVersion')
    @mock.patch('novaclient.client.Client')
    @mock.patch('keystoneauth1.loading.get_plugin_loader')
    @mock.patch('keystoneauth1.session.Session')
    def test_nova_client_privileged_user(self, p_session, p_plugin_loader,
                                         p_client, p_api_version):
        nova.novaclient(self.ctx, privileged_user=True)
        p_plugin_loader.return_value.load_from_options.assert_called_once_with(
            auth_url='http://keystonehost:5000/v2.0',
            password='strongpassword', project_name=None, username='adminuser'
        )
        p_client.assert_called_once_with(
            p_api_version(nova.NOVA_API_VERSION),
            session=p_session.return_value, region_name=None,
            insecure=False, endpoint_type='publicURL', cacert=None,
            timeout=None, extensions=nova.nova_extensions)

    @mock.patch('novaclient.api_versions.APIVersion')
    @mock.patch('novaclient.client.Client')
    @mock.patch('keystoneauth1.loading.get_plugin_loader')
    @mock.patch('keystoneauth1.session.Session')
    def test_nova_client_privileged_user_custom_auth_url(self, p_session,
                                                         p_plugin_loader,
                                                         p_client,
                                                         p_api_version):
        self.override_config('os_privileged_user_auth_url',
                             'http://privatekeystonehost:5000/v2.0')
        nova.novaclient(self.ctx, privileged_user=True)
        p_plugin_loader.return_value.load_from_options.assert_called_once_with(
            auth_url='http://privatekeystonehost:5000/v2.0',
            password='strongpassword', project_name=None, username='adminuser'
        )
        p_client.assert_called_once_with(
            p_api_version(nova.NOVA_API_VERSION),
            session=p_session.return_value, region_name=None,
            insecure=False, endpoint_type='publicURL', cacert=None,
            timeout=None, extensions=nova.nova_extensions)

    @mock.patch('novaclient.api_versions.APIVersion')
    @mock.patch('novaclient.client.Client')
    @mock.patch('keystoneauth1.loading.get_plugin_loader')
    @mock.patch('keystoneauth1.session.Session')
    def test_nova_client_custom_region(self, p_session, p_plugin_loader,
                                       p_client, p_api_version):
        self.override_config('os_region_name', 'farfaraway')
        nova.novaclient(self.ctx)
        p_plugin_loader.return_value.load_from_options.assert_called_once_with(
            auth_url='http://novahost:8774/v2/e3f0833dc08b4cea',
            password='token', project_name=None, username='regularuser'
        )
        p_client.assert_called_once_with(
            p_api_version(nova.NOVA_API_VERSION),
            session=p_session.return_value, region_name='farfaraway',
            insecure=False, endpoint_type='publicURL', cacert=None,
            timeout=None, extensions=nova.nova_extensions)


class NovaApiTestCase(test.TestCase):
    def setUp(self):
        super(NovaApiTestCase, self).setUp()
        self.api = nova.API()
        self.ctx = context.get_admin_context()

    @mock.patch('masakari.compute.nova.novaclient')
    def test_get_server(self, mock_novaclient):
        server_id = uuidsentinel.fake_server
        mock_servers = mock.MagicMock()
        mock_novaclient.return_value = mock.MagicMock(servers=mock_servers)
        self.api.get_server(self.ctx, server_id)

        mock_novaclient.assert_called_once_with(self.ctx, admin_endpoint=True,
                                                privileged_user=True)
        mock_servers.get.assert_called_once_with(server_id)

    @mock.patch('masakari.compute.nova.novaclient')
    def test_get_failed_not_found(self, mock_novaclient):
        mock_novaclient.return_value.servers.get.side_effect = (
            nova_exception.NotFound(404, '404'))

        self.assertRaises(exception.NotFound,
                  self.api.get_server, self.ctx, uuidsentinel.fake_server)

    @mock.patch('masakari.compute.nova.novaclient')
    def test_get_failed_bad_request(self, mock_novaclient):
        mock_novaclient.return_value.servers.get.side_effect = (
            nova_exception.BadRequest(400, '400'))

        self.assertRaises(exception.InvalidInput,
                  self.api.get_server, self.ctx, uuidsentinel.fake_server)

    @mock.patch('masakari.compute.nova.novaclient')
    def test_get_failed_connection_error(self, mock_novaclient):
        mock_novaclient.return_value.servers.get.side_effect = (
            keystone_exception.ConnectionError(''))

        self.assertRaises(exception.MasakariException,
                  self.api.get_server, self.ctx, uuidsentinel.fake_server)

    @mock.patch('masakari.compute.nova.novaclient')
    def test_get_servers(self, mock_novaclient):
        host = 'fake'
        mock_servers = mock.MagicMock()
        mock_novaclient.return_value = mock.MagicMock(servers=mock_servers)
        self.api.get_servers(self.ctx, host)

        mock_novaclient.assert_called_once_with(self.ctx, admin_endpoint=True,
                                                privileged_user=True)
        mock_servers.list.assert_called_once_with(
            detailed=True, search_opts={'host': 'fake', 'all_tenants': True})

    @mock.patch('masakari.compute.nova.novaclient')
    def test_enable_disable_service_enable(self, mock_novaclient):
        host = 'fake'
        mock_services = mock.MagicMock()
        mock_novaclient.return_value = mock.MagicMock(services=mock_services)
        self.api.enable_disable_service(self.ctx, host, enable=True)

        mock_novaclient.assert_called_once_with(self.ctx, admin_endpoint=True,
                                                privileged_user=True)
        mock_services.enable.assert_called_once_with(host, 'nova-compute')

    @mock.patch('masakari.compute.nova.novaclient')
    def test_enable_disable_service_disable(self, mock_novaclient):
        host = 'fake'
        mock_services = mock.MagicMock()
        mock_novaclient.return_value = mock.MagicMock(services=mock_services)
        self.api.enable_disable_service(self.ctx, host)

        mock_novaclient.assert_called_once_with(self.ctx, admin_endpoint=True,
                                                privileged_user=True)
        mock_services.disable.assert_called_once_with(host, 'nova-compute')

    @mock.patch('masakari.compute.nova.novaclient')
    def test_enable_disable_service_disable_reason(self, mock_novaclient):
        host = 'fake'
        mock_services = mock.MagicMock()
        mock_novaclient.return_value = mock.MagicMock(services=mock_services)
        self.api.enable_disable_service(self.ctx, host, reason='fake_reason')

        mock_novaclient.assert_called_once_with(self.ctx, admin_endpoint=True,
                                                privileged_user=True)
        mock_services.disable_log_reason.assert_called_once_with(
            host, 'nova-compute', 'fake_reason')

    @mock.patch('masakari.compute.nova.novaclient')
    def test_is_service_down(self, mock_novaclient):
        host_name = 'fake'
        binary = "nova-compute"
        mock_services = mock.MagicMock()
        mock_novaclient.return_value = mock.MagicMock(services=mock_services)
        self.api.is_service_down(self.ctx, host_name, binary)

        mock_novaclient.assert_called_once_with(self.ctx, admin_endpoint=True,
                                                privileged_user=True)
        mock_services.list.assert_called_once_with(binary='nova-compute',
                                                   host='fake')

    @mock.patch('masakari.compute.nova.novaclient')
    def test_evacuate_instance(self, mock_novaclient):
        uuid = uuidsentinel.fake_server
        mock_servers = mock.MagicMock()
        mock_novaclient.return_value = mock.MagicMock(servers=mock_servers)
        self.api.evacuate_instance(self.ctx, uuid)

        mock_novaclient.assert_called_once_with(self.ctx, admin_endpoint=True,
                                                privileged_user=True)
        mock_servers.evacuate.assert_called_once_with(
            uuidsentinel.fake_server, host=None, on_shared_storage=True)

    @mock.patch('masakari.compute.nova.novaclient')
    def test_stop_server(self, mock_novaclient):
        uuid = uuidsentinel.fake_server
        mock_servers = mock.MagicMock()
        mock_novaclient.return_value = mock.MagicMock(servers=mock_servers)
        self.api.stop_server(self.ctx, uuid)

        mock_novaclient.assert_called_once_with(self.ctx, admin_endpoint=True,
                                                privileged_user=True)
        mock_servers.stop.assert_called_once_with(uuidsentinel.fake_server)

    @mock.patch('masakari.compute.nova.novaclient')
    def test_start_server(self, mock_novaclient):
        uuid = uuidsentinel.fake_server
        mock_servers = mock.MagicMock()
        mock_novaclient.return_value = mock.MagicMock(servers=mock_servers)
        self.api.start_server(self.ctx, uuid)

        mock_novaclient.assert_called_once_with(self.ctx, admin_endpoint=True,
                                                privileged_user=True)
        mock_servers.start.assert_called_once_with(uuidsentinel.fake_server)
