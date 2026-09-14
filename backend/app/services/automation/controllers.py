"""Platform-specific controllers for OS automation."""

import logging
import os
import platform
import re
import subprocess
from dataclasses import dataclass
from typing import Optional, Any
import uuid

from .schema import IntentType

logger = logging.getLogger("hsbot.automation.controllers")


@dataclass
class ControllerResult:
    """Result from executing a controller action."""
    success: bool
    message: str
    data: Optional[Any] = None
    error: Optional[str] = None


class BaseController:
    """Base class for platform-specific controllers."""
    
    def __init__(self):
        self.os_type = platform.system().lower()
        self.is_windows = self.os_type == "windows"
        self.is_linux = self.os_type == "linux"
        self.is_macos = self.os_type == "darwin"


class ApplicationController(BaseController):
    """Handles application launch, close, and management."""
    
    APP_PATHS = {
        "chrome": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            "/usr/bin/google-chrome",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        ],
        "vscode": [
            r"C:\Program Files\Microsoft VS Code\Code.exe",
            "/usr/bin/code",
            "/Applications/Visual Studio Code.app/Contents/MacOS/Electron",
        ],
        "spotify": [
            r"C:\Users\{user}\AppData\Roaming\Spotify\Spotify.exe",
            "/usr/bin/spotify",
            "/Applications/Spotify.app/Contents/MacOS/Spotify",
        ],
        "discord": [
            r"C:\Users\{user}\AppData\Local\Discord\app-1.0.9019\Discord.exe",
            "/usr/bin/discord",
            "/Applications/Discord.app/Contents/MacOS/Discord",
        ],
    }
    
    def open_application(self, app_name: str) -> ControllerResult:
        """Open an application by name in isolated subprocess."""
        try:
            from .isolated_executor import get_isolated_executor
            executor = get_isolated_executor()
            
            app_path = self._find_app_path(app_name)
            if not app_path:
                return ControllerResult(
                    success=False,
                    message=f"Application '{app_name}' not found",
                    error="App not found"
                )
            
            request_id = f"open_{app_name}_{uuid.uuid4().hex[:8]}"
            
            # Launch detached — GUI apps never exit, so never wait on them
            result = executor.execute_sync(
                app_path,
                [],
                timeout=30,
                request_id=request_id,
                wait=False
            )
            
            # App launching often returns non-zero but still succeeds
            return ControllerResult(
                success=True,
                message=f"Opened {app_name}",
                data={"app": app_name, "path": app_path}
            )
        except Exception as e:
            logger.error(f"Error opening application {app_name}: {e}")
            return ControllerResult(
                success=False,
                message=f"Failed to open {app_name}",
                error=str(e)
            )
    
    def close_application(self, app_name: str) -> ControllerResult:
        """Close an application by name."""
        try:
            if self.is_windows:
                subprocess.run(["taskkill", "/IM", f"{app_name}.exe", "/F"], 
                             capture_output=True)
            else:
                subprocess.run(["pkill", app_name], capture_output=True)
            
            return ControllerResult(
                success=True,
                message=f"Closed {app_name}",
            )
        except Exception as e:
            logger.error(f"Error closing application {app_name}: {e}")
            return ControllerResult(
                success=False,
                message=f"Failed to close {app_name}",
                error=str(e)
            )
    
    def switch_application(self, app_name: str) -> ControllerResult:
        """Switch to an application — verify a real window exists first."""
        try:
            if self.is_windows:
                return window_controller.switch(app_name)
            else:
                return ControllerResult(
                    success=False,
                    message="Switch application not implemented on this platform",
                )
        except Exception as e:
            return ControllerResult(
                success=False,
                message=f"Failed to switch to {app_name}",
                error=str(e)
            )

    def minimize_application(self, app_name: str) -> ControllerResult:
        """Minimize an application's windows."""
        return window_controller.minimize(app_name)

    def maximize_application(self, app_name: str) -> ControllerResult:
        """Maximize an application's windows."""
        return window_controller.maximize(app_name)

    def restart_application(self, app_name: str) -> ControllerResult:
        """Restart an application (close then reopen)."""
        closed = self.close_application(app_name)
        if not closed.success:
            return closed
        return self.open_application(app_name)
    
    def _find_app_path(self, app_name: str) -> Optional[str]:
        """Find the full path to an application."""
        app_name_lower = app_name.lower()
        if app_name_lower in self.APP_PATHS:
            for path in self.APP_PATHS[app_name_lower]:
                if self.is_windows and os.path.exists(path):
                    return path
                elif not self.is_windows and os.path.exists(path):
                    return path
        
        if self.is_windows and os.path.exists(app_name):
            return app_name
        
        return None


