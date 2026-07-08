# BTS Song Atlas V3 — Visual Polish Report

## Objective

V3 focuses exclusively on presentation, hierarchy, and exploration flow. It does not change embeddings, UMAP coordinates, canonical-song relationships, or the existing application architecture.

## High-impact improvements selected

The implementation prioritized nine changes that offered strong visual impact without a frontend rewrite:

1. Tighter, geometry-preserving map framing.
2. A subtle native Plotly density layer.
3. Similarity-weighted connection lines.
4. Stronger selected-node hierarchy.
5. More restrained distant-song presentation.
6. Premium hover-label styling.
7. Deeper background and map-surface treatment.
8. Refined artwork, story, timeline, and neighbor presentation.
9. A clearer invitation to continue the semantic journey.

## Atlas camera and space usage

- The complete semantic cloud now receives only 3.5% axis padding.
- The displayed coordinate bounds retain the projection's 1.377 aspect ratio.
- The y-axis is anchored to the x-axis with an equal scale ratio, preventing visual distortion of semantic distance.
- Search focus uses a camera window based on that same aspect ratio.
- Existing `uirevision` behavior continues to preserve user zoom and pan.

No coordinate values were changed.

## Background depth and density

- A low-opacity `Histogram2dContour` trace now sits behind the song points.
- The contour is calculated from the currently visible coordinates and communicates dense semantic regions without changing point positions.
- The layer has no hover behavior, labels, legend, or color scale.
- CSS adds soft violet and blue radial lighting, a gentle vertical vignette, and deeper map shadows.
- No stars or decorative particle fields were introduced.

## Visual hierarchy

### Selected song

- 54px low-opacity outer halo.
- 38px inner violet glow.
- 24px bright-blue core.
- White outline and persistent text label.

### Semantic neighbors

- Similarity continues to control point size and color strength.
- Closest neighbors can reach 19px.
- The first ten neighbors receive labels; larger 20/50-song neighborhoods remain uncluttered.

### Remaining songs

- Default base size reduced to 5.5px.
- After selection, unrelated songs fade to 5.5% opacity.
- In the All-songs overview, every song remains at 78% opacity.

## Similarity connections

Connections are now divided into three native WebGL strength buckets:

| Relative strength | Width | Opacity |
|---|---:|---:|
| Lower | 0.7px | 10% |
| Medium | 1.2px | 20% |
| Highest | 2.0px | 36% |

This creates visible similarity hierarchy while keeping trace count bounded. Even a 50-song neighborhood uses three connection traces instead of fifty.

Compare mode uses the same approach with amber lines.

## Hover experience

- Native Plotly hover labels now use a near-opaque dark surface.
- Violet borders, brighter text, and readable 12px typography improve contrast.
- Hover names are not truncated.

WebGL point enlargement on hover is not available through native Streamlit Plotly events. Implementing it would require custom JavaScript and introduce rerender or performance costs, so it was intentionally not added.

## Right-panel refinement

- Selected artwork increased to 98px.
- Artwork receives a subtle border, shadow, and glow.
- The song hero now has a premium gradient card treatment.
- Metadata uses a bordered glass-like surface.
- Similarity bars are thicker, brighter, and softly illuminated.
- Neighbor rows receive lightweight hover and movement feedback.
- Semantic stories use improved spacing, contrast, and a restrained gradient.
- A “Continue the journey” cue now leads directly into the fuzzy neighbor selector.

## Album artwork decision

Artwork remains emphasized in the selected-song and neighbor panels rather than being placed directly over map coordinates.

Native Plotly layout images are available, but map images:

- are not WebGL markers;
- do not participate naturally in point selection;
- introduce external image loading and CORS behavior;
- can obscure nearby semantic points and labels;
- cannot appear automatically at a zoom threshold because Streamlit does not expose Plotly relayout events.

Keeping map nodes geometric preserves performance and interaction clarity while the details panel supplies strong artwork context.

## Progressive labels

The current native compromise remains:

- Overview: no arbitrary labels.
- Selected song: always labeled.
- Neighborhood: up to ten closest songs labeled.
- Larger neighborhoods: highlighted but not fully labeled.

True zoom-level label switching requires browser relayout events unavailable in native Streamlit.

## Minimap and Explore mode

The existing native implementation remains in place:

- WebGL overview map.
- Selected-song and journey highlighting.
- Point selection to refocus the main map.
- Connected Explore-mode journey.

A synchronized viewport rectangle is still not feasible without Plotly relayout synchronization.

## Performance results

Measured with the maximum 50-song neighborhood:

- Figure traces: 15.
- Serialized figure size: approximately 48.4 KB.
- Local Python build and serialization time: approximately 0.255 seconds.
- Weighted connection widths confirmed at 0.7, 1.2, and 2.0px.
- Main atlas and minimap render successfully through Streamlit AppTest.

## Validation

- All-songs overview: zero exceptions.
- Song search and focus: zero exceptions.
- Compare mode: zero exceptions.
- Fifty-neighbor and 2013 time-boundary combination: zero exceptions.
- Python compilation: successful.
- Dependency consistency: no broken requirements.
- Git whitespace validation: successful.
- Atlas and embedding hashes remain unchanged.

## Final assessment

V3 makes the atlas feel denser, more intentional, and more alive while keeping interaction fast and native. Visual attention now moves clearly from the complete semantic field to the selected song, then through weighted connections to the nearest neighbors, and finally into the journey control. The result remains a maintainable Streamlit/Plotly product rather than a collection of custom effects.
