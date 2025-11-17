"""Calculator tool for Freya."""

from __future__ import annotations

import math
import re

from .base import FreyaTool, ToolResult


class CalculatorTool(FreyaTool):
    """Evaluate mathematical expressions safely."""

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Calculate mathematical expressions (supports +, -, *, /, ^, sqrt, sin, cos, etc.)"

    # Safe mathematical functions allowed in eval
    SAFE_FUNCTIONS = {
        'abs': abs,
        'round': round,
        'min': min,
        'max': max,
        'sum': sum,
        'pow': pow,
        # Math functions
        'sqrt': math.sqrt,
        'sin': math.sin,
        'cos': math.cos,
        'tan': math.tan,
        'log': math.log,
        'log10': math.log10,
        'exp': math.exp,
        'floor': math.floor,
        'ceil': math.ceil,
        # Constants
        'pi': math.pi,
        'e': math.e,
    }

    def execute(self, expression: str) -> ToolResult:  # type: ignore[override]
        """Evaluate a mathematical expression.

        Args:
            expression: Math expression to evaluate (e.g., "2 + 2", "sqrt(16)", "sin(pi/2)")

        Returns:
            ToolResult with calculation result
        """
        try:
            # Clean and validate expression
            expr = expression.strip()

            if not expr:
                return ToolResult(success=False, output="", error="Empty expression")

            # Replace ^ with ** for exponentiation
            expr = expr.replace('^', '**')

            # Security check - only allow safe characters
            if not re.match(r'^[0-9+\-*/().,\s\w]+$', expr):
                return ToolResult(
                    success=False,
                    output="",
                    error="Expression contains invalid characters"
                )

            # Evaluate with restricted globals
            result = eval(
                expr,
                {"__builtins__": {}},
                self.SAFE_FUNCTIONS
            )

            # Format result
            if isinstance(result, float):
                # Round to reasonable precision
                if result.is_integer():
                    output = str(int(result))
                else:
                    output = f"{result:.10f}".rstrip('0').rstrip('.')
            else:
                output = str(result)

            return ToolResult(
                success=True,
                output=f"{expression} = {output}",
                metadata={
                    "expression": expression,
                    "result": result,
                    "result_type": type(result).__name__
                }
            )

        except ZeroDivisionError:
            return ToolResult(success=False, output="", error="Division by zero")
        except SyntaxError:
            return ToolResult(success=False, output="", error=f"Invalid syntax: {expression}")
        except NameError as e:
            return ToolResult(success=False, output="", error=f"Unknown function or constant: {e}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Calculation failed: {e}")


__all__ = ["CalculatorTool"]
