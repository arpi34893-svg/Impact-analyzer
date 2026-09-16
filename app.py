import os
import streamlit as st
from agent_workflow import run_workflow, analyze_real_instance

st.set_page_config(page_title="Agentic Code Reviewer", page_icon="◆", layout="wide")

# ---------- Styling ----------
st.markdown("""
<style>
    .stApp { font-family: 'SFMono-Regular', Consolas, monospace; }
    .header-title { font-size: 1.6rem; font-weight: 700; margin-bottom: 0; }
    .header-sub { color: #8b949e; font-size: 0.9rem; margin-top: 2px; }
    .status-row { display: flex; gap: 18px; margin: 10px 0 20px 0; flex-wrap: wrap; }
    .status-dot { font-size: 0.82rem; color: #8b949e; }
    .status-on { color: #3fb950; }
    .status-off { color: #6e7681; }
    .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 14px 18px; }
    .badge-high { background:#3d1d1d; color:#f85149; padding:2px 10px; border-radius:4px; font-size:0.78rem; font-weight:600; }
    .badge-medium { background:#3d321a; color:#e3b341; padding:2px 10px; border-radius:4px; font-size:0.78rem; font-weight:600; }
    .badge-low { background:#132e21; color:#3fb950; padding:2px 10px; border-radius:4px; font-size:0.78rem; font-weight:600; }
    .diff-add { background:#0f2418; color:#3fb950; padding:1px 6px; font-family:monospace; display:block; white-space:pre; }
    .diff-remove { background:#2d1214; color:#f85149; padding:1px 6px; font-family:monospace; display:block; white-space:pre; }
    .diff-context { color:#8b949e; padding:1px 6px; font-family:monospace; display:block; white-space:pre; }
</style>
""", unsafe_allow_html=True)


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
st.markdown('<p class="header-title">AGENTIC CODE REVIEWER</p>', unsafe_allow_html=True)
st.markdown('<p class="header-sub">Repository-Level Change Impact Analysis</p>', unsafe_allow_html=True)

gemini_ok = bool(os.getenv("GEMINI_API_KEY"))
st.markdown(f"""
<div class="status-row">
  <span class="status-dot status-on">● Repository Connected</span>
  <span class="status-dot status-on">● SWE-bench Lite</span>
  <span class="status-dot status-on">● AST Analyzer</span>
  <span class="status-dot status-on">● NetworkX</span>
  <span class="status-dot status-on">● LangGraph</span>
  <span class="status-dot {'status-on' if gemini_ok else 'status-off'}">● Gemini {'' if gemini_ok else '(not configured)'}</span>
</div>
""", unsafe_allow_html=True)

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("**PROJECT**")
    st.caption("Dataset: SWE-bench/SWE-bench_Lite")
    st.caption("Source: Hugging Face")

    st.markdown("---")
    st.markdown("**ANALYSIS**")
    mode = st.radio("Mode", ["Toy demo (target_repo)", "Real SWE-bench instance"], label_visibility="collapsed")
    instance_index = None
    if mode == "Real SWE-bench instance":
        instance_index = st.number_input("Instance index", min_value=0, max_value=299, value=0)
    run_clicked = st.button("▶ Run Analysis", type="primary", use_container_width=True)

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