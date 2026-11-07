"""Complete MVP workflows: OCR metadata, goals, recurring rules and moderation.

Revision ID: 7d15f8a34b20
Revises: 0062c1f62474
Create Date: 2026-11-07
"""
from alembic import op
import sqlalchemy as sa

revision = "7d15f8a34b20"
down_revision = "0062c1f62474"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("receipts", sa.Column("ocr_text", sa.Text(), nullable=False, server_default=""))
    op.add_column("receipts", sa.Column("ocr_fields", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.add_column("receipts", sa.Column("ocr_confidence", sa.Float(), nullable=True))

    op.create_table(
        "goals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("target_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("current_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("note", sa.String(500), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_goals_user_id", "goals", ["user_id"])

    op.create_table(
        "recurring_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(12), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("source_account_id", sa.String(36), sa.ForeignKey("financial_accounts.id"), nullable=True),
        sa.Column("target_account_id", sa.String(36), sa.ForeignKey("financial_accounts.id"), nullable=True),
        sa.Column("category_id", sa.String(36), sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("description", sa.String(140), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("frequency", sa.String(12), nullable=False),
        sa.Column("next_run_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_recurring_rules_user_id", "recurring_rules", ["user_id"])

    op.create_table(
        "recurring_executions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("rule_id", sa.String(36), sa.ForeignKey("recurring_rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scheduled_on", sa.Date(), nullable=False),
        sa.Column("transaction_id", sa.String(36), sa.ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("rule_id", "scheduled_on", name="uq_recurring_rule_date"),
    )
    op.create_index("ix_recurring_executions_rule_id", "recurring_executions", ["rule_id"])

    op.create_table(
        "message_reactions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("message_id", sa.String(36), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("emoji", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("message_id", "user_id", "emoji", name="uq_message_reaction"),
    )
    op.create_index("ix_message_reactions_message_id", "message_reactions", ["message_id"])
    op.create_index("ix_message_reactions_user_id", "message_reactions", ["user_id"])

    op.create_table(
        "content_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("reporter_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("group_id", sa.String(36), sa.ForeignKey("community_groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message_id", sa.String(36), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=True),
        sa.Column("reason", sa.String(40), nullable=False),
        sa.Column("details", sa.String(1000), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_content_reports_reporter_id", "content_reports", ["reporter_id"])
    op.create_index("ix_content_reports_group_id", "content_reports", ["group_id"])

    op.create_table(
        "user_blocks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("blocker_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("blocked_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("blocker_id", "blocked_id", name="uq_user_block"),
    )
    op.create_index("ix_user_blocks_blocker_id", "user_blocks", ["blocker_id"])
    op.create_index("ix_user_blocks_blocked_id", "user_blocks", ["blocked_id"])


def downgrade():
    op.drop_index("ix_user_blocks_blocked_id", table_name="user_blocks")
    op.drop_index("ix_user_blocks_blocker_id", table_name="user_blocks")
    op.drop_table("user_blocks")
    op.drop_index("ix_content_reports_group_id", table_name="content_reports")
    op.drop_index("ix_content_reports_reporter_id", table_name="content_reports")
    op.drop_table("content_reports")
    op.drop_index("ix_message_reactions_user_id", table_name="message_reactions")
    op.drop_index("ix_message_reactions_message_id", table_name="message_reactions")
    op.drop_table("message_reactions")
    op.drop_index("ix_recurring_executions_rule_id", table_name="recurring_executions")
    op.drop_table("recurring_executions")
    op.drop_index("ix_recurring_rules_user_id", table_name="recurring_rules")
    op.drop_table("recurring_rules")
    op.drop_index("ix_goals_user_id", table_name="goals")
    op.drop_table("goals")
    op.drop_column("receipts", "ocr_confidence")
    op.drop_column("receipts", "ocr_fields")
    op.drop_column("receipts", "ocr_text")
