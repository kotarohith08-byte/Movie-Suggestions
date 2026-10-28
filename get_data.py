"""
get_data.py - MovieLens Dataset Ingestion & Preprocessing for CineMatch AI
========================================================================
Downloads, validates, cleans, and pre-processes MovieLens data (ml-latest-small).
Handles missing values, parses release years, aggregates tags, and computes
baseline movie statistics (vote count, mean rating, Bayesian weighted score).
"""

import os
import sys
import ssl
import json
import zipfile
import re
import urllib.request
import pandas as pd
import numpy as np

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
GROUPLENS_URL = "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip"
ZIP_PATH = os.path.join(DATA_DIR, "ml-latest-small.zip")

MOVIES_CSV = os.path.join(DATA_DIR, "movies.csv")
RATINGS_CSV = os.path.join(DATA_DIR, "ratings.csv")
TAGS_CSV = os.path.join(DATA_DIR, "tags.csv")
LINKS_CSV = os.path.join(DATA_DIR, "links.csv")
PROCESSED_MOVIES_CSV = os.path.join(DATA_DIR, "processed_movies.csv")


def extract_year_and_clean_title(title_raw: str):
    """
    Extracts the 4-digit release year from a MovieLens title string like 'Toy Story (1995)'
    and returns (clean_title, year).
    """
    if not isinstance(title_raw, str):
        return str(title_raw), None
    match = re.search(r"\((\d{4})\)\s*$", title_raw.strip())
    if match:
        year = int(match.group(1))
        clean_title = re.sub(r"\s*\(\d{4}\)\s*$", "", title_raw).strip()
        return clean_title, year
    return title_raw.strip(), None


