"""Rebuild the song atlas from existing embeddings without external data.

The projection is fit on one averaged embedding per canonical song title. This
prevents repeated album, live, remix, and language releases from dominating
the geometry while retaining every Spotify track in the exported datasets.
"""

from __future__ import annotations

import re
from pathlib import Path

import hdbscan
import numpy as np
import pandas as pd
import umap
from sklearn.neighbors import NearestNeighbors


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"


def canonical_title(title: str) -> str:
    title = str(title).lower()
    title = re.sub(r"\s*-\s*(live|japanese ver\.?)$", "", title)
    title = re.sub(r"\s*\(.*?\)", "", title)
    return re.sub(r"[^a-z0-9가-힣ぁ-ゔァ-ヴー一-龯\s]", "", title).strip()


def version_penalty(title: str) -> int:
    """Prefer the plain studio-title release as the displayed representative."""
    return sum(
        marker in str(title).casefold()
        for marker in ("live", "remix", "japanese ver", "instrumental", "edition", "mix")
    )


def build_projection() -> pd.DataFrame:
    embeddings = pd.read_parquet(PROCESSED / "song_embeddings.parquet")
    embedding_columns = [column for column in embeddings if column.startswith("embedding_")]
    embeddings["canonical_title"] = embeddings["track_name"].map(canonical_title)

    canonical_names: list[str] = []
    centroids: list[np.ndarray] = []
    for name, group in embeddings.groupby("canonical_title", sort=True):
        centroid = group[embedding_columns].to_numpy(dtype=np.float32).mean(axis=0)
        centroid /= np.linalg.norm(centroid)
        canonical_names.append(name)
        centroids.append(centroid)

    centroid_matrix = np.vstack(centroids)
    coordinates = umap.UMAP(
        n_neighbors=12,
        min_dist=0.3,
        spread=1.8,
        n_components=2,
        metric="cosine",
        random_state=11,
        n_jobs=1,
    ).fit_transform(centroid_matrix)

    # Leaf clustering exposes useful local neighborhoods while still allowing
    # genuinely ambiguous songs to remain unassigned as noise (-1).
    clusters = hdbscan.HDBSCAN(
        min_cluster_size=6,
        min_samples=1,
        cluster_selection_method="leaf",
        metric="euclidean",
    ).fit_predict(coordinates)

    centroid_frame = pd.DataFrame(
        {
            "canonical_title": canonical_names,
            "centroid_x": coordinates[:, 0],
            "centroid_y": coordinates[:, 1],
            "cluster": clusters,
        }
    )
    projection = embeddings[["track_id", "track_name", "canonical_title"]].merge(
        centroid_frame, on="canonical_title", how="left", validate="many_to_one"
    )

    # Give duplicate releases a small deterministic orbit around their shared
    # semantic centroid. The primary version stays exactly at the centroid.
    neighbor_distances = NearestNeighbors(n_neighbors=6).fit(coordinates).kneighbors(coordinates)[0]
    local_scale = dict(zip(canonical_names, neighbor_distances[:, 1:].mean(axis=1), strict=True))
    projection["version_penalty"] = projection["track_name"].map(version_penalty)
    projection = projection.sort_values(
        ["canonical_title", "version_penalty", "track_name", "track_id"]
    )
    projection["version_index"] = projection.groupby("canonical_title").cumcount()
    projection["version_count"] = projection.groupby("canonical_title")["track_id"].transform("size")
    projection["is_primary_version"] = projection["version_index"].eq(0)

    index = projection["version_index"].to_numpy()
    count = projection["version_count"].to_numpy()
    angle = np.where(count > 1, 2 * np.pi * index / count, 0)
    scale = projection["canonical_title"].map(local_scale).to_numpy()
    radius = np.where(index == 0, 0, np.minimum(scale * (0.10 + 0.018 * index), 0.55))
    projection["x"] = projection["centroid_x"] + np.cos(angle) * radius
    projection["y"] = projection["centroid_y"] + np.sin(angle) * radius

    return projection[
        ["track_id", "canonical_title", "is_primary_version", "version_count", "x", "y", "cluster"]
    ]


def main() -> None:
    projection = build_projection()
    for filename in ("song_atlas.csv", "song_atlas_full.csv"):
        path = PROCESSED / filename
        atlas = pd.read_csv(path)
        replace_columns = [
            "canonical_title",
            "is_primary_version",
            "version_count",
            "x",
            "y",
            "cluster",
        ]
        atlas = atlas.drop(columns=replace_columns, errors="ignore")
        atlas = atlas.merge(projection, on="track_id", how="left", validate="one_to_one")
        atlas["lyrics_clean"] = atlas["lyrics_clean"].str.replace(
            r"[ \t]+(?=\n|$)", "", regex=True
        )
        preferred_order = [
            "track_id",
            "track_name",
            "album_name",
            "release_year",
            "x",
            "y",
            "cluster",
            "spotify_url",
            "image_url",
            "lyrics_clean",
            "word_count",
            "character_count",
            "canonical_title",
            "is_primary_version",
            "version_count",
        ]
        atlas = atlas[preferred_order]
        atlas.to_csv(path, index=False)
        print(f"Updated {path.relative_to(ROOT)}: {len(atlas)} releases, "
              f"{atlas['canonical_title'].nunique()} canonical songs")


if __name__ == "__main__":
    main()
