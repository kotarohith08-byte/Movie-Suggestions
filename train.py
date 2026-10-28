"""
train.py - ML Training & Evaluation Pipeline for CineMatch AI
============================================================
Trains:
1. Content-Based TF-IDF Vectorizer and precomputed nearest neighbor similarities.
2. TruncatedSVD Collaborative Filtering Matrix Factorization on MovieLens ratings.
3. Evaluates models on held-out test split (RMSE, MAE, Precision@K, Recall@K, NDCG@K).
4. Persists trained artifacts to models/ for instant runtime inference.
"""

import os
import sys
import json
import math
import joblib
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
from sklearn.model_selection import train_test_split

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MODELS_DIR = os.path.join(BASE_DIR, "models")

PROCESSED_MOVIES_CSV = os.path.join(DATA_DIR, "processed_movies.csv")
RATINGS_CSV = os.path.join(DATA_DIR, "ratings.csv")


def train_content_based_model(movies_df: pd.DataFrame):
    """
    Builds TF-IDF matrix from movie metadata (genres, tags, title tokens).
    Precomputes top 40 similar movies per title to ensure instant O(1) lookups
    at runtime without recalculating the similarity matrix on every request.
    """
    print("\n--- [1/3] Training Content-Based Recommendation Model ---")
    tfidf = TfidfVectorizer(
        stop_words="english",
        token_pattern=r"(?u)\b[\w-]+\b",
        ngram_range=(1, 2),
        max_features=10000,
        sublinear_tf=True
    )

    tfidf_matrix = tfidf.fit_transform(movies_df["metadata_text"].fillna(""))
    print(f"[OK] TF-IDF Matrix shape: {tfidf_matrix.shape}")

    # Map movieId <-> dataframe index
    movie_id_to_idx = {int(mid): idx for idx, mid in enumerate(movies_df["movieId"])}
    idx_to_movie_id = {idx: int(mid) for idx, mid in enumerate(movies_df["movieId"])}

    print("[*] Precomputing Top-40 content similarities per movie...")
    # Compute in chunks to be gentle with memory
    chunk_size = 1000
    n_movies = tfidf_matrix.shape[0]
    top_similarities = {}

    for start_idx in range(0, n_movies, chunk_size):
        end_idx = min(start_idx + chunk_size, n_movies)
        chunk_sim = cosine_similarity(tfidf_matrix[start_idx:end_idx], tfidf_matrix)

        for i, row in enumerate(chunk_sim):
            current_idx = start_idx + i
            current_movie_id = idx_to_movie_id[current_idx]

            # Argsort descending (excluding the movie itself at position current_idx)
            # Take top 40 candidates
            sim_scores = row
            # set self-similarity to -1
            sim_scores[current_idx] = -1.0
            top_k_indices = np.argpartition(sim_scores, -40)[-40:]
            top_k_indices = top_k_indices[np.argsort(-sim_scores[top_k_indices])]

            sim_list = []
            for neighbor_idx in top_k_indices:
                score = float(sim_scores[neighbor_idx])
                if score > 0.05:  # meaningful similarity threshold
                    sim_list.append((idx_to_movie_id[neighbor_idx], round(score, 4)))
            top_similarities[current_movie_id] = sim_list

    print(f"[OK] Precomputed similarities for {len(top_similarities)} movies.")

    # Save artifacts
    joblib.dump(tfidf, os.path.join(MODELS_DIR, "tfidf_vectorizer.joblib"))
    joblib.dump(tfidf_matrix, os.path.join(MODELS_DIR, "tfidf_matrix.joblib"))
    joblib.dump(top_similarities, os.path.join(MODELS_DIR, "content_top_sims.joblib"))
    joblib.dump(movie_id_to_idx, os.path.join(MODELS_DIR, "movie_id_to_idx.joblib"))
    joblib.dump(idx_to_movie_id, os.path.join(MODELS_DIR, "idx_to_movie_id.joblib"))
    print("[OK] Content-based artifacts saved to models/")


