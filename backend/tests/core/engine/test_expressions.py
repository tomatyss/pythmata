"""Tests for the expression evaluation system."""

from datetime import datetime
from typing import Any, Dict

import pytest

from pythmata.core.engine.expressions import (
    ExpressionEvalError,
    ExpressionSyntaxError,
)


def create_test_context(**kwargs) -> Dict[str, Any]:
    """Create a test context with common test data."""
    base_context = {
        "amount": 1500,
        "status": "approved",
        "active": True,
        "user": {
            "role": "admin",
            "settings": {"theme": "dark"}
        },
        "created_at": datetime.fromisoformat("2024-02-01T10:00:00"),
        "due_date": datetime.fromisoformat("2024-03-01"),
        "order": {
            "items": [{"price": 100}]
        }
    }
    return {**base_context, **kwargs}


class TestExpressionEvaluator:
    """Tests for expression evaluation functionality."""

    def test_basic_number_comparison(self, expression_evaluator):
        """Test basic numeric comparisons."""
        context = create_test_context()

        assert expression_evaluator.evaluate("${amount > 1000}", context) is True
        assert expression_evaluator.evaluate("${amount < 2000}", context) is True
        assert expression_evaluator.evaluate("${amount >= 1500}", context) is True
        assert expression_evaluator.evaluate("${amount <= 1500}", context) is True
        assert expression_evaluator.evaluate("${amount == 1500}", context) is True
        assert expression_evaluator.evaluate("${amount != 2000}", context) is True

    def test_string_comparison(self, expression_evaluator):
        """Test string comparisons."""
        context = create_test_context()

        assert expression_evaluator.evaluate("${status == 'approved'}", context) is True
        assert expression_evaluator.evaluate("${status != 'pending'}", context) is True
        assert expression_evaluator.evaluate('${status == "approved"}', context) is True

    def test_boolean_conditions(self, expression_evaluator):
        """Test boolean conditions."""
        context = create_test_context(enabled=False)

        assert expression_evaluator.evaluate("${active == true}", context) is True
        assert expression_evaluator.evaluate("${enabled == false}", context) is True
        assert expression_evaluator.evaluate("${active && !enabled}", context) is True
        assert expression_evaluator.evaluate("${active || enabled}", context) is True

    def test_date_comparison(self, expression_evaluator):
        """Test date comparisons."""
        context = create_test_context()

        assert expression_evaluator.evaluate("${created_at < '2024-02-02'}", context) is True
        assert expression_evaluator.evaluate("${due_date > '2024-02-01'}", context) is True
        assert expression_evaluator.evaluate("${created_at != due_date}", context) is True

    def test_nested_object_access(self, expression_evaluator):
        """Test nested object property access."""
        context = create_test_context()

        assert expression_evaluator.evaluate("${user.role == 'admin'}", context) is True
        assert expression_evaluator.evaluate("${user.settings.theme == 'dark'}", context) is True
        assert expression_evaluator.evaluate("${order.items[0].price == 100}", context) is True

    def test_null_handling(self, expression_evaluator):
        """Test null value handling."""
        context = create_test_context(user=None)

        assert expression_evaluator.evaluate("${user == null}", context) is True
        assert expression_evaluator.evaluate("${status != null}", context) is True
        # Null-safe property access
        assert expression_evaluator.evaluate("${user.name == null}", context) is True

    def test_type_coercion(self, expression_evaluator):
        """Test type coercion in comparisons."""
        context = create_test_context(limit="500")

        assert expression_evaluator.evaluate("${amount > limit}", context) is True
        assert expression_evaluator.evaluate("${limit < 1000}", context) is True

    def test_complex_expressions(self, expression_evaluator):
        """Test complex expressions with multiple operators."""
        context = create_test_context(priority="high")

        assert expression_evaluator.evaluate(
            "${amount > 1000 && (status == 'approved' || priority == 'high')}",
            context
        ) is True
        assert expression_evaluator.evaluate(
            "${user.role == 'admin' && amount >= 1000 && status == 'approved'}",
            context
        ) is True

    def test_error_handling(self, expression_evaluator):
        """Test error handling for invalid expressions."""
        context = create_test_context()

        # Invalid syntax
        with pytest.raises(ExpressionSyntaxError):
            expression_evaluator.evaluate("${invalid syntax", context)

        # Missing closing brace
        with pytest.raises(ExpressionSyntaxError):
            expression_evaluator.evaluate("${amount > 1000", context)

        # Undefined variable
        with pytest.raises(ExpressionEvalError):
            expression_evaluator.evaluate("${undefined > 1000}", context)

        # Invalid operator
        with pytest.raises(ExpressionSyntaxError):
            expression_evaluator.evaluate("${amount >>> 1000}", context)

        # Invalid property access
        with pytest.raises(ExpressionEvalError):
            expression_evaluator.evaluate("${amount.invalid}", context)
