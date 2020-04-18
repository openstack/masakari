# Copyright 2016 NTT DATA
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from unittest import mock

from masakari.cmd import api
from masakari import config
from masakari import exception
from masakari import test


@mock.patch.object(config, 'parse_args', new=lambda *args, **kwargs: None)
class TestMasakariAPI(test.NoDBTestCase):

    def test_continues_without_failure(self):

        fake_server = mock.MagicMock()
        fake_server.workers = 123

        def fake_service(api, **kw):
            return fake_server

        with mock.patch.object(api, 'service') as mock_service:
            mock_service.WSGIService.side_effect = fake_service
            api.main()
            mock_service.WSGIService.assert_has_calls([
                mock.call('masakari_api', use_ssl=False),
            ])
            launcher = mock_service.process_launcher.return_value
            launcher.launch_service.assert_called_once_with(
                fake_server, workers=123)
            self.assertTrue(launcher.wait.called)

    @mock.patch('sys.exit')
    def test_fails_if_all_failed(self, mock_exit):
        mock_exit.side_effect = exception.MasakariException
        with mock.patch.object(api, 'service') as mock_service:
            mock_service.WSGIService.side_effect = exception.PasteAppNotFound(
                name='masakari_api', path='/')
            self.assertRaises(exception.MasakariException, api.main)
            mock_exit.assert_called_once_with(1)
            launcher = mock_service.process_launcher.return_value
            self.assertFalse(launcher.wait.called)
