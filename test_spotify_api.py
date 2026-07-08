from dotenv import load_dotenv
import os 
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials


def main() -> None:
    """Run a manual Spotify credentials and artist-search smoke check."""
    load_dotenv()
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("Spotify credentials are missing from the local .env file.")

    spotify = spotipy.Spotify(
        auth_manager=SpotifyClientCredentials(
            client_id=client_id,
            client_secret=client_secret,
        )
    )
    result = spotify.search(q="BTS", type="artist", limit=1)
    artist = result["artists"]["items"][0]
    print(f"Spotify API OK: {artist['name']} ({artist['id']})")


if __name__ == "__main__":
    main()
