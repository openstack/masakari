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

======================
Development Quickstart
======================

This page describes how to setup and use a working Python development
environment that can be used in developing masakari on Ubuntu.
These instructions assume you're already familiar with git.

Following these instructions will allow you to build the documentation
and run the masakari unit tests.

.. note:: For how to contribute to Masakari, see
          `How To Contribute <http://docs.openstack.org/infra/manual/developers.html>`_.
          Masakari uses the Gerrit code review system,
          See `Gerrit Workflow <http://docs.openstack.org/infra/manual/developers.html#development-workflow>`_.

Setup
=====

There are two ways to create a development environment: using
DevStack, or explicitly installing and cloning just what you need.


Using DevStack
--------------

To enable Masakari in DevStack, perform the following steps:


Download DevStack
~~~~~~~~~~~~~~~~~

.. sourcecode:: bash

    export DEVSTACK_DIR=~/devstack
    git clone git://git.openstack.org/openstack-dev/devstack.git $DEVSTACK_DIR

Enable the Masakari plugin
~~~~~~~~~~~~~~~~~~~~~~~~~~

Enable the plugin by adding the following section to ``$DEVSTACK_DIR/local.conf``

.. sourcecode:: bash

     [[local|localrc]]
     enable_plugin masakari git://git.openstack.org/openstack/masakari

Optionally, a git refspec (branch or tag or commit) may be provided as follows:

.. sourcecode:: bash

     [[local|localrc]]
     enable_plugin masakari git://git.openstack.org/openstack/masakari <refspec>

Run the DevStack utility
~~~~~~~~~~~~~~~~~~~~~~~~

.. sourcecode:: bash

     cd $DEVSTACK_DIR
     ./stack.sh

Explicit Install/Clone
----------------------

DevStack installs a complete OpenStack environment.  Alternatively,
you can explicitly install and clone just what you need for Masakari
development.

Getting the code
~~~~~~~~~~~~~~~~

Grab the code from git::

    git clone https://git.openstack.org/openstack/masakari
    cd masakari


Linux Systems
~~~~~~~~~~~~~

The first step of this process is to install the system (not Python)
packages that are required. Following are instructions on how to do
this on Linux.

On Debian-based distributions (e.g., Debian/Mint/Ubuntu)::

  sudo apt-get install python-pip
  sudo pip install tox
  tox -e bindep
  sudo apt-get install <indicated missing package names>

Building the Documentation
==========================

Install the prerequisite packages: graphviz

To do a full documentation build, issue the following command while
the masakari directory is current.

.. code-block:: bash

  tox -e docs

That will create a Python virtual environment, install the needed
Python prerequisites in that environment, and build all the
documentation in that environment.

Running unit tests
==================

See `Running Python Unit Tests <https://docs.openstack.org/project-team-guide/project-setup/python.html#running-python-unit-tests>`_.
