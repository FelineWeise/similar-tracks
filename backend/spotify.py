import re

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

from backend.config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET
from backend.models import AudioFeatures, SimilarityWeights, TrackInfo

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


def _build_audio_features(raw: dict) -> AudioFeatures:
    return AudioFeatures(
        bpm=raw["tempo"],
        energy=raw["energy"],
        danceability=raw["danceability"],
        valence=raw["valence"],
        instrumentalness=raw["instrumentalness"],
        speechiness=raw["speechiness"],
        acousticness=raw["acousticness"],
        liveness=raw["liveness"],
    )


def _build_track_info(track: dict, features: dict | None = None) -> TrackInfo:
    album_images = track.get("album", {}).get("images", [])
    return TrackInfo(
        name=track["name"],
        artists=[a["name"] for a in track["artists"]],
        album=track["album"]["name"],
        album_art=album_images[0]["url"] if album_images else None,
        preview_url=track.get("preview_url"),
        spotify_url=track["external_urls"]["spotify"],
        audio_features=_build_audio_features(features) if features else None,
    )


def get_track_with_features(
    sp: spotipy.Spotify, track_id: str
) -> tuple[dict, dict]:
    """Fetch track metadata and its audio features."""
    track = sp.track(track_id)
    features = sp.audio_features([track_id])[0]
    if features is None:
        raise ValueError(f"Audio features unavailable for track: {track_id}")
    return track, features


def find_similar_tracks(
    url_or_uri: str,
    weights: SimilarityWeights,
    limit: int = 10,
) -> tuple[TrackInfo, list[TrackInfo]]:
    """Find tracks similar to the given one, respecting user weight preferences."""
    sp = get_spotify_client()
    track_id = extract_track_id(url_or_uri)
    seed_track, seed_features = get_track_with_features(sp, track_id)

    # Build recommendation parameters based on weights.
    # For each dimension the user cares about (weight > 0), we set a
    # target value equal to the seed track's value so Spotify's
    # recommendation engine tries to match it.
    rec_kwargs: dict = {
        "seed_tracks": [track_id],
        "limit": limit,
    }

    if weights.bpm > 0:
        rec_kwargs["target_tempo"] = seed_features["tempo"]
    if weights.mood > 0:
        rec_kwargs["target_valence"] = seed_features["valence"]
    if weights.style > 0:
        rec_kwargs["target_danceability"] = seed_features["danceability"]
        rec_kwargs["target_energy"] = seed_features["energy"]
    if weights.vocals > 0:
        rec_kwargs["target_speechiness"] = seed_features["speechiness"]
    if weights.instrumentals > 0:
        rec_kwargs["target_instrumentalness"] = seed_features["instrumentalness"]

    results = sp.recommendations(**rec_kwargs)
    rec_track_ids = [t["id"] for t in results["tracks"]]

    # Fetch audio features for all recommended tracks in one call
    all_features = {}
    if rec_track_ids:
        features_list = sp.audio_features(rec_track_ids)
        for f in features_list:
            if f:
                all_features[f["id"]] = f

    seed_info = _build_track_info(seed_track, seed_features)
    similar = [
        _build_track_info(t, all_features.get(t["id"]))
        for t in results["tracks"]
    ]

    return seed_info, similar
