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

.. _getting_involved:

========================================
How to get (more) involved with Masakari
========================================

So you want to get more involved with Masakari? Or you are new to Masakari and
wondering where to start?

We are working on building easy ways for you to get help and ideas on
how to learn more about Masakari and how the Masakari community works.

How do I get started?
=====================

There are quite a few global docs on this:

-  http://www.openstack.org/assets/welcome-guide/OpenStackWelcomeGuide.pdf
-  https://wiki.openstack.org/wiki/How_To_Contribute
-  http://www.openstack.org/community/

There is more general info, non Masakari specific info here:

-  https://wiki.openstack.org/wiki/Mentors
-  https://wiki.openstack.org/wiki/OpenStack_Upstream_Training

What should I work on?
~~~~~~~~~~~~~~~~~~~~~~

So you are starting out your Masakari journey, where is a good place to
start?

If you'd like to learn how Masakari works before changing anything
(good idea!), we recommend looking for reviews with -1s and -2s and seeing
why they got down voted. Once you have some understanding, start reviewing
patches. It's OK to ask people to explain things you don't understand. It's
also OK to see some potential problems but put a +0.

Once you're ready to write code, take a look at some of the work already marked
as low-hanging fruit:

* https://bugs.launchpad.net/masakari/+bugs?field.tag=low-hanging-fruit

How do I get my feature in?
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The best way of getting your feature in is... well it depends.

First concentrate on solving your problem and/or use case, don't fixate
on getting the code you have working merged. It's likely things will need
significant re-work after you discuss how your needs match up with all
the existing ways Masakari is currently being used. The good news, is this
process should leave you with a feature that's more flexible and doesn't
lock you into your current way of thinking.

A key part of getting code merged, is helping with reviewing other
people's code. Great reviews of others code will help free up more core
reviewer time to look at your own patches. In addition, you will
understand how the review is thinking when they review your code.

Also, work out if any ongoing efforts are blocking your feature and
helping out speeding those up. The spec review process should help with
this effort.

For more details on our process, please see: :ref:`process`.

What is expected of a good contributor?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

TODO - need more info on this

Top Tips for working with the Masakari community
================================================

Here are some top tips around engaging with the Masakari community:

-  IRC

   -  we talk a lot in #openstack-masakari
   -  do ask us questions in there, and we will try to help you
   -  not sure about asking questions? feel free to listen in around
      other people's questions
   -  we recommend you setup an IRC bouncer:
      https://wiki.openstack.org/wiki/IRC

-  Email

   -  Use the [masakari] tag in the mailing lists
   -  Filtering on [masakari] and [all] can help tame the list

-  Be Open

   -  i.e. don't review your teams code in private, do it publicly in
      gerrit
   -  i.e. be ready to talk about openly about problems you are having,
      not "theoretical" issues
   -  that way you can start to gain the trust of the wider community

-  Got a problem? Please ask!

   -  Please raise any problems and ask questions early
   -  we want to help you before you are frustrated or annoyed
   -  unsure who to ask? Just ask in IRC.

-  Talk about problems first, then solutions

   -  Don't think about "merging your patch", instead think about
      "solving your problem"
   -  conversations are more productive that way

-  It's not the decision that's important, it's the reason behind it that's
   important

   -  Don't like the way the community is going?
   -  Please ask why we were going that way, and please engage with the
      debate
   -  If you don't, we are unable to learn from what you have to offer

-  No one will decide, this is stuck, who can help me?

   -  it's rare, but it happens
   -  ...but if you don't ask, it's hard for them to help you

Process
=======

It can feel like you are faced with a wall of process. We are a big
community, to make sure the right communication happens, we do use a
minimal amount of process.

If you find something that doesn't make sense, please:

-  ask questions to find out \*why\* it happens
-  if you know of a better way to do it, please speak up
-  one "better way" might be to remove the process if it no longer helps

To learn more about Masakari's process, please read :ref:`process`.

Why bother with any process?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Why is it worth creating a bug or blueprint to track your code review?
This may seem like silly process, but there is usually a good reason
behind it.

We have lots of code to review, and we have tools to try and get to
really important code reviews first. If yours is really important, but
not picked up by our tools, it's possible you just get lost in the bottom
of a big queue.

If you have a bug fix, you have done loads of work to identify the
issue, and test out your fix, and submit it. By adding a bug report, you
are making it easier for other folks who hit the same problem to find
your work, possibly saving them the hours of pain you went through. With
any luck that gives all those people the time to fix different bugs, all
that might have affected you, if you had not given them the time go fix
it.

It's similar with blueprints. You have worked out how to scratch your
itch, lets tell others about that great new feature you have added, so
they can use that. Also, it stops someone with a similar idea going
through all the pain of creating a feature only to find you already have
that feature ready and up for review, or merged into the latest release.

