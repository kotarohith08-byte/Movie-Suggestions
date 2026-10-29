/**
 * site.js - Client-Side Recommendation & Discovery Engine for GitHub Pages
 * Powers search, genre filtering, star rating persistence (localStorage),
 * hybrid recommendations, and movie modals.
 */

(function () {
  // Safe extraction of MOVIES array across all browsers
  const MOVIES = (typeof MOVIES_DATABASE !== "undefined" && Array.isArray(MOVIES_DATABASE))
    ? MOVIES_DATABASE
    : ((typeof window !== "undefined" && Array.isArray(window.MOVIES_DATABASE)) ? window.MOVIES_DATABASE : []);

  const MOVIE_MAP = new Map(MOVIES.map(m => [Number(m.id), m]));

  // State
  let activeGenre = "All";
  let activeAlgorithm = "hybrid";
  let activeIndustry = "Kollywood";
  let indianDisplayCount = 24;
  let userRatings = loadUserRatings();

  // Storage helpers
  function loadUserRatings() {
    try {
      return JSON.parse(localStorage.getItem("cinematch_user_ratings") || "{}");
    } catch {
      return {};
    }
  }

  function saveUserRating(movieId, rating) {
    userRatings[movieId] = rating;
    try {
      localStorage.setItem("cinematch_user_ratings", JSON.stringify(userRatings));
    } catch (e) {
      console.warn("Could not persist rating:", e);
    }
  }

  // Fallback SVG Generator
  function getPosterSrc(m) {
    if (m && m.poster && typeof m.poster === "string" && m.poster.startsWith("http")) {
      return m.poster;
    }
    const safeTitle = escapeHtml((m && m.title ? m.title : "Movie").length > 22 ? (m.title.slice(0, 20) + "...") : (m && m.title ? m.title : "Movie"));
    const safeGenre = (m && m.genres && m.genres[0]) ? escapeHtml(m.genres[0]) : "Cinema";
    const safeYear = (m && m.year) ? String(m.year) : "";
    const safeRating = (m && m.rating) ? String(m.rating) : "4.0";

    return `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 450" width="300" height="450"><rect width="300" height="450" fill="%23131b2c"/><rect width="300" height="450" fill="none" stroke="%238b5cf6" stroke-width="2"/><circle cx="150" cy="180" r="50" fill="%238b5cf6" opacity="0.3"/><text x="150" y="60" text-anchor="middle" font-family="sans-serif" font-size="12" font-weight="700" fill="%23a78bfa" letter-spacing="2">${safeGenre.toUpperCase()}</text><text x="150" y="240" text-anchor="middle" font-family="sans-serif" font-size="18" font-weight="800" fill="%23ffffff">${safeTitle}</text><text x="150" y="280" text-anchor="middle" font-family="sans-serif" font-size="14" font-weight="600" fill="%2394a3b8">${safeYear}</text><text x="150" y="380" text-anchor="middle" font-family="sans-serif" font-size="15" font-weight="700" fill="%23fbbf24">${safeRating} ★</text></svg>`;
  }

  // Initialize on load
  function init() {
    initGenres();
    initSearch();
    initAlgoTabs();
    initIndianTabs();
    initModals();
    renderAllSections();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  function renderAllSections() {
    renderPersonalized();
    renderIndianSpotlight();
    renderPopular();
    renderUserRatings();
  }

  // --- 1. Genres ---
  function initGenres() {
    const genreCounts = {};
    MOVIES.forEach(m => {
      (m.genres || []).forEach(g => {
        if (g && g !== "(no genres listed)") {
          genreCounts[g] = (genreCounts[g] || 0) + 1;
        }
      });
    });

    const sortedGenres = Object.entries(genreCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 16);

    const wrapper = document.getElementById("genreChipsWrapper");
    if (!wrapper) return;

    wrapper.innerHTML = `
      <button type="button" class="genre-chip active" data-genre="All">All Genres</button>
      ${sortedGenres.map(([g, c]) => `
        <button type="button" class="genre-chip" data-genre="${escapeHtml(g)}">
          ${escapeHtml(g)} <span class="chip-count">${c}</span>
        </button>
      `).join("")}
    `;

    wrapper.addEventListener("click", (e) => {
      const chip = e.target.closest(".genre-chip");
      if (!chip) return;
      wrapper.querySelectorAll(".genre-chip").forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      activeGenre = chip.dataset.genre || "All";

      const status = document.getElementById("genreFilterStatus");
      if (status) status.textContent = activeGenre === "All" ? "Showing All" : `Filtered: ${activeGenre}`;

      renderPersonalized();
      renderIndianSpotlight();
      renderPopular();
    });
  }

  // --- 2. Search ---
  function initSearch() {
    const heroInput = document.getElementById("heroSearchInput");
    const navInput = document.getElementById("navSearchInput");
    const searchBtn = document.getElementById("heroSearchBtn");
    const clearBtn = document.getElementById("clearSearchBtn");

    function doSearch(query) {
      const q = (query || "").trim().toLowerCase();
      const resultsSection = document.getElementById("searchResultsSection");
      const grid = document.getElementById("searchResultsGrid");
      const countEl = document.getElementById("searchResultsCount");

      if (!q) {
        if (resultsSection) resultsSection.classList.add("hidden");
        return;
      }

      const matches = MOVIES.filter(m => {
        const title = (m.title || "").toLowerCase();
        const fullTitle = (m.full_title || m.title || "").toLowerCase();
        const genres = (m.genres || []).map(g => g.toLowerCase());
        const year = m.year ? String(m.year) : "";
        return title.includes(q) || fullTitle.includes(q) || genres.some(g => g.includes(q)) || year === q;
      });

      if (resultsSection) resultsSection.classList.remove("hidden");
      if (countEl) countEl.textContent = `Found ${matches.length} matching movies for "${query}"`;
      if (grid) renderMovieCards(grid, matches.slice(0, 36));

      resultsSection.scrollIntoView({ behavior: "smooth" });
    }

    if (heroInput) {
      heroInput.addEventListener("input", (e) => doSearch(e.target.value));
      heroInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") doSearch(heroInput.value);
      });
    }

    if (navInput) {
      navInput.addEventListener("input", (e) => {
        if (heroInput) heroInput.value = e.target.value;
        doSearch(e.target.value);
      });
      navInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") doSearch(navInput.value);
      });
    }

    if (searchBtn && heroInput) {
      searchBtn.addEventListener("click", () => doSearch(heroInput.value));
    }

    if (clearBtn) {
      clearBtn.addEventListener("click", () => {
        if (heroInput) heroInput.value = "";
        if (navInput) navInput.value = "";
        const resultsSection = document.getElementById("searchResultsSection");
        if (resultsSection) resultsSection.classList.add("hidden");
      });
    }
  }

  // --- 3. Algorithm Tabs ---
  function initAlgoTabs() {
    const tabs = document.querySelectorAll(".algorithm-tabs .tab-btn");
    tabs.forEach(tab => {
      tab.addEventListener("click", () => {
        tabs.forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        activeAlgorithm = tab.dataset.algo;
        renderPersonalized();
      });
    });
  }

  function initIndianTabs() {
    const tabs = document.querySelectorAll("#indianTabs .tab-btn");
    const loadMoreBtn = document.getElementById("loadMoreIndianBtn");

    tabs.forEach(tab => {
      tab.addEventListener("click", () => {
        tabs.forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        activeIndustry = tab.dataset.industry || "all";
        indianDisplayCount = 24;
        renderIndianSpotlight();
      });
    });

    if (loadMoreBtn) {
      loadMoreBtn.addEventListener("click", () => {
        indianDisplayCount += 24;
        renderIndianSpotlight();
      });
    }
  }

  // --- 4. Recommendations Engine ---
  function getRecommendations(algorithm = "hybrid", limit = 8) {
    const ratedIds = new Set(Object.keys(userRatings).map(Number));
    let candidates = MOVIES.filter(m => !ratedIds.has(m.id));

    if (activeGenre !== "All") {
      const filtered = candidates.filter(m => (m.genres || []).includes(activeGenre));
      if (filtered.length > 0) {
        candidates = filtered;
      }
    }

    const ratedList = Object.entries(userRatings).map(([id, r]) => ({
      movie: MOVIE_MAP.get(Number(id)),
      rating: Number(r)
    })).filter(x => x.movie);

    if (algorithm === "popular") {
      return candidates.slice().sort((a, b) => (b.votes * Math.pow(b.score, 1.5)) - (a.votes * Math.pow(a.score, 1.5))).slice(0, limit);
    }

    if (algorithm === "content" && ratedList.length > 0) {
      const highest = ratedList.slice().sort((a, b) => b.rating - a.rating)[0];
      const simIds = new Set(highest.movie.sims || []);
      const similarCandidates = candidates.filter(m => simIds.has(m.id));
      if (similarCandidates.length >= 4) {
        return similarCandidates.slice(0, limit);
      }
    }

    if (algorithm === "collab" || algorithm === "hybrid") {
      if (ratedList.length > 0) {
        const poolScores = new Map();
        ratedList.forEach(({ movie, rating }) => {
          const weight = (rating - 2.5) / 2.5;
          (movie.sims || []).forEach(simId => {
            if (!ratedIds.has(simId)) {
              poolScores.set(simId, (poolScores.get(simId) || 0) + (1.0 * weight));
            }
          });
        });

        const scored = candidates.map(m => {
          const simBonus = poolScores.get(m.id) || 0;
          const quality = (m.score - 1.0) / 4.0;
          return {
            ...m,
            _calcScore: (0.55 * simBonus) + (0.45 * quality)
          };
        });

        scored.sort((a, b) => (b._calcScore || 0) - (a._calcScore || 0));
        return scored.slice(0, limit);
      }
    }

    // Default: Top Bayesian weighted score
    return candidates.slice().sort((a, b) => b.score - a.score).slice(0, limit);
  }

  function renderPersonalized() {
    const grid = document.getElementById("personalizedGrid");
    if (!grid) return;
    const recs = getRecommendations(activeAlgorithm, 8);
    renderMovieCards(grid, recs);
  }

  function renderIndianSpotlight() {
    const grid = document.getElementById("indianGrid");
    const loadMoreBtn = document.getElementById("loadMoreIndianBtn");
    if (!grid) return;

    let pool = MOVIES.filter(m => {
      if (m.id < 200000) return false;
      if (activeIndustry === "Kollywood") {
        return m.industry === "Kollywood" || m.id >= 201001;
      }
      if (activeIndustry === "Tollywood") {
        return m.industry === "Tollywood" || (200001 <= m.id && m.id <= 200030) || (200061 <= m.id && m.id <= 200275);
      }
      if (activeIndustry === "Bollywood") {
        return m.industry === "Bollywood" || (200031 <= m.id && m.id <= 200060) || (200301 <= m.id && m.id <= 200615);
      }
      return true;
    }).slice().sort((a, b) => b.score - a.score);

    if (activeGenre !== "All") {
      const filtered = pool.filter(m => (m.genres || []).includes(activeGenre));
      if (filtered.length > 0) {
        pool = filtered;
      }
    }

    renderMovieCards(grid, pool.slice(0, indianDisplayCount));

    if (loadMoreBtn) {
      if (indianDisplayCount >= pool.length) {
        loadMoreBtn.style.display = "none";
      } else {
        loadMoreBtn.style.display = "inline-block";
        const indName = activeIndustry === "all" ? "Indian" : activeIndustry;
        loadMoreBtn.textContent = `⬇ Load More ${indName} Movies (${pool.length - indianDisplayCount} remaining)`;
      }
    }
  }

  function renderPopular() {
    const grid = document.getElementById("popularGrid");
    if (!grid) return;
    let popular = MOVIES.slice().sort((a, b) => (b.votes * Math.pow(b.score, 1.5)) - (a.votes * Math.pow(a.score, 1.5)));
    if (activeGenre !== "All") {
      const filtered = popular.filter(m => (m.genres || []).includes(activeGenre));
      if (filtered.length > 0) {
        popular = filtered;
      }
    }
    renderMovieCards(grid, popular.slice(0, 12));
  }

  function renderUserRatings() {
    const grid = document.getElementById("userRatingsGrid");
    const emptyState = document.getElementById("userRatingsEmpty");
    if (!grid) return;

    const ratedList = Object.entries(userRatings).map(([id, r]) => ({
      movie: MOVIE_MAP.get(Number(id)),
      rating: Number(r)
    })).filter(x => x.movie);

    if (ratedList.length === 0) {
      if (emptyState) emptyState.classList.remove("hidden");
      grid.innerHTML = "";
    } else {
      if (emptyState) emptyState.classList.add("hidden");
      grid.innerHTML = ratedList.map(({ movie, rating }) => `
        <div class="movie-card" data-movie-id="${movie.id}">
          <div class="card-media">
            <img src="${getPosterSrc(movie)}" alt="${escapeHtml(movie.title)}" loading="lazy" class="movie-poster">
            <div class="user-rated-badge">Rated: ${rating}★</div>
            <button class="btn-quick-rate" data-movie-id="${movie.id}" data-title="${escapeHtml(movie.title)}">★ Edit</button>
          </div>
          <div class="card-body">
            <div class="card-meta">
              <span class="movie-year">${movie.year || "N/A"}</span>
              <span class="movie-rating-badge">Your: ${rating}★</span>
            </div>
            <h3 class="movie-title">${escapeHtml(movie.title)}</h3>
            <div class="card-actions">
              <button class="btn-card-details" data-detail-id="${movie.id}">Details</button>
            </div>
          </div>
        </div>
      `).join("");
    }
  }

  // --- 5. Render Movie Cards ---
  function renderMovieCards(container, movies) {
    if (!movies || movies.length === 0) {
      container.innerHTML = `<div class="empty-state" style="grid-column: 1 / -1;"><p>No movies found matching criteria.</p></div>`;
      return;
    }

    container.innerHTML = movies.map(m => {
      const userR = userRatings[m.id];
      const matchScore = m._calcScore ? Math.min(99, Math.round(m._calcScore * 100)) : Math.round((m.score / 5.0) * 100);

      return `
        <div class="movie-card" data-movie-id="${m.id}">
          <div class="card-media">
            <img src="${getPosterSrc(m)}" alt="${escapeHtml(m.title)}" loading="lazy" class="movie-poster" onerror="this.onerror=null;this.src='${getPosterSrc({ ...m, poster: '' })}'">
            <div class="match-badge"><span class="match-val">${matchScore}%</span> Match</div>
            ${userR ? `<div class="user-rated-badge">Rated ${userR}★</div>` : ""}
            <button class="btn-quick-rate" data-movie-id="${m.id}" data-title="${escapeHtml(m.title)}">★ Rate</button>
          </div>

          <div class="card-body">
            <div class="card-meta">
              <span class="movie-year">${m.year || "N/A"}</span>
              <span class="movie-rating-badge">★ ${m.rating} <span class="vote-count">(${m.votes})</span></span>
            </div>

            <h3 class="movie-title" title="${escapeHtml(m.title)}">
              <a href="javascript:void(0)" class="open-detail-link" data-detail-id="${m.id}">${escapeHtml(m.title)}</a>
            </h3>

            <div class="movie-genres">
              ${(m.genres || []).slice(0, 3).map(g => `<span class="genre-pill">${escapeHtml(g)}</span>`).join("")}
            </div>

            <div class="card-actions">
              <button class="btn-card-details" data-detail-id="${m.id}">Details</button>
              <button class="btn-card-similar" data-similar-id="${m.id}">Similar</button>
            </div>
          </div>
        </div>
      `;
    }).join("");
  }

  // --- 6. Modals (Details, Rating, Metrics) ---
  function initModals() {
    // Rating Modal
    const ratingModal = document.getElementById("ratingModal");
    const closeRatingBtn = document.getElementById("closeRatingModalBtn");
    const modalStars = document.querySelectorAll("#modalStars .star-btn");
    const ratingText = document.getElementById("modalRatingText");
    const modalMovieId = document.getElementById("modalMovieId");

    document.addEventListener("click", (e) => {
      const rateBtn = e.target.closest(".btn-quick-rate");
      if (rateBtn) {
        const mid = Number(rateBtn.dataset.movieId);
        const title = rateBtn.dataset.title;
        modalMovieId.value = mid;
        document.getElementById("ratingModalTitle").textContent = `Rate "${title}"`;
        ratingText.textContent = "Click a star to submit rating";
        modalStars.forEach(s => s.classList.remove("active"));
        ratingModal.classList.add("active");
      }
    });

    if (closeRatingBtn) closeRatingBtn.onclick = () => ratingModal.classList.remove("active");

    modalStars.forEach(btn => {
      btn.onclick = () => {
        const val = Number(btn.dataset.val);
        const mid = Number(modalMovieId.value);
        saveUserRating(mid, val);

        modalStars.forEach(s => s.classList.toggle("active", Number(s.dataset.val) <= val));
        ratingText.textContent = `Saved ${val}.0★ rating!`;
        showToast(`Saved ${val}.0★ rating! Model recommendations updated.`);

        setTimeout(() => {
          ratingModal.classList.remove("active");
          renderAllSections();
        }, 350);
      };
    });

    // Detail Modal
    const detailModal = document.getElementById("detailModal");
    const closeDetailBtn = document.getElementById("closeDetailModalBtn");
    const detailBody = document.getElementById("modalDetailBody");

    document.addEventListener("click", (e) => {
      const detailBtn = e.target.closest("[data-detail-id]") || e.target.closest("[data-similar-id]");
      if (detailBtn) {
        const mid = Number(detailBtn.dataset.detailId || detailBtn.dataset.similarId);
        const movie = MOVIE_MAP.get(mid);
        if (!movie) return;

        document.getElementById("modalMovieTitle").textContent = `${movie.title} (${movie.year || "N/A"})`;

        // Find similar movies
        const similarMovies = (movie.sims || []).map(id => MOVIE_MAP.get(id)).filter(Boolean);

        detailBody.innerHTML = `
          <div class="movie-detail-card" style="box-shadow: none; border: none; padding: 0;">
            <div class="detail-poster-wrap">
              <img src="${getPosterSrc(movie)}" alt="${escapeHtml(movie.title)}" class="detail-poster">
            </div>
            <div class="detail-info-wrap">
              <div class="detail-genres">
                ${(movie.genres || []).map(g => `<span class="genre-pill large-pill">${escapeHtml(g)}</span>`).join("")}
              </div>
              <div class="detail-stats-grid">
                <div class="stat-card">
                  <span class="stat-num text-yellow">★ ${movie.rating}</span>
                  <span class="stat-lbl">Rating</span>
                </div>
                <div class="stat-card">
                  <span class="stat-num text-cyan">${movie.votes}</span>
                  <span class="stat-lbl">Ratings Logged</span>
                </div>
                <div class="stat-card">
                  <span class="stat-num text-purple">${movie.score}</span>
                  <span class="stat-lbl">Weighted Quality</span>
                </div>
              </div>
              <div class="detail-rating-box">
                <h3>Rate this Movie:</h3>
                <div class="interactive-star-rater" style="margin-top: 8px;">
                  ${[1, 2, 3, 4, 5].map(v => `
                    <button class="star-rating-star ${userRatings[movie.id] >= v ? 'active' : ''}" data-val="${v}">★</button>
                  `).join("")}
                  <span class="rating-feedback-msg">${userRatings[movie.id] ? `Rated ${userRatings[movie.id]}★` : "Not yet rated"}</span>
                </div>
              </div>
            </div>
          </div>
          ${similarMovies.length > 0 ? `
            <div style="margin-top: 30px;">
              <h3 style="font-size: 1.15rem; margin-bottom: 16px;">Similar Titles Like "${escapeHtml(movie.title)}"</h3>
              <div class="movie-grid">${renderCardsHtml(similarMovies.slice(0, 4))}</div>
            </div>
          ` : ""}
        `;

        // Attach rater inside detail
        detailBody.querySelectorAll(".star-rating-star").forEach(s => {
          s.onclick = () => {
            const val = Number(s.dataset.val);
            saveUserRating(movie.id, val);
            detailBody.querySelectorAll(".star-rating-star").forEach(st => st.classList.toggle("active", Number(st.dataset.val) <= val));
            detailBody.querySelector(".rating-feedback-msg").textContent = `Rated ${val}★`;
            showToast(`Updated rating to ${val}★!`);
            renderAllSections();
          };
        });

        detailModal.classList.add("active");
      }
    });

    if (closeDetailBtn) closeDetailBtn.onclick = () => detailModal.classList.remove("active");

    // Metrics Modal & Chart.js
    const metricsModal = document.getElementById("metricsModal");
    const openMetricsBtn = document.getElementById("openMetricsBtn");
    const closeMetricsBtn = document.getElementById("closeMetricsBtn");
    let chartRendered = false;

    if (openMetricsBtn) {
      openMetricsBtn.onclick = () => {
        metricsModal.classList.add("active");
        if (!chartRendered && typeof Chart !== "undefined") {
          const canvas = document.getElementById("metricsChart");
          if (canvas) {
            new Chart(canvas.getContext("2d"), {
              type: "bar",
              data: {
                labels: ["RMSE (0.9255)", "MAE (0.7177)", "Precision@10 (69.0%)", "NDCG@10 (0.8721)"],
                datasets: [{
                  data: [0.9255, 0.7177, 0.6900, 0.8721],
                  backgroundColor: ["#f43f5e", "#06b6d4", "#10b981", "#8b5cf6"],
                  borderRadius: 6
                }]
              },
              options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                  y: { beginAtZero: true, max: 1.1, grid: { color: "rgba(255,255,255,0.08)" } },
                  x: { grid: { display: false } }
                }
              }
            });
            chartRendered = true;
          }
        }
      };
    }

    if (closeMetricsBtn) closeMetricsBtn.onclick = () => metricsModal.classList.remove("active");

    // Close on overlay backdrop click
    [ratingModal, detailModal, metricsModal].forEach(m => {
      if (m) m.addEventListener("click", (e) => {
        if (e.target === m) m.classList.remove("active");
      });
    });
  }

  function renderCardsHtml(movies) {
    return movies.map(m => `
      <div class="movie-card" data-movie-id="${m.id}">
        <div class="card-media">
          <img src="${getPosterSrc(m)}" alt="${escapeHtml(m.title)}" loading="lazy" class="movie-poster">
        </div>
        <div class="card-body">
          <span class="movie-year">${m.year || "N/A"}</span>
          <h4 class="movie-title" style="font-size: 0.9rem;">${escapeHtml(m.title)}</h4>
          <span class="movie-rating-badge">★ ${m.rating}</span>
        </div>
      </div>
    `).join("");
  }

  function showToast(msg) {
    const cont = document.getElementById("toastContainer");
    if (!cont) return;
    const t = document.createElement("div");
    t.className = "toast success";
    t.innerHTML = `<span>✓</span> <span>${msg}</span>`;
    cont.appendChild(t);
    setTimeout(() => {
      t.style.opacity = "0";
      setTimeout(() => t.remove(), 300);
    }, 3000);
  }

  function escapeHtml(str) {
    return String(str || "").replace(/[&<>"']/g, s => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[s]);
  }

})();
