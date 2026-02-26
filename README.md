# Similar Tracks Finder

A web app that finds songs similar to a given Spotify track. Tune configurable similarity weights to focus the search on specific audio traits like BPM, vocals, instrumentals, style, and mood.

## Features

- **Spotify URL input** – paste any Spotify track link
- **Similarity weights** – adjust sliders to control what matters most:
  | Weight | Spotify feature(s) used |
  |---|---|
  | BPM / Tempo | `tempo` |
  | Vocals | `speechiness` |
  | Instrumentals | `instrumentalness` |
  | Style | `danceability` + `energy` |
  | Mood | `valence` |
- **Audio feature badges** on every result (BPM, energy, danceability, mood, instrumentalness)
- **30-second preview playback** (when Spotify provides a preview URL)
- Configurable result count (5 / 10 / 20 / 50)

## Prerequisites

- Python 3.10+
- [Poetry](https://python-poetry.org/docs/#installation)
- A **Spotify Developer** application (free) — create one at https://developer.spotify.com/dashboard

## Setup

```bash
# Clone the repo
cd /Users/feline/Desktop/Repositories
git clone https://github.com/FelineWeise/similar-tracks.git
cd similar-tracks

# Install dependencies
poetry install

# Configure credentials
cp .env.example .env
# Edit .env and add your Spotify Client ID and Secret
```

## Running

```bash
poetry run python run.py
```

Open http://localhost:8000 in your browser.

## API

### `POST /api/similar`

**Request body:**

```json
{
  "url": "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT",
  "weights": {
    "bpm": 0.8,
    "vocals": 0.3,
    "instrumentals": 0.5,
    "style": 0.7,
    "mood": 0.6
  },
  "limit": 10
}
```

**Response:** JSON with `seed_track` and `similar_tracks`, each containing name, artists, album, album art, Spotify URL, and audio features.

## Tech Stack

- **Backend:** Python, FastAPI, Spotipy
- **Frontend:** Vanilla HTML / CSS / JS
- **API:** Spotify Web API (Recommendations + Audio Features)

## License

MIT