class FileController(BaseController):
    """Handles file operations."""
    
    def create_file(self, file_path: str) -> ControllerResult:
        """Create a new file."""
        try:
            path_obj = os.path.expanduser(file_path)
            os.makedirs(os.path.dirname(path_obj), exist_ok=True)
            with open(path_obj, 'w') as f:
                f.write("")
            
            return ControllerResult(
                success=True,
                message=f"Created file: {file_path}",
                data={"path": path_obj}
            )
        except Exception as e:
            logger.error(f"Error creating file {file_path}: {e}")
            return ControllerResult(
                success=False,
                message=f"Failed to create file {file_path}",
                error=str(e)
            )
    
    def delete_file(self, file_path: str) -> ControllerResult:
        """Delete a file."""
        try:
            path_obj = os.path.expanduser(file_path)
            if os.path.exists(path_obj):
                os.remove(path_obj)
                return ControllerResult(
                    success=True,
                    message=f"Deleted file: {file_path}",
                )
            else:
                return ControllerResult(
                    success=False,
                    message=f"File not found: {file_path}",
                    error="File not found"
                )
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
            return ControllerResult(
                success=False,
                message=f"Failed to delete file {file_path}",
                error=str(e)
            )
    
    def open_file(self, file_path: str) -> ControllerResult:
        """Open a file with default application."""
        try:
            path_obj = os.path.expanduser(file_path)
            if not os.path.exists(path_obj):
                return ControllerResult(
                    success=False,
                    message=f"File not found: {file_path}",
                    error="File not found"
                )
            
            if self.is_windows:
                os.startfile(path_obj)
            elif self.is_macos:
                subprocess.run(["open", path_obj])
            else:
                subprocess.run(["xdg-open", path_obj])
            
            return ControllerResult(
                success=True,
                message=f"Opened file: {file_path}",
            )
        except Exception as e:
            logger.error(f"Error opening file {file_path}: {e}")
            return ControllerResult(
                success=False,
                message=f"Failed to open file {file_path}",
                error=str(e)
            )

    def rename_file(self, file_path: str, new_name: str) -> ControllerResult:
        """Rename a file."""
        try:
            path_obj = os.path.expanduser(file_path)
            if not os.path.exists(path_obj):
                return ControllerResult(success=False, message=f"File not found: {file_path}", error="File not found")
            if not os.path.isfile(path_obj):
                return ControllerResult(success=False, message=f"Not a file: {file_path}", error="Not a file")
            new_path = os.path.join(os.path.dirname(path_obj), new_name)
            os.rename(path_obj, new_path)
            return ControllerResult(success=True, message=f"Renamed to {os.path.basename(new_path)}", data={"path": new_path})
        except Exception as e:
            logger.error(f"Error renaming file: {e}")
            return ControllerResult(success=False, message=f"Failed to rename {file_path}", error=str(e))

    def copy_file(self, file_path: str, destination: str) -> ControllerResult:
        """Copy a file to a destination."""
        try:
            import shutil
            path_obj = os.path.expanduser(file_path)
            if not os.path.exists(path_obj):
                return ControllerResult(success=False, message=f"File not found: {file_path}", error="File not found")
            dest = os.path.expanduser(destination)
            if os.path.isdir(dest):
                dest = os.path.join(dest, os.path.basename(path_obj))
            shutil.copy2(path_obj, dest)
            return ControllerResult(success=True, message=f"Copied to {dest}", data={"path": dest})
        except Exception as e:
            logger.error(f"Error copying file: {e}")
            return ControllerResult(success=False, message=f"Failed to copy {file_path}", error=str(e))

    def move_file(self, file_path: str, destination: str) -> ControllerResult:
        """Move a file to a destination."""
        try:
            import shutil
            path_obj = os.path.expanduser(file_path)
            if not os.path.exists(path_obj):
                return ControllerResult(success=False, message=f"File not found: {file_path}", error="File not found")
            dest = os.path.expanduser(destination)
            if os.path.isdir(dest):
                dest = os.path.join(dest, os.path.basename(path_obj))
            shutil.move(path_obj, dest)
            return ControllerResult(success=True, message=f"Moved to {dest}", data={"path": dest})
        except Exception as e:
            logger.error(f"Error moving file: {e}")
            return ControllerResult(success=False, message=f"Failed to move {file_path}", error=str(e))

    def search_files(self, query: str, root: Optional[str] = None, limit: int = 20) -> ControllerResult:
        """Search for files by name/extension under a root directory."""
        try:
            root = root or os.path.join(os.path.expanduser("~"), "Documents")
            root = os.path.expanduser(root)
            if not os.path.isdir(root):
                return ControllerResult(success=False, message=f"Search root not found: {root}", error="Folder not found")
            q = query.strip().lower()
            matches: list = []
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [d for d in dirnames if d not in ("node_modules", ".git", "__pycache__", ".venv", ".venv312", "venv", ".cache")]
                for fname in filenames:
                    if q in fname.lower():
                        matches.append(os.path.join(dirpath, fname))
                        if len(matches) >= limit:
                            return ControllerResult(success=True, message=f"Found {len(matches)} matching files", data={"results": matches, "count": len(matches)})
            return ControllerResult(
                success=len(matches) > 0,
                message=f"Found {len(matches)} matching files" if matches else f"No files matched '{query}' under {root}",
                data={"results": matches, "count": len(matches)},
            )
        except Exception as e:
            logger.error(f"Error searching files: {e}")
            return ControllerResult(success=False, message="Failed to search files", error=str(e))

    def file_metadata(self, file_path: str) -> ControllerResult:
        """Read file metadata (size, modified time)."""
        try:
            path_obj = os.path.expanduser(file_path)
            if not os.path.exists(path_obj):
                return ControllerResult(success=False, message=f"File not found: {file_path}", error="File not found")
            stat = os.stat(path_obj)
            from datetime import datetime
            return ControllerResult(
                success=True,
                message=f"{os.path.basename(path_obj)} — {stat.st_size / 1024:.1f} KB, modified {datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')}",
                data={
                    "name": os.path.basename(path_obj),
                    "path": path_obj,
                    "size_bytes": stat.st_size,
                    "size_kb": round(stat.st_size / 1024, 1),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                },
            )
        except Exception as e:
            logger.error(f"Error reading metadata: {e}")
            return ControllerResult(success=False, message=f"Failed to read metadata for {file_path}", error=str(e))


