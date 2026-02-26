(() => {
  const form = document.getElementById("search-form");
  const urlInput = document.getElementById("track-url");
  const searchBtn = document.getElementById("search-btn");
  const seedEl = document.getElementById("seed-track");
  const resultsEl = document.getElementById("results");
  const errorEl = document.getElementById("error");
  const loadingEl = document.getElementById("loading");

  let currentAudio = null;

  // Keep slider value labels in sync
  document.querySelectorAll('input[type="range"]').forEach((slider) => {
    const label = document.querySelector(
      `.slider-val[data-for="${slider.id}"]`
    );
    if (label) {
      slider.addEventListener("input", () => {
        label.textContent = parseFloat(slider.value).toFixed(2);
      });
    }
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    await search();
  });

  async function search() {
    const url = urlInput.value.trim();
    if (!url) return;

    // Gather weights
    const weights = {
      bpm: parseFloat(document.getElementById("w-bpm").value),
      vocals: parseFloat(document.getElementById("w-vocals").value),
      instrumentals: parseFloat(document.getElementById("w-instrumentals").value),
      style: parseFloat(document.getElementById("w-style").value),
      mood: parseFloat(document.getElementById("w-mood").value),
    };
    const limit = parseInt(document.getElementById("limit").value, 10);

    // UI state
    stopAudio();
    seedEl.classList.add("hidden");
    resultsEl.innerHTML = "";
    errorEl.classList.add("hidden");
    loadingEl.classList.remove("hidden");
    searchBtn.disabled = true;

    try {
      const resp = await fetch("/api/similar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, weights, limit }),
      });

      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(data.detail || `Request failed (${resp.status})`);
      }

      const data = await resp.json();
      renderSeed(data.seed_track);
      renderResults(data.similar_tracks);
    } catch (err) {
      errorEl.textContent = err.message;
      errorEl.classList.remove("hidden");
    } finally {
      loadingEl.classList.add("hidden");
      searchBtn.disabled = false;
    }
  }

  function featureBadges(af) {
    if (!af) return "";
    return `
      <span class="feat-badge">${Math.round(af.bpm)} BPM</span>
      <span class="feat-badge">Energy ${(af.energy * 100).toFixed(0)}%</span>
      <span class="feat-badge">Dance ${(af.danceability * 100).toFixed(0)}%</span>
      <span class="feat-badge">Mood ${(af.valence * 100).toFixed(0)}%</span>
      <span class="feat-badge">Instr ${(af.instrumentalness * 100).toFixed(0)}%</span>
    `;
  }

  function renderSeed(track) {
    seedEl.innerHTML = `
      ${track.album_art ? `<img src="${track.album_art}" alt="Album art" />` : ""}
      <div class="seed-meta">
        <h2><a href="${track.spotify_url}" target="_blank" rel="noopener">${esc(track.name)}</a></h2>
        <div class="artists">${esc(track.artists.join(", "))} &mdash; ${esc(track.album)}</div>
        <div class="seed-features">${featureBadges(track.audio_features)}</div>
      </div>
    `;
    seedEl.classList.remove("hidden");
  }

  function renderResults(tracks) {
    if (!tracks.length) {
      resultsEl.innerHTML = "<p>No similar tracks found.</p>";
      return;
    }
    let html = `<h3>Similar Tracks (${tracks.length})</h3>`;
    tracks.forEach((t) => {
      const previewBtn = t.preview_url
        ? `<button class="play-btn" data-url="${t.preview_url}" title="Preview">&#9654;</button>`
        : "";
      html += `
        <div class="track-card">
          ${t.album_art ? `<img src="${t.album_art}" alt="" />` : ""}
          <div class="track-info">
            <div class="name"><a href="${t.spotify_url}" target="_blank" rel="noopener">${esc(t.name)}</a></div>
            <div class="detail">${esc(t.artists.join(", "))} &mdash; ${esc(t.album)}</div>
          </div>
          <div class="track-features">${featureBadges(t.audio_features)}</div>
          ${previewBtn}
        </div>
      `;
    });
    resultsEl.innerHTML = html;

    // Attach preview listeners
    resultsEl.querySelectorAll(".play-btn").forEach((btn) => {
      btn.addEventListener("click", () => togglePreview(btn));
    });
  }

  function togglePreview(btn) {
    const url = btn.dataset.url;
    if (currentAudio && currentAudio.src === url) {
      stopAudio();
      return;
    }
    stopAudio();
    currentAudio = new Audio(url);
    currentAudio.volume = 0.5;
    currentAudio.play();
    btn.innerHTML = "&#9724;";
    currentAudio.addEventListener("ended", () => {
      btn.innerHTML = "&#9654;";
      currentAudio = null;
    });
  }

  function stopAudio() {
    if (currentAudio) {
      currentAudio.pause();
      currentAudio = null;
      document.querySelectorAll(".play-btn").forEach((b) => {
        b.innerHTML = "&#9654;";
      });
    }
  }

  function esc(str) {
    const d = document.createElement("div");
    d.textContent = str;
    return d.innerHTML;
  }
})();
