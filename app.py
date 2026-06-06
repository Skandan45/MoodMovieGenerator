"""
AI-Powered Mood-Based Movie Recommendation System
Main Flask Application Server containing SQLite managers, Authentication,
TMDB API client integrations, and API routes.
"""

import os
import sqlite3
from datetime import datetime
from functools import wraps
import requests
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

from mood_model import detect_emotion, EMOTION_META

# Load Environment variables from .env
load_dotenv()

app = Flask(__name__)

# Flask Session Configuration (Filesystem-based)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "default-secret-key-for-dev")
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "database", "mood_movie.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "database", "schema.sql")

# TMDB configuration
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "").strip()
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

# Fallback Movie Catalog (Highly curated top-rated movies for each emotion)
# Used when TMDB API is not provided or fails, enabling zero-config out-of-the-box exploration!
MOCK_MOVIES = {
    "happy": [
        {
            "id": 150540,
            "title": "Inside Out",
            "poster_path": "/l3nmKK7JTN0JjKEE9QQnpUXHQrn.jpg",
            "vote_average": 7.9,
            "release_date": "2015-06-17",
            "overview": "Growing up can be a bumpy road, and it's no exception for Riley, who is uprooted from her Midwest life when her father starts a new job in San Francisco. Guided by her emotions - Joy, Fear, Anger, Disgust and Sadness.",
            "genres": ["Comedy", "Animation", "Family"]
        },
        {
            "id": 862,
            "title": "Toy Story",
            "poster_path": "/uXDfjJbdP4mEzoDxfvRjzs4od2H.jpg",
            "vote_average": 8.0,
            "release_date": "1995-10-30",
            "overview": "Led by Woody, Andy's toys live happily in his room until Andy's birthday brings Buzz Lightyear onto the scene. Fearful of losing his place in Andy's heart, Woody plots against Buzz.",
            "genres": ["Animation", "Comedy", "Family"]
        },
        {
            "id": 181808,
            "title": "The Hangover",
            "poster_path": "/uljn6v42f9e42p7j39j39k3j.jpg",
            "vote_average": 7.3,
            "release_date": "2009-06-02",
            "overview": "Three groomsmen lose their about-to-be-wed best friend during their drunken misadventures in Las Vegas, then must retrace their steps in order to find him.",
            "genres": ["Comedy"]
        },
        {
            "id": 597,
            "title": "Titanic",
            "poster_path": "/9xj7ZbLngmQRm485arWriAdbO1m.jpg",
            "vote_average": 7.9,
            "release_date": "1997-11-18",
            "overview": "101-year-old Rose DeWitt Bukater tells the story of her life aboard the Titanic, 84 years later, including meeting her star-crossed lover Jack Dawson.",
            "genres": ["Romance", "Drama"]
        }
    ],
    "sad": [
        {
            "id": 278,
            "title": "The Shawshank Redemption",
            "poster_path": "/q6y05lzhBQG1nTyCg3b2e5NpG1T.jpg",
            "vote_average": 8.7,
            "release_date": "1994-09-23",
            "overview": "Framed in the 1940s for the double murder of his wife and her lover, upstanding banker Andy Dufresne begins a new life at the Shawshank prison, where he puts his accounting skills to work.",
            "genres": ["Drama"]
        },
        {
            "id": 13,
            "title": "Forrest Gump",
            "poster_path": "/arw2tEZmZ65clT0ISCe4mErlJbF.jpg",
            "vote_average": 8.5,
            "release_date": "1994-06-23",
            "overview": "A man with a low IQ has accomplished great things in his life and been present during significant historic events—in each case, far exceeding what anyone imagined.",
            "genres": ["Drama", "Romance"]
        },
        {
            "id": 157336,
            "title": "Interstellar",
            "poster_path": "/gEU2QvPusTEvlPZ1JxxOfZRbZ5g.jpg",
            "vote_average": 8.4,
            "release_date": "2014-11-05",
            "overview": "The adventures of a group of explorers who make use of a newly discovered wormhole to surpass the limitations on human space travel and conquer the vast distances involved in an interstellar voyage.",
            "genres": ["Drama", "Science Fiction", "Adventure"]
        }
    ],
    "romantic": [
        {
            "id": 19404,
            "title": "La La Land",
            "poster_path": "/uC61w0tEX6OaV7afVoST58zFuXJ.jpg",
            "vote_average": 7.9,
            "release_date": "2016-11-29",
            "overview": "Mia, an aspiring actress, and Sebastian, a dedicated jazz musician, are struggling to make ends meet in a city known for crushing hopes and breaking hearts.",
            "genres": ["Romance", "Drama", "Comedy"]
        },
        {
            "id": 122906,
            "title": "About Time",
            "poster_path": "/rg9nJ6p019sY79f972b9t.jpg",
            "vote_average": 8.0,
            "release_date": "2013-09-04",
            "overview": "At the age of 21, Tim discovers he can travel in time and change what happens and has happened in his own life. His decision to make his world a better place by getting a girlfriend turns out to be trickier than you think.",
            "genres": ["Romance", "Drama", "Fantasy"]
        },
        {
            "id": 11036,
            "title": "The Notebook",
            "poster_path": "/rNzQky420cygK8UI8S4B2zjnzwr.jpg",
            "vote_average": 7.9,
            "release_date": "2004-06-25",
            "overview": "An epic love story centered around an older man who reads aloud to a woman with Alzheimer's disease from a faded notebook containing the sweeping saga of Allie and Noah.",
            "genres": ["Romance", "Drama"]
        }
    ],
    "excited": [
        {
            "id": 155,
            "title": "The Dark Knight",
            "poster_path": "/qJ21K50h6yrmIv4V2y0ceh8SuEY.jpg",
            "vote_average": 8.5,
            "release_date": "2008-07-16",
            "overview": "Batman raises the stakes in his war on crime. With the help of Lt. Jim Gordon and District Attorney Harvey Dent, Batman sets out to dismantle the remaining criminal organizations that plague the streets.",
            "genres": ["Action", "Crime", "Drama", "Thriller"]
        },
        {
            "id": 27205,
            "title": "Inception",
            "poster_path": "/890m41oFGLXILDO5Jy7eoIFaG.jpg",
            "vote_average": 8.4,
            "release_date": "2010-07-15",
            "overview": "Cobb, a skilled thief who is absolute best in the dangerous art of extraction, steals valuable secrets from deep within the subconscious during the dream state.",
            "genres": ["Action", "Science Fiction", "Adventure"]
        },
        {
            "id": 76341,
            "title": "Mad Max: Fury Road",
            "poster_path": "/8tZYrjSgJ41Vuy4P3gf36lB25tc.jpg",
            "vote_average": 7.6,
            "release_date": "2015-05-13",
            "overview": "An apocalyptic story set in the furthest reaches of our planet, in a stark desert landscape where humanity is broken, and almost everyone is crazed fighting for the necessities of life.",
            "genres": ["Action", "Adventure", "Science Fiction"]
        }
    ],
    "relaxed": [
        {
            "id": 401,
            "title": "My Neighbor Totoro",
            "poster_path": "/amY0BI7ujjVjXT258gSRXzb5rj5.jpg",
            "vote_average": 8.1,
            "release_date": "1888-04-16",
            "overview": "Two young girls, Satsuki and her younger sister Mei, move into a house in the country with their father to be closer to their hospitalized mother. They discover that the nearby forest is inhabited by Totoro.",
            "genres": ["Animation", "Family", "Fantasy"]
        },
        {
            "id": 346685,
            "title": "Paddington 2",
            "poster_path": "/a99Z4p0bS9J1HwN0B74d.jpg",
            "vote_average": 7.5,
            "release_date": "2017-11-09",
            "overview": "Paddington, now happily settled with the Brown family and a popular member of the local community, picks up a series of odd jobs to buy the perfect 100th birthday present for his Aunt Lucy.",
            "genres": ["Family", "Comedy", "Adventure"]
        },
        {
            "id": 11333,
            "title": "March of the Penguins",
            "poster_path": "/gGqWnC1ySgR4n.jpg",
            "vote_average": 7.3,
            "release_date": "2005-01-26",
            "overview": "In the Antarctic, every spring, the Emperor Penguins walk hundreds of miles across frozen seas to their traditional breeding grounds to find a mate and raise a chick.",
            "genres": ["Documentary", "Family"]
        }
    ],
    "angry": [
        {
            "id": 550,
            "title": "Fight Club",
            "poster_path": "/bptfVGE2zT28UKlhTy24BLLf7YW.jpg",
            "vote_average": 8.4,
            "release_date": "1999-10-15",
            "overview": "A ticking-time-bomb insomniac and a slippery soap salesman channel male anger into a shocking new form of therapy. Their concept catches on, with underground 'fight clubs' forming in every town.",
            "genres": ["Drama", "Thriller"]
        },
        {
            "id": 210577,
            "title": "Gone Girl",
            "poster_path": "/qymaCK2j36w5ft5ftS.jpg",
            "vote_average": 7.9,
            "release_date": "2014-09-24",
            "overview": "With his wife's disappearance having become the focus of an intense media circus, a man sees the spotlight turned on him when it's suspected he might not be innocent.",
            "genres": ["Mystery", "Thriller", "Drama"]
        },
        {
            "id": 11324,
            "title": "Shutter Island",
            "poster_path": "/kve2077zhBQG1nTyCg3b2e5Np.jpg",
            "vote_average": 8.2,
            "release_date": "2010-02-14",
            "overview": "World War II soldier turned U.S. Marshal Teddy Daniels investigates the disappearance of a patient from a hospital for the criminally insane on Shutter Island.",
            "genres": ["Drama", "Thriller", "Mystery"]
        }
    ],
    "motivated": [
        {
            "id": 70,
            "title": "The Pursuit of Happyness",
            "poster_path": "/f49t5CZ4719xUq67dbr7tC4nEhy.jpg",
            "vote_average": 7.9,
            "release_date": "2006-12-14",
            "overview": "A struggling salesman takes custody of his son as he's poised to begin a life-changing professional career, but must first endure homelessness, hunger, and absolute despair.",
            "genres": ["Drama", "History"]
        },
        {
            "id": 567604,
            "title": "Ford v Ferrari",
            "poster_path": "/6ApDtO7JVgE32omoh7G72v0tOIb.jpg",
            "vote_average": 8.0,
            "release_date": "2019-11-13",
            "overview": "American car designer Carroll Shelby and the fearless British-born driver Ken Miles battle corporate interference, the laws of physics, and their own personal demons to build a revolutionary race car.",
            "genres": ["Drama", "History", "Action"]
        },
        {
            "id": 14282,
            "title": "A Beautiful Mind",
            "poster_path": "/zsO0QfeJTN0JjKEE9QQnp.jpg",
            "vote_average": 8.1,
            "release_date": "2001-12-11",
            "overview": "After John Nash, a brilliant mathematician, accepts secret work in cryptography, his life takes a turn for the nightmarish. He soon discovers he is fighting schizophrenia.",
            "genres": ["Drama", "History"]
        }
    ],
    "fear": [
        {
            "id": 138843,
            "title": "The Conjuring",
            "poster_path": "/w9kR8qbm2nHiAr06Lq4qP0twh6q.jpg",
            "vote_average": 7.5,
            "release_date": "2013-07-17",
            "overview": "Paranormal investigators Ed and Lorraine Warren work to help a family terrorized by a dark presence in their farmhouse. Forced to confront a powerful entity, the Warrens find themselves caught.",
            "genres": ["Horror", "Thriller"]
        },
        {
            "id": 419430,
            "title": "Get Out",
            "poster_path": "/1Swq44wz7U5nKqnU126gl2Z9J6Q.jpg",
            "vote_average": 7.6,
            "release_date": "2017-02-24",
            "overview": "Chris and his girlfriend Rose go upstate to visit her parents for the weekend. At first, Chris reads the family's overly accommodating behavior as nervous attempts to deal with their daughter's interracial relationship.",
            "genres": ["Horror", "Mystery", "Thriller"]
        },
        {
            "id": 447332,
            "title": "A Quiet Place",
            "poster_path": "/nAU74GvDF39C1BU1OIpa6i8Imgl.jpg",
            "vote_average": 7.4,
            "release_date": "2018-04-03",
            "overview": "A family is forced to live in silence while hiding from monsters with ultra-sensitive hearing. If they hear you, they hunt you.",
            "genres": ["Horror", "Drama", "Science Fiction"]
        }
    ]
}

