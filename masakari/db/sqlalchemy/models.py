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

from oslo_db.sqlalchemy import models
from oslo_utils import timeutils
from sqlalchemy import (Column, DateTime, Index, Integer, Enum, String,
                        schema)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import orm
from sqlalchemy import ForeignKey, Boolean, Text


BASE = declarative_base()


class MasakariTimestampMixin(object):
    # Note(tpatil): timeutils.utcnow() method return microseconds part but db
    # doesn't store it because of which subsequent calls to get resources
    # from the same db session object instance doesn't return microsecond for
    # datetime fields. To avoid this discrepancy, removed microseconds from
    # datetime fields so that there is no need to remove it for create/update
    # cases in the respective versioned objects.
    created_at = Column(DateTime, default=lambda: timeutils.utcnow().replace(
                        microsecond=0))
    updated_at = Column(DateTime, onupdate=lambda: timeutils.utcnow().replace(
                        microsecond=0))


class MasakariAPIBase(MasakariTimestampMixin, models.ModelBase):
    """Base class for MasakariAPIBase Models."""

    metadata = None

    def __copy__(self):
        """Implement a safe copy.copy().

        SQLAlchemy-mapped objects travel with an object
        called an InstanceState, which is pegged to that object
        specifically and tracks everything about that object.  It's
        critical within all attribute operations, including gets
        and deferred loading.   This object definitely cannot be
        shared among two instances, and must be handled.

        The copy routine here makes use of session.merge() which
        already essentially implements a "copy" style of operation,
        which produces a new instance with a new InstanceState and copies
        all the data along mapped attributes without using any SQL.

        The mode we are using here has the caveat that the given object
        must be "clean", e.g. that it has no database-loaded state
        that has been updated and not flushed.   This is a good thing,
        as creating a copy of an object including non-flushed, pending
        database state is probably not a good idea; neither represents
        what the actual row looks like, and only one should be flushed.

        """
        session = orm.Session()

        copy = session.merge(self, load=False)
        session.expunge(copy)
        return copy


class FailoverSegment(BASE, MasakariAPIBase, models.SoftDeleteMixin):
    """Represents a failover segment."""
    __tablename__ = 'failover_segments'
    __table_args__ = (
        schema.UniqueConstraint("name", "deleted",
                                name="uniq_segment0name0deleted"),
        schema.UniqueConstraint('uuid', name='uniq_segments0uuid'),
        Index('segments_service_type_idx', 'service_type'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(36), nullable=False)
    name = Column(String(255), nullable=False)
    service_type = Column(String(255), nullable=False)
    enabled = Column(Boolean, default=True)
    description = Column(Text)
    recovery_method = Column(Enum('auto', 'reserved_host', 'auto_priority',
                                  'rh_priority',
                                  name='recovery_methods'), nullable=False)


class Host(BASE, MasakariAPIBase, models.SoftDeleteMixin):
    """Represents a host."""
    __tablename__ = 'hosts'
    __table_args__ = (
        schema.UniqueConstraint("name", "deleted",
                                name="uniq_host0name0deleted"),
        schema.UniqueConstraint('uuid', name='uniq_host0uuid'),
        Index('hosts_type_idx', 'type'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(36), nullable=False)
    name = Column(String(255), nullable=False)
    reserved = Column(Boolean, default=False)
    type = Column(String(255), nullable=False)
    control_attributes = Column(Text, nullable=False)
    on_maintenance = Column(Boolean, default=False)
    failover_segment_id = Column(String(36),
                                 ForeignKey('failover_segments.uuid'),
                                 nullable=False)

    failover_segment = orm.relationship(FailoverSegment,
                                        backref=orm.backref('hosts'),
                                        foreign_keys=failover_segment_id,
                                        primaryjoin='and_(Host.'
                                                    'failover_segment_id=='
                                                    'FailoverSegment.uuid,'
                                                    'Host.deleted==0)')


class Notification(BASE, MasakariAPIBase, models.SoftDeleteMixin):
    """Represents a notification."""
    __tablename__ = 'notifications'
    __table_args__ = (
        schema.UniqueConstraint('notification_uuid',
                                name='uniq_notification0uuid'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    notification_uuid = Column(String(36), nullable=False)
    generated_time = Column(DateTime, nullable=False)
    type = Column(String(36), nullable=False)
    payload = Column(Text)
    status = Column(Enum('new', 'running', 'error', 'failed',
                         'ignored', 'finished', name='notification_status'),
                    nullable=False)
    source_host_uuid = Column(String(36), nullable=False)
