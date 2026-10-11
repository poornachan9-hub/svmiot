# ============================================================
# SecureIoT-X Backend — Docker Image
# ============================================================
# Python 3.10 + FastAPI + SVM model + all project modules
# ============================================================

FROM python:3.10-slim

WORKDIR /app

# System dependencies for scikit-learn, numpy, web3
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies (cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project source code and assets
COPY backend/ backend/
COPY ai_engine/ ai_engine/
COPY blockchain/ blockchain/
COPY security/ security/
COPY simulation/ simulation/
COPY iot/ iot/
COPY config/ config/
COPY database/ database/
COPY sdn/ sdn/
COPY contracts/ contracts/
COPY pyproject.toml .

# Copy trained SVM model + preprocessing pipeline
COPY models/ models/

# Copy datasets (needed for model registry metadata)
COPY datasets/ datasets/

# Create runtime directories
RUN mkdir -p logs reports

EXPOSE 8000

# Health check — backend /api/health endpoint
HEALTHCHECK --interval=15s --timeout=10s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

CMD ["python", "-m", "backend"]
