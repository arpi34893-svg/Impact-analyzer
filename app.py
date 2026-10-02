"""
Agentic Code Reviewer - Streamlit UI.
All analysis logic stays in agent_workflow.py (unchanged); this file only renders results.
"""
import importlib.util
import json
import os
import traceback
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Agentic Code Reviewer", page_icon="◆", layout="wide")

try:  # lets you keep GEMINI_API_KEY (and GITHUB_TOKEN) in a local .env file
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _bridge_secrets() -> None:
    """On Streamlit Cloud, copy keys from st.secrets into the environment if they are not already set."""
    for key in ("GEMINI_API_KEY", "GITHUB_TOKEN"):
        if os.getenv(key):
            continue
        try:
            value = st.secrets.get(key)
        except Exception:  # no secrets file locally
            value = None
        if value:
            os.environ[key] = str(value)


_bridge_secrets()

from agent_workflow import run_workflow, analyze_real_instance, analyze_any_repo  # noqa: E402
from ui_components import (  # noqa: E402
    STAGES, badge, chips, code_diff, empty_state, error_state, hero, inject_css, kpi_grid,
    pipeline_timeline, ranked_files, section, tone_for_level,
)

inject_css()

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "impact_model.joblib"
EVAL_PATH = BASE_DIR / "evaluation_results.json"

MODE_TOY = "Toy demo (target_repo)"
MODE_SWE = "Real SWE-bench instance"
MODE_GH = "Any GitHub repo (ML model)"
MODE_EVAL = "Evaluation & Experiments"

LEVELS = ("HIGH", "MEDIUM", "LOW")
LEVEL_COLORS = {"HIGH": "#f85149", "MEDIUM": "#d29922", "LOW": "#3fb950"}
AI_STAGE = STAGES.index("AI Review")

gemini_ok = bool(os.getenv("GEMINI_API_KEY"))
model_ok = MODEL_PATH.exists()
eval_ok = EVAL_PATH.exists()


# ---------------------------------------------------------------- helpers

