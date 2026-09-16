import ast
import os
import networkx as nx


class RepoParser:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.graph = nx.DiGraph()

    def build_dependency_graph(self) -> nx.DiGraph:
        """Parses python files and tracks dependency calls across the repo."""
        for root, _, files in os.walk(self.repo_path):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, self.repo_path)
                    self._parse_file(file_path, rel_path)
        return self.graph

    def _parse_file(self, full_path: str, rel_path: str):
        with open(full_path, "r", encoding="utf-8") as f:
            try:
                tree = ast.parse(f.read(), filename=rel_path)
            except SyntaxError as e:
                print(f"[WARN] Skipping {rel_path}: syntax error ({e})")
                return

        self.graph.add_node(rel_path, type="file")

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                target_file = self._resolve_module_to_file(module)
                if target_file:
                    self.graph.add_node(target_file, type="file")
                    self.graph.add_edge(rel_path, target_file, kind="import")

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    target_file = self._resolve_module_to_file(alias.name)
                    if target_file:
                        self.graph.add_node(target_file, type="file")
                        self.graph.add_edge(rel_path, target_file, kind="import")

            elif isinstance(node, ast.FunctionDef):
                func_id = f"{rel_path}::{node.name}"
                self.graph.add_node(func_id, type="function")
                self.graph.add_edge(rel_path, func_id, kind="defines")

            elif isinstance(node, ast.ClassDef):
                class_id = f"{rel_path}::{node.name}"
                self.graph.add_node(class_id, type="class")
                self.graph.add_edge(rel_path, class_id, kind="defines")

    def _resolve_module_to_file(self, module_name: str):
        """Best-effort resolution of a local module name to a .py file in the repo."""
        if not module_name:
            return None
        candidate = module_name.replace(".", os.sep) + ".py"
        full_candidate = os.path.join(self.repo_path, candidate)
        if os.path.exists(full_candidate):
            return candidate
        return None

    def get_impacted_files(self, changed_file: str) -> list:
        """Returns files that depend (directly or transitively) on changed_file."""
        changed_file = changed_file.replace("/", os.sep)
        if changed_file not in self.graph:
            return []
        impacted = nx.ancestors(self.graph, changed_file)
        impacted_files = [
            n for n in impacted if self.graph.nodes[n].get("type") == "file"
        ]
        return sorted(impacted_files)