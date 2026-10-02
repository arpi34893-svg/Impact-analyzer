"""
ui_components.py - presentation-only helpers for the Agentic Code Reviewer.

Contains NO analysis logic and NO data: every function renders exactly what the caller passes in.
Only dependency: streamlit. Safe on Streamlit Community Cloud (no local paths, no secrets).
"""
from __future__ import annotations

import html
from typing import Iterable, Optional, Sequence

import streamlit as st

STAGES = ["Repository", "Parse", "AST Analysis", "Dependency Analysis", "Impact Scoring", "AI Review", "Report"]

_TONES = {"high", "medium", "low", "ok", "info", "neutral"}

_CSS = """
<style>
.stApp{background:#0d1117}
.block-container{padding-top:2rem;padding-bottom:3rem;max-width:1200px}
header[data-testid="stHeader"]{background:transparent}
section[data-testid="stSidebar"]{background:#0b0f14;border-right:1px solid #21262d}
section[data-testid="stSidebar"] [role="radiogroup"] label{background:#11161d;border:1px solid #21262d;border-radius:8px;padding:8px 10px;margin-bottom:6px}
section[data-testid="stSidebar"] [role="radiogroup"] label:hover{border-color:#30363d}
.stTabs [data-baseweb="tab-list"]{gap:4px;border-bottom:1px solid #21262d}
.stTabs [data-baseweb="tab"]{padding:8px 14px;color:#8b949e}
.stTabs [aria-selected="true"]{color:#e6edf3}
.stButton>button[kind="primary"]{border-radius:8px;font-weight:600}
.stButton>button,.stDownloadButton>button{border-radius:8px}
.cr-hero{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;padding-bottom:16px;margin-bottom:18px;border-bottom:1px solid #21262d}
.cr-title{font-size:1.65rem;font-weight:650;letter-spacing:-.01em;color:#e6edf3;line-height:1.2}
.cr-sub{margin-top:4px;color:#8b949e;font-size:.95rem}
.cr-status{display:inline-flex;align-items:center;gap:8px;border:1px solid #21262d;border-radius:999px;padding:4px 12px;font-size:.8rem;color:#c9d1d9;background:#11161d}
.cr-dot{width:8px;height:8px;border-radius:50%;background:#8b949e;display:inline-block}
.cr-dot.ok{background:#3fb950}.cr-dot.high{background:#f85149}.cr-dot.info{background:#58a6ff}.cr-dot.medium{background:#d29922}
.cr-sec{margin:22px 0 10px}.cr-sec b{font-size:1.02rem;color:#e6edf3;font-weight:600}.cr-sec span{display:block;color:#8b949e;font-size:.85rem;margin-top:2px}
.cr-chips{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 16px}
.cr-chip{display:inline-flex;align-items:center;gap:7px;border:1px solid #21262d;background:#11161d;border-radius:999px;padding:3px 11px;font-size:.78rem;color:#c9d1d9}
.cr-kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin-bottom:6px}
.cr-kpi{background:#161b22;border:1px solid #21262d;border-radius:10px;padding:14px 16px;min-width:0}
.cr-kl{color:#8b949e;font-size:.78rem;margin-bottom:6px}
.cr-kv{font-size:1.55rem;font-weight:600;color:#e6edf3;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cr-kh{color:#8b949e;font-size:.76rem;margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cr-kv.high{color:#f85149}.cr-kv.medium{color:#d29922}.cr-kv.low,.cr-kv.ok{color:#3fb950}.cr-kv.info{color:#58a6ff}
.cr-badge{display:inline-block;padding:1px 9px;border-radius:999px;font-size:.72rem;font-weight:600;border:1px solid #30363d;color:#8b949e}
.cr-badge.high{color:#f85149;border-color:#f8514966;background:#f851490f}
.cr-badge.medium{color:#d29922;border-color:#d2992266;background:#d299220f}
.cr-badge.low,.cr-badge.ok{color:#3fb950;border-color:#3fb95066;background:#3fb9500f}
.cr-badge.info{color:#58a6ff;border-color:#58a6ff66;background:#58a6ff0f}
.cr-rows{border:1px solid #21262d;border-radius:10px;overflow:hidden;background:#11161d}
.cr-row{display:grid;grid-template-columns:minmax(0,1fr) auto 46px 120px;gap:12px;align-items:center;padding:10px 14px;border-bottom:1px solid #1b222c}
.cr-row:last-child{border-bottom:0}
.cr-file{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:.84rem;color:#e6edf3;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cr-score{font-variant-numeric:tabular-nums;color:#c9d1d9;font-size:.84rem;text-align:right}
.cr-bar{height:6px;border-radius:3px;background:#21262d;overflow:hidden}.cr-bar i{display:block;height:100%;background:#58a6ff}
.cr-why{grid-column:1/-1;color:#8b949e;font-size:.8rem;margin-top:-4px}
.cr-tl{display:flex;flex-wrap:wrap;gap:8px;margin:4px 0 12px}
.cr-step{display:inline-flex;align-items:center;gap:8px;border:1px solid #21262d;border-radius:8px;padding:6px 12px;font-size:.8rem;color:#6e7681;background:#0d1117}
.cr-step em{font-style:normal;width:18px;height:18px;border-radius:50%;border:1px solid #30363d;display:grid;place-items:center;font-size:.68rem}
.cr-step.done{color:#c9d1d9}.cr-step.done em{background:#3fb950;border-color:#3fb950;color:#04130a}
.cr-step.active{color:#e6edf3;border-color:#58a6ff}.cr-step.active em{border-color:#58a6ff;color:#58a6ff}
.cr-step.failed{color:#f85149;border-color:#f8514966}.cr-step.failed em{background:#f85149;border-color:#f85149;color:#1a0505}
.cr-empty{border:1px dashed #30363d;border-radius:12px;padding:40px 24px;text-align:center;background:#0f141b}
.cr-empty b{display:block;font-size:1.1rem;color:#e6edf3;margin-bottom:6px}.cr-empty span{color:#8b949e;font-size:.92rem}
.cr-err{border:1px solid #f8514966;background:#f851490f;border-radius:10px;padding:14px 16px;margin:8px 0}
.cr-err b{color:#f85149}.cr-err p{margin:6px 0 0;color:#c9d1d9;font-size:.9rem}
.cr-err details{margin-top:8px;color:#8b949e;font-size:.8rem}.cr-err pre{white-space:pre-wrap;word-break:break-word;margin:6px 0 0;color:#8b949e}
section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked){border-color:#2f81f7;background:#10233f}
section[data-testid="stSidebar"] .stButton>button,[data-testid="stFormSubmitButton"] button,[data-testid="stForm"] .stButton>button{width:100%}
.cr-bar i.high{background:#f85149}.cr-bar i.medium{background:#d29922}.cr-bar i.low{background:#3fb950}
.cr-step.skipped{border-style:dashed;color:#6e7681}.cr-step.skipped em{border-style:dashed}
.cr-diff{border:1px solid #21262d;border-radius:10px;overflow:auto;background:#0d1117;max-height:520px;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:.8rem;padding:6px 0}
.cr-ln{white-space:pre;padding:1px 12px;color:#8b949e;min-width:max-content}
.cr-ln.add{background:#0f2418;color:#3fb950}.cr-ln.del{background:#2d1214;color:#f85149}.cr-ln.hunk{color:#58a6ff;background:#0f1b2d}
@media (max-width:640px){.block-container{padding:1rem .9rem 2rem}.cr-row{grid-template-columns:minmax(0,1fr) auto 46px}.cr-bar{display:none}.cr-title{font-size:1.3rem}}
</style>
"""


