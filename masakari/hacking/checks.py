# Copyright (c) 2016, NTT Data
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import re

from hacking import core

"""
Guidelines for writing new hacking checks

 - Use only for Masakari specific tests. OpenStack general tests
   should be submitted to the common 'hacking' module.
 - Pick numbers in the range M3xx. Find the current test with
   the highest allocated number and then pick the next value.
 - Keep the test method code in the source file ordered based
   on the M3xx value.
 - List the new rule in the top level HACKING.rst file
 - Add test cases for each new rule to masakari/tests/unit/test_hacking.py

"""

UNDERSCORE_IMPORT_FILES = []

session_check = re.compile(r"\w*def [a-zA-Z0-9].*[(].*session.*[)]")
cfg_re = re.compile(r".*\scfg\.")
cfg_opt_re = re.compile(r".*[\s\[]cfg\.[a-zA-Z]*Opt\(")
rule_default_re = re.compile(r".*RuleDefault\(")
policy_enforce_re = re.compile(r".*_ENFORCER\.enforce\(")
asse_trueinst_re = re.compile(
    r"(.)*assertTrue\(isinstance\((\w|\.|\'|\"|\[|\])+, "
    r"(\w|\.|\'|\"|\[|\])+\)\)")
asse_equal_type_re = re.compile(
    r"(.)*assertEqual\(type\((\w|\.|\'|\"|\[|\])+\), "
    r"(\w|\.|\'|\"|\[|\])+\)")
asse_equal_in_end_with_true_or_false_re = re.compile(
    r"assertEqual\("r"(\w|[][.'\"])+ in (\w|[][.'\", ])+, (True|False)\)")
asse_equal_in_start_with_true_or_false_re = re.compile(
    r"assertEqual\("r"(True|False), (\w|[][.'\"])+ in (\w|[][.'\", ])+\)")
asse_equal_end_with_none_re = re.compile(
    r"assertEqual\(.*?,\s+None\)$")
asse_equal_start_with_none_re = re.compile(
    r"assertEqual\(None,")
# NOTE(abhishekk): Next two regexes weren't united to one for more readability.
#                 asse_true_false_with_in_or_not_in regex checks
#                 assertTrue/False(A in B) cases where B argument has no spaces
#                 asse_true_false_with_in_or_not_in_spaces regex checks cases
#                 where B argument has spaces and starts/ends with [, ', ".
#                 For example: [1, 2, 3], "some string", 'another string'.
#                 We have to separate these regexes to escape a false positives
#                 results. B argument should have spaces only if it starts
#                 with [, ", '. Otherwise checking of string
#                 "assertFalse(A in B and C in D)" will be false positives.
#                 In this case B argument is "B and C in D".
asse_true_false_with_in_or_not_in = re.compile(
    r"assert(True|False)\("r"(\w|[][.'\"])+( not)? in (\w|[][.'\",])"
    r"+(, .*)?\)")
asse_true_false_with_in_or_not_in_spaces = re.compile(
    r"assert(True|False)"r"\((\w|[][.'\"])+( not)? in [\[|'|\"](\w|"
    r"[][.'\", ])+[\[|'|\"](, .*)?\)")
asse_raises_regexp = re.compile(r"assertRaisesRegexp\(")
conf_attribute_set_re = re.compile(r"CONF\.[a-z0-9_.]+\s*=\s*\w")
translated_log = re.compile(
    r"(.)*LOG\.(audit|error|info|critical|exception)"
    r"\(\s*_\(\s*('|\")")
mutable_default_args = re.compile(r"^\s*def .+\((.+=\{\}|.+=\[\])")
string_translation = re.compile(r"[^_]*_\(\s*('|\")")
underscore_import_check = re.compile(r"(.)*import _(.)*")
import_translation_for_log_or_exception = re.compile(
    r"(.)*(from\smasakari.i18n\simport)\s_")
