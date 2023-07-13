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

"""Initial revision

Revision ID: 8f848eb45d03
Revises:
Create Date: 2023-07-13 12:00:07.851502
"""

from alembic import op
from oslo_db.sqlalchemy import types as oslo_db_types
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '8f848eb45d03'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'failover_segments',
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
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('service_type', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column(
            'recovery_method',
            sa.Enum(
                'auto',
                'reserved_host',
                'auto_priority',
                'rh_priority',
                name='recovery_methods',
            ),
            nullable=False,
        ),
        sa.Column('enabled', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'name', 'deleted', name='uniq_segment0name0deleted'
        ),
        sa.UniqueConstraint('uuid', name='uniq_segments0uuid'),
    )
    op.create_index(
        'segments_service_type_idx',
        'failover_segments',
        ['service_type'],
        unique=False,
    )
    op.create_table(
        'notifications',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column(
            'deleted',
            oslo_db_types.SoftDeleteInteger(),
            nullable=True,
        ),
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('notification_uuid', sa.String(length=36), nullable=False),
        sa.Column('generated_time', sa.DateTime(), nullable=False),
        sa.Column('source_host_uuid', sa.String(length=36), nullable=False),
        sa.Column('type', sa.String(length=36), nullable=False),
        sa.Column('payload', sa.Text(), nullable=True),
        sa.Column(
            'status',
            sa.Enum(
                'new',
                'running',
                'error',
                'failed',
                'ignored',
                'finished',
                name='notification_status',
            ),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'notification_uuid', name='uniq_notification0uuid'
        ),
    )
    op.create_table(
        'hosts',
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
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('reserved', sa.Boolean(), nullable=True),
        sa.Column('type', sa.String(length=255), nullable=False),
        sa.Column('control_attributes', sa.Text(), nullable=False),
        sa.Column('failover_segment_id', sa.String(length=36), nullable=False),
        sa.Column('on_maintenance', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(
            ['failover_segment_id'],
            ['failover_segments.uuid'],
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'deleted', name='uniq_host0name0deleted'),
        sa.UniqueConstraint('uuid', name='uniq_host0uuid'),
    )
    op.create_index('hosts_type_idx', 'hosts', ['type'], unique=False)
