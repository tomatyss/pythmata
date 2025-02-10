"""
Expression evaluation system for BPMN gateway conditions.

This module provides safe and robust expression evaluation for gateway
conditions, supporting various data types and operations.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ExpressionError(Exception):
    """Base class for expression-related errors."""

    pass


class ExpressionSyntaxError(ExpressionError):
    """Raised when expression syntax is invalid."""

    pass


class ExpressionEvalError(ExpressionError):
    """Raised when expression evaluation fails."""

    pass


class TokenType(Enum):
    """Types of tokens in expressions."""

    NUMBER = "NUMBER"
    STRING = "STRING"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    NULL = "NULL"
    IDENTIFIER = "IDENTIFIER"
    OPERATOR = "OPERATOR"
    DOT = "DOT"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    LBRACKET = "LBRACKET"
    RBRACKET = "RBRACKET"
    EOF = "EOF"


class Token:
    """Represents a token in the expression."""

    def __init__(self, type: TokenType, value: Any):
        self.type = type
        self.value = value

    def __repr__(self):
        return f"Token({self.type}, {self.value})"


class ExpressionParser:
    """Parses expression strings into tokens."""

    OPERATORS = {
        "==": "eq",
        "!=": "ne",
        ">": "gt",
        ">=": "ge",
        "<": "lt",
        "<=": "le",
        "&&": "and",
        "||": "or",
        "!": "not",
    }

    def __init__(self):
        self.expression: str = ""
        self.position: int = 0
        self.tokens: List[Token] = []

    def tokenize(self, expression: str) -> List[Token]:
        """Convert expression string into list of tokens."""
        if not expression.startswith("${") or not expression.endswith("}"):
            raise ExpressionSyntaxError("Expression must be wrapped in ${}")

        # Remove ${ and }
        self.expression = expression[2:-1].strip()
        self.position = 0
        self.tokens = []

        while self.position < len(self.expression):
            char = self.expression[self.position]

            if char.isspace():
                self.position += 1
                continue

            if char.isdigit():
                self.tokens.append(self._parse_number())
            elif char == '"' or char == "'":
                self.tokens.append(self._parse_string())
            elif char.isalpha() or char == "_":
                self.tokens.append(self._parse_identifier())
            elif char == ".":
                self.tokens.append(Token(TokenType.DOT, "."))
                self.position += 1
            elif char == "(":
                self.tokens.append(Token(TokenType.LPAREN, "("))
                self.position += 1
            elif char == ")":
                self.tokens.append(Token(TokenType.RPAREN, ")"))
                self.position += 1
            elif char == "[":
                self.tokens.append(Token(TokenType.LBRACKET, "["))
                self.position += 1
            elif char == "]":
                self.tokens.append(Token(TokenType.RBRACKET, "]"))
                self.position += 1
            else:
                # Try to match operators
                operator = self._match_operator()
                if operator:
                    self.tokens.append(Token(TokenType.OPERATOR, operator))
                else:
                    raise ExpressionSyntaxError(
                        f"Invalid character at position {self.position}: {char}"
                    )

        self.tokens.append(Token(TokenType.EOF, None))
        return self.tokens

    def _parse_number(self) -> Token:
        """Parse numeric literal."""
        number = ""
        has_decimal = False

        while self.position < len(self.expression):
            char = self.expression[self.position]
            if char.isdigit():
                number += char
            elif char == "." and not has_decimal:
                number += char
                has_decimal = True
            else:
                break
            self.position += 1

        return Token(TokenType.NUMBER, float(number) if has_decimal else int(number))

    def _parse_string(self) -> Token:
        """Parse string literal."""
        quote = self.expression[self.position]
        string = ""
        self.position += 1  # Skip opening quote

        while self.position < len(self.expression):
            char = self.expression[self.position]
            if char == quote:
                self.position += 1
                # Check if this might be a date string
                try:
                    date = datetime.fromisoformat(string)
                    return Token(TokenType.DATE, date)
                except ValueError:
                    return Token(TokenType.STRING, string)
            string += char
            self.position += 1

        raise ExpressionSyntaxError("Unterminated string literal")

    def _parse_identifier(self) -> Token:
        """Parse identifier or keyword."""
        identifier = ""

        while self.position < len(self.expression):
            char = self.expression[self.position]
            if char.isalnum() or char == "_":
                identifier += char
                self.position += 1
            else:
                break

        if identifier == "true":
            return Token(TokenType.BOOLEAN, True)
        elif identifier == "false":
            return Token(TokenType.BOOLEAN, False)
        elif identifier == "null":
            return Token(TokenType.NULL, None)
        else:
            return Token(TokenType.IDENTIFIER, identifier)

    def _match_operator(self) -> Optional[str]:
        """Try to match operator at current position."""
        for op in sorted(self.OPERATORS.keys(), key=len, reverse=True):
            if self.expression.startswith(op, self.position):
                self.position += len(op)
                return self.OPERATORS[op]
        return None


class Expression(ABC):
    """Base class for expression nodes."""

    @abstractmethod
    def evaluate(self, context: Dict[str, Any]) -> Any:
        """Evaluate expression with given context."""
        pass


class LiteralExpression(Expression):
    """Expression node for literal values."""

    def __init__(self, value: Any):
        self.value = value

    def evaluate(self, context: Dict[str, Any]) -> Any:
        return self.value


class IdentifierExpression(Expression):
    """Expression node for variable references."""

    def __init__(self, name: str):
        self.name = name

    def evaluate(self, context: Dict[str, Any]) -> Any:
        if self.name not in context:
            raise ExpressionEvalError(f"Undefined variable: {self.name}")
        return context[self.name]


class PropertyExpression(Expression):
    """Expression node for object property access."""

    def __init__(self, obj: Expression, prop: str):
        self.obj = obj
        self.prop = prop

    def evaluate(self, context: Dict[str, Any]) -> Any:
        obj = self.obj.evaluate(context)
        if obj is None:
            return None  # Null-safe property access
        if not hasattr(obj, self.prop) and not isinstance(obj, dict):
            raise ExpressionEvalError(f"Cannot access property {self.prop} of {obj}")
        return obj.get(self.prop) if isinstance(obj, dict) else getattr(obj, self.prop)


class ArrayAccessExpression(Expression):
    """Expression node for array indexing."""

    def __init__(self, array: Expression, index: Expression):
        self.array = array
        self.index = index

    def evaluate(self, context: Dict[str, Any]) -> Any:
        array = self.array.evaluate(context)
        if array is None:
            return None  # Null-safe array access
        
        index = self.index.evaluate(context)
        if not isinstance(index, (int, float)):
            raise ExpressionEvalError(f"Array index must be a number, got {type(index)}")
        
        try:
            return array[int(index)]
        except (IndexError, TypeError):
            raise ExpressionEvalError(f"Invalid array access: {array}[{index}]")


class BinaryExpression(Expression):
    """Expression node for binary operations."""

    def __init__(self, operator: str, left: Expression, right: Expression):
        self.operator = operator
        self.left = left
        self.right = right

    def evaluate(self, context: Dict[str, Any]) -> Any:
        left_val = self.left.evaluate(context)
        right_val = self.right.evaluate(context)

        # Handle null values
        if left_val is None or right_val is None:
            if self.operator == "eq":
                return left_val is right_val
            if self.operator == "ne":
                return left_val is not right_val
            return False

        # Type coercion for comparisons
        if isinstance(left_val, (int, float)) and isinstance(right_val, str):
            try:
                right_val = float(right_val)
            except ValueError:
                pass
        elif isinstance(right_val, (int, float)) and isinstance(left_val, str):
            try:
                left_val = float(left_val)
            except ValueError:
                pass

        # Operator implementations
        if self.operator == "eq":
            return left_val == right_val
        elif self.operator == "ne":
            return left_val != right_val
        elif self.operator == "gt":
            return left_val > right_val
        elif self.operator == "ge":
            return left_val >= right_val
        elif self.operator == "lt":
            return left_val < right_val
        elif self.operator == "le":
            return left_val <= right_val
        elif self.operator == "and":
            return bool(left_val and right_val)
        elif self.operator == "or":
            return bool(left_val or right_val)
        else:
            raise ExpressionEvalError(f"Unknown operator: {self.operator}")


class UnaryExpression(Expression):
    """Expression node for unary operations."""

    def __init__(self, operator: str, operand: Expression):
        self.operator = operator
        self.operand = operand

    def evaluate(self, context: Dict[str, Any]) -> Any:
        val = self.operand.evaluate(context)
        if self.operator == "not":
            return not val
        raise ExpressionEvalError(f"Unknown unary operator: {self.operator}")


class ExpressionEvaluator:
    """Main class for evaluating gateway conditions."""

    def __init__(self):
        self.parser = ExpressionParser()

    def evaluate(self, expression: str, context: Dict[str, Any]) -> bool:
        """
        Evaluate a gateway condition expression.

        Args:
            expression: Condition expression (e.g. ${amount > 1000})
            context: Variable context from token data

        Returns:
            Boolean result of evaluation

        Raises:
            ExpressionError: If expression is invalid or evaluation fails
        """
        try:
            tokens = self.parser.tokenize(expression)
            ast = self._parse(tokens)
            result = ast.evaluate(context)
            return bool(result)
        except ExpressionError:
            raise
        except Exception as e:
            raise ExpressionEvalError(f"Evaluation failed: {str(e)}")

    def _parse(self, tokens: List[Token]) -> Expression:
        """Parse tokens into expression tree."""

        # Simple recursive descent parser
        def parse_expression(pos: int) -> tuple[Expression, int]:
            expr, pos = parse_or(pos)
            if pos < len(tokens) and tokens[pos].type not in (
                TokenType.EOF,
                TokenType.RPAREN,
            ):
                raise ExpressionSyntaxError("Unexpected token")
            return expr, pos

        def parse_or(pos: int) -> tuple[Expression, int]:
            expr, pos = parse_and(pos)
            while (
                pos < len(tokens)
                and tokens[pos].type == TokenType.OPERATOR
                and tokens[pos].value == "or"
            ):
                op = tokens[pos].value
                pos += 1
                right, pos = parse_and(pos)
                expr = BinaryExpression(op, expr, right)
            return expr, pos

        def parse_and(pos: int) -> tuple[Expression, int]:
            expr, pos = parse_comparison(pos)
            while (
                pos < len(tokens)
                and tokens[pos].type == TokenType.OPERATOR
                and tokens[pos].value == "and"
            ):
                op = tokens[pos].value
                pos += 1
                right, pos = parse_comparison(pos)
                expr = BinaryExpression(op, expr, right)
            return expr, pos

        def parse_comparison(pos: int) -> tuple[Expression, int]:
            expr, pos = parse_primary(pos)
            while pos < len(tokens) and tokens[pos].type == TokenType.OPERATOR:
                op = tokens[pos].value
                if op not in ("eq", "ne", "gt", "ge", "lt", "le"):
                    break
                pos += 1
                right, pos = parse_primary(pos)
                expr = BinaryExpression(op, expr, right)
            return expr, pos

        def parse_primary(pos: int) -> tuple[Expression, int]:
            token = tokens[pos]
            pos += 1

            if token.type in (
                TokenType.NUMBER,
                TokenType.STRING,
                TokenType.BOOLEAN,
                TokenType.DATE,
                TokenType.NULL,
            ):
                return LiteralExpression(token.value), pos
            elif token.type == TokenType.IDENTIFIER:
                expr = IdentifierExpression(token.value)
                while pos < len(tokens) and (tokens[pos].type in (TokenType.DOT, TokenType.LBRACKET)):
                    if tokens[pos].type == TokenType.DOT:
                        pos += 1
                        if pos >= len(tokens) or tokens[pos].type != TokenType.IDENTIFIER:
                            raise ExpressionSyntaxError("Expected identifier after dot")
                        expr = PropertyExpression(expr, tokens[pos].value)
                        pos += 1
                    else:  # LBRACKET
                        pos += 1
                        index_expr, pos = parse_or(pos)  # Allow expressions in array indices
                        if pos >= len(tokens) or tokens[pos].type != TokenType.RBRACKET:
                            raise ExpressionSyntaxError("Expected closing bracket")
                        expr = ArrayAccessExpression(expr, index_expr)
                        pos += 1
                return expr, pos
            elif token.type == TokenType.OPERATOR and token.value == "not":
                operand, pos = parse_primary(pos)
                return UnaryExpression("not", operand), pos
            elif token.type == TokenType.LPAREN:
                expr, pos = parse_or(pos)  # Start from parse_or for nested expressions
                if pos >= len(tokens) or tokens[pos].type != TokenType.RPAREN:
                    raise ExpressionSyntaxError("Expected closing parenthesis")
                return expr, pos + 1
            else:
                raise ExpressionSyntaxError(f"Unexpected token: {token}")

        expr, _ = parse_expression(0)
        return expr
