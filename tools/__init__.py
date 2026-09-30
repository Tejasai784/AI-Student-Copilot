"""Tools Package Initialization.
Registers all safe tools with the global ToolRegistry.
"""
from tools.registry import get_tool_registry, BaseTool, ToolRegistry
from tools.calculator import CalculatorTool
from tools.python_sandbox import PythonSandboxTool
from tools.document_reader import DocumentReaderTool
from tools.semantic_search import SemanticSearchTool
from tools.tabular_reader import TabularReaderTool
from tools.web_research import WebResearchTool
from tools.quiz_generator import QuizGeneratorTool
from tools.report_generator import ReportGeneratorTool
from tools.task_manager import TaskManagerTool


def register_default_tools() -> ToolRegistry:
    registry = get_tool_registry()
    registry.register(CalculatorTool())
    registry.register(PythonSandboxTool())
    registry.register(DocumentReaderTool())
    registry.register(SemanticSearchTool())
    registry.register(TabularReaderTool())
    registry.register(WebResearchTool())
    registry.register(QuizGeneratorTool())
    registry.register(ReportGeneratorTool())
    registry.register(TaskManagerTool())
    return registry


# Auto-register on import
register_default_tools()

__all__ = [
    "get_tool_registry",
    "BaseTool",
    "ToolRegistry",
    "CalculatorTool",
    "PythonSandboxTool",
    "DocumentReaderTool",
    "SemanticSearchTool",
    "TabularReaderTool",
    "WebResearchTool",
    "QuizGeneratorTool",
    "ReportGeneratorTool",
    "TaskManagerTool"
]
