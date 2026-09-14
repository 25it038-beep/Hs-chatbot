"""Main automation engine orchestrating intent detection and execution."""

import asyncio
import logging
import os
import re
import uuid
from datetime import datetime
from typing import Optional, Dict, List, Any, Callable
from .schema import AutomationIntent, AutomationAction, AutomationResponse, IntentType, RiskLevel
from .intent_detector import intent_detector
from .controllers import (
    app_controller, file_controller, folder_controller, system_controller,
    keyboard_controller, mouse_controller, window_controller,
    process_controller, terminal_controller, browser_controller,
    ControllerResult,
)

logger = logging.getLogger("hsbot.automation.engine")

# HIGH/CRITICAL actions can never be auto-executed — always confirmation.
_HARD_CONFIRM_RISKS = {RiskLevel.HIGH, RiskLevel.CRITICAL}


class AutomationEngine:
    """Main orchestration engine for OS automation."""

    def __init__(self):
        self.recent_actions: Dict[str, AutomationAction] = {}
        self.pending_confirmations: Dict[str, AutomationAction] = {}
        self.execution_log: List[Dict] = []
        self._subscribers: List[asyncio.Queue] = []
        self._cancel_event: Optional[asyncio.Event] = None
        self._active_request_id: Optional[str] = None

    # ── Event bus ──────────────────────────────────────────────

    def subscribe(self) -> asyncio.Queue:
        """Subscribe to engine events. Returns an asyncio.Queue."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        try:
            self._subscribers.remove(queue)
        except ValueError:
            pass

    async def _publish(self, event: dict):
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                    queue.put_nowait(event)
                except Exception:
                    pass

    # ── Command processing ─────────────────────────────────────

    async def process_command(self, user_command: str, user_id: Optional[str] = None,
                              voice_verified: Optional[bool] = None) -> AutomationResponse:
        """Process a user automation command (possibly a chain of commands)."""
        request_id = str(uuid.uuid4())
        self._active_request_id = request_id
        self._cancel_event = asyncio.Event()

        steps = self._split_chain(user_command)
        total = len(steps)
        if total == 0:
            return self._failed("No command detected.", "Empty command")

        await self._publish({"type": "chain_start", "request_id": request_id,
                             "steps": [s for s in steps], "total": total})

        results: List[dict] = []
        for index, step in enumerate(steps, start=1):
            if self._cancel_event.is_set():
                await self._publish({"type": "cancelled", "request_id": request_id,
                                     "step_index": index, "total": total})
                return AutomationResponse(success=False, action_id=request_id,
                                          message="Execution cancelled.", error="cancelled",
                                          step_index=index, total_steps=total,
                                          spoken="Execution cancelled.")
            response = await self._process_single(step, user_id, voice_verified, request_id, index, total)
            results.append(response.to_dict())
            await self._publish({
                "type": "step", "request_id": request_id, "step_index": index, "total": total,
                "command": step, "success": response.success, "message": response.message,
                "result": response.result, "error": response.error,
                "requires_confirmation": response.requires_confirmation,
                "confirmation_prompt": response.confirmation_prompt,
                "options": response.options, "action_id": response.action_id,
            })
            if response.requires_confirmation and not response.success:
                # Chain paused waiting for user confirmation.
                return response
            if not response.success:
                await self._publish({"type": "chain_failed", "request_id": request_id,
                                     "step_index": index, "total": total,
                                     "message": f"Step {index} failed: {response.message}"})
                return AutomationResponse(
                    success=False, action_id=request_id,
                    message=f"Stopped at step {index}/{total} — {response.message}",
                    error=response.error, step_index=index, total_steps=total,
                    spoken=f"Stopped at step {index}. {response.message}",
                )

        await self._publish({"type": "chain_done", "request_id": request_id,
                             "total": total, "results": results})
        first = results[-1]
        return AutomationResponse(
            success=True, action_id=request_id,
            message=f"Completed {total} action(s). {first.get('message', '')}",
            result={"steps": results}, step_index=total, total_steps=total,
            spoken=first.get("message", "Done."),
        )

    async def _process_single(self, user_command: str, user_id: Optional[str],
                              voice_verified: Optional[bool],
                              chain_request_id: str, index: int, total: int) -> AutomationResponse:
        """Process a single automation command."""
        try:
            intent = intent_detector.detect_intent(user_command)
            action_id = f"{chain_request_id[:8]}-{index}" if total > 1 else chain_request_id
            action = AutomationAction(action_id=action_id, intent=intent, state="detected")
            self.recent_actions[action_id] = action

            logger.info(f"Intent detected: {intent.intent.value} | Confidence: {intent.confidence} | Risk: {intent.risk_level}")

            if intent.intent == IntentType.UNKNOWN:
                return self._failed(intent.explanation, "Could not understand the command.", action_id, index, total)

            # Never auto-execute HIGH/CRITICAL actions.
            if intent.risk_level in _HARD_CONFIRM_RISKS:
                intent.requires_confirmation = True

            # Voice identity gate: rejected speakers never get to confirm critical actions.
            if voice_verified is False and intent.risk_level in _HARD_CONFIRM_RISKS:
                return self._failed(
                    "Voice authentication failed. This action requires a verified voice match.",
                    "voice not verified", action_id, index, total,
                )

            # Trusted voice match bypasses the UI prompt for MEDIUM (not HIGH/CRITICAL).
            if voice_verified is True and intent.risk_level == RiskLevel.MEDIUM:
                intent.requires_confirmation = False

            if intent.requires_confirmation:
                self.pending_confirmations[action_id] = action
                await self._publish({"type": "confirmation_required", "action_id": action_id,
                                     "request_id": chain_request_id, "prompt": intent.explanation,
                                     "risk": intent.risk_level.value})
                return AutomationResponse(
                    success=False, action_id=action_id,
                    message=f"This action requires confirmation: {intent.explanation}",
                    requires_confirmation=True,
                    confirmation_prompt=f"Do you want to {intent.explanation.lower()}?",
                    step_index=index, total_steps=total,
                    spoken=f"{intent.explanation}. Is that okay?",
                )

            return await self._execute_action(action_id, intent, user_id, index, total)
        except Exception as e:
            logger.error(f"Error processing command: {e}", exc_info=True)
            return self._failed("An unexpected error occurred while processing your command.",
                                str(e), "error", index, total)

    def _failed(self, message: str, error: str, action_id: str = "error",
                index: int = 1, total: int = 1) -> AutomationResponse:
        return AutomationResponse(success=False, action_id=action_id, message=message,
                                  error=error, step_index=index, total_steps=total,
                                  spoken=message)

    async def confirm_action(self, action_id: str, confirmed: bool,
                             user_id: Optional[str] = None,
                             choice: Optional[str] = None,
                             voice_verified: Optional[bool] = None) -> AutomationResponse:
        """Confirm or cancel a pending action."""
        if action_id not in self.pending_confirmations:
            return AutomationResponse(
                success=False, action_id=action_id,
                message="No pending confirmation for this action ID.",
                error="Action not found",
                spoken="No pending confirmation.",
            )

        action = self.pending_confirmations.pop(action_id)

        if not confirmed:
            action.state = "cancelled"
            self.recent_actions[action_id] = action
            await self._publish({"type": "confirmed", "action_id": action_id, "confirmed": False})
            return AutomationResponse(success=False, action_id=action_id,
                                      message="Action cancelled.", spoken="Cancelled.")

        # Ambiguity resolution: choice selects among candidate options.
        if choice and action.intent.intent in (IntentType.OPEN_FOLDER, IntentType.OPEN_APPLICATION):
            action.intent.target = choice
            if action.intent.intent == IntentType.OPEN_FOLDER:
                action.intent.parameters["path"] = choice
            else:
                action.intent.parameters["app"] = os.path.basename(choice)

        # Voice gate re-check at execution time.
        if voice_verified is False and action.intent.risk_level in _HARD_CONFIRM_RISKS:
            return self._failed("Voice authentication failed.", "voice not verified", action_id)

        await self._publish({"type": "confirmed", "action_id": action_id, "confirmed": True})
        response = await self._execute_action(action_id, action.intent, user_id, 1, 1)
        response.requires_confirmation = False
        return response

    async def _execute_action(self, action_id: str, intent: AutomationIntent,
                              user_id: Optional[str], index: int, total: int) -> AutomationResponse:
        """Execute an automation action."""
        action = self.recent_actions.get(action_id)
        if not action:
            action = AutomationAction(action_id=action_id, intent=intent)
            self.recent_actions[action_id] = action

        action.state = "executing"
        start_time = datetime.now()
        await self._publish({"type": "action_start", "action_id": action_id,
                             "intent": intent.intent.value, "target": intent.target,
                             "explanation": intent.explanation, "step_index": index, "total": total})

        def _cancelled_response():
            return AutomationResponse(
                success=False, action_id=action_id, message="Execution cancelled.",
                error="cancelled", step_index=index, total_steps=total,
                spoken="Execution cancelled.",
            )

        if self._cancel_event is not None and self._cancel_event.is_set():
            return _cancelled_response()

        try:
            result = await self._route_intent(intent)
            if asyncio.iscoroutine(result):
                result = await result
            if self._cancel_event is not None and self._cancel_event.is_set():
                return _cancelled_response()
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Ambiguity: controller returned candidate options → await a choice.
            if (not result.success and isinstance(result.data, dict)
                    and result.data.get("options")):
                action.state = "awaiting_choice"
                action.error = result.error
                action.result = result.data
                self.pending_confirmations[action_id] = action
                await self._publish({"type": "confirmation_required", "action_id": action_id,
                                     "prompt": result.message, "risk": intent.risk_level.value,
                                     "options": result.data["options"]})
                return AutomationResponse(
                    success=False, action_id=action_id,
                    message=result.message, result=result.data,
                    requires_confirmation=True, confirmation_prompt=result.message,
                    options=result.data["options"], error=result.error,
                    step_index=index, total_steps=total,
                    spoken=result.message,
                )

            action.state = "success" if result.success else "failed"
            action.result = result.data
            action.error = result.error
            action.execution_time_ms = execution_time_ms
            action.verification_passed = result.success

            self._log_execution(action_id, intent, result, execution_time_ms, user_id)
            await self._publish({"type": "action_done", "action_id": action_id,
                                 "intent": intent.intent.value, "target": intent.target,
                                 "success": result.success, "message": result.message,
                                 "result": result.data, "error": result.error,
                                 "execution_time_ms": execution_time_ms,
                                 "step_index": index, "total": total})

            return AutomationResponse(
                success=result.success, action_id=action_id,
                message=result.message, result=result.data, error=result.error,
                execution_time_ms=execution_time_ms, step_index=index, total_steps=total,
                spoken=result.message,
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            action.state = "failed"
            action.error = str(e)
            action.execution_time_ms = execution_time_ms
            logger.error(f"Action execution failed: {e}", exc_info=True)
            self._log_execution(action_id, intent, None, execution_time_ms, user_id, error=str(e))
            await self._publish({"type": "action_done", "action_id": action_id,
                                 "intent": intent.intent.value, "target": intent.target,
                                 "success": False, "message": "Action execution failed.",
                                 "error": str(e), "step_index": index, "total": total})
            return AutomationResponse(success=False, action_id=action_id,
                                      message="Action execution failed.", error=str(e),
                                      execution_time_ms=execution_time_ms,
                                      step_index=index, total_steps=total,
                                      spoken="That action failed.")

    async def _route_intent(self, intent: AutomationIntent) -> ControllerResult:
        """Route an intent to the appropriate controller."""
        params = intent.parameters
        target = intent.target
        destination = params.get("destination")

        # ── Application ──
        if intent.intent == IntentType.OPEN_APPLICATION:
            app = params.get("app") or target or ""
            # "open the project" → folder ambiguity resolution
            if app in ("project", "projects") or app.startswith("my project"):
                return await self._open_folder_with_ambiguity("project")
            return app_controller.open_application(app)
        if intent.intent == IntentType.CLOSE_APPLICATION:
            return app_controller.close_application(params.get("app") or target or "")
        if intent.intent == IntentType.SWITCH_APPLICATION:
            return app_controller.switch_application(params.get("app") or target or "")
        if intent.intent == IntentType.MINIMIZE_APPLICATION:
            app = params.get("app") or target or ""
            if "window" in app:
                return window_controller.minimize()
            return app_controller.minimize_application(app)
        if intent.intent == IntentType.MAXIMIZE_APPLICATION:
            app = params.get("app") or target or ""
            if "window" in app:
                return window_controller.maximize()
            return app_controller.maximize_application(app)
        if intent.intent == IntentType.RESTART_APPLICATION:
            return app_controller.restart_application(params.get("app") or target or "")

        # ── Files ──
        if intent.intent == IntentType.CREATE_FILE:
            return file_controller.create_file(target or params.get("name") or "New File.txt")
        if intent.intent == IntentType.DELETE_FILE:
            return file_controller.delete_file(target or "")
        if intent.intent == IntentType.OPEN_FILE:
            return file_controller.open_file(target or "")
        if intent.intent == IntentType.RENAME_FILE:
            return file_controller.rename_file(target or "", params.get("new_name") or "")
        if intent.intent == IntentType.COPY_FILE:
            return file_controller.copy_file(target or "", destination or "")
        if intent.intent == IntentType.MOVE_FILE:
            return file_controller.move_file(target or "", destination or "")
        if intent.intent == IntentType.SEARCH_FILES:
            return file_controller.search_files(target or "")
        if intent.intent == IntentType.FILE_METADATA:
            return file_controller.file_metadata(target or "")

        # ── Folders ──
        if intent.intent == IntentType.CREATE_FOLDER:
            return folder_controller.create_folder(target or params.get("name") or "New Folder")
        if intent.intent == IntentType.DELETE_FOLDER:
            return folder_controller.delete_folder(target or "")
        if intent.intent == IntentType.RENAME_FOLDER:
            return folder_controller.rename_folder(target or "", params.get("new_name") or "")
        if intent.intent == IntentType.COPY_FOLDER:
            return folder_controller.copy_folder(target or "", destination or "")
        if intent.intent == IntentType.MOVE_FOLDER:
            return folder_controller.move_folder(target or "", destination or "")
        if intent.intent == IntentType.SEARCH_FOLDERS:
            return folder_controller.search_folders(target or "")
        if intent.intent == IntentType.OPEN_FOLDER:
            folder_path = target or params.get("path", "")
            if not folder_path or folder_path in ("downloads", "documents", "desktop"):
                return self._open_known_folder(folder_path)
            # URL-like target ("open youtube.com") → browser, not folder.
            if "." in folder_path and " " not in folder_path and "\\" not in folder_path and "/" not in folder_path:
                return await browser_controller.execute(IntentType.OPEN_URL, folder_path, {"url": folder_path})
            if not os.path.isabs(os.path.expanduser(folder_path)) or not os.path.isdir(os.path.expanduser(folder_path)):
                # Not a literal absolute path — try ambiguity resolution
                return await self._open_folder_with_ambiguity(folder_path)
            return folder_controller.open_folder(folder_path)

        # ── Keyboard ──
        if intent.intent == IntentType.KEY_PRESS:
            return keyboard_controller.press(target or "")
        if intent.intent == IntentType.TYPE_TEXT:
            return keyboard_controller.type_text(target or "")

        # ── Mouse ──
        if intent.intent == IntentType.CLICK:
            return mouse_controller.click("left")
        if intent.intent == IntentType.RIGHT_CLICK:
            return mouse_controller.click("right")
        if intent.intent == IntentType.DOUBLE_CLICK:
            return mouse_controller.double_click()
        if intent.intent == IntentType.SCROLL:
            return mouse_controller.scroll(params.get("direction", "down"))
        if intent.intent == IntentType.DRAG:
            return mouse_controller.move(50, 50)

        # ── Windows ──
        if intent.intent == IntentType.MAXIMIZE_WINDOW:
            return window_controller.maximize()
        if intent.intent == IntentType.MINIMIZE_WINDOW:
            return window_controller.minimize()
        if intent.intent == IntentType.RESTORE_WINDOW:
            return window_controller.restore()
        if intent.intent == IntentType.CLOSE_WINDOW:
            return window_controller.close()
        if intent.intent == IntentType.SNAP_WINDOW_LEFT:
            return window_controller.snap("left")
        if intent.intent == IntentType.SNAP_WINDOW_RIGHT:
            return window_controller.snap("right")
        if intent.intent == IntentType.SHOW_DESKTOP:
            return window_controller.show_desktop()

        # ── System ──
        if intent.intent == IntentType.GET_CPU_USAGE and params.get("combined"):
            results = [
                system_controller.get_cpu_usage(),
                system_controller.get_ram_usage(),
            ]
            ok = all(r.success for r in results)
            return ControllerResult(
                success=ok,
                message="; ".join(r.message for r in results),
                data={r.message.split(":")[0].strip().lower(): r.data for r in results},
                error=next((r.error for r in results if not r.success), None),
            )
        if intent.intent == IntentType.SET_VOLUME:
            return system_controller.set_volume(params.get("level", 50))
        if intent.intent == IntentType.ADJUST_VOLUME:
            return system_controller.adjust_volume(params.get("direction", "up"), params.get("delta", 5))
        if intent.intent == IntentType.GET_VOLUME:
            return system_controller.get_volume()
        if intent.intent == IntentType.SET_BRIGHTNESS:
            return system_controller.set_brightness(params.get("level", 50))
        if intent.intent == IntentType.GET_BRIGHTNESS:
            return system_controller.get_brightness()
        if intent.intent == IntentType.GET_CPU_USAGE:
            return system_controller.get_cpu_usage()
        if intent.intent == IntentType.GET_RAM_USAGE:
            return system_controller.get_ram_usage()
        if intent.intent == IntentType.GET_DISK_USAGE:
            return system_controller.get_disk_usage()
        if intent.intent == IntentType.TAKE_SCREENSHOT:
            return system_controller.take_screenshot()
        if intent.intent == IntentType.LOCK_SCREEN:
            return system_controller.lock_screen()
        if intent.intent == IntentType.SLEEP:
            return system_controller.sleep()
        if intent.intent == IntentType.RESTART:
            return system_controller.restart()
        if intent.intent == IntentType.SHUTDOWN:
            return system_controller.shutdown()
        if intent.intent == IntentType.CHECK_WIFI:
            return system_controller.check_wifi()
        if intent.intent == IntentType.CHECK_BLUETOOTH:
            return system_controller.check_bluetooth()
        if intent.intent == IntentType.CHECK_NETWORK:
            return system_controller.check_network()
        if intent.intent == IntentType.CHECK_BATTERY:
            return system_controller.check_battery()

        # ── Browser (delegated to dedicated browser agent) ──
        if intent.intent in (IntentType.OPEN_URL, IntentType.SEARCH_WEB, IntentType.OPEN_NEW_TAB,
                             IntentType.CLOSE_TAB, IntentType.REFRESH_PAGE,
                             IntentType.GO_BACK, IntentType.GO_FORWARD):
            return await browser_controller.execute(intent.intent, target, params)

        # ── Processes / Terminal ──
        if intent.intent == IntentType.LIST_PROCESSES:
            return process_controller.list_processes()
        if intent.intent == IntentType.START_PROCESS:
            return process_controller.start(params.get("server") or target or "")
        if intent.intent == IntentType.STOP_PROCESS:
            return process_controller.stop(target or "")
        if intent.intent == IntentType.RESTART_PROCESS:
            return process_controller.restart(target or "")
        if intent.intent == IntentType.MONITOR_PROCESS:
            return process_controller.monitor(target or "")
        if intent.intent == IntentType.RUN_COMMAND:
            return terminal_controller.run_command(target or "")
        if intent.intent == IntentType.RUN_SCRIPT:
            return terminal_controller.run_script(target or "")

        return ControllerResult(success=False,
                                message=f"Intent '{intent.intent.value}' is not yet implemented.",
                                error="Unsupported intent")

    def _open_known_folder(self, folder_key: str) -> ControllerResult:
        home = os.path.expanduser("~")
        folder_map = {
            "downloads": os.path.join(home, "Downloads"),
            "documents": os.path.join(home, "Documents"),
            "desktop": os.path.join(home, "Desktop"),
        }
        return folder_controller.open_folder(folder_map.get(folder_key, folder_key))

    def _resolve_path(self, value: str) -> str:
        """Resolve user-friendly locations like 'Documents' to real paths."""
        value = (value or "").strip().strip('"')
        home = os.path.expanduser("~")
        known = {
            "documents": os.path.join(home, "Documents"),
            "downloads": os.path.join(home, "Downloads"),
            "desktop": os.path.join(home, "Desktop"),
            "pictures": os.path.join(home, "Pictures"),
            "music": os.path.join(home, "Music"),
            "videos": os.path.join(home, "Videos"),
            "home": home,
        }
        lowered = value.lower()
        if lowered in known:
            return known[lowered]
        if value.startswith("~"):
            return os.path.expanduser(value)
        return value

    async def _open_folder_with_ambiguity(self, name: str) -> ControllerResult:
        """Resolve ambiguous folder names — never randomly pick one."""
        candidates = folder_controller.find_folder_candidates(name)
        if not candidates:
            return ControllerResult(success=False,
                                    message=f"Could not find a folder named '{name}' on this computer.",
                                    error="Folder not found")
        if len(candidates) == 1:
            return folder_controller.open_folder(candidates[0])
        # Ambiguous — require user choice.
        return ControllerResult(
            success=False,
            message=f"Multiple matches for '{name}'. Which one should I open?",
            error="ambiguous",
            data={"options": candidates},
        )

    # ── Chaining ───────────────────────────────────────────────

    _COMBINED_SINGLE = re.compile(
        r"^(?:check|get|show|what is|what's)\b.*\b(?:and|&)\b.*\b(?:usage|status|level|%|battery|wifi|volume)\b",
        re.I,
    )

    def _split_chain(self, command: str) -> List[str]:
        """Split a command into sequential steps on ', ' / ' and ' / ' then '."""
        text = command.strip()
        if not text:
            return []
        # "check cpu and ram usage" is ONE combined query, not a chain.
        if self._COMBINED_SINGLE.match(text):
            return [text]
        parts = re.split(r"\s+(?:and|then)\s+|,\s*(?:and\s+)?", text)
        steps = [p.strip().strip(".") for p in parts if p.strip()]
        if not steps:
            steps = [text]
        return steps

    async def cancel(self) -> bool:
        """Cancel the currently active chain."""
        if self._cancel_event:
            self._cancel_event.set()
            logger.info("Automation chain cancellation requested")
            return True
        return False

    # ── Status / logs ──────────────────────────────────────────

    def get_action_status(self, action_id: str) -> Optional[dict]:
        if action_id in self.recent_actions:
            action = self.recent_actions[action_id]
            return {
                "action_id": action.action_id,
                "state": action.state,
                "intent": action.intent.intent.value,
                "target": action.intent.target,
                "risk": action.intent.risk_level.value,
                "result": action.result,
                "error": action.error,
                "verification_passed": action.verification_passed,
                "execution_time_ms": action.execution_time_ms,
            }
        return None

    def get_pending_confirmations(self) -> List[dict]:
        return [
            {"action_id": a.action_id, "intent": a.intent.intent.value,
             "target": a.intent.target, "explanation": a.intent.explanation,
             "risk": a.intent.risk_level.value}
            for a in self.pending_confirmations.values()
        ]

    def get_execution_log(self, limit: int = 50, user_id: Optional[str] = None) -> list[dict]:
        entries = self.execution_log[-limit:]
        if user_id:
            entries = [e for e in entries if e.get("user_id") == user_id]
        return entries

    def _log_execution(self, action_id: str, intent: AutomationIntent,
                       result: Optional[ControllerResult], execution_time_ms: float,
                       user_id: Optional[str], error: Optional[str] = None):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action_id": action_id,
            "user_id": user_id,
            "intent": intent.intent.value,
            "category": intent.category,
            "target": intent.target,
            "parameters": intent.parameters,
            "risk_level": intent.risk_level.value,
            "confidence": intent.confidence,
            "execution_time_ms": execution_time_ms,
            "success": result.success if result else False,
            "error": error or (result.error if result else None),
            "explanation": intent.explanation,
        }
        self.execution_log.append(log_entry)
        logger.info(f"Action logged: {action_id} | Intent: {intent.intent.value} | Success: {result.success if result else False} | Time: {execution_time_ms:.0f}ms")


automation_engine = AutomationEngine()
