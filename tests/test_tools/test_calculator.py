"""
Unit tests for Calculator tool.

Tests AST-based expression evaluation with security validation.
"""
import pytest

from freya.tools.calculator import CalculatorTool


class TestCalculatorBasicOperations:
    """Test basic arithmetic operations."""

    @pytest.fixture
    def calculator(self):
        """Create calculator tool instance."""
        return CalculatorTool()

    @pytest.mark.parametrize("expression,expected", [
        ("2 + 2", 4),
        ("10 - 3", 7),
        ("5 * 6", 30),
        ("100 / 4", 25),
        ("2 ** 8", 256),
        ("17 % 5", 2),
        ("17 // 5", 3),
    ])
    def test_basic_arithmetic(self, calculator, expression, expected):
        """Test basic arithmetic operations."""
        result = calculator.execute(expression=expression)
        assert result.success is True
        assert result.metadata["result"] == expected

    def test_order_of_operations(self, calculator):
        """Test that order of operations is respected."""
        result = calculator.execute(expression="2 + 3 * 4")
        assert result.success is True
        assert result.metadata["result"] == 14  # Not 20

    def test_parentheses(self, calculator):
        """Test parentheses for grouping."""
        result = calculator.execute(expression="(2 + 3) * 4")
        assert result.success is True
        assert result.metadata["result"] == 20

    def test_nested_operations(self, calculator):
        """Test nested expressions."""
        result = calculator.execute(expression="((10 + 5) * 2) - 6")
        assert result.success is True
        assert result.metadata["result"] == 24


class TestCalculatorMathFunctions:
    """Test mathematical functions."""

    @pytest.fixture
    def calculator(self):
        """Create calculator tool instance."""
        return CalculatorTool()

    @pytest.mark.parametrize("expression,expected", [
        ("abs(-5)", 5),
        ("abs(5)", 5),
        ("round(3.7)", 4),
        ("round(3.2)", 3),
        ("min(5, 3, 8, 1)", 1),
        ("max(5, 3, 8, 1)", 8),
        ("pow(2, 10)", 1024),
    ])
    def test_basic_functions(self, calculator, expression, expected):
        """Test basic math functions."""
        result = calculator.execute(expression=expression)
        assert result.success is True
        assert result.metadata["result"] == expected

    @pytest.mark.parametrize("expression,expected", [
        ("sqrt(16)", 4.0),
        ("sqrt(25)", 5.0),
        ("sqrt(2)", 1.4142135623730951),
    ])
    def test_sqrt(self, calculator, expression, expected):
        """Test square root function."""
        result = calculator.execute(expression=expression)
        assert result.success is True
        assert abs(result.metadata["result"] - expected) < 0.0001


class TestCalculatorSecurity:
    """Test security features and blocked operations."""

    @pytest.fixture
    def calculator(self):
        """Create calculator tool instance."""
        return CalculatorTool()

    def test_blocks_import_statement(self, calculator):
        """Import statements should be blocked."""
        result = calculator.execute(expression="__import__('os')")
        assert result.success is False
        assert "not allowed" in result.error.lower()

    def test_blocks_exec(self, calculator):
        """Exec function should be blocked."""
        result = calculator.execute(expression="exec('print(1)')")
        assert result.success is False
        assert "not allowed" in result.error.lower()

    def test_blocks_eval(self, calculator):
        """Eval function should be blocked."""
        result = calculator.execute(expression="eval('2+2')")
        assert result.success is False
        assert "not allowed" in result.error.lower()

    def test_blocks_code_injection(self, calculator):
        """Code injection attempts should fail."""
        result = calculator.execute(expression="__import__('os').system('ls')")
        assert result.success is False

    def test_blocks_attribute_access(self, calculator):
        """Attribute access on objects should be blocked."""
        result = calculator.execute(expression="(1).__class__")
        assert result.success is False
        assert "not allowed" in result.error.lower()

    def test_blocks_dunder_methods(self, calculator):
        """Dunder method access should be blocked."""
        result = calculator.execute(expression="''.__doc__")
        assert result.success is False


class TestCalculatorEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def calculator(self):
        """Create calculator tool instance."""
        return CalculatorTool()

    def test_division_by_zero(self, calculator):
        """Division by zero should return error."""
        result = calculator.execute(expression="10 / 0")
        assert result.success is False
        assert "division" in result.error.lower()

    def test_invalid_syntax(self, calculator):
        """Invalid syntax should return error."""
        result = calculator.execute(expression="2 +")
        assert result.success is False

    def test_empty_expression(self, calculator):
        """Empty expression should return error."""
        result = calculator.execute(expression="")
        assert result.success is False

    def test_very_large_numbers(self, calculator):
        """Very large numbers should work."""
        result = calculator.execute(expression="10 ** 100")
        assert result.success is True
        assert result.metadata["result"] == 10 ** 100

    def test_floating_point_precision(self, calculator):
        """Floating point operations should work."""
        result = calculator.execute(expression="0.1 + 0.2")
        assert result.success is True
        assert abs(result.metadata["result"] - 0.3) < 0.0001

    def test_negative_numbers(self, calculator):
        """Negative numbers should work."""
        result = calculator.execute(expression="-5 * 3")
        assert result.success is True
        assert result.metadata["result"] == -15

    def test_multiple_operations(self, calculator):
        """Complex multi-operation expressions should work."""
        result = calculator.execute(expression="(sqrt(16) + pow(2, 3)) * abs(-2)")
        assert result.success is True
        assert result.metadata["result"] == 24.0


class TestCalculatorToolResult:
    """Test ToolResult structure."""

    @pytest.fixture
    def calculator(self):
        """Create calculator tool instance."""
        return CalculatorTool()

    def test_success_result_structure(self, calculator):
        """Successful result should have correct structure."""
        result = calculator.execute(expression="2 + 2")
        assert hasattr(result, "success")
        assert hasattr(result, "output")
        assert hasattr(result, "error")
        assert result.success is True
        assert result.metadata["result"] == 4
        assert result.error is None or result.error == ""

    def test_error_result_structure(self, calculator):
        """Error result should have correct structure."""
        result = calculator.execute(expression="invalid")
        assert result.success is False
        assert result.output == ""
        assert isinstance(result.error, str)
        assert len(result.error) > 0
