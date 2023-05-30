masakari Style Commandments
===========================

- Step 1: Read the OpenStack Style Commandments
  https://docs.openstack.org/hacking/latest/
- Step 2: Read on

Masakari Specific Commandments
------------------------------


- [M301] no db session in public API methods (disabled)
  This enforces a guideline defined in ``oslo.db.sqlalchemy.session``
- [M302] timeutils.utcnow() wrapper must be used instead of direct
  calls to datetime.datetime.utcnow() to make it easy to override its return value in tests
- [M303] capitalize help string
  Config parameter help strings should have a capitalized first letter
- [M305] Change assertTrue(isinstance(A, B)) by optimal assert like
  assertIsInstance(A, B).
- [M306] Change assertEqual(type(A), B) by optimal assert like
  assertIsInstance(A, B)
- [M308] Validate that log messages are not translated.
- [M309] Don't import translation in tests
- [M310] Setting CONF.* attributes directly in tests is forbidden. Use
  self.flags(option=value) instead.
- [M315] Method's default argument shouldn't be mutable
- [M316] Ensure that the _() function is explicitly imported to ensure proper translations.
- [M317] Ensure that jsonutils.%(fun)s must be used instead of json.%(fun)s
- [M318] Change assertTrue/False(A in/not in B, message) to the more specific
  assertIn/NotIn(A, B, message)
- [M319] Check for usage of deprecated assertRaisesRegexp
- [M320] Must use a dict comprehension instead of a dict constructor with a sequence of key-value pairs.
- [M321] Change assertEqual(A in B, True), assertEqual(True, A in B),
  assertEqual(A in B, False) or assertEqual(False, A in B) to the more specific
  assertIn/NotIn(A, B)
- [M322] Check masakari.utils.spawn() is used instead of greenthread.spawn() and eventlet.spawn()
- [M323] contextlib.nested is deprecated
- [M324] Config options should be in the central location ``masakari/conf/``
- [M325] Check for common double word typos
- [M326] Python 3: do not use dict.iteritems.
- [M327] Python 3: do not use dict.iterkeys.
- [M328] Python 3: do not use dict.itervalues.
- [M329] Deprecated library function os.popen()
- [M331] LOG.warn is deprecated. Enforce use of LOG.warning.
- [M332] Yield must always be followed by a space when yielding a value.
- [M333] Policy registration should be in the central location ``masakari/policies/``
- [M334] Do not use the oslo_policy.policy.Enforcer.enforce() method.

Use of pre-commit checks
------------------------
`pre-commit`_ is a software tool that allows us to manage pre-commit checks as
part of the Git repository's configuration
and to run checks as Git pre-commit hooks (or other types of Git hooks)
automatically on developer machines.
It helps to catch and fix common issues before they get pushed to the server.
After the installation of the tool (e.g. on Fedora via
`sudo dnf install pre-commit`) simply `cd` to the Git repository and run
`pre-commit install` to let the tool install its Git pre-commit hook.
From now on these predefined checks will run on files that you change in new
Git commits.

.. _pre-commit: https://pre-commit.com/
