"""Calculator tool for mathematical operations."""

from __future__ import annotations

import math
from typing import Any

from freya.infrastructure.tools.base_tool import BaseTool


class CalculatorTool(BaseTool):
    """Tool for performing mathematical calculations."""

    def __init__(self) -> None:
        """Initialize tool."""
        super().__init__(
            name="calculator",
            description="Perform mathematical calculations (basic arithmetic, trigonometry, etc.)",
        )

    def get_parameters_schema(self) -> dict[str, Any]:
        """Get parameter schema."""
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate (e.g., '2 + 2', 'sqrt(16)', 'sin(pi/2)')",
                },
            },
            "required": ["expression"],
        }

    async def _execute_internal(self, **parameters: Any) -> str:
        """Execute tool."""
        expression = parameters["expression"]

        try:
            # Safe evaluation with math functions
            allowed_names = {
                # Math functions
                "abs": abs,
                "round": round,
                "min": min,
                "max": max,
                "sum": sum,
                "pow": pow,
                # Math module
                "sqrt": math.sqrt,
                "sin": math.sin,
                "cos": math.cos,
                "tan": math.tan,
                "asin": math.asin,
                "acos": math.acos,
                "atan": math.atan,
                "log": math.log,
                "log10": math.log10,
                "exp": math.exp,
                "floor": math.floor,
                "ceil": math.ceil,
                # Constants
                "pi": math.pi,
                "e": math.e,
            }

            # Evaluate expression
            result = eval(expression, {"__builtins__": {}}, allowed_names)

            return f"Result: {result}"

        except ZeroDivisionError:
            return "Error: Division by zero"
        except Exception as e:
            return f"Error: Invalid expression - {str(e)}"
