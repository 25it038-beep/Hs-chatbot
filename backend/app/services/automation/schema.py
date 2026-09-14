"""Automation intent and action schemas using dataclasses."""

from dataclasses import dataclass, field
from typing import Any, Optional, List
from enum import Enum
from datetime import datetime


class IntentType(str, Enum):
    """All supported automation intent types."""
    OPEN_APPLICATION = "open_application"
    CLOSE_APPLICATION = "close_application"
    RESTART_APPLICATION = "restart_application"
    SWITCH_APPLICATION = "switch_application"
    MINIMIZE_APPLICATION = "minimize_application"
    MAXIMIZE_APPLICATION = "maximize_application"
    
    CREATE_FOLDER = "create_folder"
    CREATE_FILE = "create_file"
    DELETE_FOLDER = "delete_folder"
    DELETE_FILE = "delete_file"
    RENAME_FILE = "rename_file"
    RENAME_FOLDER = "rename_folder"
    MOVE_FILE = "move_file"
    MOVE_FOLDER = "move_folder"
    COPY_FILE = "copy_file"
    COPY_FOLDER = "copy_folder"
    SEARCH_FILES = "search_files"
    SEARCH_FOLDERS = "search_folders"
    FILE_METADATA = "file_metadata"
    OPEN_FOLDER = "open_folder"
    OPEN_FILE = "open_file"
    
    KEY_PRESS = "key_press"
    TYPE_TEXT = "type_text"
    
    CLICK = "click"
    RIGHT_CLICK = "right_click"
    DOUBLE_CLICK = "double_click"
    SCROLL = "scroll"
    DRAG = "drag"
    
    SET_VOLUME = "set_volume"
    ADJUST_VOLUME = "adjust_volume"
    GET_VOLUME = "get_volume"
    GET_CPU_USAGE = "get_cpu_usage"
    GET_RAM_USAGE = "get_ram_usage"
    GET_DISK_USAGE = "get_disk_usage"
    TAKE_SCREENSHOT = "take_screenshot"
    LOCK_SCREEN = "lock_screen"
    SLEEP = "sleep"
    RESTART = "restart"
    SHUTDOWN = "shutdown"
    CHECK_WIFI = "check_wifi"
    CHECK_BLUETOOTH = "check_bluetooth"
    CHECK_NETWORK = "check_network"
    CHECK_BATTERY = "check_battery"
    GET_BRIGHTNESS = "get_brightness"
    SET_BRIGHTNESS = "set_brightness"
    
    MAXIMIZE_WINDOW = "maximize_window"
    MINIMIZE_WINDOW = "minimize_window"
    RESTORE_WINDOW = "restore_window"
    CLOSE_WINDOW = "close_window"
    SNAP_WINDOW_LEFT = "snap_window_left"
    SNAP_WINDOW_RIGHT = "snap_window_right"
    SHOW_DESKTOP = "show_desktop"
    
    OPEN_URL = "open_url"
    SEARCH_WEB = "search_web"
    OPEN_NEW_TAB = "open_new_tab"
    CLOSE_TAB = "close_tab"
    REFRESH_PAGE = "refresh_page"
    GO_BACK = "go_back"
    GO_FORWARD = "go_forward"
    
    LIST_PROCESSES = "list_processes"
    START_PROCESS = "start_process"
    STOP_PROCESS = "stop_process"
    RESTART_PROCESS = "restart_process"
    MONITOR_PROCESS = "monitor_process"
    RUN_COMMAND = "run_command"
    RUN_SCRIPT = "run_script"
    
    UNKNOWN = "unknown"


class RiskLevel(str, Enum):
    """Risk classification for automation actions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AutomationIntent:
    """Structured intent representing a user's automation request."""
    intent: IntentType
    category: str
    target: Optional[str] = None
    parameters: dict = field(default_factory=dict)
    confidence: float = 0.5
    risk_level: RiskLevel = RiskLevel.LOW
    requires_confirmation: bool = False
    explanation: str = ""


@dataclass
class AutomationAction:
    """Executable automation action."""
    action_id: str
    intent: AutomationIntent
    state: str = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None
    verification_passed: bool = False


@dataclass
class AutomationResponse:
    """Response from automation engine."""
    success: bool
    action_id: str
    message: str
    result: Optional[Any] = None
    error: Optional[str] = None
    requires_confirmation: bool = False
    confirmation_prompt: Optional[str] = None
    execution_time_ms: Optional[float] = None
    spoken: Optional[str] = None
    options: Optional[List[str]] = None
    step_index: int = 1
    total_steps: int = 1
    
    def to_dict(self):
        """Convert response to dictionary."""
        return {
            "success": self.success,
            "action_id": self.action_id,
            "message": self.message,
            "result": self.result,
            "error": self.error,
            "requires_confirmation": self.requires_confirmation,
            "confirmation_prompt": self.confirmation_prompt,
            "execution_time_ms": self.execution_time_ms,
            "spoken": self.spoken,
            "options": self.options,
            "step_index": self.step_index,
            "total_steps": self.total_steps,
        }


@dataclass
class CommandChain:
    """A sequence of automation commands to execute."""
    chain_id: str
    name: str
    description: str
    commands: List[str] = field(default_factory=list)
    parallel: bool = False
    stop_on_error: bool = True
    created_at: Optional[str] = None
    executed_at: Optional[str] = None
