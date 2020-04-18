# Copyright 2016 NTT DATA
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

from unittest import mock

from masakari.api.openstack.ha import extension_info
from masakari import policy
from masakari import test
from masakari.tests.unit.api.openstack import fakes


class fake_extension(object):
    def __init__(self, name, alias, description, version):
        self.name = name
        self.alias = alias
        self.__doc__ = description
        self.version = version


fake_extensions = {
    'ext1-alias': fake_extension('ext1', 'ext1-alias', 'ext1 description', 1),
    'ext2-alias': fake_extension('ext2', 'ext2-alias', 'ext2 description', 2),
    'ext3-alias': fake_extension('ext3', 'ext3-alias', 'ext3 description', 1)
}

simulated_extension_list = {
    'segments': fake_extension('Segments', 'segments', 'Segments.', 1),
    'hosts': fake_extension('Hosts', 'hosts', 'Hosts.', 2),
    'os-fake': fake_extension('Cells', 'os-fake', 'Cells description', 1)
}


def fake_policy_authorize_selective(context, action, target):
    return action != 'os_masakari_api:ext1-alias:discoverable'


class ExtensionInfoTest(test.NoDBTestCase):

    def setUp(self):
        super(ExtensionInfoTest, self).setUp()
        ext_info = extension_info.LoadedExtensionInfo()
        ext_info.extensions = fake_extensions
        self.controller = extension_info.ExtensionInfoController(ext_info)

    def _filter_extensions(self, res_dict):

        for e in [x for x in res_dict['extensions'] if '-alias' in x['alias']]:
            self.assertIn(e['alias'], fake_extensions)
            self.assertEqual(e['name'], fake_extensions[e['alias']].name)
            self.assertEqual(e['alias'], fake_extensions[e['alias']].alias)
            self.assertEqual(e['description'],
                             fake_extensions[e['alias']].__doc__)
            self.assertEqual(e['updated'], "")
            self.assertEqual(e['links'], [])
            self.assertEqual(6, len(e))

    @mock.patch.object(policy, 'authorize', mock.Mock(return_value=True))
    def test_extension_info_list(self):
        req = fakes.HTTPRequest.blank('/extensions')
        res_dict = self.controller.index(req)
        self.assertGreaterEqual(len(res_dict['extensions']), 3)
        self._filter_extensions(res_dict)

    @mock.patch.object(policy, 'authorize', mock.Mock(return_value=True))
    def test_extension_info_show(self):
        req = fakes.HTTPRequest.blank('/extensions/ext1-alias')
        res_dict = self.controller.show(req, 'ext1-alias')
        self.assertEqual(1, len(res_dict))
        self.assertEqual(res_dict['extension']['name'],
                         fake_extensions['ext1-alias'].name)
        self.assertEqual(res_dict['extension']['alias'],
                         fake_extensions['ext1-alias'].alias)
        self.assertEqual(res_dict['extension']['description'],
                         fake_extensions['ext1-alias'].__doc__)
        self.assertEqual(res_dict['extension']['updated'], "")
        self.assertEqual(res_dict['extension']['links'], [])
        self.assertEqual(6, len(res_dict['extension']))

    @mock.patch.object(policy, 'authorize')
    def test_extension_info_list_not_all_discoverable(self, mock_authorize):
        mock_authorize.side_effect = fake_policy_authorize_selective
        req = fakes.HTTPRequest.blank('/extensions')
        res_dict = self.controller.index(req)
        self.assertGreaterEqual(len(res_dict['extensions']), 2)
        self._filter_extensions(res_dict)
