.. _install-ubuntu:

Install and configure for Ubuntu
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This section describes how to install and configure Masakari for Ubuntu
18.04 (bionic).

Prerequisites
-------------

Before you install and configure the masakari service, you must create
databases, service credentials, and API endpoints.

#. To create the masakari database, follow these steps:

   * Use the database access client to connect to the database server
     as the ``root`` user:

     .. code-block:: console

        # mysql

   * Create the ``masakari`` database:

     .. code-block:: console

        mysql> CREATE DATABASE masakari CHARACTER SET utf8;

   * Grant access privileges to the databases:

     .. code-block:: console

        mysql> GRANT ALL PRIVILEGES ON masakari.* TO 'username'@'localhost' \
          IDENTIFIED BY 'MASAKARI_DBPASS';
        mysql> GRANT ALL PRIVILEGES ON masakari.* TO 'username'@'%' \
          IDENTIFIED BY 'MASAKARI_DBPASS';

     Replace ``MASAKARI_DBPASS`` with a suitable password.

   * Exit the database access client.

#. Source the ``admin`` credentials to gain access to admin-only CLI commands:

   .. code-block:: console

      $ . admin-openrc

#. Create the Masakari service credentials:

   * Create the ``masakari`` user with password as ``masakari``:

     .. code-block:: console

        $ openstack user create --password-prompt masakari

        User Password:
        Repeat User Password:
        +---------------------+----------------------------------+
        | Field               | Value                            |
        +---------------------+----------------------------------+
        | domain_id           | default                          |
        | enabled             | True                             |
        | id                  | 8a7dbf5279404537b1c7b86c033620fe |
        | name                | masakari                             |
        | options             | {}                               |
        | password_expires_at | None                             |
        +---------------------+----------------------------------+

   * Add the ``admin`` role to the ``masakari`` user:

     .. code-block:: console

        $ openstack role add --project service --user masakari admin

   * Create the ``masakari`` service entity:

     .. code-block:: console

        $ openstack service create --name masakari \
        --description "masakari high availability" instance-ha

        +-------------+----------------------------------+
        | Field       | Value                            |
        +-------------+----------------------------------+
        | description | masakari high availability       |
        | enabled     | True                             |
        | id          | 060d59eac51b4594815603d75a00aba2 |
        | name        | masakari                         |
        | type        | instance-ha                      |
        +-------------+----------------------------------+

#. Create the Masakari API service endpoints:

   .. code-block:: console

      $ openstack endpoint create --region RegionOne \
        masakari public http:// <CONTROLLER_IP>/instance-ha/v1/$\(tenant_id\)s

      +--------------+-------------------------------------------------------+
      | Field        | Value                                                 |
      +--------------+-------------------------------------------------------+
      | enabled      | True                                                  |
      | id           | 38f7af91666a47cfb97b4dc790b94424                      |
      | interface    | public                                                 |
      | region       | RegionOne                                             |
      | region_id    | RegionOne                                             |
      | service_id   | 060d59eac51b4594815603d75a00aba2                      |
      | service_name | masakari                                              |
      | service_type | instance-ha                                           |
      | url          | http://<CONTROLLER_IP>/instance-ha/v1/$(tenant_id)s   |
      +--------------+-------------------------------------------------------+

      $ openstack endpoint create --region RegionOne \
        masakari internal http:// <CONTROLLER_IP>/instance-ha/v1/$\(tenant_id\)s

      +--------------+-------------------------------------------------------+
      | Field        | Value                                                 |
      +--------------+-------------------------------------------------------+
      | enabled      | True                                                  |
      | id           | 38f7af91666a47cfb97b4dc790b94424                      |
      | interface    | internal                                              |
      | region       | RegionOne                                             |
      | region_id    | RegionOne                                             |
      | service_id   | 060d59eac51b4594815603d75a00aba2                      |
      | service_name | masakari                                              |
      | service_type | instance-ha                                           |
      | url          | http://<CONTROLLER_IP>/instance-ha/v1/$(tenant_id)s   |
      +--------------+-------------------------------------------------------+

      $ openstack endpoint create --region RegionOne \
        masakari admin http://<CONTROLLER_IP>/instance-ha/v1/$\(tenant_id\)s

      +--------------+-------------------------------------------------------+
      | Field        | Value                                                 |
      +--------------+-------------------------------------------------------+
      | enabled      | True                                                  |
      | id           | 38f7af91666a47cfb97b4dc790b94424                      |
      | interface    | admin                                                 |
      | region       | RegionOne                                             |
      | region_id    | RegionOne                                             |
      | service_id   | 060d59eac51b4594815603d75a00aba2                      |
      | service_name | masakari                                              |
      | service_type | instance-ha                                           |
      | url          | http://<CONTROLLER_IP>/instance-ha/v1/$(tenant_id)s   |
      +--------------+-------------------------------------------------------+

