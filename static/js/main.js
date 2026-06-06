/**
 * Slate SaaS-Style MoodMovie JavaScript Client
 * Manages theme toggling, instant mood selection cards,
 * movie card grid generators, debounced search triggers, watchlist bookmarks,
 * history journals, and YouTube trailer responsive modals.
 */

// Global State
let userWatchlistCache = new Set();
let searchDebounceTimeout = null;

// Initialize elements on DOM Content Loaded
document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initPageLoaders();
    bindTrailerModalCleanup();
});

// ==========================================
// 1. THEME MANAGEMENT
// ==========================================
function initTheme() {
    const htmlNode = document.documentElement;
    const themeToggler = document.getElementById("theme-toggler");
    const themeIcon = document.getElementById("theme-icon");
    
    // Default to dark theme for that sleek Slate experience
    let activeTheme = localStorage.getItem("theme");
    if (!activeTheme) {
        activeTheme = "dark";
    }
    
    htmlNode.setAttribute("data-theme", activeTheme);
    updateThemeIcon(activeTheme, themeIcon);

    if (themeToggler) {
        themeToggler.addEventListener("click", () => {
            let newTheme = htmlNode.getAttribute("data-theme") === "dark" ? "light" : "dark";
            htmlNode.setAttribute("data-theme", newTheme);
            localStorage.setItem("theme", newTheme);
            updateThemeIcon(newTheme, themeIcon);
        });
    }
}

function updateThemeIcon(theme, iconElement) {
    if (!iconElement) return;
    if (theme === "dark") {
        iconElement.className = "fa-solid fa-sun text-warning";
    } else {
        iconElement.className = "fa-solid fa-moon text-primary";
    }
}

// ==========================================
// 2. PAGE DETECTORS & ROUTE DISPATCHERS
// ==========================================
function initPageLoaders() {
    const isLanding = document.getElementById("trending-carousel-inner");
    const isDashboard = document.getElementById("movies-grid");
    const isWatchlist = document.getElementById("watchlist-grid");
    const isHistory = document.getElementById("history-table-body");

    const isLoggedIn = document.getElementById("nav-link-logout") !== null;

    if (isLoggedIn) {
        fetchWatchlistCache().then(() => {
            if (isDashboard) {
                loadInitialDashboardSuggestions();
            }
            if (isWatchlist) {
                loadWatchlistGallery();
            }
        });
        
        if (isHistory) {
            loadHistoryLogs();
        }
    }

    if (isLanding) {
        loadLandingTrendingCarousel();
    }
}

// ==========================================
// 3. LANDING PAGE TRENDING HORIZONTAL SLIDER
// ==========================================
async function loadLandingTrendingCarousel() {
    const sliderContainer = document.getElementById("trending-carousel-inner");
    if (!sliderContainer) return;

    try {
        const response = await fetch("/api/movies/trending");
        if (!response.ok) throw new Error();
        const movies = await response.json();
        
        if (movies.length === 0) {
            sliderContainer.innerHTML = `<p class="text-secondary text-center py-4">No trending movies found.</p>`;
            return;
        }

        let sliderHTML = "";
        movies.forEach(movie => {
            const poster = movie.poster_path 
                ? `https://image.tmdb.org/t/p/w500${movie.poster_path}` 
                : "https://images.unsplash.com/photo-1594909122845-11baa439b7bf?w=500&auto=format&fit=crop";

            const releaseYear = movie.release_date && movie.release_date !== "N/A" 
                ? movie.release_date.split("-")[0] 
                : "N/A";

            sliderHTML += `
                <div class="trending-slide-card animate-fade-in">
                    <div class="card-movie">
                        <div class="poster-container">
                            <img src="${poster}" class="poster-img" alt="${movie.title}" loading="lazy">
                            <div class="rating-badge">
                                <i class="fa-solid fa-star"></i>${movie.vote_average}
                            </div>
                        </div>
                        <div class="movie-details">
                            <h4 class="movie-title" title="${movie.title}">${movie.title}</h4>
                            <div class="movie-meta">
                                <span>${releaseYear}</span>
                            </div>
                            <p class="movie-overview">${movie.overview}</p>
                            <a href="/login" class="btn btn-sm btn-primary-custom w-100 mt-auto py-2 text-decoration-none">
                                <i class="fa-solid fa-play me-1"></i>Discover Now
                            </a>
                        </div>
                    </div>
                </div>`;
        });

        sliderContainer.innerHTML = sliderHTML;
    } catch (err) {
        console.error("Trending slider error:", err);
        sliderContainer.innerHTML = `<p class="text-danger text-center small py-4"><i class="fa-solid fa-circle-exclamation me-1"></i>Failed to fetch trending movies.</p>`;
    }
}

