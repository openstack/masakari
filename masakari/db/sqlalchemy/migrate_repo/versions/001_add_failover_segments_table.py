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

from migrate import changeset
from sqlalchemy import Column, MetaData, Table, Index
from sqlalchemy import Integer, DateTime, String, Enum, Text


def define_failover_segments_table(meta):

    failover_segments = Table('failover_segments',
                              meta,
                              Column('created_at', DateTime, nullable=False),
                              Column('updated_at', DateTime),
                              Column('deleted_at', DateTime),
                              Column('deleted', Integer),
                              Column('id', Integer, primary_key=True,
                                     nullable=False),
                              Column('uuid', String(36), nullable=False),
                              Column('name', String(255), nullable=False),
                              Column('service_type', String(255),
                                     nullable=False),
                              Column('description', Text),
                              Column('recovery_method',
                                     Enum('auto', 'reserved_host',
                                          'auto_priority',
                                          'rh_priority',
                                          name='recovery_methods'),
                                     nullable=False),
                              changeset.UniqueConstraint(
                                  'name', 'deleted',
                                  name='uniq_segment0name0deleted'
                              ),
                              changeset.UniqueConstraint(
                                  'uuid',
                                  name='uniq_segments0uuid'),
                              Index('segments_service_type_idx',
                                    'service_type'),
                              mysql_engine='InnoDB',
                              mysql_charset='utf8',
                              extend_existing=True)

    return failover_segments


def upgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine
    table = define_failover_segments_table(meta)
    table.create()
