import re

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

from backend.config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET
from backend.models import TrackInfo

# Patterns for extracting Spotify track IDs
TRACK_URL_PATTERN = re.compile(
    r"(?:https?://)?open\.spotify\.com/track/([a-zA-Z0-9]+)"
)
TRACK_URI_PATTERN = re.compile(r"spotify:track:([a-zA-Z0-9]+)")


def get_spotify_client() -> spotipy.Spotify:
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        raise ValueError(
            "Spotify credentials not configured. "
            "Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in your .env file."
        )
    auth_manager = SpotifyClientCredentials(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
    )
    return spotipy.Spotify(auth_manager=auth_manager)


def extract_track_id(url_or_uri: str) -> str:
    """Extract the Spotify track ID from a URL or URI."""
    url_or_uri = url_or_uri.strip()

    match = TRACK_URL_PATTERN.search(url_or_uri)
    if match:
        return match.group(1)

    match = TRACK_URI_PATTERN.search(url_or_uri)
    if match:
        return match.group(1)

    # Assume it's already a raw ID
    if re.match(r"^[a-zA-Z0-9]{22}$", url_or_uri):
        return url_or_uri

    raise ValueError(
        f"Could not extract a Spotify track ID from: {url_or_uri}"
    )


def get_track_info(url_or_uri: str) -> TrackInfo:
    """Fetch basic track metadata from Spotify (no audio features needed)."""
    sp = get_spotify_client()
    track_id = extract_track_id(url_or_uri)
    track = sp.track(track_id)

    album_images = track.get("album", {}).get("images", [])
    return TrackInfo(
        name=track["name"],
        artists=[a["name"] for a in track["artists"]],
        album=track["album"]["name"],
        album_art=album_images[0]["url"] if album_images else None,
        preview_url=track.get("preview_url"),
        spotify_url=track["external_urls"]["spotify"],
    )


def search_track(artist: str, track_name: str) -> TrackInfo | None:
    """Search Spotify for a track by artist + name. Returns metadata or None."""
    sp = get_spotify_client()
    query = f"artist:{artist} track:{track_name}"
    results = sp.search(q=query, type="track", limit=1)
    items = results.get("tracks", {}).get("items", [])
    if not items:
        return None

    t = items[0]
    album_images = t.get("album", {}).get("images", [])
    return TrackInfo(
        name=t["name"],
        artists=[a["name"] for a in t["artists"]],
        album=t["album"]["name"],
        album_art=album_images[0]["url"] if album_images else None,
        preview_url=t.get("preview_url"),
        spotify_url=t["external_urls"]["spotify"],
    )