Hopefully this gives you an idea why we have applied a small layer of
process to what we are doing. Having said all this, we need to unlearn
old habits to move forward, there may be better ways to do things, and
we are open to trying them. Please help be part of the solution.

.. _why_plus1:

Why do code reviews if I am not in masakari-core?
=================================================

Code reviews are the life blood of the developer community.

There is a good discussion on how you do good reviews, and how anyone
can be a reviewer:
http://docs.openstack.org/infra/manual/developers.html#peer-review

In the draft process guide, I discuss how doing reviews can help get
your code merged faster: :ref:`process`.

Let's look at some of the top reasons why participating with code reviews
really helps you:

-  Doing more reviews, and seeing what other reviewers notice, will help
   you better understand what is expected of code that gets merged into
   master
-  Having more non-core people do great reviews, leaves less review work
   for the core reviewers to do, so we are able get more code merged
-  Empathy is one of the keys to a happy community. If you are used to
   doing code reviews, you will better understand the comments you get
   when people review your code. As you do more code reviews, and see
   what others notice, you will get a better idea of what people are
   looking for when then apply a +2 to your code.

What are the most useful types of code review comments? Well here are a
few to the top ones:

-  Fundamental flaws are the biggest thing to spot. Does the patch break
   a whole set of existing users, or an existing feature?
-  Consistency of behavior is really important. Does this bit of code
   do things differently to where similar things happen elsewhere in
   Masakari?
-  Is the code easy to maintain, well tested and easy to read? Code is
   read order of magnitude times more than it is written, so optimize
   for the reader of the code, not the writer.

Let's look at some problems people hit when starting out doing code
reviews:

-  My +1 doesn't mean anything, why should I bother?

   -  So your +1 really does help. Some really useful -1 votes that lead
      to a +1 vote helps get code into a position

-  When to use -1 vs 0 vs +1

   -  Please see the guidelines here:
      http://docs.openstack.org/infra/manual/developers.html#peer-review

-  I have already reviewed this code internally, no point in adding a +1
   externally?

   -  Please talk to your company about doing all code reviews in the
      public, that is a much better way to get involved. Showing how the
      code has evolved upstream, is much better than trying to 'perfect'
      code internally, before uploading for public review. You can use
      Draft mode, and mark things as WIP if you prefer, but please do
      the reviews upstream.

-  Where do I start? What should I review?

   -  There are various tools, but a good place to start is:
      https://etherpad.openstack.org/p/masakari-pike-workitems
   -  Depending on the time in the cycle, it's worth looking at
      NeedsCodeReview blueprints:
      https://blueprints.launchpad.net/masakari/
   -  Maybe take a look at things you want to see merged, bug fixes and
      features, or little code fixes
   -  Look for things that have been waiting a long time for a review:
   -  If you get through the above lists, try other tools, such as:
      http://status.openstack.org/reviews

How to do great code reviews?
=============================

http://docs.openstack.org/infra/manual/developers.html#peer-review

For more tips, please see: `Why do code reviews if I am not in masakari-core?`_

How do I become masakari-core?
==============================

You don't have to be masakari-core to be a valued member of the Masakari
community. There are many, many ways you can help. Every quality review
that helps someone get their patch closer to being ready to merge helps
everyone get their code merged faster.

The first step to becoming masakari-core is learning how to be an active
member of the Masakari community, including learning how to do great code
reviews.

If you feel like you have the time to commit to all the masakari-core
membership expectations, reach out to the Masakari PTL who will be
able to find you an existing member of masakari-core to help mentor you. If
all goes well, and you seem like a good candidate, your mentor will
contact the rest of the masakari-core team to ask them to start looking at
your reviews, so they are able to vote for you, if you get nominated for
join masakari-core.

We encourage all mentoring, where possible, to occur on #openstack-masakari
so everyone can learn and benefit from your discussions.

The above mentoring is available to everyone who wants to learn how to
better code reviews, even if you don't ever want to commit to becoming
masakari-core. If you already have a mentor, that's great, the process is
only there for folks who are still trying to find a mentor. Being
admitted to the mentoring program no way guarantees you will become a
member of masakari-core eventually, it's here to help you improve, and help
you have the sort of involvement and conversations that can lead to
becoming a member of masakari-core.

.. note::

   You can try using ``masakari-ptl`` and/or ``masakari-core`` in
   your IRC message to get a response from the desired people.

.. note::

   For basic information on Masakari's governance, including the current PTL
   (Project Team Lead), please visit
   `Masakari's governance page <https://governance.openstack.org/tc/reference/projects/masakari.html>`__.

   To see the current list of Masakari core reviewers (aka cores), see the
   `masakari-core group on Gerrit <https://review.opendev.org/#/admin/groups/1448,members>`__.
