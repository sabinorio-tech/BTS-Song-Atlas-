# BTS Song Atlas — Work Report

**Report date:** 8 July 2026  
**Scope:** Work completed from the initial repository review through the current atlas and application improvements.

## 1. Executive summary

The repository began as a notebook-first data pipeline with completed Spotify, Genius, embedding, UMAP, and clustering outputs, but only a minimal Streamlit prototype. The work completed in this session turned that prototype into a functional interactive dashboard based on the supplied design reference, fixed runtime and interaction problems, and rebuilt the semantic projection using only the existing data.

The final application includes:

- A dark, responsive BTS Song Atlas dashboard.
- Search, popular-song shortcuts, filters, coloring modes, and display controls.
- An interactive semantic map with selection and preserved viewport state.
- Song metadata, artwork, Spotify and Genius links, and lyric previews.
- Real cosine-similarity recommendations from the stored embeddings.
- A deduplication-aware projection showing 194 canonical songs by default while retaining all 381 Spotify releases.
- A reproducible script for rebuilding the improved atlas.

## 2. Initial repository analysis

The repository was inspected before implementation. No files were changed during this initial audit.

### Original architecture

The project was found to be a sequential notebook pipeline:

1. `01-spotify_ingestion.ipynb` retrieves BTS albums, singles, and tracks.
2. `02_data_cleaning.ipynb` cleans and validates Spotify metadata.
3. `03_lyrics_ingestion.ipynb` searches Genius using fuzzy title and artist validation.
4. `04_lyrics_cleaning.ipynb` retains exact matches and cleans lyric text.
5. `05_song_master.ipynb` merges Spotify metadata and Genius lyrics.
6. `06_embeddings.ipynb` creates 384-dimensional multilingual lyric embeddings.
7. `07_song_atlas.ipynb` creates UMAP coordinates, similarity results, and HDBSCAN clusters.
8. `08_dashboard_testing.ipynb` was empty.

### Original data inventory

- 77 Spotify releases.
- 441 unique Spotify track records.
- 381 accepted Genius lyric matches.
- 381 songs with multilingual embeddings and atlas coordinates.
- Release-year range of 2013–2026.
- 20 original HDBSCAN clusters.
- 245 of 381 records, approximately 64%, originally labeled as cluster noise.

The Genius ingestion results contained:

- 381 exact matches.
- 27 rejected matches.
- 12 manual-review matches.
- 11 songs not found.
- 10 instrumental tracks.

### Original application state

- `app/Home.py` contained only a small introduction.
- `app/pages/1_atlas.py` contained a basic Plotly scatterplot.
- Song Explorer, Statistics, About, shared components, and utility files were empty.
- `README.md` and root `main.py` were empty.
- `app/requirements.txt` listed only Streamlit.
- The entire `app/` directory was and remains untracked by Git unless explicitly added by the user.

## 3. Dashboard implementation

The supplied visual reference was translated into a native Streamlit interface using the repository’s real data.

### Shared application structure

- `app/Home.py` now launches the complete dashboard.
- `app/pages/1_atlas.py` also uses the shared dashboard renderer.
- `app/components.py` contains the interface, Plotly map, controls, metrics, and detail panels.
- `app/utiles.py` contains data loading, enrichment, similarity, duration, and language helpers.
- `app/styles.css` contains the custom dark-violet visual system and responsive styling.
- `app/requirements.txt` now declares Streamlit, pandas, NumPy, Plotly, and PyArrow.

### Implemented interface features

The left sidebar now includes:

- Search across song and album names.
- Popular-song shortcuts.
- Coloring by album, semantic cluster, or release-year group.
- Release-year filtering.
- Album filtering.
- Album-type filtering.
- Song-label toggle.
- Lyric-density sizing toggle.
- Similar-song highlighting toggle.
- Distant-song fading toggle.
- Duplicate-release visibility toggle.

The dashboard header includes live metrics for:

- Total embedded releases.
- Album count.
- Release-year range.
- Average lyric word count.
- Approximate language coverage.

The main explorer includes:

- The existing UMAP coordinates rendered as an interactive Plotly map.
- Album, cluster, and release-year coloring modes.
- Hover metadata.
- Song selection.
- Similarity-based point fading and outlines.
- Connections from the selected song to nearby recommendations.
- Optional lyric-density point sizing.
- Zoom, pan, reset, and responsive layout behavior.

