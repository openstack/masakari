.. -*- rst -*-

============================
 FailoverSegments (segments)
============================

**Segments**

System can be zoned from top to down levels, into Regions, Availability Zones
and Host Aggregates (or Cells). Within those zones, one or more
pacemaker/pacemaker-remote clusters may exist. In addition to those boundaries,
shared storage boundary is also important to decide the optimal host for
fail-over. Openstack zoned boundaries (such as Regions, AZ, Host Aggregates,
etc..) can be managed by the nova scheduler. However, shared storage
boundaries are difficult to manage. Moreover, the operator may want to use
other types of boundary such as rack layout and powering. Therefore, operator
may want to define the segment of hypervisor hosts and assign the failover
host/hosts for each of them. Those segment can be define based on the shared
storage boundaries or any other limitations may critical for selection of the
failover host.

Lists, creates, shows details for, updates, and deletes segments.

List FailoverSegments
=====================

.. rest_method:: GET /segments

Lists IDs, names, description, recovery_method, service_type, enabled for all
segments.

Segments contains `service_type`, `recovery_method` and `enabled` attributes.
`service_type` attribute indicates for which service (e.g. compute, cinder
etc) this segment belongs to. `recovery_method` attribute indicates the
recovery action to be followed when any host in a segment goes down. `enabled`
attribute indicates whether notifications which belong to this segment will
be dealt with. The possible `recovery_method` values are:

- ``auto``. Auto recovery action.
- ``reserved_host``. Reserved host recovery action.
- ``auto_priority``. First executes auto and if auto fails then retried with
  reserved host recovery action.
- ``rh_priority``. First executes reserved host and if it fails then retried
  with auto recovery action.

You can filter on the `service_type`, `recovery_method` and `enabled` when you
complete a list segments request.

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

  - limit: limit
  - marker: marker
  - recovery_method: recovery_method_query_segment
  - service_type: service_type_query_segment
  - enabled: segment_enabled
  - sort_dir: sort_dir
  - sort_key: sort_key_segment

Response
--------

.. rest_parameters:: parameters.yaml

  - segments: segments
  - name: segment_name
  - uuid: segment_uuid

**Example List Segments**

.. literalinclude:: ../../doc/api_samples/segments/segments-list-resp.json
   :language: javascript


Create Segment
==============

.. rest_method:: POST /segments

Creates a segment.

Creates a FailoverSegment with name, description, service_type, enabled and
recovery_method. For `service_type` user can mention the name of service for
which this segment is created. As of now user can mention `COMPUTE` as
`service_type`. For `recovery_method` user can mention either `auto`,
`reserved_host`, `auto_priority` or `rh_priority`. Segment name should be
unique. For `enabled` user can mention `true` or `false` to enable/disable
this segment.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 202

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 409

..

  A conflict(409) is returned if segment with same name is already present.

Request
-------

.. rest_parameters:: parameters.yaml


  - segment: segment
  - description: segment_description
  - name: segment_name
  - recovery_method: segment_recovery_method
  - service_type: segment_service_type
  - enabled: segment_enabled

**Example Create Segment**

.. literalinclude:: ../../doc/api_samples/segments/segment-create-req.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

  - segment: segment
  - created: created
  - description: segment_description
  - id: segment_id
  - name: segment_name
  - recovery_method: segment_recovery_method
  - service_type: segment_service_type
  - enabled: segment_enabled
  - updated: updated
  - uuid: segment_uuid

**Example Create Segment**

.. literalinclude:: ../../doc/api_samples/segments/segment-create-resp.json
   :language: javascript


Show Segment Details
====================

.. rest_method:: GET /segments/{segment_id}

Shows details for a segment.

**Preconditions**

The segment must exist.

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

Response
--------

.. rest_parameters:: parameters.yaml

  - segment: segment
  - created: created
  - description: segment_description
  - id: segment_id
  - name: segment_name
  - recovery_method: segment_recovery_method
  - service_type: segment_service_type
  - enabled: segment_enabled
  - updated: updated
  - uuid: segment_uuid

**Example Show Segment Details**

.. literalinclude:: ../../doc/api_samples/segments/segment-get-resp.json
   :language: javascript


Update Segment
==============

.. rest_method:: PUT /segments/{segment_id}

Updates the editable attributes of an existing segment.

**Preconditions**

- The segment must exist.
- User can not update segment if any host from the segment has any usage in
  the notification table i.e. any host from the failover segment has
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

  A conflict(409) is returned if user tries to update segment name which is
  already assigned to segment or if any host from the segment has any usage in
  the notification table i.e. any host from the failover segment has
  notification status as new/error/running.


Request
-------

.. rest_parameters:: parameters.yaml

  - segment_id: segment_id_path
  - description: segment_description
  - name: segment_name
  - recovery_method: segment_recovery_method
  - service_type: segment_service_type
  - enabled: segment_enabled

**Example Update segment name**

.. literalinclude:: ../../doc/api_samples/segments/segment-update-req.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

  - segment: segment
  - created: created
  - description: segment_description
  - id: segment_id
  - name: segment_name
  - recovery_method: segment_recovery_method
  - service_type: segment_service_type
  - enabled: segment_enabled
  - updated: updated
  - uuid: segment_uuid

**Example Update Segment name**

.. literalinclude:: ../../doc/api_samples/segments/segment-update-resp.json
   :language: javascript


Delete Segment
==============

.. rest_method:: DELETE /segments/{segment_id}

Deletes a segment.

**Preconditions**

- The segment must exist.
- User can not delete segment if any host from the segment has any usage in
  the notification table i.e. any host from the failover segment has
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

  A conflict(409) is returned if user tries to delete the segment if any host
  from the segment has any usage in the notification table i.e. any host from
  the failover segment has notification status as new/error/running.

Request
-------

.. rest_parameters:: parameters.yaml

  - segment_id: segment_id_path

Response
--------

There is no body content for the response of a successful DELETE query.
