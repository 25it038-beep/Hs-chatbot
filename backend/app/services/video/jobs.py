"""Asynchronous Video Generation Job Manager with Queue and Concurrency Control."""

import os
import time
import uuid
import asyncio
import logging
from typing import Dict, List, Optional, Any
from app.services.video.schemas import (
    VideoGenerationRequest,
    VideoJobResponse,
    VideoJobStatus,
    VideoMode,
)
from app.services.video.models import model_registry
from app.services.video.router import video_router
from app.services.video.storage import video_storage
from app.services.video.validation import video_validator

logger = logging.getLogger("hsbot.video.jobs")


class VideoJobManager:
    """
    Manages asynchronous video generation jobs, queues, concurrency limits,
    state progression, and user-isolated history.
    """

    MAX_CONCURRENT_JOBS = 2

    def __init__(self):
        self._jobs: Dict[str, VideoJobResponse] = {}
        self._tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_JOBS)

    async def create_job(self, user_id: str, request: VideoGenerationRequest) -> VideoJobResponse:
        """Enqueues a new video generation job for the user."""
        job_id = f"vid_{uuid.uuid4().hex[:12]}"
        now = time.time()

        dim = model_registry.calculate_dimensions(request.resolution, request.aspect_ratio)

        job = VideoJobResponse(
            id=job_id,
            user_id=user_id,
            model=request.model,
            mode=request.mode.value,
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            status=VideoJobStatus.QUEUED,
            progress_stage="In queue waiting for execution slot",
            created_at=now,
            elapsed_seconds=0.0,
            parameters={
                "aspect_ratio": request.aspect_ratio,
                "resolution": request.resolution,
                "duration_seconds": request.duration_seconds,
                "fps": request.fps,
                "width": dim[0],
                "height": dim[1],
                "seed": request.seed,
                "reference_image_id": request.reference_image_id,
                "motion_strength": request.motion_strength,
            },
        )

        async with self._lock:
            self._jobs[job_id] = job

        # Launch background worker
        task = asyncio.create_task(self._process_job(job_id, user_id, request))
        self._tasks[job_id] = task

        return job

    async def _process_job(self, job_id: str, user_id: str, req: VideoGenerationRequest) -> None:
        """Worker lifecycle handling state progression from QUEUED to COMPLETED/FAILED."""
        # Wait for semaphore slot
        async with self._semaphore:
            job = self._jobs.get(job_id)
            if not job or job.status == VideoJobStatus.CANCELLED:
                return

            job.status = VideoJobStatus.SUBMITTING
            job.started_at = time.time()
            job.progress_stage = "Connecting to NVIDIA video inference service..."

            try:
                # 1. Resolve reference image if image-to-video
                ref_bytes: Optional[bytes] = None
                if req.mode == VideoMode.IMAGE_TO_VIDEO and req.reference_image_id:
                    ref_path = video_storage.get_reference_image_path(user_id, req.reference_image_id)
                    if ref_path and os.path.exists(ref_path):
                        with open(ref_path, "rb") as f:
                            ref_bytes = f.read()

                # 2. Get provider
                provider = video_router.get_provider(req.model)
                width, height = model_registry.calculate_dimensions(req.resolution, req.aspect_ratio)

                job.status = VideoJobStatus.GENERATING
                job.progress_stage = f"Synthesizing {req.duration_seconds}s video frames via {req.model}..."

                # 3. Call video provider (NVIDIA API)
                video_bytes = await provider.generate_video(
                    prompt=req.prompt,
                    negative_prompt=req.negative_prompt,
                    width=width,
                    height=height,
                    duration_seconds=req.duration_seconds,
                    fps=req.fps,
                    seed=req.seed,
                    reference_image_bytes=ref_bytes,
                )

                job.status = VideoJobStatus.PROCESSING
                job.progress_stage = "Verifying MP4 stream container and saving asset..."

                # 4. Validate output
                valid, err, meta = video_validator.validate_mp4_bytes(video_bytes)
                if not valid:
                    raise RuntimeError(f"Video validation failed: {err}")

                # 5. Persist isolated asset
                meta_dict = {
                    "job_id": job_id,
                    "user_id": user_id,
                    "model": req.model,
                    "mode": req.mode.value,
                    "prompt": req.prompt,
                    "width": width,
                    "height": height,
                    "duration_seconds": req.duration_seconds,
                    "fps": req.fps,
                    "created_at": job.created_at,
                    "completed_at": time.time(),
                }
                file_path, stream_url = video_storage.save_video(user_id, job_id, video_bytes, meta_dict)

                # 6. Mark COMPLETED
                job.status = VideoJobStatus.COMPLETED
                job.completed_at = time.time()
                job.elapsed_seconds = round(job.completed_at - (job.started_at or job.created_at), 2)
                job.progress_stage = "Video generation complete"
                job.stream_url = stream_url
                job.video_url = stream_url
                job.download_url = f"/api/video/{job_id}/download"
                job.duration_seconds = float(req.duration_seconds)
                job.width = width
                job.height = height
                job.file_size = len(video_bytes)

            except asyncio.CancelledError:
                job.status = VideoJobStatus.CANCELLED
                job.completed_at = time.time()
                job.progress_stage = "Job cancelled by user"
                job.elapsed_seconds = round(job.completed_at - (job.started_at or job.created_at), 2)
                logger.info(f"Video job {job_id} was cancelled.")

            except Exception as e:
                job.status = VideoJobStatus.FAILED
                job.completed_at = time.time()
                job.error_message = str(e)
                job.progress_stage = f"Generation failed: {str(e)}"
                job.elapsed_seconds = round(job.completed_at - (job.started_at or job.created_at), 2)
                logger.error(f"Video job {job_id} failed: {e}", exc_info=True)

            finally:
                self._tasks.pop(job_id, None)

    async def get_job(self, job_id: str, user_id: str) -> Optional[VideoJobResponse]:
        """Gets job status, updating real elapsed time."""
        job = self._jobs.get(job_id)
        if not job or job.user_id != user_id:
            # Check persisted storage metadata if not in active memory
            meta = video_storage.get_video_metadata(user_id, job_id)
            if meta:
                vpath = video_storage.get_video_path(user_id, job_id)
                size = os.path.getsize(vpath) if vpath and os.path.exists(vpath) else None
                return VideoJobResponse(
                    id=job_id,
                    user_id=user_id,
                    model=meta.get("model", "wan-ai/wan2.2"),
                    mode=meta.get("mode", "text_to_video"),
                    prompt=meta.get("prompt", ""),
                    status=VideoJobStatus.COMPLETED,
                    progress_stage="Completed",
                    created_at=meta.get("created_at", time.time()),
                    completed_at=meta.get("completed_at", time.time()),
                    elapsed_seconds=round(meta.get("completed_at", 0) - meta.get("created_at", 0), 2),
                    stream_url=f"/api/video/{job_id}/stream",
                    video_url=f"/api/video/{job_id}/stream",
                    download_url=f"/api/video/{job_id}/download",
                    duration_seconds=float(meta.get("duration_seconds", 5)),
                    width=meta.get("width", 1280),
                    height=meta.get("height", 720),
                    file_size=size,
                )
            return None

        # Update elapsed time if active
        if job.status in [VideoJobStatus.QUEUED, VideoJobStatus.SUBMITTING, VideoJobStatus.GENERATING, VideoJobStatus.PROCESSING]:
            ref_time = job.started_at or job.created_at
            job.elapsed_seconds = round(time.time() - ref_time, 2)

        return job

    async def cancel_job(self, job_id: str, user_id: str) -> bool:
        """Cancels an in-flight or queued job."""
        job = self._jobs.get(job_id)
        if not job or job.user_id != user_id:
            return False

        if job.status in [VideoJobStatus.COMPLETED, VideoJobStatus.FAILED, VideoJobStatus.CANCELLED]:
            return False

        task = self._tasks.get(job_id)
        if task and not task.done():
            task.cancel()

        job.status = VideoJobStatus.CANCELLED
        job.progress_stage = "Job cancelled by user"
        job.completed_at = time.time()
        return True

    async def list_user_jobs(self, user_id: str) -> List[VideoJobResponse]:
        """Lists all active and historical jobs for the user."""
        seen_ids = set()
        results: List[VideoJobResponse] = []

        # 1. In-memory jobs
        for j in self._jobs.values():
            if j.user_id == user_id:
                seen_ids.add(j.id)
                # Refresh elapsed time
                if j.status in [VideoJobStatus.QUEUED, VideoJobStatus.SUBMITTING, VideoJobStatus.GENERATING, VideoJobStatus.PROCESSING]:
                    ref_time = j.started_at or j.created_at
                    j.elapsed_seconds = round(time.time() - ref_time, 2)
                results.append(j)

        # 2. Disk-persisted jobs
        user_dir = video_storage._get_user_video_dir(user_id)
        if os.path.exists(user_dir):
            for fname in os.listdir(user_dir):
                if fname.endswith(".json"):
                    jid = fname[:-5]
                    if jid not in seen_ids:
                        meta = video_storage.get_video_metadata(user_id, jid)
                        if meta:
                            vpath = video_storage.get_video_path(user_id, jid)
                            size = os.path.getsize(vpath) if vpath and os.path.exists(vpath) else None
                            results.append(
                                VideoJobResponse(
                                    id=jid,
                                    user_id=user_id,
                                    model=meta.get("model", "wan-ai/wan2.2"),
                                    mode=meta.get("mode", "text_to_video"),
                                    prompt=meta.get("prompt", ""),
                                    status=VideoJobStatus.COMPLETED,
                                    progress_stage="Completed",
                                    created_at=meta.get("created_at", time.time()),
                                    completed_at=meta.get("completed_at", time.time()),
                                    elapsed_seconds=round(meta.get("completed_at", 0) - meta.get("created_at", 0), 2),
                                    stream_url=f"/api/video/{jid}/stream",
                                    video_url=f"/api/video/{jid}/stream",
                                    download_url=f"/api/video/{jid}/download",
                                    duration_seconds=float(meta.get("duration_seconds", 5)),
                                    width=meta.get("width", 1280),
                                    height=meta.get("height", 720),
                                    file_size=size,
                                )
                            )

        results.sort(key=lambda x: x.created_at, reverse=True)
        return results

    async def delete_job(self, job_id: str, user_id: str) -> bool:
        """Deletes a job and associated video asset."""
        await self.cancel_job(job_id, user_id)
        self._jobs.pop(job_id, None)
        return video_storage.delete_video(user_id, job_id)


video_job_manager = VideoJobManager()
