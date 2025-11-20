"""Calculator tool for Freya with AST-based safe evaluation."""

from __future__ import annotations

import ast
import math
import operator
from typing import Union

from .base import FreyaTool, ToolResult


class CalculatorTool(FreyaTool):
    """Evaluate mathematical expressions safely using AST parsing (no eval())."""

    # Safe binary operators
    SAFE_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.Mod: operator.mod,
        ast.FloorDiv: operator.floordiv,
    }

    # Safe unary operators
    SAFE_UNARY_OPERATORS = {
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    # Safe mathematical functions
    SAFE_FUNCTIONS = {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "pow": pow,
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log,
        "log10": math.log10,
        "exp": math.exp,
        "floor": math.floor,
        "ceil": math.ceil,
    }

    # Safe constants
    SAFE_CONSTANTS = {
        "pi": math.pi,
        "e": math.e,
    }

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Calculate mathematical expressions (supports +, -, *, /, ^, sqrt, sin, cos, etc.)"

    def _eval_node(self, node: ast.AST) -> Union[int, float]:
        """Recursively evaluate AST nodes safely."""
        if isinstance(node, ast.Constant):  # Python 3.8+
            if not isinstance(node.value, (int, float)):
                raise ValueError(f"Only numbers allowed, got: {type(node.value).__name__}")
            return node.value

        elif isinstance(node, ast.Num):  # Python 3.7 compatibility
            return node.n

        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            op = self.SAFE_OPERATORS.get(type(node.op))
            if op is None:
                raise ValueError(f"Operator not allowed: {type(node.op).__name__}")
            return op(left, right)

        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            op = self.SAFE_UNARY_OPERATORS.get(type(node.op))
            if op is None:
                raise ValueError(f"Unary operator not allowed: {type(node.op).__name__}")
            return op(operand)

        elif isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("Only simple function calls allowed")

            func_name = node.func.id
            if func_name not in self.SAFE_FUNCTIONS:
                raise ValueError(f"Function not allowed: {func_name}")

            args = [self._eval_node(arg) for arg in node.args]
            return self.SAFE_FUNCTIONS[func_name](*args)

        elif isinstance(node, ast.Name):
            if node.id not in self.SAFE_CONSTANTS:
                raise ValueError(f"Variable/constant not allowed: {node.id}")
            return self.SAFE_CONSTANTS[node.id]

        else:
            raise ValueError(f"Expression type not allowed: {type(node).__name__}")

    def _safe_eval(self, expression: str) -> Union[int, float]:
        """Safely evaluate mathematical expression using AST parsing."""
        try:
            # Parse expression into AST
            tree = ast.parse(expression, mode="eval")
            # Evaluate the AST
            return self._eval_node(tree.body)
        except SyntaxError as e:
            raise ValueError(f"Invalid syntax: {e}")
        except Exception as e:
            raise ValueError(str(e))
    def execute(self, expression: str) -> ToolResult:
        """Evaluate a mathematical expression safely.

        Args:
            expression: Math expression to evaluate (e.g., "2 + 2", "sqrt(16)", "sin(pi/2)")

        Returns:
            ToolResult with calculation result
        """
        try:
            # Clean expression
            expr = expression.strip()

            if not expr:
                return ToolResult(success=False, output="", error="Empty expression")

            # Replace ^ with ** for exponentiation (common notation)
            expr = expr.replace("^", "**")

            # Evaluate using AST (no eval()!)
            result = self._safe_eval(expr)

            # Format result
            if isinstance(result, float):
                if result.is_integer():
                    output = str(int(result))
                else:
                    output = f"{result:.10f}".rstrip("0").rstrip(".")
            else:
                output = str(result)

            return ToolResult(
                success=True,
                output=f"{expression} = {output}",
                metadata={
                    "expression": expression,
                    "result": result,
                    "result_type": type(result).__name__,
                },
            )

        except ZeroDivisionError:
            return ToolResult(success=False, output="", error="Division by zero")
        except ValueError as e:
            return ToolResult(success=False, output="", error=str(e))
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Calculation failed: {e}")


__all__ = ["CalculatorTool"]