# We need this for cases where they have created their own _ function.
custom_underscore_check = re.compile(r"(.)*_\s*=\s*(.)*")
dict_constructor_with_list_copy_re = re.compile(r".*\bdict\((\[)?(\(|\[)")
http_not_implemented_re = re.compile(r"raise .*HTTPNotImplemented\(")
spawn_re = re.compile(
    r".*(eventlet|greenthread)\.(?P<spawn_part>spawn(_n)?)\(.*\)")
contextlib_nested = re.compile(r"^with (contextlib\.)?nested\(")
doubled_words_re = re.compile(
    r"\b(then?|[iao]n|i[fst]|but|f?or|at|and|[dt]o)\s+\1\b")
yield_not_followed_by_space = re.compile(r"^\s*yield(?:\(|{|\[|\"|').*$")
_all_log_levels = {'critical', 'error', 'exception', 'info',
                   'warning', 'debug'}
_all_hints = {'_', '_LE', '_LI', '_LW', '_LC'}

log_translation_re = re.compile(
    r".*LOG\.(%(levels)s)\(\s*(%(hints)s)\(" % {
        'levels': '|'.join(_all_log_levels),
        'hints': '|'.join(_all_hints),
    })


@core.flake8ext
def no_db_session_in_public_api(logical_line, filename):
    if "db/api.py" in filename:
        if session_check.match(logical_line):
            yield (0, "M301: public db api methods may not accept"
                      " session")


@core.flake8ext
def use_timeutils_utcnow(logical_line, filename):
    # tools are OK to use the standard datetime module
    if "/tools/" in filename:
        return

    msg = ("M302: timeutils.utcnow() must be used instead of "
           "datetime.%s()")

    datetime_funcs = ['now', 'utcnow']
    for f in datetime_funcs:
        pos = logical_line.find('datetime.%s' % f)
        if pos != -1:
            yield (pos, msg % f)


@core.flake8ext
def capital_cfg_help(logical_line, tokens):
    msg = "M303: capitalize help string"

    if cfg_re.match(logical_line):
        for t in range(len(tokens)):
            if tokens[t][1] == "help":
                txt = tokens[t + 2][1]
                if len(txt) > 1 and txt[1].islower():
                    yield (0, msg)


@core.flake8ext
def assert_true_instance(logical_line):
    """Check for assertTrue(isinstance(a, b)) sentences

    M305
    """
    if asse_trueinst_re.match(logical_line):
        yield (0, "M305: assertTrue(isinstance(a, b)) sentences "
                  "not allowed")


@core.flake8ext
def assert_equal_type(logical_line):
    """Check for assertEqual(type(A), B) sentences

    M306
    """
    if asse_equal_type_re.match(logical_line):
        yield (0, "M306: assertEqual(type(A), B) sentences not allowed")


@core.flake8ext
def no_translate_logs(logical_line):
    """Check for 'LOG.*(_*("'

    OpenStack no longer supports log translation, so we shouldn't
    translate logs.

    * This check assumes that 'LOG' is a logger.

    M308
    """
    if log_translation_re.match(logical_line):
        yield (0, "M308: Log messages should not be translated")


@core.flake8ext
def no_import_translation_in_tests(logical_line, filename):
    """Check for 'from masakari.i18n import _'
    M309
    """
    if 'masakari/tests/' in filename:
        res = import_translation_for_log_or_exception.match(logical_line)
        if res:
            yield (0, "M309 Don't import translation in tests")


@core.flake8ext
def no_setting_conf_directly_in_tests(logical_line, filename):
    """Check for setting CONF.* attributes directly in tests

    The value can leak out of tests affecting how subsequent tests run.
    Using self.flags(option=value) is the preferred method to temporarily
    set config options in tests.

    M310
    """
    if 'masakari/tests/' in filename:
        res = conf_attribute_set_re.match(logical_line)
        if res:
            yield (0, "M310: Setting CONF.* attributes directly in "
                      "tests is forbidden. Use self.flags(option=value) "
                      "instead")


@core.flake8ext
def no_mutable_default_args(logical_line):
    msg = "M315: Method's default argument shouldn't be mutable!"
    if mutable_default_args.match(logical_line):
        yield (0, msg)


