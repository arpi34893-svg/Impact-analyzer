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
        current_dir = os.path.dirname(rel_path)

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                level = node.level or 0  # 0 = absolute, 1+ = relative ("." , "..", ...)
                targets = set()
                base_target = self._resolve_module_to_file(module, current_dir, level)
                if base_target:
                    targets.add(base_target)
                # "from pkg import mod": the imported name may itself be a submodule file
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    sub_name = f"{module}.{alias.name}" if module else alias.name
                    sub_target = self._resolve_module_to_file(sub_name, current_dir, level)
                    if sub_target:
                        targets.add(sub_target)
                for target_file in targets:
                    if target_file != rel_path:
                        self.graph.add_node(target_file, type="file")
                        self.graph.add_edge(rel_path, target_file, kind="import")

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    target_file = self._resolve_module_to_file(alias.name, current_dir, level=0)
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

    def _candidate_paths(self, module_path: str) -> list:
        """
        Given a module path relative to the repo root (no extension),
        returns the possible real file paths it could correspond to:
        either module_path.py, or module_path/__init__.py (package).
        """
        return [
            module_path + ".py",
            os.path.join(module_path, "__init__.py"),
        ]

    def _resolve_module_to_file(self, module_name: str, current_dir: str, level: int = 0):
        """
        Best-effort resolution of a module name to a .py file in the repo.
        Handles:
          - absolute imports: import pkg.mod  /  from pkg.mod import x
          - relative imports: from . import x  /  from .mod import x  /  from ..pkg import x
          - packages: resolves to pkg/__init__.py when pkg/mod.py doesn't exist
        """
        if level > 0:
            # Relative import: walk up `level` directories from the importing file's folder.
            base_dir = current_dir
            for _ in range(level - 1):
                base_dir = os.path.dirname(base_dir)
            module_rel = module_name.replace(".", os.sep) if module_name else ""
            base_path = os.path.join(base_dir, module_rel) if module_rel else base_dir
            for candidate in self._candidate_paths(base_path):
                if os.path.exists(os.path.join(self.repo_path, candidate)):
                    return os.path.normpath(candidate)
            return None

        if not module_name:
            return None
        base_path = module_name.replace(".", os.sep)
        # absolute imports: try repo root, then common source roots (src/ layout)
        for root in ("", "src", "lib"):
            for candidate in self._candidate_paths(os.path.join(root, base_path)):
                if os.path.exists(os.path.join(self.repo_path, candidate)):
                    return os.path.normpath(candidate)
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