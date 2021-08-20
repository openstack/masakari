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

====================================
Welcome to Masakari's documentation!
====================================

Masakari is an OpenStack project designed to ensure high availability of
instances and compute processes running on hosts.

This documentation is intended to help explain the current scope of the
Masakari project and  the architectural decisions made to support this scope.
The documentation will include the future architectural roadmap and  the
current development process and policies.

Masakari API References
=======================

The `Masakari API <https://docs.openstack.org/api-ref/instance-ha/>`_ is
extensive. We provide a concept guide which gives some of the high level
details, as well as a more detailed API reference.

Operator Guide
==============

Architecture Overview
---------------------

* :doc:`Masakari architecture </user/architecture>`: An overview of how all
  the components in masakari work together.

Installation
------------

A detailed install guide for masakari.

.. toctree::
   :maxdepth: 2

   install/index

Reference Material
------------------

* :doc:`Configuration Guide <configuration/index>`: Information on configuration files.
* :doc:`Custom Recovery Workflow Configuration Guide <configuration/recovery_workflow_custom_task>`
* :doc:`CLI Commands for Masakari </cli/index>`: The complete command
  reference for Masakari.
* :doc:`Versioned Notifications </user/notifications>`: This provides the list
  of existing versioned notifications with sample payloads.
  This will help newcomers understand basics of Masakari
* `Nova Docs <https://docs.openstack.org/nova/latest/index.html>`_: A collection of guides for Nova.


.. # NOTE(shilpasd): This is the section where we hide things that we don't
   # actually want in the table of contents but sphinx build would fail if
   # they aren't in the toctree somewhere.
.. toctree::
   :hidden:

   cli/index
   configuration/api-paste.ini.rst
   configuration/config.rst
   configuration/index.rst
   configuration/policy.rst
   configuration/recovery_config.rst
   configuration/recovery_workflow_custom_task.rst
   configuration/sample_policy.rst
   user/architecture.rst
   user/notifications.rst

.. only:: html

   .. toctree::
      :hidden:

      configuration/recovery_workflow_sample_config.rst
      configuration/sample_config.rst

.. only:: html

   Contributor Guide
   =================

   .. toctree::
      :maxdepth: 2

      user/how_to_get_involved
      user/process
      install/development.environment
      contributor/code_structure
      contributor/release_notes

   For Contributors
   ================

   * If you are a new contributor to Masakari please refer: :doc:`contributor/contributing`

      .. toctree::
         :hidden:

         contributor/contributing

   Search
   ======

   * :ref:`search`: Search the contents of this document.
   * `OpenStack wide search <https://docs.openstack.org>`_: Search the wider
     set of OpenStack documentation, including forums.