class FolderController(BaseController):
    """Handles folder operations."""
    
    def create_folder(self, folder_path: str) -> ControllerResult:
        """Create a new folder."""
        try:
            path_obj = os.path.expanduser(folder_path)
            os.makedirs(path_obj, exist_ok=True)
            
            return ControllerResult(
                success=True,
                message=f"Created folder: {folder_path}",
                data={"path": path_obj}
            )
        except Exception as e:
            logger.error(f"Error creating folder {folder_path}: {e}")
            return ControllerResult(
                success=False,
                message=f"Failed to create folder {folder_path}",
                error=str(e)
            )
    
    def open_folder(self, folder_path: str) -> ControllerResult:
        """Open a folder in file explorer."""
        try:
            path_obj = os.path.expanduser(folder_path)
            if not os.path.exists(path_obj):
                return ControllerResult(
                    success=False,
                    message=f"Folder not found: {folder_path}",
                    error="Folder not found"
                )
            
            if self.is_windows:
                os.startfile(path_obj)
            elif self.is_macos:
                subprocess.run(["open", path_obj])
            else:
                subprocess.run(["xdg-open", path_obj])
            
            return ControllerResult(
                success=True,
                message=f"Opened folder: {folder_path}",
            )
        except Exception as e:
            logger.error(f"Error opening folder {folder_path}: {e}")
            return ControllerResult(
                success=False,
                message=f"Failed to open folder {folder_path}",
                error=str(e)
            )

    def delete_folder(self, folder_path: str) -> ControllerResult:
        """Delete a folder (recursive, requires confirmation at engine level)."""
        try:
            import shutil
            path_obj = os.path.expanduser(folder_path)
            if not os.path.exists(path_obj):
                return ControllerResult(success=False, message=f"Folder not found: {folder_path}", error="Folder not found")
            if not os.path.isdir(path_obj):
                return ControllerResult(success=False, message=f"Not a folder: {folder_path}", error="Not a folder")
            name = os.path.basename(path_obj.rstrip("/\\"))
            if name.lower() in ("c:\\", "c:/", "", "users", "windows", "program files", "program files (x86)"):
                return ControllerResult(success=False, message="Refusing to delete a system-critical folder.", error="Protected path")
            shutil.rmtree(path_obj)
            return ControllerResult(success=True, message=f"Deleted folder: {folder_path}")
        except Exception as e:
            logger.error(f"Error deleting folder {folder_path}: {e}")
            return ControllerResult(success=False, message=f"Failed to delete folder {folder_path}", error=str(e))

    def rename_folder(self, folder_path: str, new_name: str) -> ControllerResult:
        """Rename a folder."""
        try:
            path_obj = os.path.expanduser(folder_path)
            if not os.path.exists(path_obj):
                return ControllerResult(success=False, message=f"Folder not found: {folder_path}", error="Folder not found")
            new_path = os.path.join(os.path.dirname(path_obj), new_name)
            os.rename(path_obj, new_path)
            return ControllerResult(success=True, message=f"Renamed to {os.path.basename(new_path)}", data={"path": new_path})
        except Exception as e:
            logger.error(f"Error renaming folder: {e}")
            return ControllerResult(success=False, message=f"Failed to rename {folder_path}", error=str(e))

    def copy_folder(self, folder_path: str, destination: str) -> ControllerResult:
        """Copy a folder tree to a destination."""
        try:
            import shutil
            path_obj = os.path.expanduser(folder_path)
            if not os.path.exists(path_obj):
                return ControllerResult(success=False, message=f"Folder not found: {folder_path}", error="Folder not found")
            dest = os.path.expanduser(destination)
            if os.path.isdir(dest):
                dest = os.path.join(dest, os.path.basename(path_obj.rstrip("/\\")))
            shutil.copytree(path_obj, dest)
            return ControllerResult(success=True, message=f"Copied to {dest}", data={"path": dest})
        except Exception as e:
            logger.error(f"Error copying folder: {e}")
            return ControllerResult(success=False, message=f"Failed to copy {folder_path}", error=str(e))

    def move_folder(self, folder_path: str, destination: str) -> ControllerResult:
        """Move a folder to a destination."""
        try:
            import shutil
            path_obj = os.path.expanduser(folder_path)
            if not os.path.exists(path_obj):
                return ControllerResult(success=False, message=f"Folder not found: {folder_path}", error="Folder not found")
            dest = os.path.expanduser(destination)
            if os.path.isdir(dest):
                dest = os.path.join(dest, os.path.basename(path_obj.rstrip("/\\")))
            shutil.move(path_obj, dest)
            return ControllerResult(success=True, message=f"Moved to {dest}", data={"path": dest})
        except Exception as e:
            logger.error(f"Error moving folder: {e}")
            return ControllerResult(success=False, message=f"Failed to move {folder_path}", error=str(e))

    def search_folders(self, query: str, root: Optional[str] = None, limit: int = 20) -> ControllerResult:
        """Search for folders by name under a root directory."""
        try:
            root = root or os.path.join(os.path.expanduser("~"), "Documents")
            root = os.path.expanduser(root)
            if not os.path.isdir(root):
                return ControllerResult(success=False, message=f"Search root not found: {root}", error="Folder not found")
            q = query.strip().lower()
            matches: list = []
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [d for d in dirnames if d not in ("node_modules", ".git", "__pycache__", ".venv", ".venv312", "venv", ".cache")]
                for dname in dirnames:
                    if q in dname.lower():
                        matches.append(os.path.join(dirpath, dname))
                        if len(matches) >= limit:
                            return ControllerResult(success=True, message=f"Found {len(matches)} matching folders", data={"results": matches, "count": len(matches)})
            return ControllerResult(
                success=len(matches) > 0,
                message=f"Found {len(matches)} matching folders" if matches else f"No folders matched '{query}' under {root}",
                data={"results": matches, "count": len(matches)},
            )
        except Exception as e:
            logger.error(f"Error searching folders: {e}")
            return ControllerResult(success=False, message="Failed to search folders", error=str(e))

    def find_folder_candidates(self, name: str, limit: int = 8) -> list:
        """Find candidate folder paths matching a name (used for ambiguity resolution)."""
        home = os.path.expanduser("~")
        roots = [
            os.path.join(home, "Documents"),
            os.path.join(home, "Desktop"),
            os.path.join(home, "Downloads"),
            os.path.join(home, "Projects"),
            os.path.join(home, "OneDrive", "Documents"),
            home,
        ]
        q = name.strip().lower()
        found: list = []
        seen = set()
        for root in roots:
            if not os.path.isdir(root):
                continue
            try:
                for entry in os.listdir(root):
                    full = os.path.join(root, entry)
                    if os.path.isdir(full) and q in entry.lower() and full not in seen:
                        seen.add(full)
                        found.append(full)
                        if len(found) >= limit:
                            return found
            except Exception:
                continue
        return found


