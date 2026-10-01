import os
import difflib
import posixpath

import networkx as nx

from parser_engine import RepoParser

FEATURE_COLUMNS = [
    "graph_distance",
    "a_imports_b",
    "b_imports_a",
    "shared_neighbors",
    "dir_distance",
    "name_similarity",
    "same_package",
    "is_test_a",
    "is_test_b",
    "in_degree_a",
    "in_degree_b",
]


def is_test_path(path: str) -> bool:
    parts = path.lower().split("/")
    base = parts[-1]
    return (
        any(p in ("test", "tests") for p in parts[:-1])
        or base.startswith("test_")
        or base.endswith("_test.py")
    )


def _stem(path: str) -> str:
    name = posixpath.splitext(posixpath.basename(path))[0].lower()
    if name.startswith("test_"):
        name = name[5:]
    if name.endswith("_test"):
        name = name[:-5]
    return name


def dir_distance(a: str, b: str) -> int:
    pa = [p for p in posixpath.dirname(a).split("/") if p]
    pb = [p for p in posixpath.dirname(b).split("/") if p]
    common = 0
    for x, y in zip(pa, pb):
        if x != y:
            break
        common += 1
    return (len(pa) - common) + (len(pb) - common)


class RepoContext:
    """
    Parses a repo once and answers structural questions about file pairs.
    All paths are normalised to forward slashes, so GitHub paths
    ('pkg/mod.py') match graph nodes on every OS (fixes the Windows '\\' mismatch).
    """

    def __init__(self, repo_path: str):
        raw_graph = RepoParser(repo_path).build_dependency_graph()
        mapping = {n: n.replace(os.sep, "/") for n in raw_graph.nodes}
        graph = nx.relabel_nodes(raw_graph, mapping)

        self.files = sorted(n for n, d in graph.nodes(data=True) if d.get("type") == "file")
        self.file_set = set(self.files)
        self.directed = graph.subgraph(self.files).copy()
        self.undirected = self.directed.to_undirected()
        self._dist_cache = {}

    def distances_from(self, a: str) -> dict:
        if a not in self._dist_cache:
            self._dist_cache[a] = nx.single_source_shortest_path_length(
                self.undirected, a, cutoff=10
            )
        return self._dist_cache[a]

    def pair_features(self, a: str, b: str) -> dict:
        na = set(self.undirected[a]) if a in self.undirected else set()
        nb = set(self.undirected[b]) if b in self.undirected else set()
        return {
            "graph_distance": self.distances_from(a).get(b, -1),
            "a_imports_b": int(self.directed.has_edge(a, b)),
            "b_imports_a": int(self.directed.has_edge(b, a)),
            "shared_neighbors": len(na & nb),
            "dir_distance": dir_distance(a, b),
            "name_similarity": round(difflib.SequenceMatcher(None, _stem(a), _stem(b)).ratio(), 4),
            "same_package": int(posixpath.dirname(a) == posixpath.dirname(b)),
            "is_test_a": int(is_test_path(a)),
            "is_test_b": int(is_test_path(b)),
            "in_degree_a": self.directed.in_degree(a),
            "in_degree_b": self.directed.in_degree(b),
        }