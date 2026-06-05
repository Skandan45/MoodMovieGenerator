"""
TMDB API Connection & Integration Diagnostics Test Suite
"""
import dotenv
import os

dotenv.load_dotenv()
from app import tmdb_request, parse_tmdb_movies

print("=" * 75)
print("TMDB INTEGRATION DIAGNOSTICS & SYSTEM TEST RUN")
print("=" * 75)

errors = 0

# Test 1: Trending Movies
try:
    trending = tmdb_request("/trending/movie/week")
    parsed_trending = parse_tmdb_movies(trending.get("results", []))
    print(f"[OK] Test 1: Trending Movies - Successfully fetched {len(parsed_trending)} movies.")
    print(f"     Top Trending Film: \"{parsed_trending[0]['title']}\" (Rating: {parsed_trending[0]['vote_average']})")
except Exception as e:
    print(f"[FAIL] Test 1: Trending Movies - Error: {e}")
    errors += 1

# Test 2: Mood Genre Discover (Happy: Comedy 35 + Animation 16)
try:
    discover = tmdb_request("/discover/movie", {"with_genres": "35,16", "sort_by": "popularity.desc"})
    parsed_discover = parse_tmdb_movies(discover.get("results", []))
    print(f"[OK] Test 2: Mood Genre Discover - Successfully fetched {len(parsed_discover)} comedies/animations.")
    print(f"     First Match: \"{parsed_discover[0]['title']}\" (Genres: {parsed_discover[0]['genres']})")
except Exception as e:
    print(f"[FAIL] Test 2: Mood Genre Discover - Error: {e}")
    errors += 1

# Test 3: Movie Search
try:
    search = tmdb_request("/search/movie", {"query": "Interstellar"})
    parsed_search = parse_tmdb_movies(search.get("results", []))
    print(f"[OK] Test 3: Movie Search (Query: \"Interstellar\") - Found {len(parsed_search)} results.")
    print(f"     First Result: \"{parsed_search[0]['title']}\" (Released: {parsed_search[0]['release_date']})")
except Exception as e:
    print(f"[FAIL] Test 3: Movie Search - Error: {e}")
    errors += 1

# Test 4: Similar Movies (Inception ID: 27205)
try:
    similar = tmdb_request("/movie/27205/similar")
    parsed_similar = parse_tmdb_movies(similar.get("results", []))
    print(f"[OK] Test 4: Similar Movies (Parent: Inception) - Retrieved {len(parsed_similar)} similar films.")
    print(f"     Similar Film Suggestion: \"{parsed_similar[0]['title']}\" - {parsed_similar[0]['overview'][:90]}...")
except Exception as e:
    print(f"[FAIL] Test 4: Similar Movies - Error: {e}")
    errors += 1

print("=" * 75)
print(f"DIAGNOSTICS COMPLETE. TOTAL INTEGRATION ERRORS: {errors}")
print("=" * 75)
