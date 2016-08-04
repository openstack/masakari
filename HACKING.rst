masakari Style Commandments
===========================

- Step 1: Read the OpenStack Style Commandments
  http://docs.openstack.org/developer/hacking/
- Step 2: Read on

Masakari Specific Commandments
------------------------------


- [M301] no db session in public API methods (disabled)
  This enforces a guideline defined in ``oslo.db.sqlalchemy.session``
- [M302] timeutils.utcnow() wrapper must be used instead of direct
  calls to datetime.datetime.utcnow() to make it easy to override its return value in tests
- [M303] capitalize help string
  Config parameter help strings should have a capitalized first letter
- [M304] vim configuration should not be kept in source files.
- [M305] Change assertTrue(isinstance(A, B)) by optimal assert like
  assertIsInstance(A, B).
- [M306] Change assertEqual(type(A), B) by optimal assert like
  assertIsInstance(A, B)
- [M307] Change assertEqual(A, None) or assertEqual(None, A) by optimal assert like
  assertIsNone(A)
- [M308] Validate that debug level logs are not translated.
- [M309] Don't import translation in tests
- [M310] Setting CONF.* attributes directly in tests is forbidden. Use
  self.flags(option=value) instead.
- [M311] Validate that LOG.info messages use _LI.
- [M312] Validate that LOG.exception messages use _LE.
- [M313] Validate that LOG.warning and LOG.warn messages use _LW.
- [M314] Log messages require translations!
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
- [M330] String interpolation should be delayed at logging calls.
- [M331] LOG.warn is deprecated. Enforce use of LOG.warning.
