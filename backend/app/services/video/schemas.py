"""Video generation request, response, and job data schemas."""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class VideoMode(str, Enum):
    TEXT_TO_VIDEO = "text_to_video"
    IMAGE_TO_VIDEO = "image_to_video"


class VideoJobStatus(str, Enum):
    QUEUED = "queued"
    SUBMITTING = "submitting"
    GENERATING = "generating"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VideoGenerationRequest(BaseModel):
    prompt: str = Field(..., min_length=2, max_length=2000, description="Cinematic descriptive prompt for video")
    negative_prompt: Optional[str] = Field(None, max_length=1000, description="Undesired elements to avoid")
    model: str = Field("wan-ai/wan2.2", description="Video model identifier")
    mode: VideoMode = Field(VideoMode.TEXT_TO_VIDEO, description="Generation modality")
    aspect_ratio: str = Field("16:9", description="Aspect ratio: 16:9, 9:16, 1:1, 4:3")
    duration_seconds: int = Field(5, ge=3, le=10, description="Target duration in seconds")
    resolution: str = Field("720p", description="Output resolution: 480p, 720p, 1080p")
    fps: int = Field(24, ge=12, le=60, description="Frames per second")
    seed: Optional[int] = Field(None, description="Optional random seed for reproducibility")
    reference_image_id: Optional[str] = Field(None, description="Reference image ID for image-to-video")
    motion_strength: Optional[float] = Field(1.0, ge=0.1, le=2.0, description="Motion amplitude scale")


class VideoJobResponse(BaseModel):
    id: str
    user_id: str
    model: str
    mode: str
    prompt: str
    negative_prompt: Optional[str] = None
    status: VideoJobStatus
    progress_stage: str
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    elapsed_seconds: float = 0.0
    video_url: Optional[str] = None
    stream_url: Optional[str] = None
    download_url: Optional[str] = None
    duration_seconds: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    file_size: Optional[int] = None
    error_message: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class EnhancePromptRequest(BaseModel):
    prompt: str = Field(..., min_length=2, max_length=1000)
    style: Optional[str] = Field("cinematic", description="Style genre (cinematic, realistic, anime, documentary, timelapse)")


class EnhancePromptResponse(BaseModel):
    original_prompt: str
    enhanced_prompt: str
    camera_movement: Optional[str] = None
    lighting: Optional[str] = None
    style: Optional[str] = None


class VideoModelCapability(BaseModel):
    model_id: str
    name: str
    provider: str
    modes: List[str]
    resolutions: List[str]
    aspect_ratios: List[str]
    durations: List[int]
    default_fps: int
    description: str
    status: str = "available"