class SystemController(BaseController):
    """Handles system operations."""
    
    def get_cpu_usage(self) -> ControllerResult:
        """Get current CPU usage percentage."""
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            return ControllerResult(
                success=True,
                message=f"CPU usage: {cpu_percent}%",
                data={"cpu_usage": cpu_percent}
            )
        except Exception as e:
            logger.error(f"Error getting CPU usage: {e}")
            return ControllerResult(
                success=False,
                message="Failed to get CPU usage",
                error=str(e)
            )
    
    def get_ram_usage(self) -> ControllerResult:
        """Get current RAM usage."""
        try:
            import psutil
            ram = psutil.virtual_memory()
            return ControllerResult(
                success=True,
                message=f"RAM usage: {ram.percent}%",
                data={
                    "ram_percent": ram.percent,
                    "ram_used_gb": ram.used / (1024**3),
                    "ram_total_gb": ram.total / (1024**3)
                }
            )
        except Exception as e:
            logger.error(f"Error getting RAM usage: {e}")
            return ControllerResult(
                success=False,
                message="Failed to get RAM usage",
                error=str(e)
            )
    
    def get_disk_usage(self) -> ControllerResult:
        """Get disk usage for all drives."""
        try:
            import psutil
            disk = psutil.disk_usage('/')
            return ControllerResult(
                success=True,
                message=f"Disk usage: {disk.percent}%",
                data={
                    "disk_percent": disk.percent,
                    "disk_used_gb": disk.used / (1024**3),
                    "disk_total_gb": disk.total / (1024**3)
                }
            )
        except Exception as e:
            logger.error(f"Error getting disk usage: {e}")
            return ControllerResult(
                success=False,
                message="Failed to get disk usage",
                error=str(e)
            )
    
    def take_screenshot(self) -> ControllerResult:
        """Take a screenshot."""
        try:
            from datetime import datetime
            filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            
            if self.is_windows:
                import mss
                with mss.mss() as sct:
                    screenshot = sct.shot(output=filename)
                    return ControllerResult(
                        success=True,
                        message=f"Screenshot saved: {filename}",
                        data={"filename": filename}
                    )
            else:
                return ControllerResult(
                    success=False,
                    message="Screenshot not implemented on this platform",
                )
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return ControllerResult(
                success=False,
                message="Failed to take screenshot",
                error=str(e)
            )
    
    def lock_screen(self) -> ControllerResult:
        """Lock the screen in isolated subprocess."""
        try:
            from .isolated_executor import get_isolated_executor
            executor = get_isolated_executor()
            
            request_id = f"lock_screen_{uuid.uuid4().hex[:8]}"
            
            if self.is_windows:
                result = executor.execute_sync(
                    "rundll32.exe",
                    ["user32.dll,LockWorkStation"],
                    timeout=10,
                    request_id=request_id
                )
            elif self.is_macos:
                result = executor.execute_sync(
                    "/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession",
                    ["-suspend"],
                    timeout=10,
                    request_id=request_id
                )
            else:
                result = executor.execute_sync(
                    "loginctl",
                    ["lock-session"],
                    timeout=10,
                    request_id=request_id
                )
            
            if result.success:
                return ControllerResult(
                    success=True,
                    message="Screen locked",
                )
            else:
                return ControllerResult(
                    success=False,
                    message="Failed to lock screen",
                    error=result.error
                )
        except Exception as e:
            logger.error(f"Error locking screen: {e}")
            return ControllerResult(
                success=False,
                message="Failed to lock screen",
                error=str(e)
            )
    
    def shutdown(self) -> ControllerResult:
        """Shutdown the computer in isolated subprocess."""
        try:
            from .isolated_executor import get_isolated_executor
            executor = get_isolated_executor()
            
            request_id = f"shutdown_{uuid.uuid4().hex[:8]}"
            
            if self.is_windows:
                result = executor.execute_sync(
                    "shutdown",
                    ["/s", "/t", "60"],
                    timeout=15,
                    request_id=request_id
                )
            elif self.is_macos:
                result = executor.execute_sync(
                    "osascript",
                    ["-e", "tell application \"System Events\" to shut down"],
                    timeout=15,
                    request_id=request_id
                )
            else:
                result = executor.execute_sync(
                    "shutdown",
                    ["-h", "+1"],
                    timeout=15,
                    request_id=request_id
                )
            
            if result.success:
                return ControllerResult(
                    success=True,
                    message="Shutdown initiated",
                )
            else:
                return ControllerResult(
                    success=False,
                    message="Failed to initiate shutdown",
                    error=result.error
                )
        except Exception as e:
            logger.error(f"Error shutting down: {e}")
            return ControllerResult(
                success=False,
                message="Failed to initiate shutdown",
                error=str(e)
            )
    
    def restart(self) -> ControllerResult:
        """Restart the computer in isolated subprocess."""
        try:
            from .isolated_executor import get_isolated_executor
            executor = get_isolated_executor()
            
            request_id = f"restart_{uuid.uuid4().hex[:8]}"
            
            if self.is_windows:
                result = executor.execute_sync(
                    "shutdown",
                    ["/r", "/t", "60"],
                    timeout=15,
                    request_id=request_id
                )
            elif self.is_macos:
                result = executor.execute_sync(
                    "osascript",
                    ["-e", "tell application \"System Events\" to restart"],
                    timeout=15,
                    request_id=request_id
                )
            else:
                result = executor.execute_sync(
                    "shutdown",
                    ["-r", "+1"],
                    timeout=15,
                    request_id=request_id
                )
            
            if result.success:
                return ControllerResult(
                    success=True,
                    message="Restart initiated",
                )
            else:
                return ControllerResult(
                    success=False,
                    message="Failed to initiate restart",
                    error=result.error
                )
        except Exception as e:
            logger.error(f"Error restarting: {e}")
            return ControllerResult(
                success=False,
                message="Failed to initiate restart",
                error=str(e)
            )

    def _volume_device(self):
        """Return the comtypes IAudioEndpointVolume for the default speakers.

        Supports both legacy pycaw (AudioDevice.Activate) and pycaw >= 2025
        (AudioDevice.EndpointVolume already wrapped)."""
        from pycaw.pycaw import AudioUtilities
        devices = AudioUtilities.GetSpeakers()
        endpoint = getattr(devices, "EndpointVolume", None)
        if endpoint is not None:
            return endpoint
        from pycaw.pycaw import IAudioEndpointVolume
        from comtypes import CLSCTX_ALL
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return interface.QueryInterface(IAudioEndpointVolume)

    def get_volume(self) -> ControllerResult:
        """Get current system volume percentage."""
        try:
            if not self.is_windows:
                return ControllerResult(success=False, message="Volume control only supported on Windows")
            volume = self._volume_device()
            level = volume.GetMasterVolumeLevelScalar()
            muted = bool(volume.GetMute())
            return ControllerResult(
                success=True,
                message=f"Volume is at {round(level * 100)}%" + (" (muted)" if muted else ""),
                data={"volume": round(level * 100), "muted": muted},
            )
        except Exception as e:
            logger.error(f"Error getting volume: {e}")
            return ControllerResult(success=False, message="Failed to read volume level", error=str(e))

    def set_volume(self, level: int) -> ControllerResult:
        """Set system volume to a percentage (0-100)."""
        try:
            if not self.is_windows:
                return ControllerResult(success=False, message="Volume control only supported on Windows")
            level = max(0, min(100, int(level)))
            volume = self._volume_device()
            volume.SetMasterVolumeLevelScalar(level / 100.0, None)
            volume.SetMute(0, None)
            return ControllerResult(
                success=True,
                message=f"Volume set to {level}%",
                data={"volume": level},
            )
        except Exception as e:
            logger.error(f"Error setting volume: {e}")
            return ControllerResult(success=False, message="Failed to set volume level", error=str(e))

    def adjust_volume(self, direction: str, delta: int = 5) -> ControllerResult:
        """Increase or decrease volume by a percentage."""
        try:
            current = self.get_volume()
            if not current.success:
                return current
            current_level = current.data["volume"]
            new_level = max(0, min(100, current_level + (delta if direction == "up" else -delta)))
            return self.set_volume(new_level)
        except Exception as e:
            logger.error(f"Error adjusting volume: {e}")
            return ControllerResult(success=False, message="Failed to adjust volume", error=str(e))

    def get_brightness(self) -> ControllerResult:
        """Get display brightness (Windows WMI)."""
        try:
            if not self.is_windows:
                return ControllerResult(success=False, message="Brightness control only supported on Windows")
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightness).CurrentBrightness"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip().isdigit():
                value = int(result.stdout.strip())
                return ControllerResult(success=True, message=f"Brightness is at {value}%", data={"brightness": value})
            return ControllerResult(success=False, message="Could not read brightness", error=result.stderr.strip() or "No brightness info")
        except Exception as e:
            logger.error(f"Error getting brightness: {e}")
            return ControllerResult(success=False, message="Failed to read brightness", error=str(e))

    def set_brightness(self, level: int) -> ControllerResult:
        """Set display brightness (Windows WMI)."""
        try:
            if not self.is_windows:
                return ControllerResult(success=False, message="Brightness control only supported on Windows")
            level = max(0, min(100, int(level)))
            script = (
                "$m = Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightnessMethods; "
                f"$m.WmiSetBrightness(1, {level})"
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return ControllerResult(success=True, message=f"Brightness set to {level}%", data={"brightness": level})
            return ControllerResult(
                success=False,
                message="Could not change brightness (may require admin rights)",
                error=result.stderr.strip() or "WMI set failed",
            )
        except Exception as e:
            logger.error(f"Error setting brightness: {e}")
            return ControllerResult(success=False, message="Failed to set brightness", error=str(e))

    def check_wifi(self) -> ControllerResult:
        """Check Wi-Fi connection status."""
        try:
            if not self.is_windows:
                import psutil
                return ControllerResult(success=True, message="Wi-Fi status check not implemented on this platform", data={"wifi": "unsupported"})
            result = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                return ControllerResult(success=False, message="Wi-Fi is unavailable (no wireless adapter)", data={"connected": False, "ssid": None})
            ssid = None
            signal = None
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.lower().startswith("ssid") and ":" in line:
                    ssid = line.split(":", 1)[1].strip()
                if line.lower().startswith("signal") and ":" in line:
                    signal = line.split(":", 1)[1].strip()
            if ssid:
                return ControllerResult(
                    success=True,
                    message=f"Connected to Wi-Fi: {ssid}" + (f" ({signal})" if signal else ""),
                    data={"connected": True, "ssid": ssid, "signal": signal},
                )
            return ControllerResult(success=True, message="Not connected to any Wi-Fi network", data={"connected": False, "ssid": None})
        except Exception as e:
            logger.error(f"Error checking wifi: {e}")
            return ControllerResult(success=False, message="Failed to check Wi-Fi status", error=str(e))

    def check_bluetooth(self) -> ControllerResult:
        """Check Bluetooth adapter status."""
        try:
            if not self.is_windows:
                return ControllerResult(success=False, message="Bluetooth status check not implemented on this platform")
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-PnpDevice -Class Bluetooth -Status OK | Measure-Object).Count"],
                capture_output=True, text=True, timeout=15,
            )
            count = result.stdout.strip()
            enabled = count.isdigit() and int(count) > 0
            return ControllerResult(
                success=True,
                message=f"Bluetooth is {'enabled' if enabled else 'disabled'}",
                data={"enabled": enabled, "devices": int(count) if count.isdigit() else 0},
            )
        except Exception as e:
            logger.error(f"Error checking bluetooth: {e}")
            return ControllerResult(success=False, message="Failed to check Bluetooth status", error=str(e))

    def check_network(self) -> ControllerResult:
        """Check network status and internet reachability."""
        try:
            import socket
            import psutil
            interfaces = []
            for name, stats in psutil.net_if_stats().items():
                interfaces.append({"name": name, "up": stats.isup, "speed_mbps": stats.speed})
            online = False
            try:
                with socket.create_connection(("1.1.1.1", 53), timeout=2):
                    online = True
            except Exception:
                online = False
            up_count = sum(1 for i in interfaces if i["up"])
            return ControllerResult(
                success=True,
                message=f"Network: {up_count} interface(s) up, internet {'reachable' if online else 'not reachable'}",
                data={"interfaces": interfaces, "internet": online, "interfaces_up": up_count},
            )
        except Exception as e:
            logger.error(f"Error checking network: {e}")
            return ControllerResult(success=False, message="Failed to check network status", error=str(e))

    def check_battery(self) -> ControllerResult:
        """Check battery status."""
        try:
            import psutil
            battery = psutil.sensors_battery()
            if battery is None:
                return ControllerResult(success=True, message="No battery detected (desktop system)", data={"battery": None})
            return ControllerResult(
                success=True,
                message=f"Battery at {battery.percent}%" + ("" if battery.power_plugged else " (on battery)"),
                data={"percent": battery.percent, "plugged": bool(battery.power_plugged)},
            )
        except Exception as e:
            logger.error(f"Error checking battery: {e}")
            return ControllerResult(success=False, message="Failed to check battery", error=str(e))

    def sleep(self) -> ControllerResult:
        """Put the computer to sleep."""
        try:
            from .isolated_executor import get_isolated_executor
            executor = get_isolated_executor()
            if self.is_windows:
                result = executor.execute_sync("rundll32.exe", ["powrprof.dll,SetSuspendState", "0,1,0"], timeout=10, request_id=f"sleep_{uuid.uuid4().hex[:8]}")
            elif self.is_macos:
                result = executor.execute_sync("pmset", ["sleepnow"], timeout=10, request_id=f"sleep_{uuid.uuid4().hex[:8]}")
            else:
                result = executor.execute_sync("systemctl", ["suspend"], timeout=10, request_id=f"sleep_{uuid.uuid4().hex[:8]}")
            return ControllerResult(success=result.success, message="Computer going to sleep" if result.success else "Failed to sleep", error=result.error)
        except Exception as e:
            logger.error(f"Error sleeping: {e}")
            return ControllerResult(success=False, message="Failed to put computer to sleep", error=str(e))


