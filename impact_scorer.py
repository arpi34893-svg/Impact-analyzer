import networkx as nx


def score_impacted_files(graph, changed_file: str, impacted_files: list) -> dict:
    """
    Assigns transparent heuristic scores based on graph distance from changed_file.
    Returns {file_path: {"score": float, "level": "HIGH"/"MEDIUM"/"LOW"}}
    """
    changed_file = changed_file.replace("/", "\\") if "\\" in next(iter(graph.nodes), "") else changed_file
    scores = {}

    for f in impacted_files:
        try:
            dist = nx.shortest_path_length(graph, source=f, target=changed_file)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            dist = None

        is_test = "test" in f.lower()

        if dist == 1:
            score = 0.80
        elif dist == 2:
            score = 0.50
        else:
            score = 0.20

        if is_test:
            score = max(score, 0.40)

        scores[f] = score

    if changed_file in graph:
        scores[changed_file] = 1.00

    classified = {}
    for f, s in scores.items():
        level = "HIGH" if s >= 0.60 else "MEDIUM" if s >= 0.30 else "LOW"
        classified[f] = {"score": s, "level": level}

    return classified