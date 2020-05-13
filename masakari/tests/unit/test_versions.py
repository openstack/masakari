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

import builtins
import io
from oslo_config import cfg

from masakari import test
from masakari import version


class VersionTestCase(test.NoDBTestCase):
    """Test cases for Versions code."""

    def test_version_string_with_package_is_good(self):
        """Ensure uninstalled code get version string."""

        self.stub_out('masakari.version.version_info.version_string',
                lambda: '5.5.5.5')
        self.stub_out('masakari.version.MASAKARI_PACKAGE', 'g9ec3421')
        self.assertEqual("5.5.5.5-g9ec3421",
                         version.version_string_with_package())

    def test_release_file(self):
        version.loaded = False
        real_open = builtins.open
        real_find_file = cfg.CONF.find_file

        def fake_find_file(self, name):
            if name == "release":
                return "/etc/masakari/release"
            return real_find_file(self, name)

        def fake_open(path, *args, **kwargs):
            if path == "/etc/masakari/release":
                data = """[Masakari]
vendor = ACME Corporation
product = ACME Masakari
package = 1337"""
                return io.StringIO(data)

            return real_open(path, *args, **kwargs)

        self.stub_out('builtins.open', fake_open)
        self.stub_out('oslo_config.cfg.ConfigOpts.find_file', fake_find_file)

        self.assertEqual(version.vendor_string(), "ACME Corporation")
        self.assertEqual(version.product_string(), "ACME Masakari")
        self.assertEqual(version.package_string(), "1337")
