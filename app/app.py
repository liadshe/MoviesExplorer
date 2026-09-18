import os
import time
import logging
import requests
from flask import Flask, jsonify, render_template

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# --- Config from ConfigMap (mounted as env vars) ---
MOVIE_NAME = os.environ.get("MOVIE_NAME", "Inception")
THEME_COLOR = os.environ.get("THEME_COLOR", "#1a1a2e")
POLL_INTERVAL_SECONDS = int(os.environ.get("POLL_INTERVAL_SECONDS", "10"))

# --- Secret 1: external API credential (OMDb) ---
OMDB_API_KEY = os.environ.get("OMDB_API_KEY")

# --- Secret 2: k8s ServiceAccount token, mounted as a file ---
K8S_TOKEN_PATH = os.environ.get("K8S_TOKEN_PATH", "/var/run/secrets/demo-website/token")
K8S_API_SERVER = "https://kubernetes.default.svc"
K8S_CA_CERT = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"

# --- Pod identity, injected via the Downward API in the Helm chart ---
POD_NAME = os.environ.get("POD_NAME", "unknown")
POD_NAMESPACE = os.environ.get("POD_NAMESPACE", "default")

_movie_cache = {"data": None, "fetched_at": 0}
MOVIE_CACHE_TTL = 3600  # seconds — avoid burning OMDb's free-tier quota


def fetch_movie():
    """Fetch movie details from OMDb, with a simple in-memory cache."""
    now = time.time()
    if _movie_cache["data"] and (now - _movie_cache["fetched_at"] < MOVIE_CACHE_TTL):
        return _movie_cache["data"]

    if not OMDB_API_KEY:
        return {"error": "OMDb API key not configured"}

    try:
        resp = requests.get(
            "https://www.omdbapi.com/",
            params={"t": MOVIE_NAME, "type": "movie", "apikey": OMDB_API_KEY},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("Response") == "False":
            # OMDb returns Response: False with an Error message (e.g. "Movie not found!")
            # whenever the title doesn't match anything in its database.
            error_msg = data.get("Error", "Unknown OMDb error")
            return {"error": f"'{MOVIE_NAME}': {error_msg}"}

        movie = {
            "title": data.get("Title"),
            "year": data.get("Year"),
            "plot": data.get("Plot"),
            "poster": data.get("Poster"),
            "rating": data.get("imdbRating"),
            "genre": data.get("Genre"),
        }
        _movie_cache["data"] = movie
        _movie_cache["fetched_at"] = now
        return movie

    except requests.RequestException as exc:
        logging.warning("OMDb fetch failed: %s", exc)
        # Fall back to the last good response if we have one, rather than crashing
        return _movie_cache["data"] or {"error": "Movie data temporarily unavailable"}


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
        movie=fetch_movie(),
    )


@app.route("/api/usage")
def api_usage():
    return jsonify(fetch_pod_usage())


@app.route("/healthz")
def healthz():
    # Liveness: is the process alive and serving requests at all.
    return "ok", 200


@app.route("/readyz")
def readyz():
    # Readiness: did we actually load our config? Deliberately does NOT check
    # OMDb reachability — an external dependency being flaky shouldn't pull
    # this pod out of the Service's endpoint list.
    if MOVIE_NAME and THEME_COLOR:
        return "ready", 200
    return "not ready: missing config", 503


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
