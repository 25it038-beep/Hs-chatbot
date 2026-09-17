FROM python:3.12-slim

ENV PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

# Install system dependencies + Node.js 20 LTS (required for persistent_riva_worker.js Riva gRPC bridge)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gnupg \
    tesseract-ocr \
    tesseract-ocr-eng \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY backend/ .

# Install Node dependencies for Riva gRPC bridge (@grpc/grpc-js + @grpc/proto-loader)
COPY package.json /app/package.json
RUN npm install --omit=dev --prefix /app

# Copy Riva proto definitions
COPY proto/ /app/proto/

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
