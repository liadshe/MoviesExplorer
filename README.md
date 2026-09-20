# Movies Explorer Demo Application

A small web application that shows a random movie, its poster, plot, rating, and live pod resource usage from the Kubernetes cluster. The project combines a Python Flask frontend, a Dockerized runtime, and a Helm chart for Kubernetes deployment.

## Overview

This project is designed as a demo application for Kubernetes-based deployments. It reads runtime configuration from Kubernetes ConfigMaps and Secrets, exposes health endpoints for probing, and uses the Kubernetes metrics API to display CPU and memory usage for the running pod.

The app is intentionally simple but useful for learning:

- Containerized application with Docker
- Flask web frontend with dynamic template rendering
- Kubernetes-native configuration with ConfigMaps and Secrets
- Deployment via Helm
- Service account token usage for cluster telemetry
- Ingress-ready service definition

## Project structure

```text
MoviesExplorer/
├── README.md
├── app/
│   ├── app.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── templates/
│       └── index.html
├── chart/
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
│       ├── _helpers.tpl
│       ├── configmap.yaml
│       ├── deployment.yaml
│       ├── ingress.yaml
│       ├── rbac.yaml
│       ├── sealed-secret.yaml
│       ├── service.yaml
│       └── serviceaccount.yaml
└── .gitignore
```

### Main application folder

`app/` contains the actual web application code.

- `app.py`: Flask app and API routes
- `requirements.txt`: Python dependencies
- `Dockerfile`: container image build instructions
- `templates/index.html`: front-end HTML, CSS, and JS for the movie UI

### Helm chart folder

`chart/` contains the Kubernetes deployment configuration.

- `Chart.yaml`: Helm metadata
- `values.yaml`: default chart values for image, ingress, resources, and app settings
- `templates/`: Kubernetes manifests for deployment, service, ingress, config map, secrets, RBAC, and service account

## Application behavior

The Flask application does the following:

1. Selects a random movie from a curated list.
2. Calls the OMDb API to fetch movie metadata.
3. Caches the data in memory so repeated movie selections do not trigger duplicate API requests.
4. Renders the film details, poster, plot, year, and rating in the browser.
5. Queries the Kubernetes metrics API for the currently running pod’s CPU and memory usage.
6. Exposes health endpoints for readiness and liveness checks.

### Routes

- `/` – main movie dashboard
- `/api/usage` – returns the pod’s CPU/memory metrics in JSON format
- `/healthz` – simple liveness endpoint
- `/readyz` – readiness endpoint that checks required configuration

## Technologies used

### Application stack

- Python 3.12
- Flask 3.0.3
- Requests 2.32.3
- Jinja2 templates

### Containerization

- Docker
- Multi-stage Dockerfile for leaner runtime image

### Kubernetes and Helm

- Kubernetes manifests
- Helm chart packaging
- ServiceAccount
- ConfigMap
- Secret management
- Ingress
- Liveness and readiness probes

### Security and secret management

- Kubernetes Secret for API credential storage
- SealedSecret template for encrypting secrets before deployment
- Service account token mounted into the pod for metrics access
- Non-root container user configuration

## Important configuration and runtime details

### App configuration

The application reads these environment variables from the ConfigMap and Secret:

- `OMDB_API_URL`
- `THEME_COLOR`
- `POLL_INTERVAL_SECONDS`
- `OMDB_API_KEY`
- `POD_NAME`
- `POD_NAMESPACE`
- `K8S_TOKEN_PATH`

The values are configured in `chart/values.yaml` and passed into the deployment through the Helm templates.

### Secrets and configuration flow

The chart uses:

- `ConfigMap` for non-sensitive settings, such as theme color and polling interval
- `SealedSecret` for the OMDb API key
- Kubernetes-generated service account token for pod-level metrics queries

This follows a common Kubernetes pattern: keep public configuration separate from sensitive credentials.

### Metrics feature

The `/api/usage` endpoint reads the service account token from the default Kubernetes path and calls:

```text
https://kubernetes.default.svc/apis/metrics.k8s.io/v1beta1/namespaces/<namespace>/pods/<pod-name>
```

This requires the Kubernetes metrics-server to be installed in the cluster. Without it, the app will return an error like “Usage data unavailable”.

### Health checks

The app includes:

- `/healthz` for basic availability
- `/readyz` to ensure required app configuration is present

The Kubernetes deployment uses these endpoints for liveness and readiness probes.

## Local development

### Prerequisites

- Python 3.12+
- pip
- Docker (optional, for container testing)
- Kubernetes access if deploying to a cluster

### Run the app locally

From the project root:

```bash
cd app
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# or .venv\Scripts\activate  # Windows PowerShell

pip install -r requirements.txt

export OMDB_API_URL="http://www.omdbapi.com/"
export OMDB_API_KEY="your_omdb_api_key"
export THEME_COLOR="#1a1a2e"
export POLL_INTERVAL_SECONDS="10"

python app.py
```

Then open:

```text
http://localhost:8080
```

## Docker build

Build the image from the application directory:

```bash
cd app
docker build -t mymoviesproject:latest .
```

Run it locally:

```bash
docker run -p 8080:8080 --env OMDB_API_URL=http://www.omdbapi.com/ --env OMDB_API_KEY=your_key --env THEME_COLOR="#1a1a2e" --env POLL_INTERVAL_SECONDS=10 mymoviesproject:latest
```

## Helm deployment

From the project root:

```bash
helm upgrade --install demo-website ./chart --namespace demo-website --create-namespace
```

### Default values in `chart/values.yaml`

The chart currently configures:

- app name: `demo-website`
- image repository: `liadshe/demo-website`
- image tag: `v0.0.1-dev.10`
- service type: `ClusterIP`
- ingress enabled: `true`
- default theme color: `#1a1a2e`
- default polling interval: `10` seconds
- resource requests and limits for CPU and memory

### Ingress

The ingress is set to use the NGINX ingress class and defaults to a host named:

```text
movies-explorer.local
```
This is meant to be adjusted to match your cluster DNS or local hosts file.
