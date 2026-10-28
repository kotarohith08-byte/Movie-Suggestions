"""
test_cinematch.py - Comprehensive Automated Test Suite for CineMatch AI
========================================================================
Covers:
- Dataset integrity and preprocessing
- Content-based filtering (TF-IDF & Cosine Similarity)
- Collaborative filtering (TruncatedSVD Matrix Factorization)
- Hybrid recommendation engine & cold-start scenarios
- SQLite database persistence & rating bounds
- Flask REST APIs, UI routing, error handling, and dynamic SVG posters
"""

import os
import sys
import unittest
import json
import sqlite3

# Add parent directory to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from get_data import extract_year_and_clean_title, PROCESSED_MOVIES_CSV, RATINGS_CSV
from recommender import get_recommender
import database as db
from app import app


class TestDatasetAndPreprocessing(unittest.TestCase):
    """Tests dataset ingestion, year parsing, and preprocessed metadata."""

    def test_year_extraction(self):
        clean_title, year = extract_year_and_clean_title("Toy Story (1995)")
        self.assertEqual(clean_title, "Toy Story")
        self.assertEqual(year, 1995)

        clean_title, year = extract_year_and_clean_title("The Matrix (1999)")
        self.assertEqual(clean_title, "The Matrix")
        self.assertEqual(year, 1999)

        clean_title, year = extract_year_and_clean_title("Title Without Year")
        self.assertEqual(clean_title, "Title Without Year")
        self.assertIsNone(year)

    def test_processed_movies_file_exists(self):
        self.assertTrue(os.path.exists(PROCESSED_MOVIES_CSV), "processed_movies.csv must exist")

    def test_ratings_file_exists(self):
        self.assertTrue(os.path.exists(RATINGS_CSV), "ratings.csv must exist")


class TestDatabasePersistence(unittest.TestCase):
    """Tests SQLite database persistence, parameterized queries, and edge cases."""

    def setUp(self):
        db.init_db()
        self.test_user = "test_user_unit_test"

    def tearDown(self):
        # Clean up test user ratings
        with db.get_db_connection() as conn:
            conn.execute("DELETE FROM user_ratings WHERE user_id = ?", (self.test_user,))
            conn.execute("DELETE FROM user_preferences WHERE user_id = ?", (self.test_user,))
            conn.commit()

    def test_save_and_retrieve_rating(self):
        # Insert rating
        db.save_rating(self.test_user, 1, 4.5)
        user_ratings = db.get_user_ratings(self.test_user)
        self.assertEqual(len(user_ratings), 1)
        self.assertEqual(user_ratings[0]["movie_id"], 1)
        self.assertEqual(user_ratings[0]["rating"], 4.5)

        # Update rating
        db.save_rating(self.test_user, 1, 5.0)
        updated_ratings = db.get_user_ratings(self.test_user)
        self.assertEqual(len(updated_ratings), 1)
        self.assertEqual(updated_ratings[0]["rating"], 5.0)

    def test_invalid_rating_bounds(self):
        with self.assertRaises(ValueError):
            db.save_rating(self.test_user, 1, 6.0)

        with self.assertRaises(ValueError):
            db.save_rating(self.test_user, 1, 0.2)

    def test_user_preferences_persistence(self):
        pref_genres = ["Sci-Fi", "Action", "Animation"]
        db.save_user_preferences(self.test_user, pref_genres)
        loaded = db.get_user_preferences(self.test_user)
        self.assertEqual(loaded, pref_genres)


