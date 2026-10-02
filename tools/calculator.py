"""Safe Mathematical Calculator Tool.
Evaluates arithmetic and mathematical expressions using a strict AST visitor.
No raw eval() or arbitrary code execution is permitted.
"""
from __future__ import annotations

import ast
import math
import operator
from typing import Dict, Any
from tools.registry import BaseTool


_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_ALLOWED_FUNCTIONS = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "abs": abs,
    "round": round,
    "floor": math.floor,
    "ceil": math.ceil,
}

_ALLOWED_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
}


def _safe_eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _safe_eval_node(node.body)
    elif isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError(f"Unsupported constant type: {type(node.value)}")
    elif isinstance(node, ast.Name):
        if node.id in _ALLOWED_CONSTANTS:
            return float(_ALLOWED_CONSTANTS[node.id])
        raise ValueError(f"Unknown or forbidden identifier: {node.id}")
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type in _ALLOWED_OPERATORS:
            operand = _safe_eval_node(node.operand)
            return float(_ALLOWED_OPERATORS[op_type](operand))
        raise ValueError(f"Forbidden unary operator: {op_type}")
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type in _ALLOWED_OPERATORS:
            left = _safe_eval_node(node.left)
            right = _safe_eval_node(node.right)
            if op_type == ast.Pow and (abs(left) > 1000 or abs(right) > 100):
                raise ValueError("Exponentiation values too large to evaluate safely.")
            return float(_ALLOWED_OPERATORS[op_type](left, right))
        raise ValueError(f"Forbidden binary operator: {op_type}")
    elif isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in _ALLOWED_FUNCTIONS:
            fn = _ALLOWED_FUNCTIONS[node.func.id]
            args = [_safe_eval_node(arg) for arg in node.args]
            return float(fn(*args))
        raise ValueError(f"Forbidden or unknown function call in calculator.")
    else:
        raise ValueError(f"Unsupported syntax in expression: {type(node).__name__}")


from tools.schemas import CalculatorInput


class CalculatorTool(BaseTool):
    name = "calculator"
    description = "Safely evaluates mathematical expressions (arithmetic, powers, trigonometry, logarithms, sqrt)."
    args_model = CalculatorInput
    parameters_schema = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Mathematical expression to evaluate, e.g. '(15 * 4) + sqrt(144)' or '2**10 - 24'."
            }
        },
        "required": ["expression"]
    }

    def execute(self, expression: str, **kwargs) -> Dict[str, Any]:
        expr = (expression or "").strip()
        if not expr:
            return {"ok": False, "error": "Empty expression provided."}
        try:
            parsed = ast.parse(expr, mode="eval")
            result = _safe_eval_node(parsed)
            # Format integer nicely if whole number
            if result.is_integer():
                formatted = str(int(result))
            else:
                formatted = f"{result:.6f}".rstrip("0").rstrip(".")

            return {
                "ok": True,
                "expression": expr,
                "result": result,
                "formatted_result": formatted
            }
        except ZeroDivisionError:
            return {"ok": False, "error": "Division by zero."}
        except Exception as e:
            return {"ok": False, "error": f"Invalid mathematical expression: {str(e)}"}
