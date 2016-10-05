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
"""Implementation of SQLAlchemy backend."""

import sys

from oslo_db import api as oslo_db_api
from oslo_db import exception as db_exc
from oslo_db.sqlalchemy import enginefacade
from oslo_db.sqlalchemy import utils as sqlalchemyutils
from oslo_utils import timeutils
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import null

import masakari.conf
from masakari.db.sqlalchemy import models
from masakari import exception
from masakari.i18n import _


CONF = masakari.conf.CONF

main_context_manager = enginefacade.transaction_context()


def _get_db_conf(conf_group, connection=None):

    return {'connection': connection or conf_group.connection,
            'slave_connection': conf_group.slave_connection,
            'sqlite_fk': False,
            '__autocommit': True,
            'expire_on_commit': False,
            'mysql_sql_mode': conf_group.mysql_sql_mode,
            'idle_timeout': conf_group.idle_timeout,
            'connection_debug': conf_group.connection_debug,
            'max_pool_size': conf_group.max_pool_size,
            'max_overflow': conf_group.max_overflow,
            'pool_timeout': conf_group.pool_timeout,
            'sqlite_synchronous': conf_group.sqlite_synchronous,
            'connection_trace': conf_group.connection_trace,
            'max_retries': conf_group.max_retries,
            'retry_interval': conf_group.retry_interval}


def _context_manager_from_context(context):
    if context:
        try:
            return context.db_connection
        except AttributeError:
            pass


def get_backend():
    """The backend is this module itself."""
    return sys.modules[__name__]


def configure(conf):
    main_context_manager.configure(**_get_db_conf(conf.database))


def get_engine(use_slave=False, context=None):
    """Get a database engine object.

    :param use_slave: Whether to use the slave connection
    :param context: The request context that can contain a context manager
    """
    ctxt_mgr = _context_manager_from_context(context) or main_context_manager
    return ctxt_mgr.get_legacy_facade().get_engine(use_slave=use_slave)


def model_query(context, model,
                args=None,
                read_deleted=None,
                project_only=False):
    """Query helper that accounts for context's `read_deleted` field.
    :param context:     MasakariContext of the query.
    :param model:       Model to query. Must be a subclass of ModelBase.
    :param args:        Arguments to query. If None - model is used.
    :param read_deleted: If not None, overrides context's read_deleted field.
                        Permitted values are 'no', which does not return
                        deleted values; 'only', which only returns deleted
                        values; and 'yes', which does not filter deleted
                        values.
    :param project_only: If set and context is user-type, then restrict
                        query to match the context's project_id. If set to
                        'allow_none', restriction includes project_id = None.
    """

    if read_deleted is None:
        read_deleted = context.read_deleted

    query_kwargs = {}
    if 'no' == read_deleted:
        query_kwargs['deleted'] = False
    elif 'only' == read_deleted:
        query_kwargs['deleted'] = True
    elif 'yes' == read_deleted:
        pass
    else:
        raise ValueError(_("Unrecognized read_deleted value '%s'")
                         % read_deleted)

    query = sqlalchemyutils.model_query(
        model, context.session, args, **query_kwargs)

    if masakari.context.is_user_context(context) and project_only:
        if project_only == 'allow_none':
            query = query.filter(or_(model.project_id == context.project_id,
                                     model.project_id == null()))
        else:
            query = query.filter_by(project_id=context.project_id)

    return query


