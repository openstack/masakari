.. -*- rst -*-

================
 VMoves (vmoves)
================

**VMoves**

A vmove belongs to one host failure notification.

Lists, shows details for vmoves.

List VMoves
============

.. rest_method:: GET /notification/{notification_id}/vmoves

Lists IDs, notification_id, instance_id, source_host, dest_host,
start_time, end_time, status and type for all VM moves.

Vmoves contain a `type` attribute that indicates the current
vmove type. The possible vmove `type` values are:

- ``evacuation``. The vmove is one evacuation.
- ``migration``. The vmove is one migration.
- ``live_migration``. The vmove is one live_migration.

Vmoves contain a `status` attribute that indicates the current
vmove state. The possible vmove `status` values are:

- ``pending``. The vmove is in pending state and yet to be processed.
- ``ongoing``. The vmove is in progress.
- ``succeeded``. The vmove is processed successfully.
- ``failed``. The vmove is processed failed.
- ``ignored``. The vmove is ignored for some reason.

You can filter on the `type` and `status` when you complete a list
vmoves request.

**Preconditions**

The notification must exist.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404

..

  BadRequest (400) is returned if the notification type is not `COMPUTE_NODE`.

Request
-------

.. rest_parameters:: parameters.yaml

  - notification_id: notification_id_path
  - limit: limit
  - marker: marker
  - sort_dir: sort_dir
  - sort_key: sort_key_vmove
  - status: status_query_vmove
  - type: type_query_vmove

Response
--------

.. rest_parameters:: parameters.yaml

  - vmoves: vmoves
  - created_at: created
  - updated_at: updated
  - deleted: deleted
  - id: vmove_id
  - uuid: vmove_uuid
  - notification_uuid: notification_uuid
  - instance_uuid: vmove_instance_uuid
  - instance_name: vmove_instance_name
  - source_host: host_name
  - dest_host: host_name
  - start_time: vmove_start_time
  - end_time: vmove_end_time
  - status: vmove_status
  - type: vmove_type
  - message: vmove_message

**Example List vmoves**

.. literalinclude:: ../../doc/api_samples/vmoves/vmoves-list-resp.json
   :language: javascript


Show VMove Details
===================

.. rest_method:: GET /notifications/{notification_id}/vmoves/{vmove_id}

Shows details for a vmove.

**Preconditions**

The notification must exist.
The vmove must exist.

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

  - notification_id: notification_id_path
  - vmove_id: vmove_id_path

Response
--------

.. rest_parameters:: parameters.yaml

  - vmove: vmove
  - created_at: created
  - updated_at: updated
  - deleted: deleted
  - id: vmove_id
  - uuid: vmove_uuid
  - notification_uuid: notification_uuid
  - instance_uuid: vmove_instance_uuid
  - instance_name: vmove_instance_name
  - source_host: host_name
  - dest_host: host_name
  - start_time: vmove_start_time
  - end_time: vmove_end_time
  - status: vmove_status
  - type: vmove_type
  - message: vmove_message

**Example Show VMove Details**

.. literalinclude:: ../../doc/api_samples/vmoves/vmove-get-resp.json
   :language: javascript
