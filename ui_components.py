"""
ui_components.py - Senior Developer Design System & Matrix Visualizers
for the Agentic Code Reviewer in Vibrant Dark Violet Palette.
"""
from __future__ import annotations

import html
from typing import Iterable, Optional, Sequence, Dict, Any, List

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

STAGES = ["Repository", "Parse", "AST Analysis", "Dependency Analysis", "Impact Scoring", "AI Review", "Report"]

_TONES = {"high", "medium", "low", "ok", "info", "neutral"}

_VIBRANT_VIOLET_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

/* Global Reset & Base */
html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
}

code, pre, .mono, [class*="stCode"] {
    font-family: 'JetBrains Mono', monospace !important;
}

.stApp {
    background: radial-gradient(circle at 50% -10%, #221245 0%, #0d071c 55%, #07030e 100%) !important;
    color: #f1f5f9;
}

.block-container {
    padding-top: 1rem !important;
    padding-bottom: 3rem !important;
    max-width: 1360px !important;
}

header[data-testid="stHeader"] {
    background: transparent !important;
}

/* Sidebar styling - Dark Obsidian Violet */
section[data-testid="stSidebar"] {
    background: rgba(12, 7, 24, 0.96) !important;
    border-right: 1px solid rgba(168, 85, 247, 0.2) !important;
    backdrop-filter: blur(20px);
}

section[data-testid="stSidebar"] [role="radiogroup"] label {
    background: rgba(26, 15, 52, 0.6);
    border: 1px solid rgba(168, 85, 247, 0.12);
    border-radius: 10px;
    padding: 10px 14px;
    margin-bottom: 8px;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

section[data-testid="stSidebar"] [role="radiogroup"] label:hover {
    border-color: rgba(168, 85, 247, 0.6);
    background: rgba(43, 24, 86, 0.85);
    transform: translateX(4px);
}

section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
    border-color: #a855f7 !important;
    background: linear-gradient(135deg, rgba(168, 85, 247, 0.3) 0%, rgba(124, 58, 237, 0.2) 100%) !important;
    box-shadow: 0 0 20px rgba(168, 85, 247, 0.35);
}

/* Primary and Standard Buttons with Electric Violet */
.stButton > button, .stDownloadButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    transition: all 0.2s ease !important;
    border: 1px solid rgba(168, 85, 247, 0.25) !important;
    background: rgba(29, 17, 60, 0.8) !important;
    color: #f1f5f9 !important;
}

.stButton > button:hover, .stDownloadButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(168, 85, 247, 0.4) !important;
    border-color: #a855f7 !important;
    background: rgba(45, 25, 95, 0.9) !important;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 50%, #6d28d9 100%) !important;
    border: none !important;
    color: #ffffff !important;
    box-shadow: 0 4px 22px rgba(139, 92, 246, 0.5) !important;
}

.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #a855f7 0%, #8b5cf6 50%, #7c3aed 100%) !important;
    box-shadow: 0 6px 28px rgba(168, 85, 247, 0.7) !important;
    transform: translateY(-2px) !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    border-bottom: 1px solid rgba(168, 85, 247, 0.2);
    padding-bottom: 4px;
}

.stTabs [data-baseweb="tab"] {
    padding: 10px 18px !important;
    color: #a78bfa !important;
    font-weight: 500 !important;
    border-radius: 8px !important;
    transition: all 0.2s ease;
}

.stTabs [data-baseweb="tab"]:hover {
    color: #ffffff !important;
    background: rgba(168, 85, 247, 0.12);
}

.stTabs [aria-selected="true"] {
    color: #ffffff !important;
    font-weight: 700 !important;
    background: rgba(168, 85, 247, 0.22) !important;
    border-bottom: 2px solid #a855f7 !important;
}

/* App Navbar / Header */
.cr-nav-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 20px;
    background: rgba(22, 12, 46, 0.85);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(168, 85, 247, 0.25);
    border-radius: 14px;
    margin-bottom: 20px;
    box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5), 0 0 15px rgba(139, 92, 246, 0.15);
}

.cr-brand {
    display: flex;
    align-items: center;
    gap: 12px;
}

