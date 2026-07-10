import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# Test with a known BTS track.
# Dynamite Spotify track ID:
TEST_TRACK_ID = "4saklk6nie3yiGePpBwUoc"


def get_access_token() -> str:
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        raise ValueError("Missing SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET in .env")

    auth_string = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    auth_bytes = auth_string.encode("utf-8")
    auth_b64 = base64.b64encode(auth_bytes).decode("utf-8")

    response = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "client_credentials"},
        timeout=20,
    )

    print("Token status:", response.status_code)

    if response.status_code != 200:
        print(response.text)
        response.raise_for_status()

    return response.json()["access_token"]


def test_endpoint(access_token: str, endpoint_name: str, url: str) -> None:
    print(f"\nChecking: {endpoint_name}")
    print("URL:", url)

    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=20,
    )

    print("Status:", response.status_code)

    try:
        data = response.json()
        print("Response preview:")
        print(data)
    except Exception:
        print(response.text[:500])


def main() -> None:
    token = get_access_token()

    test_endpoint(
        access_token=token,
        endpoint_name="Track metadata",
        url=f"https://api.spotify.com/v1/tracks/{TEST_TRACK_ID}",
    )

    test_endpoint(
        access_token=token,
        endpoint_name="Audio features",
        url=f"https://api.spotify.com/v1/audio-features/{TEST_TRACK_ID}",
    )

    test_endpoint(
        access_token=token,
        endpoint_name="Audio analysis",
        url=f"https://api.spotify.com/v1/audio-analysis/{TEST_TRACK_ID}",
    )


if __name__ == "__main__":
    main()