The selected-song panel includes:

- Real Spotify album artwork.
- Track, album, and release information.
- Album type and formatted duration.
- Word and character counts.
- A lightweight language heuristic based on lyric scripts.
- Spotify and Genius links.
- Ten embedding-based similar songs with cosine scores.
- A lyric preview.

## 4. Similarity implementation

Similarity recommendations use the existing 384-dimensional multilingual embeddings stored in `song_embeddings.parquet`.

The implementation:

1. Loads the embedding matrix once through Streamlit caching.
2. Normalizes each embedding vector.
3. Computes cosine similarity using a matrix-vector product.
4. Removes the selected canonical song from its own results.
5. Deduplicates alternate releases by canonical title.
6. Returns the ten highest-scoring distinct songs.

No new external data or model calls are required at application runtime.

## 5. Runtime bug fix

Some song selections caused Plotly to raise this error:

> Invalid element(s) received for the `opacity` property of `scattergl.marker`.

The cause was Float32 rounding during cosine similarity. Mathematically valid values of `1.0` occasionally appeared as values such as `1.0000001`, producing an opacity slightly above Plotly’s allowed maximum.

The fix applies two safeguards:

- Cosine scores are clamped to `[-1, 1]`.
- Derived opacity values are clamped to `[0, 1]`.

All 381 song vectors were checked after the fix. The resulting similarity range remains valid and the application renders without exceptions.

## 6. Map interaction improvements

Three requested interaction changes were implemented.

### Smoother zooming and panning

- Removed 420 decorative star-field points from the Plotly figure.
- Combined eight separate similarity-edge traces into one WebGL trace.
- Retained WebGL rendering for the song points.
- Added responsive Plotly configuration.
- Added hover-mode toolbar behavior and double-click reset.
- Added a short transition for state changes.
- Reduced hover distance and preserved a stable map identity.

### Reduced refresh behavior

- The explorer is now wrapped in a Streamlit fragment.
- Point selections rerun only the explorer fragment instead of explicitly rerunning the entire page.
- Plotly `uirevision` remains stable so zoom and pan state are preserved when the selected song changes.

### Background cleanup

- Removed the generated star-field trace.
- Removed the extra star-like radial layer from the application background.
- Retained a subtle dark-violet gradient so the plot remains visually separated from surrounding panels.

## 7. Semantic atlas analysis

The dense original map was investigated quantitatively.

### Main cause

The atlas contained 381 Spotify release records but only 194 canonical song titles:

- 187 records were alternate releases of an existing canonical title.
- 115 records contained exactly duplicated cleaned lyrics.
- Only 266 unique lyric bodies existed among the 381 embedded releases.

Examples included:

- 14 releases of “Dynamite.”
- 9 releases of “Butter.”
- 8 releases of “Fake Love.”
- 7 releases each of “DNA,” “I Need U,” and “Run.”

Fitting UMAP directly on all releases caused repeated versions and identical lyrics to occupy or pull toward the same areas. This contributed substantially to the visible central crowding.

## 8. Improved projection

A new reproducible projection process was added in `scripts/rebuild_atlas_projection.py`.

### Canonical-song construction

Titles are normalized to group alternate releases while preserving Latin, Korean, Japanese kana, and CJK characters. Live, Japanese-version, parenthetical, punctuation, and formatting variations are normalized where appropriate.

For each canonical title:

1. All associated embedding vectors are averaged.
2. The averaged vector is normalized.
3. UMAP is fit once on the resulting 194 semantic centroids.

This means every canonical song contributes equally to the projection, regardless of how many Spotify releases it has.

### New UMAP configuration

The selected configuration is:

- `n_neighbors=12`
- `min_dist=0.3`
- `spread=1.8`
- `metric="cosine"`
- `random_state=11`

Multiple parameter and seed combinations were measured before selecting this configuration.

### Duplicate release placement

All 381 track records remain in the exported datasets.

- One preferred primary release stays exactly on its canonical centroid.
- Other releases receive a small deterministic orbit around the shared centroid.
- The primary version favors plain studio titles over live, remix, Japanese-version, instrumental, edition, and mix variants.
- The application hides duplicate releases by default but exposes them through the new toggle.

### Revised clustering

HDBSCAN is now run on the canonical projection with:

- `min_cluster_size=6`
- `min_samples=1`
- `cluster_selection_method="leaf"`
- Euclidean distance in projection space.