def _e(value) -> str:
    return html.escape(str(value), quote=True).replace("$", "&#36;")


def _tone(tone: Optional[str]) -> str:
    return tone if tone in _TONES else "neutral"


def _html(markup: str) -> None:
    # Flatten so Markdown never treats indented HTML as a code block.
    st.markdown(" ".join(line.strip() for line in markup.splitlines() if line.strip()), unsafe_allow_html=True)


def inject_css() -> None:
    """Call once, right after st.set_page_config()."""
    st.markdown(_CSS, unsafe_allow_html=True)


def tone_for_level(level: Optional[str]) -> str:
    """Map a level label produced by YOUR pipeline (HIGH/MEDIUM/LOW) to a display tone."""
    return {"HIGH": "high", "MEDIUM": "medium", "LOW": "low"}.get(str(level or "").strip().upper(), "neutral")


def badge(text: str, tone: str = "neutral") -> str:
    """Returns an HTML badge string (for use inside other helpers)."""
    return f'<span class="cr-badge {_tone(tone)}">{_e(text)}</span>'


def hero(title: str, subtitle: str, status: str = "Ready", status_tone: str = "ok") -> None:
    _html(f'<div class="cr-hero"><div><div class="cr-title">{_e(title)}</div><div class="cr-sub">{_e(subtitle)}</div></div>'
          f'<div class="cr-status"><span class="cr-dot {_tone(status_tone)}"></span>{_e(status)}</div></div>')


