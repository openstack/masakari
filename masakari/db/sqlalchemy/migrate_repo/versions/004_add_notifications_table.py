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

from migrate.changeset import UniqueConstraint
from sqlalchemy import Column, MetaData, Table
from sqlalchemy import Integer, DateTime, String, Enum, Text


def define_notifications_table(meta):

    notifications = Table('notifications',
                          meta,
                          Column('created_at', DateTime),
                          Column('updated_at', DateTime),
                          Column('deleted_at', DateTime),
                          Column('deleted', Integer),
                          Column('id', Integer, primary_key=True,
                                 nullable=False),
                          Column('notification_uuid', String(36),
                                 nullable=False),
                          Column('generated_time', DateTime, nullable=False),
                          Column('source_host_uuid', String(36), nullable=False
                                 ),
                          Column('type', String(length=36), nullable=False),
                          Column('payload', Text),
                          Column('status',
                                 Enum('new', 'running', 'error', 'failed',
                                      'ignored', 'finished',
                                      name='notification_status'),
                                 nullable=False),
                          UniqueConstraint('notification_uuid',
                                           name='uniq_notifications0uuid'),
                          mysql_engine='InnoDB',
                          mysql_charset='utf8',
                          extend_existing=True)

    return notifications


def upgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine
    table = define_notifications_table(meta)
    table.create()
