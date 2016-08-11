=============================
Enabling Masakari in DevStack
=============================

To enable Masakari in DevStack, perform the following steps:


Download DevStack
=================

.. sourcecode:: bash

    export DEVSTACK_DIR=~/devstack
    git clone git://git.openstack.org/openstack-dev/devstack.git $DEVSTACK_DIR

Enable the Masakari plugin
==========================

Enable the plugin by adding the following section to ``$DEVSTACK_DIR/local.conf``

.. sourcecode:: bash

     [[local|localrc]]
     enable_plugin masakari git://git.openstack.org/openstack/masakari

Optionally, a git refspec (branch or tag or commit) may be provided as follows:

.. sourcecode:: bash

     [[local|localrc]]
     enable_plugin masakari git://git.openstack.org/openstack/masakari <refspec>

Run the DevStack utility
========================

.. sourcecode:: bash

     cd $DEVSTACK_DIR
     ./stack.sh
