# Copyright 2016 NTT DATA
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

"""Matcher classes to be used inside of the testtools assertThat framework."""

import six
import testtools.matchers


class EncodedByUTF8(object):
    def match(self, obj):
        if isinstance(obj, six.binary_type):
            if hasattr(obj, "decode"):
                try:
                    obj.decode("utf-8")
                except UnicodeDecodeError:
                    return testtools.matchers.Mismatch(
                        "%s is not encoded in UTF-8." % obj)
        elif isinstance(obj, six.text_type):
            try:
                obj.encode("utf-8", "strict")
            except UnicodeDecodeError:
                return testtools.matchers.Mismatch("%s cannot be "
                                                   "encoded in UTF-8." % obj)
        else:
            reason = ("Type of '%(obj)s' is '%(obj_type)s', "
                      "should be '%(correct_type)s'."
                      % {
                          "obj": obj,
                          "obj_type": type(obj).__name__,
                          "correct_type": six.binary_type.__name__
                      })
            return testtools.matchers.Mismatch(reason)
