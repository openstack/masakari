===============================
Masakari
===============================

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
* Documentation: https://docs.openstack.org/developer/masakari
* Source: https://git.openstack.org/cgit/openstack/masakari
* Bugs: https://bugs.launchpad.net/masakari


Configure masakari-api
----------------------

1. Create masakari user:
$ openstack user create --password-prompt masakari
(give password as masakari)

2. Add admin role to masakari user:
$ openstack role add --project service --user masakari admin

3. Create new service:
$ openstack service create --name masakari --description "masakari high availability" masakari

4. Create endpoint for masakari service:
$ openstack endpoint create --region RegionOne masakari --publicurl http://<ip-address>:<port>/v1/%\(tenant_id\)s --adminurl http://<ip-address>:<port>/v1/%\(tenant_id\)s --internalurl http://<ip-address>:<port>/v1/%\(tenant_id\)s

5. Clone masakari using
$ git clone https://github.com/openstack/masakari.git

6. Run setup.py from masakari
$ sudo python setup.py install

7. Create masakari directory in /etc/

8. Copy masakari.conf, api-paste.ini and policy.json file from masakari/etc/ to
   /etc/masakari folder

9. To run masakari-api simply use following binary:
$ masakari-api


Configure masakari database
---------------------------

1. Create 'masakari' database

2. After running setup.py for masakari '$ sudo python setup.py install'
    run 'masakari-manage' command to sync the database
    $ masakari-manage db sync


Features
--------

* TODO
