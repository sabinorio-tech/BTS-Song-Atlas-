# BTS Song Atlas — Final Audit Report

**Audit date:** 8 July 2026

## Overall readiness score

**9/10 — ready to commit and push after staging the intended worktree changes.**

The repository is in strong shape for a final portfolio-oriented push. Runtime dependencies are lightweight, the app boots from the repository root, processed data is internally consistent, and the README now explains the project clearly. The remaining items are mostly packaging and clarity concerns rather than release blockers.

## Passed checks

- Git hygiene: no obvious secrets, tokens, tracked `.env` files, cache directories, or screenshot junk detected.
- `.gitignore` now covers local secrets, caches, checkpoints, logs, and OS noise.
- Runtime dependency split is appropriate:
  - `requirements.txt` points to lightweight app runtime requirements.
  - `requirements/base.txt` keeps heavier research dependencies separate.
  - `pyarrow` is present for parquet loading.
- Streamlit configuration exists at `.streamlit/config.toml`.
- The app starts from the repo root with `streamlit run app/Home.py`.
- The app does not require Spotify or Genius secrets at runtime.
- `python3 -m compileall app scripts` passed.
- Streamlit AppTest startup passed after a small import-path fix.
- Default UI behavior is correct:
  - search defaults to `All songs`
  - compare mode renders its second selector
  - selecting a song exits overview mode and starts a journey
- Processed data checks passed for both `data/processed/song_atlas.csv` and `data/processed/song_atlas_full.csv`:
  - 381 rows
  - required columns present
  - unique `track_id`
  - no missing `x`, `y`, or `cluster`
  - 194 canonical titles
  - 194 primary versions
  - `version_count` values consistent
- Embeddings align with atlas outputs:
  - 381 embedding rows
  - 381 unique embedding `track_id` values
  - no atlas IDs missing from embeddings
  - no extra embedding IDs outside the atlas
- Rebuild reproducibility passed:
  - `scripts/core/rebuild_atlas_projection.py` reconstructs a valid 381-row projection
  - rebuilt metadata matches the checked-in atlas
  - coordinate deltas are only floating-point noise
- Notebooks `01` through `07` contain outputs and no stored error outputs.
- README is portfolio-ready and now covers architecture, pipeline, NLP, projection, deployment, and roadmap.
- Reports are already moved under `docs/reports/`, which keeps the root cleaner.

## Issues found

### Fixed

- `app/Home.py` depended on implicit script-path behavior for `from components import render_dashboard`.
  - Effect: Streamlit AppTest startup from the repo root failed with `ModuleNotFoundError: components`.
  - Resolution: added a small, safe app-directory path bootstrap in `app/Home.py`.

### Non-blocking

- `data/processed/song_atlas.csv` and `data/processed/song_atlas_full.csv` are currently identical.
  - This is not breaking the app, because duplicate-release behavior is controlled through `is_primary_version` and the UI toggle.
  - Recommendation: either document that both files are intentionally equivalent at this stage or simplify to one authoritative atlas export later.
- Portfolio media is still a placeholder state.
  - `docs/assets/.gitkeep` exists, and the README correctly documents the missing screenshots/GIF.
  - Real screenshots and one short exploration GIF should still be captured after deployment.
- Git currently shows notebook ingestion as a delete-plus-add:
  - deleted: `notebooks/01-spotify_ingestion.ipynb`
  - untracked: `notebooks/01_spotify_ingestion.ipynb`
  - Recommendation: stage this as the intended rename before commit.
- `app/pages/` is effectively empty.
  - This is acceptable for the current single-page product direction, but it is worth keeping that intentional in documentation rather than implying a live multipage app.

## Fixes applied

- Hardened app startup imports in `app/Home.py` so repo-root execution works under both `streamlit run` and Streamlit AppTest.
- Added this final audit report under `docs/reports/`.

## Validation commands run

- `python3 -m compileall app scripts` — passed
- `.venv/bin/python` Streamlit AppTest startup check for `app/Home.py` — passed after fix
- `.venv/bin/streamlit run app/Home.py --server.headless true --server.port 8502` — passed
- `.venv/bin/python` data integrity checks for atlas CSVs and embeddings parquet — passed
- `.venv/bin/python` rebuild projection check via `scripts/core/rebuild_atlas_projection.py` — passed
- notebook JSON scan for stored error outputs in notebooks `01`–`07` — passed
- repository secret-pattern scan — no matches found

## Remaining recommendations

- Stage the notebook rename intentionally so Git records it cleanly.
- Keep `main.py` deleted unless you specifically want a legacy entry point.
- Keep `notebooks/08_dashboard_testing.ipynb` deleted if it was empty and no longer part of the story.
- Capture real deployment screenshots and one short GIF into `docs/assets/`.
- If you want stricter long-term clarity, decide whether `song_atlas_full.csv` should remain as a documented duplicate of `song_atlas.csv` or become meaningfully distinct.

## Files changed

### Audit fix

- `app/Home.py`

### Audit report

- `docs/reports/FINAL_AUDIT_REPORT.md`

### Existing worktree changes observed during audit

- `.gitignore`
- `README.md`
- `requirements.txt`
- `test_spotify_api.py`
- `data/processed/song_atlas.csv`
- `data/processed/song_atlas_full.csv`
- `.streamlit/config.toml`
- `app/`
- `docs/`
- `scripts/`
- `main.py` deleted
- `notebooks/08_dashboard_testing.ipynb` deleted
- `notebooks/01-spotify_ingestion.ipynb` replaced by `notebooks/01_spotify_ingestion.ipynb`

## Suggested final commit command

If all current repository changes are intentional:

```bash
git add -A
git commit -m "Finalize BTS Song Atlas for deployment and portfolio readiness"
```

## Suggested final commit message

`Finalize BTS Song Atlas for deployment and portfolio readiness`

## Whether it is safe to push

**Yes — after staging the intended worktree changes, this repository is safe to push.**

The only caution is human intent, not technical readiness: confirm that the notebook rename, `main.py` deletion, and `08_dashboard_testing.ipynb` deletion are all meant to ship.
