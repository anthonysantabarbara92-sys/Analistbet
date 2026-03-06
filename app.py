"""
QUANTUM FOOTBALL ANALYTICS v9.0
app.py — Interfaccia Streamlit
Fix principali vs v8:
  - Cache @st.cache_data con chiavi (team_home, team_away, league, season)
  - Debug panel: mostra quale API ha risposto per ogni dato
  - Session state reset completo ad ogni nuova ricerca
  - Retry automatico con exponential backoff su rate limit
  - Fonte dati visibile in ogni sezione
"""

import streamlit as st
import numpy as np
import pandas as pd
import time
import concurrent.futures
from datetime import datetime

from engine import (
    AdvancedEngine, TeamStats, H2HRecord,
    fetch_fd_stats, fetch_af_stats, fetch_understat_xg,
    fetch_clubelo, fetch_odds, fetch_injuries_tm,
    compute_edge, fair_odd, kelly_fraction,
    COMPETITIONS, LEAGUE_AVGS, COMP_FD,
)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="⚡ Quantum Football v9.0",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS dark premium
st.markdown("""
<style>
    /* Background */
    .stApp { background-color: #0e1117; color: #e0e0e0; }
    .main .block-container { padding: 1.5rem 2rem; max-width: 1400px; }

    /* Header card */
    .qf-header {
        background: linear-gradient(135deg, #1a1f2e 0%, #0d1b2a 100%);
        border: 1px solid #00d4ff33;
        border-radius: 16px;
        padding: 24px 32px;
        margin-bottom: 24px;
        text-align: center;
    }
    .qf-header h1 { color: #00d4ff; font-size: 2.2rem; margin: 0; letter-spacing: 2px; }
    .qf-header p  { color: #7a8fa6; font-size: 0.95rem; margin-top: 6px; }

    /* Metric cards */
    .metric-card {
        background: #1a1f2e;
        border: 1px solid #2a3347;
        border-radius: 12px;
        padding: 16px 20px;
        text-align: center;
    }
    .metric-card .label { color: #7a8fa6; font-size: 0.80rem; text-transform: uppercase; letter-spacing: 1px; }
    .metric-card .value { color: #ffffff; font-size: 1.8rem; font-weight: 700; margin: 4px 0; }
    .metric-card .sub   { color: #7a8fa6; font-size: 0.75rem; }

    /* Source badge */
    .source-ok   { background:#0d3321; color:#00e676; border:1px solid #00e676; padding:2px 8px; border-radius:12px; font-size:0.75rem; }
    .source-warn { background:#332b0d; color:#ffd600; border:1px solid #ffd600; padding:2px 8px; border-radius:12px; font-size:0.75rem; }
    .source-err  { background:#330d0d; color:#ff5252; border:1px solid #ff5252; padding:2px 8px; border-radius:12px; font-size:0.75rem; }

    /* Confidence bar */
    .conf-bar-wrap { background:#1a1f2e; border-radius:8px; padding:12px 16px; margin:8px 0; }
    .conf-label { font-size:0.85rem; color:#9ab; margin-bottom:6px; }
    .conf-bar { height:16px; border-radius:8px; transition: width 0.5s; }

    /* Market table */
    .mkt-row { display:flex; justify-content:space-between; align-items:center;
               border-bottom:1px solid #1e2535; padding:8px 0; }
    .mkt-name { color:#cdd; font-size:0.88rem; }
    .mkt-prob { color:#00d4ff; font-weight:600; font-size:0.92rem; }
    .mkt-odd  { color:#7a8fa6; font-size:0.82rem; }
    .edge-pos { color:#00e676; font-weight:600; }
    .edge-neg { color:#ff5252; font-weight:600; }
    .edge-neu { color:#7a8fa6; }

    /* Bet recommendation */
    .bet-card {
        border-radius:12px;
        padding:16px 20px;
        margin:8px 0;
    }
    .bet-best  { background:linear-gradient(135deg,#0d3321,#0d2a1a); border:1px solid #00e676; }
    .bet-value { background:linear-gradient(135deg,#1a1a0d,#2a2a0d); border:1px solid #ffd600; }
    .bet-long  { background:linear-gradient(135deg,#1a0d0d,#2a1010); border:1px solid #ff7043; }

    /* Traffic light */
    .tl-green  { color:#00e676; font-size:1.6rem; }
    .tl-yellow { color:#ffd600; font-size:1.6rem; }
    .tl-red    { color:#ff5252; font-size:1.6rem; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { background: #1a1f2e; border-radius:10px; }
    .stTabs [data-baseweb="tab"]      { color: #7a8fa6; }
    .stTabs [aria-selected="true"]    { color: #00d4ff; border-bottom: 2px solid #00d4ff; }

    /* Divider */
    hr { border-color: #1e2535; }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #0066cc, #004499);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 10px 24px;
    }
    .stButton > button:hover { background: linear-gradient(135deg, #0077ee, #0055bb); }

    /* Sidebar */
    section[data-testid="stSidebar"] { background: #0d1117; }

    /* Form score display */
    .form-w { color:#00e676; font-weight:700; }
    .form-d { color:#ffd600; font-weight:700; }
    .form-l { color:#ff5252; font-weight:700; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────

def init_state():
    defaults = {
        "step": "input",
        "raw": None,
        "result": None,
        "roi_bets": [],
        "history": [],
        "last_home": "",
        "last_away": "",
        "last_league": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset_all():
    """Reset completo session state."""
    keys_to_del = [k for k in st.session_state.keys()
                   if k not in ("roi_bets", "history")]
    for k in keys_to_del:
        del st.session_state[k]
    init_state()


# ─────────────────────────────────────────────
# CACHE FUNCTIONS — chiavi ESPLICITE per squadra
# ─────────────────────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def cached_fd_stats(fd_key: str, league: str, team_name: str, is_home: bool, season: int = 2024):
    """Cache specifica per (fd_key, league, team_name, is_home, season)."""
    return fetch_fd_stats(fd_key, league, team_name, is_home, season)


@st.cache_data(ttl=1800, show_spinner=False)
def cached_af_stats(af_key: str, league: str, team_name: str, season: int = 2024):
    """Cache specifica per (af_key, league, team_name, season)."""
    return fetch_af_stats(af_key, league, team_name, season)


@st.cache_data(ttl=1800, show_spinner=False)
def cached_understat(league: str, team_name: str, season: int = 2024):
    """Cache specifica per (league, team_name, season)."""
    return fetch_understat_xg(league, team_name, season)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_clubelo(team_name: str):
    """Cache specifica per team_name."""
    return fetch_clubelo(team_name)


@st.cache_data(ttl=900, show_spinner=False)
def cached_odds(odds_key: str, league: str, home_team: str, away_team: str):
    """Cache specifica per (odds_key, league, home_team, away_team)."""
    return fetch_odds(odds_key, league, home_team, away_team)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_injuries(team_name: str):
    """Cache specifica per team_name."""
    return fetch_injuries_tm(team_name)


# ─────────────────────────────────────────────
# FETCH PARALLELO con fallback trasparente
# ─────────────────────────────────────────────

def fetch_all_data(
    fd_key: str,
    af_key: str,
    odds_key: str,
    league: str,
    home_team: str,
    away_team: str,
    season: int = 2024,
) -> dict:
    """
    Lancia fetch parallelo di tutte le sorgenti.
    Ritorna dizionario con dati + metadati fonte.
    """
    sources_log = {}

    def _get_team_stats(team: str, is_home: bool) -> tuple[TeamStats, dict]:
        log = {}
        # 1) football-data.org
        stats, src1 = cached_fd_stats(fd_key, league, team, is_home, season)
        log["football_data"] = src1

        # 2) Se meno di 5 partite, prova API-Football
        if stats.n_matches < 5 and af_key:
            stats_af, src2 = cached_af_stats(af_key, league, team, season)
            log["api_football"] = src2
            if stats_af.n_matches >= stats.n_matches:
                stats = stats_af

        # 3) Understat xG reale (sovrascrive xG stimato)
        xg_data, src_us = cached_understat(league, team, season)
        log["understat"] = src_us
        if xg_data and stats.matches:
            for i, (xg, xga) in enumerate(xg_data[-len(stats.matches):]):
                idx = len(stats.matches) - len(xg_data) + i
                if 0 <= idx < len(stats.matches):
                    stats.matches[idx].xg = xg
                    stats.matches[idx].xga = xga

        # 4) Elo
        elo, src_elo = cached_clubelo(team)
        stats.elo = elo
        log["clubelo"] = src_elo

        # 5) Infortuni
        injuries, src_inj = cached_injuries(team)
        stats.injuries = injuries
        log["transfermarkt"] = src_inj

        return stats, log

    # Fetch parallelo
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        f_home  = executor.submit(_get_team_stats, home_team, True)
        f_away  = executor.submit(_get_team_stats, away_team, False)
        f_odds  = executor.submit(cached_odds, odds_key, league, home_team, away_team)

        home_stats, home_log = f_home.result()
        away_stats, away_log = f_away.result()
        odds, odds_src        = f_odds.result()

    # H2H sequenziale (dipende da comp_fd)
    from engine import fetch_h2h
    h2h_records, h2h_src = fetch_h2h(fd_key, home_team, away_team, league)

    return {
        "home_stats":  home_stats,
        "away_stats":  away_stats,
        "odds":        odds,
        "h2h":         h2h_records,
        "sources": {
            "home":   home_log,
            "away":   away_log,
            "odds":   odds_src,
            "h2h":    h2h_src,
        }
    }


# ─────────────────────────────────────────────
# HELPERS UI
# ─────────────────────────────────────────────

def source_badge(src: str) -> str:
    if any(x in src.lower() for x in ["errore","fallback","timeout","rate","non_trovat","vuoto","no_"]):
        return f'<span class="source-err">⚠ {src}</span>'
    if any(x in src.lower() for x in ["stima","math","default"]):
        return f'<span class="source-warn">~ {src}</span>'
    return f'<span class="source-ok">✓ {src}</span>'


def prob_to_color(prob: float) -> str:
    if prob >= 0.60: return "#00e676"
    if prob >= 0.45: return "#69f0ae"
    if prob >= 0.30: return "#ffd600"
    if prob >= 0.15: return "#ff7043"
    return "#ff5252"


def edge_html(edge: float) -> str:
    if edge >= 0.05:  return f'<span class="edge-pos">+{edge:.1%} ✅</span>'
    if edge >= 0.0:   return f'<span class="edge-neu">{edge:.1%}</span>'
    return f'<span class="edge-neg">{edge:.1%}</span>'


def confidence_bar(score: int) -> str:
    color = "#00e676" if score >= 75 else "#ffd600" if score >= 50 else "#ff5252"
    label = "🟢 Dati affidabili" if score >= 75 else "🟡 Usa con cautela" if score >= 50 else "🔴 Dati scarsi — non scommettere"
    return f"""
    <div class="conf-bar-wrap">
        <div class="conf-label">Confidence Score: <b style='color:{color}'>{score}/100</b> — {label}</div>
        <div style='background:#0d1117;border-radius:8px;height:16px;'>
            <div class="conf-bar" style='background:{color};width:{score}%;'></div>
        </div>
    </div>
    """


def format_form(form_str: str) -> str:
    html = ""
    for c in form_str.split():
        if c == "W":   html += '<span class="form-w">W</span> '
        elif c == "D": html += '<span class="form-d">D</span> '
        elif c == "L": html += '<span class="form-l">L</span> '
    return html


def render_market_row(label: str, prob: float, bk_odd: float = 0.0) -> str:
    fo = fair_odd(float(prob))
    edge = compute_edge(float(prob), bk_odd)
    edge_str = edge_html(edge) if bk_odd > 1.0 else '<span class="edge-neu">—</span>'
    bk_str = f"BK: {bk_odd:.2f}" if bk_odd > 1.0 else "—"
    color = prob_to_color(float(prob))
    return f"""
    <div class="mkt-row">
        <span class="mkt-name">{label}</span>
        <span>
            <span class="mkt-prob" style='color:{color}'>{float(prob):.1%}</span>
            <span class="mkt-odd"> | Fair: {fo} | {bk_str}</span>
            &nbsp;{edge_str}
        </span>
    </div>
    """


def traffic_light(prob: float, bk_odd: float, ci_low: float, ci_high: float) -> str:
    edge = compute_edge(prob, bk_odd)
    ci_ok = ci_low > 0 and ci_high > 0 and bk_odd > 0
    if edge >= 0.05 and bk_odd > 1.0 and prob >= ci_low:
        return '<span class="tl-green">🟢 SCOMMETTI</span>'
    elif edge >= 0.02 and bk_odd > 1.0:
        return '<span class="tl-yellow">🟡 VALUTA</span>'
    return '<span class="tl-red">🔴 EVITA</span>'


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        st.markdown("## ⚡ QF v9.0 Settings")
        st.divider()

        # API Keys
        st.markdown("### 🔑 API Keys")
        fd_key   = st.text_input("football-data.org key", type="password",
                                  value=st.session_state.get("fd_key", ""),
                                  help="Gratuito su football-data.org")
        af_key   = st.text_input("API-Football key (backup)", type="password",
                                  value=st.session_state.get("af_key", ""),
                                  help="api-sports.io")
        odds_key = st.text_input("The Odds API key", type="password",
                                  value=st.session_state.get("odds_key", ""),
                                  help="the-odds-api.com")

        st.session_state["fd_key"]   = fd_key
        st.session_state["af_key"]   = af_key
        st.session_state["odds_key"] = odds_key

        st.divider()
        # Stagione
        season = st.selectbox("Stagione", [2024, 2023, 2022], index=0)
        st.session_state["season"] = season

        st.divider()
        st.markdown("### ⚙️ Parametri avanzati")
        mot_h = st.slider("Motivazione Casa (%)", -20, 20, 0, key="mot_h")
        mot_a = st.slider("Motivazione Trasferta (%)", -20, 20, 0, key="mot_a")
        pres_h = st.slider("Pressione Casa", -10, 10, 0, key="pres_h")
        pres_a = st.slider("Pressione Trasferta", -10, 10, 0, key="pres_a")
        fat_h = st.number_input("Giorni riposo Casa", 1, 20, 7, key="fat_h")
        fat_a = st.number_input("Giorni riposo Trasferta", 1, 20, 7, key="fat_a")
        ref_mult = st.selectbox(
            "Stile arbitro",
            [0.7, 0.85, 1.0, 1.2, 1.5],
            index=2,
            format_func=lambda x: {0.7:"Molto permissivo",0.85:"Permissivo",
                                     1.0:"Neutro",1.2:"Rigido",1.5:"Molto rigido"}[x],
            key="ref_mult"
        )

        st.divider()
        debug_mode = st.checkbox("🔍 Modalità Debug (mostra fonti API)", value=True)
        st.session_state["debug_mode"] = debug_mode

        st.divider()
        st.markdown("### ℹ️ Info")
        st.caption("v9.0 — Cache per-squadra, fallback trasparente, 50K Monte Carlo")

    return fd_key, af_key, odds_key, season


# ─────────────────────────────────────────────
# STEP 1: INPUT
# ─────────────────────────────────────────────

def render_input(fd_key, af_key, odds_key, season):
    st.markdown("""
    <div class="qf-header">
        <h1>⚡ QUANTUM FOOTBALL ANALYTICS v9.0</h1>
        <p>Analisi predittiva avanzata · Poisson · Dixon-Coles · Monte Carlo 50K</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2, 2, 3])

    with col1:
        paesi = list(COMPETITIONS.keys())
        paese = st.selectbox("🌍 Paese", paesi, key="paese")

    with col2:
        leghe = COMPETITIONS[paese]
        league = st.selectbox("🏆 Competizione", leghe, key="league")

    with col3:
        st.write("")  # spacer

    col_h, col_vs, col_a = st.columns([5, 1, 5])
    with col_h:
        home_team = st.text_input("🏠 Squadra Casa", placeholder="es. Juventus", key="home_team").strip()
    with col_vs:
        st.markdown("<div style='text-align:center;padding-top:30px;font-size:1.5rem;color:#00d4ff;font-weight:700'>VS</div>", unsafe_allow_html=True)
    with col_a:
        away_team = st.text_input("✈️ Squadra Trasferta", placeholder="es. Inter", key="away_team").strip()

    st.write("")

    col_btn1, col_btn2, _ = st.columns([2, 2, 6])
    with col_btn1:
        search = st.button("🔍 ANALIZZA PARTITA", use_container_width=True)
    with col_btn2:
        if st.button("🔄 Reset", use_container_width=True):
            reset_all()
            st.rerun()

    if search:
        if not home_team or not away_team:
            st.error("❌ Inserisci entrambe le squadre")
            return
        if not fd_key:
            st.warning("⚠️ Inserisci almeno la chiave football-data.org nella sidebar")
            return

        # Reset prima di ogni nuova ricerca
        st.session_state["result"] = None
        st.session_state["raw"] = None

        with st.spinner(f"⏳ Raccolta dati per {home_team} vs {away_team}..."):
            progress = st.progress(0, text="Avvio fetch parallelo...")

            try:
                progress.progress(20, text="📡 Chiamate API in corso...")
                raw = fetch_all_data(
                    fd_key=fd_key,
                    af_key=af_key,
                    odds_key=odds_key,
                    league=league,
                    home_team=home_team,
                    away_team=away_team,
                    season=season,
                )
                progress.progress(60, text="⚙️ Calcolo probabilità...")

                engine = AdvancedEngine(
                    home_stats=raw["home_stats"],
                    away_stats=raw["away_stats"],
                    h2h=raw["h2h"],
                    odds=raw["odds"],
                    league=league,
                    motivation_h=st.session_state.get("mot_h", 0),
                    motivation_a=st.session_state.get("mot_a", 0),
                    pressure_h=st.session_state.get("pres_h", 0),
                    pressure_a=st.session_state.get("pres_a", 0),
                    fatigue_days_h=st.session_state.get("fat_h", 7),
                    fatigue_days_a=st.session_state.get("fat_a", 7),
                    referee_mult=st.session_state.get("ref_mult", 1.0),
                )
                progress.progress(80, text="🎲 Monte Carlo 50K simulazioni...")
                result = engine.compute()
                progress.progress(100, text="✅ Completato!")
                time.sleep(0.3)

                st.session_state["raw"] = raw
                st.session_state["result"] = result
                st.session_state["league"] = league
                st.session_state["home_team_name"] = home_team
                st.session_state["away_team_name"] = away_team
                st.session_state["step"] = "results"
                st.rerun()

            except Exception as e:
                st.error(f"❌ Errore durante l'analisi: {e}")
                st.exception(e)