.cr-logo-icon {
    width: 36px;
    height: 36px;
    background: linear-gradient(135deg, #a855f7 0%, #ec4899 100%);
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    font-size: 1.15rem;
    color: #ffffff;
    box-shadow: 0 0 18px rgba(168, 85, 247, 0.6);
}

.cr-brand-name {
    font-weight: 800;
    font-size: 1.25rem;
    letter-spacing: -0.02em;
    color: #ffffff;
}

.cr-brand-tag {
    font-size: 0.72rem;
    font-weight: 600;
    padding: 3px 8px;
    background: rgba(168, 85, 247, 0.2);
    border: 1px solid rgba(168, 85, 247, 0.45);
    border-radius: 6px;
    color: #d8b4fe;
    margin-left: 6px;
}

.cr-nav-pills {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}

.cr-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.76rem;
    padding: 4px 10px;
    border-radius: 999px;
    border: 1px solid rgba(168, 85, 247, 0.2);
    background: rgba(36, 19, 74, 0.6);
    color: #e2e8f0;
}

.cr-pulse-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #10b981;
    box-shadow: 0 0 8px #10b981;
    display: inline-block;
    animation: pulseGlow 2s infinite ease-in-out;
}

@keyframes pulseGlow {
    0%, 100% { opacity: 0.4; transform: scale(0.9); }
    50% { opacity: 1; transform: scale(1.15); }
}

