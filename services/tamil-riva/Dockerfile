# NVIDIA Riva Tamil Speech Service
# Standalone microservice for hosting custom NVIDIA NeMo Tamil ASR & TTS models.
FROM nvcr.io/nvidia/riva/riva-speech:2.15.0-servicemaker

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /opt/riva

# Copy configuration and service scripts
COPY config/config.sh /opt/riva/config.sh
COPY models/ /opt/riva/models/
COPY server/ /opt/riva/server/

EXPOSE 50051 8001 8002

HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
  CMD trt-server-client --url localhost:8001 || exit 1

ENTRYPOINT ["/opt/riva/bin/riva_server"]
CMD ["--config_file=/opt/riva/config.sh"]
