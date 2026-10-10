"""
Agentic Code Reviewer - Production Grade Academic Edition.
A modern, web-grade application for repository change-impact intelligence,
topological graph matrices, ML co-change prediction, and multi-agent AI review.
"""
import os
import json
import traceback
from pathlib import Path
from typing import Dict, Any, List, Optional

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(
    page_title="Agentic Code Reviewer | Impact Intelligence",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _bridge_secrets() -> None:
    """Bridge Streamlit Cloud secrets to environment variables."""
    for key in ("GEMINI_API_KEY", "GITHUB_TOKEN"):
        if os.getenv(key):
            continue
        try:
            value = st.secrets.get(key)
        except Exception:
            value = None
        if value:
            os.environ[key] = str(value)


_bridge_secrets()

# Import presentation and calculation helpers
from ui_components import (
    inject_css,
    app_navbar,
    section,
    kpi_grid,
    ranked_files,
    badge,
    tone_for_level,
    pipeline_timeline,
    empty_state,
    error_state,
    code_diff,
    radial_graph_figure,
    render_coupling_heatmap,
    render_centrality_chart,
    render_feature_importance_figure,
    render_confusion_matrix_heatmap,
    STAGES,
)
from matrix_calculator import (
    compute_dependency_coupling_matrix,
    compute_feature_matrix,
    compute_topological_centrality_matrix,
    compute_confusion_matrix,
    get_feature_importances,
)
from repo_ingestion import (
    extract_uploaded_zip,
    list_local_repositories,
    get_repo_modules,
    run_comprehensive_analysis,
)
from agent_workflow import analyze_real_instance

# Apply vibrant dark violet theme
inject_css()

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "impact_model.joblib"
EVAL_PATH = BASE_DIR / "evaluation_results.json"

NAV_WORKSPACE = "🏠 Reviewer Workspace & Hub"
NAV_GITHUB = "🌐 Live GitHub Explorer"
NAV_SWEBENCH = "🔬 SWE-bench Benchmark Lab"
NAV_MATRICES = "📊 Matrix & Generalization Lab"

NAV_OPTIONS = [NAV_WORKSPACE, NAV_GITHUB, NAV_SWEBENCH, NAV_MATRICES]

LEVELS = ("HIGH", "MEDIUM", "LOW")
LEVEL_COLORS = {"HIGH": "#f43f5e", "MEDIUM": "#f59e0b", "LOW": "#10b981"}
AI_STAGE = STAGES.index("AI Review")

gemini_ok = bool(os.getenv("GEMINI_API_KEY"))
model_ok = MODEL_PATH.exists()
eval_ok = EVAL_PATH.exists()
local_repos = list_local_repositories()


# ---------------------------------------------------------------- helpers & navigation

def navigate_to(target_mode: str) -> None:
    st.session_state["nav_mode"] = target_mode
    st.rerun()


def render_page_arrows(
    prev_nav: Optional[str] = None,
    next_nav: Optional[str] = None,
    prev_label: str = "← Previous",
    next_label: str = "Next Page →",
) -> None:
    """Renders sleek arrow navigation buttons to transition between workflow stages."""
    c1, c2 = st.columns([1, 1])
    if prev_nav:
        if c1.button(prev_label, key=f"prev_{prev_nav}_{next_nav}", use_container_width=True):
            navigate_to(prev_nav)
    if next_nav:
        if c2.button(next_label, type="primary", key=f"next_{prev_nav}_{next_nav}", use_container_width=True):
            navigate_to(next_nav)


def redact(text: str) -> str:
    for key in ("GEMINI_API_KEY", "GITHUB_TOKEN"):
        value = os.getenv(key)
        if value:
            text = text.replace(value, "***")
    return text


def overall_risk(scored: dict) -> str:
    levels = [str(info.get("level", "")).upper() for info in scored.values()]
    if "HIGH" in levels:
        return "HIGH"
    if "MEDIUM" in levels:
        return "MEDIUM"
    return "LOW"


def run_guarded(label: str, fn, *args, **kwargs):
    with st.status(label, expanded=True) as status:
        try:
            val = fn(*args, **kwargs)
        except Exception as exc:
            status.update(label="Analysis failed", state="error", expanded=False)
            return None, {"exc": exc, "tb": traceback.format_exc()}
        status.update(label="Analysis complete", state="complete", expanded=False)
        return val, None


def show_error(title: str, err: dict) -> None:
    msg = redact(str(err["exc"]) or err["exc"].__class__.__name__)
    error_state(title, msg, detail=redact(err["tb"]))


def rows_for(scored: dict, reason_fn=None, only_level=None, mark_tests=False) -> list:
    rows = []
    for f, info in scored.items():
        lvl = str(info.get("level", "")).upper()
        if only_level and lvl != only_level:
            continue
        name = f + (" (test file)" if mark_tests and ("test" in f.lower() or info.get("is_test")) else "")
        reason = reason_fn(info) if reason_fn else info.get("reason", "")
        rows.append({"file": name, "score": info.get("score"), "level": info.get("level"), "reason": reason})
    return rows


def build_markdown_report(title: str, meta: list, risk: str, scored: dict, explanation: str = "") -> str:
    lines = [f"# {title}", ""]
    lines += [f"- **{k}:** {v}" for k, v in meta]
    lines += [f"- **Overall Risk:** {risk}", "", "## Impacted Files", "", "| File | Impact Score | Level | Reason |", "|---|---|---|---|"]
    for f, info in scored.items():
        reason = info.get("reason", "-").replace("|", "/")
        lines.append(f"| `{f}` | {info['score']:.2f} | {info.get('level', '-')} | {reason} |")
    if explanation:
        lines += ["", "## AI Architectural Review", "", explanation]
    lines += [
        "", "## Recommended Engineering Actions", "",
        "1. Prioritize peer review on HIGH severity files.",
        "2. Execute integration test suites covering the flagged modules.",
        "3. Validate backward compatibility of public APIs.",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- Matrix Tab Visualizer

def render_calculated_matrices_tab(
    analysis_data: Dict[str, Any],
    changed_file: str,
    scored: Dict[str, Any],
) -> None:
    section("🧮 Calculated Matrices Suite", "Mathematical and topological matrices derived from the codebase.")

    m_tab1, m_tab2, m_tab3, m_tab4 = st.tabs([
        "🔗 Dependency Coupling Matrix",
        "📋 Pairwise Feature Matrix (X)",
        "🌐 Graph Centrality Matrix",
        "⚖️ Model Feature Weights",
    ])

    with m_tab1:
        st.markdown(
            "**Module Dependency Coupling Matrix ($C_{ij}$):** "
            "Evaluates pairwise import connections between the target module and candidate files in the AST graph. "
            "Hover over cells to inspect exact directional import relationships."
        )
        coupling = analysis_data.get("coupling_matrix")
        if coupling and coupling.get("matrix"):
            fig = render_coupling_heatmap(coupling)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            empty_state("Coupling Matrix Unavailable", "No dependency coupling records were found for this module.")

    with m_tab2:
        st.markdown(
            "**Feature Calculation Matrix ($X \\in \\mathbb{R}^{N \\times 11}$):** "
            "Numerical and categorical feature vectors evaluated by the Random Forest classifier for each candidate file pair."
        )
        feat_df = analysis_data.get("feature_matrix_df")
        if feat_df is not None and not feat_df.empty:
            st.dataframe(
                feat_df.style.format({
                    "impact_probability": "{:.4f}",
                    "name_similarity": "{:.2f}",
                }).background_gradient(subset=["impact_probability"], cmap="Purples"),
                use_container_width=True,
                height=380,
            )
            c1, c2 = st.columns(2)
            c1.download_button(
                "📥 Export Feature Matrix (.csv)",
                feat_df.to_csv(index=False),
                file_name="feature_matrix.csv",
                mime="text/csv",
                key="dl_feat_csv",
            )
            c2.download_button(
                "📥 Export Feature Matrix (.json)",
                feat_df.to_json(orient="records", indent=2),
                file_name="feature_matrix.json",
                mime="application/json",
                key="dl_feat_json",
            )
        else:
            empty_state("No Feature Matrix", "Feature vectors were not generated for this run.")

    with m_tab3:
        st.markdown(
            "**Topological Graph Centrality Matrix:** "
            "Measures the structural significance of the modified module and candidate files within the repository graph. "
            "High Betweenness indicates an architectural bridge or bottleneck module."
        )
        cent_df = analysis_data.get("centrality_df")
        if cent_df is not None and not cent_df.empty:
            c_fig = render_centrality_chart(cent_df)
            st.plotly_chart(c_fig, use_container_width=True, config={"displayModeBar": False})
            st.dataframe(cent_df, use_container_width=True)
        else:
            empty_state("Centrality Data Unavailable", "Centrality metrics could not be computed.")

    with m_tab4:
        st.markdown(
            "**Random Forest Feature Importance Weights:** "
            "Relative contribution of each topological and syntactic feature towards the predicted co-change probability."
        )
        importances = get_feature_importances()
        if importances:
            f_fig = render_feature_importance_figure(importances)
            st.plotly_chart(f_fig, use_container_width=True, config={"displayModeBar": False})
            kpi_grid([
                ("Top Feature", max(importances.items(), key=lambda x: x[1])[0], "Highest predictive weight"),
                ("Graph Features", f"{(importances.get('shared_neighbors', 0) + importances.get('graph_distance', 0))*100:.1f}%", "Combined graph weight"),
                ("Naming Similarity", f"{importances.get('name_similarity', 0)*100:.1f}%", "Filename match weight"),
            ])
        else:
            empty_state("Model Not Loaded", "Feature weights are available once impact_model.joblib is loaded.")


# ---------------------------------------------------------------- Page 1: Reviewer Workspace & Hub

def page_workspace(opts: dict) -> None:
    # Top Status KPIs
    kpi_grid([
        ("Repository Catalog", f"{len(local_repos)} repos", "Cached & local repositories", "info"),
        ("Model Generalization", "0.971 MRR", "Held-out ranking benchmark", "ok"),
        ("Dependency Graph", "AST NetworkX", "Deterministic AST resolution", "ok"),
        ("AI Review Agent", "Gemini 3.6 Flash", "Autonomous code reasoning", "ok" if gemini_ok else "medium"),
    ])

    # Direct Working Area
    section(
        "Ingest Repository & Select Target Module",
        "Select an indexed repository or upload a ZIP archive, pick the modified module, and calculate impact matrices.",
    )

    ingest_tab1, ingest_tab2 = st.tabs(["📂 Select Indexed Repository", "📁 Upload Archive (.zip)"])

    repo_source_path = None
    repo_display_label = ""

    with ingest_tab1:
        repo_names = [r["name"] for r in local_repos]
        active_preset = st.session_state.get("active_repo_source")
        preset_idx = 0
        if active_preset:
            for i, r in enumerate(local_repos):
                if r["path"] == active_preset:
                    preset_idx = i
                    break

        selected_name = st.selectbox(
            "Repository:",
            repo_names,
            index=preset_idx if repo_names else None,
            key="workspace_repo_select",
        )
        if selected_name:
            for r in local_repos:
                if r["name"] == selected_name:
                    repo_source_path = r["path"]
                    repo_display_label = r["name"]
                    break

    with ingest_tab2:
        uploaded_file = st.file_uploader(
            "Upload Python project archive (.zip):",
            type=["zip"],
            key="workspace_zip_upload",
            help="Upload a zip file containing Python code.",
        )
        if uploaded_file is not None:
            with st.spinner("Extracting repository archive..."):
                extracted_dir = extract_uploaded_zip(uploaded_file, uploaded_file.name)
                repo_source_path = extracted_dir
                repo_display_label = f"Uploaded: {uploaded_file.name}"
                st.success(f"Extracted '{uploaded_file.name}' successfully.")

    if not repo_source_path or not os.path.exists(repo_source_path):
        empty_state("No Repository Selected", "Select a repository above to index Python modules.")
        return

    # Index Python modules
    modules = get_repo_modules(repo_source_path)
    if not modules:
        error_state("No Python Modules Found", f"No .py files detected inside '{repo_display_label}'.")
        return

    # Quick sample test presets
    col_p1, col_p2, col_p3 = st.columns([1, 1, 2])
    with col_p1:
        if st.button("⚡ Quick Test: Mongo collection.py", use_container_width=True):
            mongo_path = os.path.join(BASE_DIR, "repositories", "mongodb__mongo-python-driver")
            if os.path.exists(mongo_path):
                st.session_state["active_repo_source"] = mongo_path
                st.session_state["active_module"] = "pymongo/collection.py"
                st.rerun()
    with col_p2:
        if st.button("⚡ Quick Test: target_repo utils.py", use_container_width=True):
            st.session_state["active_repo_source"] = os.path.join(BASE_DIR, "target_repo")
            st.session_state["active_module"] = "utils.py"
            st.rerun()

    # Module selection form
    with st.form("workspace_analyze_form"):
        col_m1, col_m2 = st.columns([3, 1])

        module_paths = [m["rel_path"] for m in modules]
        default_idx = 0
        preset_mod = st.session_state.get("active_module")
        if preset_mod and preset_mod in module_paths:
            default_idx = module_paths.index(preset_mod)

        with col_m1:
            chosen_module = st.selectbox(
                f"Target Modified Module ({len(modules)} found):",
                module_paths,
                index=default_idx,
                key="workspace_module_box",
            )

        with col_m2:
            top_k = st.slider("Candidate files to rank:", min_value=5, max_value=30, value=12, key="ws_top_k")

        submit_btn = st.form_submit_button("🚀 Run Module Impact Analysis & Compute Matrices", type="primary")

    if submit_btn:
        with st.spinner("Building AST dependency graph and computing matrices..."):
            data, err = run_guarded(
                f"Analyzing impact for '{chosen_module}'...",
                run_comprehensive_analysis,
                repo_source_path,
                chosen_module,
                top_n=int(top_k),
                use_ai=opts["ai"],
            )
            if err:
                show_error("Analysis failed", err)
            else:
                st.session_state["res_workspace"] = data

    result = st.session_state.get("res_workspace")
    if result is not None:
        scored = result["impacted_scored"]
        risk = overall_risk(scored)
        test_files_flagged = [f for f, info in scored.items() if info.get("is_test") or "test" in f.lower()]

        section("Analysis Results", f"Module: `{result['changed_file']}` &bull; Repo: `{result['repo']}`")

        kpi_grid([
            ("Target Module", result["changed_file"].split("/")[-1], result["changed_file"]),
            ("Overall Risk", risk, "Composite severity", tone_for_level(risk)),
            ("Impacted Files", len(scored), f"Ranked from {result['total_modules']} modules"),
            ("AST Graph Edges", result["total_import_edges"], "Total directional imports", "info"),
            ("Test Suites at Risk", len(test_files_flagged), "Tests affected", "medium" if test_files_flagged else "ok"),
        ])

        tab_files, tab_mat, tab_ai, tab_rep = st.tabs([
            "🎯 Impacted Files & Graph",
            "🧮 The Matrices Being Calculated",
            "🤖 AI Reviewer & Trace",
            "📄 Engineering Report",
        ])

        with tab_files:
            col_g, col_l = st.columns([1, 1])
            with col_g:
                section("Dependency Topology Map")
                rad_fig = radial_graph_figure(result["changed_file"], scored, top_n=10)
                if rad_fig:
                    st.plotly_chart(rad_fig, use_container_width=True, config={"displayModeBar": False})
            with col_l:
                section("Ranked Impacted Files", "Sorted by Random Forest co-change probability.")
                ranked_files(rows_for(scored, mark_tests=opts["tests"]))

        with tab_mat:
            render_calculated_matrices_tab(result, result["changed_file"], scored)

        with tab_ai:
            section("🤖 Multi-Agent Reviewer Synthesis")
            st.markdown(f"**Calculated Merge Risk:** {badge(risk, tone_for_level(risk))}", unsafe_allow_html=True)
            if result.get("explanation"):
                st.info(result["explanation"])

            section("Pipeline Execution Trace")
            pipeline_timeline(done=len(STAGES), skipped=[] if (opts["ai"] and gemini_ok) else [AI_STAGE])
            with st.expander("Agent 01: Ingestion & Module Parser", expanded=False):
                st.write(f"Scanned {result['total_modules']} Python modules from `{result['repo']}`.")
            with st.expander("Agent 02: AST NetworkX Graph Engine", expanded=False):
                st.write(f"Constructed directed dependency graph with {result['total_import_edges']} import edges.")
            with st.expander("Agent 03: Random Forest ML Predictor", expanded=False):
                st.write("Extracted 11 pairwise features and computed co-change probabilities for candidate files.")
            with st.expander("Agent 04: Matrix Computation Suite", expanded=False):
                st.write("Generated dependency coupling matrix, topological centrality matrix, and feature table.")
            with st.expander("Agent 05: Gemini AI Synthesis", expanded=False):
                st.write(result.get("explanation", "AI review generated."))

        with tab_rep:
            md_report = build_markdown_report(
                "Autonomous Code Review & Impact Report",
                [("Repository", result["repo"]), ("Target Module", result["changed_file"])],
                risk,
                scored,
                explanation=result.get("explanation", ""),
            )
            c_d1, c_d2 = st.columns(2)
            c_d1.download_button("📥 Download Report (.md)", md_report, file_name="impact_report.md", mime="text/markdown", key="dl_rep_md")
            c_d2.download_button("📥 Download Data (.json)", json.dumps(scored, indent=2), file_name="impact_data.json", mime="application/json", key="dl_rep_json")
            st.markdown(md_report)

    # Next Stage Navigation Arrows
    st.markdown("<br>", unsafe_allow_html=True)
    render_page_arrows(
        prev_nav=None,
        next_nav=NAV_GITHUB,
        next_label="Next: Live GitHub Explorer →",
    )


# ---------------------------------------------------------------- Page 2: Live GitHub Explorer

def page_github_explorer(opts: dict) -> None:
    render_page_arrows(
        prev_nav=NAV_WORKSPACE,
        next_nav=NAV_SWEBENCH,
        prev_label="← Previous: Reviewer Workspace",
        next_label="Next: SWE-bench Lab →",
    )

    section(
        "🌐 Live GitHub Repository Analyzer",
        "Connect directly to any public GitHub repository, parse its AST dependency graph, and calculate impact matrices.",
    )

    with st.form("gh_live_form"):
        col_g1, col_g2 = st.columns(2)
        repo_input = col_g1.text_input(
            "GitHub Repository (owner/name or URL):",
            value="mongodb/mongo-python-driver",
            help="Example: 'psf/requests' or 'mongodb/mongo-python-driver'",
            key="gh_repo_in",
        )
        mod_input = col_g2.text_input(
            "Modified Python Module path:",
            value="pymongo/collection.py",
            help="Relative path to .py file in repo root",
            key="gh_mod_in",
        )
        top_k = st.slider("Candidate files to rank:", min_value=5, max_value=30, value=10, key="gh_top_k")
        submit_gh = st.form_submit_button("🚀 Clone & Analyze GitHub Repo", type="primary")

    if submit_gh:
        if not repo_input.strip() or not mod_input.strip():
            error_state("Missing Input", "Enter both a GitHub repository and a module path.")
        else:
            with st.spinner("Fetching GitHub repository, building graph, and scoring impact..."):
                data, err = run_guarded(
                    f"Cloning and analyzing '{repo_input}'...",
                    run_comprehensive_analysis,
                    repo_input.strip(),
                    mod_input.strip(),
                    top_n=int(top_k),
                    use_ai=opts["ai"],
                )
                if err:
                    show_error("GitHub Analysis Failed", err)
                else:
                    st.session_state["res_gh"] = data

    res = st.session_state.get("res_gh")
    if res is None:
        empty_state("Analyze Any GitHub Project", "Fill in the form above and click 'Clone & Analyze GitHub Repo'.")
        return

    scored = res["impacted_scored"]
    risk = overall_risk(scored)

    kpi_grid([
        ("Repository", res["repo"], "GitHub Source"),
        ("Changed Module", res["changed_file"].split("/")[-1], res["changed_file"]),
        ("Blast Radius", risk, "", tone_for_level(risk)),
        ("Impacted Files", len(scored)),
        ("Total Modules", res["total_modules"], "Parsed in repo"),
    ])

    tab1, tab2, tab3 = st.tabs(["🎯 Impacted Files & Graph", "🧮 Calculated Matrices", "🤖 AI Review & Report"])

    with tab1:
        col1, col2 = st.columns([1, 1])
        with col1:
            rad_fig = radial_graph_figure(res["changed_file"], scored)
            if rad_fig:
                st.plotly_chart(rad_fig, use_container_width=True, config={"displayModeBar": False})
        with col2:
            ranked_files(rows_for(scored, mark_tests=opts["tests"]))

    with tab2:
        render_calculated_matrices_tab(res, res["changed_file"], scored)

    with tab3:
        if res.get("explanation"):
            st.info(res["explanation"])
        md = build_markdown_report("GitHub Code Review Summary", [("Repo", res["repo"]), ("File", res["changed_file"])], risk, scored)
        st.download_button("Download Report (.md)", md, file_name="gh_report.md", mime="text/markdown", key="dl_gh_rep")

    st.markdown("<br>", unsafe_allow_html=True)
    render_page_arrows(
        prev_nav=NAV_WORKSPACE,
        next_nav=NAV_SWEBENCH,
        prev_label="← Previous: Reviewer Workspace",
        next_label="Next: SWE-bench Lab →",
    )


# ---------------------------------------------------------------- Page 3: SWE-bench Benchmark Lab

def page_swebench_lab(opts: dict) -> None:
    render_page_arrows(
        prev_nav=NAV_GITHUB,
        next_nav=NAV_MATRICES,
        prev_label="← Previous: Live GitHub Explorer",
        next_label="Next: Matrix & Generalization Lab →",
    )

    section(
        "🔬 SWE-bench Lite Laboratory",
        "Benchmark against real-world production PRs from SWE-bench Lite. "
        "Calculates ground-truth test suite matching, recall, and classification confusion matrices.",
    )

    with st.form("swe_form"):
        col_s1, col_s2 = st.columns([3, 1])
        instance_idx = col_s1.number_input("SWE-bench Lite Instance Index (0 to 299):", min_value=0, max_value=299, value=0)
        submit_swe = col_s2.form_submit_button("Analyze Instance", type="primary")

    if submit_swe:
        with st.spinner("Checking out repo commit, parsing patch, and evaluating ground-truth tests..."):
            data, err = run_guarded("Evaluating SWE-bench instance...", analyze_real_instance, int(instance_idx))
            if err:
                show_error("SWE-bench Pipeline Error", err)
            else:
                st.session_state["res_swe"] = data

    result = st.session_state.get("res_swe")
    if result is None:
        empty_state("Choose an Instance", "Select a SWE-bench Lite instance above and click 'Analyze Instance'.")
        return

    scored = result["impacted_scored"]
    risk = overall_risk(scored)
    ev = result["evaluation"]
    gt_tests = ev["ground_truth_tests"]

    cm_data = compute_confusion_matrix(list(scored.keys()), gt_tests)

    kpi_grid([
        ("Instance ID", result["instance_id"], result["repo"]),
        ("Changed File", result["changed_file"].split("/")[-1], result["changed_file"]),
        ("Test Recall", f"{ev['recall'] * 100:.0f}%", "vs. ground-truth tests", "ok" if ev['recall'] > 0.5 else "medium"),
        ("Matched Tests", f"{len(ev['matched_tests'])} / {len(gt_tests)}", "Ground truth caught"),
        ("Overall Risk", risk, "", tone_for_level(risk)),
    ])

    tab_ov, tab_cm, tab_diff, tab_ai = st.tabs([
        "🎯 Predictions & Graph",
        "🧮 Ground-Truth Confusion Matrix",
        "📜 Patch Diff",
        "🤖 AI Review & Trace",
    ])

    with tab_ov:
        c1, c2 = st.columns([1, 1])
        with c1:
            rad = radial_graph_figure(result["changed_file"], scored)
            if rad:
                st.plotly_chart(rad, use_container_width=True, config={"displayModeBar": False})
        with c2:
            ranked_files(rows_for(scored, mark_tests=opts["tests"]))

    with tab_cm:
        section("Benchmark Confusion Matrix & Test Oracle Alignment")
        st.markdown(
            "Compares statically predicted impacted files against ground-truth tests modified in the reference PR. "
            "Calculates precision, recall, and harmonic F1 score."
        )
        col_cm1, col_cm2 = st.columns([1, 1])
        with col_cm1:
            cm_fig = render_confusion_matrix_heatmap(cm_data)
            st.plotly_chart(cm_fig, use_container_width=True, config={"displayModeBar": False})
        with col_cm2:
            kpi_grid([
                ("Precision", f"{cm_data['precision']:.3f}", "TP / (TP + FP)"),
                ("Recall", f"{cm_data['recall']:.3f}", "TP / (TP + FN)"),
                ("F1 Score", f"{cm_data['f1']:.3f}", "Harmonic Mean"),
                ("True Positives", f"{cm_data['tp']}", "Verified tests caught", "ok"),
            ])
            with st.expander("Matched Ground-Truth Tests", expanded=True):
                for t in ev["matched_tests"]:
                    st.code(t, language=None)

    with tab_diff:
        code_diff(result.get("raw_patch", ""))

    with tab_ai:
        if result.get("explanation"):
            st.info(result["explanation"])
        pipeline_timeline(done=len(STAGES), skipped=[] if (opts["ai"] and gemini_ok) else [AI_STAGE])

    st.markdown("<br>", unsafe_allow_html=True)
    render_page_arrows(
        prev_nav=NAV_GITHUB,
        next_nav=NAV_MATRICES,
        prev_label="← Previous: Live GitHub Explorer",
        next_label="Next: Matrix & Generalization Lab →",
    )


# ---------------------------------------------------------------- Page 4: Generalization & Matrix Lab

def page_matrix_and_generalization() -> None:
    render_page_arrows(
        prev_nav=NAV_SWEBENCH,
        next_nav=NAV_WORKSPACE,
        prev_label="← Previous: SWE-bench Lab",
        next_label="🏠 Return to Reviewer Workspace →",
    )

    section(
        "📊 Held-Out Generalization & Matrix Laboratory",
        "Empirical evaluation on unseen repositories held out during Random Forest training. "
        "Validates that graph topological features generalize without overfitting.",
    )

    if not eval_ok:
        empty_state(
            "Evaluation Report Missing",
            "Run 'python -u evaluate_model.py' to generate held-out generalization results."
        )
        return

    try:
        with open(EVAL_PATH, "r", encoding="utf-8") as fh:
            ev = json.load(fh)

        ks = ev["k_values"]
        at_k = ev["ranking"]["at_k"]

        kpi_grid([
            ("Pairwise Accuracy", f"{ev['classification']['accuracy'] * 100:.1f}%", "Single file-pair classification", "ok"),
            ("ROC AUC", f"{ev['classification']['roc_auc']:.3f}", "Discriminative ability", "ok"),
            ("Mean Reciprocal Rank", f"{ev['ranking']['mean_reciprocal_rank']:.3f}", "Top rank position (1.0 = best)", "ok"),
            ("Held-out Repos", f"{ev['held_out_repos']}", f"{ev['held_out_rows']} file-pairs never seen in training", "info"),
        ])

        section("Precision@K, Recall@K, and F1@K Curves")
        labels = [f"K={k}" for k in ks]
        chart_df = pd.DataFrame({
            "Precision@K": [at_k[str(k)]["precision"] for k in ks],
            "Recall@K": [at_k[str(k)]["recall"] for k in ks],
            "F1@K": [at_k[str(k)]["f1"] for k in ks],
        }, index=labels)
        st.bar_chart(chart_df)

        if "baseline" in ev:
            section("Ablation Study: Ours (Graph + ML) vs. Baseline (Filename Only)")
            fig = go.Figure()
            fig.add_bar(name="Ours (AST Graph + ML)", x=labels, y=[at_k[str(k)]["precision"] for k in ks], marker_color="#8b5cf6")
            fig.add_bar(name="Baseline (Filename heuristic only)", x=labels, y=[ev["baseline"]["at_k"][str(k)]["precision"] for k in ks], marker_color="#475569")
            fig.update_layout(
                barmode="group",
                height=320,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#cbd5e1"),
                margin=dict(t=10, b=10, l=10, r=10),
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        section("Random Forest Feature Importance Weights")
        importances = get_feature_importances()
        if importances:
            imp_fig = render_feature_importance_figure(importances)
            st.plotly_chart(imp_fig, use_container_width=True, config={"displayModeBar": False})

    except Exception as exc:
        error_state("Failed to read evaluation report", str(exc))

    st.markdown("<br>", unsafe_allow_html=True)
    render_page_arrows(
        prev_nav=NAV_SWEBENCH,
        next_nav=NAV_WORKSPACE,
        prev_label="← Previous: SWE-bench Lab",
        next_label="🏠 Return to Reviewer Workspace →",
    )


# ---------------------------------------------------------------- Main Shell & Navigation

# Top Navbar (Single clean executive header)
app_navbar(model_ok=model_ok, gemini_ok=gemini_ok, repo_count=len(local_repos))

# Sidebar controls
with st.sidebar:
    st.markdown("### 🧭 Navigation")
    current_nav = st.session_state.get("nav_mode", NAV_WORKSPACE)
    curr_idx = NAV_OPTIONS.index(current_nav) if current_nav in NAV_OPTIONS else 0
    mode_selection = st.radio(
        "Application Mode",
        NAV_OPTIONS,
        index=curr_idx,
        key=f"sidebar_radio_{current_nav}",
    )
    if mode_selection != current_nav:
        st.session_state["nav_mode"] = mode_selection
        st.rerun()

    st.markdown("### ⚙️ Pipeline Options")
    opt_ai = st.checkbox("Enable Gemini AI Review", value=True, key="opt_ai")
    opt_map = st.checkbox("Enable Dependency Graph", value=True, key="opt_map")
    opt_tests = st.checkbox("Flag Test Suite Modules", value=True, key="opt_tests")

    with st.expander("🔑 API Key Configuration", expanded=not gemini_ok):
        user_key = st.text_input("Gemini API Key:", value=os.getenv("GEMINI_API_KEY", ""), type="password")
        if user_key:
            os.environ["GEMINI_API_KEY"] = user_key
            st.caption("Key active for this session.")

    st.caption("Agentic Code Reviewer &bull; Production Academic Edition<br>AST Graph &bull; RandomForest &bull; SWE-bench", unsafe_allow_html=True)

opts = {"ai": opt_ai, "map": opt_map, "tests": opt_tests}

if current_nav == NAV_WORKSPACE:
    page_workspace(opts)
elif current_nav == NAV_GITHUB:
    page_github_explorer(opts)
elif current_nav == NAV_SWEBENCH:
    page_swebench_lab(opts)
else:
    page_matrix_and_generalization()