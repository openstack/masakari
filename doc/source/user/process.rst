..
      Copyright 2017 NTT DATA

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

.. _process:

=====================
Masakari team process
=====================

Masakari is always evolving its processes to ensure productive communication
between all members of our community easily.

OpenStack Wide Patterns
=======================

Masakari follows most of the generally adopted norms for OpenStack projects.
You can get more details here:

* https://docs.openstack.org/infra/manual/developers.html
* https://docs.openstack.org/project-team-guide/

If you are new to Masakari, please read this first: :ref:`getting_involved`.

How do I get my code merged?
============================

OK, so you are new to Masakari, and you have been given a feature to
implement. How do I make that happen?

You can get most of your questions answered here:

-  https://docs.openstack.org/infra/manual/developers.html

But let's put a Masakari specific twist on things...

Overview
~~~~~~~~

.. image:: /_static/Masakari_spec_process.svg
   :alt: Flow chart showing the Masakari bug/feature process

Where do you track bugs?
~~~~~~~~~~~~~~~~~~~~~~~~

We track bugs here:

-  https://bugs.launchpad.net/masakari

If you fix an issue, please raise a bug so others who spot that issue
can find the fix you kindly created for them.

Also before submitting your patch it's worth checking to see if someone
has already fixed it for you (Launchpad helps you with that, at little,
when you create the bug report).

When do I need a blueprint vs. a spec?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To understand this question, we need to understand why blueprints and
specs are useful.

But here is the rough idea:

-  if it needs a spec, it will need a blueprint.
-  if it's an API change, it needs a spec.
-  if it's a single small patch that touches a small amount of code,
   with limited deployer and doc impact, it probably doesn't need a
   spec.

If you are unsure, please ask the PTL (masakari-ptl) or one of the other
masakari-core on IRC.

How do I get my blueprint approved?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

So you need your blueprint approved? Here is how:

-  if you don't need a spec, please add a link to your blueprint to the
   agenda for the next masakari meeting:
   https://wiki.openstack.org/wiki/Meetings/Masakari

   -  be sure your blueprint description has enough context for the
      review in that meeting.

-  if you need a spec, then please submit a masakari-spec for review.

Got any more questions? Contact the PTL (masakari-ptl) or one of the other
masakari-core who are awake at the same time as you. IRC is best as
you will often get an immediate response. If they are too busy, send
them an email.

How do I get a procedural -2 removed from my patch?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When feature freeze hits, any patches for blueprints that are still in review
get a procedural -2 to stop them merging. In Masakari a blueprint is only
approved for a single release. To have the -2 removed, you need to get the
blueprint approved for the current release
(see `How do I get my blueprint approved?`_).

My code review seems stuck, what can I do?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

First and foremost - address any -1s and -2s! A few tips:

-  Be precise. Ensure you're not talking at cross purposes.
-  Try to understand where the reviewer is coming from. They may have a
   very different perspective and/or use-case to you.
-  If you don't understand the problem, ask them to explain - this is
   common and helpful behavior.
-  Be positive. Everyone's patches have issues, including core
   reviewers. No-one cares once the issues are fixed.
-  Try not to flip-flop. When two reviewers are pulling you in different
   directions, stop pushing code and negotiate the best way forward.
-  If the reviewer does not respond to replies left on the patchset,
   reach out to them on IRC or email. If they still don't respond, you
   can try to ask their colleagues if they're on holiday (or simply
   wait). Finally, you can ask for mediation in the Masakari meeting by
   adding it to the agenda
   (https://wiki.openstack.org/wiki/Meetings/Masakari). This is also what
   you should do if you are unable to negotiate a resolution to an
   issue.

Eventually you should get some +1s from people working through the
review queue. Expect to get -1s as well. You can ask for reviews within
your company, 1-2 are useful (not more), especially if those reviewers
are known to give good reviews. You can spend some time while you wait
reviewing other people's code - they may reciprocate and you may learn
something (:ref:`Why do code reviews when I'm not core? <why_plus1>`).

If you've waited an appropriate amount of time and you haven't had any
+1s, you can ask on IRC for reviews. Please don't ask for core review
straight away, especially not directly (IRC or email). Core reviewer
time is very valuable and gaining some +1s is a good way to show your
patch meets basic quality standards.

Once you have a few +1s, be patient. Remember the average wait times.
You can ask for reviews each week in IRC, it helps to ask when cores are
awake.

Bugs
----

It helps to apply correct tracking information.

-  Put "Closes-Bug", "Partial-Bug" or "Related-Bug" in the commit
   message tags as necessary.
-  If you have to raise a bug in Launchpad first, do it - this helps
   someone else find your fix.
-  Make sure the bug has the correct priority and tag set.

Features
--------

Again, it helps to apply correct tracking information. For
blueprint-only features:

-  Put your blueprint in the commit message, EG "blueprint
   simple-feature".
-  Mark the blueprint as NeedsCodeReview if you are finished.
-  Maintain the whiteboard on the blueprint so it's easy to understand
   which patches need reviews.
-  Use a single topic for all related patches. All patches for one
   blueprint should share a topic.

For blueprint and spec features, do everything for blueprint-only
features and also:

-  If it's a project or subteam priority, add it to:
   https://etherpad.openstack.org/p/masakari-pike-workitems
-  Ensure your spec is approved for the current release cycle.

If it's not a priority, your blueprint/spec has been approved for the
cycle and you have been patient, you can raise it during the Masakari
meeting. The outcome may be that your spec gets unapproved for the
cycle, so that priority items can take focus. If this happens to you,
sorry - it should not have been approved in the first place, Masakari team
bit off more than they could chew, it is their mistake not yours. You
can re-propose it for the next cycle.

If it's not a priority and your spec has not been approved, your code
will not merge this cycle. Please re-propose your spec for the next
cycle.

Release notes
-------------

Release notes are covered on their own page: :doc:`Release notes </contributor/release_notes>`
