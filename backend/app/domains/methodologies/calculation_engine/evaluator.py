import ast
import math
import operator
from typing import Dict, Union


class EvaluationError(Exception):
    pass


class DeterministicEvaluator(ast.NodeVisitor):
    """
    A strictly deterministic, sandboxed AST evaluator.
    No `eval()` or `exec()` is ever called.
    """

    ALLOWED_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    ALLOWED_FUNCTIONS = {
        "log": math.log,
        "log10": math.log10,
        "exp": math.exp,
        "sqrt": math.sqrt,
        "min": min,
        "max": max,
        "abs": abs,
        "round": round,
    }

    def __init__(self, parameters: Dict[str, Union[int, float]]):
        self.parameters = parameters
        self.audit_trail = []

    def evaluate(self, expression: str) -> float:
        try:
            tree = ast.parse(expression, mode="eval")
            return self.visit(tree.body)
        except SyntaxError as e:
            raise EvaluationError(f"Syntax error in expression: {expression}") from e

    def visit_Constant(self, node: ast.Constant) -> float:
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise EvaluationError(f"Unsupported constant type: {type(node.value)}")

    def visit_Name(self, node: ast.Name) -> float:
        var_name = node.id
        if var_name in self.parameters:
            val = self.parameters[var_name]
            self.audit_trail.append(
                {"action": "resolve_variable", "name": var_name, "value": val}
            )
            return float(val)
        raise EvaluationError(f"Unknown parameter: {var_name}")

    def visit_BinOp(self, node: ast.BinOp) -> float:
        left = self.visit(node.left)
        right = self.visit(node.right)
        op_type = type(node.op)
        if op_type in self.ALLOWED_OPERATORS:
            return self.ALLOWED_OPERATORS[op_type](left, right)
        raise EvaluationError(f"Unsupported binary operator: {op_type}")

    def visit_UnaryOp(self, node: ast.UnaryOp) -> float:
        operand = self.visit(node.operand)
        op_type = type(node.op)
        if op_type in self.ALLOWED_OPERATORS:
            return self.ALLOWED_OPERATORS[op_type](operand)
        raise EvaluationError(f"Unsupported unary operator: {op_type}")

    def visit_Call(self, node: ast.Call) -> float:
        if not isinstance(node.func, ast.Name):
            raise EvaluationError("Only basic mathematical functions are supported")
        func_name = node.func.id
        if func_name not in self.ALLOWED_FUNCTIONS:
            raise EvaluationError(f"Unsupported function: {func_name}")

        args = [self.visit(arg) for arg in node.args]
        result = self.ALLOWED_FUNCTIONS[func_name](*args)
        self.audit_trail.append(
            {
                "action": "call_function",
                "name": func_name,
                "args": args,
                "result": result,
            }
        )
        return float(result)

    def generic_visit(self, node: ast.AST):
        raise EvaluationError(f"Unsupported AST node: {type(node)}")