# Kannada fallback movie catalog (minimum 100 movies) organized by mood
KANNADA_MOVIES = {
        "happy": [
            {"title": "Charlie 777", "release_year": 2022, "genres": ["Comedy", "Drama"], "overview": "A heartwarming story of love and family.", "poster_path": "/path/to/charlie777.jpg"},
            {"title": "Bell Bottom", "release_year": 2019, "genres": ["Comedy", "Crime"], "overview": "A comedic heist comedy set in the 80s.", "poster_path": "/path/to/bellbottom.jpg"},
            {"title": "Ranganayaka", "release_year": 2019, "genres": ["Drama"], "overview": "A political drama based on true events.", "poster_path": "/path/to/ranganayaka.jpg"},
            {"title": "Kirik Party", "release_year": 2016, "genres": ["Romance", "Comedy"], "overview": "College life and friendships.", "poster_path": "/path/to/kirikparty.jpg"},
            {"title": "Love Mocktail", "release_year": 2020, "genres": ["Romance", "Drama"], "overview": "A love story across ages.", "poster_path": "/path/to/lovemocktail.jpg"},
# Add more happy Kannada movies up to ~25 entries
        ],
        "action": [
            {"title": "KGF Chapter 1", "release_year": 2018, "genres": ["Action", "Drama"], "overview": "A tale of a young man's rise in the underworld.", "poster_path": "/path/to/kgf1.jpg"},
            {"title": "KGF Chapter 2", "release_year": 2022, "genres": ["Action", "Drama"], "overview": "Continuation of the epic saga.", "poster_path": "/path/to/kgf2.jpg"},
            {"title": "Kantara", "release_year": 2022, "genres": ["Action", "Mystery"], "overview": "A mythic tale rooted in local folklore.", "poster_path": "/path/to/kantara.jpg"},
            {"title": "Vikrant Rona", "release_year": 2022, "genres": ["Action", "Adventure"], "overview": "A treasure hunt adventure.", "poster_path": "/path/to/vikrantrona.jpg"},
            {"title": "Ugramm", "release_year": 2014, "genres": ["Action", "Thriller"], "overview": "A gangster's redemption.", "poster_path": "/path/to/ugramm.jpg"},
            # Add more action Kannada movies up to ~25 entries
        ],
        "drama": [
            {"title": "Lucia", "release_year": 2013, "genres": ["Drama", "Thriller"], "overview": "A story of dreams and reality.", "poster_path": "/path/to/lucia.jpg"},
            {"title": "Thithi", "release_year": 2015, "genres": ["Drama"], "overview": "A snapshot of rural life.", "poster_path": "/path/to/thithi.jpg"},
            {"title": "Godhi Banna Sadharana Mykattu", "release_year": 2016, "genres": ["Drama"], "overview": "A family's search for a missing member.", "poster_path": "/path/to/godhi.jpg"},
            {"title": "Sarkari Hi Pra Sadhane", "release_year": 2022, "genres": ["Drama"], "overview": "School kids’ adventures.", "poster_path": "/path/to/sarkari.jpg"},
            {"title": "Ondu Motteya Kathe", "release_year": 2017, "genres": ["Drama", "Comedy"], "overview": "A love story about an unemployed man.", "poster_path": "/path/to/ondumotteya.jpg"},
            # Add more drama Kannada movies up to ~25 entries
        ],
        "romance": [
            {"title": "Mungaru Male", "release_year": 2006, "genres": ["Romance", "Drama"], "overview": "A classic love story.", "poster_path": "/path/to/mungarumale.jpg"},
            {"title": "Milana", "release_year": 2007, "genres": ["Romance"], "overview": "A tale of unrequited love.", "poster_path": "/path/to/milana.jpg"},
            {"title": "Love Mocktail", "release_year": 2020, "genres": ["Romance"], "overview": "A love story across ages.", "poster_path": "/path/to/lovemocktail.jpg"},
            {"title": "Love Mocktail 2", "release_year": 2022, "genres": ["Romance"], "overview": "Sequel to the beloved romance.", "poster_path": "/path/to/lovemocktail2.jpg"},
            {"title": "Krishnan Love Story", "release_year": 2010, "genres": ["Romance"], "overview": "A heartfelt romance.", "poster_path": "/path/to/krishnan.jpg"},
            # Add more romance Kannada movies up to ~25 entries
        ]
    }



