from alembic import op
import sqlalchemy as sa
revision = "c9a01f27b001"
down_revision = "bca06b0bc606"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("users", sa.Column("preferred_currency", sa.String(3), server_default="USD", nullable=False))
    op.add_column("users", sa.Column("reminders_enabled", sa.Boolean(), server_default="true", nullable=False))
    op.create_check_constraint("ck_users_preferred_currency", "users", "preferred_currency IN ('USD','EUR','GBP','CAD','JPY','INR')")

def downgrade():
    op.drop_constraint("ck_users_preferred_currency", "users", type_="check")
    op.drop_column("users", "reminders_enabled")
    op.drop_column("users", "preferred_currency")
