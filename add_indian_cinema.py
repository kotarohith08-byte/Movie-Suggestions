"""
add_indian_cinema.py - Enrich CineMatch AI with Tollywood & Bollywood (Post-2011)
================================================================================
Adds 60 celebrated Tollywood (Telugu) and Bollywood (Hindi) movies released
between 2012 and 2026, complete with authentic theatrical posters, tags,
and synthetic rating interactions for Collaborative Filtering.
"""

import os
import json
import re
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
POSTERS_CACHE_FILE = os.path.join(DATA_DIR, "posters_cache.json")
MOVIES_CSV = os.path.join(DATA_DIR, "movies.csv")
RATINGS_CSV = os.path.join(DATA_DIR, "ratings.csv")
PROCESSED_MOVIES_CSV = os.path.join(DATA_DIR, "processed_movies.csv")

# 60 Curated Blockbusters & Masterpieces: Tollywood & Bollywood (2012 - 2026)
INDIAN_MOVIES = [
    # --- TOLLYWOOD (TELUGU CINEMA: 2012-2026) ---
    {
        "id": 200001,
        "title": "RRR (2022)",
        "genres": "Action|Drama|War",
        "industry": "Tollywood",
        "tags": "tollywood telugu ss-rajamouli ram-charan jr-ntr freedom-fighters epic-action oscar-winner naatu-naatu",
        "rating_mean": 4.65,
        "rating_count": 82,
        "poster": "https://upload.wikimedia.org/wikipedia/en/d/d7/RRR_Poster.jpg"
    },
    {
        "id": 200002,
        "title": "Baahubali: The Beginning (2015)",
        "genres": "Action|Adventure|Drama|Fantasy",
        "industry": "Tollywood",
        "tags": "tollywood telugu ss-rajamouli prabhas rana-daggubati mahishmati epic-fantasy blockbuster",
        "rating_mean": 4.55,
        "rating_count": 78,
        "poster": "https://upload.wikimedia.org/wikipedia/en/5/5f/Baahubali_The_Beginning_poster.jpg"
    },
    {
        "id": 200003,
        "title": "Baahubali 2: The Conclusion (2017)",
        "genres": "Action|Adventure|Drama|Fantasy",
        "industry": "Tollywood",
        "tags": "tollywood telugu ss-rajamouli prabhas why-kattappa-killed-baahubali epic-climax all-time-blockbuster",
        "rating_mean": 4.60,
        "rating_count": 85,
        "poster": "https://upload.wikimedia.org/wikipedia/en/9/93/Baahubali_2_The_Conclusion_poster.jpg"
    },
    {
        "id": 200004,
        "title": "Kalki 2898 AD (2024)",
        "genres": "Action|Adventure|Fantasy|Sci-Fi",
        "industry": "Tollywood",
        "tags": "tollywood telugu nag-ashwin prabhas amitabh-bachchan kamal-haasan dystopia sci-fi mahabharata",
        "rating_mean": 4.45,
        "rating_count": 65,
        "poster": "https://upload.wikimedia.org/wikipedia/en/4/4c/Kalki_2898_AD.jpg"
    },
    {
        "id": 200005,
        "title": "Pushpa: The Rise (2021)",
        "genres": "Action|Crime|Drama|Thriller",
        "industry": "Tollywood",
        "tags": "tollywood telugu allu-arjun rashmika-mandanna fahadh-faasil red-sanders-smuggling mass-action",
        "rating_mean": 4.35,
        "rating_count": 62,
        "poster": "https://upload.wikimedia.org/wikipedia/en/7/75/Pushpa_-_The_Rise_%282021_film%29.jpg"
    },
    {
        "id": 200006,
        "title": "Pushpa 2: The Rule (2024)",
        "genres": "Action|Crime|Drama|Thriller",
        "industry": "Tollywood",
        "tags": "tollywood telugu allu-arjun fahadh-faasil red-sanders rule-the-world mass-blockbuster",
        "rating_mean": 4.40,
        "rating_count": 55,
        "poster": "https://upload.wikimedia.org/wikipedia/en/1/11/Pushpa_2_The_Rule.jpg"
    },
    {
        "id": 200007,
        "title": "Hanu-Man (2024)",
        "genres": "Action|Adventure|Fantasy|Sci-Fi",
        "industry": "Tollywood",
        "tags": "tollywood telugu prasanth-varma teja-sajja superhero indian-mythology lord-hanuman",
        "rating_mean": 4.40,
        "rating_count": 58,
        "poster": "https://upload.wikimedia.org/wikipedia/en/6/66/Hanu_Man_poster.jpg"
    },
    {
        "id": 200008,
        "title": "Salaar: Part 1 - Ceasefire (2023)",
        "genres": "Action|Crime|Drama|Thriller",
        "industry": "Tollywood",
        "tags": "tollywood telugu prashanth-neel prabhas prithviraj khansaar violent-action dark-world",
        "rating_mean": 4.30,
        "rating_count": 60,
        "poster": "https://upload.wikimedia.org/wikipedia/en/a/a6/Salaar_Part_1_%E2%80%93_Ceasefire.jpg"
    },
    {
        "id": 200009,
        "title": "Devara: Part 1 (2024)",
        "genres": "Action|Drama|Thriller",
        "industry": "Tollywood",
        "tags": "tollywood telugu koratala-siva jr-ntr saif-ali-khan janhvi-kapoor coastal-action fear-is-necessary",
        "rating_mean": 4.15,
        "rating_count": 45,
        "poster": "https://upload.wikimedia.org/wikipedia/en/c/c5/Devara_Part_1.jpg"
    },
    {
        "id": 200010,
        "title": "Saripodhaa Sanivaaram (2024)",
        "genres": "Action|Crime|Thriller",
        "industry": "Tollywood",
        "tags": "tollywood telugu vivek-athreya nani sj-suryah anger-management saturday-vigilante",
        "rating_mean": 4.25,
        "rating_count": 42,
        "poster": "https://upload.wikimedia.org/wikipedia/en/6/60/Saripodhaa_Sanivaaram_poster.jpg"
    },
    {
        "id": 200011,
        "title": "Hi Nanna (2023)",
        "genres": "Drama|Romance",
        "industry": "Tollywood",
        "tags": "tollywood telugu nani mrunal-thakur father-daughter emotional-romance heart-touching",
        "rating_mean": 4.50,
        "rating_count": 52,
        "poster": "https://upload.wikimedia.org/wikipedia/en/8/8f/Hi_Nanna_poster.jpg"
    },
    {
        "id": 200012,
        "title": "Sita Ramam (2022)",
        "genres": "Drama|Mystery|Romance|War",
        "industry": "Tollywood",
        "tags": "tollywood telugu hanu-raghavapudi dulquer-salmaan mrunal-thakur rashmika army-officer love-letters kashmir",
        "rating_mean": 4.60,
        "rating_count": 64,
        "poster": "https://upload.wikimedia.org/wikipedia/en/9/90/Sita_Ramam.jpg"
    },
    {
        "id": 200013,
        "title": "Karthikeya 2 (2022)",
        "genres": "Action|Adventure|Mystery|Thriller",
        "industry": "Tollywood",
        "tags": "tollywood telugu chandoo-mondeti nikhil-siddharth anupama lord-krishna-anklet dwarka mystery",
        "rating_mean": 4.30,
        "rating_count": 48,
        "poster": "https://upload.wikimedia.org/wikipedia/en/2/23/Karthikeya_2_film_poster.jpg"
    },
    {
        "id": 200014,
        "title": "Major (2022)",
        "genres": "Action|Biography|Drama|War",
        "industry": "Tollywood",
        "tags": "tollywood telugu sashi-kiran-tikka adivi-sesh major-sandeep-unnikrishnan 26-11-mumbai-attacks patriotic",
        "rating_mean": 4.55,
        "rating_count": 50,
        "poster": "https://upload.wikimedia.org/wikipedia/en/3/36/Major_film_poster.jpg"
    },
    {
        "id": 200015,
        "title": "Ala Vaikunthapurramuloo (2020)",
        "genres": "Action|Comedy|Drama",
        "industry": "Tollywood",
        "tags": "tollywood telugu trivikram allu-arjun pooja-hegde butta-bomma samaja-varagamana family-entertainer",
        "rating_mean": 4.35,
        "rating_count": 60,
        "poster": "https://upload.wikimedia.org/wikipedia/en/2/28/Ala_Vaikunthapurramuloo.jpeg"
    },
    {
        "id": 200016,
        "title": "Jersey (2019)",
        "genres": "Drama|Sport",
        "industry": "Tollywood",
        "tags": "tollywood telugu gowtam-tinnanuri nani shraddha-srinath cricket-comeback father-love inspirational",
        "rating_mean": 4.70,
        "rating_count": 68,
        "poster": "https://upload.wikimedia.org/wikipedia/en/4/4c/Jersey_2019_poster.jpg"
    },
    {
        "id": 200017,
        "title": "Agent Sai Srinivasa Athreya (2019)",
        "genres": "Comedy|Crime|Mystery|Thriller",
        "industry": "Tollywood",
        "tags": "tollywood telugu swaroop-rsj naveen-polishetty detective-comedy dead-body-mystery smart-investigation",
        "rating_mean": 4.50,
        "rating_count": 54,
        "poster": "https://upload.wikimedia.org/wikipedia/en/9/90/Agent_Sai_Srinivasa_Athreya.jpg"
    },
    {
        "id": 200018,
        "title": "Mathu Vadalara (2019)",
        "genres": "Comedy|Crime|Mystery|Thriller",
        "industry": "Tollywood",
        "tags": "tollywood telugu ritesh-rana sri-simha satya delivery-boy accidental-crime dark-comedy",
        "rating_mean": 4.35,
        "rating_count": 40,
        "poster": "https://upload.wikimedia.org/wikipedia/en/7/7b/Mathu_Vadalara_poster.jpg"
    },
    {
        "id": 200019,
        "title": "Rangasthalam (2018)",
        "genres": "Action|Drama",
        "industry": "Tollywood",
        "tags": "tollywood telugu sukumar ram-charan samantha chitti-babu hearing-impaired village-politics revenge",
        "rating_mean": 4.60,
        "rating_count": 72,
        "poster": "https://upload.wikimedia.org/wikipedia/en/5/5d/Rangasthalam.jpg"
    },
    {
        "id": 200020,
        "title": "Mahanati (2018)",
        "genres": "Biography|Drama",
        "industry": "Tollywood",
        "tags": "tollywood telugu nag-ashwin keerthy-suresh dulquer-salmaan savitri-biopic classic-cinema golden-age",
        "rating_mean": 4.65,
        "rating_count": 58,
        "poster": "https://upload.wikimedia.org/wikipedia/en/8/87/Mahanati_poster.jpg"
    },
    {
        "id": 200021,
        "title": "Goodachari (2018)",
        "genres": "Action|Mystery|Thriller",
        "industry": "Tollywood",
        "tags": "tollywood telugu sashi-kiran-tikka adivi-sesh spy-thriller raw-agent intelligence-agency",
        "rating_mean": 4.40,
        "rating_count": 46,
        "poster": "https://upload.wikimedia.org/wikipedia/en/6/69/Goodachari_poster.jpg"
    },
    {
        "id": 200022,
        "title": "C/o Kancharapalem (2018)",
        "genres": "Drama|Romance",
        "industry": "Tollywood",
        "tags": "tollywood telugu venkatesh-maha indie-masterpiece four-love-stories realistic-cinema",
        "rating_mean": 4.75,
        "rating_count": 56,
        "poster": "https://upload.wikimedia.org/wikipedia/en/a/a2/C_o_Kancharapalem_poster.jpg"
    },
    {
        "id": 200023,
        "title": "Arjun Reddy (2017)",
        "genres": "Drama|Romance",
        "industry": "Tollywood",
        "tags": "tollywood telugu sandeep-reddy-vanga vijay-deverakonda shalini-pandey intense-romance surgeon addiction",
        "rating_mean": 4.35,
        "rating_count": 66,
        "poster": "https://upload.wikimedia.org/wikipedia/en/4/46/Arjun_Reddy_poster.jpg"
    },
    {
        "id": 200024,
        "title": "Fidaa (2017)",
        "genres": "Comedy|Drama|Romance",
        "industry": "Tollywood",
        "tags": "tollywood telugu sekhar-kammula varun-tej sai-pallavi telangana-village nri-love",
        "rating_mean": 4.30,
        "rating_count": 50,
        "poster": "https://upload.wikimedia.org/wikipedia/en/e/eb/Fidaa_poster.jpg"
    },
    {
        "id": 200025,
        "title": "Eega (2012)",
        "genres": "Action|Comedy|Fantasy|Sci-Fi",
        "industry": "Tollywood",
        "tags": "tollywood telugu ss-rajamouli nani sudeep samantha housefly-reincarnation revenge-comedy innovative",
        "rating_mean": 4.50,
        "rating_count": 70,
        "poster": "https://upload.wikimedia.org/wikipedia/en/9/91/Eega_poster.jpg"
    },
    {
        "id": 200026,
        "title": "Manam (2014)",
        "genres": "Comedy|Drama|Fantasy|Romance",
        "industry": "Tollywood",
        "tags": "tollywood telugu vikram-kumar nageswara-rao nagarjuna naga-chaitanya samantha reincarnation family",
        "rating_mean": 4.45,
        "rating_count": 52,
        "poster": "https://upload.wikimedia.org/wikipedia/en/4/4e/Manam_poster.jpg"
    },
    {
        "id": 200027,
        "title": "Race Gurram (2014)",
        "genres": "Action|Comedy",
        "industry": "Tollywood",
        "tags": "tollywood telugu surender-reddy allu-arjun shruti-haasan brahmanandam kill-bill-pandey energetic-entertainer",
        "rating_mean": 4.20,
        "rating_count": 48,
        "poster": "https://upload.wikimedia.org/wikipedia/en/3/30/Race_Gurram_poster.jpg"
    },
    {
        "id": 200028,
        "title": "Srimanthudu (2015)",
        "genres": "Action|Drama",
        "industry": "Tollywood",
        "tags": "tollywood telugu koratala-siva mahesh-babu shruti-haasan village-adoption billionaire-hero social-drama",
        "rating_mean": 4.30,
        "rating_count": 56,
        "poster": "https://upload.wikimedia.org/wikipedia/en/5/5a/Srimanthudu_Poster.jpg"
    },
    {
        "id": 200029,
        "title": "Dasara (2023)",
        "genres": "Action|Crime|Drama",
        "industry": "Tollywood",
        "tags": "tollywood telugu srikanth-odela nani keerthy-suresh singareni-coal-mines rustic-raw friendship-revenge",
        "rating_mean": 4.25,
        "rating_count": 44,
        "poster": "https://upload.wikimedia.org/wikipedia/en/1/18/Dasara_film_poster.jpg"
    },
    {
        "id": 200030,
        "title": "Brochevarevarura (2019)",
        "genres": "Comedy|Crime",
        "industry": "Tollywood",
        "tags": "tollywood telugu vivek-athreya sree-vishnu nivetha-thomas rahul-ramakrishna kidnap-comedy college-youth",
        "rating_mean": 4.40,
        "rating_count": 42,
        "poster": "https://upload.wikimedia.org/wikipedia/en/9/91/Brochevarevarura.jpg"
    },

    # --- BOLLYWOOD (HINDI CINEMA: 2012-2026) ---
    {
        "id": 200031,
        "title": "12th Fail (2023)",
        "genres": "Biography|Drama",
        "industry": "Bollywood",
        "tags": "bollywood hindi vidhu-vinod-chopra vikrant-massey manoj-kumar-sharma ias-upsc struggle restart inspirational",
        "rating_mean": 4.85,
        "rating_count": 76,
        "poster": "https://upload.wikimedia.org/wikipedia/en/f/f2/12th_Fail_poster.jpeg"
    },
    {
        "id": 200032,
        "title": "Jawan (2023)",
        "genres": "Action|Thriller",
        "industry": "Bollywood",
        "tags": "bollywood hindi atlee shah-rukh-khan nayanthara vijay-sethupathi mass-action social-justice dual-role",
        "rating_mean": 4.35,
        "rating_count": 70,
        "poster": "https://upload.wikimedia.org/wikipedia/en/3/39/Jawan_film_poster.jpg"
    },
    {
        "id": 200033,
        "title": "Pathaan (2023)",
        "genres": "Action|Adventure|Thriller",
        "industry": "Bollywood",
        "tags": "bollywood hindi siddharth-anand shah-rukh-khan john-abraham deepika-padukone spy-universe raw-agent",
        "rating_mean": 4.20,
        "rating_count": 68,
        "poster": "https://upload.wikimedia.org/wikipedia/en/c/c3/Pathaan_film_poster.jpg"
    },
    {
        "id": 200034,
        "title": "Animal (2023)",
        "genres": "Action|Crime|Drama|Thriller",
        "industry": "Bollywood",
        "tags": "bollywood hindi sandeep-reddy-vanga ranbir-kapoor anil-kapoor bobby-deol father-son violent-action intense",
        "rating_mean": 4.30,
        "rating_count": 72,
        "poster": "https://upload.wikimedia.org/wikipedia/en/9/90/Animal_%282023_film%29_poster.jpg"
    },
    {
        "id": 200035,
        "title": "Stree 2 (2024)",
        "genres": "Comedy|Horror",
        "industry": "Bollywood",
        "tags": "bollywood hindi amar-kaushik shraddha-kapoor rajkummar-rao pankaj-tripathi sarkata horror-comedy blockbuster",
        "rating_mean": 4.45,
        "rating_count": 64,
        "poster": "https://upload.wikimedia.org/wikipedia/en/a/a1/Stree_2.jpg"
    },
    {
        "id": 200036,
        "title": "Stree (2018)",
        "genres": "Comedy|Horror",
        "industry": "Bollywood",
        "tags": "bollywood hindi amar-kaushik rajkummar-rao shraddha-kapoor pankaj-tripathi o-stree-kal-aana horror-comedy",
        "rating_mean": 4.40,
        "rating_count": 62,
        "poster": "https://upload.wikimedia.org/wikipedia/en/4/4f/Stree_-_2018_Movie_Poster.jpg"
    },
    {
        "id": 200037,
        "title": "Brahmāstra: Part One – Shiva (2022)",
        "genres": "Action|Adventure|Fantasy|Sci-Fi",
        "industry": "Bollywood",
        "tags": "bollywood hindi ayan-mukerji ranbir-kapoor alia-bhatt amitabh-bachchan astraverse indian-mythology fantasy",
        "rating_mean": 4.10,
        "rating_count": 55,
        "poster": "https://upload.wikimedia.org/wikipedia/en/4/40/Brahmastra_Part_One_Shiva.jpg"
    },
    {
        "id": 200038,
        "title": "Drishyam (2015)",
        "genres": "Crime|Drama|Mystery|Thriller",
        "industry": "Bollywood",
        "tags": "bollywood hindi nishikant-kamat ajay-devgn tabu 2-october panaji murder-cover-up suspense-thriller",
        "rating_mean": 4.60,
        "rating_count": 75,
        "poster": "https://upload.wikimedia.org/wikipedia/en/8/8a/Drishyam_2015_film_poster.jpg"
    },
    {
        "id": 200039,
        "title": "Drishyam 2 (2022)",
        "genres": "Crime|Drama|Mystery|Thriller",
        "industry": "Bollywood",
        "tags": "bollywood hindi abhishek-pathak ajay-devgn tabu akshaye-khanna mind-game murder-investigation",
        "rating_mean": 4.50,
        "rating_count": 66,
        "poster": "https://upload.wikimedia.org/wikipedia/en/3/30/Drishyam_2_2022_poster.jpg"
    },
    {
        "id": 200040,
        "title": "Tumbbad (2018)",
        "genres": "Drama|Fantasy|Horror|Mystery",
        "industry": "Bollywood",
        "tags": "bollywood hindi rahi-anil-barve sohum-shah hastar greed atmospheric-horror atmospheric-masterpiece",
        "rating_mean": 4.65,
        "rating_count": 68,
        "poster": "https://upload.wikimedia.org/wikipedia/en/4/41/Tumbbad_poster.jpg"
    },
    {
        "id": 200041,
        "title": "Andhadhun (2018)",
        "genres": "Comedy|Crime|Mystery|Thriller",
        "industry": "Bollywood",
        "tags": "bollywood hindi sriram-raghavan ayushmann-khurrana tabu radhika-apte blind-pianist dark-comedy twists",
        "rating_mean": 4.70,
        "rating_count": 78,
        "poster": "https://upload.wikimedia.org/wikipedia/en/4/47/Andhadhun_poster.jpg"
    },
    {
        "id": 200042,
        "title": "Badhaai Ho (2018)",
        "genres": "Comedy|Drama|Romance",
        "industry": "Bollywood",
        "tags": "bollywood hindi amit-sharma ayushmann-khurrana neena-gupta gajraj-rao sanya-malhotra family-comedy late-pregnancy",
        "rating_mean": 4.40,
        "rating_count": 52,
        "poster": "https://upload.wikimedia.org/wikipedia/en/1/14/Badhaai_Ho_Poster.jpg"
    },
    {
        "id": 200043,
        "title": "Article 15 (2019)",
        "genres": "Crime|Drama|Mystery|Thriller",
        "industry": "Bollywood",
        "tags": "bollywood hindi anubhav-sinha ayushmann-khurrana police-investigation caste-discrimination constitution-india",
        "rating_mean": 4.55,
        "rating_count": 60,
        "poster": "https://upload.wikimedia.org/wikipedia/en/6/69/Article_15_poster.jpg"
    },
    {
        "id": 200044,
        "title": "Uri: The Surgical Strike (2019)",
        "genres": "Action|Drama|War",
        "industry": "Bollywood",
        "tags": "bollywood hindi aditya-dhar vicky-kaushal yami-gautam how-is-the-josh surgical-strike indian-army patriotic",
        "rating_mean": 4.60,
        "rating_count": 74,
        "poster": "https://upload.wikimedia.org/wikipedia/en/3/3b/URI_-_New_Poster.jpg"
    },
    {
        "id": 200045,
        "title": "Gully Boy (2019)",
        "genres": "Drama",
        "industry": "Bollywood",
        "tags": "bollywood hindi zoya-akhtar ranveer-singh alia-bhatt siddhant-chaturvedi dharavi rap hip-hop apna-time-aayega",
        "rating_mean": 4.45,
        "rating_count": 65,
        "poster": "https://upload.wikimedia.org/wikipedia/en/0/07/Gully_Boy_poster.jpg"
    },
    {
        "id": 200046,
        "title": "Chhichhore (2019)",
        "genres": "Comedy|Drama",
        "industry": "Bollywood",
        "tags": "bollywood hindi nitesh-tiwari sushant-singh-rajput shraddha-kapoor hostel-life engineering friendship-losers",
        "rating_mean": 4.50,
        "rating_count": 62,
        "poster": "https://upload.wikimedia.org/wikipedia/en/3/3d/Chhichhore_Poster.jpg"
    },
    {
        "id": 200047,
        "title": "Shershaah (2021)",
        "genres": "Action|Biography|Drama|War",
        "industry": "Bollywood",
        "tags": "bollywood hindi vishnuvardhan sidharth-malhotra kiara-advani captain-vikram-batra kargil-war yeh-dil-maange-more",
        "rating_mean": 4.65,
        "rating_count": 67,
        "poster": "https://upload.wikimedia.org/wikipedia/en/9/91/Shershaah_film_poster.jpg"
    },
    {
        "id": 200048,
        "title": "Sardar Udham (2021)",
        "genres": "Biography|Crime|Drama|History",
        "industry": "Bollywood",
        "tags": "bollywood hindi shoojit-sircar vicky-kaushal udham-singh jallianwala-bagh london-assassination freedom-struggle",
        "rating_mean": 4.75,
        "rating_count": 64,
        "poster": "https://upload.wikimedia.org/wikipedia/en/9/90/Sardar_Udham_film_poster.jpg"
    },
    {
        "id": 200049,
        "title": "Dangal (2016)",
        "genres": "Action|Biography|Drama",
        "industry": "Bollywood",
        "tags": "bollywood hindi nitesh-tiwari aamir-khan fatima-sana-shaikh wrestling geeta-phogat commonwealth-gold inspirational",
        "rating_mean": 4.80,
        "rating_count": 86,
        "poster": "https://upload.wikimedia.org/wikipedia/en/9/99/Dangal_Poster.jpg"
    },
    {
        "id": 200050,
        "title": "Bajrangi Bhaijaan (2015)",
        "genres": "Action|Adventure|Comedy|Drama",
        "industry": "Bollywood",
        "tags": "bollywood hindi kabir-khan salman-khan nawazuddin-siddiqui harshali-malhotra cross-border-love india-pakistan emotional",
        "rating_mean": 4.60,
        "rating_count": 78,
        "poster": "https://upload.wikimedia.org/wikipedia/en/d/dc/Bajrangi_Bhaijaan_Poster.jpg"
    },
    {
        "id": 200051,
        "title": "PK (2014)",
        "genres": "Comedy|Drama|Sci-Fi",
        "industry": "Bollywood",
        "tags": "bollywood hindi rajkumar-hirani aamir-khan anushka-sharma alien-on-earth wrong-number religious-satire",
        "rating_mean": 4.55,
        "rating_count": 80,
        "poster": "https://upload.wikimedia.org/wikipedia/en/c/c3/PK_poster.jpg"
    },
    {
        "id": 200052,
        "title": "Queen (2014)",
        "genres": "Adventure|Comedy|Drama",
        "industry": "Bollywood",
        "tags": "bollywood hindi vikas-bahl kangana-ranaut solo-honeymoon paris amsterdam self-discovery women-empowerment",
        "rating_mean": 4.60,
        "rating_count": 66,
        "poster": "https://upload.wikimedia.org/wikipedia/en/4/45/QueenMoviePoster7thMarch.jpg"
    },
    {
        "id": 200053,
        "title": "Haider (2014)",
        "genres": "Action|Crime|Drama|Thriller",
        "industry": "Bollywood",
        "tags": "bollywood hindi vishal-bhardwaj shahid-kapoor tabu kay-kay-menon hamlet-adaptation kashmir-conflict",
        "rating_mean": 4.50,
        "rating_count": 58,
        "poster": "https://upload.wikimedia.org/wikipedia/en/9/98/Haider_Movie_Poster.jpg"
    },
    {
        "id": 200054,
        "title": "Gangs of Wasseypur (2012)",
        "genres": "Action|Comedy|Crime|Drama|Thriller",
        "industry": "Bollywood",
        "tags": "bollywood hindi anurag-kashyap manoj-bajpayee nawazuddin-siddiqui coal-mafia revenge-saga cult-classic",
        "rating_mean": 4.70,
        "rating_count": 82,
        "poster": "https://upload.wikimedia.org/wikipedia/en/6/6a/Gangs_of_Wasseypur_poster.jpg"
    },
    {
        "id": 200055,
        "title": "Barfi! (2012)",
        "genres": "Comedy|Drama|Romance",
        "industry": "Bollywood",
        "tags": "bollywood hindi anurag-basu ranbir-kapoor priyanka-chopra ileana-dcruz deaf-mute-hero autistic-girl beautiful-romance darjeeling",
        "rating_mean": 4.60,
        "rating_count": 72,
        "poster": "https://upload.wikimedia.org/wikipedia/en/2/2e/Barfi%21_poster.jpg"
    },
    {
        "id": 200056,
        "title": "Kahaani (2012)",
        "genres": "Mystery|Thriller",
        "industry": "Bollywood",
        "tags": "bollywood hindi sujoy-ghosh vidya-balan nawazuddin-siddiqui kolkata durga-puja pregnant-woman-search shock-twist",
        "rating_mean": 4.65,
        "rating_count": 70,
        "poster": "https://upload.wikimedia.org/wikipedia/en/9/91/Kahaani_poster.jpg"
    },
    {
        "id": 200057,
        "title": "Bhaag Milkha Bhaag (2013)",
        "genres": "Biography|Drama",
        "industry": "Bollywood",
        "tags": "bollywood hindi rakeysh-omprakash-mehra farhan-akhtar milkha-singh flying-sikh olympics-runner partition inspirational",
        "rating_mean": 4.60,
        "rating_count": 68,
        "poster": "https://upload.wikimedia.org/wikipedia/en/4/42/Bhaag_Milkha_Bhaag_poster.jpg"
    },
    {
        "id": 200058,
        "title": "Yeh Jawaani Hai Deewani (2013)",
        "genres": "Comedy|Drama|Romance",
        "industry": "Bollywood",
        "tags": "bollywood hindi ayan-mukerji ranbir-kapoor deepika-padukone bunny naina trekking friendship wanderlust",
        "rating_mean": 4.45,
        "rating_count": 75,
        "poster": "https://upload.wikimedia.org/wikipedia/en/1/15/Yeh_jawaani_hai_deewani_poster.jpg"
    },
    {
        "id": 200059,
        "title": "Padmaavat (2018)",
        "genres": "Drama|Romance|War",
        "industry": "Bollywood",
        "tags": "bollywood hindi sanjay-leela-bhansali deepika-padukone ranveer-singh shahid-kapoor alauddin-khilji chittor historical-epic",
        "rating_mean": 4.35,
        "rating_count": 64,
        "poster": "https://upload.wikimedia.org/wikipedia/en/7/73/Padmaavat_poster.jpg"
    },
    {
        "id": 200060,
        "title": "Raazi (2018)",
        "genres": "Action|Drama|Thriller",
        "industry": "Bollywood",
        "tags": "bollywood hindi meghna-gulzar alia-bhatt vicky-kaushal sehmat raw-spy kashmir 1971-war patriot",
        "rating_mean": 4.55,
        "rating_count": 60,
        "poster": "https://upload.wikimedia.org/wikipedia/en/2/2f/Raazi_Poster.jpg"
    }
]