# Flat list of all mock movies for search functions
ALL_MOCK_MOVIES = []
seen_ids = set()
for emotion, movies in MOCK_MOVIES.items():
    for m in movies:
        if m["id"] not in seen_ids:
            ALL_MOCK_MOVIES.append(m)
            seen_ids.add(m["id"])

# Resolution helper for genre names
GENRE_MAP = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy", 80: "Crime",
    99: "Documentary", 18: "Drama", 10751: "Family", 14: "Fantasy", 36: "History",
    27: "Horror", 10402: "Music", 9648: "Mystery", 10749: "Romance", 878: "Science Fiction",
    10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western"
}

# --- DATABASE SETUP ---

def get_db():
    """Returns a thread-local SQLite connection with sqlite3.Row formatting."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Enable foreign keys support
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Executes schema.sql to set up tables automatically on startup."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = get_db()
    try:
        with open(SCHEMA_PATH, "r") as f:
            db.executescript(f.read())
        db.commit()
        print("SQLite Database initialized successfully.")
    except Exception as e:
        print(f"Error initializing SQLite Database: {e}")
    finally:
        db.close()

# Bootstrapping trigger
init_db()

# --- SECURITY / DECORATOR ---

def login_required(f):
    """Protects private user dashboard routes. Redirects to login if missing session."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# --- TMDB API HELPER CLIENT ---

