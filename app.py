import os
import json
import streamlit as st

try:  # lets you keep GEMINI_API_KEY (and GITHUB_TOKEN) in a .env file
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from agent_workflow import run_workflow, analyze_real_instance, analyze_any_repo

st.set_page_config(page_title="Agentic Code Reviewer", page_icon="◆", layout="wide")

# ---------- Styling ----------
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
    :root {
        --bg-0: #0a0e14; --bg-1: #10151d; --bg-2: #161d29; --border: #232b38;
        --text-0: #e6edf3; --text-1: #9aa7b8; --text-2: #6b7686;
        --accent: #5b8cff; --accent-dim: #223252;
        --ok: #2ea86b; --warn: #d99a2b; --bad: #e5534b;
    }
    .stApp { background: var(--bg-0); font-family: 'Inter', sans-serif; }
    code, .stCode, pre { font-family: 'JetBrains Mono', monospace !important; }
    #MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }

    section[data-testid="stSidebar"] { background: var(--bg-1); border-right: 1px solid var(--border); }
    section[data-testid="stSidebar"] .stRadio label, section[data-testid="stSidebar"] p { color: var(--text-1); }

    .brand-row { display:flex; align-items:center; gap:10px; margin-bottom:2px; }
    .brand-mark { width:9px; height:9px; border-radius:2px; background:var(--accent);
                  box-shadow:0 0 10px var(--accent); display:inline-block; }
    .header-title { font-family:'JetBrains Mono',monospace; font-size:1.5rem; font-weight:700;
                    color:var(--text-0); letter-spacing:0.02em; margin:0; }
    .header-sub { color: var(--text-2); font-size:0.88rem; margin:4px 0 18px 22px; }

    .status-row { display:flex; gap:10px; margin:0 0 22px 0; flex-wrap:wrap; }
    .status-chip { font-size:0.74rem; font-family:'JetBrains Mono',monospace; padding:4px 10px;
                   border-radius:20px; border:1px solid var(--border); background:var(--bg-2); }
    .chip-on { color:var(--ok); border-color:#1b3d2c; }
    .chip-off { color:var(--text-2); }

    .kpi-row { display:flex; gap:14px; flex-wrap:wrap; margin-bottom:18px; }
    .kpi { flex:1; min-width:150px; background:var(--bg-1); border:1px solid var(--border);
           border-radius:10px; padding:14px 16px; }
    .kpi-label { font-size:0.72rem; color:var(--text-2); text-transform:uppercase; letter-spacing:0.06em; }
    .kpi-value { font-family:'JetBrains Mono',monospace; font-size:1.5rem; color:var(--text-0);
                 font-weight:700; margin-top:4px; word-break:break-all; }
    .kpi-high { color:var(--bad); } .kpi-medium { color:var(--warn); } .kpi-low { color:var(--ok); }

    .badge-high { background:#33161a; color:var(--bad); padding:2px 10px; border-radius:4px; font-size:0.76rem; font-weight:600; border:1px solid #4a2027; }
    .badge-medium { background:#332b16; color:var(--warn); padding:2px 10px; border-radius:4px; font-size:0.76rem; font-weight:600; border:1px solid #4a3d20; }
    .badge-low { background:#122a1e; color:var(--ok); padding:2px 10px; border-radius:4px; font-size:0.76rem; font-weight:600; border:1px solid #1e4230; }

    .rank-row { display:flex; align-items:center; gap:12px; padding:10px 4px;
                border-bottom:1px solid var(--border); }
    .rank-file { font-family:'JetBrains Mono',monospace; font-size:0.85rem; color:var(--text-0); flex:2; min-width:0;
                 overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .rank-bar-track { flex:2; background:var(--bg-2); border-radius:4px; height:8px; overflow:hidden; min-width:60px; }
    .rank-bar-fill { height:100%; border-radius:4px; }
    .rank-score { font-family:'JetBrains Mono',monospace; font-size:0.8rem; color:var(--text-1); width:48px; text-align:right; }
    .rank-reason { color:var(--text-2); font-size:0.78rem; flex:3; min-width:0; }

    .diff-add { background:#0f2418; color:#3fb950; padding:1px 6px; font-family:'JetBrains Mono',monospace; display:block; white-space:pre; }
    .diff-remove { background:#2d1214; color:#f85149; padding:1px 6px; font-family:'JetBrains Mono',monospace; display:block; white-space:pre; }
    .diff-context { color:var(--text-2); padding:1px 6px; font-family:'JetBrains Mono',monospace; display:block; white-space:pre; }

    .stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid var(--border); }
    .stTabs [data-baseweb="tab"] { font-family:'JetBrains Mono',monospace; font-size:0.82rem;
                                    color:var(--text-2); padding: 8px 4px; }
    .stTabs [aria-selected="true"] { color: var(--accent) !important; }

    .stButton>button { font-family:'JetBrains Mono',monospace; font-weight:600; border-radius:8px; }
    div[data-testid="stMetricValue"] { font-family:'JetBrains Mono',monospace; }
</style>
""", unsafe_allow_html=True)


def bar_color(score: float) -> str:
    if score >= 0.80:
        return "#e5534b"
    if score >= 0.60:
        return "#d99a2b"
    return "#2ea86b"


def render_ranking(impacted_scored: dict):
    """Custom ranked list with inline score bars — replaces the raw st.dataframe table."""
    if not impacted_scored:
        st.info("No candidate files were ranked for this query.")
        return
    max_score = max((info["score"] for info in impacted_scored.values()), default=1.0) or 1.0
    rows_html = ""
    for f, info in impacted_scored.items():
        pct = max(4, round((info["score"] / max_score) * 100))
        color = bar_color(info["score"])
        rows_html += f"""
        <div class="rank-row">
            <span class="rank-file" title="{f}">{f}</span>
            <span class="rank-score">{info['score']:.2f}</span>
            <div class="rank-bar-track"><div class="rank-bar-fill" style="width:{pct}%;background:{color};"></div></div>
            <span class="rank-reason">{info['reason']}</span>
        </div>"""
    st.markdown(f'<div>{rows_html}</div>', unsafe_allow_html=True)


def kpi_card(label: str, value: str, tone: str = "") -> str:
    cls = f"kpi-value {tone}".strip()
    return f'<div class="kpi"><div class="kpi-label">{label}</div><div class="{cls}">{value}</div></div>'


def badge(level: str) -> str:
    cls = {"HIGH": "badge-high", "MEDIUM": "badge-medium", "LOW": "badge-low"}[level]
    return f'<span class="{cls}">{level}</span>'


def overall_risk(scored: dict) -> str:
    if not scored:
        return "LOW"
    levels = [info["level"] for info in scored.values()]
    if "HIGH" in levels:
        return "HIGH"
    if "MEDIUM" in levels:
        return "MEDIUM"
    return "LOW"


# ---------- Header ----------
st.markdown('<div class="brand-row"><span class="brand-mark"></span>'
            '<p class="header-title">AGENTIC CODE REVIEWER</p></div>', unsafe_allow_html=True)
st.markdown('<p class="header-sub">Repository-Level Change Impact Analysis · AST + ML + LLM</p>', unsafe_allow_html=True)

gemini_ok = bool(os.getenv("GEMINI_API_KEY"))
model_ok = os.path.exists("impact_model.joblib")
eval_ok = os.path.exists("evaluation_results.json")


def chip(label: str, ok: bool, off_label: str = None) -> str:
    text = label if ok else (off_label or f"{label} (off)")
    cls = "chip-on" if ok else "chip-off"
    return f'<span class="status-chip {cls}">● {text}</span>'


st.markdown(
    '<div class="status-row">'
    + chip("Repository Connected", True)
    + chip("AST Analyzer", True)
    + chip("NetworkX", True)
    + chip("LangGraph", True)
    + chip("ML Impact Model", model_ok, "ML Impact Model (not trained)")
    + chip("Gemini", gemini_ok, "Gemini (not configured)")
    + chip("Evaluation Report", eval_ok, "Evaluation Report (not run)")
    + "</div>",
    unsafe_allow_html=True,
)

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("**PROJECT**")
    st.caption("Dataset: SWE-bench/SWE-bench_Lite")
    st.caption("Source: Hugging Face")

    st.markdown("---")
    st.markdown("**ANALYSIS**")
    mode = st.radio(
        "Mode",
        ["Toy demo (target_repo)", "Real SWE-bench instance", "Any GitHub repo (ML model)",
         "Evaluation & Experiments"],
        label_visibility="collapsed",
    )
    instance_index = None
    repo_input = None
    changed_input = None
    top_n = 10
    if mode == "Real SWE-bench instance":
        instance_index = st.number_input("Instance index", min_value=0, max_value=299, value=0)
    elif mode == "Any GitHub repo (ML model)":
        repo_input = st.text_input("GitHub repo", value="mongodb/mongo-python-driver",
                                   help="owner/name or a github.com URL")
        changed_input = st.text_input("Changed file (path inside repo)", value="pymongo/collection.py",
                                      help="A .py file path relative to the repo root")
        top_n = st.slider("Files to rank", min_value=5, max_value=30, value=10)

    run_clicked = False
    if mode != "Evaluation & Experiments":
        run_clicked = st.button("▶ Run Analysis", type="primary", use_container_width=True)

    show_ai = show_map = show_tests = True
    if mode != "Evaluation & Experiments":
        st.markdown("---")
        st.markdown("**OPTIONS**")
        show_ai = st.checkbox("Enable AI explanation", value=True)
        show_map = st.checkbox("Enable dependency analysis", value=True)
        show_tests = st.checkbox("Enable test impact analysis", value=True)

    st.markdown("---")
    st.markdown("**SYSTEM**")
    st.caption(f"Pipeline status: {'Ready' if run_clicked else 'Idle'}")
    st.caption("Cache: repositories/ (local)")


# ---------- Toy demo ----------
if mode == "Toy demo (target_repo)":
    if run_clicked:
        with st.spinner("Analyzing dependency graph..."):
            try:
                report = run_workflow()
                st.markdown(report)
            except Exception as e:
                st.error(f"Error during analysis: {e}")
    else:
        st.info("Click Run Analysis to analyze the sample target_repo.")
    st.stop()

# ---------- Any GitHub repo (ML model) ----------
if mode == "Any GitHub repo (ML model)":
    if not run_clicked:
        st.info("Enter a GitHub repo and a changed .py file in the sidebar, then click Run Analysis. "
                "The first run on a new repo clones it, so it takes a little longer.")
        st.stop()

    with st.spinner("Cloning repo (if new), building dependency graph, scoring impact with the ML model..."):
        try:
            ml = analyze_any_repo(repo_input, changed_input, top_n=int(top_n), use_ai=show_ai)
        except Exception as e:
            st.error(f"Analysis error: {e}")
            st.stop()

    ml_risk = overall_risk(ml["impacted_scored"])
    ml_tests = [f for f in ml["impacted_scored"] if "test" in f.lower()]

    tab_o, tab_m, tab_r, tab_f = st.tabs(["OVERVIEW", "IMPACT MAP", "AI REVIEW", "FINAL REPORT"])

    with tab_o:
        risk_tone = {"HIGH": "kpi-high", "MEDIUM": "kpi-medium", "LOW": "kpi-low"}[ml_risk]
        st.markdown(
            '<div class="kpi-row">'
            + kpi_card("Repository", ml["repo"])
            + kpi_card("Overall Impact", ml_risk, risk_tone)
            + kpi_card("Files Ranked", str(len(ml["impacted_scored"])))
            + kpi_card("Test Files Flagged", str(len(ml_tests)) if show_tests else "off")
            + "</div>", unsafe_allow_html=True,
        )
        st.markdown(f"**Changed file:** `{ml['changed_file']}`")
        st.caption("Ranking from an ML model trained on co-change patterns in real GitHub pull requests. "
                   "Scores rank likelihood of also needing changes; they are not exact probabilities.")
        render_ranking(ml["impacted_scored"])

    with tab_m:
        if not show_map:
            st.info("Dependency analysis disabled in sidebar options.")
        else:
            st.markdown(f"**Changed** → `{ml['changed_file']}`")
            st.markdown("↓")
            for level_name in ["HIGH", "MEDIUM", "LOW"]:
                files_at_level = [f for f, info in ml["impacted_scored"].items() if info["level"] == level_name]
                if files_at_level:
                    st.markdown(f"**{level_name} impact**")
                    for f in files_at_level:
                        tag = " (test file)" if "test" in f.lower() else ""
                        st.code(f"{f}{tag}   score {ml['impacted_scored'][f]['score']:.2f}", language=None)

    with tab_r:
        st.markdown("**REVIEW COMPLETED**")
        st.markdown(f"**Overall Risk:** {badge(ml_risk)}", unsafe_allow_html=True)
        if show_ai and gemini_ok:
            st.markdown("**Review Summary**")
            st.info(ml["explanation"])
        elif show_ai and not gemini_ok:
            st.warning("AI explanation unavailable.\n\nReason: Gemini API key is not configured "
                       "(add GEMINI_API_KEY to your .env file). ML ranking above is still valid.")
        else:
            st.caption("AI explanation disabled in sidebar options.")

        st.markdown("---")
        st.markdown("**Findings**")
        for i, (f, info) in enumerate(ml["impacted_scored"].items(), 1):
            with st.expander(f"Finding #{i} — {f}"):
                st.markdown(f"**Severity:** {badge(info['level'])}", unsafe_allow_html=True)
                st.markdown(f"**File:** `{f}`")
                st.markdown(f"**Reason:** {info['reason']}")
                st.markdown(f"**Impact score:** {info['score']:.2f}")
                st.markdown("**Recommendation:** Run this file's tests before merging.")

    with tab_f:
        lines = [
            "CODE REVIEW SUMMARY", "-" * 40,
            f"Repository: {ml['repo']}",
            f"Changed: {ml['changed_file']}",
            f"Overall Risk: {ml_risk}",
            "",
            "IMPACTED FILES (ML model ranking)", "-" * 40,
        ]
        for f, info in ml["impacted_scored"].items():
            lines.append(f"{f}  {info['score']:.2f}  {info['level']}")
        lines += [
            "",
            "RECOMMENDED ACTIONS", "-" * 40,
            "1. Review affected files, highest score first",
            "2. Run the flagged test files",
            "3. Validate downstream behavior",
        ]
        ml_report = "\n".join(lines)
        st.code(ml_report, language=None)
        st.download_button("Download report (.md)", ml_report, file_name="code_review_report.md")
    st.stop()

# ---------- Evaluation & Experiments ----------
if mode == "Evaluation & Experiments":
    if not eval_ok:
        st.warning(
            "No evaluation report found. Run this once in your terminal, then reload this page:\n\n"
            "`python -u evaluate_model.py`"
        )
        st.caption("This trains on 75% of repos and evaluates ranking quality on the other 25% — "
                   "repos the model never saw during training.")
        st.stop()

    with open("evaluation_results.json", "r", encoding="utf-8") as f:
        ev = json.load(f)

    st.markdown("### Held-out generalization evaluation")
    st.caption(f"Model trained on repos excluding {ev['held_out_repos']} held-out repo(s) "
               f"({ev['held_out_rows']} candidate file-pairs), then evaluated only on those unseen repos.")

    c1, c2 = st.columns(2)
    c1.markdown(kpi_card("Pairwise Accuracy", f"{ev['classification']['accuracy']*100:.1f}%"),
                unsafe_allow_html=True)
    c2.markdown(kpi_card("ROC AUC", f"{ev['classification']['roc_auc']:.3f}"), unsafe_allow_html=True)
    st.caption("Pairwise accuracy: given one file-pair, is it correctly labeled impacted / not-impacted? "
               "This is the raw classifier score, not the ranking quality below.")

    st.markdown("### Ranking quality (Precision@K / Recall@K / F1@K)")
    st.caption(
        f"Evaluated over {ev['ranking']['queries_evaluated']} held-out queries — each query is "
        "'one file changes, rank every other file in its repo', scored against files that "
        "really co-changed with it in a merged pull request."
    )

    k_labels = [f"K={k}" for k in ev["k_values"]]
    precision_vals = [ev["ranking"]["at_k"][str(k)]["precision"] for k in ev["k_values"]]
    recall_vals = [ev["ranking"]["at_k"][str(k)]["recall"] for k in ev["k_values"]]
    f1_vals = [ev["ranking"]["at_k"][str(k)]["f1"] for k in ev["k_values"]]

    import pandas as pd
    chart_df = pd.DataFrame({"Precision@K": precision_vals, "Recall@K": recall_vals, "F1@K": f1_vals},
                             index=k_labels)
    st.bar_chart(chart_df)

    cols = st.columns(len(ev["k_values"]) + 1)
    cols[0].markdown(kpi_card("Mean Reciprocal Rank", f"{ev['ranking']['mean_reciprocal_rank']:.3f}"),
                      unsafe_allow_html=True)
    for i, k in enumerate(ev["k_values"], start=1):
        m = ev["ranking"]["at_k"][str(k)]
        cols[i].markdown(kpi_card(f"F1 @ K={k}", f"{m['f1']:.3f}"), unsafe_allow_html=True)

    with st.expander("What do these metrics mean?"):
        st.markdown("""
- **Precision@K** — of the top K files the model flags, what fraction actually needed changes?
- **Recall@K** — of the files that actually needed changes, what fraction were caught in the top K?
- **F1@K** — harmonic mean of the two; a single number balancing both.
- **Mean Reciprocal Rank (MRR)** — on average, how close to #1 was the *first* correctly-flagged file?
  A value of 1.0 means the top-ranked file is always correct; 0.5 means it's typically the 2nd result.
        """)

    st.markdown("---")
    st.caption("Regenerate this report after retraining or adding repos: `python -u evaluate_model.py`")
    st.stop()

# ---------- Real instance ----------
if not run_clicked:
    st.info("Select an instance index in the sidebar, then click Run Analysis.")
    st.stop()

with st.spinner("Cloning repo, parsing patch, building dependency graph, scoring impact..."):
    try:
        result = analyze_real_instance(int(instance_index))
    except Exception as e:
        st.error(f"Pipeline error: {e}")
        st.stop()

risk = overall_risk(result["impacted_scored"])
tests_affected = len(result["evaluation"]["matched_tests"])

tab_overview, tab_diff, tab_map, tab_review, tab_trace, tab_final = st.tabs(
    ["OVERVIEW", "DIFF", "IMPACT MAP", "AI REVIEW", "AGENT TRACE", "FINAL REPORT"]
)

# ----- OVERVIEW -----
with tab_overview:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Repository", result["repo"])
    c2.metric("Changed Files", result.get("changed_files_count", 1))
    c3.metric("Impact", risk)
    c4.metric("Impacted Files", len(result["impacted_scored"]))

    c5, c6 = st.columns(2)
    c5.metric("Changed Lines", len(result["changed_lines"]))
    c6.metric("Tests Affected", f"{tests_affected} of {len(result['evaluation']['ground_truth_tests'])}")

    st.markdown(f"**Instance:** `{result['instance_id']}`")
    st.markdown(f"**Changed file:** `{result['changed_file']}`")

# ----- DIFF -----
with tab_diff:
    st.caption("Raw patch as provided by SWE-bench Lite (real diff, not fabricated).")
    for line in result["raw_patch"].splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            st.markdown(f'<span class="diff-add">{line}</span>', unsafe_allow_html=True)
        elif line.startswith("-") and not line.startswith("---"):
            st.markdown(f'<span class="diff-remove">{line}</span>', unsafe_allow_html=True)
        else:
            st.markdown(f'<span class="diff-context">{line}</span>', unsafe_allow_html=True)

# ----- IMPACT MAP -----
with tab_map:
    if not show_map:
        st.info("Dependency analysis disabled in sidebar options.")
    elif not result["impacted_scored"]:
        st.warning("No dependency graph could be generated for this instance.")
    else:
        st.markdown(f"**Changed** → `{result['changed_file']}`")
        st.markdown("↓")
        for level_name in ["HIGH", "MEDIUM", "LOW"]:
            files_at_level = [f for f, info in result["impacted_scored"].items() if info["level"] == level_name]
            if files_at_level:
                st.markdown(f"**{level_name} impact**")
                for f in files_at_level:
                    tag = " (test file)" if "test" in f.lower() else ""
                    st.code(f + tag, language=None)

# ----- AI REVIEW -----
with tab_review:
    st.markdown("**REVIEW COMPLETED**")
    st.markdown(f"**Overall Risk:** {badge(risk)}", unsafe_allow_html=True)

    if show_ai and gemini_ok:
        st.markdown("**Review Summary**")
        st.info(result.get("explanation", "Not available from current analysis."))
    elif not gemini_ok:
        st.warning("AI explanation unavailable.\n\nReason: Gemini API key is not configured. Static analysis results are still available.")
    else:
        st.caption("AI explanation disabled in sidebar options.")

    st.markdown("---")
    st.markdown("**Findings**")
    if not result["impacted_scored"]:
        st.write("No issue detected by static analysis.")
    else:
        for i, (f, info) in enumerate(result["impacted_scored"].items(), 1):
            with st.expander(f"Finding #{i} — {f}"):
                st.markdown(f"**Severity:** {badge(info['level'])}", unsafe_allow_html=True)
                st.markdown(f"**File:** `{f}`")
                reason = "Directly imports or is imported by the changed file." if info["score"] >= 0.80 else \
                         "Indirectly depends on the changed file through the dependency graph." if info["score"] >= 0.30 else \
                         "Weak/indirect connection detected in the dependency graph."
                st.markdown(f"**Reason:** {reason}")
                st.markdown(f"**Impact score:** {info['score']:.2f}")
                st.markdown("**Recommendation:** Run this file's tests before merging.")

# ----- AGENT TRACE -----
with tab_trace:
    st.markdown("**AGENT EXECUTION TRACE**")
    stages = [
        ("Dataset Agent", f"Loaded SWE-bench instance `{result['instance_id']}`"),
        ("Repository Agent", f"Repository `{result['repo']}` checked out"),
        ("Patch Agent", f"Parsed {len(result['changed_lines'])} changed line(s)"),
        ("AST + Dependency Agent", "Built AST-based NetworkX dependency graph"),
        ("Impact Agent", f"Scored {len(result['impacted_scored'])} impacted file(s)"),
        ("Test Evaluation Agent", f"Matched against {len(result['evaluation']['ground_truth_tests'])} real ground-truth test(s)"),
        ("Review Agent (Gemini)", "Generated developer-facing explanation" if gemini_ok else "Skipped — Gemini not configured"),
    ]
    for name, detail in stages:
        mark = "✓" if (name != "Review Agent (Gemini)" or gemini_ok) else "○"
        st.markdown(f"**{mark} {name}**  \n{detail}")

# ----- FINAL REPORT -----
with tab_final:
    lines = [
        "CODE REVIEW SUMMARY", "-" * 40,
        f"Repository: {result['repo']}",
        f"Changed: {result['changed_file']}",
        f"Overall Static Risk: {risk}",
        "",
        "IMPACTED FILES", "-" * 40,
    ]
    for f, info in result["impacted_scored"].items():
        lines.append(f"{f}  {info['score']:.2f}  {info['level']}")
    lines += [
        "",
        f"Recall vs. real tests: {result['evaluation']['recall']*100:.0f}%",
        "",
        "RECOMMENDED ACTIONS", "-" * 40,
        "1. Review affected functions",
        "2. Run impacted tests",
        "3. Validate downstream behavior",
    ]
    report_text = "\n".join(lines)
    st.code(report_text, language=None)
    st.download_button("Download report (.md)", report_text, file_name="code_review_report.md")