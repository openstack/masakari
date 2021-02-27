========
Masakari
========

Virtual Machine High Availability (VMHA) service for OpenStack

Masakari provides Virtual Machine High Availability (VMHA) service
for OpenStack clouds by automatically recovering the KVM-based Virtual
Machine(VM)s from failure events such as VM process down,
provisioning process down, and nova-compute host failure.
It also provides API service for manage and control the automated
rescue mechanism.

NOTE:
Use masakari only if instance path is configured on shared storage system
i.e, 'instances_path' config option of nova has a path of shared directory
otherwise instance data will be lost after the evacuation of instance from
failed host if,
* instance is booted from image
* flavor using ephemeral disks is used

Original version of Masakari: https://github.com/ntt-sic/masakari

Tokyo Summit Session: https://www.youtube.com/watch?v=BmjNKceW_9A

Masakari is distributed under the terms of the Apache License,
Version 2.0. The full terms and conditions of this license are
detailed in the LICENSE file.

* Free software: Apache license 2.0
* Documentation: https://docs.openstack.org/masakari/latest
* Release notes: https://docs.openstack.org/releasenotes/masakari/
* Source: https://opendev.org/openstack/masakari
* Bugs: https://bugs.launchpad.net/masakari


Configure masakari-api
----------------------

#. Create masakari user:

   .. code-block:: shell-session

      openstack user create --password-prompt masakari
      (give password as masakari)

#. Add admin role to masakari user:

   .. code-block:: shell-session

      openstack role add --project service --user masakari admin

#. Create new service:

   .. code-block:: shell-session

      openstack service create --name masakari --description "masakari high availability" instance-ha

#. Create endpoint for masakari service:

   .. code-block:: shell-session

      openstack endpoint create --region RegionOne masakari --publicurl http://<ip-address>:<port>/v1/%\(tenant_id\)s

#. Clone masakari using

   .. code-block:: shell-session

      git clone https://github.com/openstack/masakari.git

#. Run setup.py from masakari

   .. code-block:: shell-session

      sudo python setup.py install

#. Create directory ``/etc/masakari``

#. Copy ``masakari.conf``, ``api-paste.ini`` and ``policy.yaml`` file
   from ``masakari/etc/`` to ``/etc/masakari`` folder

#. To run masakari-api simply use following binary:

   .. code-block:: shell-session

      masakari-api

Configure masakari database
---------------------------

#. Create 'masakari' database

#. After running setup.py for masakari (``sudo python setup.py install``),
   run ``masakari-manage`` command to sync the database

   .. code-block:: shell-session

      masakari-manage db sync

Features
--------

* TODO
