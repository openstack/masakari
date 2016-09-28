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

import mock
import pep8

from masakari.hacking import checks
from masakari import test


class HackingTestCase(test.NoDBTestCase):
    """This class tests the hacking checks in masakari.hacking.checks by
    passing strings to the check methods like the pep8/flake8 parser would.
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
        filename: Path of the file being run through pep8

    When running a test on a check method the return will be False/None if
    there is no violation in the sample input. If there is an error a tuple is
    returned with a position in the line, and a message. So to check the result
    just assertTrue if the check is expected to fail and assertFalse if it
    should pass.
    """
    def test_no_vi_headers(self):

        lines = ['Line 1\n', 'Line 2\n', 'Line 3\n', 'Line 4\n', 'Line 5\n',
                 'Line 6\n', 'Line 7\n', 'Line 8\n', 'Line 9\n', 'Line 10\n',
                 'Line 11\n', 'Line 12\n', 'Line 13\n', 'Line14\n', 'Line15\n']

        self.assertIsNone(checks.no_vi_headers(
            "Test string foo", 1, lines))
        self.assertEqual(len(list(checks.no_vi_headers(
            "# vim: et tabstop=4 shiftwidth=4 softtabstop=4",
            2, lines))), 2)
        self.assertIsNone(checks.no_vi_headers(
            "# vim: et tabstop=4 shiftwidth=4 softtabstop=4",
            6, lines))
        self.assertIsNone(checks.no_vi_headers(
            "# vim: et tabstop=4 shiftwidth=4 softtabstop=4",
            9, lines))
        self.assertEqual(len(list(checks.no_vi_headers(
            "# vim: et tabstop=4 shiftwidth=4 softtabstop=4",
            14, lines))), 2)
        self.assertIsNone(checks.no_vi_headers(
            "Test end string for vi",
            15, lines))

    def test_assert_true_instance(self):
        self.assertEqual(len(list(checks.assert_true_instance(
            "self.assertTrue(isinstance(e, "
            "exception.BuildAbortException))"))), 1)

        self.assertEqual(
            len(list(checks.assert_true_instance("self.assertTrue()"))), 0)

    def test_assert_equal_type(self):
        self.assertEqual(len(list(checks.assert_equal_type(
            "self.assertEqual(type(als['QuicAssist']), list)"))), 1)

        self.assertEqual(
            len(list(checks.assert_equal_type("self.assertTrue()"))), 0)

    def test_assert_equal_in(self):
        self.assertEqual(len(list(checks.assert_equal_in(
            "self.assertEqual(a in b, True)"))), 1)

        self.assertEqual(len(list(checks.assert_equal_in(
            "self.assertEqual('str' in 'string', True)"))), 1)

        self.assertEqual(len(list(checks.assert_equal_in(
            "self.assertEqual(any(a==1 for a in b), True)"))), 0)

        self.assertEqual(len(list(checks.assert_equal_in(
            "self.assertEqual(True, a in b)"))), 1)

        self.assertEqual(len(list(checks.assert_equal_in(
            "self.assertEqual(True, 'str' in 'string')"))), 1)

        self.assertEqual(len(list(checks.assert_equal_in(
            "self.assertEqual(True, any(a==1 for a in b))"))), 0)

        self.assertEqual(len(list(checks.assert_equal_in(
            "self.assertEqual(a in b, False)"))), 1)

        self.assertEqual(len(list(checks.assert_equal_in(
            "self.assertEqual('str' in 'string', False)"))), 1)

        self.assertEqual(len(list(checks.assert_equal_in(
            "self.assertEqual(any(a==1 for a in b), False)"))), 0)

        self.assertEqual(len(list(checks.assert_equal_in(
            "self.assertEqual(False, a in b)"))), 1)

        self.assertEqual(len(list(checks.assert_equal_in(
            "self.assertEqual(False, 'str' in 'string')"))), 1)

        self.assertEqual(len(list(checks.assert_equal_in(
            "self.assertEqual(False, any(a==1 for a in b))"))), 0)

    def test_assert_equal_none(self):
        self.assertEqual(len(list(checks.assert_equal_none(
            "self.assertEqual(A, None)"))), 1)

        self.assertEqual(len(list(checks.assert_equal_none(
            "self.assertEqual(None, A)"))), 1)

        self.assertEqual(
            len(list(checks.assert_equal_none("self.assertIsNone()"))), 0)

    def test_assert_true_or_false_with_in_or_not_in(self):
        self.assertEqual(len(list(checks.assert_equal_none(
            "self.assertEqual(A, None)"))), 1)
        self.assertEqual(len(list(checks.assert_true_or_false_with_in(
            "self.assertTrue(A in B)"))), 1)

        self.assertEqual(len(list(checks.assert_true_or_false_with_in(
            "self.assertFalse(A in B)"))), 1)

        self.assertEqual(len(list(checks.assert_true_or_false_with_in(
            "self.assertTrue(A not in B)"))), 1)

        self.assertEqual(len(list(checks.assert_true_or_false_with_in(
            "self.assertFalse(A not in B)"))), 1)

        self.assertEqual(len(list(checks.assert_true_or_false_with_in(
            "self.assertTrue(A in B, 'some message')"))), 1)

        self.assertEqual(len(list(checks.assert_true_or_false_with_in(
            "self.assertFalse(A in B, 'some message')"))), 1)

        self.assertEqual(len(list(checks.assert_true_or_false_with_in(
            "self.assertTrue(A not in B, 'some message')"))), 1)

        self.assertEqual(len(list(checks.assert_true_or_false_with_in(
            "self.assertFalse(A not in B, 'some message')"))), 1)

        self.assertEqual(len(list(checks.assert_true_or_false_with_in(
            "self.assertTrue(A in 'some string with spaces')"))), 1)

        self.assertEqual(len(list(checks.assert_true_or_false_with_in(
            "self.assertTrue(A in 'some string with spaces')"))), 1)

        self.assertEqual(len(list(checks.assert_true_or_false_with_in(
            "self.assertTrue(A in ['1', '2', '3'])"))), 1)

        self.assertEqual(len(list(checks.assert_true_or_false_with_in(
            "self.assertTrue(A in [1, 2, 3])"))), 1)

        self.assertEqual(len(list(checks.assert_true_or_false_with_in(
            "self.assertTrue(any(A > 5 for A in B))"))), 0)

        self.assertEqual(len(list(checks.assert_true_or_false_with_in(
            "self.assertTrue(any(A > 5 for A in B), 'some message')"))), 0)

        self.assertEqual(len(list(checks.assert_true_or_false_with_in(
            "self.assertFalse(some in list1 and some2 in list2)"))), 0)

    def test_no_translate_debug_logs(self):
        self.assertEqual(len(list(checks.no_translate_debug_logs(
            "LOG.debug(_('foo'))", "masakari/foo.py"))), 1)

        self.assertEqual(len(list(checks.no_translate_debug_logs(
            "LOG.debug('foo')", "masakari/foo.py"))), 0)

        self.assertEqual(len(list(checks.no_translate_debug_logs(
            "LOG.info(_('foo'))", "masakari/foo.py"))), 0)

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

    def test_log_translations(self):
        logs = ['audit', 'error', 'info', 'warning', 'critical', 'warn',
                'exception']
        levels = ['_LI', '_LW', '_LE', '_LC']
        debug = "LOG.debug('OK')"
        self.assertEqual(
            0, len(list(checks.validate_log_translations(debug, debug, 'f'))))
        for log in logs:
            bad = 'LOG.%s("Bad")' % log
            self.assertEqual(1,
                len(list(
                    checks.validate_log_translations(bad, bad, 'f'))))
            ok = "LOG.%s('OK')    # noqa" % log
            self.assertEqual(0,
                len(list(
                    checks.validate_log_translations(ok, ok, 'f'))))
            ok = "LOG.%s(variable)" % log
            self.assertEqual(0,
                len(list(
                    checks.validate_log_translations(ok, ok, 'f'))))
            for level in levels:
                ok = "LOG.%s(%s('OK'))" % (log, level)
                self.assertEqual(0,
                    len(list(
                        checks.validate_log_translations(ok, ok, 'f'))))

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
            "from masakari.i18n import _, _LW",
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

    # We are patching pep8 so that only the check under test is actually
    # installed.
    @mock.patch('pep8._checks',
                {'physical_line': {}, 'logical_line': {}, 'tree': {}})
    def _run_check(self, code, checker, filename=None):
        pep8.register_check(checker)

        lines = textwrap.dedent(code).strip().splitlines(True)

        checker = pep8.Checker(filename=filename, lines=lines)
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

    def test_oslo_assert_raises_regexp(self):
        code = """
               self.assertRaisesRegexp(ValueError,
                                       "invalid literal for.*XYZ'$",
                                       int,
                                       'XYZ')
               """
        self._assert_has_errors(code, checks.assert_raises_regexp,
                                expected_errors=[(1, 0, "M319")])

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
               with test.nested(
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

        # Artificial break to stop pep8 detecting the test !
        code = "This is the" + " the best comment"
        self._assert_has_errors(code, checks.check_doubled_words,
                                expected_errors=errors)

        code = "This is the then best comment"
        self._assert_has_no_errors(code, checks.check_doubled_words)

    def test_dict_iteritems(self):
        self.assertEqual(1, len(list(checks.check_python3_no_iteritems(
            "obj.iteritems()"))))

        self.assertEqual(0, len(list(checks.check_python3_no_iteritems(
            "six.iteritems(ob))"))))

    def test_dict_iterkeys(self):
        self.assertEqual(1, len(list(checks.check_python3_no_iterkeys(
            "obj.iterkeys()"))))

        self.assertEqual(0, len(list(checks.check_python3_no_iterkeys(
            "six.iterkeys(ob))"))))

    def test_dict_itervalues(self):
        self.assertEqual(1, len(list(checks.check_python3_no_itervalues(
            "obj.itervalues()"))))

        self.assertEqual(0, len(list(checks.check_python3_no_itervalues(
            "six.itervalues(ob))"))))

    def test_no_os_popen(self):
        code = """
               import os

               foobar_cmd = "foobar -get -beer"
               answer = os.popen(foobar_cmd).read()

               if answer == nok":
                   try:
                       os.popen(os.popen('foobar -beer -please')).read()

                   except ValueError:
                       go_home()
               """
        errors = [(4, 0, 'M329'), (8, 8, 'M329')]
        self._assert_has_errors(code, checks.no_os_popen,
                                expected_errors=errors)

    def test_check_delayed_string_interpolation(self):
        checker = checks.check_delayed_string_interpolation
        code = """
               msg_w = _LW('Test string (%s)')
               msg_i = _LI('Test string (%s)')
               value = 'test'

               LOG.error(_LE("Test string (%s)") % value)
               LOG.warning(msg_w % 'test%string')
               LOG.info(msg_i %
                        "test%string%info")
               LOG.critical(
                   _LC('Test string (%s)') % value,
                   instance=instance)
               LOG.exception(_LE(" 'Test quotation %s' \"Test\"") % 'test')
               LOG.debug(' "Test quotation %s" \'Test\'' % "test")
               LOG.debug('Tesing %(test)s' %
                         {'test': ','.join(
                             ['%s=%s' % (name, value)
                              for name, value in test.items()])})
               """

        expected_errors = [(5, 34, 'M330'), (6, 18, 'M330'), (7, 15, 'M330'),
                           (10, 28, 'M330'), (12, 49, 'M330'),
                           (13, 40, 'M330'), (14, 28, 'M330')]
        self._assert_has_errors(code, checker, expected_errors=expected_errors)
        self._assert_has_no_errors(
            code, checker, filename='masakari/tests/unit/test_hacking.py')

        code = """
               msg_w = _LW('Test string (%s)')
               msg_i = _LI('Test string (%s)')
               value = 'test'

               LOG.error(_LE("Test string (%s)"), value)
               LOG.error(_LE("Test string (%s)") % value) # noqa
               LOG.warn(_LW('Test string (%s)'),
                        value)
               LOG.info(msg_i,
                        "test%string%info")
               LOG.critical(
                   _LC('Test string (%s)'), value,
                   instance=instance)
               LOG.exception(_LE(" 'Test quotation %s' \"Test\""), 'test')
               LOG.debug(' "Test quotation %s" \'Test\'', "test")
               LOG.debug('Tesing %(test)s',
                         {'test': ','.join(
                             ['%s=%s' % (name, value)
                              for name, value in test.items()])})
               """
        self._assert_has_no_errors(code, checker)

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
