.. -*- rst -*-

==============
 Hosts (hosts)
==============

**Hosts**

A host belongs to segment. Host can be any kind of virtual machine which can
have compute service running on it.

Lists, creates, shows details for, updates, and deletes hosts.

List Hosts
==========

.. rest_method:: GET /segments/{segment_id}/hosts

Lists IDs, names, type, reserved, on_maintenance for all hosts.

You can filter on the type, on_maintenance and reserved when you
complete a list hosts request.

**Preconditions**

The segment must exist.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404

Request
-------

.. rest_parameters:: parameters.yaml

  - segment_id: segment_id_path
  - limit: limit
  - marker: marker
  - on_maintenance: on_maintenance_query_host
  - reserved: reserved_query_host
  - sort_dir: sort_dir
  - sort_key: sort_key_host
  - type: type_query_host

Response
--------

.. rest_parameters:: parameters.yaml

  - hosts: hosts
  - name: host_name
  - uuid: host_uuid
  - failover_segment_id: segment_uuid
  - deleted: deleted
  - on_maintenance: on_maintenance
  - reserved: reserved
  - created_at: created
  - control_attributes: control_attributes
  - updated_at: updated
  - failover_segment: segment
  - type: host_type
  - id: host_id

**Example List hosts**

.. literalinclude:: ../../doc/api_samples/hosts/hosts-list-resp.json
   :language: javascript


Create Host
===========

.. rest_method:: POST /segments/{segment_id}/hosts

Creates a host under given segment.

Creates a Host under given segment with name, type, control_attributes.
User can set sepcific hosts as reserved by setting reserved attribute to True.
By default `on_maintenance` mode which indicates whether host is under
maintenance or not is False when host is created. Host name should be equal
to nova-compute host name from nova service list and host name from the
corosync cluster.

**Preconditions**

The segment must exist.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 201

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404
   - 409

..

  A conflict(409) is returned if host with same name is already present under
  given segment.

  BadRequest (400) is returned if host doesn't exists in nova.

Request
-------

.. rest_parameters:: parameters.yaml


  - segment_id: segment_id_path
  - host: host
  - type: host_type
  - name: host_name
  - control_attributes: control_attributes
  - reserved: reserved
  - on_maintenance: on_maintenance

**Example Create Host**

.. literalinclude:: ../../doc/api_samples/hosts/host-create-req.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

  - host: host
  - name: host_name
  - uuid: host_uuid
  - failover_segment_id: segment_uuid
  - deleted: deleted
  - on_maintenance: on_maintenance
  - reserved: reserved
  - created_at: created
  - control_attributes: control_attributes
  - updated_at: updated
  - failover_segment: segment
  - type: host_type
  - id: host_id

**Example Create Host**

.. literalinclude:: ../../doc/api_samples/hosts/host-create-resp.json
   :language: javascript


Show Host Details
=================

.. rest_method:: GET /segments/{segment_id}/hosts/{host_id}

Shows details for a host.

**Preconditions**

The segment must exist.
The host must exist.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 401
   - 403
   - 404

Request
-------

.. rest_parameters:: parameters.yaml

  - segment_id: segment_id_path
  - host_id: host_id_path

Response
--------

.. rest_parameters:: parameters.yaml

  - host: host
  - name: host_name
  - uuid: host_uuid
  - failover_segment_id: segment_uuid
  - deleted: deleted
  - on_maintenance: on_maintenance
  - reserved: reserved
  - created_at: created
  - control_attributes: control_attributes
  - updated_at: updated
  - failover_segment: segment
  - type: host_type
  - id: host_id

**Example Show Host Details**

.. literalinclude:: ../../doc/api_samples/hosts/host-get-resp.json
   :language: javascript


Update Host
===========

.. rest_method:: PUT /segments/{segment_id}/hosts/{host_id}

Updates the editable attributes of an existing host.

**Preconditions**

- The segment must exist.
- The host must exist.
- User can not update host if that host or any host from
  the failover segment has any usage in the notification
  table i.e. any host from the failover segment has
  notification status as new/error/running.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404
   - 409

..

  A conflict(409) is returned if user tries to update host name which is
  already assigned to host under given segment or user tries to update the
  host or any other host from the failover segment has any usage in the
  notification table i.e. any host from the failover segment has
  notification status as new/error/running.

  BadRequest (400) is returned if host doesn't exists in nova.

Request
-------

.. rest_parameters:: parameters.yaml

  - segment_id: segment_id_path
  - host_id: host_id_path
  - type: host_type
  - name: segment_name
  - on_maintenance: on_maintenance
  - reserved: reserved

**Example Update host reserved flag**

.. literalinclude:: ../../doc/api_samples/hosts/host-update-req.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

  - host: host
  - name: host_name
  - uuid: host_uuid
  - failover_segment_id: segment_uuid
  - deleted: deleted
  - on_maintenance: on_maintenance
  - reserved: reserved
  - created_at: created
  - control_attributes: control_attributes
  - updated_at: updated
  - failover_segment: segment
  - type: host_type
  - id: host_id

**Example Update host reserved flag**

.. literalinclude:: ../../doc/api_samples/hosts/host-update-resp.json
   :language: javascript


Delete Host
===========

.. rest_method:: DELETE /segments/{segment_id}/hosts/{host_id}

Deletes a host from given segment.

**Preconditions**

- The segment must exist.
- The host must exist.
- User can not delete host if that host or any host from
  the failover segment has any usage in the notification
  table i.e. any host from the failover segment has
  notification status as new/error/running.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 204

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404
   - 409

..

  A conflict(409) is returned if user tries to delete the
  host or any other host from the failover segment has any usage in the
  notification table i.e. any host from the failover segment has
  notification status as new/error/running.

Request
-------

.. rest_parameters:: parameters.yaml

  - segment_id: segment_id_path
  - host_id: host_id_path


Response
--------

There is no body content for the response of a successful DELETE query.
