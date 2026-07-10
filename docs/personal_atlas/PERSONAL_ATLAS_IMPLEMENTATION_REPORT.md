# Personal Atlas Implementation Report

## Executive summary

The BTS Song Atlas now includes a production-ready Personal Atlas experience inside the existing Streamlit application shell. The page maps personal Spotify listening history onto the established two-dimensional semantic atlas without changing the original semantic coordinates.

The implementation uses processed production artifacts only. It does not recompute notebook pipelines, call Spotify APIs, require secrets, or modify the Phase 1 projection scripts.

The current Personal Atlas reports:

- 75.0 total listening hours
- 313 of 381 atlas releases explored
- 86 of 86 listening-history albums explored
- highest mastery level: Level 4
- 100% atlas-coordinate coverage
- 18 genuinely unexplored canonical songs
- 47 unplayed alternate releases of canonical songs heard elsewhere

The processed BTS listening history spans 24 July 2024 through 8 July 2026. The latest event is 8 July 2026 at 21:46 UTC.

## Scope completed

### Notebook and visualization-ready export

The existing notebook was extended in place:

`notebooks/personal_atlas/03_personal_atlas_visualization.ipynb`

The notebook now:

1. Loads the production atlas source used by Streamlit.
2. Inspects coordinate columns and key cardinality.
3. Merges coordinates into the personal overlay on `track_id`.
4. Validates row preservation, key uniqueness, and coordinate coverage.
5. Exports a lean visualization-ready Parquet file.
6. Produces an exploratory Plotly Personal Atlas preview.

The verified production coordinate source is:

`data/processed/song_atlas.csv`

The visualization-ready output is:

`data/processed/personal_atlas/personal_atlas_map.parquet`

Merge results:

| Check | Result |
|---|---:|
| Overlay rows before merge | 381 |
| Rows after merge | 381 |
| Coordinate coverage | 100% |
| Unmatched `track_id` values | 0 |
| Duplicate `track_id` values | 0 |
| Releases with listening history | 313 |
| Releases without listening history | 68 |

The merge relationship is one-to-one. Both sources contain 381 unique `track_id` values.

## Production data sources

The application loads the following processed files:

### `personal_atlas_map.parquet`

Primary map dataset containing:

- track and album identity
- canonical title
- primary-version flag
- semantic `x` and `y` coordinates
- semantic cluster
- personal plays and hours
- first and last matched play dates
- match metadata
- personal rank
- mastery level
- listening-history flag

Shape: 381 rows × 21 columns.

### `bts_song_league.parquet`

Used for total listening hours and ranked top songs.

Shape: 344 rows × 8 columns.

### `bts_album_league.parquet`

Used for ranked top albums and album coverage.

Shape: 86 rows × 6 columns. It contains 86 unique album names, all with positive listening time.

### `bts_listening_history.parquet`

Event-level history used for the monthly listening timeline.

Shape: 2,855 rows × 24 columns.

Time range: 24 July 2024 to 8 July 2026.

## Application experience

### Existing navigation preserved

The original application shell and sidebar remain the source of navigation. No second sidebar, duplicate Personal Atlas entry, or Streamlit automatic multipage menu was introduced.

The Personal Atlas sidebar entry now opens the implemented experience and no longer carries a “Soon” badge. The Home experience card also links to the finished Personal Atlas page.

### Header

The page uses the product copy:

> Personal Atlas  
> Your listening journey across the BTS universe.

It follows the existing dark cosmic interface, violet emphasis, rounded panels, borders, and typography.

### Summary cards

The page displays only values supported by the processed datasets:

- **Total listening hours:** 75.0h
- **Songs explored:** 313 / 381
- **Albums explored:** 86 / 86
- **Highest mastery:** Level 4

The album denominator refers to the processed listening-history album universe. The semantic map itself contains 57 distinct album names, while the album league contains 86 albums across BTS and member listening history.

Unsupported claims such as listener percentiles, global ARMY rankings, or comparisons with other Spotify users were deliberately excluded.

### Personal semantic map

The main Plotly visualization preserves the production semantic `x` and `y` coordinates.

It provides two color modes:

- Listening intensity
- Semantic clusters

Listening intensity uses `np.log1p(personal_hours)` as a display-only transformation. Raw listening hours remain unchanged and appear in hover tooltips.

Hover content includes:

- song title
- album
- actual listening hours
- plays
- mastery level

Raw coordinates are hidden.

Unexplored releases remain visible as small, subdued landmarks unless the listened-only filter is enabled.

### Point sizing

When **Size by plays** is active, marker size is calculated as:

```python
np.clip(7 + 1.6 * np.sqrt(personal_plays), 8, 32)
```

This makes highly played songs visibly larger without allowing them to cover large semantic neighborhoods.

### Map controls

The map includes:

- searchable song-and-album dropdown
- listened-only toggle
- show-duplicate-releases toggle
- size-by-plays toggle
- listening-intensity or semantic-cluster color selection

The searchable dropdown lists valid song and album combinations, preventing spelling mismatches and empty free-text searches.

The duplicate-release behavior follows the existing 2D Atlas semantics:

- off: prefer `is_primary_version` and keep one row per `canonical_title`
- on: show all album, live, remix, Japanese, and alternate releases

### Ranked panels

The page includes:

- top seven songs by listening hours
- top seven albums by listening hours

