"""
Check AcousticBrainz coverage for BTS Song Atlas audio-similarity research.

Goal:
1. Load current song metadata.
2. Extract ISRCs where available.
3. Use MusicBrainz to find recording MBIDs.
4. Use AcousticBrainz to check whether audio descriptors exist.
5. Export a coverage report.

This is research code, not the final production pipeline.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests


MUSICBRAINZ_BASE_URL = "https://musicbrainz.org/ws/2"
ACOUSTICBRAINZ_BASE_URL = "https://acousticbrainz.org/api/v1"
PROJECT_ROOT = Path(__file__).resolve().parents[3]

HEADERS = {
    "User-Agent": "BTS-Song-Atlas/0.1 (research; contact: local-project)",
}


def load_songs(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    if path.suffix == ".parquet":
        return pd.read_parquet(path)

    if path.suffix == ".csv":
        return pd.read_csv(path)

    raise ValueError("Input must be .csv or .parquet")


def find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lookup = {col.lower(): col for col in df.columns}

    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]

    return None


def get_recordings_by_isrc(isrc: str) -> list[dict[str, Any]]:
    url = f"{MUSICBRAINZ_BASE_URL}/isrc/{isrc}"
    params = {
        "fmt": "json",
        "inc": "artists+releases",
    }

    response = requests.get(url, params=params, headers=HEADERS, timeout=30)

    if response.status_code == 404:
        return []

    response.raise_for_status()
    data = response.json()

    return data.get("recordings", [])


def search_recording_by_title_artist(title: str, artist: str = "BTS") -> list[dict[str, Any]]:
    url = f"{MUSICBRAINZ_BASE_URL}/recording"
    query = f'recording:"{title}" AND artist:"{artist}"'

    params = {
        "fmt": "json",
        "query": query,
        "limit": 5,
    }

    response = requests.get(url, params=params, headers=HEADERS, timeout=30)
    response.raise_for_status()

    data = response.json()
    return data.get("recordings", [])


def check_acousticbrainz(mbid: str, level: str = "high-level") -> tuple[bool, int]:
    url = f"{ACOUSTICBRAINZ_BASE_URL}/{mbid}/{level}"

    response = requests.get(url, headers=HEADERS, timeout=30)

    if response.status_code == 200:
        return True, response.status_code

    if response.status_code == 404:
        return False, response.status_code

    return False, response.status_code


def choose_best_recording(recordings: list[dict[str, Any]], expected_artist: str = "BTS") -> dict[str, Any] | None:
    if not recordings:
        return None

    for recording in recordings:
        artist_credit = recording.get("artist-credit", [])
        artist_names = [
            item.get("name", "").lower()
            for item in artist_credit
            if isinstance(item, dict)
        ]

        if expected_artist.lower() in artist_names:
            return recording

    return recordings[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=str(PROJECT_ROOT / "data" / "processed" / "song_master.csv"),
        help="Path to current song metadata CSV or Parquet.",
    )
    parser.add_argument(
        "--output",
        default=str(
            PROJECT_ROOT
            / "data"
            / "processed"
            / "research"
            / "audio_similarity"
            / "acousticbrainz_coverage.csv"
        ),
        help="Output coverage report path.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=1.1,
        help="Seconds to sleep between MusicBrainz requests.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit for quick testing.",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = load_songs(input_path)

    title_col = find_column(
        df,
        [
            "canonical_title",
            "canonical_song",
            "canonical_name",
            "track_name",
            "song_name",
            "name",
            "title",
        ],
    )

    isrc_col = find_column(
        df,
        [
            "isrc",
            "spotify_isrc",
            "external_ids.isrc",
            "external_id_isrc",
        ],
    )

    spotify_id_col = find_column(
        df,
        [
            "spotify_track_id",
            "track_id",
            "id",
            "spotify_id",
        ],
    )

    if title_col is None:
        raise ValueError(
            "Could not find a title column. "
            f"Available columns: {list(df.columns)}"
        )

    work_df = df.copy()

    if args.limit:
        work_df = work_df.head(args.limit)

    rows = []

    print(f"Input rows: {len(work_df)}")
    print(f"Title column: {title_col}")
    print(f"ISRC column: {isrc_col}")
    print(f"Spotify ID column: {spotify_id_col}")

    for index, row in work_df.iterrows():
        title = str(row.get(title_col, "")).strip()
        isrc = str(row.get(isrc_col, "")).strip() if isrc_col else ""

        if isrc.lower() in {"", "nan", "none"}:
            isrc = ""

        spotify_id = str(row.get(spotify_id_col, "")).strip() if spotify_id_col else ""

        print(f"\n[{index + 1}/{len(work_df)}] {title}")

        match_method = None
        recordings = []

        try:
            if isrc:
                print(f"  Searching MusicBrainz by ISRC: {isrc}")
                recordings = get_recordings_by_isrc(isrc)
                match_method = "isrc"
                time.sleep(args.sleep)

            if not recordings:
                print("  Searching MusicBrainz by title + artist")
                recordings = search_recording_by_title_artist(title, artist="BTS")
                match_method = "title_artist"
                time.sleep(args.sleep)

            recording = choose_best_recording(recordings)

            if recording is None:
                rows.append(
                    {
                        "title": title,
                        "spotify_track_id": spotify_id,
                        "isrc": isrc,
                        "match_method": match_method,
                        "musicbrainz_recording_mbid": None,
                        "musicbrainz_title": None,
                        "musicbrainz_score": None,
                        "has_acousticbrainz_high_level": False,
                        "high_level_status": None,
                        "has_acousticbrainz_low_level": False,
                        "low_level_status": None,
                    }
                )
                print("  No MusicBrainz recording found")
                continue

            mbid = recording.get("id")
            mb_title = recording.get("title")
            score = recording.get("score")

            print(f"  MBID: {mbid}")
            print(f"  MusicBrainz title: {mb_title}")

            has_high, high_status = check_acousticbrainz(mbid, "high-level")
            has_low, low_status = check_acousticbrainz(mbid, "low-level")

            rows.append(
                {
                    "title": title,
                    "spotify_track_id": spotify_id,
                    "isrc": isrc,
                    "match_method": match_method,
                    "musicbrainz_recording_mbid": mbid,
                    "musicbrainz_title": mb_title,
                    "musicbrainz_score": score,
                    "has_acousticbrainz_high_level": has_high,
                    "high_level_status": high_status,
                    "has_acousticbrainz_low_level": has_low,
                    "low_level_status": low_status,
                }
            )

            print(f"  AcousticBrainz high-level: {has_high} ({high_status})")
            print(f"  AcousticBrainz low-level: {has_low} ({low_status})")

        except Exception as exc:
            rows.append(
                {
                    "title": title,
                    "spotify_track_id": spotify_id,
                    "isrc": isrc,
                    "match_method": match_method,
                    "musicbrainz_recording_mbid": None,
                    "musicbrainz_title": None,
                    "musicbrainz_score": None,
                    "has_acousticbrainz_high_level": False,
                    "high_level_status": "error",
                    "has_acousticbrainz_low_level": False,
                    "low_level_status": "error",
                    "error": str(exc),
                }
            )
            print(f"  ERROR: {exc}")

    result = pd.DataFrame(rows)
    result.to_csv(output_path, index=False)

    total = len(result)
    mb_matches = result["musicbrainz_recording_mbid"].notna().sum()
    high_matches = result["has_acousticbrainz_high_level"].sum()
    low_matches = result["has_acousticbrainz_low_level"].sum()

    print("\n=== Coverage Summary ===")
    print(f"Total checked: {total}")
    print(f"MusicBrainz matches: {mb_matches} ({mb_matches / total:.1%})")
    print(f"AcousticBrainz high-level matches: {high_matches} ({high_matches / total:.1%})")
    print(f"AcousticBrainz low-level matches: {low_matches} ({low_matches / total:.1%})")
    print(f"Saved report to: {output_path}")


if __name__ == "__main__":
    main()
