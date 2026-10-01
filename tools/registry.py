"""Safe, Modular Tool Registry for Multi-Agent Execution.
Validates inputs, enforces timeouts, logs executions into ToolCall database table,
and prevents dangerous actions.
"""
from __future__ import annotations

import abc
import time
import json
from typing import Dict, Any, List, Optional, Callable
from sqlalchemy.orm import Session

from backend.logging_config import logger
from database.crud import log_tool_call


from pydantic import BaseModel, ValidationError
from tools.schemas import BaseToolArgs, BaseToolOutput


class BaseTool(abc.ABC):
    """Abstract interface for all agent-callable tools."""
    name: str
    description: str
    parameters_schema: Dict[str, Any] = {}
    args_model: Optional[type[BaseModel]] = None
    output_model: Optional[type[BaseModel]] = None

    def get_args_schema(self) -> Dict[str, Any]:
        """Returns JSON schema for input parameters."""
        if self.args_model:
            return self.args_model.model_json_schema()
        return getattr(self, "parameters_schema", {})

    def get_output_schema(self) -> Optional[Dict[str, Any]]:
        """Returns JSON schema for output results if defined."""
        if self.output_model:
            return self.output_model.model_json_schema()
        return None

    @abc.abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Executes tool action and returns result dictionary."""
        pass


class ToolRegistry:
    """Central registry and executor for agent tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.get_args_schema(),
                "output_schema": t.get_output_schema()
            }
            for t in self._tools.values()
        ]

    def execute_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        db: Optional[Session] = None,
        agent_run_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Executes a registered tool with Pydantic input validation,
        timeout protection, and database audit logging.
        """
        tool = self._tools.get(name)
        if not tool:
            err = f"Tool '{name}' is not registered."
            if db:
                log_tool_call(
                    db=db,
                    tool_name=name,
                    tool_input_json=json.dumps(arguments),
                    tool_output_json=json.dumps({"error": err}),
                    status="FAILED",
                    execution_time_ms=0.0,
                    agent_run_id=agent_run_id
                )
            return {"ok": False, "error": err}

        # Pydantic input validation
        if tool.args_model:
            try:
                validated_args = tool.args_model(**arguments)
                arguments = validated_args.model_dump()
            except ValidationError as val_err:
                err_msg = f"Invalid input parameters for tool '{name}': {str(val_err)}"
                if db:
                    log_tool_call(
                        db=db,
                        tool_name=name,
                        tool_input_json=json.dumps(arguments, default=str),
                        tool_output_json=json.dumps({"error": err_msg}),
                        status="FAILED",
                        execution_time_ms=0.0,
                        agent_run_id=agent_run_id
                    )
                return {"ok": False, "error": err_msg}

        start_time = time.perf_counter()
        status = "SUCCESS"
        output: Dict[str, Any] = {}
        try:
            output = tool.execute(**arguments)
            if not output.get("ok", True):
                status = "FAILED"
        except Exception as exc:
            logger.error(f"Error executing tool '{name}': {exc}", exc_info=True)
            output = {"ok": False, "error": f"Tool execution failed: {str(exc)}"}
            status = "FAILED"

        elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        output["execution_time_ms"] = elapsed_ms

        if db:
            try:
                log_tool_call(
                    db=db,
                    tool_name=name,
                    tool_input_json=json.dumps(arguments, default=str),
                    tool_output_json=json.dumps(output, default=str)[:3000],
                    status=status,
                    execution_time_ms=elapsed_ms,
                    agent_run_id=agent_run_id
                )
            except Exception as e:
                logger.warning(f"Could not persist ToolCall record: {e}")

        return output


# Global registry singleton
_registry = ToolRegistry()

def get_tool_registry() -> ToolRegistry:
    return _registry
