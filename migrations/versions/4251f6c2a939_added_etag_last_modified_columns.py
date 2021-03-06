"""Added ETag & Last-Modified columns

Revision ID: 4251f6c2a939
Revises: daf00bd7bd65
Create Date: 2018-07-16 19:02:34.421149

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4251f6c2a939'
down_revision = 'daf00bd7bd65'
branch_labels = None
depends_on = None


def upgrade():
  # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('feed', sa.Column('etag', sa.String(), nullable=True))
    op.add_column('feed', sa.Column('last_modified', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
  # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('feed', 'last_modified')
    op.drop_column('feed', 'etag')
    # ### end Alembic commands ###
