# BTS Song Atlas — Current Status Report

**Status date:** 8 July 2026  
**Application state:** Functional development build  
**Validation state:** Core modes and boundary interactions passing

## Executive summary

BTS Song Atlas is now a map-first Streamlit application for exploring BTS songs through multilingual lyric embeddings. It no longer presents itself as a conventional dashboard. The default experience is a neutral overview of the complete semantic universe, and exploration begins only when a user searches for or selects a song.

The application currently supports semantic-neighborhood highlighting, fuzzy search, journey building, two-song comparison, time-based exploration, multiple color modes, adjustable neighborhood sizes, factual semantic stories, a navigable overview map, and deployment-oriented configuration.

The existing embeddings and current UMAP projection were preserved during the latest UI work.

## Current default experience

When the application opens:

- Search displays **All songs**.
- No song is preselected.
- Black Swan is not highlighted by default.
- All 194 canonical songs are shown at normal visibility.
- No semantic neighborhood is active.
- The right panel explains the atlas overview rather than showing arbitrary song details.
- Selecting a point or searching for a title begins exploration.

## Current data state

| Item | Current value |
|---|---:|
| Spotify track/release records in atlas | 381 |
| Canonical songs | 194 |
| Preferred primary versions | 194 |
| Atlas columns | 15 |
| Release range | 2013–2026 |
| Non-noise semantic clusters | 17 |
| Canonical songs marked as cluster noise | 27.3% |
| Embedding dimensions | 384 |

The atlas retains every Spotify release while showing one preferred release per canonical title by default. Alternate releases can be exposed through an advanced toggle.

## Implemented product features

### Full-atlas overview

- Neutral default map with no selection bias.
- Full coordinate extent visible.
- Overview instructions and catalog summary in the right panel.
- All-song points remain visible even when distant-song fading is enabled, because fading activates only after a neighborhood exists.

### Semantic neighborhood exploration

- Selected song receives a blue core, white border, and violet glow.
- Top semantic neighbors receive a separate similarity-weighted violet layer.
- Neighbor size and intensity reflect cosine similarity.
- Unrelated songs fade substantially after selection.
- Selected song and closest-neighbor labels remain prominent.
- Soft connection lines clarify relationships without creating one trace per edge.
- Neighbor count can be set to 5, 10, 20, or 50.
- Labels are capped at ten even when more neighbors are highlighted to avoid clutter.

### Search

- Native Streamlit fuzzy autocomplete.
- Keyboard navigation and Enter selection.
- Search across song-title and album labels.
- **All songs** resets the atlas to the neutral overview.
- Explicit song search focuses and zooms the map around the result.
- Search does not discard active user filters.
- Recent searches and popular-song shortcuts are available.

### Explore and Journey mode

- Selecting or jumping to another song adds it to a semantic journey.
- Up to twelve recent journey stops are retained.
- Journey points are connected on the main map and overview map.
- The side panel shows the traveled song sequence.
- Back and clear-path controls are available.

### Compare mode

- A second song can be selected with fuzzy search or from the map.
- The selected neighborhood is violet.
- The compared neighborhood is amber.
- Shared neighbors are gold.
- The panel reports cosine similarity, 2D map distance, albums, release years, shared-neighbor count, and unique-neighbor counts.

### Time Explorer

- A release-year cutoff reveals the semantic universe progressively.
- Moving from 2013 toward 2026 adds later releases without changing coordinates.
- Explicitly searched songs remain reachable without destroying the selected cutoff.

### Color modes

The immutable map layout can be colored by:

- Album
- Release Year
- Language
- Word Count
- Semantic Cluster

Changing color mode does not recalculate or move the semantic projection.

### Song details

The selected-song panel includes:

- Spotify artwork
- Track and album names
- Release year and album type
- Duration
- Word and character counts
- Detected writing-system languages
- Spotify and Genius links
- Catalog timeline position
- Rule-based semantic-neighborhood story
- Scrollable similarity list with strength bars
- Fuzzy jump-to-neighbor control
- Lyrics preview

The semantic story uses only observable cluster, neighbor, year, language, and length information. It does not invent lyrical themes.

### Overview map

- Lightweight WebGL minimap shows the complete atlas.
- Selected song and journey are emphasized.
- Selecting a minimap point focuses the main atlas.

## Architecture

Application responsibilities are separated as follows:

- `app/Home.py` — Streamlit entry point.
- `app/components.py` — layout, controls, panels, and session-state behavior.
- `app/visualization.py` — main Plotly atlas and overview map.
- `app/utils.py` — data loading, metadata enrichment, similarity, and story helpers.
- `app/styles.css` — visual design system.
- `app/utiles.py` — compatibility import shim.
- `scripts/rebuild_atlas_projection.py` — reproducible production projection rebuild.