def _has(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def redact(text: str) -> str:
    for key in ("GEMINI_API_KEY", "GITHUB_TOKEN"):
        value = os.getenv(key)
        if value:
            text = text.replace(value, "***")
    return text


def friendly_hint(exc: Exception) -> str:
    msg = str(exc).lower()
    if "rate limit" in msg or "403" in msg:
        return "GitHub may be rate-limiting this app. Add GITHUB_TOKEN under Secrets and try again."
    if "404" in msg or "not found" in msg or "could not read" in msg:
        return "Check that the repository is public and written as owner/name."
    if "no such file" in msg or "does not exist" in msg or "not in repo" in msg:
        return "Check that the changed file path exists inside the repository (for example pkg/module.py)."
    return "Check the repository and file path, then try again. Open technical details if it keeps failing."


def run_guarded(label: str, fn, *args, **kwargs):
    """Runs a backend call inside a progress panel. Returns (value, None) or (None, error_dict)."""
    with st.status(label, expanded=True) as status:
        try:
            value = fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - surfaced to the user below
            status.update(label="Analysis failed", state="error", expanded=False)
            return None, {"exc": exc, "tb": traceback.format_exc()}
        status.update(label="Analysis complete", state="complete", expanded=False)
        return value, None


def show_error(title: str, err: dict) -> None:
    message = redact(str(err["exc"]) or err["exc"].__class__.__name__)
    error_state(title, message, hint=friendly_hint(err["exc"]), detail=redact(err["tb"]))


def level_of(info: dict) -> str:
    return str(info.get("level", "")).upper()


def overall_risk(scored: dict) -> str:
    levels = [level_of(info) for info in scored.values()]
    if "HIGH" in levels:
        return "HIGH"
    if "MEDIUM" in levels:
        return "MEDIUM"
    return "LOW"


def swe_reason(info: dict) -> str:
    score = info["score"]
    if score >= 0.80:
        return "Directly imports or is imported by the changed file."
    if score >= 0.30:
        return "Indirectly depends on the changed file through the dependency graph."
    return "Weak/indirect connection detected in the dependency graph."


def rows_for(scored: dict, reason_fn=None, only_level=None, mark_tests=False) -> list:
    rows = []
    for f, info in scored.items():
        if only_level and level_of(info) != only_level:
            continue
        name = f + (" (test file)" if mark_tests and "test" in f.lower() else "")
        reason = reason_fn(info) if reason_fn else info.get("reason")
        rows.append({"file": name, "score": info.get("score"), "level": info.get("level"), "reason": reason})
    return rows


def build_markdown(title: str, meta: list, risk: str, scored: dict, extra=None) -> str:
    out = [f"# {title}", ""]
    out += [f"- **{k}:** {v}" for k, v in meta]
    out += [f"- **Overall risk:** {risk}", "", "## Impacted files", "", "| File | Score | Level |", "|---|---|---|"]
    for f, info in scored.items():
        out.append(f"| `{f}` | {info['score']:.2f} | {info.get('level', '-')} |")
    if extra:
        out += ["", *extra]
    out += ["", "## Recommended actions", "", "1. Review affected files, highest score first",
            "2. Run the flagged test files", "3. Validate downstream behavior"]
    return "\n".join(out)


# ---------------------------------------------------------------- figures

def distribution_figure(scored: dict, risk: str):
    import plotly.graph_objects as go
    counts = [sum(1 for i in scored.values() if level_of(i) == lv) for lv in LEVELS]
    if not any(counts):
        return None
    fig = go.Figure(go.Pie(
        labels=[lv.title() for lv in LEVELS], values=counts, hole=0.7, sort=False, textinfo="none",
        marker=dict(colors=[LEVEL_COLORS[lv] for lv in LEVELS], line=dict(color="#0d1117", width=2)),
        hovertemplate="%{label}: %{value} files<extra></extra>",
    ))
    fig.update_layout(
        showlegend=False, height=210, margin=dict(t=0, b=0, l=0, r=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        annotations=[
            dict(text=f"<b>{risk}</b>", x=0.5, y=0.56, showarrow=False, font=dict(size=18, color=LEVEL_COLORS[risk])),
            dict(text="overall", x=0.5, y=0.42, showarrow=False, font=dict(size=11, color="#8b949e")),
        ],
    )
    return fig


def radial_figure(changed_file: str, scored: dict, top_n: int = 8):
    """Top-ranked files arranged around the changed file. Layout only: lines are NOT import edges."""
    import math
    import plotly.graph_objects as go

    items = list(scored.items())[:top_n]
    if not items:
        return None
    pos = {changed_file: (0.0, 0.0)}
    for i, (f, _) in enumerate(items):
        angle = 2 * math.pi * i / len(items)
        pos[f] = (math.cos(angle), math.sin(angle))

    ex, ey = [], []
    for f, _ in items:
        ex += [0.0, pos[f][0], None]
        ey += [0.0, pos[f][1], None]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ex, y=ey, mode="lines", line=dict(color="#30363d", width=1.2), hoverinfo="skip"))
    fig.add_trace(go.Scatter(
        x=[pos[f][0] for f, _ in items], y=[pos[f][1] for f, _ in items], mode="markers+text",
        text=[f.split("/")[-1] for f, _ in items], textposition="top center",
        textfont=dict(size=10, color="#8b949e"),
        marker=dict(size=20, color=[LEVEL_COLORS.get(level_of(i), "#8b949e") for _, i in items],
                    line=dict(width=1, color="#0d1117")),
        hovertext=[f"{f}<br>score {i['score']:.2f} - {level_of(i)}" for f, i in items], hoverinfo="text",
    ))
    fig.add_trace(go.Scatter(
        x=[0], y=[0], mode="markers+text", text=[changed_file.split("/")[-1]], textposition="bottom center",
        textfont=dict(size=11, color="#e6edf3"),
        marker=dict(size=28, color="#2f81f7", line=dict(width=2, color="#0d1117")),
        hovertext=[f"{changed_file} (changed)"], hoverinfo="text",
    ))
    fig.update_layout(
        showlegend=False, height=380, margin=dict(t=10, b=10, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False, range=[-1.6, 1.6]), yaxis=dict(visible=False, range=[-1.6, 1.6]),
    )
    return fig


# ---------------------------------------------------------------- shared result sections