class KeyboardController(BaseController):
    """Handles keyboard input (key presses, combos, typing) via native APIs."""

    VK_MAP = {
        "space": 0x20, "enter": 0x0D, "return": 0x0D, "tab": 0x09, "esc": 0x1B, "escape": 0x1B,
        "backspace": 0x08, "delete": 0x2E, "del": 0x2E, "insert": 0x2D, "home": 0x24, "end": 0x23,
        "pageup": 0x21, "pagedown": 0x22, "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
        "capslock": 0x14, "numlock": 0x90, "scrolllock": 0x91, "printscreen": 0x2C, "pause": 0x13,
        "volumeup": 0xAF, "volumedown": 0xAE, "volumemute": 0xAD, "mediatracknext": 0xB0,
        "mediatrackprev": 0xB1, "playpause": 0xB3, "windowsspace": 0x5B,
    }
    MODIFIER_MAP = {
        "ctrl": 0x11, "control": 0x11, "alt": 0x12, "shift": 0x10,
        "win": 0x5B, "windows": 0x5B, "cmd": 0x5B, "meta": 0x5B,
    }

    def _vk_for(self, token: str) -> Optional[int]:
        token = token.strip().lower()
        if token in self.MODIFIER_MAP:
            return self.MODIFIER_MAP[token]
        if token in self.VK_MAP:
            return self.VK_MAP[token]
        if len(token) == 1:
            ch = ord(token.upper())
            if 0x30 <= ch <= 0x39 or 0x41 <= ch <= 0x5A:
                return ch
            return None
        if token.startswith("f") and token[1:].isdigit() and 1 <= int(token[1:]) <= 24:
            return 0x70 + int(token[1:]) - 1
        return None

    def _send_key(self, vk: int, keyup: bool = False):
        import ctypes
        from ctypes import wintypes
        INPUT_KEYBOARD = 1
        KEYEVENTF_KEYUP = 0x0002
        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                        ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]
        class INPUT(ctypes.Structure):
            class _I(ctypes.Union):
                _fields_ = [("ki", KEYBDINPUT)]
            _anonymous_ = ("i",)
            _fields_ = [("type", wintypes.DWORD), ("i", _I)]
        extra = ctypes.c_ulong(0)
        inp = INPUT(type=INPUT_KEYBOARD)
        inp.ki.wVk = vk
        inp.ki.dwFlags = KEYEVENTF_KEYUP if keyup else 0
        inp.ki.dwExtraInfo = ctypes.pointer(extra)
        ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def press(self, combo: str) -> ControllerResult:
        """Press a key or key combination, e.g. 'ctrl+c', 'alt+tab', 'enter', 'win+d'."""
        try:
            if not self.is_windows:
                return ControllerResult(success=False, message="Keyboard automation only supported on Windows")
            tokens = [t for t in re.split(r"[\s+]+", combo.strip()) if t]
            if not tokens:
                return ControllerResult(success=False, message="No key specified", error="Empty key combo")
            vks = [self._vk_for(t) for t in tokens]
            if any(v is None for v in vks):
                bad = tokens[vks.index(None)]
                return ControllerResult(success=False, message=f"Unsupported key: '{bad}'", error="Unknown key")
            for vk in vks:
                self._send_key(vk)
            for vk in reversed(vks):
                self._send_key(vk, keyup=True)
            return ControllerResult(success=True, message=f"Pressed {'+'.join(tokens)}", data={"keys": tokens})
        except Exception as e:
            logger.error(f"Error pressing keys: {e}")
            return ControllerResult(success=False, message="Failed to press keys", error=str(e))

    def type_text(self, text: str) -> ControllerResult:
        """Type text using Unicode key events."""
        try:
            if not self.is_windows:
                return ControllerResult(success=False, message="Keyboard automation only supported on Windows")
            import ctypes
            from ctypes import wintypes
            INPUT_KEYBOARD = 1
            KEYEVENTF_UNICODE = 0x0004
            KEYEVENTF_KEYUP = 0x0002
            class KEYBDINPUT(ctypes.Structure):
                _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                            ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]
            class INPUT(ctypes.Structure):
                class _I(ctypes.Union):
                    _fields_ = [("ki", KEYBDINPUT)]
                _anonymous_ = ("i",)
                _fields_ = [("type", wintypes.DWORD), ("i", _I)]
            extra = ctypes.c_ulong(0)
            for ch in text:
                for flags in (0, KEYEVENTF_KEYUP):
                    inp = INPUT(type=INPUT_KEYBOARD)
                    inp.ki.wScan = ord(ch)
                    inp.ki.dwFlags = KEYEVENTF_UNICODE | flags
                    inp.ki.dwExtraInfo = ctypes.pointer(extra)
                    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
            return ControllerResult(success=True, message=f"Typed: {text[:40]}{'...' if len(text) > 40 else ''}")
        except Exception as e:
            logger.error(f"Error typing text: {e}")
            return ControllerResult(success=False, message="Failed to type text", error=str(e))


