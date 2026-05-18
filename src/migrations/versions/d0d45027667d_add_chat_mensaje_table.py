"""add chat_mensaje table

Revision ID: d0d45027667d
Revises: 
Create Date: 2026-05-12 23:22:11.909290

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'd0d45027667d'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Solo crea la tabla chat_mensaje.
    # Las columnas FK deben ser BIGINT UNSIGNED para coincidir con auditoria.id
    # y usuario.id que son bigint unsigned en la BD existente.
    op.create_table(
        'chat_mensaje',
        sa.Column('id',           mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column('auditoria_id', mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column('autor_id',     mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column('contenido',    sa.Text(),   nullable=False),
        sa.Column('creado_en',    sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['auditoria_id'], ['auditoria.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['autor_id'],     ['usuario.id']),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
    )


def downgrade():
    op.drop_table('chat_mensaje')