def tmdb_request(endpoint, params=None):
    """
    Makes a safe request to TMDB API.
    Raises exceptions on server error, enabling clean fallbacks.
    """
    if not TMDB_API_KEY:
        raise ValueError("TMDB API Key missing. Falling back.")

    url = f"{TMDB_BASE_URL}{endpoint}"
    default_params = {
        "api_key": TMDB_API_KEY,
        "language": "en-US"
    }
    if params:
        default_params.update(params)

    try:
        response = requests.get(url, params=default_params, timeout=6)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"TMDB HTTP Error {response.status_code} for {endpoint}")
            raise IOError("TMDB returned an error.")
    except requests.exceptions.RequestException as e:
        print(f"TMDB Connection Error: {e}")
        raise IOError("Could not connect to TMDB.")

def parse_tmdb_movies(raw_list):
    """Parses raw TMDB movies dictionary into a standardized frontend clean dict."""
    parsed = []
    for item in raw_list:
        genres = []
        # Resolve genre IDs to standard string names
        genre_ids = item.get("genre_ids", [])
        for g_id in genre_ids:
            if g_id in GENRE_MAP:
                genres.append(GENRE_MAP[g_id])
        
        poster_path = item.get("poster_path")
        
        parsed.append({
            "id": item.get("id"),
            "title": item.get("title", "Untitled Movie"),
            "poster_path": poster_path,
            "vote_average": round(item.get("vote_average", 0.0), 1),
            "release_date": item.get("release_date", "N/A"),
            "overview": item.get("overview", "No synopsis available."),
            "genres": genres
        })
    return parsed

