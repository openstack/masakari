.. -*- rst -*-

==============================
 Notifications (notifications)
==============================

**Notifications**

A notification is a kind of alert provided by monitoring services
(masakari-monitors) for failure of either host, process or instance.

Lists, creates and shows details for notifications.

List Notifications
==================

.. rest_method:: GET /notifications

Lists IDs, notification types, host_name, generated_time, payload and status
for all notifications.

Notifications contain a `status` attribute that indicates the current
notification state. You can filter on the notification `status` when you
complete a list notifications request. The notification `status` is returned
in the response body. The possible notification `status` values are:

- ``new``. The notification is in new state and yet to be processed.
- ``running``. The notification is in progress.
- ``finished``. The notification is completed successfully.
- ``error``. The notification is ended up in error.
- ``failed``. The notification is not processed successfully after failed once.
- ``ignored``. The notification is ignored by masakari engine.

You can also filter on the basis of `source_host_uuid`, `generated_since` and
`type` when you complete a list notifications request.

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

  - generated_since: generated_since_query_notifications
  - limit: limit
  - marker: marker
  - sort_dir: sort_dir
  - sort_key: sort_key_notification
  - source_host_uuid: source_host_uuid_query_notifications
  - type: type_query_notifications

Response
--------

.. rest_parameters:: parameters.yaml

  - notifications: notifications
  - notification_uuid: notification_uuid
  - deleted: deleted
  - created_at: created
  - updated_at: updated
  - status: notification_status
  - uuid: notification_uuid
  - source_host_uuid: source_host_uuid
  - generated_time: generated_time
  - type: notification_type
  - payload: notification_payload
  - id: notification_id


**Example List Notifications**

.. literalinclude:: ../../doc/api_samples/notifications/notifcations-list-resp.json
   :language: javascript


Create Notification
===================

.. rest_method:: POST /notifications

Creates a notification.

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

  A conflict(409) is returned if notification with same payload is exists or
  host for which notification is generated is under maintenance.

  BadRequest (400) is returned if notification payload is incorrect.

Request
-------

.. rest_parameters:: parameters.yaml

  - notification: notification
  - type: notification_type
  - generated_time: generated_time
  - payload: notification_payload
  - host_name: notification_host_name

**Example create Process failure notification**

.. literalinclude:: ../../doc/api_samples/notifications/process-notification-create-req.json
   :language: javascript

**Example create VM failure notification**

.. literalinclude:: ../../doc/api_samples/notifications/vm-notification-create-req.json
   :language: javascript

**Example create COMPUTE_HOST failure notification**

.. literalinclude:: ../../doc/api_samples/notifications/host-notification-create-req.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

  - notification: notification
  - type: notification_type
  - generated_time: generated_time
  - payload: notification_payload
  - source_host_uuid: source_host_uuid
  - uuid: notification_uuid
  - deleted: deleted
  - created_at: created
  - status: notification_status
  - updated_at: updated
  - id: notification_id

**Example create Process failure notification**

.. literalinclude:: ../../doc/api_samples/notifications/process-notification-create-resp.json
   :language: javascript

**Example create VM failure notification**

.. literalinclude:: ../../doc/api_samples/notifications/vm-notification-create-resp.json
   :language: javascript

**Example create COMPUTE_HOST failure notification**

.. literalinclude:: ../../doc/api_samples/notifications/host-notification-create-resp.json
   :language: javascript


Show Notification Details
=========================

.. rest_method:: GET /notifications/{notification_id}

Shows details for a notification.

**Preconditions**

The notification must exist.

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

Response
--------

.. rest_parameters:: parameters.yaml

  - notification: notification
  - type: notification_type
  - generated_time: generated_time
  - payload: notification_payload
  - source_host_uuid: source_host_uuid
  - uuid: notification_uuid
  - deleted: deleted
  - created_at: created
  - status: notification_status
  - updated_at: updated
  - recovery_workflow_details: recovery_workflow_details
  - id: notification_id

**Example Show Notification Details**

.. literalinclude:: ../../doc/api_samples/notifications/notification-get-resp.json
   :language: javascript
