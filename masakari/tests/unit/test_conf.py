# Copyright 2016 NTT DATA
#
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

import os
import tempfile

import fixtures
from oslo_config import cfg

import masakari.conf.api
from masakari import test


class ConfTest(test.NoDBTestCase):
    """This is a test and pattern for parsing tricky options."""

    class TestConfigOpts(cfg.ConfigOpts):
        def __call__(self, args=None, default_config_files=None):
            if default_config_files is None:
                default_config_files = []
            return cfg.ConfigOpts.__call__(
                self,
                args=args,
                prog='test',
                version='1.0',
                usage='%(prog)s FOO BAR',
                default_config_files=default_config_files,
                validate_default_values=True)

    def setUp(self):
        super(ConfTest, self).setUp()
        self.useFixture(fixtures.NestedTempfile())
        self.conf = self.TestConfigOpts()
        self.tempdirs = []

    def create_tempfiles(self, files, ext='.conf'):
        tempfiles = []
        for (basename, contents) in files:
            if not os.path.isabs(basename):
                (fd, path) = tempfile.mkstemp(prefix=basename, suffix=ext)
            else:
                path = basename + ext
                fd = os.open(path, os.O_CREAT | os.O_WRONLY)
            tempfiles.append(path)
            try:
                os.write(fd, contents.encode('utf-8'))
            finally:
                os.close(fd)
        return tempfiles

    def test_reserved_huge_page(self):
        masakari.conf.api.register_opts(self.conf)

        paths = self.create_tempfiles(
            [('1',
              '[DEFAULT]\n'
              'osapi_max_limit = 1000\n')])
        self.conf(['--config-file', paths[0]])
        # NOTE(Dinesh_Bhor): In oslo.config if you specify a parameter
        # incorrectly, it silently drops it from the conf. Which means
        # the attr doesn't exist at all. The first attr test here is
        # for an unrelated boolean option that is using defaults (so
        # will always work. It's a basic control that *anything* is working.
        self.assertTrue(hasattr(self.conf, 'osapi_max_limit'))
        self.assertTrue(hasattr(self.conf, 'use_forwarded_for'))

        # NOTE(Dinesh_Bhor): Yes, this actually parses as an array holding
        # a dict.
        actual = 1000
        self.assertEqual(actual, self.conf.osapi_max_limit)