.cr-pulse-dot.amber { background: #f59e0b; box-shadow: 0 0 8px #f59e0b; }
.cr-pulse-dot.rose { background: #f43f5e; box-shadow: 0 0 8px #f43f5e; }
.cr-pulse-dot.indigo { background: #a855f7; box-shadow: 0 0 8px #a855f7; }

/* Front Page Hero - Clean Executive Styling (No decorative curves) */
.cr-welcome-hero {
    position: relative;
    padding: 24px 28px;
    background: linear-gradient(135deg, rgba(34, 18, 70, 0.7) 0%, rgba(20, 10, 42, 0.85) 60%, rgba(13, 7, 28, 0.95) 100%);
    border: 1px solid rgba(168, 85, 247, 0.25);
    border-radius: 14px;
    margin-bottom: 20px;
    box-shadow: 0 12px 30px -10px rgba(0, 0, 0, 0.5);
}

.cr-welcome-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 0.78rem;
    font-weight: 600;
    color: #d8b4fe;
    background: rgba(168, 85, 247, 0.16);
    border: 1px solid rgba(168, 85, 247, 0.35);
    padding: 3px 10px;
    border-radius: 999px;
    margin-bottom: 10px;
}

.cr-welcome-title {
    font-size: 2.1rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    line-height: 1.15;
    margin-bottom: 8px;
    color: #ffffff;
}

.cr-gradient-text {
    background: linear-gradient(135deg, #ffffff 0%, #e9d5ff 40%, #c084fc 70%, #a855f7 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.cr-welcome-sub {
    font-size: 0.96rem;
    color: #cbd5e1;
    max-width: 900px;
    line-height: 1.55;
    margin-bottom: 0;
}

/* Feature Launchpad Cards */
.cr-launchpad {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
}

.cr-card {
    background: rgba(25, 14, 53, 0.72);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(168, 85, 247, 0.2);
    border-radius: 14px;
    padding: 22px;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
}

.cr-card:hover {
    transform: translateY(-4px);
    border-color: rgba(168, 85, 247, 0.6);
    box-shadow: 0 12px 30px -8px rgba(168, 85, 247, 0.35);
    background: rgba(36, 19, 74, 0.85);
}

.cr-card-icon {
    font-size: 1.65rem;
    margin-bottom: 12px;
    display: inline-block;
}

.cr-card-title {
    font-size: 1.12rem;
    font-weight: 700;
    color: #ffffff;
    margin-bottom: 6px;
}

.cr-card-desc {
    font-size: 0.86rem;
    color: #cbd5e1;
    line-height: 1.5;
    margin-bottom: 14px;
}

.cr-card-badge {
    display: inline-block;
    font-size: 0.74rem;
    font-weight: 600;
    padding: 3px 9px;
    border-radius: 6px;
    background: rgba(168, 85, 247, 0.16);
    border: 1px solid rgba(168, 85, 247, 0.35);
    color: #d8b4fe;
}

/* Live KPI Grid */
.cr-kpis {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px;
    margin-bottom: 18px;
}

.cr-kpi {
    background: rgba(25, 14, 53, 0.75);
    backdrop-filter: blur(14px);
    border: 1px solid rgba(168, 85, 247, 0.18);
    border-radius: 12px;
    padding: 16px 18px;
    transition: all 0.2s ease;
}

.cr-kpi:hover {
    border-color: rgba(168, 85, 247, 0.45);
    background: rgba(36, 19, 74, 0.85);
    transform: translateY(-2px);
}

.cr-kl {
    font-size: 0.74rem;
    font-weight: 600;
    color: #a78bfa;
    margin-bottom: 5px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.cr-kv {
    font-size: 1.65rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: #ffffff;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.cr-kh {
    font-size: 0.74rem;
    color: #94a3b8;
    margin-top: 4px;
}

.cr-kv.high { color: #f43f5e; }
.cr-kv.medium { color: #f59e0b; }
.cr-kv.low, .cr-kv.ok { color: #10b981; }
.cr-kv.info { color: #38bdf8; }

/* Section Header - Clean, No Distracting Divider Lines */
.cr-sec {
    margin: 22px 0 10px;
}

.cr-sec b {
    font-size: 1.18rem;
    font-weight: 750;
    color: #ffffff;
    letter-spacing: -0.01em;
}

.cr-sec span {
    display: block;
    color: #a78bfa;
    font-size: 0.86rem;
    margin-top: 3px;
}

/* Badges */
.cr-badge {
    display: inline-flex;
    align-items: center;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 0.74rem;
    font-weight: 700;
    letter-spacing: 0.03em;
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #94a3b8;
    background: rgba(255, 255, 255, 0.04);
}

.cr-badge.high {
    color: #fda4af;
    border-color: rgba(244, 63, 94, 0.5);
    background: rgba(244, 63, 94, 0.15);
    box-shadow: 0 0 12px rgba(244, 63, 94, 0.25);
}

.cr-badge.medium {
    color: #fde047;
    border-color: rgba(245, 158, 11, 0.5);
    background: rgba(245, 158, 11, 0.15);
    box-shadow: 0 0 12px rgba(245, 158, 11, 0.25);
}

.cr-badge.low, .cr-badge.ok {
    color: #86efac;
    border-color: rgba(16, 185, 129, 0.5);
    background: rgba(16, 185, 129, 0.15);
    box-shadow: 0 0 12px rgba(16, 185, 129, 0.25);
}

.cr-badge.info {
    color: #7dd3fc;
    border-color: rgba(56, 189, 248, 0.5);
    background: rgba(56, 189, 248, 0.15);
}

/* Ranked File Cards */
.cr-file-card {
    background: rgba(24, 14, 51, 0.7);
    backdrop-filter: blur(14px);
    border: 1px solid rgba(168, 85, 247, 0.2);
    border-radius: 12px;
    padding: 14px 18px;
    margin-bottom: 10px;
    transition: all 0.2s ease;
}

.cr-file-card:hover {
    border-color: rgba(168, 85, 247, 0.5);
    background: rgba(35, 19, 73, 0.85);
    transform: translateX(3px);
}

.cr-file-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 8px;
}

.cr-file-name {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
    font-weight: 600;
    color: #ffffff;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.cr-score-bar-bg {
    height: 6px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.08);
    overflow: hidden;
    margin: 8px 0;
}

.cr-score-bar-fill {
    height: 100%;
    border-radius: 999px;
    transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.cr-score-bar-fill.high { background: linear-gradient(90deg, #f43f5e 0%, #fb7185 100%); }
.cr-score-bar-fill.medium { background: linear-gradient(90deg, #f59e0b 0%, #fbbf24 100%); }
.cr-score-bar-fill.low { background: linear-gradient(90deg, #10b981 0%, #34d399 100%); }

.cr-file-reason {
    font-size: 0.82rem;
    color: #cbd5e1;
    line-height: 1.45;
}

/* Agent Architecture Flow */
.cr-agent-flow {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px;
    margin: 16px 0;
}

.cr-agent-card {
    background: rgba(22, 12, 47, 0.8);
    border: 1px solid rgba(168, 85, 247, 0.2);
    border-radius: 12px;
    padding: 16px;
    position: relative;
    transition: all 0.2s ease;
}

.cr-agent-card:hover {
    border-color: rgba(168, 85, 247, 0.55);
    background: rgba(35, 18, 73, 0.9);
    transform: translateY(-2px);
}

.cr-agent-num {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    font-weight: 700;
    color: #c084fc;
    margin-bottom: 6px;
}

.cr-agent-title {
    font-size: 0.94rem;
    font-weight: 750;
    color: #ffffff;
    margin-bottom: 4px;
}

.cr-agent-desc {
    font-size: 0.8rem;
    color: #cbd5e1;
    line-height: 1.4;
}

/* Pipeline timeline */
.cr-tl {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 8px 0 14px;
}

.cr-step {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    border: 1px solid rgba(168, 85, 247, 0.2);
    border-radius: 999px;
    padding: 5px 13px;
    font-size: 0.78rem;
    color: #a78bfa;
    background: rgba(25, 14, 53, 0.6);
}

.cr-step em {
    font-style: normal;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    border: 1px solid rgba(168, 85, 247, 0.3);
    display: grid;
    place-items: center;
    font-size: 0.7rem;
}

.cr-step.done {
    color: #ffffff;
    border-color: rgba(16, 185, 129, 0.5);
    background: rgba(16, 185, 129, 0.12);
}

.cr-step.done em {
    background: #10b981;
    border-color: #10b981;
    color: #022c22;
    font-weight: 800;
}

.cr-step.active {
    color: #ffffff;
    border-color: #a855f7;
    background: rgba(168, 85, 247, 0.22);
}

.cr-step.active em {
    border-color: #a855f7;
    color: #e9d5ff;
}

/* Diff viewer */
.cr-diff {
    border: 1px solid rgba(168, 85, 247, 0.2);
    border-radius: 12px;
    overflow: auto;
    background: #090414;
    max-height: 520px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
    padding: 8px 0;
}

.cr-ln {
    white-space: pre;
    padding: 2px 14px;
    color: #94a3b8;
    min-width: max-content;
}

.cr-ln.add { background: rgba(16, 185, 129, 0.16); color: #86efac; }
.cr-ln.del { background: rgba(244, 63, 94, 0.16); color: #fda4af; }
.cr-ln.hunk { color: #38bdf8; background: rgba(56, 189, 248, 0.12); }

/* Empty state */
.cr-empty {
    border: 1px dashed rgba(168, 85, 247, 0.25);
    border-radius: 16px;
    padding: 44px 24px;
    text-align: center;
    background: rgba(24, 13, 51, 0.4);
    margin: 18px 0;
}

.cr-empty b {
    display: block;
    font-size: 1.15rem;
    color: #ffffff;
    margin-bottom: 6px;
}

.cr-empty span {
    color: #cbd5e1;
    font-size: 0.92rem;
}

/* Error state */
.cr-err {
    border: 1px solid rgba(244, 63, 94, 0.4);
    background: rgba(244, 63, 94, 0.1);
    border-radius: 12px;
    padding: 16px 20px;
    margin: 12px 0;
}

.cr-err b { color: #f43f5e; font-size: 1.05rem; }
.cr-err p { margin: 6px 0 0; color: #fecdd3; font-size: 0.92rem; }
.cr-err details { margin-top: 10px; color: #cbd5e1; font-size: 0.82rem; }
.cr-err pre { white-space: pre-wrap; word-break: break-word; color: #fda4af; }

/* Arrow Navigation Bar */
.cr-nav-banner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 20px;
    background: rgba(30, 16, 64, 0.6);
    border: 1px solid rgba(168, 85, 247, 0.25);
    border-radius: 12px;
    margin: 24px 0 10px;
}

.cr-nav-banner span {
    font-size: 0.9rem;
    color: #d8b4fe;
    font-weight: 500;
}

@media (max-width: 768px) {
    .cr-welcome-title { font-size: 1.85rem; }
    .cr-welcome-hero { padding: 24px 20px; }
}
</style>
"""


def _e(value) -> str:
    return html.escape(str(value), quote=True).replace("$", "&#36;")


def _tone(tone: Optional[str]) -> str:
    return tone if tone in _TONES else "neutral"


def _html(markup: str) -> None:
    st.markdown(" ".join(line.strip() for line in markup.splitlines() if line.strip()), unsafe_allow_html=True)


def inject_css() -> None:
    st.markdown(_VIBRANT_VIOLET_CSS, unsafe_allow_html=True)


def tone_for_level(level: Optional[str]) -> str:
    return {"HIGH": "high", "MEDIUM": "medium", "LOW": "low"}.get(str(level or "").strip().upper(), "neutral")


def badge(text: str, tone: str = "neutral") -> str:
    return f'<span class="cr-badge {_tone(tone)}">{_e(text)}</span>'


def app_navbar(
    model_ok: bool = True,
    gemini_ok: bool = False,
    repo_count: int = 19,
) -> None:
    """Renders sleek top SaaS header bar in dark violet theme."""
    gem_cls = "indigo" if gemini_ok else "amber"
    gem_label = "Gemini AI: Active" if gemini_ok else "Gemini: Not Configured"

    ml_cls = "pulse" if model_ok else "amber"
    ml_label = "RandomForest: Online" if model_ok else "ML: Missing"

    _html(f"""
    <div class="cr-nav-header">
        <div class="cr-brand">
            <div class="cr-logo-icon">◆</div>
            <div>
                <span class="cr-brand-name">Agentic Code Reviewer</span>
                <span class="cr-brand-tag">Production Grade</span>
            </div>
        </div>
        <div class="cr-nav-pills">
            <span class="cr-pill"><span class="cr-pulse-dot indigo"></span>AST Graph Engine</span>
            <span class="cr-pill"><span class="cr-pulse-dot {ml_cls}"></span>{ml_label}</span>
            <span class="cr-pill"><span class="cr-pulse-dot {gem_cls}"></span>{gem_label}</span>
            <span class="cr-pill"><span class="cr-pulse-dot indigo"></span>{repo_count} Local Repos</span>
        </div>
    </div>
    """)


def developer_welcome_hero() -> None:
    """Renders the exclusive front page hero for Agentic Code Reviewer."""
    _html("""
    <div class="cr-welcome-hero">
        <div class="cr-welcome-badge">
            <span class="cr-pulse-dot indigo"></span> Production Code Review Intelligence
        </div>
        <div class="cr-welcome-title">
            Agentic Code Reviewer & <span class="cr-gradient-text">Impact Analyzer</span>
        </div>
        <div class="cr-welcome-sub">
            Built for senior engineers and tech leads. Analyzes cross-module blast radius when Python files are modified
            using <b>deterministic AST dependency graphs</b>, <b>Random Forest co-change machine learning</b> (0.971 MRR),
            and <b>autonomous Multi-Agent reasoning</b>. Compute exact coupling matrices and isolate regressions before merging.
        </div>
    </div>
    """)


def render_launchpad_cards() -> None:
    """Renders interactive feature launchpad cards on the front page."""
    _html("""
    <div class="cr-launchpad">
        <div class="cr-card">
            <div class="cr-card-icon">📦</div>
            <div class="cr-card-title">Ingest & Analyze Repo</div>
            <div class="cr-card-desc">
                Upload a ZIP archive or pick from 19 local repositories. Select the exact modified module and inspect blast radius.
            </div>
            <span class="cr-card-badge">Live Coupling & Feature Matrices</span>
        </div>
        <div class="cr-card">
            <div class="cr-card-icon">🌐</div>
            <div class="cr-card-title">Live GitHub Explorer</div>
            <div class="cr-card-desc">
                Connect directly to any public GitHub repository. Clone, construct AST graphs, and score co-change probabilities.
            </div>
            <span class="cr-card-badge">Remote Git Cloner</span>
        </div>
        <div class="cr-card">
            <div class="cr-card-icon">🔬</div>
            <div class="cr-card-title">SWE-bench Benchmark Lab</div>
            <div class="cr-card-desc">
                Benchmark against real SWE-bench Lite production PRs and test suites. Calculates ground-truth confusion matrices.
            </div>
            <span class="cr-card-badge">Ground-Truth Test Oracle</span>
        </div>
        <div class="cr-card">
            <div class="cr-card-icon">📊</div>
            <div class="cr-card-title">Generalization & Matrix Lab</div>
            <div class="cr-card-desc">
                Inspect held-out generalization, Precision@K / Recall@K ablation studies, and Random Forest feature weights.
            </div>
            <span class="cr-card-badge">MRR 0.971 Verified</span>
        </div>
    </div>
    """)


def render_agent_architecture_flow() -> None:
    """Renders the 5 specialized agent pipeline cards."""
    _html("""
    <div class="cr-agent-flow">
        <div class="cr-agent-card">
            <div class="cr-agent-num">AGENT 01</div>
            <div class="cr-agent-title">📥 Ingestion & Patch Agent</div>
            <div class="cr-agent-desc">Unpacks archives, detects changed files, and parses line-level diff hunks.</div>
        </div>
        <div class="cr-agent-card">
            <div class="cr-agent-num">AGENT 02</div>
            <div class="cr-agent-title">🕸️ AST Graph Engine</div>
            <div class="cr-agent-desc">Builds NetworkX directed graphs from Python ASTs, resolving import dependencies.</div>
        </div>
        <div class="cr-agent-card">
            <div class="cr-agent-num">AGENT 03</div>
            <div class="cr-agent-title">🧠 Random Forest ML Agent</div>
            <div class="cr-agent-desc">Extracts 11 structural features and predicts co-change probabilities from real PR patterns.</div>
        </div>
        <div class="cr-agent-card">
            <div class="cr-agent-num">AGENT 04</div>
            <div class="cr-agent-title">🧪 Test Oracle Agent</div>
            <div class="cr-agent-desc">Identifies affected unit and integration test suites needing mandatory re-execution.</div>
        </div>
        <div class="cr-agent-card">
            <div class="cr-agent-num">AGENT 05</div>
            <div class="cr-agent-title">🤖 Gemini Synthesis Agent</div>
            <div class="cr-agent-desc">Generates plain-language architecture reviews, risk breakdowns, and PR audit summaries.</div>
        </div>
    </div>
    """)


def hero(title: str, subtitle: str, status: str = "Ready", status_tone: str = "ok") -> None:
    _html(f'<div class="cr-welcome-hero" style="padding:24px 28px;margin-bottom:18px;">'
          f'<div class="cr-welcome-badge"><span class="cr-pulse-dot {_tone(status_tone)}"></span>{_e(status)}</div>'
          f'<div class="cr-welcome-title" style="font-size:1.85rem;margin-bottom:6px;">{_e(title)}</div>'
          f'<div class="cr-welcome-sub" style="margin-bottom:0;font-size:0.95rem;">{_e(subtitle)}</div></div>')


def section(title: str, subtitle: str = "") -> None:
    sub = f"<span>{_e(subtitle)}</span>" if subtitle else ""
    _html(f'<div class="cr-sec"><b>{_e(title)}</b>{sub}</div>')


def chips(items: Iterable[tuple]) -> None:
    out = "".join(f'<span class="cr-pill"><span class="cr-pulse-dot {"" if ok else "amber"}"></span>{_e(label)}</span>'
                  for label, ok in items)
    if out:
        _html(f'<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px;">{out}</div>')


def kpi_grid(items: Sequence[tuple]) -> None:
    cards = []
    for it in items:
        label, value = it[0], it[1]
        hint = it[2] if len(it) > 2 and it[2] else ""
        tone = _tone(it[3]) if len(it) > 3 else "neutral"
        hint_html = f'<div class="cr-kh" title="{_e(hint)}">{_e(hint)}</div>' if hint else ""
        cards.append(f'<div class="cr-kpi"><div class="cr-kl">{_e(label)}</div>'
                     f'<div class="cr-kv {tone}" title="{_e(value)}">{_e(value)}</div>{hint_html}</div>')
    if cards:
        _html(f'<div class="cr-kpis">{"".join(cards)}</div>')


def ranked_files(rows: Iterable[dict]) -> None:
    """Renders ranked impacted files using dark violet glass cards."""
    cards = []
    for r in rows:
        try:
            score = float(r.get("score"))
        except (TypeError, ValueError):
            score = None
        pct = 0 if score is None else max(0, min(100, round(score * 100)))
        level = r.get("level") or "LOW"
        tone = tone_for_level(level)
        score_txt = "-" if score is None else f"{score:.2f} ({pct}%)"
        reason = r.get("reason", "")
        file_name = r.get("file", "")

        test_badge = '<span class="cr-badge info" style="margin-left:6px;">🧪 TEST SUITE</span>' if "test" in file_name.lower() else ""

        cards.append(f"""
        <div class="cr-file-card">
            <div class="cr-file-card-header">
                <span class="cr-file-name" title="{_e(file_name)}">{_e(file_name)} {test_badge}</span>
                <span class="cr-badge {tone}">{_e(level)} &bull; {score_txt}</span>
            </div>
            <div class="cr-score-bar-bg">
                <div class="cr-score-bar-fill {tone}" style="width: {pct}%;"></div>
            </div>
            <div class="cr-file-reason">{_e(reason)}</div>
        </div>
        """)
    if cards:
        _html(f'<div>{"".join(cards)}</div>')


def render_coupling_heatmap(matrix_data: Dict[str, Any]) -> go.Figure:
    """
    Renders an interactive Plotly Heatmap for the dependency coupling matrix in vibrant violet palette.
    """
    labels = matrix_data["labels"]
    matrix = matrix_data["matrix"]
    text_matrix = matrix_data["text_matrix"]

    colorscale = [
        [0.0, "#0b0717"],
        [0.2, "#241042"],
        [0.4, "#4c1d95"],
        [0.7, "#8b5cf6"],
        [1.0, "#f43f5e"],
    ]

    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=labels,
        y=labels,
        text=text_matrix,
        hovertemplate="<b>%{y}</b> &rarr; <b>%{x}</b><br>%{text}<extra></extra>",
        colorscale=colorscale,
        showscale=True,
        colorbar=dict(
            title=dict(text="Coupling Type", font=dict(color="#d8b4fe", size=11)),
            tickvals=[0, 0.5, 1, 2, 3],
            ticktext=["None", "2-Hop", "Imports", "Depended By", "Mutual"],
            tickfont=dict(color="#cbd5e1", size=10),
            len=0.8,
        )
    ))

    fig.update_layout(
        height=max(420, len(labels) * 32),
        margin=dict(t=30, b=50, l=150, r=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="JetBrains Mono, monospace", color="#cbd5e1", size=10),
        xaxis=dict(tickangle=-35, gridcolor="rgba(168,85,247,0.1)"),
        yaxis=dict(gridcolor="rgba(168,85,247,0.1)", autorange="reversed"),
    )
    return fig


def render_centrality_chart(centrality_df: pd.DataFrame) -> go.Figure:
    """
    Renders an interactive Plotly bar chart comparing topological graph metrics in violet theme.
    """
    df = centrality_df.head(10).copy()
    labels = [f.split("/")[-1] for f in df["Module"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="In-Degree (Dependents)",
        x=labels,
        y=df["In-Degree (Dependents)"],
        marker=dict(color="#a855f7"),
    ))
    fig.add_trace(go.Bar(
        name="Out-Degree (Imports)",
        x=labels,
        y=df["Out-Degree (Imports)"],
        marker=dict(color="#38bdf8"),
    ))
    fig.add_trace(go.Bar(
        name="Betweenness x10",
        x=labels,
        y=(df["Betweenness Centrality"] * 10).round(2),
        marker=dict(color="#f59e0b"),
    ))

    fig.update_layout(
        barmode="group",
        height=340,
        margin=dict(t=20, b=40, l=30, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans, sans-serif", color="#d8b4fe", size=11),
        legend=dict(orientation="h", y=1.15, x=0),
        xaxis=dict(gridcolor="rgba(168,85,247,0.08)"),
        yaxis=dict(gridcolor="rgba(168,85,247,0.1)"),
    )
    return fig


def render_feature_importance_figure(importances: Dict[str, float]) -> go.Figure:
    """
    Renders horizontal bar chart of feature weights from Random Forest model in violet/fuchsia gradient.
    """
    sorted_items = sorted(importances.items(), key=lambda x: x[1])
    cols = [k[0] for k in sorted_items]
    vals = [k[1] * 100 for k in sorted_items]

    fig = go.Figure(go.Bar(
        x=vals,
        y=cols,
        orientation="h",
        marker=dict(
            color=vals,
            colorscale=[[0, "#7c3aed"], [1, "#ec4899"]],
        ),
        text=[f"{v:.1f}%" for v in vals],
        textposition="outside",
        textfont=dict(color="#f1f5f9", size=10),
    ))

    fig.update_layout(
        height=320,
        margin=dict(t=10, b=20, l=130, r=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="JetBrains Mono, monospace", color="#d8b4fe", size=11),
        xaxis=dict(title="Feature Weight (%)", gridcolor="rgba(168,85,247,0.1)"),
        yaxis=dict(gridcolor="rgba(168,85,247,0.08)"),
    )
    return fig


def render_confusion_matrix_heatmap(cm_data: Dict[str, Any]) -> go.Figure:
    """
    Renders a 2x2 confusion matrix heatmap for benchmark evaluations in dark violet theme.
    """
    mat = cm_data["matrix_2x2"]
    x_labels = ["Predicted Affected", "Predicted Clean"]
    y_labels = ["Ground-Truth Affected", "Ground-Truth Clean"]

    fig = go.Figure(data=go.Heatmap(
        z=mat,
        x=x_labels,
        y=y_labels,
        text=[[f"TP: {mat[0][0]}", f"FN: {mat[0][1]}"], [f"FP: {mat[1][0]}", f"TN: {mat[1][1]}"]],
        texttemplate="%{text}",
        textfont=dict(size=14, color="#ffffff"),
        colorscale=[[0, "#130924"], [0.5, "#7c3aed"], [1, "#10b981"]],
        showscale=False,
    ))

    fig.update_layout(
        height=260,
        margin=dict(t=20, b=20, l=140, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans, sans-serif", color="#d8b4fe", size=11),
    )
    return fig


def radial_graph_figure(changed_file: str, scored: dict, top_n: int = 10) -> go.Figure:
    """Renders interactive radial dependency graph with vibrant glowing violet nodes."""
    import math

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

    colors = {"HIGH": "#f43f5e", "MEDIUM": "#f59e0b", "LOW": "#10b981"}

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=ex, y=ey, mode="lines",
        line=dict(color="rgba(168, 85, 247, 0.35)", width=1.6),
        hoverinfo="skip"
    ))

    fig.add_trace(go.Scatter(
        x=[pos[f][0] for f, _ in items],
        y=[pos[f][1] for f, _ in items],
        mode="markers+text",
        text=[f.split("/")[-1] for f, _ in items],
        textposition="top center",
        textfont=dict(family="JetBrains Mono, monospace", size=10, color="#d8b4fe"),
        marker=dict(
            size=22,
            color=[colors.get(i.get("level", "LOW"), "#10b981") for _, i in items],
            line=dict(width=2, color="#120826"),
        ),
        hovertext=[f"<b>{f}</b><br>Score: {i['score']:.2f}<br>Level: {i.get('level', '-')}" for f, i in items],
        hoverinfo="text",
    ))

    fig.add_trace(go.Scatter(
        x=[0], y=[0], mode="markers+text",
        text=[f"🎯 {changed_file.split('/')[-1]}"],
        textposition="bottom center",
        textfont=dict(family="JetBrains Mono, monospace", size=12, color="#ffffff"),
        marker=dict(size=30, color="#8b5cf6", line=dict(width=3, color="#ffffff")),
        hovertext=[f"🎯 Target Changed Module: {changed_file}"],
        hoverinfo="text",
    ))

    fig.update_layout(
        showlegend=False,
        height=400,
        margin=dict(t=15, b=15, l=15, r=15),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False, range=[-1.5, 1.5]),
        yaxis=dict(visible=False, range=[-1.5, 1.5]),
    )
    return fig


def pipeline_timeline(stages: Sequence[str] = STAGES, done: int = 0, failed_at: Optional[int] = None,
                      skipped: Sequence[int] = ()) -> None:
    steps = []
    for i, name in enumerate(stages):
        if i in skipped:
            state = "skipped"
        elif failed_at is not None and i == failed_at:
            state = "failed"
        elif i < done:
            state = "done"
        elif i == done and failed_at is None and done < len(stages):
            state = "active"
        else:
            state = "pending"
        mark = {"failed": "!", "done": "&#10003;", "skipped": "-"}.get(state, str(i + 1))
        steps.append(f'<span class="cr-step {state}"><em>{mark}</em>{_e(name)}</span>')
    _html(f'<div class="cr-tl">{"".join(steps)}</div>')


def empty_state(title: str, body: str) -> None:
    _html(f'<div class="cr-empty"><b>{_e(title)}</b><span>{_e(body)}</span></div>')


def error_state(title: str, message: str, hint: str = "", detail: str = "") -> None:
    hint_html = f"<p style='color:#d8b4fe;margin-top:6px;'>{_e(hint)}</p>" if hint else ""
    detail_html = f"<details><summary style='cursor:pointer;color:#a78bfa;'>Technical Details</summary><pre>{_e(detail)}</pre></details>" if detail else ""
    _html(f'<div class="cr-err"><b>{_e(title)}</b><p>{_e(message)}</p>{hint_html}{detail_html}</div>')


def code_diff(patch: str, max_lines: int = 600) -> None:
    lines = (patch or "").splitlines()
    if not lines:
        empty_state("No diff available", "This analysis did not include a patch.")
        return
    rows = []
    for ln in lines[:max_lines]:
        if ln.startswith("+") and not ln.startswith("+++"):
            cls = "add"
        elif ln.startswith("-") and not ln.startswith("---"):
            cls = "del"
        elif ln.startswith("@@"):
            cls = "hunk"
        else:
            cls = ""
        rows.append(f'<div class="cr-ln {cls}">{_e(ln) or "&nbsp;"}</div>')
    _html(f'<div class="cr-diff">{"".join(rows)}</div>')
    if len(lines) > max_lines:
        st.caption(f"Showing the first {max_lines} of {len(lines)} lines.")