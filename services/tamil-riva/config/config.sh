#!/usr/bin/env bash
# NVIDIA Riva Configuration for Tamil (ta-IN)
# Configures ASR (Conformer-CTC) and TTS (FastPitch + HiFi-GAN) for Tamil speech.

# Target GPU Family: tegra, pascal, volta, turing, ampere, hopper
riva_target_gpu_family="ampere"

# Services to enable
service_enabled_asr=true
service_enabled_nlp=false
service_enabled_tts=true

# Language configuration
language_code="ta-IN"

# Custom NeMo Tamil Model Artifacts
asr_model_name="riva-tamil-conformer-asr"
asr_acoustic_model="ta_conformer_ctc.nemo"
asr_decoder_type="greedy"

tts_model_name="riva-tamil-fastpitch-tts"
tts_acoustic_model="ta_fastpitch.nemo"
tts_vocoder_model="ta_hifigan.nemo"
tts_voice_name="ta-IN-Standard"
tts_sample_rate=24000

# Riva Server Ports
riva_server_port=50051
triton_http_port=8001
triton_metrics_port=8002
