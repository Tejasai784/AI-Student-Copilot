"""Task & State Manager Tool.
Enables agents to inspect active goals, create subtasks, and update completion status.
"""
from __future__ import annotations

from typing import Dict, Any, Optional
from tools.registry import BaseTool
from database.database import get_db
from database.crud import get_goals, get_goal_by_id, create_task, update_task_status, toggle_task_completion


from tools.schemas import TaskManagerInput


class TaskManagerTool(BaseTool):
    name = "task_state_manager"
    description = "Queries, creates, or updates academic goals and decomposed subtasks."
    args_model = TaskManagerInput
    parameters_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list_goals", "get_goal", "create_subtask", "complete_task"],
                "description": "Action to perform."
            },
            "goal_id": {
                "type": "integer",
                "description": "Goal ID (for get_goal or create_subtask)."
            },
            "task_id": {
                "type": "integer",
                "description": "Task ID (for complete_task)."
            },
            "task_title": {
                "type": "string",
                "description": "Title when creating a subtask."
            }
        },
        "required": ["action"]
    }

    def execute(
        self,
        action: str,
        goal_id: Optional[int] = None,
        task_id: Optional[int] = None,
        task_title: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        with get_db() as db:
            if action == "list_goals":
                goals = get_goals(db)
                return {
                    "ok": True,
                    "count": len(goals),
                    "goals": [
                        {
                            "id": g.id,
                            "title": g.title,
                            "status": g.status,
                            "progress": g.progress_percentage,
                            "tasks_count": len(g.tasks)
                        }
                        for g in goals
                    ]
                }

            elif action == "get_goal":
                if not goal_id:
                    return {"ok": False, "error": "goal_id is required."}
                goal = get_goal_by_id(db, goal_id)
                if not goal:
                    return {"ok": False, "error": f"Goal #{goal_id} not found."}
                return {
                    "ok": True,
                    "id": goal.id,
                    "title": goal.title,
                    "objective": goal.objective,
                    "status": goal.status,
                    "progress": goal.progress_percentage,
                    "tasks": [
                        {
                            "id": t.id,
                            "title": t.title,
                            "status": t.status,
                            "agent_assigned": t.agent_assigned,
                            "effort_minutes": t.effort_estimate_minutes
                        }
                        for t in goal.tasks
                    ]
                }

            elif action == "create_subtask":
                if not goal_id or not task_title:
                    return {"ok": False, "error": "goal_id and task_title are required."}
                t = create_task(db=db, goal_id=goal_id, title=task_title)
                return {"ok": True, "task_id": t.id, "title": t.title, "status": t.status}

            elif action == "complete_task":
                if not task_id:
                    return {"ok": False, "error": "task_id is required."}
                t = update_task_status(db=db, task_id=task_id, status="COMPLETED")
                if not t:
                    return {"ok": False, "error": f"Task #{task_id} not found."}
                return {"ok": True, "task_id": t.id, "title": t.title, "status": t.status}

            return {"ok": False, "error": f"Unknown action: '{action}'"}
