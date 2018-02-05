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

=======================================================
Welcome to Masakari's developer/operator documentation!
=======================================================

Masakari is an OpenStack project designed to assure high availability of
instances and compute processes running on hosts.

The developer documentation provided here is continually kept up-to-date
based on the latest code, and may not represent the state of the project at
any specific prior release.

This documentation is intended to help explain what the Masakari developers
think is the current scope of the Masakari project, as well as the
architectural decisions we have made in order to support that scope. We also
document our plans for evolving our architecture over time. Finally, we
documented our current development process and policies.

Masakari API References
=======================

The Masakari API is quite large, we provide a concept guide which
gives some of the high level details, as well as a more detailed API
reference.

To generate API reference guide issue the following command while
the masakari directory is current.

.. code-block:: bash

   $ tox -e api-ref

Developer Guide
===============

If you are new to Masakari, this should help you start to understand what
masakari actually does, and why.

.. toctree::
   :maxdepth: 1

   how_to_get_involved
   architecture
   development.environment

Operator Guide
==============

This section will help you in configuring masakari mannualy.

.. toctree::
    :maxdepth: 1

    operators_guide
    sample_config
    sample_policy
    recovery_workflow_sample_config
    recovery_workflow_custom_task

Indices and tables
==================

* :ref:`search`
