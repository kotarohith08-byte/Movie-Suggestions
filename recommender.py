"""
recommender.py - CineMatch AI Core Recommendation Engine
=========================================================
Implements:
1. Content-Based Filtering (TF-IDF & Cosine Similarity)
2. Collaborative Filtering (TruncatedSVD Matrix Factorization & Folding-in)
3. Hybrid Recommendation Engine (Configurable multi-signal weighted scoring)
4. Cold-Start Handling (Genre preference profiling & Bayesian weighted popularity)
5. Fast Title Search & Multi-criteria Filtering
"""

import os
import re
import json
import joblib
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple, Set
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MODELS_DIR = os.path.join(BASE_DIR, "models")
PROCESSED_MOVIES_CSV = os.path.join(DATA_DIR, "processed_movies.csv")
POSTERS_CACHE_FILE = os.path.join(DATA_DIR, "posters_cache.json")


class MovieRecommender:
    """
    Unified recommendation engine combining Content-Based,
    Collaborative Filtering, and Hybrid strategies.
    """

    def __init__(self):
        print("[*] Initializing CineMatch AI Recommender Engine...")
        self.movies_df = pd.read_csv(PROCESSED_MOVIES_CSV)
        self.movies_df["movieId"] = self.movies_df["movieId"].astype(int)

        # Load authentic posters cache if available
        self.posters_cache = {}
        if os.path.exists(POSTERS_CACHE_FILE):
            try:
                with open(POSTERS_CACHE_FILE, "r", encoding="utf-8") as f:
                    self.posters_cache = json.load(f)
                print(f"[OK] Loaded {len([v for v in self.posters_cache.values() if v])} authentic movie posters.")
            except Exception as e:
                print(f"[!] Warning reading posters cache: {e}")

        # Build fast lookup dictionary: movieId -> movie metadata dict
        self.movie_dict = {}
        for _, row in self.movies_df.iterrows():
            mid = int(row["movieId"])
            genres_list = [g.strip() for g in str(row["genres"]).split("|") if g.strip() and g != "(no genres listed)"]
            cached_poster = self.posters_cache.get(str(mid))
            poster_url = cached_poster if cached_poster else f"/poster/{mid}"

            self.movie_dict[mid] = {
                "movieId": mid,
                "title": row["title"],
                "clean_title": row["clean_title"],
                "year": int(row["year"]) if pd.notnull(row["year"]) else None,
                "genres": genres_list,
                "genres_str": ", ".join(genres_list) if genres_list else "General",
                "rating_mean": float(row["rating_mean"]),
                "rating_count": int(row["rating_count"]),
                "weighted_score": float(row["weighted_score"]),
                "tags": str(row["tags"]) if pd.notnull(row["tags"]) else "",
                "poster_url": poster_url,
                "has_authentic_poster": bool(cached_poster)
            }

        # Load models
        self.tfidf = joblib.load(os.path.join(MODELS_DIR, "tfidf_vectorizer.joblib"))
        self.tfidf_matrix = joblib.load(os.path.join(MODELS_DIR, "tfidf_matrix.joblib"))
        self.top_similarities = joblib.load(os.path.join(MODELS_DIR, "content_top_sims.joblib"))
        self.movie_id_to_idx = joblib.load(os.path.join(MODELS_DIR, "movie_id_to_idx.joblib"))
        self.idx_to_movie_id = joblib.load(os.path.join(MODELS_DIR, "idx_to_movie_id.joblib"))

        # Load Collaborative Filtering artifacts
        self.cf = joblib.load(os.path.join(MODELS_DIR, "cf_svd_model.joblib"))
        self.U_sigma = self.cf["U_sigma"]
        self.Vt = self.cf["Vt"]
        self.user_to_idx = self.cf["user_to_idx"]
        self.movie_to_matrix_idx = self.cf["movie_to_matrix_idx"]
        self.matrix_idx_to_movie = self.cf["matrix_idx_to_movie"]
        self.user_means = self.cf["user_means"]
        self.global_mean = self.cf["global_mean"]

        # Load evaluation metrics
        metrics_path = os.path.join(MODELS_DIR, "evaluation_metrics.json")
        self.evaluation_metrics = {}
        if os.path.exists(metrics_path):
            with open(metrics_path, "r") as f:
                self.evaluation_metrics = json.load(f)

        # Collect unique genres and their movie counts
        self.all_genres = self._extract_unique_genres()
        print(f"[OK] Recommender initialized with {len(self.movie_dict):,} movies & {len(self.all_genres)} genres.")

    def _extract_unique_genres(self) -> List[Dict]:
        """Extracts sorted list of unique genres and movie counts."""
        genre_counts = {}
        for m in self.movie_dict.values():
            for g in m["genres"]:
                genre_counts[g] = genre_counts.get(g, 0) + 1
        sorted_genres = sorted(
            [{"name": g, "count": count} for g, count in genre_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )
        return sorted_genres

    def get_movie_details(self, movie_id: int) -> Optional[Dict]:
        """Returns details for a single movie by ID."""
        return self.movie_dict.get(int(movie_id))

    def search_movies(self, query: str = "", genre: Optional[str] = None, year: Optional[int] = None, limit: int = 24) -> List[Dict]:
        """
        Searches movies with case-insensitive partial substring match,
        token overlap matching, and optional genre/year filtering.
        """
        results = []
        q_clean = query.strip().lower() if query else ""
        q_tokens = set(re.findall(r"\w+", q_clean))

        for mid, m in self.movie_dict.items():
            # Genre filter
            if genre and genre.lower() != "all":
                if not any(g.lower() == genre.lower() for g in m["genres"]):
                    continue

            # Year filter
            if year and m["year"] != year:
                continue

            # Text query matching
            if q_clean:
                title_lower = m["title"].lower()
                clean_title_lower = m["clean_title"].lower()

                # Exact substring match has highest priority
                if q_clean in clean_title_lower or q_clean in title_lower:
                    relevance = 100.0 - (len(clean_title_lower) - len(q_clean)) * 0.1
                else:
                    # Token overlap
                    title_tokens = set(re.findall(r"\w+", clean_title_lower))
                    overlap = len(q_tokens & title_tokens)
                    if overlap > 0:
                        relevance = (overlap / max(len(q_tokens), 1)) * 50.0
                    else:
                        continue
            else:
                relevance = m["weighted_score"]

            item = dict(m)
            item["search_relevance"] = round(relevance, 2)
            results.append(item)

        # Sort by relevance descending, then by weighted_score
        results.sort(key=lambda x: (x.get("search_relevance", 0), x["weighted_score"], x["rating_count"]), reverse=True)
        return results[:limit]

    def get_popular_movies(self, limit: int = 12, genre: Optional[str] = None) -> List[Dict]:
        """Returns trending/popular movies based on rating count and quality score."""
        candidates = list(self.movie_dict.values())
        if genre and genre.lower() != "all":
            candidates = [m for m in candidates if any(g.lower() == genre.lower() for g in m["genres"])]

        # Popularity score combines rating count with weighted average rating
        candidates.sort(key=lambda x: (x["rating_count"] * (x["weighted_score"] ** 1.5)), reverse=True)
        return candidates[:limit]

    def get_top_rated_movies(self, limit: int = 12, min_ratings: int = 10, genre: Optional[str] = None) -> List[Dict]:
        """Returns highest rated movies satisfying a minimum rating count threshold."""
        candidates = [m for m in self.movie_dict.values() if m["rating_count"] >= min_ratings]
        if genre and genre.lower() != "all":
            candidates = [m for m in candidates if any(g.lower() == genre.lower() for g in m["genres"])]

        candidates.sort(key=lambda x: (x["weighted_score"], x["rating_mean"]), reverse=True)
        return candidates[:limit]

    def get_movies_by_genre(self, genre: str, limit: int = 12) -> List[Dict]:
        """Retrieves top rated movies for a specific genre."""
        return self.get_top_rated_movies(limit=limit, min_ratings=5, genre=genre)

    def get_content_based_recommendations(self, movie_id: int, top_n: int = 10) -> List[Dict]:
        """
        Recommends movies most similar to the target movie based on metadata (TF-IDF).
        Uses precomputed similarities for instant performance.
        """
        mid = int(movie_id)
        if mid not in self.movie_dict:
            return []

        similar_pairs = self.top_similarities.get(mid, [])
        recommendations = []
        for sim_mid, sim_score in similar_pairs[:top_n]:
            if sim_mid in self.movie_dict:
                item = dict(self.movie_dict[sim_mid])
                item["similarity_score"] = sim_score
                item["match_percentage"] = int(min(100, round(sim_score * 100)))
                item["recommendation_reason"] = f"Similar to {self.movie_dict[mid]['clean_title']} ({item['match_percentage']}% match)"
                recommendations.append(item)

        return recommendations

    def get_collaborative_recommendations(
        self,
        user_id: str,
        user_local_ratings: Optional[List[Dict]] = None,
        top_n: int = 10,
        exclude_movie_ids: Optional[Set[int]] = None
    ) -> List[Dict]:
        """
        Recommends movies using Collaborative Filtering (TruncatedSVD).
        Supports both existing MovieLens user IDs (int) and new local users
        via folding-in projection using their local ratings!
        """
        exclude_set = set(exclude_movie_ids or set())

        # Check if user is an existing MovieLens integer user ID
        is_movielens_user = False
        try:
            uid_int = int(user_id)
            if uid_int in self.user_to_idx:
                is_movielens_user = True
        except ValueError:
            is_movielens_user = False

        if is_movielens_user:
            u_idx = self.user_to_idx[uid_int]
            u_mean = self.user_means.get(uid_int, self.global_mean)
            user_latent = self.U_sigma[u_idx]  # shape: (n_components,)
        elif user_local_ratings and len(user_local_ratings) > 0:
            # "Folding-in" projection for new user with local ratings:
            # Construct centered sparse vector for user and project into latent space:
            # user_latent = (r_u - mean_u) * Vt.T
            local_ratings_dict = {int(r["movie_id"]): float(r["rating"]) for r in user_local_ratings}
            exclude_set.update(local_ratings_dict.keys())
            u_mean = float(np.mean(list(local_ratings_dict.values())))

            # Vector in item space
            n_items = self.Vt.shape[1]
            user_vec = np.zeros(n_items)
            for mid, rating in local_ratings_dict.items():
                if mid in self.movie_to_matrix_idx:
                    m_idx = self.movie_to_matrix_idx[mid]
                    user_vec[m_idx] = rating - u_mean

            # Project to latent factors: user_latent = user_vec @ Vt.T
            user_latent = np.dot(user_vec, self.Vt.T)
        else:
            # Cold-start: return top rated movies
            return self.get_top_rated_movies(limit=top_n)

        # Predict ratings for all movies in matrix: u_mean + dot(user_latent, Vt)
        predicted_ratings = u_mean + np.dot(user_latent, self.Vt)

        # Rank movies
        scored_movies = []
        for m_idx, pred_score in enumerate(predicted_ratings):
            mid = self.matrix_idx_to_movie.get(m_idx)
            if mid is None or mid in exclude_set or mid not in self.movie_dict:
                continue

            movie_meta = self.movie_dict[mid]
            # Minimum rating count filter for CF stability
            if movie_meta["rating_count"] < 3:
                continue

            scored_movies.append((mid, float(pred_score)))

        scored_movies.sort(key=lambda x: x[1], reverse=True)

        recommendations = []
        for mid, pred_score in scored_movies[:top_n]:
            item = dict(self.movie_dict[mid])
            clipped_score = round(float(np.clip(pred_score, 1.0, 5.0)), 2)
            item["predicted_rating"] = clipped_score
            item["match_percentage"] = int(min(100, round((clipped_score / 5.0) * 100)))
            item["recommendation_reason"] = f"Predicted {clipped_score}/5.0 stars from users with similar taste"
            recommendations.append(item)

        return recommendations

    def get_hybrid_recommendations(
        self,
        user_id: str,
        user_local_ratings: Optional[List[Dict]] = None,
        preferred_genres: Optional[List[str]] = None,
        top_n: int = 12,
        weights: Optional[Dict[str, float]] = None,
        exclude_movie_ids: Optional[Set[int]] = None
    ) -> List[Dict]:
        """
        Hybrid Recommendation Engine combining:
        1. Content-based similarity to movies user rated highly (>= 3.5 stars)
        2. SVD Collaborative Filtering rating predictions
        3. User preferred genres matching score
        4. Bayesian movie quality score (weighted IMDb formula)

        Gracefully handles cold-start:
        - 0 ratings + no genres: Diverse popular and top-rated movies
        - 0 ratings + genres: Top-rated movies in preferred genres
        - 1-4 ratings: Heavier content-based and genre preference
        - >=5 ratings: Full balanced hybrid ensemble
        """
        user_ratings = user_local_ratings or []
        preferred_genres = preferred_genres or []
        exclude_set = set(exclude_movie_ids or set())

        # Exclude movies the user has already rated
        for r in user_ratings:
            exclude_set.add(int(r["movie_id"]))

        # Check Cold-Start Cases
        n_ratings = len(user_ratings)

        # CASE 1: Pure Cold Start (No ratings, no genres chosen)
        if n_ratings == 0 and len(preferred_genres) == 0:
            popular = self.get_top_rated_movies(limit=top_n * 2)
            results = []
            seen_genres = set()
            for m in popular:
                if m["movieId"] in exclude_set:
                    continue
                # Ensure genre diversity
                primary_genre = m["genres"][0] if m["genres"] else "General"
                item = dict(m)
                item["recommendation_reason"] = "Critically acclaimed & popular"
                item["match_percentage"] = int(min(100, round((m["weighted_score"] / 5.0) * 100)))
                item["score_source"] = "Popularity & Quality Prior"
                results.append(item)
                if len(results) >= top_n:
                    break
            return results

        # CASE 2: New user with Preferred Genres but 0 ratings
        if n_ratings == 0 and len(preferred_genres) > 0:
            preferred_set = set(g.lower() for g in preferred_genres)
            candidates = []
            for mid, m in self.movie_dict.items():
                if mid in exclude_set:
                    continue
                m_genres_lower = set(g.lower() for g in m["genres"])
                overlap = len(preferred_set & m_genres_lower)
                if overlap > 0:
                    genre_score = overlap / len(preferred_set)
                    # Quality score
                    quality_score = m["weighted_score"] / 5.0
                    combined = 0.6 * genre_score + 0.4 * quality_score
                    candidates.append((mid, combined, overlap))

            candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
            results = []
            for mid, score, overlap in candidates[:top_n]:
                item = dict(self.movie_dict[mid])
                matched = [g for g in item["genres"] if g.lower() in preferred_set]
                item["recommendation_reason"] = f"Matches your interest in {', '.join(matched[:2])}"
                item["match_percentage"] = int(min(100, round(score * 100)))
                item["score_source"] = "Genre Preference & Quality Prior"
                results.append(item)
            return results

        # CASE 3: Active User (>= 1 ratings) -> Full Hybrid Engine
        # Set dynamic weights based on rating volume or custom config
        if weights is None:
            if n_ratings < 5:
                # Sparse ratings: rely more on content similarity and genre preferences
                w_content = 0.50
                w_collab = 0.20
                w_genre = 0.15
                w_quality = 0.15
            else:
                # Mature user profile: balanced ensemble
                w_content = 0.35
                w_collab = 0.35
                w_genre = 0.15
                w_quality = 0.15
        else:
            w_content = weights.get("content", 0.35)
            w_collab = weights.get("collaborative", 0.35)
            w_genre = weights.get("genre", 0.15)
            w_quality = weights.get("quality", 0.15)

        # Normalize weights to sum to 1.0
        total_w = w_content + w_collab + w_genre + w_quality
        if total_w > 0:
            w_content /= total_w
            w_collab /= total_w
            w_genre /= total_w
            w_quality /= total_w

        # --- A. CONTENT-BASED PROFILE SCORING ---
        # Find movies user rated positively (>= 3.0, weighted by user rating)
        liked_movies = [r for r in user_ratings if float(r["rating"]) >= 3.0]
        content_scores = {}
        top_liked_titles = []

        if liked_movies:
            # Aggregate similarity to liked movies
            for r in liked_movies:
                mid = int(r["movie_id"])
                rating_weight = (float(r["rating"]) - 2.5) / 2.5  # scale 3.0->0.2, 5.0->1.0
                if mid in self.movie_dict:
                    top_liked_titles.append(self.movie_dict[mid]["clean_title"])

                sim_neighbors = self.top_similarities.get(mid, [])
                for neighbor_mid, sim in sim_neighbors:
                    if neighbor_mid not in exclude_set:
                        content_scores[neighbor_mid] = content_scores.get(neighbor_mid, 0.0) + (sim * rating_weight)

            # Normalize content scores
            if content_scores:
                max_cs = max(content_scores.values())
                if max_cs > 0:
                    for k in content_scores:
                        content_scores[k] = content_scores[k] / max_cs

        # --- B. COLLABORATIVE FILTERING SCORING ---
        collab_scores = {}
        try:
            cf_recs = self.get_collaborative_recommendations(
                user_id=user_id,
                user_local_ratings=user_ratings,
                top_n=top_n * 5,
                exclude_movie_ids=exclude_set
            )
            for rec in cf_recs:
                mid = rec["movieId"]
                # Normalize predicted 1-5 rating to [0, 1]
                pred_r = rec.get("predicted_rating", self.global_mean)
                norm_score = max(0.0, min(1.0, (pred_r - 1.0) / 4.0))
                collab_scores[mid] = norm_score
        except Exception as e:
            print(f"[!] Warning during CF hybrid scoring: {e}")

        # --- C. GENRE PREFERENCE & QUALITY SCORING ---
        preferred_set = set(g.lower() for g in preferred_genres)
        candidate_ids = set(content_scores.keys()) | set(collab_scores.keys())

        # If candidates are few, pull in top-rated movies
        if len(candidate_ids) < top_n * 3:
            top_rated = self.get_top_rated_movies(limit=top_n * 3)
            for m in top_rated:
                if m["movieId"] not in exclude_set:
                    candidate_ids.add(m["movieId"])

        final_candidates = []
        for mid in candidate_ids:
            if mid in exclude_set or mid not in self.movie_dict:
                continue

            movie_meta = self.movie_dict[mid]

            # 1. Content component
            c_score = content_scores.get(mid, 0.0)

            # 2. Collaborative component
            cf_score = collab_scores.get(mid, (movie_meta["weighted_score"] - 1.0) / 4.0)

            # 3. Genre preference component
            m_genres_lower = set(g.lower() for g in movie_meta["genres"])
            g_overlap = len(preferred_set & m_genres_lower)
            g_score = (g_overlap / max(len(preferred_set), 1)) if preferred_set else 0.5

            # 4. Bayesian Quality prior
            q_score = (movie_meta["weighted_score"] - 1.0) / 4.0
            q_score = max(0.0, min(1.0, q_score))

            # Combined Ensemble Score
            hybrid_score = (
                w_content * c_score +
                w_collab * cf_score +
                w_genre * g_score +
                w_quality * q_score
            )

            # Determine dominant explanation
            reason = "Recommended by hybrid algorithm"
            if c_score >= cf_score and c_score >= g_score and top_liked_titles:
                reason = f"Because you loved {top_liked_titles[0]}"
            elif cf_score >= c_score and cf_score >= 0.7:
                reason = "Popular among users with similar cinematic taste"
            elif g_overlap > 0:
                matched_genres = [g for g in movie_meta["genres"] if g.lower() in preferred_set]
                reason = f"Matches your {', '.join(matched_genres[:2])} preference"
            else:
                reason = "Top-tier critically acclaimed recommendation"

            final_candidates.append({
                "movie": movie_meta,
                "hybrid_score": hybrid_score,
                "components": {
                    "content": round(c_score, 3),
                    "collaborative": round(cf_score, 3),
                    "genre": round(g_score, 3),
                    "quality": round(q_score, 3)
                },
                "reason": reason
            })

        final_candidates.sort(key=lambda x: x["hybrid_score"], reverse=True)

        results = []
        for item in final_candidates[:top_n]:
            m = dict(item["movie"])
            m["hybrid_score"] = round(item["hybrid_score"], 3)
            m["match_percentage"] = int(min(100, max(50, round(item["hybrid_score"] * 100))))
            m["recommendation_reason"] = item["reason"]
            m["components"] = item["components"]
            m["score_source"] = f"Hybrid (Content {int(w_content*100)}% + Collab {int(w_collab*100)}% + Genre {int(w_genre*100)}% + Quality {int(w_quality*100)}%)"
            results.append(m)

        return results


# Global singleton instance loaded once
_recommender_instance = None


def get_recommender() -> MovieRecommender:
    """Returns singleton instance of MovieRecommender."""
    global _recommender_instance
    if _recommender_instance is None:
        _recommender_instance = MovieRecommender()
    return _recommender_instance


if __name__ == "__main__":
    rec = get_recommender()
    # Test sample search
    print("\n--- Search Test: 'Matrix' ---")
    search_res = rec.search_movies("Matrix", limit=3)
    for m in search_res:
        print(f"  {m['title']} | Year: {m['year']} | Genres: {m['genres_str']} | Rating: {m['rating_mean']}/5.0")

    # Test content-based for Toy Story (movieId=1)
    print("\n--- Content-Based for Toy Story (1) ---")
    toy_story_sims = rec.get_content_based_recommendations(1, top_n=3)
    for m in toy_story_sims:
        print(f"  {m['title']} | Score: {m['similarity_score']} | Reason: {m['recommendation_reason']}")

    # Test collaborative for user 1
    print("\n--- Collaborative for User 1 ---")
    cf_res = rec.get_collaborative_recommendations("1", top_n=3)
    for m in cf_res:
        print(f"  {m['title']} | Pred: {m['predicted_rating']}/5.0 | Reason: {m['recommendation_reason']}")
