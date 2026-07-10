# 3D Semantic Explorer Feasibility Report

**Date:** 9 July 2026

## Summary

An optional 3D Semantic Explorer is technically feasible for BTS Song Atlas and fits the product philosophy better as an **immersive secondary view** than as a replacement for the current analytical atlas.

The strongest implementation path is:

- keep the current 2D atlas unchanged
- generate a parallel 3D projection from the same embedding pipeline
- expose 3D as an optional explorer mode
- preserve only the interactions that remain clear and reliable in 3D

## Recommendation

**Recommended**

It is technically achievable with the current stack, the dataset size is small enough for Plotly 3D, and the repository impact can be contained. However, 3D should stay explicitly optional because analytical clarity, accessibility, and mobile usability are all weaker than the current 2D atlas.

## 1. UMAP Feasibility

### Can UMAP simply be regenerated with `n_components=3`?

Yes.

The current projection script already builds canonical-song centroids and fits UMAP on those centroids in [scripts/core/rebuild_atlas_projection.py](../../scripts/core/rebuild_atlas_projection.py). Right now the script uses:

- the same normalized lyric embeddings
- the same canonical-title grouping
- the same UMAP hyperparameters
- `n_components=2`

UMAP’s own parameter documentation shows that `n_components` directly controls the output dimensionality, and their example explicitly demonstrates `n_components=3` for 3D embeddings. Sources:

- UMAP parameters docs: https://umap-learn.readthedocs.io/en/latest/parameters.html

### What changes exactly?

The embedding pipeline does **not** need to change:

- no changes to SentenceTransformers
- no changes to cosine-similarity logic
- no changes to canonical-title grouping
- no changes to duplicate-release handling

Only the projection stage changes:

- current output: `x`, `y`
- future 3D output: `x3`, `y3`, `z3` or `x`, `y`, `z` in a parallel file

### Important caution

Changing UMAP from 2D to 3D is not just “adding one more column” to the exact same layout. It creates a **different manifold embedding**. Local neighborhoods should remain broadly meaningful, but the geometry will not be identical to the 2D projection.

That matters because the current clustering is fit on 2D coordinates. If the current script were simply switched from `n_components=2` to `n_components=3`, both:

- coordinates
- HDBSCAN cluster assignments

could change.

### Best interpretation for this project

The cleanest approach is:

- leave the current 2D atlas and 2D cluster labels untouched
- generate a separate 3D coordinate export from the same centroids
- initially reuse existing cluster labels from the 2D atlas for coloring and storytelling consistency

That keeps 3D exploratory instead of making it a competing analytical truth source.

## 2. Plotly 3D in Streamlit

### Can Plotly render an interactive `Scatter3d` efficiently in Streamlit?

Yes, in principle.

Plotly supports `go.Scatter3d`, `customdata`, and `hovertemplate`, which means the current metadata-rich point rendering pattern can be carried into 3D. Sources:

- Plotly 3D scatter docs: https://plotly.com/python/3d-scatter-plots/
- Plotly `scatter3d` reference: https://plotly.com/python/reference/scatter3d/

Plotly’s 3D scene also supports camera and interaction configuration such as:

- `camera`
- `dragmode`
- `aspectmode`
- annotations within the 3D scene

Sources:

- Plotly `layout.scene` reference: https://plotly.com/python/reference/layout/scene/

### Interaction support by category

#### Rotation

Supported. Plotly scene drag modes include `orbit` and `turntable`, which are appropriate for exploration.

#### Zoom

Supported.

#### Pan

Supported.

#### Hover

Supported. `Scatter3d` supports `hovertemplate`, so the current tooltip style can be translated to 3D.

#### Click / point selection

Likely workable for the current app model, but this is the main area that deserves a prototype before implementation.

The current app relies on Streamlit’s Plotly selection return value in [app/components.py](../../app/components.py), using:

- `on_select="rerun"`
- `selection_mode="points"`
- `customdata` to recover the selected `track_id`

Streamlit documents that `st.plotly_chart` supports selection events and returns a `PlotlyState`, but also states that **only selection events are supported at this time**. Source:

- Streamlit `st.plotly_chart` docs: https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart

That means:

- direct point selection is the right event model to depend on
- hover state and camera movement are not returned to Python
- any richer 3D interaction that depends on live camera state would require a custom component or JavaScript bridge

#### Camera controls

Supported from the Plotly side. Explicit camera presets and reset buttons are feasible through figure layout/state management.

#### Responsiveness

Reasonable for desktop and tablet. Less convincing for mobile because 3D gestures compete with page scroll and the control density becomes awkward.

## 3. Can Existing Interactions Be Preserved?

### Search

Yes.

Search is UI-state driven in [app/components.py](../../app/components.py) and does not depend on the chart being 2D. A selected `track_id` can still be found and highlighted in 3D.

### Hover tooltips

Yes.

Plotly `Scatter3d` supports the same hover templating model already used in 2D.

### Clicking songs

Probably yes for single-point selection, but it will feel less reliable than 2D because of depth and occlusion. The current app should continue to rely on single-point selection only, not box/lasso workflows.

### Nearest neighbors

Yes.

Nearest-neighbor logic comes from embedding similarity in [app/utils.py](../../app/utils.py), not from the plotted coordinates. The 3D chart only changes how those relationships are displayed.

### Highlighted selections

Yes.

Selected-song halos, neighbor highlighting, compare colors, and journey paths can all be recreated in `Scatter3d` with separate traces, the same way the current 2D atlas layers traces in [app/visualization.py](../../app/visualization.py).

### Journey mode

Yes, with caveats.

Journey paths can become glowing 3D polylines between selected songs. This is a strong fit for the “explore a universe” concept. The tradeoff is that overlapping paths will be harder to read from some camera angles.