def extract_year(title: str):
    m = re.search(r"\((\d{4})\)", title)
    return int(m.group(1)) if m else None


def clean_title_str(title: str):
    return re.sub(r"\s*\(\d{4}\)\s*$", "", title).strip()


def run_enrichment():
    print("[*] Adding Post-2011 Tollywood & Bollywood Movies to CineMatch AI...")
    
    # 1. Update posters_cache.json
    cache = {}
    if os.path.exists(POSTERS_CACHE_FILE):
        with open(POSTERS_CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)

    for m in INDIAN_MOVIES:
        cache[str(m["id"])] = m["poster"]

    with open(POSTERS_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)
    print(f"[OK] Added {len(INDIAN_MOVIES)} authentic poster URLs to posters_cache.json")

    # 2. Update movies.csv
    movies_df = pd.read_csv(MOVIES_CSV)
    existing_ids = set(movies_df["movieId"].astype(int))

    new_movie_rows = []
    for m in INDIAN_MOVIES:
        if m["id"] not in existing_ids:
            new_movie_rows.append({
                "movieId": m["id"],
                "title": m["title"],
                "genres": m["genres"]
            })

    if new_movie_rows:
        new_movies_df = pd.DataFrame(new_movie_rows)
        movies_df = pd.concat([movies_df, new_movies_df], ignore_index=True)
        movies_df.to_csv(MOVIES_CSV, index=False)
        print(f"[OK] Appended {len(new_movie_rows)} movies to movies.csv")

    # 3. Update ratings.csv with realistic audience interactions
    ratings_df = pd.read_csv(RATINGS_CSV)
    existing_rating_mids = set(ratings_df["movieId"].astype(int))

    np.random.seed(42)
    new_ratings = []
    all_user_ids = sorted(ratings_df["userId"].unique())

    for m in INDIAN_MOVIES:
        if m["id"] in existing_rating_mids:
            continue
        # Select random users who rated this movie
        n_raters = min(m["rating_count"], len(all_user_ids))
        raters = np.random.choice(all_user_ids, size=n_raters, replace=False)
        
        for u in raters:
            # Sample rating with normal distribution around the movie's mean
            r = np.clip(np.round(np.random.normal(m["rating_mean"], 0.45) * 2) / 2, 2.5, 5.0)
            new_ratings.append({
                "userId": int(u),
                "movieId": int(m["id"]),
                "rating": float(r),
                "timestamp": 1600000000 + np.random.randint(1000, 50000000)
            })

    if new_ratings:
        new_ratings_df = pd.DataFrame(new_ratings)
        ratings_df = pd.concat([ratings_df, new_ratings_df], ignore_index=True)
        ratings_df.to_csv(RATINGS_CSV, index=False)
        print(f"[OK] Appended {len(new_ratings)} audience ratings to ratings.csv")

    # 4. Generate processed_movies.csv
    print("[*] Rebuilding processed_movies.csv metadata...")
    from get_data import preprocess_movielens_data
    preprocess_movielens_data()
    print("[SUCCESS] Tollywood and Bollywood movies added and processed successfully!")


if __name__ == "__main__":
    run_enrichment()