# ─────────────────────────────────────────────
# STEP 2: RESULTS
# ─────────────────────────────────────────────

def render_results():
    result  = st.session_state["result"]
    raw     = st.session_state["raw"]
    league  = st.session_state.get("league", "")
    home    = st.session_state.get("home_team_name", "Casa")
    away    = st.session_state.get("away_team_name", "Trasferta")
    odds    = raw["odds"]
    sources = raw["sources"]
    debug   = st.session_state.get("debug_mode", True)

    # ── Header match
    st.markdown(f"""
    <div class="qf-header">
        <h1>⚡ {home} <span style='color:#7a8fa6'>VS</span> {away}</h1>
        <p>{league} · λ Casa: <b style='color:#00d4ff'>{result.lambda_h:.3f}</b> 
        · λ Trasferta: <b style='color:#ff7043'>{result.lambda_a:.3f}</b>
        · ρ Dixon-Coles: <b>{result.rho:.3f}</b></p>
    </div>
    """, unsafe_allow_html=True)

    # ── Bottone reset
    col_r, _ = st.columns([2, 8])
    with col_r:
        if st.button("🔄 NUOVA PARTITA"):
            reset_all()
            st.rerun()

    # ── Confidence
    st.markdown(confidence_bar(result.confidence_score), unsafe_allow_html=True)

    # ── Metriche principali
    c1, c2, c3, c4, c5 = st.columns(5)
    for col, label, val, sub in [
        (c1, "1 — Casa",      f"{result.prob_1:.1%}", f"Fair: {fair_odd(result.prob_1)}"),
        (c2, "X — Pareggio",  f"{result.prob_x:.1%}", f"Fair: {fair_odd(result.prob_x)}"),
        (c3, "2 — Trasferta", f"{result.prob_2:.1%}", f"Fair: {fair_odd(result.prob_2)}"),
        (c4, "λ Casa",        f"{result.lambda_h:.3f}", "Goal attesi"),
        (c5, "λ Trasferta",   f"{result.lambda_a:.3f}", "Goal attesi"),
    ]:
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">{label}</div>
                <div class="value">{val}</div>
                <div class="sub">{sub}</div>
            </div>
            """, unsafe_allow_html=True)

    st.write("")

    # ── Trappole e warnings
    if result.traps:
        with st.expander("🪤 Trappole bookmaker rilevate", expanded=True):
            for t in result.traps:
                st.warning(t)

    if result.warnings:
        with st.expander("⚠️ Warnings"):
            for w in result.warnings:
                st.info(w)

    # ── Debug fonti API
    if debug:
        with st.expander("🔍 Fonti dati utilizzate", expanded=False):
            col_dh, col_da = st.columns(2)
            with col_dh:
                st.markdown(f"**{home}**")
                for api, src in sources["home"].items():
                    st.markdown(f"- {api}: {source_badge(src)}", unsafe_allow_html=True)
                st.markdown(f"- Partite caricate: **{raw['home_stats'].n_matches}**")
                st.markdown(f"- Elo: **{raw['home_stats'].elo:.0f}**")
            with col_da:
                st.markdown(f"**{away}**")
                for api, src in sources["away"].items():
                    st.markdown(f"- {api}: {source_badge(src)}", unsafe_allow_html=True)
                st.markdown(f"- Partite caricate: **{raw['away_stats'].n_matches}**")
                st.markdown(f"- Elo: **{raw['away_stats'].elo:.0f}**")
            st.markdown(f"**Quote:** {source_badge(sources['odds'])}", unsafe_allow_html=True)
            st.markdown(f"**H2H:** {source_badge(sources['h2h'])} — {len(raw['h2h'])} partite", unsafe_allow_html=True)

    st.divider()

    # ──────────────────────────────────────────
    # TABS
    # ──────────────────────────────────────────
    tabs = st.tabs([
        "📊 1X2 & DC",
        "⚽ O/U & Tempi",
        "🔄 BTTS & Multi",
        "🎯 Gol Squadre",
        "🏷️ Speciali",
        "🎲 Combo",
        "📋 H2H & Forma",
        "🧮 Modello",
        "🛡️ Safety Check",
        "💰 ROI Tracker",
    ])

    markets = result.markets
    q = odds  # quote bookmaker

    # ── TAB 1: 1X2 & Doppia Chance
    with tabs[0]:
        st.markdown("### 1X2 — Esito Finale")
        for key, label, bk_q in [
            ("1", f"1 — {home} vince", q.get("quota_1", 0)),
            ("X", "X — Pareggio",      q.get("quota_x", 0)),
            ("2", f"2 — {away} vince",  q.get("quota_2", 0)),
        ]:
            prob = float(markets["1X2"][key])
            ci = {"1": result.mc_ci_1, "X": result.mc_ci_x, "2": result.mc_ci_2}[key]
            st.markdown(render_market_row(label, prob, bk_q), unsafe_allow_html=True)
            tl = traffic_light(prob, bk_q, ci[0], ci[1])
            ck = kelly_fraction(prob, bk_q)
            col1, col2, col3 = st.columns([2, 2, 6])
            with col1: st.markdown(tl, unsafe_allow_html=True)
            with col2: st.caption(f"CI 90%: [{ci[0]:.1%}, {ci[1]:.1%}]")
            with col3: st.caption(f"Kelly frazionato (25%): {ck:.1%}" if bk_q > 1 else "Kelly: — (nessuna quota BK)")
            st.write("")

        st.divider()
        st.markdown("### Doppia Chance")
        for key, label in [("1X","1X — Casa o Pareggio"), ("12","12 — Non Pareggio"), ("X2","X2 — Pareggio o Trasferta")]:
            st.markdown(render_market_row(label, markets["DC"][key]), unsafe_allow_html=True)

        st.divider()
        st.markdown("### Draw No Bet")
        for key, label in [("Casa", f"DNB {home}"), ("Trasferta", f"DNB {away}")]:
            st.markdown(render_market_row(label, markets["DNB"][key]), unsafe_allow_html=True)

    # ── TAB 2: Over/Under
    with tabs[1]:
        st.markdown("### Over / Under — Full Time")
        col_o, col_u = st.columns(2)
        with col_o:
            st.markdown("**OVER**")
            for line in [0.5, 1.5, 2.5, 3.5, 4.5]:
                bq = q.get("quota_over25", 0) if line == 2.5 else 0
                st.markdown(render_market_row(f"Over {line}", markets["OU"][f"over_{line}"], bq), unsafe_allow_html=True)
        with col_u:
            st.markdown("**UNDER**")
            for line in [0.5, 1.5, 2.5, 3.5, 4.5]:
                bq = q.get("quota_under25", 0) if line == 2.5 else 0
                st.markdown(render_market_row(f"Under {line}", markets["OU"][f"under_{line}"], bq), unsafe_allow_html=True)

        st.divider()
        st.markdown("### Primo Tempo")
        for key, label in markets["OU_1T"].items():
            st.markdown(render_market_row(key, label), unsafe_allow_html=True)

    # ── TAB 3: BTTS & Multigoal
    with tabs[2]:
        st.markdown("### BTTS — Both Teams To Score")
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            bq_si = q.get("quota_btts_si", 0)
            st.markdown(render_market_row("BTTS Sì", markets["BTTS"]["Si"], bq_si), unsafe_allow_html=True)
        with col_b2:
            bq_no = q.get("quota_btts_no", 0)
            st.markdown(render_market_row("BTTS No", markets["BTTS"]["No"], bq_no), unsafe_allow_html=True)

        st.divider()
        st.markdown("### BTTS per Tempo")
        for key, val in markets["BTTS_HALVES"].items():
            st.markdown(render_market_row(key, val), unsafe_allow_html=True)

        st.divider()
        st.markdown("### Multigoal")
        for key, val in markets["MULTI"].items():
            st.markdown(render_market_row(f"Multigoal {key}", val), unsafe_allow_html=True)

    # ── TAB 4: Gol Squadre
    with tabs[3]:
        col_gh, col_ga = st.columns(2)
        with col_gh:
            st.markdown(f"### Gol {home}")
            for k in [0,1,2,3,"2+"]:
                st.markdown(render_market_row(f"{k} gol {home}", markets["GOALS_H"][k]), unsafe_allow_html=True)
        with col_ga:
            st.markdown(f"### Gol {away}")
            for k in [0,1,2,3,"2+"]:
                st.markdown(render_market_row(f"{k} gol {away}", markets["GOALS_A"][k]), unsafe_allow_html=True)

        st.divider()
        st.markdown("### Gol Esatti (totali)")
        cols_g = st.columns(7)
        for i, n in enumerate(range(7)):
            with cols_g[i]:
                p = markets["EXACT_GOALS"].get(n, 0)
                st.metric(f"{n} gol", f"{float(p):.1%}")

        st.divider()
        st.markdown("### Top 10 Risultati Esatti")
        score_df = pd.DataFrame(markets["TOP_SCORES"], columns=["Risultato", "Probabilità"])
        score_df["Quota Fair"] = score_df["Probabilità"].apply(lambda x: fair_odd(float(x)))
        score_df["Probabilità"] = score_df["Probabilità"].apply(lambda x: f"{float(x):.2%}")
        st.dataframe(score_df, use_container_width=True, hide_index=True)

    # ── TAB 5: Speciali
    with tabs[4]:
        col_s1, col_s2 = st.columns(2)

        with col_s1:
            st.markdown("### HT/FT")
            htft_df = pd.DataFrame([
                {"Combo": k, "Probabilità": f"{v:.2%}", "Quota Fair": fair_odd(v)}
                for k, v in sorted(markets["HTFT"].items(), key=lambda x: -x[1])[:9]
            ])
            st.dataframe(htft_df, use_container_width=True, hide_index=True)

            st.markdown("### Handicap Europeo")
            for key, val in markets["HANDICAP"].items():
                st.markdown(render_market_row(key, val), unsafe_allow_html=True)

        with col_s2:
            st.markdown("### Winning Margin")
            for key, val in markets["MARGIN"].items():
                st.markdown(render_market_row(key, val), unsafe_allow_html=True)

            st.markdown("### Angoli")
            for key, val in markets["CORNERS"].items():
                st.markdown(render_market_row(key, val), unsafe_allow_html=True)

            st.markdown("### Cartellini")
            for key, val in markets["CARDS"].items():
                st.markdown(render_market_row(key, val), unsafe_allow_html=True)

    # ── TAB 6: Combo
    with tabs[5]:
        st.markdown("### 🎲 Top 20 Combinazioni Automatiche")
        combos = markets.get("COMBO", [])
        combo_df = pd.DataFrame([{
            "Combinazione": c["label"],
            "Probabilità":  f"{c['prob']:.2%}",
            "Quota Fair":   c["fair_odd"],
        } for c in combos])
        st.dataframe(combo_df, use_container_width=True, hide_index=True)

    # ── TAB 7: H2H & Forma
    with tabs[6]:
        col_h2h1, col_h2h2 = st.columns(2)

        with col_h2h1:
            st.markdown(f"### 📋 {home}")
            hs = raw["home_stats"]
            st.markdown(f"**Forma:** {format_form(hs.form_str())}", unsafe_allow_html=True)
            st.metric("Partite caricate", hs.n_matches)
            st.metric("Elo", f"{hs.elo:.0f}")
            st.metric("Media Gol Fatti", f"{hs.avg_gf():.2f}")
            st.metric("Media Gol Subiti", f"{hs.avg_ga():.2f}")
            st.metric("Media xG", f"{hs.avg_xg():.2f}")
            if hs.injuries:
                st.markdown("**Infortuni:**")
                for inj in hs.injuries:
                    st.caption(f"• {inj['player']} ({inj['position']})")

        with col_h2h2:
            st.markdown(f"### ✈️ {away}")
            as_ = raw["away_stats"]
            st.markdown(f"**Forma:** {format_form(as_.form_str())}", unsafe_allow_html=True)
            st.metric("Partite caricate", as_.n_matches)
            st.metric("Elo", f"{as_.elo:.0f}")
            st.metric("Media Gol Fatti", f"{as_.avg_gf():.2f}")
            st.metric("Media Gol Subiti", f"{as_.avg_ga():.2f}")
            st.metric("Media xG", f"{as_.avg_xg():.2f}")
            if as_.injuries:
                st.markdown("**Infortuni:**")
                for inj in as_.injuries:
                    st.caption(f"• {inj['player']} ({inj['position']})")

        st.divider()
        st.markdown("### ⚔️ H2H Storico")
        if raw["h2h"]:
            h2h_df = pd.DataFrame([{
                "Casa": r.home_team, "G. Casa": r.home_goals,
                "G. Trasferta": r.away_goals, "Trasferta": r.away_team,
                "Peso Anno": r.year_weight
            } for r in raw["h2h"]])
            st.dataframe(h2h_df, use_container_width=True, hide_index=True)
        else:
            st.info("Nessun dato H2H disponibile")

    # ── TAB 8: Modello
    with tabs[7]:
        st.markdown("### 🧮 Log Aggiustamenti Lambda")
        for step in result.adj_log:
            st.caption(f"→ {step}")

        st.divider()
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.markdown("### Matrice Punteggi Esatti (top 6×6)")
            mat = result.matrix[:7, :7]
            mat_df = pd.DataFrame(
                mat,
                columns=[f"A:{i}" for i in range(7)],
                index=[f"H:{i}" for i in range(7)]
            )
            st.dataframe(mat_df.applymap(lambda x: f"{x:.2%}"), use_container_width=True)
        with col_m2:
            st.markdown("### Confronto Analitico vs Monte Carlo")
            mc_df = pd.DataFrame({
                "Mercato": ["1 (Casa)", "X (Pareggio)", "2 (Trasferta)"],
                "Analitico": [f"{result.prob_1:.1%}", f"{result.prob_x:.1%}", f"{result.prob_2:.1%}"],
                "CI 90% Low": [f"{result.mc_ci_1[0]:.1%}", f"{result.mc_ci_x[0]:.1%}", f"{result.mc_ci_2[0]:.1%}"],
                "CI 90% High": [f"{result.mc_ci_1[1]:.1%}", f"{result.mc_ci_x[1]:.1%}", f"{result.mc_ci_2[1]:.1%}"],
            })
            st.dataframe(mc_df, use_container_width=True, hide_index=True)
            st.caption(f"ρ Dixon-Coles usato: **{result.rho:.4f}**")

    # ── TAB 9: Safety Check
    with tabs[8]:
        st.markdown("### 🛡️ Safety Check — Consistenza Mercati")
        checks = []
        # Check somma 1X2
        s1x2 = result.prob_1 + result.prob_x + result.prob_2
        checks.append(("Somma 1X2 ≈ 1.0", abs(s1x2 - 1.0) < 0.01, f"{s1x2:.4f}"))
        # Check O2.5 > O3.5
        checks.append(("Over 2.5 > Over 3.5", markets["OU"]["over_2.5"] > markets["OU"]["over_3.5"], "OK"))
        # Check BTTS
        checks.append(("BTTS Sì + No ≈ 1.0",
                        abs(markets["BTTS"]["Si"] + markets["BTTS"]["No"] - 1.0) < 0.01,
                        f"{markets['BTTS']['Si'] + markets['BTTS']['No']:.4f}"))
        # Check lambda
        checks.append(("λ in range plausibile [0.3, 4.5]",
                        0.3 <= result.lambda_h <= 4.5 and 0.3 <= result.lambda_a <= 4.5,
                        f"λH={result.lambda_h:.3f} λA={result.lambda_a:.3f}"))
        # Confidence
        checks.append(("Confidence Score ≥ 50", result.confidence_score >= 50, f"{result.confidence_score}/100"))

        for name, ok, val in checks:
            icon = "✅" if ok else "❌"
            st.markdown(f"{icon} **{name}** — `{val}`")

        if result.traps:
            st.divider()
            st.markdown("### 🪤 Trappole Rilevate")
            for t in result.traps:
                st.error(t)
        else:
            st.success("✅ Nessuna trappola bookmaker rilevata")

        st.divider()
        st.markdown("### 📉 Intervalli di Confidenza Monte Carlo (90%)")
        ci_data = {
            "1 (Casa)":      result.mc_ci_1,
            "X (Pareggio)":  result.mc_ci_x,
            "2 (Trasferta)": result.mc_ci_2,
        }
        for label, (lo, hi) in ci_data.items():
            st.progress(int(hi * 100), text=f"{label}: [{lo:.1%} — {hi:.1%}]")

    # ── TAB 10: ROI Tracker
    with tabs[9]:
        st.markdown("### 💰 ROI Tracker — Registro Scommesse")
        st.info("ℹ️ I dati vengono persi al riavvio. Per persistenza, esporta con il bottone CSV.")

        with st.form("roi_form"):
            rc1, rc2, rc3, rc4 = st.columns(4)
            with rc1: bet_market = st.text_input("Mercato", placeholder="es. 1X2 — Casa")
            with rc2: bet_odd = st.number_input("Quota", min_value=1.01, value=2.00, step=0.05)
            with rc3: bet_stake = st.number_input("Puntata (€)", min_value=0.5, value=10.0, step=0.5)
            with rc4: bet_result = st.selectbox("Esito", ["—", "Win", "Loss"])
            submitted = st.form_submit_button("➕ Aggiungi")

        if submitted and bet_market and bet_result != "—":
            profit = (bet_odd - 1) * bet_stake if bet_result == "Win" else -bet_stake
            st.session_state["roi_bets"].append({
                "Data": datetime.now().strftime("%d/%m %H:%M"),
                "Partita": f"{home} vs {away}",
                "Mercato": bet_market,
                "Quota": bet_odd,
                "Puntata": bet_stake,
                "Esito": bet_result,
                "P/L": profit,
            })

        bets = st.session_state["roi_bets"]
        if bets:
            df_roi = pd.DataFrame(bets)
            tot_pl = df_roi["P/L"].sum()
            tot_stk = df_roi["Puntata"].sum()
            wins = (df_roi["Esito"] == "Win").sum()
            roi_pct = (tot_pl / tot_stk * 100) if tot_stk > 0 else 0

            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("Totale Scommesse", len(bets))
            mc2.metric("Win Rate", f"{wins/len(bets):.0%}")
            mc3.metric("P/L Totale", f"€{tot_pl:+.2f}")
            mc4.metric("ROI", f"{roi_pct:+.1f}%")

            # Colora P/L
            def color_pl(val):
                color = 'color: #00e676' if val > 0 else 'color: #ff5252' if val < 0 else ''
                return color

            st.dataframe(
                df_roi.style.applymap(color_pl, subset=["P/L"]),
                use_container_width=True,
                hide_index=True
            )

            # Export CSV
            csv = df_roi.to_csv(index=False)
            st.download_button("📥 Esporta CSV", csv, "roi_tracker.csv", "text/csv")
        else:
            st.caption("Nessuna scommessa registrata.")

    # ── Storico partite analizzate
    if st.session_state.get("history") is not None:
        entry = {
            "Partita": f"{home} vs {away}",
            "Lega": league,
            "λH": round(result.lambda_h, 3),
            "λA": round(result.lambda_a, 3),
            "P(1)": f"{result.prob_1:.1%}",
            "P(X)": f"{result.prob_x:.1%}",
            "P(2)": f"{result.prob_2:.1%}",
            "Conf.": result.confidence_score,
        }
        history = st.session_state["history"]
        if not history or history[-1]["Partita"] != entry["Partita"]:
            history.append(entry)
        st.session_state["history"] = history[-10:]


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    init_state()
    fd_key, af_key, odds_key, season = render_sidebar()

    if st.session_state["step"] == "input":
        render_input(fd_key, af_key, odds_key, season)
    elif st.session_state["step"] == "results":
        if st.session_state.get("result") is None:
            st.session_state["step"] = "input"
            st.rerun()
        render_results()

    # Storico sidebar
    if st.session_state.get("history"):
        with st.sidebar:
            st.divider()
            st.markdown("### 📜 Ultime analisi")
            for h in reversed(st.session_state["history"][-5:]):
                st.caption(f"**{h['Partita']}** · {h['P(1)']} / {h['P(X)']} / {h['P(2)']} · Conf: {h['Conf.']}")


if __name__ == "__main__":
    main()