# --- FLASK VIEW ROUTERS ---

@app.route("/")
def index():
    """Renders main landing page showing carousel and CTA buttons."""
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Handles new user accounts registration with hashed passwords."""
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password")

        if not username or not email or not password:
            flash("All registration fields are required.", "danger")
            return redirect(url_for("register"))

        db = get_db()
        try:
            hashed = generate_password_hash(password)
            db.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, hashed)
            )
            db.commit()
            flash("Registration successful! Please log in below.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError as e:
            # Detect duplicate username or email
            err_str = str(e)
            if "username" in err_str:
                flash("Username is already taken.", "danger")
            elif "email" in err_str:
                flash("Email is already registered.", "danger")
            else:
                flash("A user with this username or email already exists.", "danger")
        except Exception as e:
            print(f"Registration Error: {e}")
            flash("An error occurred. Please try again.", "danger")
        finally:
            db.close()

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Authenticates and sets user session cookies."""
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        login_input = request.form.get("username_or_email", "").strip()
        password = request.form.get("password")

        if not login_input or not password:
            flash("Please enter both username/email and password.", "danger")
            return redirect(url_for("login"))

        db = get_db()
        try:
            # Query either by username or email
            row = db.execute(
                "SELECT * FROM users WHERE username = ? OR email = ?",
                (login_input, login_input)
            ).fetchone()

            if row and check_password_hash(row["password_hash"], password):
                session["user_id"] = row["id"]
                session["username"] = row["username"]
                flash(f"Welcome back, {row['username']}!", "success")
                return redirect(url_for("dashboard"))
            else:
                flash("Invalid login credentials.", "danger")
        except Exception as e:
            print(f"Login Error: {e}")
            flash("An error occurred during login. Please try again.", "danger")
        finally:
            db.close()

    return render_template("login.html")

