# Production-ready Dockerfile for LinkPlease backend
# Based on the project's verified local Python version (backend/venv/pyvenv.cfg)

FROM python:3.13-slim

# Prevent Python from writing .pyc files and enable unbuffered stdout/stderr
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Create a non-root user for running the app
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Install dependencies from the reproducible pinned file generated from the verified local env
COPY backend/requirements-pinned.txt /app/requirements-pinned.txt
RUN pip install --no-cache-dir -r /app/requirements-pinned.txt \
    && pip install --no-cache-dir psycopg2-binary==2.9.12

# Copy application code
COPY backend/ /app/

# Ensure files are owned by the non-root user
RUN chown -R appuser:appuser /app

USER appuser

# Expose default port (runtime may override via PORT env)
EXPOSE 8000

# Bind to 0.0.0.0 and support Render's dynamic PORT while keeping the app in the foreground.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
