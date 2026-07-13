import ast
from typing import Set


class DependencyExtractor(ast.NodeVisitor):
    def __init__(self):
        self.dependencies: Set[str] = set()

    def visit_Name(self, node: ast.Name):
        self.dependencies.add(node.id)

    def visit_Call(self, node: ast.Call):
        for arg in node.args:
            self.visit(arg)
        for keyword in node.keywords:
            self.visit(keyword.value)


def extract_dependencies(expression: str) -> Set[str]:
    try:
        tree = ast.parse(expression, mode="eval")
        extractor = DependencyExtractor()
        extractor.visit(tree.body)
        return extractor.dependencies
    except SyntaxError:
        return set()