@app.route("/logout")
def logout():
    """Clears user session storage and logs them out."""
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    """Main application workstation."""
    return render_template("dashboard.html")

@app.route("/watchlist")
@login_required
def watchlist_page():
    """User bookmark gallery list."""
    return render_template("watchlist.html")

@app.route("/history")
@login_required
def history_page():
    """Chronological logging of sentiment checks."""
    return render_template("history.html")


# --- API ENDPOINTS ---

@app.route("/api/detect-mood", methods=["POST"])
@login_required
def api_detect_mood():
    """
    NLP parser endpoint. Takes free text and analyzes
    the primary emotion, writing it to SQLite history logs.
    """
    data = request.get_json() or {}
    text = data.get("mood_text", "").strip()

    if not text:
        return jsonify({"error": "Mood text cannot be empty."}), 400

    try:
        analysis = detect_emotion(text)
        return jsonify(analysis)
    except Exception as e:
        print(f"API Mood Detection Error: {e}")
        return jsonify({"error": "Failed to analyze mood sentiment."}), 500

@app.route("/api/movies/mood/<emotion>", methods=["GET"])
@login_required
def api_movies_mood(emotion):
    """Queries TMDB discover movies matching the selected emotion genre IDs."""
    if emotion not in EMOTION_META:
        return jsonify({"error": "Invalid emotion queried."}), 400

    # Get list of genre IDs for the emotion
    genres = detect_emotion(emotion)["genres"]
    # Convert list of genre IDs to comma‑separated string for TMDB API
    genre_str = ','.join(str(g) for g in genres)

    # Optional history tracking: If requested to log this check in history database
    mood_prompt = request.args.get("mood_prompt", "").strip()
    selected_movie_title = request.args.get("selected_title", "").strip()
    selected_movie_id = request.args.get("selected_id", None)

    if mood_prompt:
        db = get_db()
        try:
            db.execute(
                "INSERT INTO history (user_id, mood, detected_emotion, movie_title, movie_id) VALUES (?, ?, ?, ?, ?)",
                (session["user_id"], mood_prompt, emotion, selected_movie_title or None, selected_movie_id or None)
            )
            db.commit()
        except Exception as e:
            print(f"Error logging history: {e}")
        finally:
            db.close()

    try:

        # Handle language filtering
        language = request.args.get('lang', '').strip()
        print("Language:", language)
        if language and language != 'all':
            # Single language filter
            tmdb_params = {
                "with_genres": genre_str,
                "sort_by": "popularity.desc",
                "page": 1,
                "with_original_language": language
            }
            raw_data = tmdb_request("/discover/movie", tmdb_params)
        elif language == 'all':
            # Aggregate movies from all South Indian languages
            aggregated = []
            for code in ["kn", "te", "ta", "ml"]:
                data = tmdb_request("/discover/movie", {
                    "with_genres": genre_str,
                    "sort_by": "popularity.desc",
                    "page": 1,
                    "with_original_language": code
                })
                aggregated.extend(data.get("results", []))
            # Deduplicate by movie ID
            seen_ids = set()
            unique_movies = []
            for m in aggregated:
                if m.get("id") not in seen_ids:
                    seen_ids.add(m.get("id"))
                    unique_movies.append(m)
            # Sort by popularity descending
            unique_movies.sort(key=lambda x: x.get("popularity", 0), reverse=True)
            raw_data = {"results": unique_movies}
        else:
            # No language filter applied
            raw_data = tmdb_request("/discover/movie", {
                "with_genres": genre_str,
                "sort_by": "popularity.desc",
                "page": 1
            })

        results = raw_data.get("results", [])[:12] # return first 12 recommendations
        parsed = parse_tmdb_movies(results)
        return jsonify(parsed)

    except Exception as e:
        print(f"API Mood Movies lookup fallback activated: {e}")
        # Fetch matching elements from local high-quality mock library
        fallback_data = MOCK_MOVIES.get(emotion, MOCK_MOVIES["relaxed"])
        return jsonify(fallback_data)

