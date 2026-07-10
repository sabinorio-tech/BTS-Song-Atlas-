# Spotify Audio Feature Check

**Date checked:** 9 July 2026

## Context

Audio similarity research includes a small diagnostic script at [`check_spotify_audio_features.py`](../../../scripts/research/audio_similarity/check_spotify_audio_features.py) to verify whether Spotify Web API audio endpoints are accessible for this project.

The script:

- loads `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` from the local `.env`
- requests an app access token using the client credentials flow
- tests one known BTS track ID: `4saklk6nie3yiGePpBwUoc` (`Dynamite`)
- calls three endpoints:
  - `GET /v1/tracks/{id}`
  - `GET /v1/audio-features/{id}`
  - `GET /v1/audio-analysis/{id}`

## Live check results

A live run was performed against Spotify using the local project credentials.

Results:

- token request: `200`
- track metadata: `200`
- audio features: `403`
- audio analysis: `403`

Observed behavior:

- authentication works
- the track ID is valid
- normal Spotify track metadata remains accessible
- the failure is specific to the audio feature and audio analysis endpoints

## Conclusion

This is a real Spotify access restriction, not just a local script bug.

For this app, Spotify currently allows basic metadata access but denies:

- `GET /v1/audio-features/{id}`
- `GET /v1/audio-analysis/{id}`

## Likely reason

Spotify announced Web API restrictions on **November 27, 2024**. Their developer notice says new Web API use cases can no longer access several endpoints, including:

- Audio Features
- Audio Analysis

Spotify also says this affects:

- existing apps still in development mode without a pending extension request
- new apps registered on or after November 27, 2024

Based on the live `403` responses, this project’s current app falls into an affected category.

## References

- Spotify change notice: https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api
- Audio Features reference: https://developer.spotify.com/documentation/web-api/reference/get-audio-features
- Audio Analysis reference: https://developer.spotify.com/documentation/web-api/reference/get-audio-analysis
- Quota modes / development mode: https://developer.spotify.com/documentation/web-api/concepts/quota-modes