def render_ranking(scored: dict, reason_fn=None, mark_tests=False) -> None:
    if not scored:
        empty_state("No candidate files", "No candidate files were ranked for this query.")
        return
    ranked_files(rows_for(scored, reason_fn, mark_tests=mark_tests))


def render_distribution(scored: dict, risk: str) -> None:
    fig = distribution_figure(scored, risk)
    if fig is None:
        st.caption("No impact levels to chart.")
        return
    st.plotly_chart(fig, config={"displayModeBar": False})
    st.markdown(
        " ".join(badge(f"{lv.title()} {sum(1 for i in scored.values() if level_of(i) == lv)}", tone_for_level(lv))
                 for lv in LEVELS),
        unsafe_allow_html=True,
    )


def render_impact_map(changed_file: str, scored: dict, enabled: bool, reason_fn=None, mark_tests=False) -> None:
    if not enabled:
        st.info("Dependency analysis is disabled in the sidebar options.")
        return
    if not scored:
        empty_state("No impact map", "No dependency relationships were found for this change.")
        return
    fig = radial_figure(changed_file, scored)
    st.plotly_chart(fig, config={"displayModeBar": False})
    st.caption(f"Blue is the changed file. The closest ring shows up to 8 of {len(scored)} ranked files, colored by "
               "impact level (red high, amber medium, green low). This is a ranking view, not an import graph.")
    for lv in LEVELS:
        rows = rows_for(scored, reason_fn, only_level=lv, mark_tests=mark_tests)
        if rows:
            with st.expander(f"{lv.title()} impact ({len(rows)})", expanded=(lv == "HIGH")):
                ranked_files(rows)


def render_review(scored: dict, risk: str, explanation, show_ai: bool, reason_fn=None) -> None:
    section("Review summary")
    st.markdown(f"**Overall risk:** {badge(risk, tone_for_level(risk))}", unsafe_allow_html=True)
    if show_ai and gemini_ok:
        if explanation:
            st.info(explanation)
        else:
            st.caption("No AI explanation was generated for this run. Enable it in the sidebar and analyze again.")
    elif show_ai and not gemini_ok:
        st.warning("AI explanation unavailable: the Gemini API key is not configured "
                   "(add GEMINI_API_KEY to your .env file or Streamlit Secrets). Static ranking is still valid.")
    else:
        st.caption("AI explanation is disabled in the sidebar options.")

    section("Findings", f"{len(scored)} file(s) flagged")
    if not scored:
        st.write("No issue detected by static analysis.")
        return
    for i, (f, info) in enumerate(scored.items(), 1):
        with st.expander(f"Finding #{i} - {f}"):
            st.markdown(f"**Severity:** {badge(level_of(info) or 'n/a', tone_for_level(level_of(info)))}",
                        unsafe_allow_html=True)
            st.code(f, language=None)
            reason = reason_fn(info) if reason_fn else info.get("reason", "")
            if reason:
                st.markdown(f"**Reason:** {reason}")
            st.markdown(f"**Impact score:** {info['score']:.2f}")
            st.markdown("**Recommendation:** Run this file's tests before merging.")


def render_report_tab(md_text: str, data, key: str, filename: str) -> None:
    safe_json = json.dumps(data, indent=2, default=str)
    c1, c2 = st.columns(2)
    c1.download_button("Download report (.md)", md_text, file_name=f"{filename}.md",
                       mime="text/markdown", key=f"{key}_dl_md")
    c2.download_button("Download data (.json)", safe_json, file_name=f"{filename}.json",
                       mime="application/json", key=f"{key}_dl_json")
    st.markdown(md_text)
    with st.expander("Raw Markdown"):
        st.code(md_text, language="markdown")
    with st.expander("Raw JSON"):
        st.json(safe_json)


# ---------------------------------------------------------------- pages

def page_toy() -> None:
    section("Toy demo", "Analyze the bundled sample repository (target_repo).")
    go = st.button("Analyze sample repository", type="primary", key="toy_go")
    failed = False
    if go:
        report, err = run_guarded("Analyzing dependency graph...", run_workflow)
        if err:
            st.session_state.pop("res_toy", None)
            show_error("Analysis failed", err)
            failed = True
        else:
            st.session_state["res_toy"] = report
    res = st.session_state.get("res_toy")
    if res is None:
        if not failed:
            empty_state("Run the sample analysis", "Click Analyze sample repository to see the workflow report.")
        return
    st.markdown(res)
    if st.button("Clear result", key="toy_reset"):
        st.session_state.pop("res_toy", None)
        st.rerun()


