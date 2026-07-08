# BTS Song Atlas V2 — Implementation Report

## Outcome

V2 shifts the application from a dashboard-style presentation to a map-first semantic explorer. The atlas is now the immediate focal point, and selecting a song transforms the map into a readable semantic neighborhood.

The existing UMAP coordinates, embeddings, and processed semantic relationships were not modified. Their SHA-256 hashes were recorded before implementation and verified unchanged afterward.

## Implemented improvements

### Map-first experience

- Removed the five-card KPI strip.
- Increased the atlas height and content width.
- Replaced dashboard language with an exploration-focused map heading.
- Kept only a compact song/release summary in the sidebar.

### Semantic neighborhood highlighting

- The selected song has a blue core, white edge, and soft violet glow.
- The ten closest canonical songs receive a dedicated violet similarity layer.
- Neighbor size and color intensity reflect cosine-similarity strength.
- Distant songs fade to low opacity by default.
- Neighbor labels can be toggled without labeling unrelated songs.
- Soft connection lines use one combined WebGL trace to avoid clutter and excess rendering cost.
- A small map annotation explains the visual language.

### Search

- Search now uses Streamlit 1.59’s native fuzzy `selectbox` filtering.
- It provides autocomplete, close-spelling matching, arrow-key navigation, and Enter selection without custom JavaScript.
- Search operates on one primary release per canonical title.
- A searched song remains visible even when existing filters would otherwise hide it, without discarding the user's filter choices.
- The map opens a focused viewport around the searched song and updates its details and semantic neighbors.

### Smooth exploration

- Song-map interactions remain inside a Streamlit fragment.
- Point selection reruns only the explorer fragment.
- Stable Plotly `uirevision` values preserve user zoom and pan during map selection.
- A new viewport revision is created only for explicit search or neighbor-focus actions.
- The map remains WebGL-based and uses a single combined edge trace.

### Color modes

Color can be switched without changing coordinates:

- Album
- Release Year
- Language
- Word Count
- Semantic Cluster

### Details and recommendations

- The details panel retains artwork, title, album, year, type, duration, word count, character count, detected language, Spotify, Genius, lyrics preview, and ten similar songs.
- Recommendations continue using cosine similarity over the existing multilingual embeddings.
- The selected canonical song is excluded.
- Only the preferred primary release of each canonical recommendation is shown.
- A fuzzy “Jump to a neighbor” control supports continued map exploration.

## Architecture

- `components.py` handles Streamlit layout and interaction state.
- `visualization.py` exclusively builds the Plotly atlas.
- `utils.py` handles data loading, metadata enrichment, cosine similarity, and formatting.
- `styles.css` owns the visual system.
- `utiles.py` remains only as a compatibility import shim.

## Native capability decisions

Native Streamlit and Plotly features were checked before implementation:

- Native fuzzy search was available and used.
- Native fragment reruns were available and used.
- Native Plotly viewport persistence was available through `uirevision` and used.
- Native WebGL scatter layers were available and used.

Two requested effects are not fully client-side in native Streamlit:

- Streamlit still performs a fragment rerun when Plotly reports a point selection. The rerun is scoped and viewport-stable, but it is not a pure browser-side state update.
- Plotly does not provide a lightweight continuous pulse for WebGL points through Streamlit. A static two-layer glow was used to preserve performance and avoid custom JavaScript.

## Validation

- All five color modes successfully build and serialize.
- The map renders ten distinct canonical semantic neighbors.
- Search-focus figures receive a bounded viewport around the selected song.
- Python compilation passes for the application.
- Streamlit AppTest renders with zero exceptions.
- The V2 render contains one atlas, three search/navigation selectboxes, four advanced toggles, and no KPI metrics.
- Git whitespace validation passes.
- Atlas CSV and embedding Parquet hashes remained unchanged throughout V2 implementation.

## Documents integration

The requested Documents plugin was not available among the installable connectors in this workspace. This report was therefore saved directly in the repository as the local documentation fallback.

## Vision prompt follow-up

The later exploration vision was implemented without changing the semantic datasets:

- Explore mode records up to twelve visited songs and draws the journey through semantic space.
- Back and clear-path controls support deliberate navigation.
- Compare mode renders a blue/violet and amber dual neighborhood, with shared neighbors in gold.
- Comparison reports cosine similarity, 2D map distance, albums, years, and shared/unique neighbor counts.
- Neighborhood size can be changed between 5, 10, 20, and 50 and drives both map layers and the side panel.
- Labels remain progressive by showing only the first ten neighbors even when 20 or 50 are highlighted.
- A rule-based semantic story reports only observable cluster, neighbor, year, and word-count facts.
- Neighbor rows include similarity bars and live inside a bounded scroll region.
- The catalog timeline shows a song's release-year position.
- The Time Explorer progressively reveals the atlas through a selected release year.
- Recent fuzzy searches and popular-song shortcuts are available.
- A WebGL overview map shows the selected song and journey; selecting a point refocuses the main atlas.
- Deployment configuration and root Streamlit requirements were added.
- `README.md` was transformed into a portfolio document with architecture and pipeline diagrams.

Native limitations remain explicit:

- Streamlit does not expose Plotly relayout events, so viewport-dependent label density and automatic close-zoom artwork cannot be implemented without a custom JavaScript component.
- The overview map can navigate by point selection but cannot display or drag the main viewport rectangle.
- Connection appearance uses Plotly's transition support, not a continuous custom animation loop.
- A real README screenshot was attempted with local headless Chrome. The WSL browser captured only Streamlit's shell before its WebSocket-rendered contents, so the blank image was removed and the media capture is documented as a deployment follow-up.
