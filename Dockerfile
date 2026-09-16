FROM python:3.12-slim

ENV PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

# System deps (no Node.js needed — pure Python gRPC replaces Node.js bridge)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies (includes grpcio + grpcio-tools for Riva gRPC bridge)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY backend/ .

# Copy Riva proto definitions
COPY proto/ /app/proto/

# Generate Python gRPC stubs from Riva proto files
# Output goes to app/live/grpc_stubs/ so riva_python_bridge.py can import them
RUN mkdir -p app/live/grpc_stubs && \
    python -m grpc_tools.protoc \
        -I /app/proto \
        --python_out=app/live/grpc_stubs \
        --grpc_python_out=app/live/grpc_stubs \
        riva/proto/riva_asr.proto \
        riva/proto/riva_tts.proto \
        riva/proto/riva_audio.proto \
        riva/proto/riva_common.proto && \
    touch app/live/grpc_stubs/__init__.py \
          app/live/grpc_stubs/riva/__init__.py \
          app/live/grpc_stubs/riva/proto/__init__.py && \
    echo "gRPC stubs generated:" && ls app/live/grpc_stubs/riva/proto/

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
