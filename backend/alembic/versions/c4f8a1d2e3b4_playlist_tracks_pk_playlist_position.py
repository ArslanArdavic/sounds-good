"""playlist_tracks primary key playlist_id + position

Revision ID: c4f8a1d2e3b4
Revises: 6b10ba2c0a55
Create Date: 2026-03-21

Spotify playlists may list the same track more than once; the previous
(playlist_id, track_id) PK forbade that. Rows are keyed by slot order.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4f8a1d2e3b4"
down_revision: Union[str, Sequence[str], None] = "6b10ba2c0a55"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Recreate playlist_tracks with PK (playlist_id, position)."""
    op.create_table(
        "playlist_tracks_new",
        sa.Column("playlist_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("track_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["playlist_id"], ["playlists.id"]),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"]),
        sa.PrimaryKeyConstraint("playlist_id", "position"),
    )
    op.execute(
        """
        INSERT INTO playlist_tracks_new (playlist_id, position, track_id)
        SELECT playlist_id, position, track_id FROM playlist_tracks
        """
    )
    op.drop_table("playlist_tracks")
    op.rename_table("playlist_tracks_new", "playlist_tracks")


def downgrade() -> None:
    """Restore PK (playlist_id, track_id); duplicate slots collapse to one row each."""
    op.create_table(
        "playlist_tracks_old",
        sa.Column("playlist_id", sa.Uuid(), nullable=False),
        sa.Column("track_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["playlist_id"], ["playlists.id"]),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"]),
        sa.PrimaryKeyConstraint("playlist_id", "track_id"),
    )
    op.execute(
        """
        INSERT INTO playlist_tracks_old (playlist_id, track_id, position)
        SELECT playlist_id, track_id, MIN(position) AS position
        FROM playlist_tracks
        GROUP BY playlist_id, track_id
        """
    )
    op.drop_table("playlist_tracks")
    op.rename_table("playlist_tracks_old", "playlist_tracks")
