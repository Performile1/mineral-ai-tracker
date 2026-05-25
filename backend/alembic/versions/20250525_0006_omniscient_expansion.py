"""omniscient_expansion

Revision ID: 20250525_0006
Revises: 20250525_0005
Create Date: 2025-05-25 00:06:00.000000

Sprint 16 Phase 1 — The Omniscient Expansion (Database Foundation)

Schema changes:
  supply_chain_nodes:
    + buyout_probability_score  NUMERIC(5,2) NULL
        Written by the Sovereign M&A Predictor agent (Phase 2).

  labor_disputes:
    + is_early_warning  BOOLEAN NOT NULL DEFAULT FALSE
        Set to TRUE by the Local Sentiment Crawler when it detects
        a "Simmering/Rumor" signal (severity level 0 equivalent)
        before a formal dispute is registered.

  transit_metrics:
    + UNIQUE INDEX ix_transit_metrics_index_name (index_name)
        Required so Phase 2's Chokepoint Oracle can use
        INSERT ... ON CONFLICT (index_name) DO UPDATE instead of
        the legacy unconditional INSERT.

  secondary_supply:
    + UNIQUE INDEX ix_secondary_supply_material_name (material_name)
        Required so Phase 2's Secondary Supply Engine can upsert
        per material without duplicates.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250525_0006"
down_revision: Union[str, None] = "20250525_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # supply_chain_nodes — M&A Predictor score                            #
    # ------------------------------------------------------------------ #
    op.add_column(
        "supply_chain_nodes",
        sa.Column(
            "buyout_probability_score",
            sa.Numeric(precision=5, scale=2),
            nullable=True,
        ),
    )

    # ------------------------------------------------------------------ #
    # labor_disputes — early-warning sentinel                             #
    # ------------------------------------------------------------------ #
    op.add_column(
        "labor_disputes",
        sa.Column(
            "is_early_warning",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )

    # ------------------------------------------------------------------ #
    # transit_metrics — unique index for ON CONFLICT upserts              #
    # ------------------------------------------------------------------ #
    op.create_index(
        "ix_transit_metrics_index_name",
        "transit_metrics",
        ["index_name"],
        unique=True,
    )

    # ------------------------------------------------------------------ #
    # secondary_supply — unique index for ON CONFLICT upserts             #
    # ------------------------------------------------------------------ #
    op.create_index(
        "ix_secondary_supply_material_name",
        "secondary_supply",
        ["material_name"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_secondary_supply_material_name", table_name="secondary_supply")
    op.drop_index("ix_transit_metrics_index_name", table_name="transit_metrics")
    op.drop_column("labor_disputes", "is_early_warning")
    op.drop_column("supply_chain_nodes", "buyout_probability_score")
