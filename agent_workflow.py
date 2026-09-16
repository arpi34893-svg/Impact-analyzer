import os
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI

from parser_engine import RepoParser

REPO_PATH = os.path.join(os.path.dirname(__file__), "target_repo")
CHANGED_FILE = "utils.py"  # demo default — the file treated as "changed"


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
        llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", google_api_key=api_key)
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
        llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", google_api_key=api_key)
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
        llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", google_api_key=api_key)
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