def page_github(opts: dict) -> None:
    section("Analyze a repository",
            "Enter a public GitHub repository and a changed .py file. The first run on a new repo clones it, "
            "so it takes a little longer.")
    with st.form("gh_form"):
        c1, c2 = st.columns(2)
        repo = c1.text_input("GitHub repository", value="mongodb/mongo-python-driver", key="gh_repo",
                             help="owner/name or a github.com URL")
        changed = c2.text_input("Changed file", value="pymongo/collection.py", key="gh_path",
                                help="A .py file path relative to the repo root")
        top_n = st.slider("Files to rank", min_value=5, max_value=30, value=10, key="gh_k")
        submitted = st.form_submit_button("Analyze repository", type="primary")

    failed = False
    if submitted:
        if not repo.strip() or not changed.strip():
            error_state("Missing input", "Enter both a repository and a changed file path.")
            failed = True
        else:
            data, err = run_guarded(
                "Cloning repository (first run only), building the dependency graph, scoring impact...",
                analyze_any_repo, repo, changed, top_n=int(top_n), use_ai=opts["ai"])
            if err:
                st.session_state.pop("res_gh", None)
                show_error("Analysis failed", err)
                failed = True
            else:
                st.session_state["res_gh"] = data

    ml = st.session_state.get("res_gh")
    if ml is None:
        if not failed:
            empty_state("Analyze your first repository",
                        "Fill in the form above and click Analyze repository to rank the files most likely "
                        "to be affected by your change.")
        return

    scored = ml["impacted_scored"]
    risk = overall_risk(scored)
    tests = [f for f in scored if "test" in f.lower()]
    if st.button("Try another repository", key="gh_reset"):
        st.session_state.pop("res_gh", None)
        st.rerun()

    tab_o, tab_m, tab_r, tab_f = st.tabs(["Overview", "Impact map", "AI review", "Final report"])
    with tab_o:
        kpi_grid([
            ("Repository", ml["repo"], "Analyzed"),
            ("Overall impact", risk, "", tone_for_level(risk)),
            ("Files ranked", len(scored)),
            ("Test files flagged", len(tests) if opts["tests"] else "off", "filename contains 'test'"),
        ])
        section("Changed file")
        st.code(ml["changed_file"], language=None)
        left, right = st.columns([2, 1])
        with left:
            section("Most likely impacted files",
                    "Ranked by an ML model trained on co-change patterns in real GitHub pull requests. "
                    "Scores rank likelihood; they are not exact probabilities.")
            render_ranking(scored, mark_tests=opts["tests"])
        with right:
            section("Impact distribution")
            render_distribution(scored, risk)
        section("Pipeline")
        pipeline_timeline(done=len(STAGES), skipped=[] if (opts["ai"] and gemini_ok) else [AI_STAGE])
    with tab_m:
        render_impact_map(ml["changed_file"], scored, opts["map"], mark_tests=opts["tests"])
    with tab_r:
        render_review(scored, risk, ml.get("explanation"), opts["ai"])
    with tab_f:
        md = build_markdown("Code review summary",
                            [("Repository", ml["repo"]), ("Changed file", ml["changed_file"])], risk, scored)
        render_report_tab(md, ml, "gh", "code_review_report")


