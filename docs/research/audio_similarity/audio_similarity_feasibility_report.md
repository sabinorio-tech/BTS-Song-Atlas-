# Audio similarity research Audio Similarity Research

## Objective

Audio similarity research investigated whether BTS Song Atlas could add an independent audio recommendation engine without changing the existing lyric-based semantic atlas from Phase 1.

The intended product direction was:

- keep the current lyric embedding atlas and map coordinates unchanged
- add a separate audio similarity pipeline
- support future exploration modes such as:
  - Lyrics
  - Audio
  - Hybrid

The Audio similarity research branch was therefore framed as a technical feasibility investigation, not as a production implementation.

## Investigation Timeline

### 1. Spotify Audio Features

The first investigation tested whether Spotify Web API audio descriptors could serve as the foundation for an audio recommendation system.

Existing project research was consolidated into a live diagnostic script:

- [`check_spotify_audio_features.py`](../../../scripts/research/audio_similarity/check_spotify_audio_features.py)
- supporting note: [`spotify_audio_feature_check.md`](spotify_audio_feature_check.md)

What was checked:

- application authentication with the client credentials flow
- normal track metadata access
- `GET /v1/audio-features/{id}`
- `GET /v1/audio-analysis/{id}`

Observed results from the live check:

- authentication succeeded
- track metadata endpoint returned HTTP `200`
- audio features endpoint returned HTTP `403`
- audio analysis endpoint returned HTTP `403`

Interpretation:

- the Spotify app credentials are valid
- the track ID is valid
- the failure is specific to the audio endpoints

Conclusion:

Spotify audio features are unavailable for this application. This is a platform access limitation rather than an implementation bug.

### 2. Commercial APIs

After Spotify audio endpoints proved unavailable, the investigation widened to commercial alternatives.

Services considered in the Audio similarity research research notes:

- Apple Music
- Deezer
- ReccoBeats
- other proprietary Spotify replacements

Strengths observed:

- low operational cost if a stable API already exposes usable descriptors
- no need to build a large local modeling stack immediately
- faster path to a prototype if coverage and access are sufficient

Weaknesses observed:

- external vendor dependency becomes part of the product architecture
- long-term reproducibility depends on a third-party service remaining available
- pricing, quotas, or API policy changes can block the feature later
- portability becomes weaker because the recommendation logic depends on a commercial source outside the repository

Conclusion:

Commercial APIs remain possible in principle, but they introduce long-term external dependency risk and vendor lock-in. For a portfolio-quality, reproducible repository, that is a significant architectural tradeoff.

### 3. Open Music Datasets

The next investigation focused on open metadata and descriptor sources, especially MusicBrainz and AcousticBrainz.

Research artifacts:

- [`check_acousticbrainz.py`](../../../scripts/research/audio_similarity/check_acousticbrainz.py)
- [`acousticbrainz_coverage.csv`](../../../data/processed/research/audio_similarity/acousticbrainz_coverage.csv)

Method:

- start from the current BTS Song Atlas song set
- look up candidate MusicBrainz recordings by ISRC when available
- fall back to title + artist search
- check whether AcousticBrainz high-level or low-level descriptors exist for the matched recording

Measured coverage results:

- Total songs checked: `381`
- MusicBrainz matches: `250` (`65.6%`)
- AcousticBrainz matches: `109` (`28.6%`)

Why the coverage is insufficient:

- a production recommendation engine needs broad catalogue coverage, not a minority subset
- missing coverage is uneven rather than neatly isolated, which weakens consistency across the discography
- low coverage would create a fragmented user experience where some songs support audio mode and many do not
- fallback logic would become complex and difficult to explain
- missing or ambiguous MusicBrainz matches introduce additional uncertainty before audio descriptors are even considered

Conclusion:

MusicBrainz is useful as open metadata infrastructure, but AcousticBrainz coverage is too limited for a production BTS audio similarity system.

### 4. Local Audio Analysis

The investigation then shifted from third-party descriptors to fully local processing.

Approaches considered:

- Librosa
- MERT
- CLAP
- OpenL3
- modern pretrained music embedding models

Why these approaches are technically attractive:

- they avoid dependence on fragile external APIs
- they allow full local processing once audio is available
- they can produce richer representations than legacy hand-authored music descriptors
- they align better with the project’s existing vector similarity workflow
- they would fit naturally with the project’s existing embedding and nearest-neighbor design

Advantages:

- full local processing
- stronger long-term control over the pipeline
- better extensibility for future experimentation
- cleaner engineering ownership than relying on vendor APIs

Blocking issue:

All of these approaches still require access to the underlying audio files. Model quality was not the limiting factor; audio acquisition was.

### 5. Audio Acquisition Investigation

The final investigation focused on the true bottleneck: acquiring the complete BTS catalogue in a way that is lawful, reproducible, and appropriate for the repository.

Key findings:

- Spotify does not expose downloadable track audio through the Web API
- public commercial embedding datasets suitable for this exact catalogue and use case were not available as a clean drop-in solution
- building a local audio pipeline would require maintaining external audio assets outside the repository’s current reproducible data flow
- copyright and redistribution considerations make it inappropriate to treat commercial audio files as part of the project’s primary reproducible pipeline

Why this matters:

- local audio analysis is technically feasible
- local audio analysis is not repository-friendly unless the source audio can be acquired and documented reproducibly
- without a dependable acquisition strategy, any resulting audio similarity system would be difficult for others to reproduce from the repository alone

Conclusion:

Obtaining the complete BTS catalogue in a reproducible and policy-safe way is the primary blocker. The hard problem is not model choice; it is data availability.

## Final Evaluation

| Source | Availability | Coverage | Reproducibility | Maintenance | Recommendation |
| --- | --- | --- | --- | --- | --- |
| Spotify Audio Features | Blocked for this app | Not usable | Weak | Medium | Reject |
| Apple Music | Possible metadata source | Unclear for audio descriptors | Weak | Medium | Reject for core pipeline |
| Deezer | Possible metadata source | Unclear for robust audio descriptors | Weak | Medium | Reject for core pipeline |
| Commercial APIs | Potentially usable | Vendor-dependent | Weak | High | Avoid as primary architecture |
| MusicBrainz | Public metadata access | Partial | Good | Medium | Useful support data only |
| AcousticBrainz | Public descriptor source | 109 / 381 songs | Medium | Medium | Insufficient for production |
| Librosa | Fully local if audio exists | Potentially full | Weak without audio source | High | Technically viable, blocked by data |
| MERT | Fully local if audio exists | Potentially full | Weak without audio source | High | Strong long-term option if audio source exists |
| CLAP | Fully local if audio exists | Potentially full | Weak without audio source | High | Strong long-term option if audio source exists |

## Final Decision

The semantic lyric atlas from Phase 1 remains the production implementation.

Audio similarity is not implemented in this branch because the limiting factor is data availability, not engineering capability.

Future implementation should proceed only if a reliable, legal, and reproducible audio source becomes available. Until then, the most responsible engineering choice is to keep the repository centered on the lyric-based semantic atlas.

## Lessons Learned

- Validate external dependency assumptions before implementation work begins.
- API authentication success does not imply endpoint access.
- Reproducibility matters as much as model quality in portfolio and research repositories.
- Data availability is often the real constraint, even when the modeling approach is clear.
- Open datasets can still be operationally insufficient when catalogue coverage is low.
- Sometimes the correct engineering decision is to stop short of implementation.

## Repository Cleanup

Audio similarity research was converted from an implementation branch into a documented research branch.

Kept as supporting artifacts:

- [`check_spotify_audio_features.py`](../../../scripts/research/audio_similarity/check_spotify_audio_features.py)
- [`check_acousticbrainz.py`](../../../scripts/research/audio_similarity/check_acousticbrainz.py)
- [`spotify_audio_feature_check.md`](spotify_audio_feature_check.md)
- [`acousticbrainz_coverage.csv`](../../../data/processed/research/audio_similarity/acousticbrainz_coverage.csv)

Removed as temporary research scaffolding:

- `notebooks/research/audio_similarity/08_audio_representation_research.ipynb`

Audio similarity research now reads as a bounded engineering investigation rather than a half-implemented feature branch.
