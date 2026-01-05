#    Copyright 2016 NTT Data.
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

import textwrap
from unittest import mock

import ddt
import pycodestyle

from masakari.hacking import checks
from masakari.tests.unit import base


@ddt.ddt
class HackingTestCase(base.NoDBTestCase):
    """This class tests the hacking checks in masakari.hacking.checks by
    passing strings to the check methods like the pycodestyle/flake8 parser
    would.

    The parser loops over each line in the file and then passes the
    parameters to the check method. The parameter names in the check method
    dictate what type of object is passed to the check method.

    The parameter types are::

        logical_line: A processed line with the following modifications:
            - Multi-line statements converted to a single line.
            - Stripped left and right.
            - Contents of strings replaced with "xxx" of same length.
            - Comments removed.
        physical_line: Raw line of text from the input file.
        lines: a list of the raw lines from the input file
        tokens: the tokens that contribute to this logical line
        line_number: line number in the input file
        total_lines: number of lines in the input file
        blank_lines: blank lines before this one
        indent_char: indentation character in this file (" " or "\t")
        indent_level: indentation (with tabs expanded to multiples of 8)
        previous_indent_level: indentation on previous line
        previous_logical: previous logical line
        filename: Path of the file being run through pycodestyle

    When running a test on a check method the return will be False/None if
    there is no violation in the sample input. If there is an error a tuple is
    returned with a position in the line, and a message. So to check the result
    just assertTrue if the check is expected to fail and assertFalse if it
    should pass.
    """
    def test_no_setting_conf_directly_in_tests(self):
        self.assertEqual(len(list(checks.no_setting_conf_directly_in_tests(
            "CONF.option = 1", "masakari/tests/test_foo.py"))), 1)

        self.assertEqual(len(list(checks.no_setting_conf_directly_in_tests(
            "CONF.group.option = 1", "masakari/tests/test_foo.py"))), 1)

        self.assertEqual(len(list(checks.no_setting_conf_directly_in_tests(
            "CONF.option = foo = 1", "masakari/tests/test_foo.py"))), 1)

        # Shouldn't fail with comparisons
        self.assertEqual(len(list(checks.no_setting_conf_directly_in_tests(
            "CONF.option == 'foo'", "masakari/tests/test_foo.py"))), 0)

        self.assertEqual(len(list(checks.no_setting_conf_directly_in_tests(
            "CONF.option != 1", "masakari/tests/test_foo.py"))), 0)

        # Shouldn't fail since not in masakari/tests/
        self.assertEqual(len(list(checks.no_setting_conf_directly_in_tests(
            "CONF.option = 1", "masakari/compute/foo.py"))), 0)

    def test_no_mutable_default_args(self):
        self.assertEqual(1, len(list(checks.no_mutable_default_args(
            "def get_info_from_bdm(virt_type, bdm, mapping=[])"))))

        self.assertEqual(0, len(list(checks.no_mutable_default_args(
            "defined = []"))))

        self.assertEqual(0, len(list(checks.no_mutable_default_args(
            "defined, undefined = [], {}"))))

    def test_check_explicit_underscore_import(self):
        self.assertEqual(len(list(checks.check_explicit_underscore_import(
            "LOG.info(_('My info message'))",
            "masakari/tests/other_files.py"))), 1)
        self.assertEqual(len(list(checks.check_explicit_underscore_import(
            "msg = _('My message')",
            "masakari/tests/other_files.py"))), 1)
        self.assertEqual(len(list(checks.check_explicit_underscore_import(
            "from masakari.i18n import _",
            "masakari/tests/other_files.py"))), 0)
        self.assertEqual(len(list(checks.check_explicit_underscore_import(
            "LOG.info(_('My info message'))",
            "masakari/tests/other_files.py"))), 0)
        self.assertEqual(len(list(checks.check_explicit_underscore_import(
            "msg = _('My message')",
            "masakari/tests/other_files.py"))), 0)
        self.assertEqual(len(list(checks.check_explicit_underscore_import(
            "from masakari.i18n import _",
            "masakari/tests/other_files2.py"))), 0)
        self.assertEqual(len(list(checks.check_explicit_underscore_import(
            "msg = _('My message')",
            "masakari/tests/other_files2.py"))), 0)
        self.assertEqual(len(list(checks.check_explicit_underscore_import(
            "_ = translations.ugettext",
            "masakari/tests/other_files3.py"))), 0)
        self.assertEqual(len(list(checks.check_explicit_underscore_import(
            "msg = _('My message')",
            "masakari/tests/other_files3.py"))), 0)

    # We are patching pycodestyle so that only the check under test is actually
    # installed.
    @mock.patch('pycodestyle._checks',
                {'physical_line': {}, 'logical_line': {}, 'tree': {}})
    def _run_check(self, code, checker, filename=None):
        pycodestyle.register_check(checker)

        lines = textwrap.dedent(code).lstrip().splitlines(True)

        checker = pycodestyle.Checker(filename=filename, lines=lines)
        checker.check_all()
        checker.report._deferred_print.sort()
        return checker.report._deferred_print

    def _assert_has_errors(self, code, checker, expected_errors=None,
                           filename=None):
        actual_errors = [e[:3] for e in
                         self._run_check(code, checker, filename)]
        self.assertEqual(expected_errors or [], actual_errors)

    def _assert_has_no_errors(self, code, checker, filename=None):
        self._assert_has_errors(code, checker, filename=filename)

    def test_dict_constructor_with_list_copy(self):
        self.assertEqual(1, len(list(checks.dict_constructor_with_list_copy(
            "    dict([(i, connect_info[i])"))))

        self.assertEqual(1, len(list(checks.dict_constructor_with_list_copy(
            "    attrs = dict([(k, _from_json(v))"))))

        self.assertEqual(1, len(list(checks.dict_constructor_with_list_copy(
            "        type_names = dict((value, key) for key, value in"))))

        self.assertEqual(1, len(list(checks.dict_constructor_with_list_copy(
            "   dict((value, key) for key, value in"))))

        self.assertEqual(1, len(list(checks.dict_constructor_with_list_copy(
            "foo(param=dict((k, v) for k, v in bar.items()))"))))

        self.assertEqual(1, len(list(checks.dict_constructor_with_list_copy(
            " dict([[i,i] for i in range(3)])"))))

        self.assertEqual(1, len(list(checks.dict_constructor_with_list_copy(
            "  dd = dict([i,i] for i in range(3))"))))

        self.assertEqual(0, len(list(checks.dict_constructor_with_list_copy(
            "        create_kwargs = dict(snapshot=snapshot,"))))

        self.assertEqual(0, len(list(checks.dict_constructor_with_list_copy(
            "      self._render_dict(xml, data_el, data.__dict__)"))))

    def test_check_contextlib_use(self):
        code = """
               with base.nested(
                   mock.patch.object(network_model.NetworkInfo, 'hydrate'),
                   mock.patch.object(objects.InstanceInfoCache, 'save'),
               ) as (
                   hydrate_mock, save_mock
               )
               """
        filename = "masakari/api/openstack/ha/test.py"
        self._assert_has_no_errors(code, checks.check_no_contextlib_nested,
                                   filename=filename)
        code = """
               with contextlib.nested(
                   mock.patch.object(network_model.NetworkInfo, 'hydrate'),
                   mock.patch.object(objects.InstanceInfoCache, 'save'),
               ) as (
                   hydrate_mock, save_mock
               )
               """
        filename = "masakari/api/openstack/compute/ha/test.py"
        errors = [(1, 0, 'M323')]
        self._assert_has_errors(code, checks.check_no_contextlib_nested,
                                expected_errors=errors, filename=filename)

    def test_check_greenthread_spawns(self):
        errors = [(1, 0, "M322")]

        code = "greenthread.spawn(func, arg1, kwarg1=kwarg1)"
        self._assert_has_errors(code, checks.check_greenthread_spawns,
                                expected_errors=errors)

        code = "greenthread.spawn_n(func, arg1, kwarg1=kwarg1)"
        self._assert_has_errors(code, checks.check_greenthread_spawns,
                                expected_errors=errors)

        code = "eventlet.greenthread.spawn(func, arg1, kwarg1=kwarg1)"
        self._assert_has_errors(code, checks.check_greenthread_spawns,
                                expected_errors=errors)

        code = "eventlet.spawn(func, arg1, kwarg1=kwarg1)"
        self._assert_has_errors(code, checks.check_greenthread_spawns,
                                expected_errors=errors)

        code = "eventlet.spawn_n(func, arg1, kwarg1=kwarg1)"
        self._assert_has_errors(code, checks.check_greenthread_spawns,
                                expected_errors=errors)

        code = "masakari.utils.spawn(func, arg1, kwarg1=kwarg1)"
        self._assert_has_no_errors(code, checks.check_greenthread_spawns)

        code = "masakari.utils.spawn_n(func, arg1, kwarg1=kwarg1)"
        self._assert_has_no_errors(code, checks.check_greenthread_spawns)

    def test_config_option_regex_match(self):
        def should_match(code):
            self.assertTrue(checks.cfg_opt_re.match(code))

        def should_not_match(code):
            self.assertFalse(checks.cfg_opt_re.match(code))

        should_match("opt = cfg.StrOpt('opt_name')")
        should_match("opt = cfg.IntOpt('opt_name')")
        should_match("opt = cfg.DictOpt('opt_name')")
        should_match("opt = cfg.Opt('opt_name')")
        should_match("opts=[cfg.Opt('opt_name')]")
        should_match("   cfg.Opt('opt_name')")
        should_not_match("opt_group = cfg.OptGroup('opt_group_name')")

    def test_check_config_option_in_central_place(self):
        errors = [(1, 0, "M324")]
        code = """
        opts = [
            cfg.StrOpt('random_opt',
                       default='foo',
                       help='I am here to do stuff'),
            ]
        """
        # option at the right place in the tree
        self._assert_has_no_errors(code,
                                   checks.check_config_option_in_central_place,
                                   filename="masakari/conf/serial_console.py")

        self._assert_has_errors(code,
                                checks.check_config_option_in_central_place,
                                filename="masakari/cmd/serialproxy.py",
                                expected_errors=errors)

    def test_check_doubled_words(self):
        errors = [(1, 0, "M325")]

        # Explicit addition of line-ending here and below since this isn't a
        # block comment and without it we trigger #1804062. Artificial break is
        # necessary to stop flake8 detecting the test
        code = "'This is the" + " the best comment'\n"
        self._assert_has_errors(code, checks.check_doubled_words,
                                expected_errors=errors)

        code = "'This is the then best comment'\n"
        self._assert_has_no_errors(code, checks.check_doubled_words)

    def test_dict_iteritems(self):
        self.assertEqual(1, len(list(checks.check_python3_no_iteritems(
            "obj.iteritems()"))))

        self.assertEqual(0, len(list(checks.check_python3_no_iteritems(
            "ob.items()"))))

    def test_dict_iterkeys(self):
        self.assertEqual(1, len(list(checks.check_python3_no_iterkeys(
            "for key in obj.iterkeys()"))))

        self.assertEqual(0, len(list(checks.check_python3_no_iterkeys(
            "for key in ob"))))

    def test_dict_itervalues(self):
        self.assertEqual(1, len(list(checks.check_python3_no_itervalues(
            "obj.itervalues()"))))

        self.assertEqual(0, len(list(checks.check_python3_no_itervalues(
            "ob.values()"))))

    def test_no_os_popen(self):
        code = """
               import os

               foobar_cmd = "foobar -get -beer"
               answer = os.popen(foobar_cmd).read()

               if answer == "ok":
                   try:
                       os.popen(os.popen('foobar -beer -please')).read()

                   except ValueError:
                       go_home()
               """
        errors = [(4, 0, 'M329'), (8, 8, 'M329')]
        self._assert_has_errors(code, checks.no_os_popen,
                                expected_errors=errors)

    def test_no_log_warn(self):
        code = """
                  LOG.warn("LOG.warn is deprecated")
               """
        errors = [(1, 0, 'M331')]
        self._assert_has_errors(code, checks.no_log_warn,
                                expected_errors=errors)
        code = """
                  LOG.warning("LOG.warn is deprecated")
               """
        self._assert_has_no_errors(code, checks.no_log_warn)

    @ddt.data('LOG.info(_LI("Bad"))',
              'LOG.warning(_LW("Bad"))',
              'LOG.error(_LE("Bad"))',
              'LOG.exception(_("Bad"))',
              'LOG.debug(_("Bad"))',
              'LOG.critical(_LC("Bad"))')
    def test_no_translate_logs(self, log_statement):
        self.assertEqual(1, len(list(checks.no_translate_logs(log_statement))))
        errors = [(1, 0, 'M308')]
        self._assert_has_errors(log_statement, checks.no_translate_logs,
                                expected_errors=errors)

    def test_check_policy_registration_in_central_place(self):
        errors = [(3, 0, "M333")]
        code = """
        from masakari import policy

        policy.RuleDefault('context_is_admin', 'role:admin')
        """
        # registration in the proper place
        self._assert_has_no_errors(
            code, checks.check_policy_registration_in_central_place,
            filename="masakari/policies/base.py")
        # option at a location which is not in scope right now
        self._assert_has_errors(
            code, checks.check_policy_registration_in_central_place,
            filename="masakari/api/openstack/ha/non_existent.py",
            expected_errors=errors)

    def test_check_policy_enforce(self):
        errors = [(3, 0, "M334")]
        code = """
        from masakari import policy

        policy._ENFORCER.enforce('context_is_admin', target, credentials)
        """
        self._assert_has_errors(code, checks.check_policy_enforce,
                                expected_errors=errors)

    def test_check_policy_enforce_does_not_catch_other_enforce(self):
        # Simulate a different enforce method defined in masakari
        code = """
        from masakari import foo

        foo.enforce()
        """
        self._assert_has_no_errors(code, checks.check_policy_enforce)