@core.flake8ext
def check_explicit_underscore_import(logical_line, filename):
    """Check for explicit import of the _ function

    We need to ensure that any files that are using the _() function
    to translate logs are explicitly importing the _ function.  We
    can't trust unit test to catch whether the import has been
    added so we need to check for it here.
    """

    # Build a list of the files that have _ imported.  No further
    # checking needed once it is found.
    if filename in UNDERSCORE_IMPORT_FILES:
        pass
    elif (underscore_import_check.match(logical_line) or
          custom_underscore_check.match(logical_line)):
        UNDERSCORE_IMPORT_FILES.append(filename)
    elif (translated_log.match(logical_line) or
          string_translation.match(logical_line)):
        yield (0, "M316: Found use of _() without explicit "
                  "import of _ !")


@core.flake8ext
def use_jsonutils(logical_line, filename):
    # tools are OK to use the standard json module
    if "/tools/" in filename:
        return

    msg = "M317: jsonutils.%(fun)s must be used instead of json.%(fun)s"

    if "json." in logical_line:
        json_funcs = ['dumps(', 'dump(', 'loads(', 'load(']
        for f in json_funcs:
            pos = logical_line.find('json.%s' % f)
            if pos != -1:
                yield (pos, msg % {'fun': f[:-1]})


@core.flake8ext
def assert_true_or_false_with_in(logical_line):
    """Check for assertTrue/False(A in B), assertTrue/False(A not in B),
    assertTrue/False(A in B, message) or assertTrue/False(A not in B, message)
    sentences.

    M318
    """
    res = (asse_true_false_with_in_or_not_in.search(logical_line) or
           asse_true_false_with_in_or_not_in_spaces.search(logical_line))
    if res:
        yield (0, "M318: Use assertIn/NotIn(A, B) rather than "
                  "assertTrue/False(A in/not in B) when checking collection "
                  "contents.")


@core.flake8ext
def assert_raises_regexp(logical_line):
    """Check for usage of deprecated assertRaisesRegexp

    M319
    """
    res = asse_raises_regexp.search(logical_line)
    if res:
        yield (0, "M319: assertRaisesRegex must be used instead "
                  "of assertRaisesRegexp")


@core.flake8ext
def dict_constructor_with_list_copy(logical_line):
    msg = ("M320: Must use a dict comprehension instead of a dict "
           "constructor with a sequence of key-value pairs.")
    if dict_constructor_with_list_copy_re.match(logical_line):
        yield (0, msg)


@core.flake8ext
def assert_equal_in(logical_line):
    """Check for assertEqual(A in B, True), assertEqual(True, A in B),
    assertEqual(A in B, False) or assertEqual(False, A in B) sentences

    M321
    """
    res = (asse_equal_in_start_with_true_or_false_re.search(logical_line) or
           asse_equal_in_end_with_true_or_false_re.search(logical_line))
    if res:
        yield (0, "M321: Use assertIn/NotIn(A, B) rather than "
                  "assertEqual(A in B, True/False) when checking collection "
                  "contents.")


@core.flake8ext
def check_greenthread_spawns(logical_line, filename):
    """Check for use of greenthread.spawn(), greenthread.spawn_n(),
    eventlet.spawn(), and eventlet.spawn_n()

    M322
    """
    msg = ("M322: Use masakari.utils.%(spawn)s() rather than "
           "greenthread.%(spawn)s() and eventlet.%(spawn)s()")
    if "masakari/utils.py" in filename or "masakari/tests/" in filename:
        return

    match = re.match(spawn_re, logical_line)

    if match:
        yield (0, msg % {'spawn': match.group('spawn_part')})


@core.flake8ext
def check_no_contextlib_nested(logical_line, filename):
    msg = ("M323: contextlib.nested is deprecated. With Python 2.7"
           "and later  the with-statement supports multiple nested objects. "
           "See https://docs.python.org/2/library/contextlib.html"
           "#contextlib.nested for  more information. masakari.test.nested() "
           "is an alternative as well.")

    if contextlib_nested.match(logical_line):
        yield (0, msg)


