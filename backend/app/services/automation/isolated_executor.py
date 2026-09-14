"""Isolated subprocess handler for OS-level automation to avoid conflicts."""

import logging
import os
import platform
import subprocess
import threading
from typing import Optional, Dict, Callable
from dataclasses import dataclass
from queue import Queue
import json
import time

logger = logging.getLogger("hsbot.automation.isolated_executor")


@dataclass
class ExecutionRequest:
    """Request to execute in isolated subprocess."""
    command: str
    args: list
    timeout: int = 30
    callback: Optional[Callable] = None
    request_id: str = ""
    wait: bool = True


@dataclass
class ExecutionResult:
    """Result from isolated subprocess execution."""
    request_id: str
    success: bool
    output: str = ""
    error: str = ""
    returncode: int = -1
    execution_time_ms: float = 0.0


class IsolatedExecutor:
    """
    Executes OS commands in isolated subprocess windows to avoid conflicts
    and prevent blocking the main backend process.
    """
    
    def __init__(self, max_workers: int = 5):
        """
        Initialize isolated executor.
        
        Args:
            max_workers: Maximum number of concurrent subprocess workers
        """
        self.max_workers = max_workers
        self.request_queue: Queue = Queue()
        self.active_processes: Dict[str, subprocess.Popen] = {}
        self.os_type = platform.system().lower()
        self.is_windows = self.os_type == "windows"
        
        # Start worker threads
        self.workers = []
        for i in range(max_workers):
            worker = threading.Thread(target=self._worker_loop, daemon=True)
            worker.start()
            self.workers.append(worker)
        
        logger.info(f"IsolatedExecutor initialized with {max_workers} workers")
    
    def _worker_loop(self):
        """Worker loop that processes requests from the queue."""
        while True:
            try:
                request: ExecutionRequest = self.request_queue.get()
                if request is None:  # Shutdown signal
                    break
                
                result = self._execute_isolated(request)
                if request.callback:
                    try:
                        request.callback(result)
                    except Exception as e:
                        logger.error(f"Error in callback: {e}")
                
                self.request_queue.task_done()
            except Exception as e:
                logger.error(f"Worker error: {e}")
    
    def _execute_isolated(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute command in isolated subprocess."""
        start_time = time.time()
        
        try:
            # Prepare subprocess arguments
            if self.is_windows:
                # Windows: spawn new window
                creationflags = subprocess.CREATE_NEW_CONSOLE
            else:
                creationflags = 0
            
            # Build full command
            full_command = [request.command] + request.args
            
            logger.info(f"[{request.request_id}] Executing isolated: {' '.join(full_command)}")
            
            # Execute in isolated subprocess
            process = subprocess.Popen(
                full_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=creationflags,
                text=True
            )
            
            # Store process reference
            self.active_processes[request.request_id] = process

            if not request.wait:
                # Fire-and-forget (GUI apps never exit — e.g. Chrome, notepad).
                launch_ms = (time.time() - start_time) * 1000
                logger.info(f"[{request.request_id}] Launched detached (took {launch_ms:.0f}ms)")
                return ExecutionResult(
                    request_id=request.request_id,
                    success=True,
                    output="",
                    returncode=None,
                    execution_time_ms=launch_ms
                )

            try:
                # Wait with timeout
                stdout, stderr = process.communicate(timeout=request.timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                error_msg = f"Command timed out after {request.timeout}s"
                logger.warning(f"[{request.request_id}] {error_msg}")
                
                execution_time_ms = (time.time() - start_time) * 1000
                return ExecutionResult(
                    request_id=request.request_id,
                    success=False,
                    error=error_msg,
                    returncode=-1,
                    execution_time_ms=execution_time_ms
                )
            
            # Prepare result
            execution_time_ms = (time.time() - start_time) * 1000
            
            if process.returncode == 0:
                logger.info(f"[{request.request_id}] Success (took {execution_time_ms:.0f}ms)")
                return ExecutionResult(
                    request_id=request.request_id,
                    success=True,
                    output=stdout,
                    returncode=0,
                    execution_time_ms=execution_time_ms
                )
            else:
                logger.warning(f"[{request.request_id}] Failed with code {process.returncode}")
                return ExecutionResult(
                    request_id=request.request_id,
                    success=False,
                    output=stdout,
                    error=stderr or f"Process exited with code {process.returncode}",
                    returncode=process.returncode,
                    execution_time_ms=execution_time_ms
                )
        
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            logger.error(f"[{request.request_id}] Execution error: {e}")
            return ExecutionResult(
                request_id=request.request_id,
                success=False,
                error=str(e),
                returncode=-1,
                execution_time_ms=execution_time_ms
            )
        
        finally:
            # Cleanup
            if request.request_id in self.active_processes:
                del self.active_processes[request.request_id]
    
    def execute_async(
        self,
        command: str,
        args: list,
        timeout: int = 30,
        callback: Optional[Callable] = None,
        request_id: str = ""
    ):
        """
        Execute command asynchronously in isolated subprocess.
        
        Args:
            command: Command/executable to run
            args: List of arguments
            timeout: Timeout in seconds
            callback: Optional callback function to call with result
            request_id: Unique identifier for this request
        """
        request = ExecutionRequest(
            command=command,
            args=args,
            timeout=timeout,
            callback=callback,
            request_id=request_id or str(time.time())
        )
        self.request_queue.put(request)
        return request.request_id
    
    def execute_sync(
        self,
        command: str,
        args: list,
        timeout: int = 30,
        request_id: str = "",
        wait: bool = True
    ) -> ExecutionResult:
        """
        Execute command synchronously (blocks until complete unless wait=False).

        Args:
            command: Command/executable to run
            args: List of arguments
            timeout: Timeout in seconds
            request_id: Unique identifier for this request
            wait: When False, launch detached and return immediately (GUI apps)

        Returns:
            ExecutionResult with output and status
        """
        request = ExecutionRequest(
            command=command,
            args=args,
            timeout=timeout,
            request_id=request_id or str(time.time()),
            wait=wait
        )
        return self._execute_isolated(request)
    
    def kill_process(self, request_id: str) -> bool:
        """Kill an active process by request ID."""
        if request_id in self.active_processes:
            try:
                self.active_processes[request_id].kill()
                logger.info(f"Killed process: {request_id}")
                return True
            except Exception as e:
                logger.error(f"Error killing process {request_id}: {e}")
                return False
        return False
    
    def get_active_count(self) -> int:
        """Get number of active processes."""
        return len(self.active_processes)
    
    def shutdown(self):
        """Shutdown executor and workers."""
        logger.info("Shutting down IsolatedExecutor...")
        
        # Kill all active processes
        for request_id, process in list(self.active_processes.items()):
            try:
                process.kill()
            except Exception as e:
                logger.error(f"Error killing process {request_id}: {e}")
        
        # Stop workers
        for _ in self.workers:
            self.request_queue.put(None)
        
        for worker in self.workers:
            worker.join(timeout=5)
        
        logger.info("IsolatedExecutor shut down complete")


# Global instance
_isolated_executor = None


def get_isolated_executor() -> IsolatedExecutor:
    """Get or create isolated executor instance."""
    global _isolated_executor
    if _isolated_executor is None:
        _isolated_executor = IsolatedExecutor(max_workers=5)
    return _isolated_executor