// ==========================================
// 4. DASHBOARD DYNAMICS & DIRECT MOOD SELECTIONS
// ==========================================
async function loadInitialDashboardSuggestions() {
    renderNetflixLoader("movies-grid", "Queueing up hot releases...");
    try {
        const response = await fetch("/api/movies/trending");
        if (!response.ok) throw new Error();
        const movies = await response.json();
        renderMovieGrid("movies-grid", movies);
    } catch {
        document.getElementById("movies-grid").innerHTML = `
            <div class="col-12 text-center py-5">
                <p class="text-danger small"><i class="fa-solid fa-triangle-exclamation me-2"></i>Failed to load suggestions.</p>
            </div>`;
    }
}

/**
 * Sets values inside text area for NLP analysis
 */
function setQuickMood(promptText) {
    const input = document.getElementById("mood-input");
    if (input) {
        input.value = promptText;
        input.focus();
    }
}

/**
 * Triggers recommendations instantly when a user clicks a mood card
 */
async function selectMoodCard(moodElement, emotionKey, labelText) {
    // 1. Manage Active Class states
    document.querySelectorAll(".mood-select-card").forEach(card => {
        card.classList.remove("active");
    });
    moodElement.classList.add("active");

    // 2. Set Input Field text for transparency
    const inputField = document.getElementById("mood-input");
    if (inputField) {
        inputField.value = `Feeling ${labelText.toLowerCase()}!`;
    }

    const gridTitle = document.getElementById("recommendation-grid-title");
    const emotionPanel = document.getElementById("emotion-panel");

    // 3. Clear Search bar
    const searchBar = document.getElementById("movie-search-bar");
    if (searchBar) searchBar.value = "";

    // 4. Show Loading Spinner
    renderNetflixLoader("movies-grid", `Gathering ${labelText.toLowerCase()} movies...`);
    gridTitle.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin text-info me-2"></i>Matching content to ${labelText.toLowerCase()}...`;

    try {
        // Log this choice in history database by calling discover endpoint with prompt
        const promptText = `Clicked mood card: ${labelText}`;
        const language = document.getElementById('language-selector')?.value || '';
        const langParam = language ? `&lang=${encodeURIComponent(language)}` : '';
        const languageNames = { kn: 'Kannada', te: 'Telugu', ta: 'Tamil', ml: 'Malayalam', all: 'All South Indian' };
        const languageLabel = language && languageNames[language] ? languageNames[language] : '';
        const movieUrl = `/api/movies/mood/${emotionKey}?mood_prompt=${encodeURIComponent(promptText)}${langParam}&selected_title=${labelText}`;
        // Prepare grid title with language if selected

        if (languageLabel) {
            gridTitle.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles text-info me-2"></i>Recommended for feeling ${labelText} (${languageLabel})`;
        } else {
            gridTitle.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles text-info me-2"></i>Recommended for feeling ${labelText}`;
        }
        
        const response = await fetch(movieUrl);
        if (!response.ok) throw new Error();
        const movies = await response.json();

        // 5. Update emotion details card dynamically
        const emojiMap = {
            happy: "😊", sad: "😢", excited: "🔥", romantic: "❤️", fear: "👻", motivated: "💪"
        };
        const explanations = {
            happy: "Positive vibes detected! Comedy and animation recommendations matched for your smile.",
            sad: "Cozy up and reflect. Touching and deep cinematic dramas to match your quiet mood.",
            excited: "High-octane blockbusters, action releases, and thrilling adventure queues.",
            romantic: "Affectionate feelings. Romance and chemistry-filled cinematic narratives.",
            fear: "Chilling horros and suspense-filled mystery suggestions.",
            motivated: "Prepare to achieve your goals! Triumphant biographies and inspiring real struggles."
        };

        document.getElementById("emotion-emoji").textContent = emojiMap[emotionKey] || "🎭";
        document.getElementById("emotion-name").textContent = labelText;
        document.getElementById("emotion-confidence-badge").textContent = "Instant Match: 99%";
        document.getElementById("emotion-explanation").textContent = explanations[emotionKey] || "Perfect selection for your mood!";
        
        // Populate dummy sentiment numbers
        document.getElementById("metric-polarity").textContent = "1.0";
        document.getElementById("metric-subjectivity").textContent = "1.0";
        
        emotionPanel.classList.remove("d-none");

        // Render movie grid
        gridTitle.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles text-info me-2"></i>Recommended for feeling ${labelText}`;
        renderMovieGrid("movies-grid", movies);

    } catch (err) {
        console.error("Mood Card selection error:", err);
        document.getElementById("movies-grid").innerHTML = `<p class="text-danger text-center">Failed to fetch recommendations.</p>`;
    }
}