def page_swe(opts: dict) -> None:
    section("Analyze a SWE-bench Lite instance", "Instances come from SWE-bench Lite on Hugging Face (0 to 299).")
    with st.form("swe_form"):
        idx = st.number_input("Instance index", min_value=0, max_value=299, value=0, key="swe_idx")
        submitted = st.form_submit_button("Analyze instance", type="primary")

    failed = False
    if submitted:
        data, err = run_guarded("Cloning repo, parsing patch, building dependency graph, scoring impact...",
                                analyze_real_instance, int(idx))
        if err:
            st.session_state.pop("res_swe", None)
            show_error("Pipeline error", err)
            failed = True
        else:
            st.session_state["res_swe"] = data

    result = st.session_state.get("res_swe")
    if result is None:
        if not failed:
            empty_state("Pick an instance", "Choose an instance index above and click Analyze instance.")
        return

    scored = result["impacted_scored"]
    risk = overall_risk(scored)
    ev = result["evaluation"]
    n_gt = len(ev["ground_truth_tests"])
    if st.button("Try another instance", key="swe_reset"):
        st.session_state.pop("res_swe", None)
        st.rerun()

    t_ov, t_diff, t_map, t_rev, t_trace, t_fin = st.tabs(
        ["Overview", "Diff", "Impact map", "AI review", "Agent trace", "Final report"])
    with t_ov:
        kpi_grid([
            ("Repository", result["repo"], "Analyzed"),
            ("Changed files", result.get("changed_files_count", 1)),
            ("Impact", risk, "", tone_for_level(risk)),
            ("Impacted files", len(scored)),
            ("Changed lines", len(result["changed_lines"])),
            ("Tests affected", f"{len(ev['matched_tests'])} of {n_gt}", "vs. ground-truth tests"),
        ])
        section("Instance")
        st.code(f"{result['instance_id']}\n{result['changed_file']}", language=None)
        section("Impacted files")
        render_ranking(scored, swe_reason, mark_tests=opts["tests"])
    with t_diff:
        st.caption("Raw patch as provided by SWE-bench Lite.")
        code_diff(result["raw_patch"])
    with t_map:
        render_impact_map(result["changed_file"], scored, opts["map"], swe_reason, mark_tests=opts["tests"])
    with t_rev:
        render_review(scored, risk, result.get("explanation"), opts["ai"], swe_reason)
    with t_trace:
        ai_ran = opts["ai"] and gemini_ok
        pipeline_timeline(done=len(STAGES), skipped=[] if ai_ran else [AI_STAGE])
        steps = [
            ("Dataset Agent", f"Loaded SWE-bench instance {result['instance_id']}"),
            ("Repository Agent", f"Repository {result['repo']} checked out"),
            ("Patch Agent", f"Parsed {len(result['changed_lines'])} changed line(s)"),
            ("AST + Dependency Agent", "Built AST-based NetworkX dependency graph"),
            ("Impact Agent", f"Scored {len(scored)} impacted file(s)"),
            ("Test Evaluation Agent", f"Matched against {n_gt} ground-truth test(s)"),
            ("Review Agent (Gemini)",
             "Generated developer-facing explanation" if ai_ran else "Skipped: Gemini not configured or disabled"),
        ]
        for name, detail in steps:
            with st.expander(name, expanded=False):
                st.write(detail)
    with t_fin:
        md = build_markdown(
            "Code review summary",
            [("Repository", result["repo"]), ("Changed file", result["changed_file"]),
             ("Instance", result["instance_id"])],
            risk, scored,
            extra=["## Evaluation", "", f"Recall vs. real tests: {ev['recall'] * 100:.0f}%"])
        render_report_tab(md, result, "swe", "code_review_report")