class MouseController(BaseController):
    """Handles mouse input (move, click, scroll, drag) via native APIs."""

    def _position(self) -> tuple:
        import ctypes
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
        pt = POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return (pt.x, pt.y)

    def _move_to(self, x: int, y: int):
        import ctypes
        ctypes.windll.user32.SetCursorPos(int(x), int(y))

    def _button_event(self, down: bool, right: bool = False, double: bool = False):
        import ctypes
        MOUSEEVENTF_LEFTDOWN = 0x0002
        MOUSEEVENTF_LEFTUP = 0x0004
        MOUSEEVENTF_RIGHTDOWN = 0x0008
        MOUSEEVENTF_RIGHTUP = 0x0010
        if right:
            evt = MOUSEEVENTF_RIGHTDOWN if down else MOUSEEVENTF_RIGHTUP
        else:
            evt = MOUSEEVENTF_LEFTDOWN if down else MOUSEEVENTF_LEFTUP
        ctypes.windll.user32.mouse_event(evt, 0, 0, 0, 0)
        if double and down:
            ctypes.windll.user32.mouse_event(evt, 0, 0, 0, 0)

    def click(self, button: str = "left", position: Optional[tuple] = None) -> ControllerResult:
        try:
            if not self.is_windows:
                return ControllerResult(success=False, message="Mouse automation only supported on Windows")
            if position:
                self._move_to(*position)
            self._button_event(True, right=(button == "right"))
            self._button_event(False, right=(button == "right"))
            return ControllerResult(success=True, message=f"{button.title()} click at {self._position()}", data={"position": self._position()})
        except Exception as e:
            return ControllerResult(success=False, message="Failed to click", error=str(e))

    def double_click(self, position: Optional[tuple] = None) -> ControllerResult:
        try:
            if not self.is_windows:
                return ControllerResult(success=False, message="Mouse automation only supported on Windows")
            if position:
                self._move_to(*position)
            self._button_event(True, double=True)
            self._button_event(False)
            return ControllerResult(success=True, message=f"Double click at {self._position()}", data={"position": self._position()})
        except Exception as e:
            return ControllerResult(success=False, message="Failed to double click", error=str(e))

    def move(self, x: int, y: int, relative: bool = False) -> ControllerResult:
        try:
            if not self.is_windows:
                return ControllerResult(success=False, message="Mouse automation only supported on Windows")
            if relative:
                cx, cy = self._position()
                self._move_to(cx + x, cy + y)
            else:
                self._move_to(x, y)
            return ControllerResult(success=True, message=f"Cursor moved to {self._position()}", data={"position": self._position()})
        except Exception as e:
            return ControllerResult(success=False, message="Failed to move cursor", error=str(e))

    def scroll(self, direction: str, amount: int = 3) -> ControllerResult:
        try:
            import ctypes
            WHEEL_DELTA = 120
            direction = direction.lower()
            if direction not in ("up", "down"):
                return ControllerResult(success=False, message="Scroll direction must be 'up' or 'down'", error="Bad direction")
            delta = WHEEL_DELTA * max(1, min(amount, 20))
            if direction == "down":
                delta = -delta
            ctypes.windll.user32.mouse_event(0x0800, 0, 0, delta, 0)
            return ControllerResult(success=True, message=f"Scrolled {direction} by {amount} ticks")
        except Exception as e:
            return ControllerResult(success=False, message="Failed to scroll", error=str(e))

    def drag(self, from_pos: tuple, to_pos: tuple) -> ControllerResult:
        try:
            if not self.is_windows:
                return ControllerResult(success=False, message="Mouse automation only supported on Windows")
            self._move_to(*from_pos)
            self._button_event(True)
            self._move_to(*to_pos)
            self._button_event(False)
            return ControllerResult(success=True, message=f"Dragged from {from_pos} to {to_pos}")
        except Exception as e:
            return ControllerResult(success=False, message="Failed to drag", error=str(e))


