# Python Frontend (Flask)

This directory contains the Python-based frontend application using **Flask**, replacing the previous ReactJS application.

## Prerequisites

- Python 3.9+
- Pip
- (Optional) PostgreSQL DB for session storage (uses local filesystem by default)

## Installation (Local)

1. Navigate to this directory:
   ```bash
   cd frontend_python
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python app.py
   ```
   Or use the provided batch script in the root directory: `start_frontend_python.bat`.
   The app runs on `http://localhost:5000`.

## Configuration

The application uses the following environment variables:

- `API_URL`: The URL of the backend API.
  - Default: `http://backend:5000` (Internal K8s service)
  - For local development: Set to `http://localhost:5000`

- `SQLALCHEMY_DATABASE_URI` (Optional): Database URI for storing user sessions.
  - If not provided, it falls back to constructing it from `POSTGRES_USER`, `POSTGRES_PASSWORD`, etc. if available.
  - If no DB config is found, it uses **filesystem** sessions (dev mode).

## Deployment

The Dockerfile in this directory builds the Flask application.
The Kubernetes deployment (`k8s/frontend.yaml`) has been updated to use port `5000` and inject `app-secrets`.

### Building the Image

```bash
docker build -t frontend:latest .
```

## Features

- **Persistent Sessions**: User login is persisted across refreshes via cookies (and optional DB storage).
- Login (Authentication via Backend)
- Dashboard (List KTP records)
- Search & Pagination
- CRUD Operations (Create, Read, Update, Delete)
