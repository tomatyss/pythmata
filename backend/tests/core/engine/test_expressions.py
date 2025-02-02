"""Tests for the expression evaluation system."""

import pytest
from datetime import datetime

from pythmata.core.engine.expressions import (
    ExpressionEvaluator,
    ExpressionError,
    ExpressionSyntaxError,
    ExpressionEvalError,
)


@pytest.fixture
def evaluator():
    """Create expression evaluator for tests."""
    return ExpressionEvaluator()


class TestExpressionEvaluator:
    def test_basic_number_comparison(self, evaluator):
        """Test basic numeric comparisons."""
        context = {"amount": 1500}

        assert evaluator.evaluate("${amount > 1000}", context) is True
        assert evaluator.evaluate("${amount < 2000}", context) is True
        assert evaluator.evaluate("${amount >= 1500}", context) is True
        assert evaluator.evaluate("${amount <= 1500}", context) is True
        assert evaluator.evaluate("${amount == 1500}", context) is True
        assert evaluator.evaluate("${amount != 2000}", context) is True

    def test_string_comparison(self, evaluator):
        """Test string comparisons."""
        context = {"status": "approved"}

        assert evaluator.evaluate("${status == 'approved'}", context) is True
        assert evaluator.evaluate("${status != 'pending'}", context) is True
        assert evaluator.evaluate('${status == "approved"}', context) is True

    def test_boolean_conditions(self, evaluator):
        """Test boolean conditions."""
        context = {"active": True, "enabled": False}

        assert evaluator.evaluate("${active == true}", context) is True
        assert evaluator.evaluate("${enabled == false}", context) is True
        assert evaluator.evaluate("${active && !enabled}", context) is True
        assert evaluator.evaluate("${active || enabled}", context) is True

    def test_date_comparison(self, evaluator):
        """Test date comparisons."""
        context = {
            "created_at": datetime.fromisoformat("2024-02-01T10:00:00"),
            "due_date": datetime.fromisoformat("2024-03-01"),
        }

        assert evaluator.evaluate("${created_at < '2024-02-02'}", context) is True
        assert evaluator.evaluate("${due_date > '2024-02-01'}", context) is True
        assert evaluator.evaluate("${created_at != due_date}", context) is True

    def test_nested_object_access(self, evaluator):
        """Test nested object property access."""
        context = {
            "user": {"role": "admin", "settings": {"theme": "dark"}},
            "order": {"items": [{"price": 100}]},
        }

        assert evaluator.evaluate("${user.role == 'admin'}", context) is True
        assert evaluator.evaluate("${user.settings.theme == 'dark'}", context) is True

    def test_null_handling(self, evaluator):
        """Test null value handling."""
        context = {"user": None, "status": "active"}

        assert evaluator.evaluate("${user == null}", context) is True
        assert evaluator.evaluate("${status != null}", context) is True
        # Null-safe property access
        assert evaluator.evaluate("${user.name == null}", context) is True

    def test_type_coercion(self, evaluator):
        """Test type coercion in comparisons."""
        context = {"amount": 1000, "limit": "500"}

        assert evaluator.evaluate("${amount > limit}", context) is True
        assert evaluator.evaluate("${limit < 1000}", context) is True

    def test_complex_expressions(self, evaluator):
        """Test complex expressions with multiple operators."""
        context = {
            "amount": 1500,
            "status": "approved",
            "priority": "high",
            "user": {"role": "admin"},
        }

        assert (
            evaluator.evaluate(
                "${amount > 1000 && (status == 'approved' || priority == 'high')}", context
            )
            is True
        )
        assert (
            evaluator.evaluate(
                "${user.role == 'admin' && amount >= 1000 && status == 'approved'}",
                context,
            )
            is True
        )

    def test_error_handling(self, evaluator):
        """Test error handling for invalid expressions."""
        context = {"amount": 1000}

        # Invalid syntax
        with pytest.raises(ExpressionSyntaxError):
            evaluator.evaluate("${invalid syntax", context)

        # Missing closing brace
        with pytest.raises(ExpressionSyntaxError):
            evaluator.evaluate("${amount > 1000", context)

        # Undefined variable
        with pytest.raises(ExpressionEvalError):
            evaluator.evaluate("${undefined > 1000}", context)

        # Invalid operator
        with pytest.raises(ExpressionSyntaxError):
            evaluator.evaluate("${amount >>> 1000}", context)

        # Invalid property access
        with pytest.raises(ExpressionEvalError):
            evaluator.evaluate("${amount.invalid}", context)