def download_movielens_dataset(force: bool = False) -> bool:
    """
    Downloads and extracts the GroupLens MovieLens latest-small dataset.
    Falls back gracefully if network is unavailable or already downloaded.
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    if not force and os.path.exists(MOVIES_CSV) and os.path.exists(RATINGS_CSV):
        print(f"[OK] MovieLens dataset already exists in: {DATA_DIR}")
        return True

    print(f"[*] Downloading MovieLens latest-small dataset from:\n    {GROUPLENS_URL}")
    try:
        # Create unverified SSL context to bypass potential Windows cert store issues
        ssl_ctx = ssl._create_unverified_context()
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl_ctx))
        urllib.request.install_opener(opener)

        # Download with progress indicator
        def reporthook(blocknum, blocksize, totalsize):
            read_so_far = blocknum * blocksize
            if totalsize > 0:
                percent = read_so_far * 1e2 / totalsize
                s = f"\r--> Downloading: {percent:5.1f}% ({read_so_far / 1024:.0f} KB / {totalsize / 1024:.0f} KB)"
                sys.stdout.write(s)
                sys.stdout.flush()

        urllib.request.urlretrieve(GROUPLENS_URL, ZIP_PATH, reporthook=reporthook)
        print("\n[OK] Download complete. Extracting archive...")

        with zipfile.ZipFile(ZIP_PATH, "r") as zf:
            for member in zf.namelist():
                # files inside ml-latest-small/
                filename = os.path.basename(member)
                if filename in ["movies.csv", "ratings.csv", "tags.csv", "links.csv", "README.txt"]:
                    source = zf.open(member)
                    target_path = os.path.join(DATA_DIR, filename)
                    with open(target_path, "wb") as target:
                        target.write(source.read())
                    print(f"    Extracted: {filename} -> {target_path}")

        try:
            if os.path.exists(ZIP_PATH):
                os.remove(ZIP_PATH)
        except Exception:
            pass

        print("[OK] Dataset extracted successfully.")
        return True
    except Exception as e:
        print(f"\n[!] Network download or extraction note: {e}")
        # Only generate fallback if movies.csv or ratings.csv is missing
        if not (os.path.exists(MOVIES_CSV) and os.path.exists(RATINGS_CSV)):
            print("[*] Generating local fallback MovieLens dataset...")
            generate_fallback_dataset()
        else:
            print("[OK] Using existing extracted MovieLens dataset.")
        return True


def generate_fallback_dataset():
    """
    Generates a realistic offline MovieLens-compatible dataset if external download fails.
    Ensures zero setup barriers in offline or restricted environments.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    print("    Creating curated offline movies & ratings dataset...")

    movies_data = [
        (1, "Toy Story (1995)", "Adventure|Animation|Children|Comedy|Fantasy"),
        (2, "Jumanji (1995)", "Adventure|Children|Fantasy"),
        (3, "Grumpier Old Men (1995)", "Comedy|Romance"),
        (4, "Waiting to Exhale (1995)", "Comedy|Drama|Romance"),
        (5, "Father of the Bride Part II (1995)", "Comedy"),
        (6, "Heat (1995)", "Action|Crime|Thriller"),
        (7, "Sabrina (1995)", "Comedy|Romance"),
        (8, "Tom and Huck (1995)", "Adventure|Children"),
        (9, "Sudden Death (1995)", "Action"),
        (10, "GoldenEye (1995)", "Action|Adventure|Thriller"),
        (11, "American President, The (1995)", "Comedy|Drama|Romance"),
        (12, "Dracula: Dead and Loving It (1995)", "Comedy|Horror"),
        (13, "Balto (1995)", "Adventure|Animation|Children"),
        (14, "Nixon (1995)", "Drama"),
        (15, "Cutthroat Island (1995)", "Action|Adventure|Romance"),
        (16, "Casino (1995)", "Crime|Drama"),
        (17, "Sense and Sensibility (1995)", "Drama|Romance"),
        (18, "Four Rooms (1995)", "Comedy"),
        (19, "Ace Ventura: When Nature Calls (1995)", "Comedy"),
        (20, "Money Train (1995)", "Action|Comedy|Crime|Drama|Thriller"),
        (21, "Get Shorty (1995)", "Comedy|Crime|Thriller"),
        (22, "Copycat (1995)", "Crime|Drama|Horror|Mystery|Thriller"),
        (23, "Assassins (1995)", "Action|Crime|Thriller"),
        (24, "Powder (1995)", "Drama|Sci-Fi"),
        (25, "Leaving Las Vegas (1995)", "Drama|Romance"),
        (28, "Persuasion (1995)", "Drama|Romance"),
        (29, "City of Lost Children, The (1995)", "Adventure|Drama|Fantasy|Mystery|Sci-Fi"),
        (31, "Dangerous Minds (1995)", "Drama"),
        (32, "Twelve Monkeys (a.k.a. 12 Monkeys) (1995)", "Mystery|Sci-Fi|Thriller"),
        (34, "Babe (1995)", "Children|Drama"),
        (36, "Dead Man Walking (1995)", "Crime|Drama"),
        (39, "Clueless (1995)", "Comedy|Romance"),
        (47, "Seven (a.k.a. Se7en) (1995)", "Mystery|Thriller"),
        (50, "Usual Suspects, The (1995)", "Crime|Mystery|Thriller"),
        (110, "Braveheart (1995)", "Action|Drama|War"),
        (150, "Apollo 13 (1995)", "Adventure|Drama|IMAX"),
        (260, "Star Wars: Episode IV - A New Hope (1977)", "Action|Adventure|Sci-Fi"),
        (296, "Pulp Fiction (1994)", "Comedy|Crime|Drama|Thriller"),
        (318, "Shawshank Redemption, The (1994)", "Crime|Drama"),
        (356, "Forrest Gump (1994)", "Comedy|Drama|Romance|War"),
        (527, "Schindler's List (1993)", "Drama|War"),
        (589, "Terminator 2: Judgment Day (1991)", "Action|Sci-Fi"),
        (593, "Silence of the Lambs, The (1991)", "Crime|Horror|Thriller"),
        (858, "Godfather, The (1972)", "Crime|Drama"),
        (1196, "Star Wars: Episode V - The Empire Strikes Back (1980)", "Action|Adventure|Sci-Fi"),
        (1198, "Raiders of the Lost Ark (Indiana Jones) (1981)", "Action|Adventure"),
        (1210, "Star Wars: Episode VI - Return of the Jedi (1983)", "Action|Adventure|Sci-Fi"),
        (1270, "Back to the Future (1985)", "Adventure|Comedy|Sci-Fi"),
        (2571, "Matrix, The (1999)", "Action|Sci-Fi|Thriller"),
        (4993, "Lord of the Rings: The Fellowship of the Ring, The (2001)", "Adventure|Fantasy"),
        (7153, "Lord of the Rings: The Return of the King, The (2003)", "Action|Adventure|Drama|Fantasy"),
        (58559, "Dark Knight, The (2008)", "Action|Crime|Drama|IMAX"),
        (79132, "Inception (2010)", "Action|Crime|Drama|Mystery|Sci-Fi|Thriller|IMAX"),
        (109487, "Interstellar (2014)", "Sci-Fi|IMAX"),
    ]

    movies_df = pd.DataFrame(movies_data, columns=["movieId", "title", "genres"])
    movies_df.to_csv(MOVIES_CSV, index=False)

    # Generate synthetic realistic ratings
    np.random.seed(42)
    ratings_rows = []
    movie_ids = [m[0] for m in movies_data]
    for uid in range(1, 101):
        # each user rates 15-35 movies
        n_ratings = np.random.randint(15, 35)
        rated_movies = np.random.choice(movie_ids, size=n_ratings, replace=False)
        for mid in rated_movies:
            # rating between 2.0 and 5.0 with normal distribution around 3.8
            r = np.clip(np.round(np.random.normal(3.8, 0.9) * 2) / 2, 0.5, 5.0)
            ratings_rows.append((uid, mid, r, 1500000000 + np.random.randint(1000, 100000)))

    ratings_df = pd.DataFrame(ratings_rows, columns=["userId", "movieId", "rating", "timestamp"])
    ratings_df.to_csv(RATINGS_CSV, index=False)

    tags_rows = [
        (1, 1, "pixar", 1500000001),
        (2, 1, "animation", 1500000002),
        (3, 296, "quentin tarantino", 1500000003),
        (4, 2571, "cyberpunk", 1500000004),
        (5, 79132, "dream", 1500000005),
        (6, 79132, "mind-bending", 1500000006),
        (7, 109487, "space", 1500000007),
        (8, 109487, "black hole", 1500000008),
        (9, 58559, "batman", 1500000009),
        (10, 318, "prison escape", 1500000010),
    ]
    pd.DataFrame(tags_rows, columns=["userId", "movieId", "tag", "timestamp"]).to_csv(TAGS_CSV, index=False)
    print("    Fallback dataset created successfully.")