Research remains in notebooks, production transformation is in `scripts/`, and application behavior remains in `app/`.

## Deployment readiness

Current deployment support includes:

- Root `requirements.txt` points to the lightweight application requirements.
- Public runtime dependencies are limited to Streamlit, pandas, NumPy, Plotly, and PyArrow.
- The larger transformer, UMAP, ingestion, and research dependencies remain in `requirements/base.txt`.
- `.streamlit/config.toml` defines a dark theme and headless server configuration.
- Application data paths are resolved relative to the repository.
- The app starts with `streamlit run app/Home.py`.
- No Spotify or Genius secrets are required for the read-only deployed atlas.

## Current validation results

The following checks currently pass:

- Default **All songs** overview: zero exceptions.
- Search and map focus: zero exceptions.
- Two-stop semantic journey: zero exceptions.
- Compare mode with Spring Day: zero exceptions.
- Neighborhood size of 50: zero exceptions.
- Time Explorer at the 2013 boundary: zero exceptions.
- Main atlas and minimap rendering: successful.
- Python compilation for `app/` and `scripts/`: successful.
- Installed dependency consistency: no broken requirements.
- Git whitespace validation: successful.

Current semantic-data hashes:

```text
song_atlas.csv             0e5e2ef8e35f4e2496ce7ab36b26fbf8668d9a641b6c65639684ee0ce7f259fc
song_embeddings.parquet    1b0a2dddd3cb1535dffe68da1edab5023847cefe23a91b14902c6beaa3fe1574
```

## Known native-stack limitations

### Zoom-aware progressive labels

Native Streamlit does not expose Plotly relayout/zoom events. Labels therefore adapt to neighborhood importance, but not dynamically to the exact browser zoom level.

### Close-zoom album artwork

Automatically replacing circles with artwork at a zoom threshold requires relayout events or a custom Plotly component. Current artwork remains in the details and recommendation panels.

### Minimap viewport rectangle

The minimap supports point-based navigation, but it cannot show or drag the main plot’s live viewport rectangle without relayout synchronization.

### Animation

The application uses Plotly transitions and layered glow rather than continuous custom animation loops. This preserves performance and avoids a JavaScript framework.

### Browser media

A real headless Chrome capture was attempted. In the current WSL environment, Chrome captured Streamlit’s shell before WebSocket-rendered content appeared. The unusable blank image was removed. Portfolio screenshots and an Explore-mode GIF still need to be captured from a deployed or interactive browser.

## Incomplete or intentionally deferred areas

- `app/pages/2_Song_Explorer.py` remains empty.
- `app/pages/3_statistics.py` remains empty.
- `app/pages/4_about.py` remains empty.
- Those pages are not needed for the current map-first product and the multipage navigation is hidden.
- Automated unit and CI tests have not yet been added; current coverage uses assertions and Streamlit AppTest.
- Natural-language search, mood filters, topic modeling, and embedding pathfinding remain future features.
- Human-validated topic or emotion metadata is not currently available.

## Git/worktree situation

The current work has not been committed.

Tracked modifications:

- `README.md`
- `requirements.txt`
- `data/processed/song_atlas.csv`
- `data/processed/song_atlas_full.csv`

Currently untracked additions:

- `.streamlit/`
- `app/`
- `scripts/`
- `PROJECT_WORK_REPORT.md`
- `BTS_SONG_ATLAS_V2_REPORT.md`
- `CURRENT_STATUS_REPORT.md`

The entire application directory was already untracked when development began. These files need to be staged explicitly before they become part of repository history.

## Recommended next priorities

1. Perform visual browser QA at desktop, tablet, and mobile sizes.
2. Capture real portfolio screenshots and an Explore-mode GIF.
3. Add unit tests for canonical deduplication and similarity ranking.
4. Add interaction tests for overview, journey, comparison, and time filtering.
5. Decide whether empty secondary pages should be removed or populated.
6. Deploy a preview build and test external artwork loading.
7. Stage and commit the application, scripts, configuration, reports, README, and regenerated atlas exports.

## Overall assessment

The project is currently a functional, differentiated semantic music explorer rather than a dashboard prototype. Its strongest features are the map-first overview, immediate semantic-neighborhood hierarchy, fuzzy navigation, journey building, and dual-neighborhood comparison. The main remaining work is visual browser QA, media capture, formal automated testing, and repository finalization rather than core product functionality.
