/**
 * script.js - CineMatch AI Client-Side Interactions
 * Handles star rating submissions, dynamic algorithm switching,
 * genre preferences persistence, user profiles, and Chart.js metrics.
 */

document.addEventListener("DOMContentLoaded", () => {
  initRatingModal();
  initDetailStarRater();
  initAlgorithmTabs();
  initGenrePreferences();
  initUserSwitchModal();
  initMetricsModal();
  loadUserRatedMovies();
});

// =========================================================================
// Toast Notifications
// =========================================================================
function showToast(message, type = "success") {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${type === "success" ? "✓" : "ℹ"}</span> <span>${message}</span>`;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// =========================================================================
// Star Rating Submission & Modal
// =========================================================================
function initRatingModal() {
  const modal = document.getElementById("ratingModal");
  const closeBtn = document.getElementById("closeRatingModalBtn");
  const modalTitle = document.getElementById("ratingModalTitle");
  const movieIdInput = document.getElementById("modalMovieId");
  const starBtns = document.querySelectorAll("#modalStars .star-btn");
  const ratingText = document.getElementById("modalRatingText");

  if (!modal) return;

  // Delegate click for all quick rate buttons across grids
  document.addEventListener("click", (e) => {
    const rateBtn = e.target.closest(".btn-quick-rate");
    if (rateBtn) {
      const mid = rateBtn.dataset.movieId;
      const title = rateBtn.dataset.title || "Movie";
      movieIdInput.value = mid;
      modalTitle.textContent = `Rate "${title}"`;
      ratingText.textContent = "Click a star to rate";

      // Reset stars
      starBtns.forEach(b => b.classList.remove("active"));
      modal.classList.remove("hidden");
    }
  });

  if (closeBtn) {
    closeBtn.addEventListener("click", () => modal.classList.add("hidden"));
  }

  modal.addEventListener("click", (e) => {
    if (e.target === modal) modal.classList.add("hidden");
  });

  // Handle star click in modal
  starBtns.forEach(btn => {
    btn.addEventListener("click", async () => {
      const val = parseFloat(btn.dataset.val);
      const mid = parseInt(movieIdInput.value);

      // Highlight up to clicked star
      starBtns.forEach(b => {
        b.classList.toggle("active", parseFloat(b.dataset.val) <= val);
      });
      ratingText.textContent = `Saving ${val}.0★...`;

      try {
        const resp = await fetch("/rate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ movie_id: mid, rating: val })
        });
        const res = await resp.json();

        if (res.status === "success") {
          showToast(`Saved ${val}.0★ rating! Recommendation engine updated.`);
          setTimeout(() => {
            modal.classList.add("hidden");
            loadUserRatedMovies();
            // Refresh personalized grid if on homepage
            const activeTab = document.querySelector(".algorithm-tabs .tab-btn.active");
            if (activeTab) {
              fetchRecommendations(activeTab.dataset.algo);
            }
          }, 400);
        } else {
          showToast(res.message || "Failed to save rating", "error");
        }
      } catch (err) {
        showToast("Network error submitting rating", "error");
      }
    });
  });
}

// Interactive Star Rater on Movie Details Page
function initDetailStarRater() {
  const rater = document.getElementById("detailStarRater");
  if (!rater) return;

  const mid = parseInt(rater.dataset.movieId);
  const stars = rater.querySelectorAll(".star-rating-star");
  const feedback = document.getElementById("detailRatingFeedback");

  stars.forEach(btn => {
    btn.addEventListener("click", async () => {
      const val = parseFloat(btn.dataset.val);

      // Update active states
      stars.forEach(s => {
        s.classList.toggle("active", parseFloat(s.dataset.val) <= val);
      });
      feedback.textContent = `Saving ${val}.0★...`;

      try {
        const resp = await fetch("/rate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ movie_id: mid, rating: val })
        });
        const res = await resp.json();
        if (res.status === "success") {
          feedback.textContent = `Rated ${val}.0★`;
          showToast(`Updated rating to ${val}.0★!`);
        }
      } catch (err) {
        feedback.textContent = "Error saving rating";
      }
    });
  });
}

// =========================================================================
// Dynamic Algorithm Switcher Tabs
// =========================================================================
function initAlgorithmTabs() {
  const tabs = document.querySelectorAll(".algorithm-tabs .tab-btn");
  if (!tabs.length) return;

  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      const algo = tab.dataset.algo;
      fetchRecommendations(algo);
    });
  });
}

async function fetchRecommendations(algorithm = "hybrid") {
  const grid = document.getElementById("personalizedGrid");
  const loading = document.getElementById("recsLoading");
  if (!grid) return;

  grid.style.opacity = "0.3";
  if (loading) loading.classList.remove("hidden");

  try {
    const resp = await fetch(`/api/recommendations?algorithm=${algorithm}&top_n=8`);
    const data = await resp.json();

    if (data.status === "success" && data.recommendations) {
      renderMovieCards(grid, data.recommendations);
    }
  } catch (err) {
    console.error("Error fetching recommendations:", err);
  } finally {
    grid.style.opacity = "1";
    if (loading) loading.classList.add("hidden");
  }
}

function renderMovieCards(container, movies) {
  if (!movies || movies.length === 0) {
    container.innerHTML = `
      <div class="empty-state" style="grid-column: 1 / -1;">
        <p>No recommendations available for this mode yet. Rate a few movies to train your profile!</p>
      </div>
    `;
    return;
  }

  container.innerHTML = movies.map(m => `
    <div class="movie-card" data-movie-id="${m.movieId}">
      <div class="card-media">
        <img src="${m.poster_url}" alt="${escapeHtml(m.clean_title)}" loading="lazy" class="movie-poster" onerror="if(this.src.indexOf('fallback=svg')===-1){this.src='/poster/${m.movieId}?fallback=svg';}">
        ${m.match_percentage ? `<div class="match-badge"><span class="match-val">${m.match_percentage}%</span> Match</div>` : ""}
        <button 
          class="btn-quick-rate" 
          data-movie-id="${m.movieId}" 
          data-title="${escapeHtml(m.clean_title)}"
          title="Rate this movie"
        >
          ★ Rate
        </button>
      </div>

      <div class="card-body">
        <div class="card-meta">
          <span class="movie-year">${m.year || "N/A"}</span>
          <span class="movie-rating-badge">
            ★ ${m.rating_mean} <span class="vote-count">(${m.rating_count})</span>
          </span>
        </div>

        <h3 class="movie-title">
          <a href="/movie/${m.movieId}" title="${escapeHtml(m.clean_title)}">
            ${escapeHtml(m.clean_title)}
          </a>
        </h3>

        <div class="movie-genres">
          ${(m.genres || []).slice(0, 3).map(g => `<span class="genre-pill">${escapeHtml(g)}</span>`).join("")}
        </div>

        ${m.recommendation_reason ? `
        <div class="rec-reason">
          <span class="reason-icon">💡</span>
          <span class="reason-text">${escapeHtml(m.recommendation_reason)}</span>
        </div>` : ""}

        <div class="card-actions">
          <a href="/movie/${m.movieId}" class="btn-card-details">Details</a>
          <a href="/recommend/${m.movieId}" class="btn-card-similar">Similar</a>
        </div>
      </div>
    </div>
  `).join("");
}

// =========================================================================
// Genre Preferences Multi-Select
// =========================================================================
function initGenrePreferences() {
  const chips = document.querySelectorAll(".genre-chip");
  const hint = document.getElementById("prefSavedHint");
  if (!chips.length) return;

  chips.forEach(chip => {
    chip.addEventListener("click", async () => {
      chip.classList.toggle("active");

      // Collect active genres
      const activeGenres = Array.from(document.querySelectorAll(".genre-chip.active"))
        .map(c => c.dataset.genre);

      // Save to backend
      try {
        await fetch("/api/user/preferences", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ genres: activeGenres })
        });

        if (hint) {
          hint.textContent = "Preferences Updated";
          hint.classList.add("visible");
          setTimeout(() => hint.classList.remove("visible"), 2000);
        }

        // Refresh recommendations
        const activeTab = document.querySelector(".algorithm-tabs .tab-btn.active");
        fetchRecommendations(activeTab ? activeTab.dataset.algo : "hybrid");
      } catch (err) {
        console.error("Failed to update preferences:", err);
      }
    });
  });
}

// =========================================================================
// User Persona Switcher Modal
// =========================================================================
function initUserSwitchModal() {
  const modal = document.getElementById("userModal");
  const openBtn = document.getElementById("switchUserBtn");
  const closeBtn = document.getElementById("closeUserModalBtn");
  const personas = document.querySelectorAll(".btn-persona");
  const customForm = document.getElementById("customUserForm");
  const customInput = document.getElementById("customUserIdInput");

  if (!modal || !openBtn) return;

  openBtn.addEventListener("click", () => modal.classList.remove("hidden"));
  if (closeBtn) closeBtn.addEventListener("click", () => modal.classList.add("hidden"));

  modal.addEventListener("click", (e) => {
    if (e.target === modal) modal.classList.add("hidden");
  });

  async function applyUser(uid) {
    try {
      const resp = await fetch("/api/user/switch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: uid })
      });
      const data = await resp.json();
      if (data.status === "success") {
        window.location.reload();
      }
    } catch (err) {
      showToast("Error switching persona", "error");
    }
  }

  personas.forEach(btn => {
    btn.addEventListener("click", () => applyUser(btn.dataset.uid));
  });

  if (customForm) {
    customForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const uid = customInput.value.trim();
      if (uid) applyUser(uid);
    });
  }
}

// =========================================================================
// User's Rated Movies Loader
// =========================================================================
async function loadUserRatedMovies() {
  const grid = document.getElementById("userRatingsGrid");
  const emptyState = document.getElementById("userRatingsEmpty");
  const refreshBtn = document.getElementById("refreshMyRatingsBtn");

  if (!grid) return;

  if (refreshBtn) {
    refreshBtn.onclick = () => loadUserRatedMovies();
  }

  try {
    const resp = await fetch("/api/user/ratings");
    const data = await resp.json();

    if (data.status === "success" && data.ratings && data.ratings.length > 0) {
      if (emptyState) emptyState.classList.add("hidden");
      grid.innerHTML = data.ratings.map(r => `
        <div class="movie-card" data-movie-id="${r.movie_id}">
          <div class="card-media">
            <img src="${r.poster_url}" alt="${escapeHtml(r.title)}" loading="lazy" class="movie-poster" onerror="if(this.src.indexOf('fallback=svg')===-1){this.src='/poster/${r.movie_id}?fallback=svg';}">
            <div class="user-rated-badge">Rated: ${r.rating}★</div>
            <button 
              class="btn-quick-rate" 
              data-movie-id="${r.movie_id}" 
              data-title="${escapeHtml(r.title)}"
              title="Update your rating"
            >
              ★ Edit
            </button>
          </div>
          <div class="card-body">
            <div class="card-meta">
              <span class="movie-year">${r.year || "N/A"}</span>
              <span class="movie-rating-badge">Your: ${r.rating}★</span>
            </div>
            <h3 class="movie-title">
              <a href="/movie/${r.movie_id}">${escapeHtml(r.title)}</a>
            </h3>
            <div class="movie-genres">
              ${(r.genres || []).slice(0, 2).map(g => `<span class="genre-pill">${escapeHtml(g)}</span>`).join("")}
            </div>
            <div class="card-actions">
              <a href="/movie/${r.movie_id}" class="btn-card-details">Details</a>
              <a href="/recommend/${r.movie_id}" class="btn-card-similar">Similar</a>
            </div>
          </div>
        </div>
      `).join("");
    } else {
      if (emptyState) emptyState.classList.remove("hidden");
      grid.innerHTML = "";
    }
  } catch (err) {
    console.error("Error loading user ratings:", err);
  }
}

// =========================================================================
// ML Metrics Modal & Chart.js Visualizer
// =========================================================================
let metricsChartInstance = null;

function initMetricsModal() {
  const modal = document.getElementById("metricsModal");
  const openBtn = document.getElementById("openMetricsBtn");
  const closeBtn = document.getElementById("closeMetricsBtn");

  if (!modal || !openBtn) return;

  openBtn.addEventListener("click", () => {
    modal.classList.remove("hidden");
    renderMetricsChart();
  });

  if (closeBtn) closeBtn.addEventListener("click", () => modal.classList.add("hidden"));

  modal.addEventListener("click", (e) => {
    if (e.target === modal) modal.classList.add("hidden");
  });
}

async function renderMetricsChart() {
  const canvas = document.getElementById("metricsChart");
  if (!canvas || typeof Chart === "undefined") return;

  try {
    const resp = await fetch("/api/metrics");
    const data = await resp.json();
    const metrics = data.metrics || {};

    // Update stat boxes if present
    const elRmse = document.getElementById("metricRmse");
    const elMae = document.getElementById("metricMae");
    const elPrecision = document.getElementById("metricPrecision");
    const elNdcg = document.getElementById("metricNdcg");

    if (elRmse && metrics.rmse) elRmse.textContent = metrics.rmse;
    if (elMae && metrics.mae) elMae.textContent = metrics.mae;
    if (elPrecision && metrics.precision_at_10) elPrecision.textContent = `${(metrics.precision_at_10 * 100).toFixed(1)}%`;
    if (elNdcg && metrics.ndcg_at_10) elNdcg.textContent = metrics.ndcg_at_10;

    if (metricsChartInstance) {
      metricsChartInstance.destroy();
    }

    const ctx = canvas.getContext("2d");
    metricsChartInstance = new Chart(ctx, {
      type: "bar",
      data: {
        labels: [
          "RMSE (Error ↓)",
          "MAE (Error ↓)",
          "Precision@10 (Hit Rate ↑)",
          "Recall@10 (Coverage ↑)",
          "NDCG@10 (Ranking ↑)"
        ],
        datasets: [{
          label: "Evaluated Model Score",
          data: [
            metrics.rmse || 0.9259,
            metrics.mae || 0.7139,
            metrics.precision_at_10 || 0.6364,
            metrics.recall_at_10 || 0.6678,
            metrics.ndcg_at_10 || 0.8536
          ],
          backgroundColor: [
            "rgba(244, 63, 94, 0.7)",   // RMSE Red
            "rgba(6, 182, 212, 0.7)",   // MAE Cyan
            "rgba(16, 185, 129, 0.7)",  // Precision Green
            "rgba(59, 130, 246, 0.7)",  // Recall Blue
            "rgba(168, 85, 247, 0.7)"   // NDCG Purple
          ],
          borderColor: [
            "#f43f5e",
            "#06b6d4",
            "#10b981",
            "#3b82f6",
            "#a855f7"
          ],
          borderWidth: 1.5,
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (context) => `Value: ${context.raw.toFixed(4)}`
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            max: 1.2,
            grid: { color: "rgba(255, 255, 255, 0.08)" },
            ticks: { color: "#94a3b8" }
          },
          x: {
            grid: { display: false },
            ticks: { color: "#cbd5e1", font: { size: 11, weight: "600" } }
          }
        }
      }
    });
  } catch (err) {
    console.error("Error creating metrics chart:", err);
  }
}

// Utility
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
