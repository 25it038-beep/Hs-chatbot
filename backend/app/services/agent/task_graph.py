import time
from typing import Dict, List, Optional, Any, Set

class TaskNode:
    """Represents a single discrete task in the agent execution graph."""
    def __init__(
        self,
        task_id: str,
        title: str,
        description: str = "",
        dependencies: Optional[List[str]] = None,
        tool_hint: Optional[str] = None
    ):
        self.id = task_id
        self.title = title
        self.description = description
        self.dependencies: List[str] = dependencies or []
        self.tool_hint = tool_hint
        self.status = "pending" # pending | running | completed | failed | blocked | skipped
        self.result: Optional[Any] = None
        self.error: Optional[str] = None
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "dependencies": self.dependencies,
            "tool_hint": self.tool_hint,
            "status": self.status,
            "error": self.error,
            "duration_s": round(self.completed_at - self.started_at, 2) if (self.started_at and self.completed_at) else None
        }

class TaskGraph:
    """
    Directed Acyclic Task Graph for the Agent Orchestrator.
    Manages ordering, dependency resolution, and task transitions.
    """
    def __init__(self, plan_id: str = "plan-1"):
        self.plan_id = plan_id
        self.tasks: Dict[str, TaskNode] = {}
        self.created_at = time.time()

    def add_task(self, task: TaskNode):
        self.tasks[task.id] = task

    def get_ready_tasks(self) -> List[TaskNode]:
        """Returns tasks whose dependencies are all completed and are currently pending."""
        ready = []
        for task in self.tasks.values():
            if task.status != "pending":
                continue
            deps_satisfied = all(
                self.tasks[dep_id].status == "completed"
                for dep_id in task.dependencies
                if dep_id in self.tasks
            )
            if deps_satisfied:
                ready.append(task)
            else:
                # If any dependency failed, mark as blocked
                if any(self.tasks[dep_id].status == "failed" for dep_id in task.dependencies if dep_id in self.tasks):
                    task.status = "blocked"
        return ready

    def mark_running(self, task_id: str):
        if task_id in self.tasks:
            self.tasks[task_id].status = "running"
            self.tasks[task_id].started_at = time.time()

    def mark_completed(self, task_id: str, result: Any = None):
        if task_id in self.tasks:
            self.tasks[task_id].status = "completed"
            self.tasks[task_id].result = result
            self.tasks[task_id].completed_at = time.time()

    def mark_failed(self, task_id: str, error: str):
        if task_id in self.tasks:
            self.tasks[task_id].status = "failed"
            self.tasks[task_id].error = error
            self.tasks[task_id].completed_at = time.time()

    def is_all_completed(self) -> bool:
        return all(t.status in ["completed", "skipped"] for t in self.tasks.values())

    def has_failures(self) -> bool:
        return any(t.status == "failed" for t in self.tasks.values())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "tasks": [t.to_dict() for t in self.tasks.values()],
            "is_completed": self.is_all_completed(),
            "has_failures": self.has_failures(),
            "total_count": len(self.tasks),
            "completed_count": sum(1 for t in self.tasks.values() if t.status == "completed")
        }