class WindowController(BaseController):
    """Handles window operations (minimize, maximize, restore, close, switch, snap, show desktop)."""

    SW_MINIMIZE = 6
    SW_MAXIMIZE = 3
    SW_RESTORE = 9
    SW_SHOW = 5
    WM_CLOSE = 0x0010

    def _hwnds_for_process(self, name: str) -> list:
        import ctypes
        import psutil
        user32 = ctypes.windll.user32
        name_lower = name.lower().rstrip(".exe")
        hwnds = []
        procs = []
        for proc in psutil.process_iter(["pid", "name"]):
            pname = (proc.info["name"] or "").lower()
            if pname == name_lower + ".exe" or pname == name_lower:
                procs.append(proc.info["pid"])
        if not procs:
            return []
        enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        def _enum(hwnd, _):
            if not user32.IsWindowVisible(hwnd):
                return True
            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value in procs:
                hwnds.append(hwnd)
            return True
        user32.EnumWindows(enum_proc(_enum), 0)
        return hwnds

    def _foreground_hwnd(self):
        import ctypes
        return ctypes.windll.user32.GetForegroundWindow()

    def _apply(self, action: str, name: Optional[str] = None) -> ControllerResult:
        import ctypes
        user32 = ctypes.windll.user32
        hwnds = self._hwnds_for_process(name) if name else []
        if name and not hwnds:
            return ControllerResult(success=False, message=f"No visible window found for '{name}'", error="Window not found")
        target = hwnds[0] if hwnds else self._foreground_hwnd()
        if action == "minimize":
            user32.ShowWindow(target, self.SW_MINIMIZE)
        elif action == "maximize":
            user32.ShowWindow(target, self.SW_MAXIMIZE)
        elif action == "restore":
            user32.ShowWindow(target, self.SW_RESTORE)
        elif action == "close":
            user32.PostMessageW(target, self.WM_CLOSE, 0, 0)
        elif action == "switch":
            user32.ShowWindow(target, self.SW_RESTORE)
            user32.SetForegroundWindow(target)
        label = name or "the foreground window"
        return ControllerResult(success=True, message=f"{action.title()}: {label}", data={"hwnd": target})

    def minimize(self, name: Optional[str] = None) -> ControllerResult:
        return self._apply("minimize", name)

    def maximize(self, name: Optional[str] = None) -> ControllerResult:
        return self._apply("maximize", name)

    def restore(self, name: Optional[str] = None) -> ControllerResult:
        return self._apply("restore", name)

    def close(self, name: Optional[str] = None) -> ControllerResult:
        return self._apply("close", name)

    def switch(self, name: Optional[str] = None) -> ControllerResult:
        if not name:
            return KeyboardController().press("alt+tab")
        return self._apply("switch", name)

    def snap(self, side: str) -> ControllerResult:
        if not self.is_windows:
            return ControllerResult(success=False, message="Window snap only supported on Windows")
        kb = KeyboardController()
        if side == "left":
            return kb.press("win+left")
        return kb.press("win+right")

    def show_desktop(self) -> ControllerResult:
        if not self.is_windows:
            return ControllerResult(success=False, message="Show desktop only supported on Windows")
        return KeyboardController().press("win+d")


class ProcessController(BaseController):
    """Handles process operations with system-process protection."""

    PROTECTED_PROCESSES = {
        "system", "smss", "csrss", "wininit", "winlogon", "services", "lsass",
        "svchost", "explorer", "dwm", "fontdrvhost", "registry", "memory compression",
        "securityhealthservice", "msmpeng", "searchhost", "wmisvc", "spoolsv", "winvnc",
        "taskmgr", "ctfmon", "userinit", "conhost", "sihost", "taskhostw", "runtimebroker",
        "startmenuexperiencehost", "shellexperiencehost", "textinputhost", "dllhost",
    }

    KNOWN_SERVERS = {
        "backend": {"cmd": ["uvicorn", "app.main:app", "--reload"], "cwd": "backend"},
        "frontend": {"cmd": ["npm", "run", "dev"], "cwd": "frontend"},
        "desktop": {"cmd": ["npm", "run", "tauri", "dev"], "cwd": "desktop"},
        "hshot": {"cmd": ["uvicorn", "app.main:app", "--reload"], "cwd": "backend"},
    }

    def _project_root(self) -> str:
        here = os.getcwd()
        for candidate in (here, os.path.dirname(here), os.path.dirname(os.path.dirname(here))):
            if os.path.isdir(os.path.join(candidate, "frontend")) and os.path.isdir(os.path.join(candidate, "backend")):
                return candidate
        return here

    def _resolve_server(self, key: str) -> Optional[dict]:
        key = key.lower().strip()
        for alias, cfg in self.KNOWN_SERVERS.items():
            if key == alias or key.startswith(alias) or alias in key:
                root = self._project_root()
                return {
                    "cmd": cfg["cmd"],
                    "cwd": os.path.join(root, cfg["cwd"]) if os.path.isdir(os.path.join(root, cfg["cwd"])) else root,
                }
        return None

    def list_processes(self, limit: int = 20) -> ControllerResult:
        try:
            import psutil
            procs = []
            for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
                try:
                    info = proc.info
                    if info["name"]:
                        procs.append({
                            "pid": info["pid"], "name": info["name"],
                            "cpu": round(info["cpu_percent"] or 0, 1),
                            "memory": round(info["memory_percent"] or 0, 1),
                            "status": info["status"],
                        })
                except Exception:
                    continue
            procs.sort(key=lambda p: p["memory"], reverse=True)
            top = procs[:limit]
            return ControllerResult(
                success=True,
                message=f"Top {len(top)} processes by memory",
                data={"processes": top, "count": len(procs)},
            )
        except Exception as e:
            logger.error(f"Error listing processes: {e}")
            return ControllerResult(success=False, message="Failed to list processes", error=str(e))

    def start(self, target: str) -> ControllerResult:
        server = self._resolve_server(target)
        if server:
            from .isolated_executor import get_isolated_executor
            executor = get_isolated_executor()
            try:
                if self.is_windows:
                    creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
                else:
                    creationflags = 0
                process = subprocess.Popen(
                    server["cmd"],
                    cwd=server["cwd"],
                    creationflags=creationflags,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                request_id = f"server_{target}_{uuid.uuid4().hex[:8]}"
                executor.active_processes[request_id] = process
                return ControllerResult(
                    success=True,
                    message=f"Started {target} (pid {process.pid})",
                    data={"pid": process.pid, "cwd": server["cwd"]},
                )
            except Exception as e:
                return ControllerResult(success=False, message=f"Failed to start {target}", error=str(e))
        return app_controller.open_application(target)

    def stop(self, target: str) -> ControllerResult:
        target_lower = target.lower().strip()
        if target_lower.endswith(".exe"):
            target_lower = target_lower[:-4]
        if target_lower in self.PROTECTED_PROCESSES:
            return ControllerResult(
                success=False,
                message=f"Refusing to stop system process '{target}' — it is required for Windows to run.",
                error="Protected process",
            )
        try:
            if target_lower.isdigit():
                result = subprocess.run(["taskkill", "/PID", target_lower, "/T"], capture_output=True, text=True)
            else:
                result = subprocess.run(["taskkill", "/IM", f"{target_lower}.exe", "/T"], capture_output=True, text=True)
            if result.returncode == 0:
                return ControllerResult(success=True, message=f"Stopped {target}")
            return ControllerResult(success=False, message=f"Could not stop {target}: process not found", error=result.stderr.strip() or result.stdout.strip())
        except Exception as e:
            logger.error(f"Error stopping process {target}: {e}")
            return ControllerResult(success=False, message=f"Failed to stop {target}", error=str(e))

    def restart(self, target: str) -> ControllerResult:
        server = self._resolve_server(target)
        if server:
            stopped = self.stop_by_pattern(target)
        else:
            stopped = self.stop(target)
        if not stopped.success:
            return stopped
        return self.start(target)

    def stop_by_pattern(self, pattern: str) -> ControllerResult:
        pattern = pattern.lower()
        if any(p in pattern for p in ("backend", "server", "uvicorn", "frontend", "npm")):
            try:
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     f"Get-Process | Where-Object {{ $_.ProcessName -match '(uvicorn|python|npm|node)' }} | Stop-Process -Force"],
                    capture_output=True, text=True, timeout=10,
                )
                return ControllerResult(success=result.returncode == 0, message="Stopped matching dev processes")
            except Exception as e:
                return ControllerResult(success=False, message="Failed to stop dev processes", error=str(e))
        return self.stop(pattern)

    def monitor(self, target: str) -> ControllerResult:
        try:
            import psutil
            target_lower = target.lower().rstrip(".exe")
            rows = []
            for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
                name = (proc.info["name"] or "").lower()
                if name == target_lower or name == target_lower + ".exe" or target_lower in name:
                    rows.append({"pid": proc.info["pid"], "name": proc.info["name"],
                                 "cpu": round(proc.info["cpu_percent"] or 0, 1),
                                 "memory": round(proc.info["memory_percent"] or 0, 1),
                                 "status": proc.info["status"]})
            if rows:
                return ControllerResult(success=True, message=f"{target}: {len(rows)} running process(es)", data={"processes": rows})
            return ControllerResult(success=False, message=f"No running process named '{target}'", error="Process not found")
        except Exception as e:
            return ControllerResult(success=False, message="Failed to monitor process", error=str(e))


