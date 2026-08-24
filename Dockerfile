# Voice Command Shopping Assistant — single-service production image.
#
# The React app is built in stage one and copied next to the backend in stage
# two, so FastAPI serves both the API and the frontend from one origin. That is
# what lets the frontend call "/api/..." with no configured base URL and no CORS.

# --- Stage 1: build the frontend ------------------------------------------- #
FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend

# Copy manifests first so the dependency layer is cached between builds.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# --- Stage 2: runtime ------------------------------------------------------- #
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

WORKDIR /app/backend

# Render (and most platforms) inject PORT; 8000 is the local default.
EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
