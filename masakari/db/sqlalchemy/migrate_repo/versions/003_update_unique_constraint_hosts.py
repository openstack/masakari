# Copyright 2016 NTT DATA
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
import sqlalchemy
from sqlalchemy import Table


def upgrade(migrate_engine):
    meta = sqlalchemy.MetaData()
    meta.bind = migrate_engine

    hosts_table = Table('hosts', meta, autoload=True)
    failover_segments = Table('failover_segments', meta, autoload=True)
    # NOTE(Dinesh_Bhor) We need to drop foreign keys first because unique
    # constraints that we want to delete depend on them. So drop the fk and
    # recreate it again after unique constraint deletion.
    cons_fk = ForeignKeyConstraint([hosts_table.c.failover_segment_id],
                                   [failover_segments.c.uuid],
                                   name="fk_failover_segments_uuid")
    cons_fk.drop(engine=migrate_engine)

    cons_unique = UniqueConstraint('failover_segment_id', 'name', 'deleted',
                                   name='uniq_host0name0deleted',
                                   table=hosts_table)
    cons_unique.drop(engine=migrate_engine)
    # Create an updated unique constraint
    updated_cons_unique = UniqueConstraint('name', 'deleted',
                                           name='uniq_host0name0deleted',
                                           table=hosts_table)
    cons_fk.create()
    updated_cons_unique.create()