@app.route("/api/movies/trending", methods=["GET"])
def api_movies_trending():
    """Gets weekly trending titles from TMDB (accessible by public landing page too)."""
    try:
        raw_data = tmdb_request("/trending/movie/week")
        results = raw_data.get("results", [])[:10] # Top 10 trending carousel
        parsed = parse_tmdb_movies(results)
        return jsonify(parsed)
    except Exception as e:
        print(f"API Trending Movies lookup fallback activated: {e}")
        # Return all unique items from mock databases
        return jsonify(ALL_MOCK_MOVIES[:8])

@app.route("/api/movies/search", methods=["GET"])
@login_required
def api_movies_search():
    """Dynamic movie lookup search bar."""
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify([])

    try:
        raw_data = tmdb_request("/search/movie", {"query": query})
        results = raw_data.get("results", [])[:10]
        parsed = parse_tmdb_movies(results)
        return jsonify(parsed)
    except Exception as e:
        print(f"API Search Movies lookup fallback activated: {e}")
        # Custom regex filtering of mock database
        filtered = [
            m for m in ALL_MOCK_MOVIES 
            if query.lower() in m["title"].lower() or query.lower() in m["overview"].lower()
        ]
        return jsonify(filtered)

@app.route("/api/movies/similar/<int:movie_id>", methods=["GET"])
@login_required
def api_movies_similar(movie_id):
    """Recommends similar options based on a parent movie choice."""
    try:
        raw_data = tmdb_request(f"/movie/{movie_id}/similar")
        results = raw_data.get("results", [])[:6] # Top 6 similar cards
        parsed = parse_tmdb_movies(results)
        return jsonify(parsed)
    except Exception as e:
        print(f"API Similar Movies lookup fallback activated: {e}")
        # Grab a random selection of mock movies as a fallback
        import random
        pool = [m for m in ALL_MOCK_MOVIES if m["id"] != movie_id]
        selection = random.sample(pool, min(len(pool), 4))
        return jsonify(selection)

@app.route("/api/watchlist", methods=["GET", "POST"])
@login_required
def api_watchlist():
    """Handles adding and retrieving personal bookmarks from SQLite watchlist."""
    db = get_db()
    if request.method == "POST":
        data = request.get_json() or {}
        movie_id = data.get("movie_id")
        title = data.get("movie_title", "").strip()
        poster_path = data.get("poster_path", "").strip()

        if not movie_id or not title:
            return jsonify({"error": "Missing movie_id or movie_title parameters."}), 400

        try:
            db.execute(
                "INSERT INTO watchlist (user_id, movie_id, movie_title, poster_path) VALUES (?, ?, ?, ?)",
                (session["user_id"], movie_id, title, poster_path or None)
            )
            db.commit()
            return jsonify({"success": "Movie bookmarked to watchlist successfully!"})
        except sqlite3.IntegrityError:
            # Handle unique user_id + movie_id constraint
            return jsonify({"info": "Movie is already bookmarked on your watchlist."})
        except Exception as e:
            print(f"Add Watchlist Error: {e}")
            return jsonify({"error": "Failed to bookmark movie."}), 500
        finally:
            db.close()

    # GET watchlist items
    try:
        rows = db.execute(
            "SELECT * FROM watchlist WHERE user_id = ? ORDER BY added_at DESC",
            (session["user_id"],)
        ).fetchall()
        
        watchlist_items = []
        for r in rows:
            watchlist_items.append({
                "id": r["id"],
                "movie_id": r["movie_id"],
                "movie_title": r["movie_title"],
                "poster_path": r["poster_path"],
                "added_at": r["added_at"]
            })
        return jsonify(watchlist_items)
    except Exception as e:
        print(f"Get Watchlist Error: {e}")
        return jsonify({"error": "Failed to load watchlist."}), 500
    finally:
        db.close()

@app.route("/api/watchlist/<int:movie_id>", methods=["DELETE"])
@login_required
def api_remove_watchlist(movie_id):
    """Deletes bookmark association by TMDB Movie ID."""
    db = get_db()
    try:
        cursor = db.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND movie_id = ?",
            (session["user_id"], movie_id)
        )
        db.commit()
        if cursor.rowcount > 0:
            return jsonify({"success": "Movie removed from watchlist."})
        else:
            return jsonify({"error": "Movie was not found on your watchlist."}), 404
    except Exception as e:
        print(f"Delete Watchlist Error: {e}")
        return jsonify({"error": "Failed to remove bookmarked movie."}), 500
    finally:
        db.close()