/**
 * Handles TextBlob NLP Form Submission
 */
async function handleMoodSubmit(event) {
    event.preventDefault();
    const inputField = document.getElementById("mood-input");
    const submitBtn = document.getElementById("detect-mood-btn");
    const emotionPanel = document.getElementById("emotion-panel");
    const gridTitle = document.getElementById("recommendation-grid-title");

    const promptText = inputField.value.trim();
    if (!promptText) return;

    // Clear active mood cards
    document.querySelectorAll(".mood-select-card").forEach(card => card.classList.remove("active"));

    // Activate UI Loading Indicators
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin me-2"></i>Analyzing Vibe...`;
    renderNetflixLoader("movies-grid", "Running TextBlob NLP analysis...");
    gridTitle.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin text-info me-2"></i>Mapping sentiment to genres...`;

    try {
        // Step 1: Detect Emotion via TextBlob Polarity subjectivity
        const moodResponse = await fetch("/api/detect-mood", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ mood_text: promptText })
        });
        
        if (!moodResponse.ok) throw new Error();
        const analysis = await moodResponse.json();

        // Step 2: Render emotional metadata panel
        document.getElementById("emotion-emoji").textContent = analysis.emoji;
        
        let displayEmotion = analysis.emotion.charAt(0).toUpperCase() + analysis.emotion.slice(1);
        if (analysis.emotion === "excited") displayEmotion = "Action";
        if (analysis.emotion === "fear") displayEmotion = "Horror";
        if (analysis.emotion === "motivated") displayEmotion = "Motivational";

        document.getElementById("emotion-name").textContent = displayEmotion;
        document.getElementById("emotion-confidence-badge").textContent = `Confidence: ${Math.round(analysis.confidence * 100)}%`;
        document.getElementById("emotion-explanation").textContent = analysis.explanation;
        
        // Debug metrics
        document.getElementById("metric-polarity").textContent = analysis.polarity;
        document.getElementById("metric-subjectivity").textContent = analysis.subjectivity;
        
        emotionPanel.classList.remove("d-none");

        // Capture selected language
        const languageSelect = document.getElementById('language-selector');
        const language = languageSelect ? languageSelect.value : '';
        const langParam = language ? `&lang=${encodeURIComponent(language)}` : '';
        const languageNames = { kn: 'Kannada', te: 'Telugu', ta: 'Tamil', ml: 'Malayalam', all: 'All Languages' };
        const languageLabel = language && languageNames[language] ? languageNames[language] : '';
// Construct movie API URL
const movieUrl = `/api/movies/mood/${analysis.emotion}?mood_prompt=${encodeURIComponent(promptText)}${langParam}`;
// Update grid title with language info if present
if (languageLabel) {
    gridTitle.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles text-info me-2"></i>Matched Vibe: ${displayEmotion} (${languageLabel})`;
} else {
    gridTitle.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles text-info me-2"></i>Matched Vibe: ${displayEmotion}`;
}
// Fetch movies from backend
const moviesResponse = await fetch(movieUrl);
if (!moviesResponse.ok) throw new Error();
const movies = await moviesResponse.json();
// Render movies grid
renderMovieGrid("movies-grid", movies);

    } catch (err) {
        console.error("NLP Submit Error:", err);
        gridTitle.textContent = "Recommended Suggestions";
        document.getElementById("movies-grid").innerHTML = `
            <div class="col-12 text-center py-5 bg-secondary border border-color rounded-4">
                <p class="text-danger mb-0"><i class="fa-solid fa-circle-exclamation me-1"></i>Unable to process recommendations.</p>
            </div>`;
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles me-2"></i>Analyze My Mood`;
    }
}