@core.flake8ext
def check_config_option_in_central_place(logical_line, filename):
    msg = ("M324: Config options should be in the central location "
           "'/masakari/conf/*'. Do not declare new config options outside "
           "of that folder.")
    # That's the correct location
    if "masakari/conf/" in filename:
        return

    # (pooja_jadhav) All config options (with exceptions that are clarified
    # in the list below) were moved to the central place. List below is for
    # all options that were impossible to move without doing a major impact
    # on code. Add full path to a module or folder.
    conf_exceptions = [
        # CLI opts are allowed to be outside of masakari/conf directory
        'masakari/cmd/manage.py',
    ]

    if any(f in filename for f in conf_exceptions):
        return

    if cfg_opt_re.match(logical_line):
        yield (0, msg)


@core.flake8ext
def check_doubled_words(physical_line, filename):
    """Check for the common doubled-word typos

    M325
    """
    msg = ("M325: Doubled word '%(word)s' typo found")

    match = re.search(doubled_words_re, physical_line)

    if match:
        return (0, msg % {'word': match.group(1)})


@core.flake8ext
def check_python3_no_iteritems(logical_line):
    msg = ("M326: Use dict.items() instead of dict.iteritems().")

    if re.search(r".*\.iteritems\(\)", logical_line):
        yield (0, msg)


@core.flake8ext
def check_python3_no_iterkeys(logical_line):
    msg = ("M327: Use 'for key in dict' instead of 'for key in "
           "dict.iterkeys()'.")

    if re.search(r".*\.iterkeys\(\)", logical_line):
        yield (0, msg)


@core.flake8ext
def check_python3_no_itervalues(logical_line):
    msg = ("M328: Use dict.values() instead of dict.itervalues().")

    if re.search(r".*\.itervalues\(\)", logical_line):
        yield (0, msg)


@core.flake8ext
def no_os_popen(logical_line):
    """Disallow 'os.popen('

    Deprecated library function os.popen() Replace it using subprocess
    https://bugs.launchpad.net/tempest/+bug/1529836

    M329
    """

    if 'os.popen(' in logical_line:
        yield (0, 'M329 Deprecated library function os.popen(). '
                  'Replace it using subprocess module. ')


@core.flake8ext
def no_log_warn(logical_line):
    """Disallow 'LOG.warn('

    Deprecated LOG.warn(), instead use LOG.warning
    https://bugs.launchpad.net/senlin/+bug/1508442

    M331
    """

    msg = ("M331: LOG.warn is deprecated, please use LOG.warning!")
    if "LOG.warn(" in logical_line:
        yield (0, msg)


@core.flake8ext
def yield_followed_by_space(logical_line):
    """Yield should be followed by a space.

    Yield should be followed by a space to clarify that yield is
    not a function. Adding a space may force the developer to rethink
    if there are unnecessary parentheses in the written code.

    Not correct: yield(x), yield(a, b)
    Correct: yield x, yield (a, b), yield a, b

    M332
    """
    if yield_not_followed_by_space.match(logical_line):
        yield (0,
               "M332: Yield keyword should be followed by a space.")


@core.flake8ext
def check_policy_registration_in_central_place(logical_line, filename):
    msg = ('M333: Policy registration should be in the central location '
           '"/masakari/policies/*".')
    # This is where registration should happen
    if "masakari/policies/" in filename:
        return
    # A couple of policy tests register rules
    if "masakari/tests/unit/test_policy.py" in filename:
        return

    if rule_default_re.match(logical_line):
        yield (0, msg)


@core.flake8ext
def check_policy_enforce(logical_line, filename):
    """Look for uses of masakari.policy._ENFORCER.enforce()

    Now that policy defaults are registered in code the _ENFORCER.authorize
    method should be used. That ensures that only registered policies are used.
    Uses of _ENFORCER.enforce could allow unregistered policies to be used, so
    this check looks for uses of that method.

    M334
    """

    msg = ('M334: masakari.policy._ENFORCER.enforce() should not be used. '
           'Use the authorize() method instead.')

    if policy_enforce_re.match(logical_line):
        yield (0, msg)
