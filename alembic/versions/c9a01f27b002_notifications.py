from alembic import op
import sqlalchemy as sa
revision = "c9a01f27b002"
down_revision = "c9a01f27b001"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("notifications", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("event_key", sa.String(160), nullable=False, unique=True), sa.Column("message", sa.String(255), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("read_at", sa.DateTime(timezone=True)))
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])

def downgrade():
    op.drop_table("notifications")
