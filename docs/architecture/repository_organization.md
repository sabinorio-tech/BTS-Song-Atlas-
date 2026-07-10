# Repository organization

## Decision

BTS Song Atlas is organized by product responsibility rather than development phase or release number. Product capabilities remain understandable as releases change, while folders named after phases quickly become ambiguous.

## Workstreams

- **Core Semantic Atlas** owns Spotify and Genius ingestion, cleaning, the song master, lyric embeddings, canonical-song projection, clustering, and stable atlas exports.
- **Personal Atlas** owns private Spotify-history ingestion, matching, listening aggregates, personal overlays, the personal map, and its implementation report.
- **BTS Universe** is an in-progress catalog expansion for member-solo and collaboration material. It should gain dedicated folders only when real artifacts exist; the current structure does not imply completion.
- **Audio Similarity** is feasibility research, not a production pipeline. Its scripts, evidence, and reports live under `research/audio_similarity`.
- **3D Explorer** is a product feasibility track. Its report remains in `docs/reports/` until implementation creates a real product workstream.

## Stable production data

Core processed artifacts remain directly under `data/processed/`. This is an intentional conservative choice: the deployed application, production rebuild script, and active notebooks already share these stable paths. Moving them would create deployment risk without improving responsibility boundaries.

Personal Atlas deployment artifacts remain under `data/processed/personal_atlas/`. Private source history belongs under `data/raw/personal_atlas/` and is ignored by Git.

## Path conventions

- Application paths resolve from `Path(__file__)`, never the shell working directory.
- Scripts resolve the project root from their own file location.
- Active notebooks search upward for a repository containing both `README.md` and `app/`.
- Documentation uses repository-relative links and never machine-specific local paths.

## Releases and folders

Git tags and release names describe shipped versions. They do not determine directory names. A capability can evolve across many releases without moving between versioned folders.

## Branch conventions

Use a short responsibility prefix:

- `feature/` for product capabilities, such as `feature/bts-universe`
- `research/` for feasibility work, such as `research/audio-similarity`
- `fix/` for defects and path corrections
- `chore/` for maintenance, such as `chore/reorganize-repository`
- `docs/` for documentation-only work

Keep branch names capability-oriented rather than phase- or version-oriented.
