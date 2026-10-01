import os
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI

from parser_engine import RepoParser

REPO_PATH = os.path.join(os.path.dirname(__file__), "target_repo")
CHANGED_FILE = "utils.py"  # demo default — the file treated as "changed"

# Gemini model name. Override without editing code: set GEMINI_MODEL in your .env
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

# Score -> level thresholds for the ML mode (tune to taste)
HIGH_THRESHOLD = 0.80
MEDIUM_THRESHOLD = 0.60


class ImpactState(TypedDict):
    repo_path: str
    changed_file: str
    impacted_files: List[str]
    report: str


def impact_agent(state: ImpactState) -> ImpactState:
    """Deterministic AST + NetworkX impact detection."""
    parser = RepoParser(state["repo_path"])
    parser.build_dependency_graph()
    state["impacted_files"] = parser.get_impacted_files(state["changed_file"])
    return state


def review_agent(state: ImpactState) -> ImpactState:
    """Uses Gemini to explain the detected impact in plain language."""
    api_key = os.getenv("GEMINI_API_KEY")
    impacted_list = state["impacted_files"] or ["(none detected)"]

    prompt = (
        f"A file named '{state['changed_file']}' was changed in a Python repository.\n"
        f"Static analysis detected these potentially impacted files:\n"
        + "\n".join(f"- {f}" for f in impacted_list)
        + "\n\nExplain briefly why these files might be affected, and suggest "
        "which tests should be re-run. Keep it under 150 words."
    )

    try:
        llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL, google_api_key=api_key)
        explanation = llm.invoke(prompt).content
    except Exception as e:
        explanation = f"(Gemini explanation unavailable: {e})"

    lines = [
        f"**Changed file:** `{state['changed_file']}`",
        "",
        "**Impacted files (deterministic AST/NetworkX analysis):**",
    ]
    lines += [f"- `{f}`" for f in state["impacted_files"]] or ["- None detected"]
    lines += ["", "**LLM Explanation:**", explanation]

    state["report"] = "\n".join(lines)
    return state


def build_workflow() -> StateGraph:
    workflow = StateGraph(ImpactState)
    workflow.add_node("ImpactAgent", impact_agent)
    workflow.add_node("ReviewAgent", review_agent)
    workflow.set_entry_point("ImpactAgent")
    workflow.add_edge("ImpactAgent", "ReviewAgent")
    workflow.add_edge("ReviewAgent", END)
    return workflow.compile()


def run_workflow(changed_file: str = CHANGED_FILE, repo_path: str = REPO_PATH) -> str:
    """Entry point called from app.py — matches `run_workflow()` with no args."""
    graph = build_workflow()
    initial_state: ImpactState = {
        "repo_path": repo_path,
        "changed_file": changed_file,
        "impacted_files": [],
        "report": "",
    }
    final_state = graph.invoke(initial_state)
    return final_state["report"]


from pipeline import run_full_pipeline
from langchain_google_genai import ChatGoogleGenerativeAI
import os


def run_real_instance_workflow(instance_index: int = 0) -> str:
    """Runs the real SWE-bench pipeline and adds an LLM explanation on top."""
    result = run_full_pipeline(instance_index)

    lines = [
        f"**Instance:** `{result['instance_id']}` ({result['repo']})",
        f"**Changed file:** `{result['changed_file']}` (lines: {result['changed_lines']})",
        "",
        "**Impacted files (heuristic score / level):**",
    ]
    for f, info in result["impacted_scored"].items():
        lines.append(f"- `{f}` — {info['level']} ({info['score']})")

    lines += [
        "",
        f"**Evaluation vs real SWE-bench tests:** recall = {result['evaluation']['recall']}",
        "",
        "**Ground-truth tests this fix actually affected:**",
    ]
    lines += [f"- `{t}`" for t in result["evaluation"]["ground_truth_tests"]]

    api_key = os.getenv("GEMINI_API_KEY")
    try:
        llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL, google_api_key=api_key)
        prompt = (
            f"Bug report: {result['problem_statement'][:500]}\n\n"
            f"The file {result['changed_file']} was changed to fix this. "
            f"Explain briefly why the following files are impacted: "
            f"{', '.join(result['impacted_scored'].keys())}"
        )
        explanation = llm.invoke(prompt).content
        lines += ["", "**LLM Explanation:**", explanation]
    except Exception as e:
        lines += ["", f"(LLM explanation unavailable: {e})"]

    return "\n".join(lines)


