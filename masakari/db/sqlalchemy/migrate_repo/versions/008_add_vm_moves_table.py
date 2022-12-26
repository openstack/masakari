# Copyright(c) 2022 Inspur
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from migrate.changeset import UniqueConstraint
from sqlalchemy import Column, MetaData, Table
from sqlalchemy import Integer, DateTime, String, Text


def define_vm_moves_table(meta):

    vm_moves = Table('vmoves',
                     meta,
                     Column('created_at', DateTime),
                     Column('updated_at', DateTime),
                     Column('deleted_at', DateTime),
                     Column('deleted', Integer),
                     Column('id', Integer, primary_key=True, nullable=False),
                     Column('uuid', String(36), nullable=False),
                     Column('notification_uuid', String(36), nullable=False),
                     Column('instance_uuid', String(36), nullable=False),
                     Column('instance_name', String(255), nullable=False),
                     Column('source_host', String(255), nullable=True),
                     Column('dest_host', String(255), nullable=True),
                     Column('start_time', DateTime, nullable=True),
                     Column('end_time', DateTime, nullable=True),
                     Column('type', String(36), nullable=True),
                     Column('status', String(36), nullable=True),
                     Column('message', Text, nullable=True),
                     UniqueConstraint('uuid', name='uniq_vmove0uuid'),
                     mysql_engine='InnoDB',
                     mysql_charset='utf8',
                     extend_existing=True)

    return vm_moves


def upgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine
    table = define_vm_moves_table(meta)
    table.create()
