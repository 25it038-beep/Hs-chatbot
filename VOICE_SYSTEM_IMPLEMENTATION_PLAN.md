# HSBot Voice Automation System - Implementation Plan

## Overview
Building a production-grade, hands-free voice assistant system with continuous listening, wake-word activation, speaker verification, multi-user support, and SaaS architecture.

## Architecture Components

### Phase 1: Core Voice Service (Windows Background Service)
**Purpose:** Always-listening, low-power voice processing

```
Voice Service (Backend)
├── Microphone Listener (PyAudio)
├── Voice Activity Detection (VAD)
├── Wake Word Detector (Porcupine/Snowboy)
├── Speaker Verification (Resemblyzer/Speechbrain)
├── Command Queue
└── IPC Interface (WebSocket/Named Pipes)
```

**Tech Stack:**
- Python FastAPI (already available)
- PyAudio for microphone input
- Silero VAD (lightweight, on-device)
- Porcupine SDK for wake-word detection
- Resemblyzer for speaker embeddings
- SQLite for local profiles
- WebSocket for IPC to UI

### Phase 2: SaaS Backend Voice APIs
**Purpose:** Account management, multi-user support, device sync

```
APIs:
- POST /api/voice/enroll          (Create voice profile)
- POST /api/voice/verify          (Verify speaker)
- GET /api/voice/profile          (Get user profile)
- DELETE /api/voice/profile       (Delete profile)
- GET /api/devices                (List devices)
- POST /api/devices               (Add device)
- DELETE /api/devices/{id}        (Revoke device)
- GET /api/automation/history     (Execution logs)
- POST /api/automation/execute    (Run command via voice)
- GET/PUT /api/voice/settings     (Settings)
```

### Phase 3: Database Schema
**Organization Structure:**

```
organizations
├── id (primary key)
├── name
├── created_at
└── updated_at

users
├── id
├── org_id (foreign key)
├── email
├── voice_enabled
└── permissions

voice_profiles
├── id
├── user_id (foreign key)
├── org_id (foreign key)
├── embedding (encrypted vector)
├── confidence_threshold
├── anti_spoofing_enabled
├── created_at
└── status (active/inactive)

devices
├── id
├── user_id (foreign key)
├── org_id (foreign key)
├── name
├── device_type (desktop/laptop/mobile)
├── last_seen
├── voice_enabled
└── status (active/paused/revoked)

voice_sessions
├── id
├── user_id
├── device_id
├── wake_word_detected_at
├── command_text
├── confidence_score
├── status (success/failed/blocked)
├── created_at

automation_history
├── id
├── user_id
├── org_id
├── command
├── status
├── permission_required
├── executed_at
```

### Phase 4: Frontend Components

**Settings Page:**
- Always Listening ON/OFF
- Wake Word selector
- Voice Match ON/OFF
- Continuous Conversation mode
- Activation Timeout slider
- Microphone selector

**Voice Enrollment:**
- Step-by-step enrollment UI
- 3-step voice sample recording
- Progress indicator
- Confidence calibration

**Microphone Status:**
- Visual indicator (mic icon)
- Status label (Listening / Active / Paused)
- Quick mute button
- Disable microphone option

**Device Management:**
- List active devices
- Add/rename/revoke devices
- Voice automation status per device

### Phase 5: Local Voice Service Components

**VoiceListener (Main Service):**
- Runs as Windows service
- Monitors microphone
- Detects wake word
- Performs speaker verification
- Routes to automation engine

**VAD (Voice Activity Detection):**
- Filters silence
- Reduces CPU/network usage
- Configurable threshold

**Wake Word Detector:**
- Lightweight on-device processing
- Supports multiple wake words
- Configurable sensitivity

**Speaker Verification:**
- Compares voice against stored embeddings
- Returns confidence score
- Anti-spoofing detection

## Security Architecture

```
┌─────────────────────────────────────────────┐
│ User Voice Input (Microphone)               │
└────────────┬────────────────────────────────┘
             │
┌────────────▼────────────────────────────────┐
│ Local VAD & Wake Word Detection             │ ← No data sent
└────────────┬────────────────────────────────┘
             │
┌────────────▼────────────────────────────────┐
│ Speaker Verification (Local Embedding)      │ ← No raw audio
└────────────┬────────────────────────────────┘
             │
          Verified?
             │
        ┌────┴────┐
    YES │         │ NO
        │         └─ Reject/Log attempt
        │
┌───────▼──────────────────────────────────┐
│ Send Command Text to Cloud               │ ← Only text
└───────┬──────────────────────────────────┘
        │
┌───────▼──────────────────────────────────┐
│ Permission Check (Role-Based)            │
└───────┬──────────────────────────────────┘
        │
┌───────▼──────────────────────────────────┐
│ Risk Assessment & Confirmation           │
└───────┬──────────────────────────────────┘
        │
┌───────▼──────────────────────────────────┐
│ Execute Automation                       │
└────────────────────────────────────────────┘
```