class TestRecommendationAlgorithms(unittest.TestCase):
    """Tests ML recommendation algorithms, search, and cold-start fallback."""

    @classmethod
    def setUpClass(cls):
        cls.rec = get_recommender()

    def test_movie_details_retrieval(self):
        movie = self.rec.get_movie_details(1)  # Toy Story
        self.assertIsNotNone(movie)
        self.assertIn("clean_title", movie)
        self.assertEqual(movie["clean_title"], "Toy Story")
        self.assertIn("Adventure", movie["genres"])

    def test_search_partial_case_insensitive(self):
        # Search 'matrix'
        results = self.rec.search_movies("matrix")
        self.assertGreater(len(results), 0)
        titles = [r["clean_title"].lower() for r in results]
        self.assertTrue(any("matrix" in t for t in titles))

    def test_content_based_recommendations(self):
        # Toy Story (1) should recommend other animated/family titles
        similar = self.rec.get_content_based_recommendations(1, top_n=5)
        self.assertEqual(len(similar), 5)
        for item in similar:
            self.assertIn("match_percentage", item)
            self.assertGreater(item["match_percentage"], 0)

    def test_collaborative_filtering_recommendations(self):
        # User 1 (MovieLens existing user)
        cf_recs = self.rec.get_collaborative_recommendations("1", top_n=5)
        self.assertGreaterEqual(len(cf_recs), 3)
        for item in cf_recs:
            self.assertIn("predicted_rating", item)
            self.assertGreaterEqual(item["predicted_rating"], 1.0)
            self.assertLessEqual(item["predicted_rating"], 5.0)

    def test_hybrid_cold_start_pure(self):
        # 0 ratings, 0 genres chosen -> Should return top-rated / popular
        recs = self.rec.get_hybrid_recommendations(
            user_id="brand_new_cold_user",
            user_local_ratings=[],
            preferred_genres=[],
            top_n=6
        )
        self.assertEqual(len(recs), 6)
        for item in recs:
            self.assertIn("weighted_score", item)

    def test_hybrid_cold_start_with_genres(self):
        # 0 ratings, but selected Sci-Fi -> Should prioritize Sci-Fi
        recs = self.rec.get_hybrid_recommendations(
            user_id="genre_only_user",
            user_local_ratings=[],
            preferred_genres=["Sci-Fi"],
            top_n=5
        )
        self.assertEqual(len(recs), 5)
        # Verify Sci-Fi presence
        has_scifi = any("Sci-Fi" in item["genres"] for item in recs)
        self.assertTrue(has_scifi, "Recommendations should reflect preferred genre")

    def test_hybrid_active_user(self):
        # Active user with ratings -> Should exclude rated items and score hybridly
        test_ratings = [
            {"movie_id": 1, "rating": 5.0},   # Toy Story
            {"movie_id": 260, "rating": 5.0}  # Star Wars
        ]
        recs = self.rec.get_hybrid_recommendations(
            user_id="active_test_user",
            user_local_ratings=test_ratings,
            preferred_genres=["Adventure"],
            top_n=5
        )
        self.assertEqual(len(recs), 5)
        rec_ids = [m["movieId"] for m in recs]
        self.assertNotIn(1, rec_ids, "Should not recommend already-rated movie #1")
        self.assertNotIn(260, rec_ids, "Should not recommend already-rated movie #260")


class TestFlaskBackendAPI(unittest.TestCase):
    """Tests Flask endpoints, HTTP status codes, JSON responses, and SVG posters."""

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def test_health_check(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "healthy")
        self.assertGreater(data["movies_loaded"], 5000)

    def test_homepage_route(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"CineMatch", res.data)
        self.assertIn(b"Discover Your Next", res.data)

    def test_search_endpoint(self):
        res = self.client.get("/search?q=Godfather")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Godfather", res.data)

    def test_movie_detail_valid(self):
        res = self.client.get("/movie/1")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Toy Story", res.data)

    def test_movie_detail_not_found(self):
        res = self.client.get("/movie/99999999")
        self.assertEqual(res.status_code, 404)

    def test_dynamic_svg_poster(self):
        res = self.client.get("/poster/1?fallback=svg")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content_type, "image/svg+xml; charset=utf-8")
        self.assertIn(b"<svg", res.data)
        self.assertIn(b"Toy Story", res.data)

    def test_authentic_poster_redirect(self):
        res = self.client.get("/poster/1")
        # For Toy Story (1), it should redirect to the authentic poster or return 200/302
        self.assertIn(res.status_code, [200, 302])
        if res.status_code == 302:
            loc = res.headers.get("Location", "")
            self.assertTrue("tmdb.org" in loc or "wikimedia.org" in loc)

    def test_api_recommendations_hybrid(self):
        res = self.client.get("/api/recommendations?algorithm=hybrid&top_n=6")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(len(data["recommendations"]), 6)

    def test_rate_movie_api_success(self):
        payload = {"movie_id": 1, "rating": 4.5}
        res = self.client.post("/rate", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")

    def test_rate_movie_api_invalid(self):
        payload = {"movie_id": 1, "rating": 9.0}  # Invalid rating > 5.0
        res = self.client.post("/rate", json=payload)
        self.assertEqual(res.status_code, 400)

    def test_api_genres(self):
        res = self.client.get("/api/genres")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("genres", data)
        self.assertGreater(len(data["genres"]), 10)

    def test_api_metrics(self):
        res = self.client.get("/api/metrics")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        metrics = data["metrics"]
        self.assertIn("rmse", metrics)
        self.assertIn("mae", metrics)
        self.assertIn("precision_at_10", metrics)


if __name__ == "__main__":
    unittest.main(verbosity=2)
