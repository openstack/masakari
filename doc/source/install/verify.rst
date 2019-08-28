Verify operation
~~~~~~~~~~~~~~~~

Verify Masakari installation.

#. Source the ``admin`` credentials to gain access to admin-only CLI commands:

   .. code-block:: console

      $ . admin-openrc

#. List API endpoints in the Identity service to verify connectivity with the
   Identity service:

   .. note::

      Below endpoints list may differ depending on the installation of
      OpenStack components.

   .. code-block:: console

      $ openstack endpoint list

      +-------------+----------------+--------------------------------------------------------+
      | Name        | Type           | Endpoints                                              |
      +-------------+----------------+--------------------------------------------------------+
      | nova_legacy | compute_legacy | RegionOne                                              |
      |             |                |   public: http://controller/compute/v2/<tenant_id>     |
      |             |                |                                                        |
      | nova        | compute        | RegionOne                                              |
      |             |                |   public: http://controller/compute/v2.1               |
      |             |                |                                                        |
      | cinder      | block-storage  | RegionOne                                              |
      |             |                |   public: http://controller/volume/v3/<tenant_id>      |
      |             |                |                                                        |
      | glance      | image          | RegionOne                                              |
      |             |                |   public: http://controller/image                      |
      |             |                |                                                        |
      | cinderv3    | volumev3       | RegionOne                                              |
      |             |                |   public: http://controller/volume/v3/<tenant_id>      |
      |             |                |                                                        |
      | masakari    | instance-ha    | RegionOne                                              |
      |             |                | internal: http://controller/instance-ha/v1/<tenant_id> |
      |             |                | RegionOne                                              |
      |             |                |  admin: http://controller/instance-ha/v1/<tenant_id>   |
      |             |                | RegionOne                                              |
      |             |                |  public: http://controller/instance-ha/v1/<tenant_id>  |
      |             |                |                                                        |
      | keystone    | identity       | RegionOne                                              |
      |             |                |   public: http://controller/identity                   |
      |             |                | RegionOne                                              |
      |             |                |   admin: http://controller/identity                    |
      |             |                |                                                        |
      | cinderv2    | volumev2       | RegionOne                                              |
      |             |                |   public: http://controller/volume/v2/<tenant_id>      |
      |             |                |                                                        |
      | placement   | placement      | RegionOne                                              |
      |             |                |   public: http://controller/placement                  |
      |             |                |                                                        |
      | neutron     | network        | RegionOne                                              |
      |             |                |   public: http://controller:9696/                      |
      |             |                |                                                        |
      +-------------+----------------+--------------------------------------------------------+

#. Run ``segment list`` command to verify masakari-api is running properly.
   This will return empty segment list as you haven't yet configured
   ``Failover segments``.

   .. code-block:: console

      $ openstack segment list

   .. note::
        Since ``Failover segments`` are not configured, there is no way to
        verify masakari-engine is running properly as the notification cannot
        be sent from masakari-api to masakari-engine.
