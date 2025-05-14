# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Add vm moves table

Revision ID: 13adff5efb9a
Revises: 8bdf5929c5a6
Create Date: 2025-05-13 14:10:42.220612
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '13adff5efb9a'
down_revision = '8bdf5929c5a6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('notifications') as batch_op:
        batch_op.add_column(sa.Column('failover_segment_uuid',
                                      sa.String(length=36)))
        batch_op.add_column(sa.Column('message', sa.Text()))
