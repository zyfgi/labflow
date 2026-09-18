"""light process collaboration: drop review/approval workflows

- weekly reports: submitted/reviewed -> published, returned -> draft;
  submitted_at renamed to published_at; new weekly_report_comments table;
  reviewer_id/reviewed_at/review_comment kept as legacy unused columns
- bookings: pending/approved -> reserved, rejected -> cancelled
  (approved_by/approved_at kept as legacy unused columns)
- tasks: review status removed (rows moved to in_progress)
- users: wechat binding columns
- equipment: qr_token column
- new wechat_binding_codes table

Revision ID: c8e1f0a2b3d4
Revises: b713192d6c44
Create Date: 2026-09-18
"""

import sqlalchemy as sa
from alembic import op

revision = "c8e1f0a2b3d4"
down_revision = "b713192d6c44"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- weekly reports: two states only ----
    op.execute(
        "UPDATE weekly_reports SET status = 'published' "
        "WHERE status IN ('submitted', 'reviewed')"
    )
    op.execute("UPDATE weekly_reports SET status = 'draft' WHERE status = 'returned'")
    op.alter_column("weekly_reports", "submitted_at", new_column_name="published_at")
    op.create_table(
        "weekly_report_comments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.String(length=2000), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["weekly_reports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_weekly_report_comments_report_id", "weekly_report_comments", ["report_id"]
    )
    op.create_index(
        "ix_weekly_report_comments_user_id", "weekly_report_comments", ["user_id"]
    )

    # ---- bookings: conflict check replaces approval ----
    op.execute(
        "UPDATE equipment_bookings SET status = 'reserved' "
        "WHERE status IN ('pending', 'approved')"
    )
    op.execute(
        "UPDATE equipment_bookings SET status = 'cancelled' WHERE status = 'rejected'"
    )

    # ---- tasks: the review state is gone ----
    op.execute("UPDATE tasks SET status = 'in_progress' WHERE status = 'review'")

    # ---- wechat ----
    op.add_column("users", sa.Column("wechat_openid", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("wechat_bound_at", sa.DateTime(), nullable=True))
    op.create_index("ix_users_wechat_openid", "users", ["wechat_openid"], unique=True)
    op.create_table(
        "wechat_binding_codes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("used_by", sa.Integer(), nullable=True),
        sa.Column("remark", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["used_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wechat_binding_codes_code", "wechat_binding_codes", ["code"], unique=True)

    # ---- equipment QR tags ----
    op.add_column("equipment", sa.Column("qr_token", sa.String(length=64), nullable=True))
    op.create_index("ix_equipment_qr_token", "equipment", ["qr_token"], unique=True)


def downgrade() -> None:
    # note: the removed states cannot be reconstructed exactly; published rows
    # collapse back to submitted, reserved back to pending
    op.drop_index("ix_equipment_qr_token", table_name="equipment")
    op.drop_column("equipment", "qr_token")
    op.drop_index("ix_wechat_binding_codes_code", table_name="wechat_binding_codes")
    op.drop_table("wechat_binding_codes")
    op.drop_index("ix_users_wechat_openid", table_name="users")
    op.drop_column("users", "wechat_bound_at")
    op.drop_column("users", "wechat_openid")
    op.execute(
        "UPDATE weekly_reports SET status = 'submitted' WHERE status = 'published'"
    )
    op.alter_column("weekly_reports", "published_at", new_column_name="submitted_at")
    op.drop_index("ix_weekly_report_comments_user_id", table_name="weekly_report_comments")
    op.drop_index(
        "ix_weekly_report_comments_report_id", table_name="weekly_report_comments"
    )
    op.drop_table("weekly_report_comments")
    op.execute(
        "UPDATE equipment_bookings SET status = 'pending' WHERE status = 'reserved'"
    )