Both panels use processed league data and make no API calls. Artwork was omitted because the league artifacts do not include image fields.

### Mastery section

The compact stacked mastery chart uses the pipeline’s numeric levels directly. It does not introduce unsupported labels such as “Moonchild.”

Current distribution:

| Mastery level | Releases |
|---|---:|
| Level 0 | 68 |
| Level 1 | 237 |
| Level 2 | 33 |
| Level 3 | 36 |
| Level 4 | 7 |

### Listening timeline

The timeline aggregates actual event-level BTS listening hours by month. No illustrative or invented values are used.

### Unexplored Songs panel

The original Recent Plays panel was replaced by a scrollable Unexplored Songs panel.

The 68 releases without direct listening history are not all unique songs:

- 47 are alternate releases of canonical songs heard through another release.
- 21 releases belong to completely unexplored canonical songs.
- Those 21 releases represent 18 canonical songs.

The panel therefore shows all 18 genuinely unexplored canonical songs, one representative release per canonical title. It displays song and album names without a redundant “Level 0” label.

## Missing and partial-data behavior

The page handles:

- missing Personal Atlas files
- unreadable or invalid Parquet artifacts
- an empty Personal Atlas map
- unavailable event-level history
- no results after map filtering
- a fully explored canonical catalog

Failures produce friendly messages instead of an application crash.

## Architecture

### Cached data loading

`app/utils.py` contains cached production-artifact loaders:

- `load_personal_atlas_data()`
- `load_personal_history()`

### Reusable visualization

`app/visualization.py` contains:

- `build_personal_atlas_figure()`

The function owns the semantic-map rendering, intensity transform, marker sizing, unexplored styling, hover templates, and cluster view.

### Page-level view structure

Route ownership is organized under:

```text
app/views/
├── __init__.py
├── router.py
├── home.py
├── atlas.py
├── compare.py
├── personal_atlas.py
├── insights.py
├── about.py
└── explorer.py
```

The folder is named `views` instead of Streamlit’s reserved `pages` directory. This prevents Streamlit from creating a second automatic navigation menu.

The existing query-parameter router and custom sidebar remain intact. Shared UI primitives and session-state behavior remain centralized in `app/components.py`.

## Files changed

- `app/components.py`
- `app/styles.css`
- `app/utils.py`
- `app/visualization.py`
- `app/views/__init__.py`
- `app/views/router.py`
- `app/views/home.py`
- `app/views/atlas.py`
- `app/views/compare.py`
- `app/views/personal_atlas.py`
- `app/views/insights.py`
- `app/views/about.py`
- `app/views/explorer.py`
- `notebooks/personal_atlas/03_personal_atlas_visualization.ipynb`
- `data/processed/personal_atlas/personal_atlas_map.parquet`

No Phase 1 scripts or original processed atlas exports were modified as part of the Personal Atlas merge.

## Validation performed

Validation included:

- Python compilation of the application package
- direct cached-loader checks
- construction of both Personal Atlas Plotly color modes
- notebook workflow execution without display calls
- output Parquet schema and coordinate checks
- Git whitespace checks
- Streamlit `AppTest` smoke tests for every route

Routes tested:

- Home
- Atlas
- Compare
- Personal Atlas
- Insights
- About
- Explorer placeholder

All tested routes completed with zero Streamlit exceptions.

## Data-quality limitations

1. The current personal map is release-level. One canonical song can appear in multiple albums, live releases, remixes, or language versions.
2. Personal matching can propagate canonical listening history across multiple releases, while some alternate releases remain directly unplayed.
3. Eighteen canonical songs currently have no matched listening history.
4. Album coverage uses the listening-history league universe, which is broader than the 57 album names represented in the semantic map.
5. The league datasets do not include artwork URLs, so ranked-list artwork is not displayed.
6. The processed map contains all-time aggregates. Accurate 30-day, 90-day, or one-year map filters would require additional pre-aggregated artifacts or pipeline work.
7. The current history ends on 8 July 2026. New Spotify exports require a Personal Atlas pipeline rerun.

## Run and test

Start the application from the repository root:

```bash
.venv/bin/streamlit run app/Home.py
```

Then select **Personal Atlas** from the existing sidebar.

Recommended manual checks:

1. Confirm the Personal Atlas header and four summary cards load.
2. Switch between listening intensity and semantic clusters.
3. Select a song through the searchable dropdown.
4. Toggle listened-only mode.
5. Toggle duplicate releases and confirm the number of visible points changes.
6. Toggle size by plays and confirm frequent songs become larger.
7. Hover points and verify hours, plays, album, and mastery values.
8. Scroll through all unexplored canonical songs.
9. Confirm the timeline covers the real history period.
10. Visit the other sidebar routes and confirm navigation remains stable.

## Recommended next steps

1. Move page-specific implementation bodies from the shared component library into their view modules as the application continues to grow.
2. Add pre-aggregated time-window artifacts if interactive 30-day, 90-day, and yearly filtering is desired.
3. Enrich ranked league artifacts with existing local artwork metadata during the data pipeline.
4. Rerun the Personal Atlas pipeline after solo-discography expansion and new Spotify history exports.
5. Add targeted unit tests for canonical-release filtering and Personal Atlas summary calculations.

## Recommended commit message

```text
feat: build and document personal listening atlas experience
```