## Encryption Strategy

**At Rest:**
- Voice embeddings: AES-256 encryption with org-specific key
- Device tokens: Hashed with bcrypt
- Profiles: Encrypted in database

**In Transit:**
- HTTPS/TLS for all API calls
- WSS (secure WebSocket) for IPC
- Device-to-service communication authenticated with JWT

**Never Stored:**
- Raw voice recordings
- Authentication tokens (except short-lived JWT)
- User passwords
- Biometric raw data

## Implementation Phases

### Phase 1A: Core Voice Service (Days 1-3)
1. Create Windows service wrapper
2. Implement PyAudio microphone listener
3. Add Silero VAD
4. Basic wake-word detection
5. WebSocket IPC to UI

### Phase 1B: Speaker Verification (Days 4-5)
1. Implement speaker embedding system
2. Create voice enrollment flow
3. Add speaker verification
4. Implement anti-spoofing basics

### Phase 2: SaaS Backend (Days 6-8)
1. Create database schema
2. Implement voice APIs
3. Add device management
4. Implement multi-tenant authorization

### Phase 3: Frontend UI (Days 9-11)
1. Voice Settings page
2. Microphone status indicator
3. Device management UI
4. Voice enrollment flow

### Phase 4: Integration & Testing (Days 12-13)
1. Connect frontend to backend
2. End-to-end testing
3. Security audit
4. Performance optimization

### Phase 5: EXE Rebuild (Day 14)
1. Update all configurations
2. Build Tauri desktop app
3. Package with service installer
4. Create deployment guide

## Key Files to Create/Modify

**Backend:**
- `backend/app/services/voice/__init__.py` (Voice service module)
- `backend/app/services/voice/listener.py` (Microphone listener)
- `backend/app/services/voice/vad.py` (Voice activity detection)
- `backend/app/services/voice/wake_word.py` (Wake word detection)
- `backend/app/services/voice/speaker_verification.py` (Voice match)
- `backend/app/api/voice.py` (Voice REST API)
- `backend/app/models/voice.py` (Database models)

**Desktop Service:**
- `backend/services/voice_service.py` (Windows service entry)
- `backend/services/voice_listener.exe.spec` (PyInstaller spec)

**Frontend:**
- `frontend/src/pages/VoiceSettings.tsx` (Settings page)
- `frontend/src/components/MicrophoneStatus.tsx` (Mic indicator)
- `frontend/src/components/VoiceEnrollment.tsx` (Enrollment flow)
- `frontend/src/components/DeviceManager.tsx` (Device management)
- `frontend/src/hooks/useVoiceService.ts` (Voice service hook)

**Desktop:**
- `desktop/src-tauri/src/voice_service.rs` (Tauri voice service bridge)
- `desktop/src/lib/voice.ts` (Frontend voice utilities)

## Technology Stack

**Voice Processing:**
- Silero VAD (lightweight, on-device)
- Porcupine SDK (wake-word detection)
- Resemblyzer (speaker embeddings)
- PyAudio (microphone access)

**Backend:**
- FastAPI (already available)
- SQLAlchemy (database ORM)
- PostgreSQL or SQLite

**Frontend:**
- React 19
- TypeScript
- TanStack Query for API calls
- WebSocket client

**Desktop:**
- Tauri 2
- Rust for service wrapper

**Security:**
- JWT for authentication
- bcrypt for hashing
- AES-256 for encryption
- TLS for transport

## Environment Variables

```
VOICE_SERVICE_ENABLED=true
VOICE_SERVICE_PORT=50051
VOICE_WAKE_WORD=Hey HS
VOICE_CONFIDENCE_THRESHOLD=0.85
VOICE_CONTINUOUS_TIMEOUT=10
VAD_THRESHOLD=0.5
PORCUPINE_API_KEY=<from Picovoice>
SPEAKER_VERIFICATION_MODEL=resemblyzer
VOICE_PROFILES_ENCRYPTED=true
```

## Next Steps

1. **Create memory file** with implementation status
2. **Start Phase 1A:** Build voice service core
3. **Implement VAD** and wake-word detection
4. **Build speaker verification** system
5. **Create SaaS APIs** for multi-user support
6. **Build frontend UI** for voice settings
7. **End-to-end testing** and security hardening
8. **Rebuild EXE** with all components integrated

## Success Criteria

- ✅ Always-listening background service active
- ✅ Wake-word detection working reliably
- ✅ Speaker verification with >90% accuracy
- ✅ Multi-user support fully working
- ✅ Device management operational
- ✅ Voice commands executing through automation engine
- ✅ Audio response generation working
- ✅ Security audit passed
- ✅ <200ms latency from wake word to execution start
- ✅ <50MB memory footprint for voice service
- ✅ EXE builds and deploys successfully