Cluster labels are assigned consistently to every release belonging to the same canonical song.

## 9. Measured projection results

The old and new layouts were compared on canonical-song centroids.

| Measurement | Original | Improved |
|---|---:|---:|
| Canonical songs represented | 194 | 194 |
| Neighborhood trustworthiness | 0.7587 | 0.7878 |
| Central-crowding fraction | 0.299 | 0.103 |
| Neighbor-distance variation | 1.747 | 0.184 |
| Cluster noise | approximately 64% of releases | 27.3% of canonical songs |
| Non-noise clusters | 20 original labels | 17 revised clusters |

Interpretation:

- Local semantic neighborhoods are preserved more accurately.
- The fraction of songs in the measured central region fell by roughly two-thirds.
- Point spacing is substantially more even.
- Considerably fewer canonical songs are treated as clustering noise.

These improvements use only the existing lyric embeddings; no additional source was introduced.

## 10. Data export changes

Both application atlas exports were regenerated:

- `data/processed/song_atlas.csv`
- `data/processed/song_atlas_full.csv`

Every export still contains 381 unique track IDs and no missing projection or cluster values.

The following fields were added:

- `canonical_title`
- `is_primary_version`
- `version_count`

The `x`, `y`, and `cluster` values were replaced with the improved projection and cluster assignments. Trailing spaces at lyric line endings were also removed from the rewritten atlas exports.

## 11. Validation performed

The completed work was checked through:

- Python compilation of `app/` and `scripts/`.
- Direct loading and joining of all application datasets.
- Verification that all 381 track IDs remain unique.
- Verification of 194 canonical titles and 194 primary versions.
- Verification that projection and cluster fields contain no missing values.
- Similarity-bound checks across every embedded song.
- Direct construction and serialization of the Plotly figure.
- Streamlit `AppTest` rendering with zero application exceptions.
- Confirmation that the test render contains five metrics, one Plotly atlas, two external links, and five advanced toggles.
- Git whitespace validation after data regeneration.

## 12. Files created or changed

### Application

- `app/Home.py` — complete dashboard entry point.
- `app/components.py` — UI, map, controls, panels, metrics, and selection behavior.
- `app/utiles.py` — data, embedding, similarity, formatting, and language helpers.
- `app/styles.css` — dashboard visual styling.
- `app/pages/1_atlas.py` — shared dashboard page.
- `app/requirements.txt` — complete application dependencies.

The pre-existing empty Song Explorer, Statistics, and About pages were not populated because the supplied reference and requested implementation focused on the single atlas dashboard.

### Projection pipeline

- `scripts/rebuild_atlas_projection.py` — reproducible canonical-centroid projection and clustering pipeline.

### Data

- `data/processed/song_atlas.csv` — regenerated application atlas.
- `data/processed/song_atlas_full.csv` — regenerated full atlas.

## 13. Commands

Run the application from the repository root:

```bash
streamlit run app/Home.py
```

Rebuild the improved projection from the current embeddings:

```bash
python scripts/rebuild_atlas_projection.py
```

The rebuild script uses only local processed data and does not call Spotify, Genius, or any external model.

## 14. Remaining limitations and recommended next work

- Language labels are inferred from writing systems because the dataset has no authoritative language field.
- Album type comes from Spotify’s broad `album` or `single` classification; it does not distinguish studio albums from compilations or reissues.
- Semantic similarity is based only on whole-song lyrics. Section-aware embeddings could distinguish verses, choruses, and themes more precisely.
- The clusters are exploratory mathematical neighborhoods, not human-labeled themes.
- Spotify artwork is loaded from external image URLs and therefore requires internet access in the deployed application.
- The original `07_song_atlas.ipynb` still represents the earlier projection approach. The new rebuild script is currently the authoritative improved projection step and should be run after older notebook output if that notebook is rerun.
- `README.md` remains empty.
- Automated unit tests have not yet been added; validation currently uses data assertions and Streamlit’s application test framework.
- The `app/` and `scripts/` directories are currently untracked and need to be staged if they should become part of Git history.

## 15. Current outcome

The project now has a functional and substantially more polished semantic exploration interface. It uses the existing data more effectively, avoids allowing repeated releases to dominate the geometry, provides reproducible atlas generation, and has passed the available data and Streamlit rendering checks.