def train_and_evaluate_collaborative_filtering(movies_df: pd.DataFrame, ratings_df: pd.DataFrame):
    """
    Trains Matrix Factorization model (TruncatedSVD) on user-item ratings.
    Evaluates rating prediction accuracy (RMSE, MAE) and ranking performance
    (Precision@K, Recall@K, NDCG@K) on held-out test ratings.
    """
    print("\n--- [2/3] Training & Evaluating Collaborative Filtering (SVD) ---")

    # Filter ratings for valid movies present in processed_movies
    valid_movie_ids = set(movies_df["movieId"])
    ratings_clean = ratings_df[ratings_df["movieId"].isin(valid_movie_ids)].copy()

    # Split 80% train / 20% test strictly by rating interactions
    train_ratings, test_ratings = train_test_split(
        ratings_clean, test_size=0.2, random_state=42, stratify=None
    )
    print(f"[*] Train ratings: {len(train_ratings):,}, Test ratings: {len(test_ratings):,}")

    unique_users = sorted(ratings_clean["userId"].unique())
    unique_movies = sorted(valid_movie_ids)

    user_to_idx = {uid: idx for idx, uid in enumerate(unique_users)}
    idx_to_user = {idx: uid for idx, uid in enumerate(unique_users)}
    movie_to_matrix_idx = {mid: idx for idx, mid in enumerate(unique_movies)}
    matrix_idx_to_movie = {idx: mid for idx, mid in enumerate(unique_movies)}

    n_users = len(unique_users)
    n_items = len(unique_movies)

    # Compute per-user mean rating on TRAINING set for mean-centering (baseline)
    user_train_means = train_ratings.groupby("userId")["rating"].mean().to_dict()
    global_train_mean = float(train_ratings["rating"].mean())

    # Build sparse train user-item matrix with centered ratings
    row_indices = []
    col_indices = []
    values = []

    for _, row in train_ratings.iterrows():
        u = user_to_idx.get(int(row["userId"]))
        m = movie_to_matrix_idx.get(int(row["movieId"]))
        if u is not None and m is not None:
            u_mean = user_train_means.get(int(row["userId"]), global_train_mean)
            row_indices.append(u)
            col_indices.append(m)
            values.append(float(row["rating"]) - u_mean)

    train_sparse = csr_matrix((values, (row_indices, col_indices)), shape=(n_users, n_items))

    # Fit TruncatedSVD (Matrix Factorization)
    n_components = min(30, min(n_users, n_items) - 1)
    svd = TruncatedSVD(n_components=n_components, random_state=42)
    U_sigma = svd.fit_transform(train_sparse)  # shape: (n_users, n_components)
    Vt = svd.components_                       # shape: (n_components, n_items)

    explained_var = float(svd.explained_variance_ratio_.sum())
    print(f"[OK] SVD trained with {n_components} components. Explained variance: {explained_var*100:.2f}%")

    # Predict ratings on test set
    test_actuals = []
    test_predictions = []

    for _, row in test_ratings.iterrows():
        uid = int(row["userId"])
        mid = int(row["movieId"])
        actual_rating = float(row["rating"])

        if uid in user_to_idx and mid in movie_to_matrix_idx:
            u_idx = user_to_idx[uid]
            m_idx = movie_to_matrix_idx[mid]
            u_mean = user_train_means.get(uid, global_train_mean)
            # Reconstructed rating: u_mean + dot(U_sigma[u], Vt[:, m])
            pred_delta = np.dot(U_sigma[u_idx], Vt[:, m_idx])
            pred_rating = u_mean + pred_delta
            # Clip to valid rating range [0.5, 5.0]
            pred_rating = float(np.clip(pred_rating, 0.5, 5.0))
        else:
            # Fallback to movie mean or global mean
            pred_rating = global_train_mean

        test_actuals.append(actual_rating)
        test_predictions.append(pred_rating)

    test_actuals = np.array(test_actuals)
    test_predictions = np.array(test_predictions)

    # 1. Rating prediction metrics
    mae = float(np.mean(np.abs(test_actuals - test_predictions)))
    rmse = float(np.sqrt(np.mean((test_actuals - test_predictions) ** 2)))

    # 2. Ranking metrics: Precision@K, Recall@K, NDCG@K
    # Group test ratings by user
    print("[*] Evaluating Top-K Ranking performance (Precision@10, Recall@10, NDCG@10)...")
    K = 10
    user_test_groups = test_ratings.groupby("userId")

    precisions = []
    recalls = []
    ndcgs = []

    # Relevance threshold: rating >= 3.5 is relevant
    RELEVANCE_THRESHOLD = 3.5

    for uid, group in user_test_groups:
        if uid not in user_to_idx:
            continue
        u_idx = user_to_idx[uid]
        u_mean = user_train_means.get(uid, global_train_mean)

        test_movies = group["movieId"].values
        test_ratings_dict = dict(zip(group["movieId"].values, group["rating"].values))
        relevant_items = {mid for mid, r in test_ratings_dict.items() if r >= RELEVANCE_THRESHOLD}

        if len(relevant_items) == 0:
            continue

        # Predict score for each candidate movie in test set
        candidate_scores = []
        for mid in test_movies:
            if mid in movie_to_matrix_idx:
                m_idx = movie_to_matrix_idx[mid]
                score = u_mean + float(np.dot(U_sigma[u_idx], Vt[:, m_idx]))
            else:
                score = global_train_mean
            candidate_scores.append((mid, score))

        # Rank candidates by predicted score
        candidate_scores.sort(key=lambda x: x[1], reverse=True)
        top_k = candidate_scores[:K]
        top_k_mids = [m[0] for m in top_k]

        # Precision@K: fraction of recommended items that are relevant
        hits = len(set(top_k_mids) & relevant_items)
        precisions.append(hits / K)

        # Recall@K: fraction of all relevant items found in top-K
        recalls.append(hits / len(relevant_items))

        # NDCG@K
        dcg = 0.0
        for rank_idx, mid in enumerate(top_k_mids):
            actual_r = test_ratings_dict.get(mid, 0.0)
            rel = 1.0 if actual_r >= RELEVANCE_THRESHOLD else 0.0
            dcg += (2.0 ** rel - 1.0) / math.log2(rank_idx + 2)

        # Ideal DCG (sort true relevant items first)
        ideal_rels = sorted([1.0 if test_ratings_dict[mid] >= RELEVANCE_THRESHOLD else 0.0 for mid in test_movies], reverse=True)[:K]
        idcg = sum((2.0 ** rel - 1.0) / math.log2(idx + 2) for idx, rel in enumerate(ideal_rels))
        ndcg = (dcg / idcg) if idcg > 0 else 0.0
        ndcgs.append(ndcg)

    mean_precision = float(np.mean(precisions)) if precisions else 0.0
    mean_recall = float(np.mean(recalls)) if recalls else 0.0
    mean_ndcg = float(np.mean(ndcgs)) if ndcgs else 0.0

    print("\n================ ML EVALUATION METRICS ================")
    print(f"  Rating RMSE (Root Mean Squared Error) : {rmse:.4f}")
    print(f"  Rating MAE  (Mean Absolute Error)     : {mae:.4f}")
    print(f"  Ranking Precision@10                  : {mean_precision:.4f} ({mean_precision*100:.1f}%)")
    print(f"  Ranking Recall@10                     : {mean_recall:.4f} ({mean_recall*100:.1f}%)")
    print(f"  Ranking NDCG@10                       : {mean_ndcg:.4f}")
    print("=======================================================\n")

    # Fit final SVD on ALL ratings for deployment
    print("[*] Fitting production SVD on full dataset...")
    user_all_means = ratings_clean.groupby("userId")["rating"].mean().to_dict()
    global_all_mean = float(ratings_clean["rating"].mean())

    full_rows = []
    full_cols = []
    full_vals = []
    for _, row in ratings_clean.iterrows():
        u = user_to_idx[int(row["userId"])]
        m = movie_to_matrix_idx[int(row["movieId"])]
        u_mean = user_all_means.get(int(row["userId"]), global_all_mean)
        full_rows.append(u)
        full_cols.append(m)
        full_vals.append(float(row["rating"]) - u_mean)

    full_sparse = csr_matrix((full_vals, (full_rows, full_cols)), shape=(n_users, n_items))
    final_svd = TruncatedSVD(n_components=n_components, random_state=42)
    final_U_sigma = final_svd.fit_transform(full_sparse)
    final_Vt = final_svd.components_

    # Save artifacts
    cf_artifacts = {
        "U_sigma": final_U_sigma,
        "Vt": final_Vt,
        "user_to_idx": user_to_idx,
        "movie_to_matrix_idx": movie_to_matrix_idx,
        "matrix_idx_to_movie": matrix_idx_to_movie,
        "user_means": user_all_means,
        "global_mean": global_all_mean,
        "n_components": n_components,
    }
    joblib.dump(cf_artifacts, os.path.join(MODELS_DIR, "cf_svd_model.joblib"))

    # Save evaluation metrics
    metrics_data = {
        "algorithm": "TruncatedSVD Matrix Factorization",
        "latent_factors": n_components,
        "rmse": round(rmse, 4),
        "mae": round(mae, 4),
        "precision_at_10": round(mean_precision, 4),
        "recall_at_10": round(mean_recall, 4),
        "ndcg_at_10": round(mean_ndcg, 4),
        "test_ratings_evaluated": len(test_ratings),
        "train_ratings_used": len(train_ratings),
        "relevance_threshold": RELEVANCE_THRESHOLD,
        "comparison": {
            "content_based": {
                "algorithm": "TF-IDF + Cosine Similarity",
                "features": "Genres, Tags, Title N-grams",
                "strengths": "Zero cold-start for new items, highly interpretable explanations",
                "weaknesses": "Cannot capture cross-user serendipity without ratings"
            },
            "collaborative_filtering": {
                "algorithm": "Latent Factor Matrix Factorization (SVD)",
                "features": "User-Item Interaction Matrix",
                "strengths": "Discovers latent taste clusters and cross-genre recommendations",
                "weaknesses": "Cold-start for new users/items with few or zero ratings"
            },
            "hybrid": {
                "algorithm": "Dynamic Weighted Ensemble (Content + SVD + Bayesian Quality)",
                "strengths": "Best of both worlds: handles cold-start gracefully while providing serendipitous recommendations",
                "status": "Active Default Engine"
            }
        }
    }

    metrics_path = os.path.join(MODELS_DIR, "evaluation_metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics_data, f, indent=2)
    print(f"[OK] Evaluation metrics saved to {metrics_path}")


def main():
    os.makedirs(MODELS_DIR, exist_ok=True)
    if not os.path.exists(PROCESSED_MOVIES_CSV) or not os.path.exists(RATINGS_CSV):
        print("[!] Preprocessed data missing. Running get_data.py first...")
        from get_data import main as get_data_main
        get_data_main()

    movies_df = pd.read_csv(PROCESSED_MOVIES_CSV)
    ratings_df = pd.read_csv(RATINGS_CSV)

    train_content_based_model(movies_df)
    train_and_evaluate_collaborative_filtering(movies_df, ratings_df)
    print("\n[SUCCESS] Model training and evaluation complete!")


if __name__ == "__main__":
    main()