Install and configure Masakari
------------------------------

.. note::

   * You must install Masakari on the Controller Nodes only.

#. Clone masakari using:

   .. code-block:: console

      # git clone https://opendev.org/openstack/masakari.git

#. Prepare the masakari configuration files:

   #. Generate via tox:

      Go to ``/opt/stack/masakari`` and execute the command below.
      This will generate ``masakari.conf.sample``, a sample configuration file,
      at ``/opt/stack/masakari/etc/masakari/``:

      .. code-block:: console

         # tox -egenconfig

   #. Download from:

      # :download:`masakari.conf.sample </_static/masakari.conf.sample>`

   #. Rename ``masakari.conf.sample`` file to ``masakari.conf``,
      and edit sections as shown below:

      .. code-block:: ini

         [DEFAULT]
         transport_url = rabbit://stackrabbit:admin@<CONTROLLER_IP>:5672/
         graceful_shutdown_timeout = 5
         os_privileged_user_tenant = service
         os_privileged_user_password = admin
         os_privileged_user_auth_url = http://<CONTROLLER_IP>/identity
         os_privileged_user_name = nova
         logging_exception_prefix = %(color)s%(asctime)s.%(msecs)03d TRACE %(name)s [01;35m%(instance)s[00m
         logging_debug_format_suffix = [00;33mfrom (pid=%(process)d) %(funcName)s %(pathname)s:%(lineno)d[00m
         logging_default_format_string = %(asctime)s.%(msecs)03d %(color)s%(levelname)s %(name)s [[00;36m-%(color)s] [01;35m%(instance)s%(color)s%(message)s[00m
         logging_context_format_string = %(asctime)s.%(msecs)03d %(color)s%(levelname)s %(name)s [[01;36m%(request_id)s [00;36m%(project_name)s %(user_name)s%(color)s] [01;35m%(instance)s%(color)s%(message)s[00m
         use_syslog = False
         debug = True
         masakari_api_workers = 2

         [database]
         connection = mysql+pymysql://root:admin@1<CONTROLLER_IP>/masakari?charset=utf8

         [keystone_authtoken]
         memcached_servers = localhost:11211
         cafile = /opt/stack/data/ca-bundle.pem
         project_domain_name = Default
         project_name = service
         user_domain_name = Default
         password = <MASAKARI_PASS>
         username = masakari
         auth_url = http://<CONTROLLER_IP>/identity
         auth_type = password

         [taskflow]
         connection = mysql+pymysql://root:admin@<CONTROLLER_IP>/masakari?charset=utf8

      .. note::

         Replace ``CONTROLLER_IP`` with the IP address of controller node.

         Replace ``MASAKARI_PASS`` with the password you chose for the
         ``masakari`` user in the Identity service.

   #. Create ``masakari`` directory in /etc/:

      Copy ``masakari.conf`` file to ``/etc/masakari/``

      .. code-block:: console

         # cp -p etc/masakari/masakari.conf.sample /etc/masakari/masakari.conf

#. To install masakari run setup.py from masakari:

   .. code-block:: console

      # cd masakari
      # sudo python setup.py install

#. Run below db command to sync database:

   .. code-block:: console

      # masakari-manage db sync

Finalize installation
---------------------

* Start masakari services:

  .. code-block:: console

     # masakari-api
     # masakari-engine