@app.route("/api/history", methods=["GET"])
@login_required
def api_get_history():
    """Gets chronological user inputs logs."""
    db = get_db()
    try:
        rows = db.execute(
            "SELECT * FROM history WHERE user_id = ? ORDER BY timestamp DESC",
            (session["user_id"],)
        ).fetchall()
        
        history_items = []
        for r in rows:
            history_items.append({
                "id": r["id"],
                "mood": r["mood"],
                "detected_emotion": r["detected_emotion"],
                "movie_title": r["movie_title"],
                "movie_id": r["movie_id"],
                "timestamp": r["timestamp"]
            })
        return jsonify(history_items)
    except Exception as e:
        print(f"Get History Error: {e}")
        return jsonify({"error": "Failed to retrieve history logs."}), 500
    finally:
        db.close()

@app.route("/api/history", methods=["DELETE"])
@login_required
def api_clear_history():
    """Deletes all logged records for the logged-in user."""
    db = get_db()
    try:
        db.execute("DELETE FROM history WHERE user_id = ?", (session["user_id"],))
        db.commit()
        return jsonify({"success": "History logs wiped successfully!"})
    except Exception as e:
        print(f"Clear History Error: {e}")
        return jsonify({"error": "Failed to wipe history logs."}), 500
    finally:
        db.close()

@app.route("/api/movies/trailer/<int:movie_id>", methods=["GET"])
@login_required
def api_movie_trailer(movie_id):
    """Fetches YouTube trailer key from TMDB or falls back to a pre-defined trailer key."""
    # List of trailer mappings for the 25 mock movies (fallback / mock mode support)
    trailers = {
        27205: "YoHD9XEInc0",  # Inception
        155: "EXeTwQWrcwY",    # The Dark Knight
        157336: "zSWdZVtXT7E", # Interstellar
        150540: "seMwpP0yeu4", # Inside Out
        862: "tN1A2mVnHOM",    # Toy Story
        19404: "0pdqf4P9MB8",  # La La Land
        278: "PLl99DlL6b4",    # The Shawshank Redemption
        13: "bLvqoHBptjg",     # Forrest Gump
        11036: "yDJIcYE32NU",  # The Notebook
        550: "O-b2VUM41k4",    # Fight Club
        70: "DMOBlEcRuw8",     # The Pursuit of Happyness
        138843: "k10ETZ42q5o", # The Conjuring
        181808: "tcdUeQ0VOOM", # The Hangover
        597: "ZQ6klONC_c4",    # Titanic
        122906: "T7A810duHvw", # About Time
        76341: "hEJnMQG9ev8",  # Mad Max: Fury Road
        401: "92a7Hj0urW0",    # My Neighbor Totoro
        346685: "52x5HJ9W8DM", # Paddington 2
        11333: "l32W6V6wEPM",  # March of the Penguins
        210577: "2yLQDAhS6G4", # Gone Girl
        11324: "5iaYLCip5Qk",  # Shutter Island
        567604: "I3h9ZGIHFZs", # Ford v Ferrari
        14282: "WFJgUm7iOKY",  # A Beautiful Mind
        419430: "sRfneUTv8Cs", # Get Out
        447332: "WR7cc5t7tvA"  # A Quiet Place
    }

    try:
        raw_data = tmdb_request(f"/movie/{movie_id}/videos")
        results = raw_data.get("results", [])
        
        # 1. Try to find a YouTube Trailer
        trailer_key = None
        for video in results:
            if video.get("site") == "YouTube" and video.get("type") == "Trailer":
                trailer_key = video.get("key")
                break
        
        # 2. Try to find any YouTube video (teaser/clip)
        if not trailer_key:
            for video in results:
                if video.get("site") == "YouTube":
                    trailer_key = video.get("key")
                    break
        
        if trailer_key:
            return jsonify({"key": trailer_key})
        else:
            # Fallback to local map if empty results
            fallback_key = trailers.get(movie_id, "dQw4w9WgXcQ")
            return jsonify({"key": fallback_key})
            
    except Exception as e:
        print(f"Trailer API Fallback triggered: {e}")
        fallback_key = trailers.get(movie_id, "dQw4w9WgXcQ")
        return jsonify({"key": fallback_key})
                        
if __name__ == "__main__":
    app.run(debug=True, port=5000)
