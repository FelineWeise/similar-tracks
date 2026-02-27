import httpx

DEEZER_SEARCH = "https://api.deezer.com/search"


def get_preview_url(artist: str, track_name: str) -> str | None:
    """Search Deezer for a track and return its 30-second preview URL, or None."""
    query = f'artist:"{artist}" track:"{track_name}"'
    try:
        resp = httpx.get(
            DEEZER_SEARCH, params={"q": query}, timeout=5
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("data", [])
        if items:
            return items[0].get("preview") or None
    except (httpx.HTTPError, KeyError, IndexError):
        pass
    return None