// ==========================================
// 5. DEBOUNCED SEARCH BAR
// ==========================================
function handleSearchInput(inputElement) {
    const query = inputElement.value.trim();
    const gridTitle = document.getElementById("recommendation-grid-title");
    
    clearTimeout(searchDebounceTimeout);
    
    if (!query) {
        gridTitle.innerHTML = `<i class="fa-solid fa-film text-info me-2"></i>Trending Suggestions For You`;
        loadInitialDashboardSuggestions();
        return;
    }

    // Clear active mood card states when search is entered
    document.querySelectorAll(".mood-select-card").forEach(card => card.classList.remove("active"));

    searchDebounceTimeout = setTimeout(() => {
        performInstantSearch(query);
    }, 300);
}

async function performInstantSearch(query) {
    const gridTitle = document.getElementById("recommendation-grid-title");
    
    gridTitle.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin text-info me-2"></i>Searching for "${query}"...`;
    renderNetflixLoader("movies-grid", `Searching databases for "${query}"...`);

    try {
        const response = await fetch(`/api/movies/search?q=${encodeURIComponent(query)}`);
        if (!response.ok) throw new Error();
        const results = await response.json();

        gridTitle.innerHTML = `<i class="fa-solid fa-magnifying-glass text-info me-2"></i>Search Results for "${query}"`;
        renderMovieGrid("movies-grid", results, `No movies found matching "${query}".`);
    } catch {
        gridTitle.innerHTML = `Search Results`;
        document.getElementById("movies-grid").innerHTML = `
            <div class="col-12 text-center py-5">
                <p class="text-danger small">Search failed. Verify your database is accessible.</p>
            </div>`;
    }
}

// ==========================================
// 6. WATCHLIST BOOKMARK MANAGEMENT
// ==========================================
async function fetchWatchlistCache() {
    try {
        const response = await fetch("/api/watchlist");
        if (response.ok) {
            const list = await response.json();
            userWatchlistCache = new Set(list.map(item => Number(item.movie_id)));
        }
    } catch (err) {
        console.error("Watchlist cache retrieval failed:", err);
    }
}

