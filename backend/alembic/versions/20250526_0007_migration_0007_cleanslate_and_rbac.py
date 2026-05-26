"""migration_0007_cleanslate_and_rbac

Revision ID: 20250526_0007
Revises: 20250525_0006
Create Date: 2026-05-26 07:30:00.000000

Sprint 18 — The CleanSlate & RBAC Secure

Schema changes:
  users:
    + is_admin  BOOLEAN NOT NULL DEFAULT FALSE
        Used by get_admin_user() in api/deps.py to gate all /api/admin/* routes.
        Set manually by the node operator: UPDATE users SET is_admin=TRUE WHERE email='…';

  supply_chain_edges:
    - is_expiry_estimated  (Skuld G — was dead code; always set to FALSE, never read by UI)
        Dropped from INSERT/ON CONFLICT in engines/nexus_engine.py (same commit).

  alert_configs:
    - telegram_chat_id     (Skuld Q6 — moved to notification_preferences JSONB)
    - discord_webhook_url  (Skuld Q6 — moved to notification_preferences JSONB)
        Both fields are now stored as:
          notification_preferences->>'telegram_chat_id'
          notification_preferences->>'discord_webhook_url'
        Code updated in api/alerts.py and ml/slm_orchestrator.py (same commit).

Data migration for alert_configs:
  Existing telegram_chat_id / discord_webhook_url values are merged into
  notification_preferences JSONB before the columns are dropped.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20250526_0007"
down_revision: Union[str, None] = "20250525_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # users — RBAC admin flag                                             #
    # ------------------------------------------------------------------ #
    op.add_column(
        "users",
        sa.Column(
            "is_admin",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )

    # ------------------------------------------------------------------ #
    # alert_configs — migrate webhook contacts to JSONB before drop       #
    # ------------------------------------------------------------------ #
    # Copy existing telegram_chat_id / discord_webhook_url values into the
    # notification_preferences JSONB column so no data is lost on upgrade.
    op.execute("""
        UPDATE alert_configs
        SET notification_preferences = notification_preferences
            || jsonb_build_object(
                'telegram_chat_id',    COALESCE(telegram_chat_id, ''),
                'discord_webhook_url', COALESCE(discord_webhook_url, '')
               )
        WHERE telegram_chat_id IS NOT NULL
           OR discord_webhook_url IS NOT NULL
    """)

    op.drop_column("alert_configs", "telegram_chat_id")
    op.drop_column("alert_configs", "discord_webhook_url")

    # ------------------------------------------------------------------ #
    # supply_chain_edges — drop dead-code column                          #
    # ------------------------------------------------------------------ #
    op.drop_column("supply_chain_edges", "is_expiry_estimated")


def downgrade() -> None:
    # supply_chain_edges
    op.add_column(
        "supply_chain_edges",
        sa.Column(
            "is_expiry_estimated",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
    )

    # alert_configs — restore columns (data loss for values merged into JSONB
    # is unavoidable on downgrade; columns come back as NULL)
    op.add_column(
        "alert_configs",
        sa.Column("discord_webhook_url", sa.Text(), nullable=True),
    )
    op.add_column(
        "alert_configs",
        sa.Column("telegram_chat_id", sa.String(255), nullable=True),
    )

    # users
    op.drop_column("users", "is_admin")
