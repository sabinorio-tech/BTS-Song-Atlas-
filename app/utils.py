"""Data loading and semantic helpers for the Streamlit application."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = BASE_DIR / "data" / "processed"
PERSONAL_DIR = PROCESSED_DIR / "personal_atlas"


def canonical_title(title: str) -> str:
    title = str(title).lower()
    title = re.sub(r"\s*-\s*(live|japanese ver\.?)$", "", title)
    title = re.sub(r"\s*\(.*?\)", "", title)
    return re.sub(r"[^a-z0-9가-힣ぁ-ゔァ-ヴー一-龯\s]", "", title).strip()


def detect_languages(text: str) -> str:
    """Infer display languages from writing systems in the lyric text."""
    text = str(text)
    languages: list[str] = []
    if re.search(r"[가-힣]", text):
        languages.append("Korean")
    if re.search(r"[A-Za-z]", text):
        languages.append("English")
    if re.search(r"[ぁ-ゔァ-ヴー]", text):
        languages.append("Japanese")
    return ", ".join(languages) or "Unknown"


@st.cache_data(show_spinner=False)
def load_dashboard_data() -> pd.DataFrame:
    """Return the immutable atlas enriched with fields used by the UI."""
    atlas = pd.read_csv(PROCESSED_DIR / "song_atlas.csv")
    master = pd.read_csv(PROCESSED_DIR / "song_master.csv")
    albums = pd.read_csv(PROCESSED_DIR / "spotify_albums_clean.csv")

    track_fields = master[
        [
            "track_id",
            "album_id",
            "duration_ms",
            "release_date",
            "genius_url",
            "total_tracks",
        ]
    ]
    data = atlas.merge(track_fields, on="track_id", how="left")
    data = data.merge(albums[["album_id", "album_type"]], on="album_id", how="left")
    data["album_type"] = data["album_type"].fillna("album").str.title()
    data["word_count"] = data["word_count"].fillna(0).astype(int)
    data["character_count"] = data["character_count"].fillna(0).astype(int)
    data["release_year"] = data["release_year"].astype(int)
    if "canonical_title" not in data:
        data["canonical_title"] = data["track_name"].map(canonical_title)
    if "is_primary_version" not in data:
        data["is_primary_version"] = ~data["canonical_title"].duplicated()
    if "version_count" not in data:
        data["version_count"] = data.groupby("canonical_title")["track_id"].transform("size")
    data["language"] = data["lyrics_clean"].map(detect_languages)
    data["word_count_group"] = pd.cut(
        data["word_count"],
        bins=[-np.inf, 200, 350, 500, np.inf],
        labels=["Short · ≤200", "Medium · 201–350", "Long · 351–500", "Very long · 500+"],
    ).astype(str)
    return data


@st.cache_data(show_spinner=False)
def load_embeddings() -> tuple[pd.DataFrame, np.ndarray]:
    embeddings = pd.read_parquet(PROCESSED_DIR / "song_embeddings.parquet")
    columns = [column for column in embeddings if column.startswith("embedding_")]
    matrix = embeddings[columns].to_numpy(dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    matrix = matrix / np.where(norms == 0, 1, norms)
    return embeddings[["track_id", "track_name", "album_name"]], matrix


@st.cache_data(show_spinner=False)
def load_personal_atlas_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load visualization-ready Personal Atlas production artifacts."""
    personal_map = pd.read_parquet(PERSONAL_DIR / "personal_atlas_map.parquet")
    song_league = pd.read_parquet(PERSONAL_DIR / "bts_song_league.parquet")
    album_league = pd.read_parquet(PERSONAL_DIR / "bts_album_league.parquet")
    return personal_map, song_league, album_league


@st.cache_data(show_spinner=False)
def load_personal_history() -> pd.DataFrame:
    """Load event-level BTS listening history for timeline and recent plays."""
    return pd.read_parquet(PERSONAL_DIR / "bts_listening_history.parquet")


def similarity_scores(track_id: str) -> dict[str, float]:
    metadata, matrix = load_embeddings()
    matches = np.flatnonzero(metadata["track_id"].to_numpy() == track_id)
    if len(matches) == 0:
        return {}
    scores = np.clip(matrix @ matrix[matches[0]], -1.0, 1.0)
    return dict(zip(metadata["track_id"], scores.astype(float), strict=True))


def pair_similarity(first_id: str, second_id: str) -> float:
    """Return cosine similarity between two existing embedding records."""
    return float(similarity_scores(first_id).get(second_id, 0.0))


def similar_songs(track_id: str, data: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    """Return distinct canonical recommendations using cosine similarity."""
    scores = similarity_scores(track_id)
    if not scores:
        return data.iloc[0:0].copy()

    results = data.copy()
    results["similarity"] = results["track_id"].map(scores).fillna(-1)
    selected = results.loc[results["track_id"] == track_id, "canonical_title"]
    selected_title = selected.iloc[0] if not selected.empty else ""
    results = results[results["canonical_title"] != selected_title]
    # Rank and display one preferred release per canonical song. This avoids
    # a live/remix copy winning only because its duplicate embedding differs
    # slightly from the studio representative.
    representatives = (
        results.sort_values("is_primary_version", ascending=False)
        .drop_duplicates("canonical_title")
        .sort_values("similarity", ascending=False)
    )
    return representatives.head(limit)


def format_duration(duration_ms: float | int) -> str:
    if pd.isna(duration_ms):
        return "—"
    total_seconds = int(duration_ms // 1000)
    return f"{total_seconds // 60}:{total_seconds % 60:02d}"


def semantic_story(song: pd.Series, neighbors: pd.DataFrame, data: pd.DataFrame) -> str:
    """Describe only observable properties of a semantic neighborhood."""
    if neighbors.empty:
        return "This song has no visible semantic neighbors under the current selection."

    years = neighbors["release_year"].astype(int)
    median_words = float(data["word_count"].median())
    length_note = "longer" if song.word_count >= median_words else "shorter"
    closest = ", ".join(neighbors["track_name"].head(3))
    cluster = "the atlas fringe" if song.cluster == -1 else f"semantic cluster {int(song.cluster)}"
    return (
        f"{song.track_name} sits in {cluster}. Its closest measured connections are "
        f"{closest}. Those neighbors span {years.min()}–{years.max()}, while this song's "
        f"lyrics are {length_note} than the catalog median. This description reflects map "
        "position and metadata, not inferred lyrical themes."
    )