def section(title: str, subtitle: str = "") -> None:
    sub = f"<span>{_e(subtitle)}</span>" if subtitle else ""
    _html(f'<div class="cr-sec"><b>{_e(title)}</b>{sub}</div>')


def chips(items: Iterable[tuple]) -> None:
    """items: (label, ok) pairs, e.g. [("Gemini", True), ("ML model (not trained)", False)]. Green = on, grey = off."""
    out = "".join(f'<span class="cr-chip"><span class="cr-dot {"ok" if ok else ""}"></span>{_e(label)}</span>'
                  for label, ok in items)
    if out:
        _html(f'<div class="cr-chips">{out}</div>')


def kpi_grid(items: Sequence[tuple]) -> None:
    """items: (label, value[, hint[, tone]]). Long values are ellipsized, grid wraps on small screens."""
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
    """
    rows: dicts with 'file' (str), 'score' (float 0-1), optional 'level' (str) and 'reason' (str).
    The level badge appears only if YOUR pipeline supplies 'level'; nothing is derived here.
    """
    out = []
    for r in rows:
        try:
            score = float(r.get("score"))
        except (TypeError, ValueError):
            score = None
        pct = 0 if score is None else max(0, min(100, round(score * 100)))
        level = r.get("level")
        b = badge(str(level).upper(), tone_for_level(level)) if level else "<span></span>"
        score_txt = "-" if score is None else f"{score:.2f}"
        why = f'<div class="cr-why">{_e(r["reason"])}</div>' if r.get("reason") else ""
        out.append(f'<div class="cr-row"><div class="cr-file" title="{_e(r.get("file", ""))}">{_e(r.get("file", ""))}</div>'
                   f'{b}<div class="cr-score">{score_txt}</div><div class="cr-bar"><i class="{tone_for_level(level)}" style="width:{pct}%"></i></div>{why}</div>')
    if out:
        _html(f'<div class="cr-rows">{"".join(out)}</div>')


def pipeline_timeline(stages: Sequence[str] = STAGES, done: int = 0, failed_at: Optional[int] = None,
                      skipped: Sequence[int] = ()) -> None:
    """done = number of completed stages (len(stages) = all finished); failed_at = failed stage index;
    skipped = indices of stages that did not run (e.g. AI review disabled)."""
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
    hint_html = f"<p>{_e(hint)}</p>" if hint else ""
    detail_html = f"<details><summary>Technical details</summary><pre>{_e(detail)}</pre></details>" if detail else ""
    _html(f'<div class="cr-err"><b>{_e(title)}</b><p>{_e(message)}</p>{hint_html}{detail_html}</div>')


def code_diff(patch: str, max_lines: int = 600) -> None:
    """Renders a unified diff as ONE escaped HTML block (fast, and safe for code containing < > & $)."""
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