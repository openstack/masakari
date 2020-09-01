.. -*- rst -*-

==============
 API Versions
==============

In order to bring new features to users over time, the Masakari API
supports versioning.

- ''major versions'', which have dedicated urls

The Version APIs work differently from other APIs as they *do not*
require authentication.

List All Major Versions
=======================

.. rest_method:: GET /

This fetches all the information about all known major API versions in
the deployment. Links to more specific information will be provided
for each API version.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

Response
--------

.. rest_parameters:: parameters.yaml

  - versions: versions
  - id: version_id
  - status: version_status
  - links: links
  - version: version_max
  - min_version: version_min

.. note::

   The ``updated`` parameter in the response is vestigial and provides
   no useful information.

Response Example
----------------

This demonstrates the expected response from a bleeding edge server
that supports up to the current version.

.. literalinclude:: /../../doc/api_samples/versions/versions-get-resp.json
   :language: javascript


Show Details of Specific API Version
====================================

.. rest_method:: GET /{api_version}/

This gets the details of a specific API at its root. Nearly all this
information exists at the API root, so this is mostly a redundant
operation.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

Request
-------

.. rest_parameters:: parameters.yaml

   - api_version: api_version

Response
--------

.. rest_parameters:: parameters.yaml

  - version: version
  - id: version_id
  - status: version_status
  - links: links
  - version: version_max
  - min_version: version_min

.. note::

   The ``updated`` and ``media-types`` parameters in the response are
   vestigial and provide no useful information. They will probably be
   deprecated and removed in the future.


Response Example
----------------

This is an example of a ``GET /v1/`` on a relatively current server.

.. literalinclude:: /../../doc/api_samples/versions/v1-version-get-resp.json
   :language: javascript
