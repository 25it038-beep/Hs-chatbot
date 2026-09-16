# HSBot Persistent Riva Bridge
import asyncio
import base64
import json
import logging
import os
import sys
from typing import AsyncGenerator, Dict, Optional
import uuid

logger = logging.getLogger('hsbot.live.riva_bridge')

WORKER_SCRIPT = os.path.join(os.path.dirname(__file__), 'persistent_riva_worker.js')

class PersistentRivaBridge:
    def __init__(self):
        self._proc: Optional[asyncio.subprocess.Process] = None
        self._lock = asyncio.Lock()
        self._reader_task: Optional[asyncio.Task] = None
        self._pending_asr: Dict[str, asyncio.Future] = {}
        self._pending_tts_queues: Dict[str, asyncio.Queue] = {}
        self._is_ready = False
        self._ready_event = asyncio.Event()

    async def ensure_started(self):
        async with self._lock:
            if self._proc and self._proc.returncode is None:
                return

            logger.info('Spawning persistent Riva worker process...')
            self._ready_event.clear()
            self._is_ready = False

            try:
                self._proc = await asyncio.create_subprocess_exec(
                    'node',
                    WORKER_SCRIPT,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            except Exception as e:
                logger.error(f'Failed to spawn persistent Riva worker: {e}')
                raise

            if self._reader_task and not self._reader_task.done():
                self._reader_task.cancel()
            self._reader_task = asyncio.create_task(self._read_stdout())
            asyncio.create_task(self._read_stderr())

            try:
                await asyncio.wait_for(self._ready_event.wait(), timeout=5.0)
                logger.info('Persistent Riva worker ready (gRPC channels warm)')
            except asyncio.TimeoutError:
                logger.warning('Timed out waiting for Riva worker ready event, proceeding anyway')

    async def _read_stderr(self):
        while self._proc and self._proc.returncode is None:
            try:
                line = await self._proc.stderr.readline()
                if not line:
                    break
                text = line.decode('utf-8', errors='replace').strip()
                if text:
                    logger.info(f'[RivaNode] {text}')
            except Exception:
                break

    async def _read_stdout(self):
        while self._proc and self._proc.returncode is None:
            try:
                line = await self._proc.stdout.readline()
                if not line:
                    break
                text = line.decode('utf-8', errors='replace').strip()
                if not text:
                    continue

                try:
                    data = json.loads(text)
                except Exception:
                    logger.warning(f'Malformed JSON from worker: {text[:100]}')
                    continue

                msg_type = data.get('type')

                if msg_type == 'ready':
                    self._is_ready = True
                    self._ready_event.set()

                elif msg_type == 'asr_final':
                    req_id = data.get('id')
                    if req_id and req_id in self._pending_asr:
                        fut = self._pending_asr.pop(req_id)
                        if not fut.done():
                            fut.set_result(data.get('text', ''))

                elif msg_type == 'asr_error':
                    req_id = data.get('id')
                    if req_id and req_id in self._pending_asr:
                        fut = self._pending_asr.pop(req_id)
                        if not fut.done():
                            fut.set_exception(RuntimeError(data.get('error', 'ASR error')))

                elif msg_type == 'tts_chunk':
                    req_id = data.get('id')
                    if req_id and req_id in self._pending_tts_queues:
                        q = self._pending_tts_queues[req_id]
                        audio_b64 = data.get('audio', '')
                        if audio_b64:
                            pcm = base64.b64decode(audio_b64)
                            await q.put(pcm)

                elif msg_type == 'tts_end':
                    req_id = data.get('id')
                    if req_id and req_id in self._pending_tts_queues:
                        q = self._pending_tts_queues[req_id]
                        await q.put(None)

                elif msg_type == 'tts_error':
                    req_id = data.get('id')
                    if req_id and req_id in self._pending_tts_queues:
                        q = self._pending_tts_queues[req_id]
                        await q.put(RuntimeError(data.get('error', 'TTS error')))

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f'Error reading worker stdout: {e}')
                break

    async def _send_json(self, req: dict):
        if not self._proc or self._proc.returncode is not None or not self._proc.stdin:
            raise RuntimeError('Persistent Riva worker process is not running')
        line = json.dumps(req) + chr(10)
        self._proc.stdin.write(line.encode('utf-8'))
        await self._proc.stdin.drain()

    async def transcribe(self, pcm_bytes: bytes, sample_rate: int = 16000, timeout: float = 8.0) -> str:
        if not pcm_bytes:
            return ''

        await self.ensure_started()
        req_id = f'asr_{uuid.uuid4().hex[:8]}'
        audio_b64 = base64.b64encode(pcm_bytes).decode('ascii')

        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self._pending_asr[req_id] = fut

        try:
            await self._send_json({
                'action': 'asr',
                'id': req_id,
                'audio': audio_b64,
                'sample_rate': sample_rate,
            })
            return await asyncio.wait_for(fut, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f'ASR request {req_id} timed out after {timeout}s')
            self._send_json_sync_safe({'action': 'cancel', 'id': req_id})
            return ''
        except Exception as e:
            logger.error(f'ASR error for {req_id}: {e}')
            return ''
        finally:
            self._pending_asr.pop(req_id, None)

    async def stream_synthesize(
        self,
        text: str,
        voice: str = 'Chatterbox-Multilingual',
        sample_rate: int = 24000,
        timeout: float = 12.0
    ) -> AsyncGenerator[bytes, None]:
        clean_text = text.strip()
        if not clean_text:
            return

        await self.ensure_started()
        req_id = f'tts_{uuid.uuid4().hex[:8]}'
        q = asyncio.Queue()
        self._pending_tts_queues[req_id] = q

        try:
            await self._send_json({
                'action': 'tts_stream',
                'id': req_id,
                'text': clean_text,
                'voice': voice,
                'sample_rate': sample_rate,
            })

            while True:
                try:
                    item = await asyncio.wait_for(q.get(), timeout=timeout)
                except asyncio.TimeoutError:
                    logger.warning(f'TTS stream {req_id} timed out waiting for chunk')
                    self._send_json_sync_safe({'action': 'cancel', 'id': req_id})
                    break

                if item is None:
                    break
                if isinstance(item, Exception):
                    logger.error(f'TTS stream error for {req_id}: {item}')
                    break
                yield item

        except asyncio.CancelledError:
            self._send_json_sync_safe({'action': 'cancel', 'id': req_id})
            raise
        finally:
            self._pending_tts_queues.pop(req_id, None)

    def _send_json_sync_safe(self, req: dict):
        try:
            if self._proc and self._proc.returncode is None and self._proc.stdin:
                line = json.dumps(req) + chr(10)
                self._proc.stdin.write(line.encode('utf-8'))
        except Exception:
            pass

    async def cancel(self, req_id: str):
        self._send_json_sync_safe({'action': 'cancel', 'id': req_id})
        if req_id in self._pending_asr:
            fut = self._pending_asr.pop(req_id)
            if not fut.done():
                fut.cancel()
        if req_id in self._pending_tts_queues:
            self._pending_tts_queues.pop(req_id, None)

    async def shutdown(self):
        if self._proc and self._proc.returncode is None:
            try:
                self._proc.terminate()
                await asyncio.wait_for(self._proc.wait(), timeout=2.0)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
        if self._reader_task and not self._reader_task.done():
            self._reader_task.cancel()
        self._proc = None
        self._is_ready = False
        logger.info('Persistent Riva worker shut down')

riva_bridge = PersistentRivaBridge()
