# Dockerfile for the FastAPI backend + simulator runtime.
# The image bundles both the backend (read-side API + run launcher) and
# the simulator itself, so the launcher can spawn `python -m
# experiments.sweep` in the same container.

FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Build deps for scientific Python wheels (statsmodels, scipy).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        git \
    && rm -rf /var/lib/apt/lists/*

# Install simulator deps first (changes less often than backend code).
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

# Then the backend-only deps.
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install -r /app/backend/requirements.txt

# Finally the code.
COPY src /app/src
COPY experiments /app/experiments
COPY scripts /app/scripts
COPY data /app/data
COPY backend /app/backend

# Canonical thesis results are baked into a *baseline* path so the
# runtime entrypoint can sync them into the `results-data` named volume
# (which would otherwise shadow /app/results). See backend/entrypoint.sh.
COPY results /app/results-baseline

ENV PYTHONPATH=/app

EXPOSE 8000

COPY backend/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