def page_eval() -> None:
    if not eval_ok:
        empty_state("No evaluation report yet",
                    "Run python -u evaluate_model.py once in your terminal, then reload this page.")
        st.caption("This trains on 75% of repos and evaluates ranking quality on the other 25%, "
                   "repos the model never saw during training.")
        return
    try:
        with open(EVAL_PATH, "r", encoding="utf-8") as fh:
            ev = json.load(fh)
        ks = ev["k_values"]
        at_k = ev["ranking"]["at_k"]
        section("Held-out generalization evaluation",
                f"Trained on repos excluding {ev['held_out_repos']} held-out repo(s) "
                f"({ev['held_out_rows']} candidate file-pairs), then evaluated only on those unseen repos.")
        kpi_grid([
            ("Pairwise accuracy", f"{ev['classification']['accuracy'] * 100:.1f}%", "Single file-pair classification"),
            ("ROC AUC", f"{ev['classification']['roc_auc']:.3f}", "Raw classifier score"),
            ("Mean reciprocal rank", f"{ev['ranking']['mean_reciprocal_rank']:.3f}", "Ours"),
        ])

        section("Ranking quality (Precision@K, Recall@K, F1@K)",
                f"Evaluated over {ev['ranking']['queries_evaluated']} held-out queries. Each query is one file "
                "changing, ranking every other file in its repo, scored against files that co-changed in a "
                "merged pull request.")
        import pandas as pd
        labels = [f"K={k}" for k in ks]
        st.bar_chart(pd.DataFrame({
            "Precision@K": [at_k[str(k)]["precision"] for k in ks],
            "Recall@K": [at_k[str(k)]["recall"] for k in ks],
            "F1@K": [at_k[str(k)]["f1"] for k in ks],
        }, index=labels))
        kpi_grid([(f"F1 at K={k}", f"{at_k[str(k)]['f1']:.3f}") for k in ks])

        if "baseline" in ev:
            import plotly.graph_objects as go
            section("Ours vs. baseline (ablation)",
                    "Baseline uses only filename similarity and same-folder location, with no dependency graph "
                    "and no ML. This isolates what the AST graph plus trained model add.")
            fig = go.Figure()
            fig.add_bar(name="Ours (graph + ML)", x=labels, y=[at_k[str(k)]["precision"] for k in ks],
                        marker_color="#2f81f7")
            fig.add_bar(name="Baseline (filename only)", x=labels,
                        y=[ev["baseline"]["at_k"][str(k)]["precision"] for k in ks], marker_color="#484f58")
            fig.update_layout(barmode="group", height=320, yaxis_title="Precision@K",
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              font=dict(color="#8b949e"), legend=dict(orientation="h", y=1.15),
                              margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig, config={"displayModeBar": False})
            kpi_grid([("Ours MRR", f"{ev['ranking']['mean_reciprocal_rank']:.3f}"),
                      ("Baseline MRR", f"{ev['baseline']['mean_reciprocal_rank']:.3f}")])

        with st.expander("What do these metrics mean?"):
            st.markdown(
                "- **Precision@K**: of the top K files flagged, what fraction actually needed changes?\n"
                "- **Recall@K**: of the files that needed changes, what fraction were caught in the top K?\n"
                "- **F1@K**: harmonic mean of the two.\n"
                "- **Mean Reciprocal Rank (MRR)**: how close to #1 the first correct file lands. "
                "1.0 means the top file is always correct; 0.5 means typically second.")
        st.caption("Regenerate this report after retraining or adding repos: python -u evaluate_model.py")
    except (KeyError, ValueError, OSError) as exc:
        error_state("Could not read the evaluation report", str(exc),
                    hint="Re-run python -u evaluate_model.py to regenerate evaluation_results.json.")


# ---------------------------------------------------------------- shell

with st.sidebar:
    section("Analysis mode")
    mode = st.radio("Mode", [MODE_TOY, MODE_SWE, MODE_GH, MODE_EVAL], label_visibility="collapsed", key="mode")
    opts = {"ai": True, "map": True, "tests": True}
    if mode != MODE_EVAL:
        section("Options")
        opts["ai"] = st.checkbox("Enable AI explanation", value=True, key="opt_ai")
        opts["map"] = st.checkbox("Enable dependency analysis", value=True, key="opt_map")
        opts["tests"] = st.checkbox("Enable test impact analysis", value=True, key="opt_tests")
    section("Powered by")
    st.caption("LangGraph, Gemini, RandomForest ML model, NetworkX, SWE-bench Lite")

hero("Agentic Code Reviewer",
     "Predict which files a code change affects, then review it with an AI agent. AST + ML + LLM.",
     status="Ready" if model_ok else "ML model not trained", status_tone="ok" if model_ok else "medium")
chips([
    ("ML impact model" if model_ok else "ML impact model (not trained)", model_ok),
    ("Gemini" if gemini_ok else "Gemini (not configured)", gemini_ok),
    ("Evaluation report" if eval_ok else "Evaluation report (not run)", eval_ok),
    ("NetworkX", _has("networkx")),
    ("LangGraph", _has("langgraph")),
])

if mode == MODE_TOY:
    page_toy()
elif mode == MODE_SWE:
    page_swe(opts)
elif mode == MODE_GH:
    page_github(opts)
else:
    page_eval()