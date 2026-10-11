"""
repo_ingestion.py - Handles repository ingestion (ZIP uploads, local folders, pre-cloned repos)
and comprehensive module analysis for the Agentic Code Reviewer.
"""
from __future__ import annotations

import os
import shutil
import zipfile
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional

from features import RepoContext
from matrix_calculator import (
    compute_feature_matrix,
    compute_dependency_coupling_matrix,
    compute_topological_centrality_matrix,
    _level_for_score,
)
from ml_impact_predictor import clone_repo_if_needed, RepoAccessError

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "repositories", "uploads")
REPOSITORIES_DIR = os.path.join(os.path.dirname(__file__), "repositories")


def _extract_text(content) -> str:
    """
    Normalizes a langchain/Gemini '.content' value into plain text for display.
    Newer Gemini responses sometimes come back as a STRING, and sometimes as a
    LIST of content blocks, e.g.:
        [{'type': 'text', 'text': '...the real answer...', 'extras': {'signature': '...'}}]
    Without this, the raw list (including the signature blob) gets shown to the user.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text" and block.get("text"):
                    parts.append(block["text"])
            elif isinstance(block, str):
                parts.append(block)
        if parts:
            return "\n\n".join(parts)
        return str(content)  # fallback: nothing recognizable, show it raw rather than silently drop it
    return str(content)


def extract_uploaded_zip(uploaded_file, upload_name: str = "custom_repo") -> str:
    """
    Safely extracts an uploaded zip file into repositories/uploads/<clean_name>.
    Returns the absolute path to the extracted repository root.
    """
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    clean_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in upload_name.replace(".zip", ""))
    target_dir = os.path.join(UPLOAD_DIR, clean_name)

    if os.path.exists(target_dir):
        shutil.rmtree(target_dir, ignore_errors=True)
    os.makedirs(target_dir, exist_ok=True)

    with zipfile.ZipFile(uploaded_file, "r") as zf:
        zf.extractall(target_dir)

    # If the zip contains a single top-level directory, descend into it
    items = [f for f in os.listdir(target_dir) if not f.startswith(".")]
    if len(items) == 1 and os.path.isdir(os.path.join(target_dir, items[0])):
        return os.path.join(target_dir, items[0])

    return target_dir


def list_local_repositories() -> List[Dict[str, str]]:
    """Returns a list of local repositories available for instant analysis."""
    repos = []
    base_dir = os.path.dirname(__file__)

    # 1. Bundled target_repo
    target_path = os.path.join(base_dir, "target_repo")
    if os.path.exists(target_path):
        repos.append({
            "name": "target_repo (Bundled Sample)",
            "path": target_path,
            "type": "sample",
        })

    # 2. Cloned repositories in repositories/
    if os.path.exists(REPOSITORIES_DIR):
        for entry in os.listdir(REPOSITORIES_DIR):
            if entry in ("uploads", "__pycache__"):
                continue
            full_p = os.path.join(REPOSITORIES_DIR, entry)
            if os.path.isdir(full_p):
                display = entry.replace("__", "/")
                repos.append({
                    "name": display,
                    "path": full_p,
                    "type": "cached",
                })

    # 3. Uploaded repositories
    if os.path.exists(UPLOAD_DIR):
        for entry in os.listdir(UPLOAD_DIR):
            full_p = os.path.join(UPLOAD_DIR, entry)
            if os.path.isdir(full_p):
                repos.append({
                    "name": f"Uploaded: {entry}",
                    "path": full_p,
                    "type": "uploaded",
                })

    return repos


def get_repo_modules(repo_path: str) -> List[Dict[str, Any]]:
    """
    Finds and indexes all .py modules inside a repository directory.
    Returns sorted list of module metadata dictionaries.
    """
    if not os.path.isdir(repo_path):
        return []

    modules = []
    for root, _, files in os.walk(repo_path):
        # Skip common non-project dirs
        rel_root = os.path.relpath(root, repo_path).replace("\\", "/")
        rel_parts = [p for p in rel_root.split("/") if p and p != "."]
        if any(part.startswith(".") or part in ("__pycache__", "venv", "env", "node_modules", "dist", "build", ".git")
               for part in rel_parts):
            continue

        for f in files:
            if f.endswith(".py"):
                full_p = os.path.join(root, f)
                rel_p = os.path.relpath(full_p, repo_path).replace("\\", "/")
                size_kb = round(os.path.getsize(full_p) / 1024, 1)
                is_test = "test" in f.lower() or "tests" in rel_p.lower()

                modules.append({
                    "rel_path": rel_p,
                    "filename": f,
                    "size_kb": size_kb,
                    "is_test": is_test,
                })

    modules.sort(key=lambda m: (m["is_test"], m["rel_path"]))
    return modules


def run_comprehensive_analysis(
    repo_source: str,
    changed_module: str,
    top_n: int = 12,
    use_ai: bool = True,
) -> Dict[str, Any]:
    """
    Performs full change-impact analysis on a repository (local path, uploaded path, or GitHub URL/name):
    1. Parses AST and builds NetworkX dependency graph via RepoContext
    2. Computes complete Pairwise Feature Matrix using ML Random Forest
    3. Computes Dependency Coupling / Adjacency Matrix
    4. Computes Graph Centrality and Topological Metrics
    5. Optionally queries Gemini LLM for developer-facing architectural reasoning
    """
    # Resolve repo path
    if os.path.isdir(repo_source):
        repo_path = repo_source
        display_name = os.path.basename(repo_source)
    else:
        # Remote GitHub repository
        repo_path = clone_repo_if_needed(repo_source)
        display_name = repo_source

    ctx = RepoContext(repo_path)
    if len(ctx.files) == 0:
        raise RepoAccessError(f"No valid Python modules found in repository '{display_name}'.")

    norm_changed = changed_module.replace("\\", "/").strip()
    if norm_changed not in ctx.file_set:
        matches = [f for f in ctx.files if norm_changed in f or f.endswith(norm_changed)]
        if matches:
            norm_changed = matches[0]
        else:
            raise ValueError(f"Selected module '{changed_module}' was not found in the repository graph.")

    # 1. Feature Matrix & ML Impact Ranking
    feat_df = compute_feature_matrix(ctx, norm_changed, top_n=top_n)

    top_candidate_files = feat_df["file"].tolist() if not feat_df.empty else []

    # 2. Dependency Coupling Adjacency Matrix
    coupling_matrix = compute_dependency_coupling_matrix(ctx, norm_changed, top_candidate_files)

    # 3. Topological Centrality Matrix
    centrality_df = compute_topological_centrality_matrix(ctx, norm_changed, top_candidate_files)

    # 4. Impacted scored dict for compatibility with existing UI widgets
    impacted_scored = {}
    for _, row in feat_df.iterrows():
        score = float(row["impact_probability"])
        level = row["level"]
        impacted_scored[row["file"]] = {
            "score": score,
            "level": level,
            "reason": row["reason"],
            "graph_distance": int(row["graph_distance"]),
            "is_test": bool(row["is_test_b"]),
        }

    # 5. AI Code Reviewer Explanation
    explanation = "AI explanation disabled."
    if use_ai:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            explanation = (
                "⚠️ Gemini API Key is not configured. Add GEMINI_API_KEY in the sidebar or .env to activate "
                "autonomous reasoning. The deterministic AST Graph and ML Random Forest matrices are fully active."
            )
        else:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
                llm = ChatGoogleGenerativeAI(model=gemini_model, google_api_key=api_key)

                evidence_lines = [
                    f"- {f} (Score: {info['score']:.2f}, Level: {info['level']}): {info['reason']}"
                    for f, info in list(impacted_scored.items())[:6]
                ]
                prompt = (
                    f"You are an expert senior code reviewer conducting change-impact blast radius analysis.\n"
                    f"Repository: {display_name}\n"
                    f"Modified Module: {norm_changed}\n\n"
                    f"Static AST Graph analysis and Random Forest ML impact model flagged these top candidate files:\n"
                    + "\n".join(evidence_lines) + "\n\n"
                    "Provide a crisp, actionable review in under 180 words addressing:\n"
                    "1. Architecture Impact: Why these specific modules are at risk of regression.\n"
                    "2. Test Strategy: Which test suites or mocks must be re-run before PR merge.\n"
                    "3. Merge Safety Verdict: HIGH, MEDIUM, or LOW risk."
                )
                raw_content = llm.invoke(prompt).content
                explanation = _extract_text(raw_content)
            except Exception as exc:
                explanation = f"AI explanation generated an error: {exc}"

    return {
        "repo": display_name,
        "repo_path": repo_path,
        "changed_file": norm_changed,
        "total_modules": len(ctx.files),
        "total_import_edges": ctx.directed.number_of_edges(),
        "impacted_scored": impacted_scored,
        "feature_matrix_df": feat_df,
        "coupling_matrix": coupling_matrix,
        "centrality_df": centrality_df,
        "explanation": explanation,
    }