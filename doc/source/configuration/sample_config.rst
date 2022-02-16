==============================
Masakari Configuration Options
==============================

The following is a sample Masakari configuration for adaptation and use. It is
auto-generated from Masakari when this documentation is built, so
if you are having issues with an option, please compare your version of
Masakari with the version of this documentation.

The sample configuration can also be downloaded from :download:`here
</_static/masakari.conf.sample>`.

.. literalinclude:: /_static/masakari.conf.sample

Minimal Configuration
=====================

Edit the ``/etc/masakari/masakari.conf`` file and complete the following actions

In the ``[DEFAULT]`` section, set following options:

.. code-block:: bash

    auth_strategy = keystone
    masakari_topic = ha_engine
    os_privileged_user_tenant = service
    os_privileged_user_auth_url = http://controller/identity
    os_privileged_user_name = nova
    os_privileged_user_password = PRIVILEGED_USER_PASS

Replace ``PRIVILEGED_USER_PASS`` with the password you chose for the privileged user in the
Identity service.

In the ``[database]`` section, configure database access:

.. code-block:: bash

    connection = mysql+pymysql://root:MASAKARI_DBPASS@controller/masakari?charset=utf8

In the ``[keystone_authtoken]`` sections, configure Identity service access:

.. code-block:: bash

    auth_url = http://controller/identity
    memcached_servers = controller:11211
    signing_dir = /var/cache/masakari
    project_domain_name = Default
    user_domain_name = Default
    project_name = service
    username = masakari
    password = MASAKARI_PASS
    auth_type = password
    cafile = /opt/stack/data/ca-bundle.pem

Replace ``MASAKARI_PASS`` with the password you chose for the ``masakari`` user in the Identity service.

In the ``[coordination]`` section, set 'backend_url' if use coordination for Masakari-api service.

.. note::
    Additional packages may be required depending on the tooz backend used in
    the installation. For example, ``etcd3gw`` is required if the backend driver
    is configured to use ``etcd3+http://``. Supported drivers are listed at
    `Tooz drivers <https://docs.openstack.org/tooz/latest/user/drivers.html>`_.