### What should not be promised up front

- exact analytical clarity equal to 2D
- frictionless point selection at all camera angles
- mobile interaction quality equal to the current 2D atlas
- camera-aware behaviors tied to Python callbacks

## 4. Performance

### Current scale

The current default analytical view is about `194` canonical songs, with `381` total release rows available when duplicates are shown.

### Future scale

A future `400–600` canonical-song explorer remains reasonable for Plotly 3D.

### Local benchmark

Using the current processed atlas and a lightweight `Scatter3d` prototype:

- `194` rows: about `29.6 KB` serialized figure payload
- `400` rows: about `48.4 KB`
- `600` rows: about `66.8 KB`

Those are small figures by Plotly standards.

### WebGL suitability

Yes, WebGL remains appropriate.

Streamlit’s docs note that Plotly uses WebGL beyond `1000` data points and also warn that browsers have limits on the number of WebGL contexts per page. Source:

- Streamlit `st.plotly_chart` docs: https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart

Practical implication for this project:

- one main 3D explorer should be fine
- avoid multiple simultaneous 3D views on the same screen
- do not pair a heavyweight 3D main plot with another heavyweight 3D minimap

### Performance conclusion

For `194` songs and even `400–600` songs, a single Plotly 3D explorer should remain smooth on desktop hardware if the trace count stays controlled.

## 5. Visual Design Recommendations

The 3D explorer should feel elegant, not overloaded.

Recommended additions:

- floating cluster labels positioned near cluster centroids
- a `Reset camera` button
- 2–4 preset camera angles such as `front`, `top`, `diagonal`, `journey`
- subtle animated transitions when changing selected song
- glowing journey lines
- stronger selected-song halo than surrounding points
- optional projected shadows or axis-plane projections for depth cues
- very light depth fog only if it improves legibility

Recommended restraint:

- no dense particle effects
- no constant auto-rotation by default
- no extra minimap in 3D mode
- no attempt to port every 2D annotation directly into floating 3D text

Best UX framing:

- 2D = analysis
- 3D = immersion and spatial exploration

## 6. Architecture Recommendation

The cleanest implementation is parallel, not invasive.

### Current

Embeddings  
↓  
UMAP 2D  
↓  
`song_atlas.csv` / `song_atlas_full.csv`

### Proposed

Embeddings  
↓  
UMAP 2D  
↓  
existing atlas outputs remain unchanged

Embeddings  
↓  
UMAP 3D  
↓  
parallel 3D coordinate file

### Suggested data split

- keep current 2D files untouched
- add a new coordinate artifact, for example:
  - `data/processed/song_atlas_3d.csv`
  - or `data/processed/atlas_coordinates_3d.parquet`

Recommended contents:

- `track_id`
- `canonical_title`
- `x3`
- `y3`
- `z3`
- optionally `is_primary_version`
- optionally `version_count`
- optionally reused 2D `cluster`

### Why this is better

- zero regression risk for the current app
- easier A/B comparison between 2D and 3D
- simpler rollback if 3D proves weak in practice
- cleaner deployment story because 2D remains the production default

## 7. Repository Impact

### Notebooks affected

- [notebooks/core/07_song_atlas.ipynb](../../notebooks/core/07_song_atlas.ipynb) if exploratory 3D prototyping is done notebook-first

### Scripts affected

- [scripts/core/rebuild_atlas_projection.py](../../scripts/core/rebuild_atlas_projection.py) or a parallel new script for 3D coordinate generation

### App files affected

- [app/visualization.py](../../app/visualization.py)
- [app/components.py](../../app/components.py)
- possibly [app/styles.css](../../app/styles.css)

### Data files affected

- one new processed 3D coordinate file
- no changes required to embeddings parquet
- no changes required to the current 2D atlas outputs

### Feature sizing

This is best treated as a **v1.1 feature**, not a minor patch and not a full v2 rewrite.

Why:

- it adds a meaningful new interaction surface
- it affects projection generation and app UI
- but it does not require replacing the core product architecture

## 8. Potential Limitations

### Point occlusion

The main analytical weakness of 3D. Songs can hide behind one another depending on camera angle.

### Navigation usability

3D is engaging but less precise. Users can become disoriented without reset controls and camera presets.

### Accessibility

Worse than the current 2D atlas. Depth perception, fine motor precision, and visual clutter are bigger issues in 3D.

### Mobile support

Weaker than 2D. Touch-based rotate/zoom interactions are possible but less comfortable, especially alongside Streamlit controls.

### Rendering limitations

Plotly 3D is strong enough for this scale, but it is still a browser-rendered scientific chart, not a game engine. Dense labels and too many effect layers will hurt readability quickly.

### Streamlit compatibility

The biggest limitation is not rendering but event richness:

- Streamlit supports Plotly selection events
- it does not expose arbitrary live hover/camera callbacks back to Python

So the 3D explorer should avoid designs that depend on continuous camera-aware logic.

## Final Recommendation

**Recommended**

Add a 3D Semantic Explorer only as an optional secondary mode.

It is a strong thematic fit for “exploring a universe of songs,” and the current stack is capable of supporting it at the project’s scale. The safest version is a parallel 3D coordinate pipeline plus a deliberately simplified 3D interaction model:

- search
- hover
- point selection
- neighbor highlighting
- journey path display
- reset/preset camera controls

The current 2D atlas should remain the default because it is still better for:

- analysis
- accessibility
- annotation clarity
- comparison tasks
- predictable navigation

In short: technically feasible, product-aligned, and worth exploring, but only if it stays secondary to the 2D atlas and avoids trying to replicate every analytical affordance in 3D.