class TerminalController(BaseController):
    """Runs shell commands through a strict allowlist. Never blind execution."""

    ALLOWED_COMMANDS = {
        "npm", "npx", "node", "python", "python3", "pip", "pip3", "uvicorn",
        "git", "dir", "ls", "pwd", "echo", "whoami", "ipconfig", "netstat",
        "tasklist", "where", "ping", "hostname", "code",
    }
    BLOCKED_TOKENS = {
        "rm", "del", "format", "shutdown", "taskkill", "reg", "diskpart", "rd",
        "rmdir", "move", "ren", "cipher", "bcdedit", "bootcfg", "format",
        "remove-item", "stop-process", "set-itemproperty", "clear-content",
        "del /s", "rm -rf", "rmdir /s", ">nul", "format c:",
    }

    def run_command(self, command: str) -> ControllerResult:
        import shlex
        try:
            argv = shlex.split(command)
        except ValueError as e:
            return ControllerResult(success=False, message=f"Could not parse command: {e}", error=str(e))
        if not argv:
            return ControllerResult(success=False, message="Empty command", error="No command")
        first = argv[0].lower()
        if first not in self.ALLOWED_COMMANDS:
            return ControllerResult(
                success=False,
                message=f"Command '{first}' is not on the allowed list (npm, python, pip, uvicorn, git, node, ...)",
                error="Command not allowed",
            )
        lowered = command.lower()
        if any(blocked in lowered for blocked in self.BLOCKED_TOKENS):
            return ControllerResult(success=False, message="Command contains a blocked token and was refused.", error="Blocked token")
        try:
            from .isolated_executor import get_isolated_executor
            executor = get_isolated_executor()
            result = executor.execute_sync(
                argv[0],
                argv[1:],
                timeout=30,
                request_id=f"term_{uuid.uuid4().hex[:8]}",
            )
            output = (result.output or "").strip()
            if len(output) > 4000:
                output = output[-4000:] + "\n... (truncated)"
            if result.success:
                return ControllerResult(success=True, message=f"'{command}' completed", data={"output": output, "returncode": 0})
            return ControllerResult(
                success=False,
                message=f"'{command}' failed (exit {result.returncode})",
                error=(result.error or output or "command failed")[:2000],
                data={"output": output[:2000]},
            )
        except Exception as e:
            logger.error(f"Error running command: {e}")
            return ControllerResult(success=False, message="Failed to run command", error=str(e))

    def run_script(self, script_path: str) -> ControllerResult:
        path_obj = os.path.expanduser(script_path.strip().strip('"'))
        if not os.path.exists(path_obj):
            return ControllerResult(success=False, message=f"Script not found: {script_path}", error="Script not found")
        if not path_obj.lower().endswith(".py"):
            return ControllerResult(success=False, message="Only .py scripts are allowed to run", error="Script type not allowed")
        return self.run_command(f"python {path_obj}")


class BrowserController(BaseController):
    """Browser automation — delegates to the dedicated browser agent layer (no coordinate clicking)."""

    def _browser_command(self, intent: IntentType, target: Optional[str], params: dict) -> str:
        if intent == IntentType.OPEN_URL:
            url = target or params.get("url", "")
            if url and "://" not in url and " " not in url:
                url = f"https://{url}"
            return f"open {url}" if url else "open a new tab"
        if intent == IntentType.SEARCH_WEB:
            return f"search the web for {target or params.get('query', '')}"
        if intent == IntentType.OPEN_NEW_TAB:
            return "open a new tab"
        if intent == IntentType.CLOSE_TAB:
            return "close the current tab"
        if intent == IntentType.REFRESH_PAGE:
            return "refresh the page"
        if intent == IntentType.GO_BACK:
            return "go back"
        if intent == IntentType.GO_FORWARD:
            return "go forward"
        return ""

    async def execute(self, intent: IntentType, target: Optional[str], params: dict) -> ControllerResult:
        message = self._browser_command(intent, target, params)
        if not message:
            return ControllerResult(success=False, message="Unsupported browser action", error="Unsupported browser intent")
        try:
            from app.services.browser.intent import classify_browser_intent
            from app.services.browser.agent import browser_agent
            browser_intent = classify_browser_intent(message)
            if browser_intent is None:
                return ControllerResult(success=False, message="Could not route browser command", error="Browser intent failed")
            summary = ""
            ok = False
            async for event in browser_agent.run_plan(browser_intent):
                if event.get("type") == "content":
                    summary = event.get("content") or ""
                if event.get("type") == "done":
                    ok = bool(event.get("success"))
            return ControllerResult(
                success=ok,
                message=summary[:300] or ("Browser action completed" if ok else "Browser action failed"),
                error=None if ok else (summary[:300] or "Browser action failed"),
                data={"message": message},
            )
        except Exception as e:
            logger.error(f"Browser controller error: {e}")
            return ControllerResult(success=False, message="Browser action failed", error=str(e))


app_controller = ApplicationController()
file_controller = FileController()
folder_controller = FolderController()
system_controller = SystemController()
keyboard_controller = KeyboardController()
mouse_controller = MouseController()
window_controller = WindowController()
process_controller = ProcessController()
terminal_controller = TerminalController()
browser_controller = BrowserController()