async function addToWatchlist(btnElement, movieId, title, posterPath) {
    btnElement.disabled = true;
    btnElement.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i>`;
    
    try {
        const response = await fetch("/api/watchlist", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                movie_id: movieId,
                movie_title: title,
                poster_path: posterPath
            })
        });
        
        if (!response.ok) throw new Error();
        
        userWatchlistCache.add(Number(movieId));
        
        // Set success visual state
        btnElement.className = "btn btn-sm btn-success w-100 py-2";
        btnElement.innerHTML = `<i class="fa-solid fa-check me-1"></i>In Watchlist`;
    } catch {
        btnElement.disabled = false;
        btnElement.className = "btn btn-sm btn-outline-danger w-100 py-2";
        btnElement.innerHTML = `<i class="fa-solid fa-triangle-exclamation me-1"></i>Error`;
    }
}

async function loadWatchlistGallery() {
    const grid = document.getElementById("watchlist-grid");
    if (!grid) return;

    renderNetflixLoader("watchlist-grid", "Fetching bookmarked watchlists...");

    try {
        const response = await fetch("/api/watchlist");
        if (!response.ok) throw new Error();
        const watchlist = await response.json();
        
        if (watchlist.length === 0) {
            grid.innerHTML = `
                <div class="col-12">
                    <div class="bg-secondary border border-color rounded-4 py-5 text-center">
                        <div class="empty-state">
                            <i class="fa-regular fa-folder-open empty-state-icon text-muted"></i>
                            <h3>No Movie Bookmarks</h3>
                            <p class="text-secondary mb-4">Your bookmarks list is empty. Select moods to populate it!</p>
                            <a href="/dashboard" class="btn btn-primary-custom px-4 py-2">
                                <i class="fa-solid fa-gauge-high me-2"></i>Go to Dashboard
                            </a>
                        </div>
                    </div>
                </div>`;
            return;
        }

        let cardsHTML = "";
        watchlist.forEach(movie => {
            const poster = movie.poster_path 
                ? `https://image.tmdb.org/t/p/w500${movie.poster_path}` 
                : "https://images.unsplash.com/photo-1594909122845-11baa439b7bf?w=500&auto=format&fit=crop";

            cardsHTML += `
                <div class="col-sm-6 col-md-4 col-lg-3 animate-fade-in" id="watchlist-card-${movie.movie_id}">
                    <div class="card-movie">
                        <div class="poster-container">
                            <img src="${poster}" class="poster-img" alt="${movie.movie_title}" loading="lazy">
                        </div>
                        <div class="movie-details">
                            <h4 class="movie-title mb-3" title="${movie.movie_title}">${movie.movie_title}</h4>
                            <div class="d-flex gap-2 mt-auto">
                                <button class="btn btn-sm btn-trailer-custom flex-grow-1" onclick="openTrailerModal(${movie.movie_id}, '${movie.movie_title.replace(/'/g, "\\'")}')">
                                    <i class="fa-solid fa-play"></i> Trailer
                                </button>
                                <button class="btn btn-sm btn-outline-danger px-3" onclick="removeFromWatchlist(this, ${movie.movie_id})" title="Remove bookmark">
                                    <i class="fa-regular fa-trash-can"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>`;
        });

        grid.innerHTML = cardsHTML;

    } catch {
        grid.innerHTML = `<p class="text-danger text-center">Failed to fetch watchlist.</p>`;
    }
}

