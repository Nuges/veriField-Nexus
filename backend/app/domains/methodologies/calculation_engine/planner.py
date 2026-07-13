from typing import Dict, List, Set

from .dependencies import extract_dependencies


class CycleDetectedError(Exception):
    pass


class ExecutionPlanner:
    def __init__(self):
        pass

    def plan(self, rules: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Sorts a list of calculation rules based on their dependencies.
        Each rule should be a dict like:
        {"output_parameter": "ER", "formula": "BE - PE - LE"}
        """
        graph: Dict[str, Set[str]] = {}
        rule_map: Dict[str, Dict[str, str]] = {}

        for rule in rules:
            output = rule.get("output_parameter")
            formula = rule.get("formula")
            if not output or not formula:
                continue
            deps = extract_dependencies(formula)
            graph[output] = deps
            rule_map[output] = rule

        # Topological Sort (Kahn's Algorithm adapted)
        sorted_rules = []
        visited = set()
        visiting = set()

        def visit(node: str):
            if node in visiting:
                raise CycleDetectedError(
                    f"Circular dependency detected involving parameter: {node}"
                )
            if node in visited:
                return
            visiting.add(node)

            # If the node has dependencies, visit them first if they are in the graph (i.e. other rules)
            if node in graph:
                for dep in graph[node]:
                    if dep in graph:
                        visit(dep)

            visiting.remove(node)
            visited.add(node)
            if node in rule_map:
                sorted_rules.append(rule_map[node])

        for output in graph.keys():
            if output not in visited:
                visit(output)

        return sorted_rules
