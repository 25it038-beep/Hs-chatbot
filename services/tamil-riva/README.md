# HSBot — NVIDIA Riva Tamil Voice Service

This directory contains the standalone production deployment assets for **Tamil Live Voice** on an external NVIDIA GPU instance.

## Architecture
```text
Browser Mic (ta-IN)
      ↓
Render Backend (HSBot)
      ↓ (gRPC streaming / port 50051)
External NVIDIA GPU Server
  - NVIDIA Riva Speech Server 2.15+
  - Tamil Conformer-CTC ASR (`riva-tamil-conformer-asr`)
  - Tamil FastPitch + HiFi-GAN TTS (`riva-tamil-fastpitch-tts`)
      ↓
Render Backend
      ↓ (NVIDIA Llama-3.2-11b with Tamil system instruction)
Synthesized Tamil Audio Stream (24000Hz PCM)
      ↓
Browser Speaker
```

## Why External GPU?
Render is a lightweight CPU container platform. NVIDIA Riva requires:
1. NVIDIA GPU with Compute Capability >= 7.0 (Volta, Turing, Ampere, Ada Lovelace, Hopper).
2. Recommended GPUs: NVIDIA T4 (16GB), L4 (24GB), or A10G (24GB).
3. NVIDIA Container Toolkit and NVIDIA Driver >= 525.60.13.

## Step 1: Model Preparation with NVIDIA NeMo
1. **ASR Model (`ta_conformer_ctc.nemo`)**:
   - Trained or fine-tuned on Tamil speech (CommonVoice Tamil + Shruti Indic corpus).
   - Export to Riva RMIR format:
     ```bash
     nemo2riva --out ta_conformer.riva ta_conformer_ctc.nemo --key <riva-key>
     ```

2. **TTS Model (`ta_fastpitch.nemo` + `ta_hifigan.nemo`)**:
   - Trained on Tamil single-speaker audio (24000Hz).
   - Export to Riva RMIR format:
     ```bash
     nemo2riva --out ta_fastpitch.riva ta_fastpitch.nemo --key <riva-key>
     ```

## Step 2: Build & Deploy Riva Models
```bash
# Build ASR RMIR
riva-build speech_recognition /data/models/ta_asr.rmir /data/models/ta_conformer.riva \
    --language_code=ta-IN

# Build TTS RMIR
riva-build speech_synthesis /data/models/ta_tts.rmir /data/models/ta_fastpitch.riva \
    --voice_name=ta-IN-Standard \
    --language_code=ta-IN

# Deploy models to Triton repository
riva-deploy /data/models/ta_asr.rmir /data/models/repository
riva-deploy /data/models/ta_tts.rmir /data/models/repository
```

## Step 3: Run Riva Server via Docker Compose
```bash
docker compose up -d
```
Verify port 50051 is open:
```bash
nc -zv <gpu-host-ip> 50051
```

## Step 4: Configure HSBot on Render
Set the following environment variables in the Render Dashboard for `hs-chatbot-2`:
- `TAMIL_VOICE_ENABLED=true`
- `TAMIL_RIVA_HOST=<gpu-host-ip>`
- `TAMIL_RIVA_PORT=50051`

Once configured, HSBot automatically detects the active Riva server, enables the Tamil button (`Tamil LIVE`), and begins routing Tamil audio chunks without touching the English pipeline.