async function removeFromWatchlist(btnElement, movieId) {
    btnElement.disabled = true;
    const oldIcon = btnElement.innerHTML;
    btnElement.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i>`;

    try {
        const response = await fetch(`/api/watchlist/${movieId}`, { method: "DELETE" });
        if (!response.ok) throw new Error();
        
        userWatchlistCache.delete(Number(movieId));

        const cardElement = document.getElementById(`watchlist-card-${movieId}`);
        if (cardElement) {
            cardElement.style.transition = "opacity 0.4s ease, transform 0.4s ease";
            cardElement.style.opacity = "0";
            cardElement.style.transform = "scale(0.8)";
            
            setTimeout(() => {
                cardElement.remove();
                const grid = document.getElementById("watchlist-grid");
                if (grid && grid.children.length === 0) {
                    loadWatchlistGallery();
                }
            }, 400);
        }
    } catch {
        btnElement.disabled = false;
        btnElement.innerHTML = oldIcon;
        alert("Wipe error. Try again.");
    }
}

// ==========================================
// 7. YOUTUBE TRAILER MODAL SYSTEM
// ==========================================
async function openTrailerModal(movieId, movieTitle) {
    const modalTitle = document.getElementById("trailerModalLabel");
    const videoBody = document.getElementById("trailerVideoContainer");
    
    // 1. Open Trailer modal via Bootstrap Trigger
    const trailerModalEl = document.getElementById("trailerModal");
    const modalInstance = bootstrap.Modal.getOrCreateInstance(trailerModalEl);
    modalInstance.show();

    // 2. Set Loading and Titles
    modalTitle.textContent = `${movieTitle} - Official Trailer`;
    videoBody.innerHTML = `
        <div class="d-flex flex-column justify-content-center align-items-center bg-black" style="position: absolute; top:0; left:0; width:100%; height:100%;">
            <div class="spinner-border text-info" role="status"></div>
            <p class="text-secondary small mt-3">Connecting to YouTube streams...</p>
        </div>`;

    try {
        // 3. Query custom endpoint for Youtube keys
        const response = await fetch(`/api/movies/trailer/${movieId}`);
        if (!response.ok) throw new Error();
        const data = await response.json();
        
        if (data.key) {
            // Embed iframe dynamically with autoplay/rel/modestbranding attributes
            videoBody.innerHTML = `
                <iframe src="https://www.youtube.com/embed/${data.key}?autoplay=1&rel=0&modestbranding=1" 
                    title="${movieTitle} Trailer"
                    frameborder="0" 
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                    allowfullscreen>
                </iframe>`;
        } else {
            throw new Error();
        }
    } catch {
        videoBody.innerHTML = `
            <div class="d-flex flex-column justify-content-center align-items-center bg-dark" style="position: absolute; top:0; left:0; width:100%; height:100%; padding:20px;">
                <i class="fa-solid fa-triangle-exclamation text-danger fa-2x mb-3"></i>
                <h5 class="small">Trailer Stream Unavailable</h5>
                <p class="text-muted small text-center mb-0">We could not retrieve an active video feed for this film.</p>
            </div>`;
    }
}

/**
 * Halts video playback completely when modal is hidden
 */
function bindTrailerModalCleanup() {
    const trailerModalEl = document.getElementById("trailerModal");
    if (!trailerModalEl) return;
    
    trailerModalEl.addEventListener("hidden.bs.modal", () => {
        const videoBody = document.getElementById("trailerVideoContainer");
        if (videoBody) {
            videoBody.innerHTML = ""; // Complete wipe kills iframe audio/video instantly
        }
    });
}

// ==========================================
// 8. SENTIMENT HISTORY DYNAMICS
// ==========================================
async function loadHistoryLogs() {
    const tableBody = document.getElementById("history-table-body");
    const tableWrapper = document.getElementById("history-table-wrapper");
    const emptyState = document.getElementById("history-empty-state");
    const loadingIndicator = document.getElementById("history-loading-indicator");
    const clearHistoryBtn = document.getElementById("clear-history-action-container");

    if (!tableBody) return;

    try {
        const response = await fetch("/api/history");
        if (!response.ok) throw new Error();
        const logs = await response.json();

        if (loadingIndicator) loadingIndicator.classList.add("d-none");

        if (logs.length === 0) {
            tableWrapper.classList.add("d-none");
            if (clearHistoryBtn) clearHistoryBtn.classList.add("d-none");
            emptyState.classList.remove("d-none");
            return;
        }

        let rowsHTML = "";
        logs.forEach(log => {
            let dateStr = "N/A";
            try {
                const dateObj = new Date(log.timestamp);
                dateStr = dateObj.toLocaleDateString("en-US", {
                    month: "short", day: "numeric", year: "numeric"
                }) + " " + dateObj.toLocaleTimeString("en-US", {
                    hour: "numeric", minute: "2-digit"
                });
            } catch (e) {}

            // Cap logs labels to SaaS design standards
            let displayEmotion = log.detected_emotion.charAt(0).toUpperCase() + log.detected_emotion.slice(1);
            if (log.detected_emotion === "excited") displayEmotion = "Action";
            if (log.detected_emotion === "fear") displayEmotion = "Horror";
            if (log.detected_emotion === "motivated") displayEmotion = "Motivational";

            const emojis = {
                happy: "😊", sad: "😢", romantic: "❤️", excited: "🔥",
                relaxed: "🧘", angry: "🔥", motivated: "💪", fear: "👻"
            };
            const emoji = emojis[log.detected_emotion] || "🎭";

            rowsHTML += `
                <tr class="align-middle">
                    <td class="small text-secondary">${dateStr}</td>
                    <td class="text-wrap text-break" style="max-width: 320px;">"${escapeHTML(log.mood)}"</td>
                    <td>
                        <span class="badge rounded-pill bg-dark border border-color py-2 px-3 text-white">
                            ${emoji} ${displayEmotion}
                        </span>
                    </td>
                    <td>
                        ${log.movie_title 
                            ? `<span class="fw-semibold text-info"><i class="fa-solid fa-ticket me-1"></i>${escapeHTML(log.movie_title)}</span>`
                            : `<span class="text-muted small">N/A</span>`
                        }
                    </td>
                </tr>`;
        });

        tableBody.innerHTML = rowsHTML;
        emptyState.classList.add("d-none");
        tableWrapper.classList.remove("d-none");
        if (clearHistoryBtn) clearHistoryBtn.classList.remove("d-none");

    } catch {
        if (loadingIndicator) {
            loadingIndicator.innerHTML = `<p class="text-danger small"><i class="fa-solid fa-triangle-exclamation"></i> Error loading logs.</p>`;
        }
    }
}

async function confirmWipeHistory() {
    if (!confirm("Wipe logs?")) return;
    try {
        const response = await fetch("/api/history", { method: "DELETE" });
        if (!response.ok) throw new Error();
        loadHistoryLogs();
    } catch {
        alert("Wipe error.");
    }
}

// ==========================================
// 9. ANIMATIONS & LOADERS UTILITIES
// ==========================================
function renderNetflixLoader(containerId, message = "Loading recommendations...") {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = `
        <div class="col-12">
            <div class="netflix-loader">
                <div class="spinner"></div>
                <p>${message}</p>
            </div>
        </div>`;
}

function renderMovieGrid(containerId, moviesList, emptyMessage = "No movie suggestions found.") {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (!moviesList || moviesList.length === 0) {
        container.innerHTML = `
            <div class="col-12 text-center py-5 bg-secondary border border-glass rounded-4 mt-3">
                <i class="fa-regular fa-face-frown text-muted fa-2x mb-3"></i>
                <h5 class="text-secondary">${emptyMessage}</h5>
            </div>`;
        return;
    }

    let gridHTML = "";
    moviesList.forEach(movie => {
        const poster = movie.poster_path 
            ? `https://image.tmdb.org/t/p/w500${movie.poster_path}` 
            : "https://images.unsplash.com/photo-1594909122845-11baa439b7bf?w=500&auto=format&fit=crop";

        const isBookmarked = userWatchlistCache.has(Number(movie.id));
        
        let bookmarkBtnHTML = "";
        if (isBookmarked) {
            bookmarkBtnHTML = `
                <button class="btn btn-sm btn-success w-100 py-2" disabled>
                    <i class="fa-solid fa-check me-1"></i>In Watchlist
                </button>`;
        } else {
            const escTitle = movie.title.replace(/'/g, "\\'").replace(/"/g, '&quot;');
            const escPoster = movie.poster_path ? movie.poster_path.replace(/'/g, "\\'") : "";
            
            bookmarkBtnHTML = `
                <button class="btn btn-sm btn-outline-custom w-100 py-2" onclick="addToWatchlist(this, ${movie.id}, '${escTitle}', '${escPoster}')">
                    <i class="fa-solid fa-plus me-1"></i>Watchlist
                </button>`;
        }

        const escTitleForTrailer = movie.title.replace(/'/g, "\\'").replace(/"/g, '&quot;');

        let genreBadges = "";
        if (movie.genres && movie.genres.length > 0) {
            movie.genres.slice(0, 1).forEach(g => {
                genreBadges = `<span class="genre">${g}</span>`;
            });
        }

        const releaseYear = movie.release_date && movie.release_date !== "N/A" 
            ? movie.release_date.split("-")[0] 
            : "N/A";

        gridHTML += `
            <div class="col-sm-6 col-md-4 col-lg-3 animate-fade-in">
                <div class="card-movie">
                    <div class="poster-container">
                        <img src="${poster}" class="poster-img" alt="${movie.title}" loading="lazy">
                        <div class="rating-badge">
                            <i class="fa-solid fa-star"></i>${movie.vote_average}
                        </div>
                    </div>
                    <div class="movie-details">
                        <h4 class="movie-title" title="${movie.title}">${movie.title}</h4>
                        <div class="movie-meta text-muted mb-2">
                            <span>${releaseYear}</span>
                            ${genreBadges ? `<span>•</span> ${genreBadges}` : ""}
                        </div>
                        <p class="movie-overview">${movie.overview}</p>
                        <div class="mt-auto d-flex flex-column gap-2">
                            <button class="btn btn-sm btn-trailer-custom w-100 py-2" onclick="openTrailerModal(${movie.id}, '${escTitleForTrailer}')">
                                <i class="fa-solid fa-play me-1"></i>Watch Trailer
                            </button>
                            ${bookmarkBtnHTML}
                        </div>
                    </div>
                </div>
            </div>`;
    });

    container.innerHTML = gridHTML;
}

function escapeHTML(str) {
    if (!str) return "";
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