def analyze_real_instance(instance_index: int = 0) -> dict:
    """Same as run_real_instance_workflow, but returns structured data
    instead of a markdown string, so the UI can render it properly."""
    result = run_full_pipeline(instance_index)

    api_key = os.getenv("GEMINI_API_KEY")
    explanation = "(LLM explanation unavailable)"
    try:
        llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL, google_api_key=api_key)
        prompt = (
            f"Bug report: {result['problem_statement'][:500]}\n\n"
            f"The file {result['changed_file']} was changed to fix this. "
            f"Explain briefly why the following files are impacted: "
            f"{', '.join(result['impacted_scored'].keys())}"
        )
        explanation = llm.invoke(prompt).content
    except Exception as e:
        explanation = f"LLM explanation unavailable: {e}"

    result["explanation"] = explanation
    return result


# ======================================================================
# ML MODE: any GitHub repo + any changed file, scored by the trained model
# ======================================================================

def _normalize_repo(text: str) -> str:
    """Accepts 'owner/name' or a github.com URL and returns 'owner/name'."""
    t = (text or "").strip().rstrip("/")
    if not t:
        raise ValueError("Enter a GitHub repo, e.g. 'psf/requests' or a github.com URL.")
    if t.endswith(".git"):
        t = t[:-4]
    for prefix in ("https://github.com/", "http://github.com/", "github.com/"):
        if t.startswith(prefix):
            t = t[len(prefix):]
    parts = [p for p in t.split("/") if p]
    if len(parts) != 2:
        raise ValueError(
            f"'{text}' doesn't look like a GitHub repo. Use the format 'owner/name' "
            "(e.g. 'psf/requests') or paste a full github.com URL."
        )
    return "/".join(parts)


def _level_for(score: float) -> str:
    if score >= HIGH_THRESHOLD:
        return "HIGH"
    if score >= MEDIUM_THRESHOLD:
        return "MEDIUM"
    return "LOW"


def _reason_for(row) -> str:
    """Plain-language reason built from the real structural features (no LLM involved)."""
    if row["b_imports_a"]:
        return "Directly imports the changed file, so behavior changes propagate to it."
    if row["a_imports_b"]:
        return "Is directly imported by the changed file (a shared dependency that often changes together)."
    d = int(row["graph_distance"])
    if d == 2:
        return "Two import hops from the changed file (shares a common import neighbour)."
    if d > 2:
        return f"{d} import hops away; related mostly through naming/location patterns."
    return "Not connected by imports; ranked from naming/location patterns learned from real pull requests."


def _explain(prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "(Gemini explanation unavailable: GEMINI_API_KEY is not set)"
    try:
        llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL, google_api_key=api_key)
        return llm.invoke(prompt).content
    except Exception as e:
        return f"(Gemini explanation unavailable: {e})"


def analyze_any_repo(repo: str, changed_file: str, top_n: int = 10, use_ai: bool = True) -> dict:
    """
    Runs the trained ML impact model on ANY public GitHub Python repo.
    Returns structured data shaped like analyze_real_instance() so the UI can reuse its widgets.
    """
    from ml_impact_predictor import predict_impact  # lazy import: only needed in this mode

    repo_name = _normalize_repo(repo)
    ranked = predict_impact(repo_name, changed_file, top_n=top_n)

    impacted_scored = {}
    ranking_rows = []
    for _, row in ranked.iterrows():
        score = float(row["impact_probability"])
        level = _level_for(score)
        reason = _reason_for(row)
        impacted_scored[row["file"]] = {
            "score": score,
            "level": level,
            "reason": reason,
            "graph_distance": int(row["graph_distance"]),
        }
        ranking_rows.append({
            "file": row["file"],
            "score": round(score, 3),
            "level": level,
            "import_hops": int(row["graph_distance"]),
            "reason": reason,
        })

    explanation = "AI explanation disabled."
    if use_ai and impacted_scored:
        evidence = "\n".join(
            f"- {f} (score {info['score']:.2f}): {info['reason']}" for f, info in impacted_scored.items()
        )
        prompt = (
            f"The Python file '{changed_file.replace(chr(92), '/')}' in the GitHub repo '{repo_name}' is being changed.\n"
            "A machine-learning model trained on co-change patterns from real GitHub pull requests "
            "ranked these files by how likely they are to be affected, with structural evidence:\n"
            f"{evidence}\n\n"
            "In under 150 words, explain why the top files are likely affected and which tests should be re-run. "
            "Use only the evidence above; do not invent details about the code."
        )
        explanation = _explain(prompt)

    return {
        "repo": repo_name,
        "changed_file": changed_file.replace("\\", "/"),
        "impacted_scored": impacted_scored,
        "ranking": ranking_rows,
        "explanation": explanation,
    }