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

from migrate import ForeignKeyConstraint, UniqueConstraint
from sqlalchemy import Column, MetaData, Table, Index
from sqlalchemy import Integer, DateTime, String, Boolean, Text


def define_hosts_table(meta):
    failover_segments = Table('failover_segments', meta, autoload=True)
    hosts = Table('hosts',
                  meta,
                  Column('created_at', DateTime, nullable=False),
                  Column('updated_at', DateTime),
                  Column('deleted_at', DateTime),
                  Column('deleted', Integer),
                  Column('id', Integer, primary_key=True,
                         nullable=False),
                  Column('uuid', String(36), nullable=False),
                  Column('name', String(255), nullable=False),
                  Column('reserved', Boolean, default=False),
                  Column('type', String(255), nullable=False),
                  Column('control_attributes', Text, nullable=False),
                  Column('failover_segment_id', String(36), nullable=False),
                  Column('on_maintenance', Boolean, default=False),
                  UniqueConstraint('failover_segment_id', 'name', 'deleted',
                                   name='uniq_host0name0deleted'),
                  UniqueConstraint('uuid', name='uniq_host0uuid'),
                  ForeignKeyConstraint(columns=['failover_segment_id'],
                                       refcolumns=[failover_segments.c.uuid],
                                       name='fk_failover_segments_uuid'),
                  Index('hosts_type_idx', 'type'),
                  mysql_engine='InnoDB',
                  mysql_charset='utf8',
                  extend_existing=True)

    return hosts


def upgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine
    table = define_hosts_table(meta)
    table.create()