def _process_sort_params(sort_keys, sort_dirs,
                         default_keys=['created_at', 'id'],
                         default_dir='desc'):
    """Process the sort parameters to include default keys.

    Creates a list of sort keys and a list of sort directions. Adds the default
    keys to the end of the list if they are not already included.

    When adding the default keys to the sort keys list, the associated
    direction is:
    1) The first element in the 'sort_dirs' list (if specified), else
    2) 'default_dir' value (Note that 'asc' is the default value since this is
    the default in sqlalchemy.utils.paginate_query)

    :param sort_keys: List of sort keys to include in the processed list
    :param sort_dirs: List of sort directions to include in the processed list
    :param default_keys: List of sort keys that need to be included in the
                         processed list, they are added at the end of the list
                         if not already specified.
    :param default_dir: Sort direction associated with each of the default
                        keys that are not supplied, used when they are added
                        to the processed list
    :returns: list of sort keys, list of sort directions
    :raise exception.InvalidInput: If more sort directions than sort keys
                                   are specified or if an invalid sort
                                   direction is specified
    """
    # Determine direction to use for when adding default keys
    default_dir_value = default_dir
    if sort_dirs and len(sort_dirs) != 0:
        default_dir_value = sort_dirs[0]

    # Create list of keys (do not modify the input list)
    result_keys = []
    if sort_keys:
        result_keys = list(sort_keys)

    # If a list of directions is not provided, use the default sort direction
    # for all provided keys
    if sort_dirs:
        result_dirs = []
        # Verify sort direction
        for sort_dir in sort_dirs:
            if sort_dir not in ('asc', 'desc'):
                msg = _("Unknown sort direction, must be 'asc' or 'desc'")
                raise exception.InvalidInput(reason=msg)
            result_dirs.append(sort_dir)
    else:
        result_dirs = [default_dir_value for _sort_key in result_keys]

    # Ensure that the key and direction length match
    while len(result_dirs) < len(result_keys):
        result_dirs.append(default_dir_value)
    # Unless more direction are specified, which is an error
    if len(result_dirs) > len(result_keys):
        msg = _("Sort direction size exceeds sort key size")
        raise exception.InvalidInput(reason=msg)

    # Ensure defaults are included
    for key in default_keys:
        if key not in result_keys:
            result_keys.append(key)
            result_dirs.append(default_dir_value)

    return result_keys, result_dirs


@oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
@main_context_manager.reader
def failover_segment_get_all_by_filters(
        context, filters=None, sort_keys=None,
        sort_dirs=None, limit=None, marker=None):

    # NOTE(Dinesh_Bhor): If the limit is 0 there is no point in even going
    # to the database since nothing is going to be returned anyway.
    if limit == 0:
        return []

    sort_keys, sort_dirs = _process_sort_params(sort_keys,
                                                sort_dirs)
    filters = filters or {}
    query = model_query(context, models.FailoverSegment)

    if 'recovery_method' in filters:
        query = query.filter(models.FailoverSegment.recovery_method == filters[
            'recovery_method'])
    if 'service_type' in filters:
        query = query.filter(models.FailoverSegment.service_type == filters[
            'service_type'])

    marker_row = None
    if marker is not None:
        marker_row = model_query(context,
                                 models.FailoverSegment
                                 ).filter_by(id=marker).first()

        if not marker_row:
            raise exception.MarkerNotFound(marker=marker)

    try:
        query = sqlalchemyutils.paginate_query(query, models.FailoverSegment,
                                               limit, sort_keys,
                                               marker=marker_row,
                                               sort_dirs=sort_dirs)
    except db_exc.InvalidSortKey as e:
        raise exception.InvalidSortKey(e.message)

    return query.all()


@oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
@main_context_manager.reader
def failover_segment_get_by_id(context, segment_id):
    query = model_query(context,
                        models.FailoverSegment).filter_by(id=segment_id)

    result = query.first()
    if not result:
        raise exception.FailoverSegmentNotFound(id=segment_id)

    return result


@oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
@main_context_manager.reader
def failover_segment_get_by_uuid(context, segment_uuid):
    return _failover_segment_get_by_uuid(context, segment_uuid)


def _failover_segment_get_by_uuid(context, segment_uuid):
    query = model_query(context,
                        models.FailoverSegment).filter_by(uuid=segment_uuid)

    result = query.first()
    if not result:
        raise exception.FailoverSegmentNotFound(id=segment_uuid)

    return result


@oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
@main_context_manager.reader
def failover_segment_get_by_name(context, name):
    query = model_query(context, models.FailoverSegment).filter_by(name=name)

    result = query.first()
    if not result:
        raise exception.FailoverSegmentNotFoundByName(segment_name=name)

    return result


@oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
@main_context_manager.writer
def failover_segment_create(context, values):

    segment = models.FailoverSegment()
    segment.update(values)
    try:
        segment.save(session=context.session)
    except db_exc.DBDuplicateEntry:
        raise exception.FailoverSegmentExists(name=segment.name)

    return _failover_segment_get_by_uuid(context, segment.uuid)


@oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
@main_context_manager.writer
def failover_segment_update(context, segment_uuid, values):
    segment = _failover_segment_get_by_uuid(context, segment_uuid)

    segment.update(values)
    try:
        segment.save(session=context.session)
    except db_exc.DBDuplicateEntry:
        raise exception.FailoverSegmentExists(name=values.get('name'))

    return _failover_segment_get_by_uuid(context, segment.uuid)


@oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
@main_context_manager.writer
def failover_segment_delete(context, segment_uuid):

    count = model_query(context, models.FailoverSegment
                        ).filter_by(uuid=segment_uuid
                                    ).soft_delete(synchronize_session=False)

    if count == 0:
        raise exception.FailoverSegmentNotFound(id=segment_uuid)


# db apis for host


@oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
@main_context_manager.reader
def host_get_all_by_filters(
        context, filters=None, sort_keys=None,
        sort_dirs=None, limit=None, marker=None):

    # NOTE(Dinesh_Bhor): If the limit is 0 there is no point in even going
    # to the database since nothing is going to be returned anyway.
    if limit == 0:
        return []

    sort_keys, sort_dirs = _process_sort_params(sort_keys,
                                                sort_dirs)

    filters = filters or {}
    query = model_query(context,
                        models.Host).options(joinedload('failover_segment'))

    if 'failover_segment_id' in filters:
        query = query.filter(models.Host.failover_segment_id == filters[
            'failover_segment_id'])

    if 'type' in filters:
        query = query.filter(models.Host.type == filters['type'])

    if 'on_maintenance' in filters:
        query = query.filter(models.Host.on_maintenance == filters[
            'on_maintenance'])

    if 'reserved' in filters:
        query = query.filter(models.Host.reserved == filters['reserved'])

    marker_row = None
    if marker is not None:
        marker_row = model_query(context,
                                 models.FailoverSegment
                                 ).filter_by(id=marker).first()
        if not marker_row:
            raise exception.MarkerNotFound(marker=marker)

    try:
        query = sqlalchemyutils.paginate_query(query, models.Host, limit,
                                               sort_keys,
                                               marker=marker_row,
                                               sort_dirs=sort_dirs)
    except db_exc.InvalidSortKey as e:
        raise exception.InvalidSortKey(e.message)

    return query.all()


@oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
@main_context_manager.reader
def host_get_by_uuid(context, host_uuid):
    return _host_get_by_uuid(context, host_uuid)


def _host_get_by_uuid(context, host_uuid):
    query = model_query(context, models.Host
                        ).filter_by(uuid=host_uuid
                                    ).options(joinedload('failover_segment'))

    result = query.first()
    if not result:
        raise exception.HostNotFound(id=host_uuid)

    return result


@oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
@main_context_manager.reader
def host_get_by_id(context, host_id):
    query = model_query(context, models.Host
                        ).filter_by(id=host_id
                                    ).options(joinedload('failover_segment'))

    result = query.first()
    if not result:
        raise exception.HostNotFound(id=host_id)

    return result


@oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
@main_context_manager.reader
def host_get_by_name(context, name):
    query = model_query(context, models.Host
                        ).filter_by(name=name
                                    ).options(joinedload('failover_segment'))

    result = query.first()
    if not result:
        raise exception.HostNotFoundByName(host_name=name)

    return result


@oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
@main_context_manager.writer
def host_create(context, values):
    host = models.Host()
    host.update(values)
    try:
        host.save(session=context.session)
    except db_exc.DBDuplicateEntry:
        raise exception.HostExists(name=host.name)

    return _host_get_by_uuid(context, host.uuid)


@oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
@main_context_manager.writer
def host_update(context, host_uuid, values):
    host = _host_get_by_uuid(context, host_uuid)

    host.update(values)
    try:
        host.save(session=context.session)
    except db_exc.DBDuplicateEntry:
        raise exception.HostExists(name=values.get('name'))

    return _host_get_by_uuid(context, host.uuid)


@oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
@main_context_manager.writer
def host_delete(context, host_uuid):

    count = model_query(context, models.Host
                        ).filter_by(uuid=host_uuid
                                    ).soft_delete(synchronize_session=False)

    if count == 0:
        raise exception.HostNotFound(id=host_uuid)


# db apis for notifications


@oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
@main_context_manager.reader
def notifications_get_all_by_filters(
        context, filters=None, sort_keys=None,
        sort_dirs=None, limit=None, marker=None):

    # NOTE(Dinesh_Bhor): If the limit is 0 there is no point in even going
    # to the database since nothing is going to be returned anyway.
    if limit == 0:
        return []

    sort_keys, sort_dirs = _process_sort_params(sort_keys,
                                                sort_dirs)

    filters = filters or {}
    query = model_query(context, models.Notification)

    if 'source_host_uuid' in filters:
        query = query.filter(models.Notification.source_host_uuid == filters[
            'source_host_uuid'])

    if 'type' in filters:
        query = query.filter(models.Notification.type == filters['type'])

    if 'status' in filters:
        status = filters['status']
        if isinstance(status, (list, tuple, set, frozenset)):
            column_attr = getattr(models.Notification, 'status')
            query = query.filter(column_attr.in_(status))
        else:
            query = query.filter(models.Notification.status == status)

    if 'generated-since' in filters:
        generated_since = timeutils.normalize_time(filters['generated-since'])
        query = query.filter(
            models.Notification.generated_time >= generated_since)

    marker_row = None
    if marker is not None:
        marker_row = model_query(context,
                                 models.Notification
                                 ).filter_by(id=marker).first()
        if not marker_row:
            raise exception.MarkerNotFound(marker=marker)

    try:
        query = sqlalchemyutils.paginate_query(query, models.Notification,
                                               limit,
                                               sort_keys,
                                               marker=marker_row,
                                               sort_dirs=sort_dirs)
    except db_exc.InvalidSortKey as err:
        raise exception.InvalidSortKey(err.message)

    return query.all()


@oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
@main_context_manager.reader
def notification_get_by_uuid(context, notification_uuid):
    return _notification_get_by_uuid(context, notification_uuid)


def _notification_get_by_uuid(context, notification_uuid):
    query = model_query(context, models.Notification
                        ).filter_by(notification_uuid=notification_uuid
                                    )

    result = query.first()
    if not result:
        raise exception.NotificationNotFound(id=notification_uuid)

    return result


@oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
@main_context_manager.reader
def notification_get_by_id(context, notification_id):
    query = model_query(context, models.Notification
                        ).filter_by(id=notification_id
                                    )

    result = query.first()
    if not result:
        raise exception.NotificationNotFound(id=notification_id)

    return result


@oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
@main_context_manager.writer
def notification_create(context, values):
    notification = models.Notification()
    notification.update(values)

    notification.save(session=context.session)

    return _notification_get_by_uuid(context, notification.notification_uuid)


@oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
@main_context_manager.writer
def notification_update(context, notification_uuid, values):
    notification = _notification_get_by_uuid(context, notification_uuid)

    notification.update(values)

    notification.save(session=context.session)

    return _notification_get_by_uuid(context, notification.notification_uuid)


@oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
@main_context_manager.writer
def notification_delete(context, notification_uuid):

    count = model_query(context, models.Notification
                        ).filter_by(notification_uuid=notification_uuid
                                    ).soft_delete(synchronize_session=False)

    if count == 0:
        raise exception.NotificationNotFound(id=notification_uuid)
