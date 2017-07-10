# Copyright 2016 NTT Data.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""Defines interface for DB access.

Functions in this module are imported into the masakari.db namespace.
Call these functions from masakari.db namespace, not the masakari.db.api
namespace.
"""

from oslo_db import concurrency

import masakari.conf

CONF = masakari.conf.CONF

_BACKEND_MAPPING = {'sqlalchemy': 'masakari.db.sqlalchemy.api'}

IMPL = concurrency.TpoolDbapiWrapper(CONF, backend_mapping=_BACKEND_MAPPING)

# The maximum value a signed INT type may have
MAX_INT = 0x7FFFFFFF


def get_engine():
    """Returns database engine"""
    return IMPL.get_engine()


def failover_segment_get_all_by_filters(
        context, filters=None, sort_keys=None, sort_dirs=None,
        limit=None, marker=None):
    """Get all failover segments that match all filters.

    :param context: context to query under
    :param filters: filters for the query in the form of key/value
    :param sort_keys: list of attributes by which results should be sorted,
                    paired with corresponding item in sort_dirs
    :param sort_dirs: list of directions in which results should be sorted,
                    paired with corresponding item in sort_keys
    :param limit: maximum number of items to return
    :param marker: the last item of the previous page, used to determine the
                  next page of results to return

    :returns: list of dictionary-like objects containing all failover segments
    """
    return IMPL.failover_segment_get_all_by_filters(context, filters=filters,
                                                    sort_keys=sort_keys,
                                                    sort_dirs=sort_dirs,
                                                    limit=limit,
                                                    marker=marker)


def failover_segment_get_by_id(context, segment_id):
    """Get failover segment by id.

    :param context: context to query under
    :param segment_id: id of failover segment

    :returns: dictionary-like object containing failover segment

    :raises exception.FailoverSegmentNotFound if failover segment with given ID
            doesn't exist.
    """
    return IMPL.failover_segment_get_by_id(context, segment_id)


def failover_segment_get_by_uuid(context, segment_uuid):
    """Get failover segment by uuid.

    :param context: context to query under
    :param segment_uuid: uuid of failover segment

    :returns: dictionary-like object containing failover segment

    :raises exception.FailoverSegmentNotFound if failover segment with given
            'segment_uuid' doesn't exist.
    """
    return IMPL.failover_segment_get_by_uuid(context, segment_uuid)


def failover_segment_get_by_name(context, name):
    """Get failover segment by name

    :param context: context: context to query under
    :param name: name of failover segment

    :returns: dictionary-like object containing failover segment

    :raises exception.FailoverSegmentNotFoundByName if failover segment with
            given 'name' doesn't exist.
    """
    return IMPL.failover_segment_get_by_name(context, name)


def failover_segment_create(context, values):
    """Insert failover segment to database.

    :param context: context to query under
    :param values: dictionary of failover segment attributes to create

    :returns: dictionary-like object containing created failover segment

    :raises exception.FailoverSegmentExists if failover segment with given name
            already exist.
    """
    return IMPL.failover_segment_create(context, values)


def failover_segment_update(context, segment_uuid, values):
    """Update failover segment by uuid.

    :param context: context to query under
    :param segment_uuid: uuid of segment to be updated
    :param values: dictionary of values to be updated

    :returns: dictionary-like object containing updated failover segment

    :raises exception.FailoverSegmentNotFound if failover segment with given
            'segment_uuid' doesn't exist.
            exception.FailoverSegmentExists if failover segment with given name
            already exist.
    """
    return IMPL.failover_segment_update(context, segment_uuid, values)


def failover_segment_delete(context, segment_uuid):
    """Delete the failover segment.

    :param context: context to query under
    :param segment_uuid: uuid of segment to be deleted

    :raises exception.FailoverSegmentNotFound if failover segment with
            'segment_uuid' doesn't exist.
    """
    return IMPL.failover_segment_delete(context, segment_uuid)


def is_failover_segment_under_recovery(context, failover_segment_id,
                                       filters=None):
    """Checks whether failover segment is used for processing any notification

    :param context: context to query under
    :param failover_segment_id: uuid of segment
    :param filters: dictionary of filters; values that are lists, tuples,
                    sets, or frozensets cause an 'IN' test to be performed,
                    while exact matching ('==' operator) is used for other
                    values.

    :returns: Returns True if any of the host belonging to a failover segment
              is being used for processing any notifications which are in
              new, error or running status otherwise it will return False.
    """
    return IMPL.is_failover_segment_under_recovery(
        context, failover_segment_id, filters=filters)


# db apis for host


def host_get_all_by_filters(
        context, filters=None, sort_keys=None, sort_dirs=None,
        limit=None, marker=None):
    """Get all hosts that match all filters.

    :param context: context to query under
    :param filters: filters for the query in the form of key/value
    :param sort_keys: list of attributes by which results should be sorted,
                     paired with corresponding item in sort_dirs
    :param sort_dirs: list of directions in which results should be sorted,
                     paired with corresponding item in sort_keys
    :param limit: maximum number of items to return
    :param marker: the last item of the previous page, used to determine the
                   next page of results to return

    :returns: list of dictionary-like objects containing all hosts
    """
    return IMPL.host_get_all_by_filters(context, filters=filters,
                                        sort_keys=sort_keys,
                                        sort_dirs=sort_dirs, limit=limit,
                                        marker=marker)


def host_get_by_uuid(context, host_uuid, segment_uuid=None):
    """Get host information by uuid.

    :param context: context to query under
    :param host_uuid: uuid of host
    :param segment_uuid: uuid of failover_segment

    :returns: dictionary-like object containing host

    :raises: exception.HostNotFound if host with 'host_uuid' doesn't exist
    """
    return IMPL.host_get_by_uuid(context, host_uuid, segment_uuid=segment_uuid)


def host_get_by_id(context, host_id):
    """Get host information by id.

    :param context: context to query under
    :param host_id: id of host

    :returns: dictionary-like object containing host

    :raises: exception.HostNotFound if host with given ID doesn't exist
    """
    return IMPL.host_get_by_id(context, host_id)


def host_get_by_name(context, name):
    """Get host information by name.

    :param context: context to query under
    :param name: name of host

    :returns: dictionary-like object containing host

    :raises: exception.HostNotFoundByName if host with given 'name' doesn't
             exist
    """
    return IMPL.host_get_by_name(context, name)


def host_create(context, values):
    """Create a host.

    :param context: context to query under
    :param values: dictionary of host attributes to create

    :returns: dictionary-like object containing created host
    """
    return IMPL.host_create(context, values)


def host_update(context, host_uuid, values):
    """Update host information in the database.

    :param context: context to query under
    :param host_uuid: uuid of host to be updated
    :param values: dictionary of host attributes to be updated

    :returns: dictionary-like object containing updated host

    :raises: exception.HostNotFound if host with 'host_uuid' doesn't exist
             exception.HostExists if host with given 'name' already exist
    """
    return IMPL.host_update(context, host_uuid, values)


def host_delete(context, host_uuid):
    """Delete the host.

    :param context: context to query under
    :param host_uuid: uuid of host to be deleted

    :raises: exception.HostNotFound if host with 'host_uuid' doesn't exist
    """
    return IMPL.host_delete(context, host_uuid)


# notification related db apis


def notifications_get_all_by_filters(
        context, filters=None, sort_keys=None, sort_dirs=None,
        limit=None, marker=None):
    """Get all notifications that match all filters.

    :param context: context to query under
    :param filters: filters for the query in the form of key/value
    :param sort_keys: list of attributes by which results should be sorted,
                     paired with corresponding item in sort_dirs
    :param sort_dirs: list of directions in which results should be sorted,
                     paired with corresponding item in sort_keys
    :param limit: maximum number of items to return
    :param marker: the last item of the previous page, used to determine the
                   next page of results to return

    :returns: list of dictionary-like objects containing all notifications
    """
    return IMPL.notifications_get_all_by_filters(context, filters=filters,
                                                 sort_keys=sort_keys,
                                                 sort_dirs=sort_dirs,
                                                 limit=limit,
                                                 marker=marker)


def notification_get_by_uuid(context, notification_uuid):
    """Get notification information by uuid.

    :param context: context to query under
    :param notification_uuid: uuid of notification

    :returns: dictionary-like object containing notification

    :raises: exception.NotificationNotFound if notification with given
             'notification_uuid' doesn't exist
    """
    return IMPL.notification_get_by_uuid(context, notification_uuid)


def notification_get_by_id(context, notification_id):
    """Get notification information by id.

    :param context: context to query under
    :param notification_id: id of notification

    :returns: dictionary-like object containing notification

    :raises: exception.NotificationNotFound if notification with given ID
             doesn't exist
    """
    return IMPL.notification_get_by_id(context, notification_id)


def notification_create(context, values):
    """Create a notification.

    :param context: context to query under
    :param values: dictionary of notification attributes to create

    :returns: dictionary-like object containing created notification
    """
    return IMPL.notification_create(context, values)


def notification_update(context, notification_uuid, values):
    """Update notification information in the database.

    :param context: context to query under
    :param notification_uuid: uuid of notification to be updated
    :param values: dictionary of notification attributes to be updated

    :returns: dictionary-like object containing updated notification

    :raises: exception.NotificationNotFound if notification with given
             'notification_uuid' doesn't exist
    """
    return IMPL.notification_update(context, notification_uuid, values)


def notification_delete(context, notification_uuid):
    """Delete the notification.

    :param context: context to query under
    :param notification_uuid: uuid of notification to be deleted

    :raises: exception.NotificationNotFound if notification with given
             'notification_uuid' doesn't exist
    """
    return IMPL.notification_delete(context, notification_uuid)


def purge_deleted_rows(context, age_in_days, max_rows):
    """Purge the soft deleted rows.

    :param context: context to query under
    :param age_in_days: Purge deleted rows older than age in days
    :param max_rows: Limit number of records to delete
    """
    return IMPL.purge_deleted_rows(context, age_in_days, max_rows)
