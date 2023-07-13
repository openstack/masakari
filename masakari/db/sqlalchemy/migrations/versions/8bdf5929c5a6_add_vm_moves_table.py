# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Add vm moves table

Revision ID: 8bdf5929c5a6
Revises: 8f848eb45d03
Create Date: 2023-07-13 12:13:42.240598
"""

from alembic import op
from oslo_db.sqlalchemy import types as oslo_db_types
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '8bdf5929c5a6'
down_revision = '8f848eb45d03'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'vmoves',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column(
            'deleted',
            oslo_db_types.SoftDeleteInteger(),
            nullable=True,
        ),
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('notification_uuid', sa.String(length=36), nullable=False),
        sa.Column('instance_uuid', sa.String(length=36), nullable=False),
        sa.Column('instance_name', sa.String(length=255), nullable=False),
        sa.Column('source_host', sa.String(length=255), nullable=True),
        sa.Column('dest_host', sa.String(length=255), nullable=True),
        sa.Column('start_time', sa.DateTime(), nullable=True),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('type', sa.String(length=36), nullable=True),
        sa.Column('status', sa.String(length=255), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid', name='uniq_vmove0uuid'),
    )
