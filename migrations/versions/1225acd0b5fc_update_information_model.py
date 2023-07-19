"""Update Information model

Revision ID: 1225acd0b5fc
Revises: 203419a40925
Create Date: 2023-07-18 20:59:24.657540

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1225acd0b5fc'
down_revision = '203419a40925'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('information', schema=None) as batch_op:
        batch_op.add_column(sa.Column('conversation_sid', sa.String(length=50), nullable=False))
        batch_op.drop_column('conversation_index')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('information', schema=None) as batch_op:
        batch_op.add_column(sa.Column('conversation_index', sa.INTEGER(), nullable=False))
        batch_op.drop_column('conversation_sid')

    # ### end Alembic commands ###
