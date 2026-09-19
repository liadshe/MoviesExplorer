import os
import random
import logging
import requests
from flask import Flask, jsonify, render_template

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# --- Config from ConfigMap (mounted as env vars) ---
OMDB_API_URL = os.environ.get("OMDB_API_URL")
THEME_COLOR = os.environ.get("THEME_COLOR")
POLL_INTERVAL_SECONDS = int(os.environ.get("POLL_INTERVAL_SECONDS"))

# --- Secret 1: external API credential (OMDb) ---
OMDB_API_KEY = os.environ.get("OMDB_API_KEY")

# --- Secret 2: k8s ServiceAccount token, mounted as a file ---
K8S_TOKEN_PATH = os.environ.get("K8S_TOKEN_PATH", "/var/run/secrets/demo-website/token")
K8S_API_SERVER = "https://kubernetes.default.svc"
K8S_CA_CERT = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"

# --- Pod identity, injected via the Downward API in the Helm chart ---
POD_NAME = os.environ.get("POD_NAME", "unknown")
POD_NAMESPACE = os.environ.get("POD_NAMESPACE", "default")

# Cache by title so we don't spam OMDb for the same movie twice
_movie_cache = {} 

# A curated list of visually striking movies for the randomizer
MOVIE_LIST = [
    "Inception", "The Matrix", "Interstellar", "Gladiator",
    "The Godfather", "Pulp Fiction", "The Dark Knight",
    "Fight Club", "Forrest Gump", "The Shawshank Redemption",
    "Jurassic Park", "Back to the Future", "The Avengers",
    "Spirited Away", "Blade Runner 2049", "Dune"
]

def fetch_random_movie():
    """Pick a random movie, check cache, or fetch from OMDb."""
    title = random.choice(MOVIE_LIST)

    # Return instantly if we already fetched this title's poster/data today
    if title in _movie_cache:
        return _movie_cache[title]

    if not OMDB_API_KEY:
        return {"error": "OMDb API key not configured"}

    try:
        resp = requests.get(
            OMDB_API_URL,
            params={"t": title, "type": "movie", "apikey": OMDB_API_KEY},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("Response") == "False":
            return {"error": data.get("Error", "Unknown OMDb error")}

        movie = {
            "title": data.get("Title"),
            "year": data.get("Year"),
            "plot": data.get("Plot"),
            "poster": data.get("Poster"),
            "rating": data.get("imdbRating"),
            "genre": data.get("Genre"),
        }
        
        # Save to cache for future random hits
        _movie_cache[title] = movie
        return movie

    except requests.RequestException as exc:
        logging.warning("OMDb fetch failed: %s", exc)
        return {"error": "Movie data temporarily unavailable"}

def read_k8s_token():
    try:
        with open(K8S_TOKEN_PATH, "r") as f:
            return f.read().strip()
    except OSError as exc:
        logging.warning("Could not read k8s token: %s", exc)
        return None

def fetch_pod_usage():
    """Call the Kubernetes metrics API for this pod's live CPU/memory usage."""
    token = read_k8s_token()
    if not token:
        return {"error": "No service account token available"}

    url = (
        f"{K8S_API_SERVER}/apis/metrics.k8s.io/v1beta1/"
        f"namespaces/{POD_NAMESPACE}/pods/{POD_NAME}"
    )
    headers = {"Authorization": f"Bearer {token}"}
    verify = K8S_CA_CERT if os.path.exists(K8S_CA_CERT) else True

    try:
        resp = requests.get(url, headers=headers, verify=verify, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        container = data["containers"][0]
        return {
            "cpu": container["usage"]["cpu"],
            "memory": container["usage"]["memory"],
        }
    except (requests.RequestException, KeyError, IndexError) as exc:
        logging.warning("metrics-server call failed: %s", exc)
        return {"error": "Usage data unavailable (is metrics-server installed?)"}

@app.route("/")
def index():
    return render_template(
        "index.html",
        theme_color=THEME_COLOR,
        poll_interval=POLL_INTERVAL_SECONDS,
        movie=fetch_random_movie(),
    )

@app.route("/api/usage")
def api_usage():
    return jsonify(fetch_pod_usage())

@app.route("/healthz")
def healthz():
    return "ok", 200

@app.route("/readyz")
def readyz():
    # Updated to check for the URL instead of MOVIE_NAME
    if OMDB_API_URL and THEME_COLOR:
        return "ready", 200
    return "not ready: missing config", 503

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)