def preprocess_movielens_data():
    """
    Cleans movies, parses years, attaches tags, computes rating aggregates,
    and produces `processed_movies.csv` with rich metadata for content-based
    and hybrid filtering.
    """
    print("[*] Preprocessing MovieLens datasets...")
    movies_df = pd.read_csv(MOVIES_CSV)
    ratings_df = pd.read_csv(RATINGS_CSV)

    # Validate types
    movies_df["movieId"] = pd.to_numeric(movies_df["movieId"], errors="coerce").astype(int)
    ratings_df["userId"] = pd.to_numeric(ratings_df["userId"], errors="coerce").astype(int)
    ratings_df["movieId"] = pd.to_numeric(ratings_df["movieId"], errors="coerce").astype(int)
    ratings_df["rating"] = pd.to_numeric(ratings_df["rating"], errors="coerce").astype(float)

    # Drop any null records
    movies_df = movies_df.dropna(subset=["movieId", "title"]).copy()
    ratings_df = ratings_df.dropna(subset=["userId", "movieId", "rating"]).copy()
    movies_df = movies_df.drop_duplicates(subset=["movieId"]).copy()

    # Clean title and extract year
    cleaned_titles = []
    years = []
    for title in movies_df["title"]:
        clean_t, yr = extract_year_and_clean_title(title)
        cleaned_titles.append(clean_t)
        years.append(yr)

    movies_df["clean_title"] = cleaned_titles
    movies_df["year"] = years

    # Fill missing genres
    movies_df["genres"] = movies_df["genres"].fillna("Unknown")

    # Aggregate tags if tags.csv is present
    tags_dict = {}
    if os.path.exists(TAGS_CSV):
        try:
            tags_df = pd.read_csv(TAGS_CSV)
            tags_df["tag"] = tags_df["tag"].astype(str).str.lower().str.strip()
            grouped_tags = tags_df.groupby("movieId")["tag"].apply(lambda tags: " ".join(set(tags))).to_dict()
            tags_dict = grouped_tags
        except Exception as e:
            print(f"[!] Warning reading tags.csv: {e}")

    movies_df["tags"] = movies_df["movieId"].map(lambda mid: tags_dict.get(mid, ""))

    # Calculate movie rating stats: count, mean
    rating_stats = ratings_df.groupby("movieId").agg(
        rating_count=("rating", "count"),
        rating_mean=("rating", "mean")
    ).reset_index()

    movies_df = pd.merge(movies_df, rating_stats, on="movieId", how="left")
    movies_df["rating_count"] = movies_df["rating_count"].fillna(0).astype(int)
    movies_df["rating_mean"] = movies_df["rating_mean"].fillna(0.0).round(2)

    # Bayesian weighted rating (IMDb style weighted average)
    # WR = (v / (v + m)) * R + (m / (v + m)) * C
    # where v = rating_count, R = rating_mean, C = global mean rating, m = minimum votes threshold
    C = ratings_df["rating"].mean()
    m = 5  # minimum vote count threshold
    v = movies_df["rating_count"]
    R = movies_df["rating_mean"]
    movies_df["weighted_score"] = ((v / (v + m)) * R + (m / (v + m)) * C).round(2)

    # Build combined metadata string for TF-IDF
    # Repeat genre tags slightly to emphasize genre importance alongside descriptive tags
    def build_metadata_text(row):
        genres_clean = " ".join(str(row["genres"]).replace("|", " ").replace("-", "").split())
        tags_clean = str(row["tags"]).strip()
        title_words = str(row["clean_title"]).lower()
        # Combine genre (doubled weight), tags, and title keywords
        return f"{genres_clean} {genres_clean} {tags_clean} {title_words}"

    movies_df["metadata_text"] = movies_df.apply(build_metadata_text, axis=1)

    # Save processed movies
    movies_df.to_csv(PROCESSED_MOVIES_CSV, index=False)
    print(f"[OK] Processed movies saved to: {PROCESSED_MOVIES_CSV}")

    # Dataset summary statistics
    n_users = ratings_df["userId"].nunique()
    n_movies = movies_df["movieId"].nunique()
    n_ratings = len(ratings_df)
    sparsity = 100.0 * (1 - (n_ratings / (n_users * n_movies)))

    stats = {
        "total_movies": int(n_movies),
        "total_users": int(n_users),
        "total_ratings": int(n_ratings),
        "global_average_rating": round(float(C), 2),
        "matrix_sparsity_percent": round(float(sparsity), 2),
        "min_rating": float(ratings_df["rating"].min()),
        "max_rating": float(ratings_df["rating"].max()),
    }

    stats_path = os.path.join(DATA_DIR, "dataset_summary.json")
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2)

    print("\n================ DATASET SUMMARY ================")
    for k, v in stats.items():
        print(f"  {k:25}: {v}")
    print("=================================================\n")
    return stats


def main():
    force_download = "--force-download" in sys.argv
    download_movielens_dataset(force=force_download)
    preprocess_movielens_data()


if __name__ == "__main__":
    main()
