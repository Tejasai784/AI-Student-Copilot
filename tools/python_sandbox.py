"""Safe Python Execution Sandbox Tool.
Executes short educational Python code snippets in a restricted execution context.
Enforces AST security checks, strict timeout limits (3 seconds), and captures stdout/stderr.
"""
from __future__ import annotations

import ast
import io
import sys
import threading
from typing import Dict, Any, List
from tools.registry import BaseTool


import tempfile
from tools.schemas import PythonSandboxInput

FORBIDDEN_MODULES = {
    "os", "sys", "subprocess", "socket", "requests", "urllib", "urllib3",
    "http", "shutil", "pathlib", "ctypes", "builtins", "__builtin__",
    "posix", "nt", "_thread", "threading", "multiprocessing", "asyncio",
    "signal", "pty", "commands", "pickle", "shelve", "webbrowser",
    "importlib", "inspect", "linecache", "gc", "code", "codeop"
}

FORBIDDEN_CALLS = {
    "open", "exec", "eval", "compile", "getattr", "setattr",
    "delattr", "__import__", "globals", "locals", "exit", "quit",
    "input", "breakpoint", "help", "memoryview"
}

FORBIDDEN_ATTRIBUTES = {
    "__subclasses__", "__bases__", "__class__", "__globals__",
    "__code__", "__closure__", "__dict__", "__builtins__",
    "__import__", "__loader__", "__spec__", "__package__"
}


def _validate_ast_safety(tree: ast.AST) -> List[str]:
    """Inspects AST nodes and flags forbidden imports, dangerous calls, and introspection escapes."""
    violations = []
    for node in ast.walk(tree):
        # Check imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_pkg = alias.name.split(".")[0]
                if root_pkg in FORBIDDEN_MODULES:
                    violations.append(f"Importing forbidden module: '{alias.name}'")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root_pkg = node.module.split(".")[0]
                if root_pkg in FORBIDDEN_MODULES:
                    violations.append(f"Importing from forbidden module: '{node.module}'")
        # Check forbidden built-in calls
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in FORBIDDEN_CALLS:
                    violations.append(f"Forbidden function call: '{node.func.id}()'")
            elif isinstance(node.func, ast.Attribute):
                if node.func.attr in FORBIDDEN_ATTRIBUTES:
                    violations.append(f"Forbidden introspective attribute access: '{node.func.attr}'")
        elif isinstance(node, ast.Attribute):
            if node.attr in FORBIDDEN_ATTRIBUTES:
                violations.append(f"Forbidden introspective attribute access: '{node.attr}'")

    return violations


class PythonSandboxTool(BaseTool):
    name = "python_sandbox"
    description = "Safely executes educational Python code snippets in an isolated environment with strict timeout (3s) and captures output."
    args_model = PythonSandboxInput
    parameters_schema = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python source code to execute and test."
            }
        },
        "required": ["code"]
    }

    def execute(self, code: str, timeout_seconds: float = 3.0, **kwargs) -> Dict[str, Any]:
        src = (code or "").strip()
        if not src:
            return {"ok": False, "error": "No Python code provided."}

        # 1. Parse and validate AST
        try:
            tree = ast.parse(src)
        except SyntaxError as syn_err:
            return {
                "ok": False,
                "error": f"SyntaxError on line {syn_err.lineno}: {syn_err.msg}",
                "stdout": "",
                "stderr": str(syn_err)
            }

        violations = _validate_ast_safety(tree)
        if violations:
            return {
                "ok": False,
                "error": f"Security restriction: {'; '.join(violations)}",
                "stdout": "",
                "stderr": "Execution blocked due to security policies."
            }

        # 2. Prepare safe execution environment
        safe_globals = {
            "__builtins__": {
                "abs": abs, "all": all, "any": any, "bin": bin, "bool": bool,
                "dict": dict, "divmod": divmod, "enumerate": enumerate,
                "filter": filter, "float": float, "format": format, "hex": hex,
                "int": int, "isinstance": isinstance, "issubclass": issubclass,
                "iter": iter, "len": len, "list": list, "map": map, "max": max,
                "min": min, "next": next, "oct": oct, "ord": ord, "pow": pow,
                "print": print, "range": range, "reversed": reversed,
                "round": round, "set": set, "slice": slice, "sorted": sorted,
                "str": str, "sum": sum, "tuple": tuple, "zip": zip,
                "Exception": Exception, "ValueError": ValueError, "TypeError": TypeError,
                "IndexError": IndexError, "KeyError": KeyError, "ZeroDivisionError": ZeroDivisionError,
                "True": True, "False": False, "None": None,
            }
        }
        # Allow safe math and collections
        import math, collections, itertools, re
        safe_globals["math"] = math
        safe_globals["collections"] = collections
        safe_globals["itertools"] = itertools
        safe_globals["re"] = re

        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        exec_error = None

        def run_target():
            nonlocal exec_error
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = stdout_buf
            sys.stderr = stderr_buf
            try:
                compiled = compile(tree, filename="<student_sandbox>", mode="exec")
                exec(compiled, safe_globals, {})
            except Exception as e:
                exec_error = e
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr

        thread = threading.Thread(target=run_target)
        thread.start()
        thread.join(timeout=timeout_seconds)

        if thread.is_alive():
            return {
                "ok": False,
                "error": f"Execution timed out ({timeout_seconds}s limit exceeded). Possible infinite loop.",
                "stdout": stdout_buf.getvalue(),
                "stderr": "Timeout expired."
            }

        out_str = stdout_buf.getvalue()
        err_str = stderr_buf.getvalue()
        if exec_error:
            return {
                "ok": False,
                "error": f"{type(exec_error).__name__}: {str(exec_error)}",
                "stdout": out_str,
                "stderr": f"{type(exec_error).__name__}: {str(exec_error)}"
            }

        return {
            "ok": True,
            "stdout": out_str,
            "stderr": err_str,
            "summary": "Executed successfully with 0 errors."
        }
